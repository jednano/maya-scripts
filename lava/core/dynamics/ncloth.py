#=================================================
# external imports
#=================================================

import os
from pymel.core import mel
from pymel.core.general import getAttr
from pymel.core.general import ls
from pymel.core.general import rename
from pymel.core.general import select
from pymel.core.general import selected
from pymel.core.general import setAttr
from pymel.core.nodetypes import NCloth
from pymel.core.nodetypes import PolyBase
from pymel.core.nodetypes import Transform
from pymel.core.runtime import nClothCreate
from pymel.core.system import convertUnit
from pymel.core.windows import promptBox
import pymel.util as _util

#=================================================
# classes
#=================================================

class ScaledNCloth(NCloth):
	"""
	Creates nCloth and fixes the space scale to behave appropriately for
	the selected object.
	"""
	
	def __new__(cls, transform, **kwargs):
		if not isinstance(transform, Transform):
			transform = transform.getParent()
		select(transform, replace=True)
		nClothCreate()
		shape = selected()[0]
		nc_xform = shape.getParent()
		rename(nc_xform, transform.namespace() + 'snCloth' + \
			_util.capitalize(transform.name().split(':')[-1]))
		shape.__class__ = cls
		return shape
		
	def __init__(self, transform, **kwargs):
		"""
		Flags:
			- real_world_length: rwl				(unicode, default:None)
				The longest length of the object in the real world (e.g. '11in' for
				a normal 8.5x11" sheet of paper.
			
			- shared_transforms: st				(list, default:None)
				Any number of transforms that share the same nucleus.
		"""
		
		super(ScaledNCloth, self).__init__()
		self.transform = transform
		self.nucleus = ls(mel.getActiveNucleusNode(0, 1))[0]
		self.shared_transforms = kwargs.pop('st',
			kwargs.pop('shared_transforms', None))
		self.real_world_length = kwargs.pop('rwl',
			kwargs.pop('real_world_length', None))
	
	@property
	def real_world_length(self):
		"""
		nCloth simulates in meters; so, convert and return the space scale
		in the scene's working units.
		"""
		self._real_world_length = convertUnit(float( \
			self.nucleus.attr('spaceScale').get()), fromUnit='m')
		return self._real_world_length
	
	@real_world_length.setter
	def real_world_length(self, value=None):
		"""
		Sets the real world length according to the scene's working units and
		also sets the nCloth nucleus space scale to compensate.
		"""
		if value:
			# Run a conversion formula to adjust for any variance between the
			# size of the object in the real world vs. the size of the object in Maya.
			max_length, bbs = 0, self.shared_transforms \
				and [st.getBoundingBox() for st in self.shared_transforms] \
				or [self.transform.getBoundingBox()]
			for bb in bbs:
				max_length = max(max_length, bb.width(), bb.height(), bb.depth())
			self._real_world_length = float(convertUnit(value))
			ss = self._real_world_length / max_length
			ss = float(convertUnit(ss, toUnit='m')[:-1])
		else:
			# No value was passed. Assume the units are accurate to the scene's
			# working units.
			self._real_world_length = float(convertUnit(1, toUnit='m')[:-1])
			ss = self._real_world_length
		self.nucleus.attr('spaceScale').set(ss)

#=================================================
# functions
#=================================================

def create_scaled_ncloth_auto(**kwargs):
	transforms = selected(transforms=True)
	kwargs['shared_transforms'] = transforms
	result = [ScaledNCloth(s, **kwargs) for s in selected() \
		if not isinstance(s, PolyBase)]
	select(result)
	return result

def create_scaled_ncloth_prompt(msg=None):
	lines = []
	if msg:
		lines.append(msg)
	rwl = promptBox('Create Scaled nCloth',
		os.linesep.join(lines +[ \
		'What is the real-world length of the longest object in',
		'your selection (e.g. 7ft, 2in, etc. or scene)?']),
		'Create Scaled nCloth', 'Cancel')
	if rwl:
		if rwl.lower() == 'scene':
			return create_scaled_ncloth_auto()
		try:
			rwl = float(convertUnit(rwl))
		except RuntimeError:
			return create_scaled_ncloth_prompt( \
				msg='Conversion error: invalid units. Please try again.')
		return create_scaled_ncloth_auto(rwl=rwl)