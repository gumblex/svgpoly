#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Converts Bezier curve to line segments.

From Anti-Grain Geometry (AGG) - Version 2.5
http://antigrain.com/research/adaptive_bezier/

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
MA 02110-1301, USA.
"""

import math

CURVE_DISTANCE_EPSILON = 1e-30
CURVE_COLLINEARITY_EPSILON = 1e-30
CURVE_ANGLE_TOLERANCE_EPSILON = 0.01
CURVE_RECURSION_LIMIT = 32


def point_sq_distance(p1: complex, p2: complex):
    d = p1 - p2
    return d.real**2 + d.imag**2


def flatten3(p1: complex, p2: complex, p3: complex,
             tol_dist=1, tol_angle=0, level=0) -> list:
    if level > CURVE_RECURSION_LIMIT:
        return []
    tol_dist_sq = tol_dist * tol_dist

    # Calculate all the mid-points of the line segments
    p12 = (p1 + p2) / 2
    p23 = (p2 + p3) / 2
    p123 = (p12 + p23) / 2
    d = p3 - p1

    dist = abs(((p2.real - p3.real) * d.imag - (p2.imag - p3.imag) * d.real))

    if dist > CURVE_COLLINEARITY_EPSILON:
        # Regular case
        if dist * dist <= tol_dist_sq * (d.real**2 + d.imag**2):
            # If the curvature doesn't exceed the distance_tolerance value
            # we tend to finish subdivisions.
            if tol_angle < CURVE_ANGLE_TOLERANCE_EPSILON:
                return [p123]

            # Angle & Cusp Condition
            p3_2 = p3 - p2
            p2_1 = p2 - p1
            da = abs(math.atan2(p3_2.imag, p3_2.real) -
                     math.atan2(p2_1.imag, p2_1.real))
            if da >= math.pi:
                da = 2*math.pi - da

            if da < tol_angle:
                # Finally we can stop the recursion
                return [p123]
    else:
        # Collinear case
        da = d.real**2 + d.imag**2
        p2_1 = p2 - p1
        if da == 0:
            dist = point_sq_distance(p1, p2)
        else:
            dist = (p2_1.real*d.real + p2_1.imag*d.imag) / da
            if 0 < dist < 1:
                # Simple collinear case, 1---2---3
                # We can leave just two endpoints
                return []

            if dist <= 0:
                dist = point_sq_distance(p2, p1)
            elif dist >= 1:
                dist = point_sq_distance(p2, p3)
            else:
                dist = point_sq_distance(p2, p1 + dist * d)
        if dist < tol_dist_sq:
            return [p2]

    # Continue subdivision
    return (flatten3(p1, p12, p123, tol_dist, tol_angle, level + 1) +
            flatten3(p123, p23, p3, tol_dist, tol_angle, level + 1))


def flatten4(p1: complex, p2: complex, p3: complex, p4: complex,
             tol_dist=1, tol_angle=0, level=0) -> list:
    if level > CURVE_RECURSION_LIMIT:
        return []
    tol_dist_sq = tol_dist * tol_dist

    # Calculate all the mid-points of the line segments
    p12 = (p1 + p2) / 2
    p23 = (p2 + p3) / 2
    p34 = (p3 + p4) / 2
    p123 = (p12 + p23) / 2
    p234 = (p23 + p34) / 2
    p1234 = (p123 + p234) / 2
    d = p4 - p1

    # Try to approximate the full cubic curve by a single straight line

    d2 = abs(((p2.real - p4.real) * d.imag - (p2.imag - p4.imag) * d.real))
    d3 = abs(((p3.real - p4.real) * d.imag - (p3.imag - p4.imag) * d.real))

    case = ((int(d2 > CURVE_COLLINEARITY_EPSILON) << 1) +
            int(d3 > CURVE_COLLINEARITY_EPSILON))

    if case == 0:
        # All collinear OR p1==p4
        k = d.real**2 + d.imag**2
        if k == 0:
            d2 = point_sq_distance(p1, p2)
            d3 = point_sq_distance(p4, p3)
        else:
            k = 1 / k
            da1 = p2.real - p1.real
            da2 = p2.imag - p1.imag
            d2 = k * (da1*d.real + da2*d.imag)
            da1 = p3.real - p1.real
            da2 = p3.imag - p1.imag
            d3 = k * (da1*d.real + da2*d.imag)
            if 0 < d2 < 1 and 0 < d3 < 1:
                # Simple collinear case, 1---2---3---4
                # We can leave just two endpoints
                return []

            if d2 <= 0:
                d2 = point_sq_distance(p2, p1)
            elif d2 >= 1:
                d2 = point_sq_distance(p2, p4)
            else:
                d2 = point_sq_distance(p2, p1 + d2 * d)

            if d3 <= 0:
                d3 = point_sq_distance(p3, p1)
            elif d3 >= 1:
                d3 = point_sq_distance(p3, p4)
            else:
                d3 = point_sq_distance(p3, p1 + d3 * d)
        if d2 > d3:
            if d2 < tol_dist_sq:
                return [p2]
        elif d3 < tol_dist_sq:
            return [p3]
    elif case == 1:
        # p1,p2,p4 are collinear, p3 is significant
        if d3 * d3 <= tol_dist_sq * (d.real**2 + d.imag**2):
            if tol_angle < CURVE_ANGLE_TOLERANCE_EPSILON:
                return [p23]
            # Angle Condition
            p4_3 = p4 - p3
            p3_2 = p3 - p2
            da1 = abs(math.atan2(p4_3.imag, p4_3.real) -
                      math.atan2(p3_2.imag, p3_2.real))
            if da1 >= math.pi:
                da1 = 2*math.pi - da1
            if da1 < tol_angle:
                return [p2, p3]
    elif case == 2:
        # p1,p3,p4 are collinear, p2 is significant
        if d2 * d2 <= tol_dist_sq * (d.real**2 + d.imag**2):
            if tol_angle < CURVE_ANGLE_TOLERANCE_EPSILON:
                return [p23]
            # Angle Condition
            p3_2 = p3 - p2
            p2_1 = p2 - p1

            da1 = abs(math.atan2(p3_2.imag, p3_2.real) -
                      math.atan2(p2_1.imag, p2_1.real))
            if da1 >= math.pi:
                da1 = 2*math.pi - da1
            if da1 < tol_angle:
                return [p2, p3]
    elif case == 3:
        # Regular case
        if (d2 + d3)*(d2 + d3) <= tol_dist_sq * (d.real**2 + d.imag**2):
            # If the curvature doesn't exceed the distance_tolerance value
            # we tend to finish subdivisions.
            if tol_angle < CURVE_ANGLE_TOLERANCE_EPSILON:
                return [p23]

            # Angle & Cusp Condition
            pdiff = p3 - p2
            k = math.atan2(pdiff.imag, pdiff.real)
            pdiff = p2 - p1
            da1 = abs(k - math.atan2(pdiff.imag, pdiff.real))
            pdiff = p4 - p3
            da2 = abs(math.atan2(pdiff.imag, pdiff.real) - k)
            if da1 >= math.pi:
                da1 = 2*math.pi - da1
            if da2 >= math.pi:
                da2 = 2*math.pi - da2
            if da1 + da2 < tol_angle:
                # Finally we can stop the recursion
                return [p23]

    # Continue subdivision
    return (flatten4(p1, p12, p123, p1234, tol_dist, tol_angle, level + 1) +
            flatten4(p1234, p234, p34, p4, tol_dist, tol_angle, level + 1))
