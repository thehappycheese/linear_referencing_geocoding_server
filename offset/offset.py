import itertools
import math
from typing import List
from typing import Tuple

from .geom.Vector2 import Vector2
import matplotlib.pyplot as plt


def pairwise(iterable):
    """s -> (s0,s1), (s1,s2), (s2, s3), ..."""
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)

def clockwise(a: Vector2, b: Vector2, c: Vector2):
	return (b - a).left.dot(c - a)


def are_collinear(a: Vector2, b: Vector2, c: Vector2):
	# this relies on computing the slope... infinite for vertical lines.
	ab = b - a
	ac = c - a
	t = ac.x / ab.x
	return math.isclose(ab.y * t, ac.y)


def segments_are_collinear(a1: Vector2, a2: Vector2, b1: Vector2, b2: Vector2):
	a1a2 = a2 - a1
	a1b1 = b1 - a1
	a1b2 = b2 - a1
	t1 = a1b1.x / a1a2.x
	t2 = a1b2.x / a1a2.x
	return math.isclose(a1a2.y * t1, a1b1.y) and math.isclose(a1a2.y * t2, a1b2.y)


def segments_are_overlapping(a_origin: Vector2, a_velocity: Vector2, b_origin: Vector2, b_velocity: Vector2):
	
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


nPointString = List[Vector2]
nSegmentString = List[Tuple[Vector2, Vector2]]


def offset_segments(inp: nPointString, offset: float) -> Tuple[nSegmentString, nSegmentString]:
	segments_positive: nSegmentString = []
	segments_negative: nSegmentString = []
	for a, b in zip(inp, inp[1:]):
		offset_vector = (b - a).left.unit.scaled(offset)
		segments_positive.append((a + offset_vector, b + offset_vector))
		segments_negative.append((a - offset_vector, b - offset_vector))
	return segments_positive, segments_negative

def connect_offset_segments(inp:nSegmentString) -> nPointString:
	# Algorithim 1
	for (a, b), (c, d) in pairwise(inp):
		ab = b - a
		cd = d - c
		
		if segments_are_overlapping():  # TODO: cover case where offset curves are 'overlapping' simply use b as the endpoint (and discard d?)
			# Case 1
			untrimmed_step2.append(b)
		else:
			# Case 2
			
			p, t_ab, t_cd = solve_intersection(a, ab, c, cd)
			
			TIP_ab = 0 <= t_ab <= 1
			FIP_ab = not TIP_ab
			PFIP_ab = FIP_ab and t_ab > 0
			NFIP_ab = FIP_ab and t_ab < 0
			
			TIP_cd = 0 <= t_cd <= 1
			FIP_cd = not TIP_cd
			PFIP_cd = FIP_cd and t_cd > 0
			NFIP_cd = FIP_cd and t_cd < 0
			
			if TIP_ab and TIP_cd:
				# Case 2a
				untrimmed_step2.append(p)
			elif FIP_ab and FIP_cd:
				# Case 2b.
				if PFIP_ab:
					untrimmed_step2.append(p)
				else:
					untrimmed_step2.append(b)
					untrimmed_step2.append(c)
			else:
				# Case 2c. (either ab or cd
				untrimmed_step2.append(b)
				untrimmed_step2.append(c)
	
	untrimmed_step2.append(d)
	return untrimmed_step2
	


def offset_linestring(inp: nPointString, offset: float) -> List[Vector2]:
	untrimmed_step1_positive, untrimmed_step1_negative = offset_segments(inp, offset)
	untrimmed_step2: List[Vector2] = [untrimmed_step1_positive[0][0]]
	
	


ls = [
	Vector2(0, 3),
	Vector2(0.9, 0),
	Vector2(1.5, 2),
	Vector2(2.1, 0),
	Vector2(3, 3),
]
lso = offset_linestring(ls, 0.2)
print(lso)

plt.plot(*transpose_vector_list(ls), "r")
plt.plot(*transpose_vector_list(lso), "g")
plt.show()
