#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Converts SVG Paths to Polygons or Polylines.

Copyright (c) 2021 gumblex

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


import os
import re
import math
import cmath
import itertools
import functools
from xml.dom.minidom import parse

import numpy as np
import svgpathtools

import bezflatten

re_transform = re.compile(r'(\w+)\(([^)]+)\)')
re_comma_wsp = re.compile(r',\s*|\s+,?\s*')


def polyline2pathd(polyline_d):
    """converts the string from a polyline d-attribute to a string for a Path
    object d-attribute"""
    points = polyline_d.replace(', ', ',')
    points = points.replace(' ,', ',')
    points = points.split()

    if points[0] == points[-1]:
        closed = True
    else:
        closed = False

    d = 'M' + points.pop(0).replace(',', ' ')
    for p in points:
        d += 'L' + p.replace(',', ' ')
    if closed:
        d += 'z'
    return d


def parse_transform(s):
    mtx = np.eye(3, dtype=float)
    for match in re_transform.finditer(s.strip()):
        fn = match.group(1)
        args = tuple(map(float, re_comma_wsp.split(match.group(2))))
        if fn == 'matrix':
            mtx = mtx @ np.array((
                (args[0], args[2], args[4]),
                (args[1], args[3], args[5]),
                (0, 0, 1)
            ))
        elif fn == 'translate':
            x = args[0]
            y = args[1] if len(args) > 1 else 0
            mtx = mtx @ np.array((
                (1, 0, x),
                (0, 1, y),
                (0, 0, 1)
            ))
        elif fn == 'scale':
            x = args[0]
            y = args[1] if len(args) > 1 else x
            mtx = mtx @ np.array((
                (x, 0, 0),
                (0, y, 0),
                (0, 0, 1)
            ))
        elif fn == 'rotate':
            r = math.radians(args[0])
            if len(args) > 1:
                x = args[1]
                y = args[2]
            else:
                x = y = 0
            if x and y:
                mtx = mtx @ np.array((
                    (1, 0, x),
                    (0, 1, y),
                    (0, 0, 1)
                ))
            mtx = mtx @ np.array((
                (math.cos(r), -math.sin(r), 0),
                (math.sin(r), math.cos(r), 0),
                (0, 0, 1)
            ))
            if x and y:
                mtx = mtx @ np.array((
                    (1, 0, -x),
                    (0, 1, -y),
                    (0, 0, 1)
                ))
        elif fn == 'skewX':
            a = math.radians(args[0])
            mtx = mtx @ np.array((
                (1, math.tan(a), 0),
                (0, 1, 0),
                (0, 0, 1)
            ))
        elif fn == 'skewY':
            a = math.radians(args[0])
            mtx = mtx @ np.array((
                (1, 0, 0),
                (math.tan(a), 1, 0),
                (0, 0, 1)
            ))
        else:
            raise ValueError('unknown transform ' + match.group(0))
    return mtx


def svg2paths(svg_file_location):
    """
    Converts an SVG file into a list of Path objects and a list of
    dictionaries containing their attributes.  This currently supports
    SVG Path, Line, Polyline, and Polygon elements.
    :param svg_file_location: the location of the svg file
    :return: list of Path objects, list of path attribute dictionaries, and
    (optionally) a dictionary of svg-attributes
    """
    doc = parse(os.path.abspath(svg_file_location))

    def dom2dict(element):
        """Converts DOM elements to dictionaries of attributes."""
        keys = list(element.attributes.keys())
        values = [val.value for val in list(element.attributes.values())]
        return dict(list(zip(keys, values)))

    def node_all_transforms(element):
        node = element
        mtx = None
        mtxs = []
        while hasattr(node, 'getAttribute'):
            tf = node.getAttribute('transform').strip()
            if tf:
                newmtx = parse_transform(tf)
                mtxs.append(newmtx)
                if mtx is None:
                    mtx = newmtx
                else:
                    mtx = newmtx @ mtx
            node = node.parentNode
        return mtx

    # Use minidom to extract path strings from input SVG
    nodes = doc.getElementsByTagName('path')
    paths = list(map(dom2dict, nodes))
    d_strings = [el['d'] for el in paths]
    transforms = list(map(node_all_transforms, nodes))
    attribute_dictionary_list = paths

    # Use minidom to extract polyline strings from input SVG, convert to
    # path strings, add to list
    nodes = doc.getElementsByTagName('polyline')
    plins = [dom2dict(el) for el in nodes]
    d_strings += [polyline2pathd(pl['points']) for pl in plins]
    transforms.extend(map(node_all_transforms, nodes))
    attribute_dictionary_list.extend(plins)

    # Use minidom to extract polygon strings from input SVG, convert to
    # path strings, add to list
    nodes = doc.getElementsByTagName('polygon')
    pgons = [dom2dict(el) for el in nodes]
    d_strings += [polyline2pathd(pg['points']) + 'z' for pg in pgons]
    transforms.extend(map(node_all_transforms, nodes))
    attribute_dictionary_list.extend(pgons)

    nodes = doc.getElementsByTagName('line')
    lines = [dom2dict(el) for el in nodes]
    d_strings += [('M' + l['x1'] + ' ' + l['y1'] +
                   'L' + l['x2'] + ' ' + l['y2']) for l in lines]
    transforms.extend(map(node_all_transforms, nodes))
    attribute_dictionary_list.extend(lines)

    for nodetype in ('circle', 'ellipse'):
        nodes = doc.getElementsByTagName(nodetype)
        ellipse = []
        for node in nodes:
            e = dom2dict(node)
            ellipse.append(e)
            cx = float(e['cx'])
            cy = float(e['cy'])
            rx = float(e.get('rx', 'r'))
            ry = float(e.get('ry', 'r'))
            d_strings.append("M%s,%s a%s,%s 0 1,0 %s,0 a%s,%s 0 1,0 %s,0" % (
                (cx - rx), cy, rx, ry, 2 * rx, rx, ry, -2 * rx))
            transforms.append(node_all_transforms(node))
        attribute_dictionary_list.extend(ellipse)

    doc.unlink()
    path_list = [svgpathtools.parse_path(d) for d in d_strings]
    return path_list, transforms, attribute_dictionary_list


def flatten_arc(arc: svgpathtools.Arc, tol_dist=1, t0=0., t1=1.):
    p1 = arc.point(t0)
    p2 = arc.point(t1)
    tmid = (t0 + t1)/2
    pmid = arc.point((t0 + t1)/2)

    pvec = p2 - p1
    dist = abs(pvec.imag*pmid.real - pvec.real*pmid.imag +
               p2.real*p1.imag - p1.real*p2.imag) / abs(p2 - p1)
    if dist <= tol_dist:
        return [pmid]
    return (flatten_arc(arc, tol_dist, t0, tmid) +
            flatten_arc(arc, tol_dist, tmid, t1))


def segment2polyline(segment, tol_dist=1, tol_angle=0):
    if isinstance(segment, svgpathtools.Line):
        return [segment.start, segment.end]
    elif isinstance(segment, svgpathtools.QuadraticBezier):
        return (
            [segment.start]
            + bezflatten.flatten3(
                segment.start, segment.control, segment.end, tol_dist, tol_angle)
            + [segment.end]
        )
    elif isinstance(segment, svgpathtools.CubicBezier):
        return (
            [segment.start]
            + bezflatten.flatten4(
                segment.start, segment.control1, segment.control2, segment.end,
                tol_dist, tol_angle)
            + [segment.end]
        )
    elif isinstance(segment, svgpathtools.Arc):
        return (
            [segment.start] + flatten_arc(segment, tol_dist) + [segment.end]
        )
    else:
        raise ValueError('unknown segment: %r' % segment)


def svg2linesegments(filename, tol_dist=0.5, tol_angle=0):
    path_list, transforms, attributes = svg2paths(filename)
    paths = []
    for path, transform in zip(path_list, transforms):
        parts = []
        for segment in path:
            polyseg = segment2polyline(segment, tol_dist, tol_angle)
            if parts and cmath.isclose(parts[-1][-1], polyseg[0], abs_tol=1e-10):
                parts[-1].extend(polyseg)
            else:
                parts.append(polyseg)
        for i in range(len(parts)):
            partarr_cplx = np.array(parts[i])
            partarr_real = np.vstack((
                partarr_cplx.real, partarr_cplx.imag,
                np.ones(partarr_cplx.shape[0])))
            if transform is not None:
                partarr_real = transform @ partarr_real
            parts[i] = tuple(partarr_real[0] + 1j*partarr_real[1])
        parts = [np.array(part) for part in parts]
        paths.append(parts)
    return paths


def bounding_box(paths):
    minx = miny = math.inf
    maxx = maxy = -math.inf
    for path in paths:
        for part in path:
            for point in part:
                minx = min(minx, point.real)
                maxx = max(maxx, point.real)
                miny = min(miny, point.imag)
                maxy = max(maxy, point.imag)
    return minx + miny*1j, maxx + maxy*1j


def output_svg(plain_paths, filename):
    paths = []
    for path in plain_paths:
        segments = []
        for part in path:
            segments.extend(
                svgpathtools.Line(p1, p2) for p1, p2 in zip(part, part[1:]))
        paths.append(svgpathtools.Path(*segments))
    svgpathtools.wsvg(paths, filename=filename)


def output_geojson(plain_paths, filename, polygon=True, from_proj=None):
    import json
    objs = []
    transform = lambda x: x
    for path in plain_paths:
        parts = [[transform((p.real, p.imag)) for p in part] for part in path]
        ispolygon = all(
            cmath.isclose(part[0], part[-1], abs_tol=1e-10) for part in path)
        if polygon and ispolygon:
            if len(parts) > 1:
                objs.append({"type": "MultiPolygon", "coordinates": parts})
            else:
                objs.append({"type": "Polygon", "coordinates": parts[0]})
        else:
            if len(parts) > 1:
                objs.append({"type": "MultiLineString", "coordinates": parts})
            else:
                objs.append({"type": "LineString", "coordinates": parts[0]})
    coll = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {}, "geometry": o}
            for o in objs]
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(coll, f)


def main(inputfile, outputfile):
    paths = svg2linesegments(inputfile)
    output_svg(paths, outputfile)
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
