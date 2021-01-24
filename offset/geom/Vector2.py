from __future__ import annotations
from math import sqrt
from typing import List


class Vector2:
	"""immutable Vector2

	In previous code I used a mutable Vector2 class which meant that updating properties like this; Layer.position_mm.x = 10.
	Meant that it was hard for the Layer class to know when its own position was changed.

	By using immutable Vector2 we are forced to do something like; Layer.position_mm += iVector2(10,0)
	This way the Layer class can use getter and setter methods to know when its position has changed.
	"""
	
	def __init__(self, x: float, y: float):
		self._x = float(x)
		self._y = float(y)
	
	@property
	def x(self):
		return self._x
	
	@property
	def y(self):
		return self._y
	
	def with_x(self, new_x: float):
		return Vector2(new_x, self._y)
	
	def with_y(self, new_y: float):
		return Vector2(self._x, new_y)
	
	def scaled(self, scale_factor: float):
		return Vector2(self._x * scale_factor, self._y * scale_factor)
	
	def len_squared(self):
		return self._x * self._x + self._y * self._y
	
	def len(self):
		return sqrt(self._x * self._x + self._y * self._y)
	
	@property
	def unit(self):
		ll = self.len()
		if ll == 0:
			# what the user wants to happen here depends on the application; Return None? Return some default unit vector?
			# Here we simply hot-potato the problem by returning a zero length vector
			# most likely the user will experience an error downstream in their code
			return Vector2(0, 0)
		return self / ll
	
	def dot(self, other: Vector2) -> float:
		return self._x * other.x + self._y * other.y
	
	def cross(self, other: Vector2) -> float:
		"""returns the scalar magnitude of the cross product assuming the z component of both 2d vectors are both zero"""
		return self.x * other.y - self.y * other.x
	
	@property
	def left(self):
		return Vector2(-self.y, self.x)
	
	def __repr__(self):
		return f"Vector2({self._x:.2f}, {self._y:.2f})"
	
	def __str__(self):
		"""suitable for SVG"""
		return f"{self._x:.5f}".rstrip("0").rstrip(".") + f" {self._y:.5f}".rstrip("0").rstrip(".")
	
	def __add__(self, other):
		if type(other) is float or type(other) is int:
			return Vector2(self.x + other, self.y + other)
		return Vector2(self.x + other.x, self.y + other.y)
	
	def __sub__(self, other: Vector2) -> Vector2:
		return Vector2(self._x - other.x, self._y - other.y)
	
	def __mul__(self, other: float):
		return Vector2(self._x * other, self._y * other)
	
	def __truediv__(self, other: float):
		return Vector2(self._x / other, self._y / other)
	
	def __neg__(self):
		return Vector2(-self._x, -self._y)
	
	def __pos__(self):
		return self
