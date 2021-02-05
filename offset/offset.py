import itertools
import math
from typing import List
from typing import Optional
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


def solve_intersection(a: Vector2, b: Vector2, c: Vector2, d: Vector2) -> Optional[Tuple[Vector2, float, float]]:
	# computes the intersection between two line segments; a to b, and c to d
	
	ab = b - a
	cd = d - c
	
	# The intersection of segments is expressed as a parametric equation
	# where t1 and t2 are unknown scalars
	# note that a real intersection can only happen when 0<=t1<=1 and 0<=t2<=1,
	# a + ab·t1 = c + cd·t2
	
	# This can be rearranged as follows:
	# ab·t1 - cd·t2 = c - a
	
	# by collecting the scalars t1 and -t2 into the column vector T,
	# and by collecting the vectors ab and cd into matrix M:
	# we get the matrix form:
	# [ab_x  cd_x][ t1] = [ac_x]
	# [ab_y  cd_y][-t2]   [ac_y]
	# or
	# M·t=ac
	
	# the determinant of the matrix M is the inverse of the cross product of ab and cd.
	# 1/(ab×cd)
	# Therefore if ab×cd=0 the determinant is undefined and the matrix cannot be inverted
	# This means the lines are
	#   a) parallel and
	#   b) possibly collinear
	
	# pre-multiplying both sides by the inverted 2x2 matrix we get:
	# [ t1] = 1/(ab×cd)·[ cd_y  -cd_x][ac_x]
	# [-t2]             [-ab_y   ab_x][ac_y]
	# or
	# t = M⁻¹·ac
	
	# multiplied out
	# [ t1] = 1/(ab_x·cd_y - ab_y·cd_x)·[ cd_y·ac_x - cd_x·ac_y]
	# [-t2]                             [-ab_y·ac_x + ab_x·ac_y]
	
	# since it is neat to write cross products in python code, observe that the above is equivalent to:
	# [ t1] = [ ac×cd / ab×cd ]
	# [-t2] = [ ab×ac / ab×cd ]
	
	ab_cross_cd = ab.cross(cd)
	
	if ab_cross_cd == 0:
		
		# vectors are not linearly independent; ab and cd are parallel
		# segments are collinear if ac is parallel to ab
		# ac ∥ ab
		# or more conveniently if ac is perpendicular to the left normal of ab
		# ac ⟂ (ab⟂)
		# the left normal of ab = [-ab_y]
		#                         [ ab_x]
		# dot product of perpendicular vectors is zero:
		# if ab.left.dot(ac) == 0:
		# 	# segments are collinear
		# 	# TODO: we can compute the range over which t1 and t2 produce an overlap, if any, here. Doesnt seem to be needed for now.
		# else:
		# 	# segments are parallel
		# 	return None
		
		return None
	else:
		ac = c - a
		t1 = ac.cross(cd) / ab_cross_cd
		t2 = -ab.cross(ac) / ab_cross_cd
		return a + ab.scaled(t1), t1, t2


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
	if len(inp) == 1:
		return [*inp[0]]
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
			p, t_ab, t_cd = solve_intersection(a, b, c, d)
			
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


def self_intersection(inp: LineString) -> List[float]:
	intersection_parameters = []
	for i, (a, b) in enumerate(pairwise(inp)):
		for j, (c, d) in enumerate(pairwise(inp[i + 2:])):
			print(f"{i},{i + 1} against {j + i + 2},{j + i + 1 + 2}")
			intersection_result = solve_intersection(a, b, c, d)
			if intersection_result is not None:
				# TODO: collect p to prevent recalculation?
				p, t1, t2 = intersection_result
				if 0 <= t1 <= 1 and 0 <= t2 <= 1:
					param_1 = i + t1
					param_2 = j + i + 2 + t2
					print((param_1, param_2))
					intersection_parameters.append(param_1)
					intersection_parameters.append(param_2)
	last_item = float("inf")
	output = []
	for item in sorted(intersection_parameters):
		if not math.isclose(last_item, item):
			output.append(item)
			last_item = item
	
	return output


def intersection(target: LineString, tool: LineString) -> List[float]:
	"""will return a list of parameters for the target where the tool intersects the target."""
	intersection_parameters = []
	for i, (a, b) in enumerate(pairwise(target)):
		for j, (c, d) in enumerate(pairwise(tool)):
			print(f"{i},{i + 1} against {j + i + 2},{j + i + 1 + 2}")
			intersection_result = solve_intersection(a, b, c, d)
			if intersection_result is not None:
				# TODO: collect p to prevent recalculation?
				p, t1, t2 = intersection_result
				if 0 <= t1 <= 1 and 0 <= t2 <= 1:
					param_1 = i + t1
					
					print(param_1)
					intersection_parameters.append(param_1)
	
	last_item = float("inf")
	output = []
	for item in sorted(intersection_parameters):
		if not math.isclose(last_item, item):
			output.append(item)
			last_item = item
	
	return output


def split_at_parameters(inp: LineString, params: List[float]):
	output: List[LineString] = []
	accumulator: LineString = [inp[0]]
	index = 0
	last_cut_param = 0
	for param in params:
		
		while param > index + 1:
			accumulator.append(inp[index + 1])
			index += 1
		
		a = inp[index]
		b = inp[index + 1]
		
		cut_point = a + (b - a).scaled(param - index)
		accumulator.append(cut_point)
		output.append(accumulator)
		if math.isclose(param - index, 1):
			accumulator = []
		else:
			accumulator = [cut_point]
	
	index += 1
	
	while index < len(inp):
		accumulator.append(inp[index])
		index += 1
	
	output.append(accumulator)
	
	return output


def params_to_points(inp: LineString, params: List[float]):
	output = []
	for param in params:
		a = inp[math.floor(param)]
		b = inp[math.ceil(param)]
		output.append(a + (b - a).scaled(param % 1))
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


non_intersecting_parallel = [
	Vector2(60.67, 44.89),
	Vector2(76.35, 44.89),
	Vector2(76.35, 33.17),
	Vector2(88.64, 33.17),
	Vector2(88.64, 44.89),
	Vector2(103.75, 44.89),
	Vector2(103.75, 60.20),
	Vector2(83.53, 60.20),
	Vector2(83.53, 23.53)
]

mid_touch_vertex = [
	Vector2(34.87, 61.50),
	Vector2(27.54, 67.34),
	Vector2(46.87, 61.90),
	Vector2(31.75, 58.12),
	Vector2(24.76, 73.43),
	Vector2(33.45, 79.85)
]

corner_touch_corner = [
	Vector2(37.26, 89.36),
	Vector2(24.76, 103.29),
	Vector2(46.87, 91.76),
	Vector2(31.75, 87.98),
	Vector2(24.76, 103.29),
	Vector2(33.45, 109.71)
]

ls = [
	Vector2(43.30, 19.69),
	Vector2(59.60, 4.99),
	Vector2(68.69, 25.83),
	Vector2(50.78, 30.38),
	Vector2(59.60, 4.99),
	Vector2(73.50, 3.11)
]

intersectors = [
	[
		Vector2(45.37, 4.61),
		Vector2(53.85, 19.50),
		Vector2(56.33, 19.70),
		Vector2(61.70, 5.03)
	],
	[
		Vector2(49.71, 27.97),
		Vector2(52.61, 11.23),
		Vector2(55.50, 11.85),
		Vector2(62.32, 26.94)
	]
]

squig = [
	Vector2(56.74, 112.31),
	Vector2(56.12, 109),
	Vector2(56.74, 106.52),
	Vector2(59.43, 104.04),
	Vector2(64.60, 105.90),
	Vector2(68.73, 110.65),
	Vector2(73.90, 112.31),
	Vector2(79.69, 108.79),
	Vector2(82.58, 101.97),
	Vector2(80.93, 92.05),
	Vector2(73.48, 82.34),
	Vector2(70.80, 69.31),
	Vector2(78.03, 58.98),
	Vector2(94.57, 64.77),
	Vector2(99.12, 75.10),
	Vector2(90.02, 78.62),
	Vector2(88.37, 76.13),
	Vector2(90.64, 69.93)
]





plot_LineString(squig, True, color="r")
offsets = [connect_offset_segments(item) for item in offset_segments(squig, 3)]
for offset_c in offsets:
	plot_LineString(offset_c, True, color="g")

# int_params = self_intersection(offsets[0])
# print(int_params)
# int_points = params_to_points(intersectors[0], int_params)
#
# # fig, ax = plt.subplots()
# plt.scatter(*transpose_vector_list(int_points))
# for point, param in zip(int_points, grouper(int_params, 2)):
# 	plt.annotate(f'   {param[0]:.2f},{param[1]:.2f}', point)

# split_lines = split_at_parameters(corner_touch_corner, int_params)
# print(split_lines)
# for index, item in enumerate(split_lines):
# 	plot_LineString(connect_offset_segments(offset_segments(item, 0.1 + index / 2)[0]), False, color="g")
plt.show()