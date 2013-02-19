#=================================================
# external imports
#=================================================

from pymel.core import nodetypes as nt
from pymel.core.animation import parentConstraint
from pymel.core.general import parent

#=================================================
# internal imports
#=================================================

from .base import Character
from .base import CharacterJoint
from .base import DeadEnd
from .base import NameHelper

#=================================================
# classes
#=================================================

class Root(CharacterJoint):
	def __init__(self, *args, **kwargs):
		super(Root, self).__init__({1:[{1:Spine, '*':Pelvis}],
			2:[Spine, Pelvis]}, *args, **kwargs)

class Spine(CharacterJoint):
	def __init__(self, *args, **kwargs):
		hip_or_collar = {1:[{1:[{1:[{2:Collar, '*':Hip}], '*':Hip}], '*':Hip}], '*':Hip}
		super(Spine, self).__init__({1:[Spine], 2:[Spine, Appendage],
			3:[{'~%d<3':Neck, '*':Spine}, hip_or_collar, hip_or_collar]},
			*args, **kwargs)

class Appendage(DeadEnd): pass

class Neck(CharacterJoint):
	def __init__(self, *args, **kwargs):
		super(Neck, self).__init__({1:[{1:[{0:Head, 1:Neck}],
			2:[Neck, Appendage]}]}, *args, **kwargs)

class Head(CharacterJoint):
	def __init__(self, *args, **kwargs):
		super(Head, self).__init__({1:[Head], 2:[Head, Jaw]},
			*args, **kwargs)

class Jaw(DeadEnd): pass

class Collar(CharacterJoint):
	def __init__(self, *args, **kwargs):
		p = self.getParent()
		parent(self, world=True)
		self.orientJoint('none')
		parent(self, p)
		super(Collar, self).__init__({1:[Shoulder]}, *args, **kwargs)

class Shoulder(CharacterJoint):
	def __init__(self, *args, **kwargs):
		super(Shoulder, self).__init__({1:[Elbow]}, *args, **kwargs)

class Elbow(CharacterJoint):
	def __init__(self, *args, **kwargs):
		super(Elbow, self).__init__({1:[Hand]}, *args, **kwargs)

class Hand(CharacterJoint):
	def __init__(self, *args, **kwargs):
		super(Hand, self).__init__({1:[Hand], 2:[Hand, Thumb],
			'*':[MiddleFinger, IndexFinger, RingFinger, PinkyFinger, ExtraFinger]},
			*args, **kwargs)

class IndexFinger(DeadEnd): pass
class MiddleFinger(DeadEnd): pass
class RingFinger(DeadEnd): pass
class PinkyFinger(DeadEnd): pass
class ExtraFinger(DeadEnd): pass
class Thumb(DeadEnd): pass

class Pelvis(CharacterJoint):
	def __init__(self, *args, **kwargs):
		super(Pelvis, self).__init__({1:[Tail], 2:[Hip, Hip],
			3:[{'~%d<2':Tail, '*':Spine}, Hip, Hip],
			4:[Spine, Tail, Hip, Hip]}, *args, **kwargs)

class Tail(DeadEnd): pass

class Hip(CharacterJoint):
	def __init__(self, *args, **kwargs):
		super(Hip, self).__init__({1:[Knee]}, *args, **kwargs)

class Knee(CharacterJoint):
	def __init__(self, *args, **kwargs):
		super(Knee, self).__init__({1:[Foot]}, *args, **kwargs)

class Ankle(CharacterJoint):
	def __init__(self, *args, **kwargs):
		super(Ankle, self).__init__({1:[Foot], 2:[Foot, BigToe]},
			*args, **kwargs)

class Foot(CharacterJoint):
	def __init__(self, *args, **kwargs):
		super(Foot, self).__init__({1:[Foot], 2:[Foot, BigToe],
			'*':[IndexToe, MiddleToe, RingToe, PinkyToe, ExtraToe]},
			*args, **kwargs)

class IndexToe(DeadEnd): pass
class MiddleToe(DeadEnd): pass
class RingToe(DeadEnd): pass
class PinkyToe(DeadEnd): pass
class ExtraToe(DeadEnd): pass
class BigToe(DeadEnd): pass

class Polyped(Character):
	def __init__(self, *args, **kwargs):
		"""
		Flags:
			- stretchy_spine: ss					(bool, default:True)
				If set, creates a stretchy spine system for the character.
			
			- stretchy_neck: sn					(bool, default:True)
				If set, creates a stretchy neck system for the character.
			
			- stretchy_tail: st					(bool, default:True)
				If set, creates a stretchy tail system for the character.
			
			- stretchy_appendage: sap		(bool, default:True)
				If set, creates a stretchy appendage systems for any
				appendages on the character.
			
			- stretchy_arm: sa					(bool, default:True)
				If set, creates a stretchy arm system for the character.
			
			- stretchy_leg: sl						(bool, default:True)
				If set, creates a stretchy leg system for the character.
			
			- extra_shoulder_joints: eshj	(bool, default:True)
				If set, creates a stretchy arm system for the character.
			
			- extra_forearm_joints: efj		(bool, default:True)
				If set, creates a stretchy arm system for the character.
			
			- extra_hip_joints: ehj				(bool, default:True)
				If set, creates a stretchy arm system for the character.
			
			- extra_knee_joints: eknj			(bool, default:True)
				If set, creates a stretchy arm system for the character.
		"""
		
		#======================================#
		# Stretchy Settings
		#======================================#
		
		stretchy_spine = kwargs.pop('ss',
			kwargs.pop('stretchy_spine', False))
		stretchy_neck = kwargs.pop('sn',
			kwargs.pop('stretchy_neck', False))
		stretchy_tail = kwargs.pop('st',
			kwargs.pop('stretchy_tail', False))
		stretchy_appendage = kwargs.pop('sap',
			kwargs.pop('stretchy_appendage', False))
		stretchy_arm = kwargs.pop('sa',
			kwargs.pop('stretchy_arm', False))
		stretchy_leg = kwargs.pop('sl',
			kwargs.pop('stretchy_leg', False))
		
		super(Polyped, self).__init__(Root, *args, **kwargs)
		
		self.insert_bind_joints(Shoulder, kwargs.pop('ishj',
			kwargs.pop('insert_shoulder_joints', 0)))
		self.insert_bind_joints(Elbow, kwargs.pop('ifj',
			kwargs.pop('insert_forearm_joints', 3)))
		self.insert_bind_joints(Hip, kwargs.pop('ihj',
			kwargs.pop('insert_hip_joints', 0)))
		self.insert_bind_joints(Knee, kwargs.pop('iknj',
			kwargs.pop('insert_knee_joints', 0)))
		
		# Parent constraint each bind joint to the respective
		# drive joint.
		for cls, dj_list in self.drive_joints.items():
			for i, dj in enumerate(dj_list):
				pc = parentConstraint(dj, self.bind_joints[cls][i])
				pc.jtype = self.name_helper.jtypes[nt.ParentConstraint]
				pc.side = dj.side
				pc.side_sequence = dj.side_sequence
				pc.__name__ = dj.__name__
				pc.name_sequence = dj.name_sequence
				self.rename_part(pc)