#=================================================
# external imports
#=================================================

from pymel.core.animation import orientConstraint
from pymel.core.general import addAttr
from pymel.core.general import ls
from pymel.core.general import select
from pymel.core.language import scriptJob
from pymel.core.nodetypes import IkHandle, IkRPsolver, Joint
from pymel.core.rendering import shadingNode
from pymel.core.system import scriptNode
from pymel.mayautils import executeDeferred

#=================================================
# internal imports
#=================================================

from ...core import shapes
from ..general import snap
from ...util.vectormath import nearest_point_on_line
from character.base import CharacterJoint

#=================================================
# classes
#=================================================

class RigControl(object):
	"""
	A control object consisting of one or more shapes, intended to
	control a transform in a rig.
	"""
	
	_buffer = None
	
	def __init__(self, driver=shapes.Plus, driven=None, **kwargs):
		
		# Driver
		if not isinstance(driver, shapes.Shape) and issubclass(driver, shapes.Shape):
			driver = driver()
		assert isinstance(driver, shapes.Shape), \
			("Parameter 'driver' must be an instance or subclass of %s." %
			 shapes.Shape.__name__)
		self._driver = driver
		self._transform = driver.get_transform()
		self._shapes = self._transform.getShapes()
		
		# Driven
		if not driven:
			driven = ls(selection=True, transforms=True)
			assert len(driven) == 1, "Parameter 'driven' requires exactly one transform."
			driven = driven[0]
		self._driven = driven
		
		# Face Axis
		face_x = kwargs.pop('fx', kwargs.pop('faceX', False))
		face_y = kwargs.pop('fy', kwargs.pop('faceY', False))
		face_z = kwargs.pop('fz', kwargs.pop('faceZ', False))
		face_sum = sum([face_x, face_y, face_z])
		if not face_sum:
			face_x = True
			face_sum = 1
		else:
			assert face_sum == 1, "Rig control can only face one axis."
		rotate(self._transform, [face_z and 90 or 0, 0, face_x and -90 or 0])
		select(self._transform)
		FreezeTransformations()
		
		# Constraints
		do_parent_constraint = kwargs.pop('pc', kwargs.pop('parentConstraint', False))
		do_point_constraint = kwargs.pop('xc', kwargs.pop('pointConstraint', False))
		do_orient_constraint = kwargs.pop('oc', kwargs.pop('orientConstraint', False))
		do_scale_constraint = kwargs.pop('sc', kwargs.pop('scaleConstraint', False))
		if do_parent_constraint or do_point_constraint or do_orient_constraint or \
			do_scale_constraint:
			self._buffer = Transform()
			snap(self._buffer, self._driven, scale=True)
			select(self._buffer)
			parent(self._transform, self._buffer)
			if do_parent_constraint:
				parentConstraint(self._transform, self._driven)
			else:
				if do_point_constraint:
					pointConstraint(self._transform, self._driven)
				if do_orient_constraint:
					orientConstraint(self._transform, self._driven)
			if do_scale_constraint:
				scaleConstraint(self._transform, self._driven)
		elif isinstance(self._driven, Joint):
			# Parent the drivers directly underneath the driven joint.
			parent(self._driver, self._driven, relative=True, shape=True)
			delete(self._transform)
			self._transform = self._driven
		elif isinstance(self._driven, IkHandle):
			self._buffer = self._transform
			self._transform = self._driven
			snap(self._ebuffer, self._transform)
			parent(self._transform, self._buffer)
			parent(self._driver, self._transform, relative=True, shape=True)
		else:
			# Parent the drivers underneath a new buffered transform.
			self._buffer = self._driven
			parent(self._transform, self._buffer)
			parent(self._buffer.getShapes(), self._transform, relative=True, shape=True)
			# Pop the shape nodes out and back in to reorder the driven shape(s) to
			# the top. This way, the Outliner icons for this transform will reflect the
			# appropriate first-child shape node.
			parent(self._driver, self._buffer, relative=True, shape=True)
			parent(self._driver, self._transform, relative=True, shape=True)
		if self._buffer:
			select(self._transform)
			ResetTransformations()
			for trs in 'trs':
				for xyz in 'xyz':
					self._buffer.attr(trs + xyz).lock()
		
		if isinstance(self._driven, IkHandle):
			self.__class__ = IkRigControl
			self.__init__()
	
	# Accessors
	def get_buffer(self):
		return self._buffer
	
	def get_transform(self):
		return self._transform
	
	def get_shapes(self):
		return self._shapes
	
	def get_driven(self):
		return self._driven

class IkRigControl(RigControl):
	def __init__(self):
		self._ik = self._driven

#=================================================
# functions
#=================================================

def create_fk_ik_mod(collar):
	# Duplicate the drive joint chain twice for both fk and ik.
	fk = dict(collar=collar.duplicate()[0])
	ik = dict(collar=collar.duplicate()[0])
	
	# Load a dictionary for both fk and ik, containing all of the
	# necessary joints for fk/ik setup.
	keys = ('collar', 'shoulder', 'elbow', 'wrist', 'hand')
	for i, key in enumerate(keys[1:]):
		fk[key] = fk[keys[i]].getChildren()[0]
		ik[key] = ik[keys[i]].getChildren()[0]
	
	
		
	

def calc_pv_loc(distance=10, **kwargs):
	hj = kwargs.pop('hj', kwargs.pop('hand_joint', None))
	if hj:
		joints = (hj.getParent(2), hj.getParent(), hj)
	else:
		ik = kwargs.pop('ik', kwargs.pop('ik_handle', None))
		joints = ik is None and \
			kwargs.pop('j', kwargs.pop('joints', selected())) or \
			ik.getJointList() + [ik.getEndEffector()]
	x, y, z = [j.getTranslation(space='world') for j in joints]
	np = nearest_point_on_line([x, z], y)
	delta = y - np
	return np + delta * (distance / sum(abs(delta)))

def create_fk_ik_sj(controls):
	"""
	Creates a separate script job for both the fk and ik controls so
	their FKIK Mode is always the same without creating a crashing
	loop.
	"""
	
	# Find out what the next script job number will be by creating
	# a new script job, only to trash it immediately afterwards.
	killjob = scriptJob(attributeAdded=['defaultLayer.foo',
		lambda:None])
	scriptJob(kill=killjob)
	
	killjob += 3
	for i, c in enumerate(controls):
		killjob -= 1
		scriptJob(runOnce=True, killWithScene=True,
			attributeChange=[c + '.FkIkMode',
				lambda c1=c, c2=controls[i-1], killjob=killjob: \
					fk_ik_switch(c1, c2, killjob)])

def create_fk_ik_sn(controls, **kwargs):
	
	fk, ik = get_fk_ik_joints(controls)
	
	# Add the FkIkMode attribute to both controls and identify
	# which control is the fk control and which is the ik control.
	for c in controls:
		addAttr(c, longName='FkIkMode', niceName='FKIK Mode',
			attributeType='enum', enumName='FK:IK', keyable=True,
			defaultValue=1)
	
	sn = scriptNode(scriptType=2, sourceType='python',
		beforeScript=';'.join(['import pymel.core.nodetypes as nt',
			'import %s as x' % __name__,
			"x.create_fk_ik_sj(%s)" % controls]),
		afterScript=';'.join(['import pymel.core.nodetypes as nt',
			"[c.attr('FkIkMode').delete() for c in %s]" % controls]),
		**kwargs)
	
	# Make the appropriate connections to toggle both visibility and
	# orient constraints.
	rev = shadingNode('reverse', asUtility=True)
	ik['ctrl'].attr('FkIkMode').connect(ik['ctrl'].attr('visibility'))
	fk['ctrl'].attr('FkIkMode').connect(rev.attr('inputX'))
	rev.attr('outputX').connect(fk['ctrl'].attr('visibility'))
	ik['ctrl'].attr('FkIkMode').connect(ik['sj'].attr('visibility'))
	fk['ctrl'].attr('FkIkMode').connect(rev.attr('inputY'))
	rev.attr('outputY').connect(fk['sj'].attr('visibility'))
	for jtype in ('shoulder', 'elbow', 'hand'):
		kwargs = jtype == 'elbow' and dict(skip=('x', 'z')) or {}
		oc = orientConstraint(ik[jtype], fk[jtype], **kwargs)
		ik['ctrl'].attr('FkIkMode').connect( \
			oc.attr(ik[jtype].nodeName() + 'W0'))
	
	create_fk_ik_sj(controls)

def create_rig_controls(shape=shapes.Plus, driven=[], **kwargs):
	if not driven:
		driven = ls(selection=True, transforms=True)
	assert driven, "Must supply one or more transforms to drive."
	assert len(driven) == len(ls(driven, transforms=True)), \
		"Rig controls can only drive transforms."
	rcs = [RigControl(shape, d, **kwargs) for d in driven]
	select([rc.get_transform() for rc in rcs])
	return rcs

def find_rp_ik(node):
	for c in node.getChildren():
		if isinstance(c, IkHandle) and isinstance(c.getSolver(), IkRPsolver):
			return c
		elif c.numChildren():
			return find_rp_ik(c)

def fk_ik_switch(sender, receiver, killjob):
	
	fk, ik = get_fk_ik_joints([sender, receiver])
	
	scriptJob(kill=killjob)
	ik_mode = sender.attr('FkIkMode').get()
	if ik_mode == receiver.attr('FkIkMode').get():
		# Attribute wasn't even changed.
		create_fk_ik_sj([sender, receiver])
		return
	
	if ik_mode:
		snap(sender, receiver)
		if ik['sj'] == ik['collar']:
			snap(fk['collar'], ik['collar'], translate=False)
		ik['pvc'] = ik['h'].attr('poleVectorX').connections()[0] \
			.attr('target[0].targetTranslate').connections()[0]
		ik['pvc'].setTranslation(calc_pv_loc(hand_joint=sender),
			space='world')
	else: # FK mode
		jtypes = fk['sj'] == fk['collar'] and ('collar',) or ()
		jtypes += ('shoulder', 'elbow', 'hand')
		[snap(ik[jtype], fk[jtype], translate=False) for jtype in jtypes]
	
	receiver.attr('FkIkMode').set(ik_mode)
	select(receiver)
	create_fk_ik_sj([sender, receiver])

def get_fk_ik_joints(controls):
	
	fk, ik = {}, {}
	
	# Add the FkIkMode attribute to both controls and identify
	# which control is the fk control and which is the ik control.
	for c in controls:
		rp_ik = find_rp_ik(c)
		if rp_ik:
			ik['ctrl'], ik['h'] = c, rp_ik
		else:
			fk['ctrl'] = c
	
	# Identify the joint chain for both fk and ik. Hand, elbow and
	# shoulder are used for code readability. It could just as well
	# be hip, knee and foot.
	for i, jtype in enumerate(('hand', 'elbow', 'shoulder', 'collar')):
		fk[jtype] = fk['ctrl'].getParent(i)
	ik['shoulder'], ik['elbow'] = ik['h'].getJointList()
	ik['collar'] = ik['shoulder'].getParent()
	ik['hand'] = ik['elbow'].getChildren()[0]
	if isinstance(fk['collar'], Joint) and CharacterJoint.label_types[ \
		fk['collar'].attr('type').get()] == 'Collar':
		fk['sj'] = fk['collar']
		ik['sj'] = ik['collar']
	else:
		fk['sj'] = fk['shoulder']
		ik['sj'] = ik['shoulder']
	
	return fk, ik