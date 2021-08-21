#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Convert Pixel Art pictures to exactly same SVG files, with path simplification.

------------------------

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


import sys
from PIL import Image


def get_borders(im, mask, start_coords):
    xsize, ysize = im.size
    val = im.getpixel(start_coords)
    stack = set((start_coords,))
    borders = []
    while stack:
        x, y = stack.pop()

        this_val = im.getpixel((x, y))
        if this_val == val and mask.getpixel((x, y)) != 1:
            mask.putpixel((x, y), 1)

            neighbours = (
                ((x - 1, y), ((x, y + 1), (x, y))),
                ((x, y - 1), ((x, y), (x + 1, y))),
                ((x + 1, y), ((x + 1, y), (x + 1, y + 1))),
                ((x, y + 1), ((x + 1, y + 1), (x, y + 1))),
            )
            for pix, border in neighbours:
                if pix[0] == -1 or pix[0] == xsize or pix[1] == -1 or pix[1] == ysize:
                    borders.append(border)
                    continue
                if im.getpixel(pix) == val:
                    stack.add(pix)
                else:
                    borders.append(border)
    borders.sort()
    for i in range(len(borders)):
        for j in range(i + 1, len(borders)):
            if borders[i][1] != borders[j][0]:
                continue
            borders[i + 1], borders[j] = borders[j], borders[i + 1]
            break
    ring_origin = None
    last_diff = (0, 0)
    paths = []
    path = []
    for p0, p1 in borders:
        if ring_origin is None:
            ring_origin = p0
        diff = (p1[0] - p0[0], p1[1] - p0[1])
        if diff != last_diff:
            path.append(p0)
        last_diff = diff
        if p1 == ring_origin:
            path.append(p1)
            if paths:
                path.reverse()
            paths.append(path)
            path = []
            ring_origin = None
    if path:
        paths.append(path)
    return paths


def color_style(color):
    if len(color) == 3 or len(color) == 4 and color[-1] == 255:
        return 'fill="#%02x%02x%02x"' % color[:3]
    elif len(color) == 1:
        return 'fill="#%02x%02x%02x"' % ((color[0],)*3)
    else:
        return 'fill="#%02x%02x%02x" fill-opacity="%.4f"' % (
            color[:3] + (color[-1] / 255,))


def pixel2svg(filename):
    im = Image.open(filename)
    hist = im.histogram()
    bgcolor = tuple(
        max(enumerate(hist[i*256:(i+1)*256]), key=lambda x: x[1])[0]
        for i in range(len(im.getbands()))
    )
    width, height = im.size
    svg = [(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg baseProfile="full" version="1.1" height="{h}" width="{w}" '
        'xmlns="http://www.w3.org/2000/svg" '
        'xmlns:ev="http://www.w3.org/2001/xml-events" '
        'xmlns:xlink="http://www.w3.org/1999/xlink"><defs />\n'
        '<rect {bg} height="{h}" width="{w}" x="0" y="0" />'
    ).format(w=width, h=height, bg=color_style(bgcolor))]
    mask = Image.new('1', im.size)
    for x in range(width):
        for y in range(height):
            if im.getpixel((x, y)) == bgcolor:
                mask.putpixel((x, y), 1)
    pix_num = width * height
    last_pos = 0
    while True:
        data = mask.getdata()
        for i in range(last_pos, pix_num):
            if data[i] == 0:
                break
        else:
            break
        y, x = divmod(i, width)
        last_pos = i
        color = im.getpixel((x, y))
        paths = get_borders(im, mask, (x, y))
        d = []
        for path in paths:
            d.append('M%d,%d' % path[0])
            last_point = path[0]
            for p in path[1:]:
                if p[0] == last_point[0]:
                    d.append('V%d' % p[1])
                elif p[1] == last_point[1]:
                    d.append('H%d' % p[0])
                else:
                    d.append('L%d,%d' % p)
                last_point = p
            d.append('Z')
        svg.append('<path d="{d}" {rule}{color} />'.format(
            d=' '.join(d),
            rule=('fill-rule="evenodd" ' if len(paths) > 1 else ''),
            color=color_style(color)
        ))
    svg.append('</svg>')
    return '\n'.join(svg)


if __name__ == '__main__':
    print(pixel2svg(sys.argv[1]))
