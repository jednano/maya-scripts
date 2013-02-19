#=================================================
# external imports
#=================================================

from pymel.core import nodetypes as nt # Joint, Transform
from pymel.core.animation import cluster
from pymel.core.animation import joint
from pymel.core.general import align
from pymel.core.general import delete
from pymel.core.general import ls
from pymel.core.general import MeshEdge
from pymel.core.general import MeshVertex
from pymel.core.general import parent
from pymel.core.general import select
from pymel.core.general import spaceLocator
from pymel.core.general import xform
from pymel.core.modeling import circle
from pymel.core.modeling import curve
from pymel.core.runtime import DeleteHistory
from pymel.core.system import convertUnit

#=================================================
# internal imports
#=================================================

from .general import snap
from .general import uniquify

#=================================================
# classes
#=================================================

class Shape(list):
	"""
	Base class for all shapes.
	"""
	
	def __init__(self, **kwargs):
		"""
		Merge all shape nodes under a single transform and trash any
		left-over (empty) transforms.
		"""
		
		shapes = [n for n in self if not isinstance(n, nt.Joint)]
		empty_transforms = [s.getParent() for s in shapes if not \
			[sib for sib in s.getSiblings() if sib not in self]]
		self._transform = nt.Transform()
		parent(self, self._transform, relative=True, shape=True)
		#if empty_transforms:
		#	print('empty transforms:', empty_transforms)
		#	delete(empty_transforms)
		select(self)
		DeleteHistory()
		
		snap_to = kwargs.pop('st', kwargs.pop('snap_to', None))
		if snap_to:
			snap(self._transform, snap_to)
	
	def get_transform(self):
		return self._transform

class Null(Shape):
	def __new__(cls, **kwargs):
		s = super(Locator, cls).__new__(cls, **kwargs)
		s.append(nt.Transform(name=Null.__name__.lower() + '#', empty=True))
		return s

class Locator(Shape):
	def __new__(cls, **kwargs):
		s = super(Locator, cls).__new__(cls, **kwargs)
		s.append(spaceLocator(name=Locator.__name__[:3].lower() + '#').getShape())
		return s

class Plus(Shape):
	def __new__(cls, **kwargs):
		s = super(Plus, cls).__new__(cls, **kwargs)
		s.append(curve(name=Plus.__name__.lower() + '#', degree=1,
			point=convert_points([ \
				[0, 1, 0], [0, -1, 0], [0, 0, 0], [-1, 0, 0], [1, 0, 0], [0, 0, 0], [0, 0, 1],
				[0, 0, -1]])).getShape())
		return s

class Circle(Shape):
    def __new__(cls, **kwargs):
        s = super(Circle, cls).__new__(cls, **kwargs)
        s.append(circle(name=Circle.__name__.lower() + '#',
			normal=(0, 1, 0))[0].getShape())
        return s

class Circles(Shape):
	def __new__(cls, **kwargs):
		s = super(Circles, cls).__new__(cls, **kwargs)
		s.append(circle(name=Circles.__name__.lower() + '#',
			normal=(0, 1, 0))[0].getShape())
		s.append(circle(name=Circles.__name__.lower() + '#', radius=0.5,
			normal=(0, 1, 0))[0].getShape())
		return s

class Square(Shape):
	def __new__(cls, **kwargs):
		s = super(Square, cls).__new__(cls, **kwargs)
		s.append(curve(name=Square.__name__.lower() + '#', degree=1,
			p=convert_points([ \
				[-1, 0, 1], [1, 0, 1], [1, 0, -1], [-1, 0, -1], [-1, 0, 1]])).getShape())
		return s

class Cube(Shape):
	def __new__(cls, **kwargs):
		s = super(Cube, cls).__new__(cls, **kwargs)
		s.append(curve(name=Cube.__name__.lower() + '#', degree=1,
			point=convert_points([ \
				[-0.5, 0.5, 0.5], [0.5, 0.5, 0.5], [0.5, 0.5, -0.5], [-0.5, 0.5, -0.5],
				[-0.5, 0.5, 0.5], [-0.5, -0.5, 0.5], [-0.5, -0.5, -0.5], [0.5, -0.5, -0.5],
				[0.5, -0.5, 0.5], [-0.5, -0.5, 0.5], [0.5, -0.5, 0.5], [0.5, 0.5, 0.5],
				[0.5, 0.5, -0.5], [0.5, -0.5, -0.5], [-0.5, -0.5, -0.5],
				[-0.5, 0.5, -0.5]])).getShape())
		return s

class Sphere(Shape):
	def __new__(cls, **kwargs):
		s = super(Sphere, cls).__new__(cls, **kwargs)
		s.append(curve(name=Sphere.__name__.lower() + '#', degree=1,
			point=convert_points([ \
				[0, 3, 0], [0, 2, -2], [0, 0, -3], [0, -2, -2], [0, -3, 0], [0, -2, 2],
				[0, 0, 3], [0, 2, 2], [0, 3, 0], [2, 2, 0], [3, 0, 0], [2, -2, 0], [0, -3, 0],
				[-2, -2, 0], [-3, 0, 0], [-2, 2, 0], [0, 3, 0]])))
		return s

class Arrow(Shape):
	def __new__(cls, **kwargs):
		s = super(Arrow, cls).__new__(cls, **kwargs)
		s.append(curve(name=Arrow.__name__.lower() + '#', degree=1,
			point=convert_points([ \
				[0, 0.6724194, 0.4034517], [0, 0, 0.4034517], [0, 0, 0.6724194],
				[0, -0.4034517, 0], [0, 0, -0.6724194], [0, 0, -0.4034517],
				[0, 0.6724194, -0.4034517], [0, 0.6724194, 0.4034517]])).getShape())
		return s

class Cross(Shape):
	def __new__(cls, **kwargs):
		s = super(Cross, cls).__new__(cls, **kwargs)
		s.append(curve(name=Cross.__name__.lower() + '#', degree=1,
			point=convert_points([ \
				[1, 0, -1], [2, 0, -1], [2, 0, 1], [1, 0, 1], [1, 0, 2], [-1, 0, 2],
				[-1, 0, 1], [-2, 0, 1], [-2, 0, -1], [-1, 0, -1], [-1, 0, -2], [1, 0, -2],
				[1, 0, -1]])).getShape())
		return s

class Orient(Shape):
	def __new__(cls, **kwargs):
		s = super(Orient, cls).__new__(cls, **kwargs)
		s.append(curve(name=Orient.__name__.lower() + '#', degree=3,
			point=convert_points([ \
				[0.0959835, 0.604001, -0.0987656], [0.500783, 0.500458, -0.0987656],
				[0.751175, 0.327886, -0.0987656], [0.751175, 0.327886, -0.0987656],
				[0.751175, 0.327886, -0.336638], [0.751175, 0.327886, -0.336638],
				[1.001567, 0, 0], [1.001567, 0, 0], [0.751175, 0.327886, 0.336638],
				[0.751175, 0.327886, 0.336638], [0.751175, 0.327886, 0.0987656],
				[0.751175, 0.327886, 0.0987656], [0.500783, 0.500458, 0.0987656],
				[0.0959835, 0.604001, 0.0987656], [0.0959835, 0.604001, 0.0987656],
				[0.0959835, 0.500458, 0.500783], [0.0959835, 0.327886, 0.751175],
				[0.0959835, 0.327886, 0.751175], [0.336638, 0.327886, 0.751175],
				[0.336638, 0.327886, 0.751175], [0, 0, 1.001567], [0, 0, 1.001567],
				[-0.336638, 0.327886, 0.751175], [-0.336638, 0.327886, 0.751175],
				[-0.0959835, 0.327886, 0.751175], [-0.0959835, 0.327886, 0.751175],
				[-0.0959835, 0.500458, 0.500783], [-0.0959835, 0.604001, 0.0987656],
				[-0.0959835, 0.604001, 0.0987656], [-0.500783, 0.500458, 0.0987656],
				[-0.751175, 0.327886, 0.0987656], [-0.751175, 0.327886, 0.0987656],
				[-0.751175, 0.327886, 0.336638], [-0.751175, 0.327886, 0.336638],
				[-1.001567, 0, 0], [-1.001567, 0, 0], [-0.751175, 0.327886, -0.336638],
				[-0.751175, 0.327886, -0.336638], [-0.751175, 0.327886, -0.0987656],
				[-0.751175, 0.327886, -0.0987656], [-0.500783, 0.500458, -0.0987656],
				[-0.0959835, 0.604001, -0.0987656], [-0.0959835, 0.604001, -0.0987656],
				[-0.0959835, 0.500458, -0.500783], [-0.0959835, 0.327886, -0.751175],
				[-0.0959835, 0.327886, -0.751175], [-0.336638, 0.327886, -0.751175],
				[-0.336638, 0.327886, -0.751175], [0, 0, -1.001567], [0, 0, -1.001567],
				[0.336638, 0.327886, -0.751175], [0.336638, 0.327886, -0.751175],
				[0.0959835, 0.327886, -0.751175], [0.0959835, 0.327886, -0.751175],
				[0.0959835, 0.500458, -0.500783],
				[0.0959835, 0.604001, -0.0987656]])).getShape())
		return s

class Bulb(Shape):
	def __new__(cls, **kwargs):
		s = super(Bulb, cls).__new__(cls, **kwargs)
		s.append(curve(name=Bulb.__name__.lower(), degree=3,
			point=convert_points([ \
				[-0.139471, -0.798108, 0], [-0.139471, -0.798108, 0],
				[-0.139471, -0.798108, 0], [-0.299681, -0.672294, 0],
				[-0.299681, -0.672294, 0], [-0.299681, -0.672294, 0],
				[-0.121956, -0.578864, 0], [-0.121956, -0.578864, 0],
				[-0.121956, -0.578864, 0], [-0.285304, -0.51952, 0],
				[-0.285304, -0.51952, 0], [-0.0744873, -0.442806, 0],
				[-0.0744873, -0.442806, 0], [-0.287769, -0.373086, 0],
				[-0.287769, -0.373086, 0], [-0.100386, -0.296549, 0],
				[-0.100386, -0.296549, 0], [-0.264344, -0.205725, 0],
				[-0.264344, -0.205725, 0], [-0.262544, -0.0993145, 0],
				[-0.262544, -0.0993145, 0], [-0.167051, -0.0613459, 0],
				[-0.167051, -0.0613459, 0], [-0.167051, -0.0613459, 0],
				[-0.166024, 0.0163458, 0], [-0.157394, 0.232092, 0],
				[-0.367902, 0.680843, 0], [-0.96336, 1.224522, 0],
				[-1.006509, 1.992577, 0], [-0.316123, 2.613925, 0],
				[0.561786, 2.548479, 0], [1.094888, 2.001207, 0],
				[1.051638, 1.166965, 0], [0.436419, 0.66543, 0],
				[0.13283, 0.232092, 0], [0.15009, 0.0163458, 0],
				[0.15073, -0.046628, 0], [0.15073, -0.046628, 0],
				[0.270326, -0.0955798, 0], [0.270326, -0.0955798, 0],
				[0.267815, -0.208156, 0], [0.267815, -0.208156, 0],
				[0.0884224, -0.291145, 0], [0.0884224, -0.291145, 0],
				[0.292477, -0.366091, 0], [0.292477, -0.366091, 0],
				[0.0946189, -0.439723, 0], [0.0946189, -0.439723, 0],
				[0.306664, -0.508968, 0], [0.306664, -0.508968, 0],
				[0.112488, -0.57513, 0], [0.112488, -0.57513, 0],
				[0.323789, -0.674644, 0], [0.323789, -0.674644, 0],
				[0.152097, -0.794645, 0], [0.152097, -0.794645, 0],
				[0.152097, -0.794645, 0], [0.106716, -0.907397, 0],
				[0.0103741, -1.003739, 0], [-0.0919896, -0.907397, 0],
				[-0.139471, -0.798108, 0], [-0.139471, -0.798108, 0]])))
		return s

class Joint(Shape):
	def __new__(cls, **kwargs):
		s = super(Custom, cls).__new__(cls, **kwargs)
		s.append(joint())
		return s

class Custom(Shape):
	def __new__(cls, **kwargs):
		s = super(Custom, cls).__new__(cls, **kwargs)
		transforms = ls(selection=True, transforms=True)
		for t in transforms:
			shapes = t.getShapes()
			if shapes:
				s.extend(shapes)
			elif isinstance(t, nt.Joint):
				s.append(t)
				xform(t, translation=(0, 0, 0))
			else:
				# Delete empty transforms.
				delete(t)
		s.extend([n for n in ls(selection=True, shapes=True) if n not in s])
		return s

#=================================================
# functions
#=================================================

def convert_points(points):
	for i, p in enumerate(points):
		for j, p2 in enumerate(p):
			points[i][j] = float(convertUnit(p2, fromUnit='cm'))
	return points

def create_shapes(shape_cls=Plus, snaps=[], **kwargs):
	if not snaps:
		snaps = ls(selection=True, transforms=True)
	if snaps:
		return [shape_cls(snap_to=s) for s in snaps]
	verts = [v for v in ls(selection=True, flatten=True) if isinstance(v, MeshVertex)]
	[verts.extend(e.connectedVertices()) for e in ls(selection=True, flatten=True) \
		if isinstance(e, MeshEdge)]
	if verts:
		verts = uniquify(verts)
		select(verts, replace=True)
		transform = cluster()[1]
		shape = shape_cls(snap_to=transform)
		delete(transform)
		return [shape]
	return [shape_cls()]