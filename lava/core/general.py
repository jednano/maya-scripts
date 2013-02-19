#=================================================
# external imports
#=================================================

from maya.OpenMaya import MGlobal
from pymel.core.animation import parentConstraint
from pymel.core.general import selected
from pymel.core.language import mel
import pymel.core.nodetypes as nt

#=================================================
# classes
#=================================================

class NameHelper(object):
	"""
	Helps establish a naming convention with the use of string formatting and regular
	expression matching and replacing.
	"""
	
	# TODO: Load the IkSpringSolver plugin
	# mod = LazyLoadModule('IkSpringSolver', globals())
	# sys.modules['IkSpringSolver'] = mod
	
	ntypes = { \
		nt.AimConstraint: 'AC',
		'bindJoint': 'BJ',
		'buffer': 'BUF',  # Same as NULL
		nt.Condition: 'CND',
		'control': 'CTRL',
		'controlJoint': 'JNT',
		nt.CurveInfo: 'CI',
		'distanceDimension': 'DD',
		'driveJoint': 'DJ',
		nt.IkEffector: 'EFF',
		nt.Follicle: 'FOL',
		nt.GeometryConstraint: 'GC',
		'group': 'GRP',
		nt.HairSystem: 'HS',
		'ikJoint': 'IKJ',
		nt.IkRPsolver: 'IKH',
		nt.IkSCsolver: 'IKH',
		nt.IkSplineSolver: 'IKH',
		#nt.IkSpringSolver: 'IKH',
		nt.Joint: 'JNT',
		nt.Locator: 'LOC',
		'module': 'MOD',
		nt.MultiplyDivide: 'MD',
		nt.NormalConstraint: 'NC',
		'null': 'NUL',
		nt.NurbsCurve: 'CRV',
		nt.OrientConstraint: 'OC',
		nt.ParentConstraint: 'PC',
		nt.PlusMinusAverage: 'PMA',
		nt.PointConstraint: 'XC',
		nt.PointOnPolyConstraint: 'POP',
		'poleVector': 'PV',
		nt.PoleVectorConstraint: 'PVC',
		'rotation': 'ROT',
		nt.SkinCluster: 'SC'
	}
	
	def __init__(self, *args, **kwargs):
		self.formats = None
		self.pattern = None
		self._segments = {}
		us = self.update_segment
		pat = re.split('\<(nt|s|ss|n|ns)\>',
			kwargs.pop('pat', '<nt>_<s><ss>_<n><ns>'))
		frags = dict( \
			nt=('s', '[A-Z]{2,4}'),
			s=('s', '[A-Z]'),
			ss=('d', '\d'),
			n=('s', '[A-Z][A-Za-z]*'),
			ns=(['02d','s'], '(\d{2}|Tip)'))
		for i in range(1, len(pat)-1, 2):
			key = pat[i]
			us(key, frags[key][0], frags[key][1], pat[i+1])
		del us, pat, frags
	
	def update_segment(self, key, fmt, pat, seg=''):
		order = len(self._segments)
		segment = {key: (order, fmt, pat, seg)}
		self._segments.update(segment)
		self.is_compiled = False
		self._pattern = None
		return segment
	
	def get_segment(self, key):
		return self._segments[key]
	
	def compile(self):
		"""Compiles the pattern, but also prepares the string formats."""
		if self.is_compiled:
			return self._pattern
		num_formats = 1
		segments = [None] * len(self._segments)
		for k, v in self._segments.items():
			i, fmt, pat, seg = v
			segments[i] = (k, fmt, pat, seg)
			# If any string formats are a list or a tuple then prepare the rename function
			# for multiple scenarios (e.g. '%02d' % 'Tip' fails, so then it would try the 2nd
			# scenario, which could be '%s' % 'Tip').
			if isinstance(fmt, list) or isinstance(fmt, tuple):
				if len(fmt) > num_formats:
					num_formats = len(fmt)
		self.pattern, self.formats = '', [''] * num_formats
		for k, fmt, pat, seg in segments:
			for i, sf in enumerate(self.formats):
				f = (isinstance(fmt, list) or isinstance(fmt, tuple)) and fmt[i] or fmt
				self.formats[i] += '%%(%s)%s%s' % (k, f, seg)
			self.pattern += '(?P<%s>%s)%s' % (k, pat, seg)
		self._pattern = re.compile(self.pattern)
		self.is_compiled = True
		return self._pattern
	
	def match(self, dag_node):
		"""
		Returns a match object that adheres to the supplied naming convention.
		"""
		self.compile()
		name = dag_node.nodeName()
		m = self._pattern.match(name)
		assert m, "Name '%s' does not match the required naming convention: %s." % \
			(name, self.pattern)
		return m
	
	def rename(self, dag_node, **kwargs):
		"""
		Returns a nicely-formatted name that adheres to the specified
		naming convention.
		"""
		self.compile()
		
		# Attempt each format until we find one that works.
		rename_to = None
		for f in self.formats:
			try:
				rename_to = f % kwargs
				break
			except TypeError:
				continue
		if not rename_to:
			raise TypeError('String format mismatch.')
		
		return rename(dag_node, rename_to)

#=================================================
# functions
#=================================================

def error(msg, showLineNumber=False):
	#return mel.error(msg, showLineNumber)
	return MGlobal.displayError(msg)

def warning(msg, showLineNumber=False):
	return mel.warning(msg, showLineNumber)

def info(msg):
	return MGlobal.displayInfo(msg)

def result(msg):
	return info('Result: ' + msg)

def flatten(nested):
	"""
	Recursive generator that flattens an arbitrary depth of a set of lists.
	"""
	try:
		# Don't iterate over string-like objects:
		try: nested + ''
		except TypeError: pass
		else: raise TypeError
		for sublist in nested:
			for element in flatten(sublist):
				yield element
	except TypeError:
		yield nested

def snap(*args, **kwargs):
	"""
	Snaps one or more source transforms to a target node's world
	position, rotation and (optionally) the scale as well.
	"""
	
	if not args: args = selected()
	target, sources = args[0], args[1:]
	
	kwargs['space'] = kwargs.pop('space', 'world')
	translate = kwargs.pop('t', kwargs.pop('translate', True))
	rotate = kwargs.pop('r', kwargs.pop('rotate', True))
	scale = kwargs.pop('s', kwargs.pop('scale', False))
	if translate:
		t = target.getTranslation(**kwargs)
		[s.setTranslation(t, **kwargs) for s in sources]
	if rotate:
		r = target.getRotation(**kwargs)
		[s.setRotation(r, **kwargs) for s in sources]
	if scale:
		s = target.getScale(**kwargs)
		[s.setScale(s, **kwargs) for s in sources]

def uniquify(seq): 
	"""
	Not order preserving. 
	"""
	
	keys = {} 
	for e in seq: 
		keys[e] = None 
	return keys.keys()

def function_on_hierarchy(dag_nodes, fn, *args, **kwargs):
	for dn in dag_nodes:
		fn(dn, *args, **kwargs)
		function_on_hierarchy(dn.getChildren(), fn, *args, **kwargs)