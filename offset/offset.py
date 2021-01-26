import itertools
import math
from typing import List
from typing import Tuple

from geom.Vector2 import Vector2
import matplotlib.pyplot as plt


def triangle_area(a: Vector2, b: Vector2, c: Vector2):
	"""for a clockwise triangle this will return the area"""
	# (x1y2 + x2y3 + x3y1 – x1y3 – x2y1 – x3y2) / 2
	# a x b = a.x*b.y - a.y*b.x
	# b x c = b.x*c.y - b.y*c.x
	# c x a = c.x*a.y - c.y*a.x
	# (a.cross(b) + b.cross(c) + c.cross(a)) / 2
	return (
			       a.x * b.y - b.x * a.y +
			       b.x * c.y - c.x * b.y +
			       c.x * a.y - c.y * a.x
	       ) * 0.5


def pairwise(iterable):
	"""s -> (s0,s1), (s1,s2), (s2, s3), ..."""
	a, b = itertools.tee(iterable)
	next(b, None)
	return zip(a, b)


def grouper(iterable, n, fillvalue=None):
	"""Collect data into fixed-length chunks or blocks"""
	# grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
	args = [iter(iterable)] * n
	return itertools.zip_longest(*args, fillvalue=fillvalue)


def clockwise(a: Vector2, b: Vector2, c: Vector2):
	return (b - a).left.dot(c - a)


def are_consecutive_segments_collinear(ab: Vector2, cd: Vector2):
	# this result is specific to two consecutive offset line segments. If they are parallel, we can assume they are also collinear.
	return math.isclose(ab.cross(cd), 0)


def segments_are_collinear(a1: Vector2, a2: Vector2, b1: Vector2, b2: Vector2):
	a1a2 = a2 - a1
	a1b1 = b1 - a1
	a1b2 = b2 - a1
	t1 = a1b1.x / a1a2.x
	t2 = a1b2.x / a1a2.x
	return math.isclose(a1a2.y * t1, a1b1.y) and math.isclose(a1a2.y * t2, a1b2.y)


def segments_are_overlapping(a: Vector2, b: Vector2, c: Vector2):
	ab = b - a
	bc = c - b
	inv_det = ab.cross(bc)
	if math.isclose(inv_det, 0):
		# line segments are parallel
		
		return False
	# segments are parallel
	return False


def solve_intersection(a_origin: Vector2, a_velocity: Vector2, b_origin: Vector2, b_velocity: Vector2):
	time_b = (a_origin - b_origin).cross(a_velocity.unit) / b_velocity.cross(a_velocity.unit)
	time_a = (b_origin - a_origin).cross(b_velocity.unit) / a_velocity.cross(b_velocity.unit)
	return b_origin + b_velocity.scaled(time_b), time_a, time_b


def transpose_vector_list(inp: List[Vector2]):
	out = [[], []]
	for item in inp:
		out[0].append(item.x)
		out[1].append(item.y)
	return out


Line = Tuple[Vector2, Vector2]
LineString = List[Vector2]


def offset_segments(inp: LineString, offset: float) -> Tuple[List[Line], List[Line]]:
	segments_positive: List[Line] = []
	segments_negative: List[Line] = []
	for a, b in zip(inp, inp[1:]):
		offset_vector = (b - a).left.unit.scaled(offset)
		segments_positive.append((a + offset_vector, b + offset_vector))
		segments_negative.append((a - offset_vector, b - offset_vector))
	return segments_positive, segments_negative


def connect_offset_segments(inp: List[Line]) -> LineString:
	# Algorithm 1 - connect disjoint line segments by extension
	result = [inp[0][0]]
	for (a, b), (c, d) in pairwise(inp):
		ab = b - a
		cd = d - c
		
		if math.isclose(ab.cross(cd), 0):
			# consecutive segments are parallel and therefore also collinear
			# Case 1
			result.append(b)
		else:
			# Case 2
			
			# the following function finds the intersection of two line segments and the coefficients such that:
			# p = a + t_ab*ab
			# p = c + t_cd*cd
			# note that t_ab and t_cd are between 0 and 1 when p lies within their respective line segments.
			p, t_ab, t_cd = solve_intersection(a, ab, c, cd)
			
			# TIP means 'true intersection point' : ie. the intersection point lies within the segment.
			# FIP means 'false intersection point' : ie the intersection point lies outside the segment.
			# PFIP means 'positive false intersection point' : ie the intersection point lies beyond the segment in the direction of the segment
			# NFIP is the 'negative false intersection point' : ie the intersection point lies behind the segment in the direction of the segment
			
			TIP_ab = 0 <= t_ab <= 1
			FIP_ab = not TIP_ab
			PFIP_ab = FIP_ab and t_ab > 0
			# NFIP_ab = FIP_ab and t_ab < 0
			
			TIP_cd = 0 <= t_cd <= 1
			FIP_cd = not TIP_cd
			# PFIP_cd = FIP_cd and t_cd > 0
			# NFIP_cd = FIP_cd and t_cd < 0
			
			if TIP_ab and TIP_cd:
				# Case 2a
				result.append(p)
			elif FIP_ab and FIP_cd:
				# Case 2b.
				if PFIP_ab:
					result.append(p)
				else:
					result.append(b)
					result.append(c)
			else:
				# Case 2c. (either ab or cd
				result.append(b)
				result.append(c)
	
	result.append(d)
	return result


def self_intersection(inp: LineString) -> Tuple[List[Vector2], List[float]]:
	intersection_parameters = []
	intersection_points = []
	for i, (a, b) in enumerate(pairwise(inp)):
		for j, (c, d) in enumerate(pairwise(inp[i + 2:])):
			print(f"{i},{i + 1} against {j + i + 2},{j + i + 1 + 2}")
			p, t1, t2 = solve_intersection(a, b - a, c, d - c)
			if 0 <= t2 <= 1:
				if math.isclose(t1, 0):
					pass
				elif math.isclose(t1, 1):
					pass
				elif 0 < t1 < 1 and 0 < t2 < 1:
					param1 = i + t1
					param2 = j + i + 2 + t2
					#if param1 not in intersection_parameters and param2 not in intersection_parameters:  # TODO: this is a costly if statement
					print((param1,param2))
					intersection_parameters.append(i + t1)
					intersection_parameters.append(j + i + 2 + t2)
					intersection_points.append(p)
	# todo: we may not need to accumulate the points.. they will need to be recalculated again in the future...
	return intersection_points, intersection_parameters


def split_at_parameters(inp: LineString, params: List[float]):
	output: List[LineString] = []
	accumulator: LineString = [inp[0]]
	index = 0
	last_cut_param = 0
	for param in sorted(params):
		while param > index + 1:
			accumulator.append(inp[index+1])
			index += 1

		a = inp[index]
		b = inp[index + 1]
		# todo: if self_intersection could return a list of dictionaries,
		#  or if this function was combined with that function...
		#  we could eliminate the recalculation of the intersection point.
		#  the only problem would be the sorting algorithim required would be a bit sill
		cut_point = a + (b - a).scaled(param - index)
		accumulator.append(cut_point)
		output.append(accumulator)
		accumulator = [cut_point]
	
	index += 1
	
	while index < len(inp):
		accumulator.append(inp[index])
		index += 1
	
	output.append(accumulator)
	
	return output


def offset_linestring(inp: LineString, offset: float) -> LineString:
	positive_seg, negative_seg = offset_segments(inp, offset)
	positive = connect_offset_segments(positive_seg)
	negative = connect_offset_segments(negative_seg)


def plot_LineString(ps: LineString, index_label=False, **kwargs):
	plt.plot(*transpose_vector_list(ps), **kwargs)
	if index_label:
		for index, item in enumerate(ps):
			plt.annotate(index, item)


# ls = [
# 	Vector2(0, 3),
# 	Vector2(0.9, 0),
# 	Vector2(1.5, 2),
# 	Vector2(2.1, 0),
# 	Vector2(3, 3),
# ]
# lso = offset_linestring(ls, 0.2)
# print(lso)
#

ls = [
	Vector2(7.38, 14.47),
	Vector2(21.37, 1.99),
	Vector2(23.64, 23.35),
	Vector2(15.32, 18.43),
	Vector2(31.01, 11.82),
	Vector2(0.58, 0.86)
]

ls = [
	Vector2(43.30, 19.69),
	Vector2(59.60, 4.99),
	Vector2(68.69, 25.83),
	Vector2(50.78, 30.38),
	Vector2(59.60, 4.99),
	Vector2(73.50, 3.11)
]

int_points, int_params = self_intersection(ls)
print(int_params)
print(int_points)
plot_LineString(ls, True, color="r")

# fig, ax = plt.subplots()
plt.scatter(*transpose_vector_list(int_points))
for point, param in zip(int_points, grouper(int_params, 2)):
	plt.annotate(f'   {param[0]:.2f},{param[1]:.2f}', point)

split_lines = split_at_parameters(ls, int_params)
print(split_lines)
plot_LineString(split_lines[2], False, color="g")

plt.show()
