#=================================================
# external imports
#=================================================

import re
import sys
from pymel.core.animation import insertJoint
from pymel.core.general import ls
from pymel.core.general import makeIdentity
from pymel.core.general import parent
from pymel.core import nodetypes as nt
from pymel.core.general import rename
from pymel.util import LazyLoadModule

#=================================================
# internal imports
#=================================================

from ...general import error
from ...general import flatten
from ...general import function_on_hierarchy
from ...general import NameHelper

#=================================================
# classes
#=================================================

class Character(object):
	
	_front = 'z'
	_bone_radius = lambda self, x: x / 10
	_vary_bone_radius = False
	_short_bone_length = sys.float_info.max
	_long_bone_length = 0
	_short_bone_radius = 0.5
	_long_bone_radius = 2.0
	_tip_bone_radius = 0.25
	drive_joints = {}
	bind_joints = {}
	
	@property
	def front(self):
		"""Defines the front axis of a character."""
		return self._front
	
	@front.setter
	def front(self, value):
		if value not in list('xz'):
			raise NotImplementedError("Only supports front-axes 'x' and 'z'.")
		self._front = value
	
	def __init__(self, root_cls=None, *args, **kwargs):
		"""
		Flags:
			- bone_radius: br				(int, default:1)
				Sets all joints' bone radii. This flag only works if -vary_bone_radius
				is False.
			
			- nhpat								(string, default:<nt>_<s><ss>_<n><ns>)
				Establishes a naming convention where 'nt' is the node type
				(drive or bind joint), 's' in the side, 'ss' is the side sequence,
				'n' is the name and 'ns' is the name sequence.
			
			- long_bone_radius: lbr		(float, default:2.0)
				Sets -vary_bone_radius' maximum range. This flag only works if
				-vary_bone_radius is True.
			
			- short_bone_radius: sbr		(float, default:0.5)
				Sets -vary_bone_radius' minimum range. This flag only works if
				-vary_bone_radius is True.
			
			- test_bone_radius: tebr		(bool, default:False)
				Tests the bone radius settings without continuing the
				rigging process.
			
			- tip_bone_radius: tbr			(float, default:0.25)
				Sets all tip joints' bone radii. This flag only works if -vary_bone_radius
				is True.
		"""
		
		# Find the joint-chain's root joint.
		joints = ls(selection=True, type='joint')
		roots = []
		for j in joints:
			while True:
				pj = j.listRelatives(parent=True, type='joint')
				if pj:
					j = pj[0]
				elif j not in roots:
					roots.append(j)
					break
				
		assert len(roots), 'Selection requires at least one joint.'
		
		# Vary bone radius.
		self._short_bone_radius = kwargs.pop('sbr',
			kwargs.pop('short_bone_radius', self._short_bone_radius))
		self._long_bone_radius = kwargs.pop('lbr',
			kwargs.pop('long_bone_radius', self._long_bone_radius))
		self._tip_bone_radius = kwargs.pop('tbr',
			kwargs.pop('tip_bone_radius', self._tip_bone_radius))
		for r in roots:
			self.set_bone_length_range(r)
			self.set_bone_radii(r)
		test_bone_radius = kwargs.pop('tebr',
			kwargs.pop('test_bone_radius', False))
		if test_bone_radius: return
		
		if not issubclass(root_cls, CharacterJoint):
			raise TypeError("%s class must be a subclass of %s." \
				% (root_cls.__name__, CharacterJoint))
		
		# NameHelper segments establish a naming convention for this character.
		self.name_helper = kwargs.pop('nh', kwargs.pop('name_helper', None))
		if not self.name_helper:
			self.name_helper = NameHelper()
		
		# In order to distinguish the character's left and right sides, first we need to
		# define the character's front axis.
		self.front = kwargs.pop('front', 'z')
		
		for jdict in [self.drive_joints, self.bind_joints]:
			jdict[root_cls] = []
		for i, root in enumerate(roots):
			# Clean-up the joint chain by freezing rotate and scale
			makeIdentity(root, apply=True, rotate=True, scale=True)
			
			# Recurse through the entire joint chain, assigning the appropriate
			# CharacterJoint class to each joint.
			self.drive_joints[root_cls].append(root_cls(root, self,
				jdict=self.drive_joints, *args, **kwargs))
			self.bind_joints[root_cls].append(root_cls(root.duplicate()[0],
				self, jdict=self.bind_joints, *args, **kwargs))
		
		# Recursion added joints to the lists backwards, so reverse it to
		# keep the joints in a top-down relationship.
		for jdict in [self.drive_joints, self.bind_joints]:
			[jdict[cls].reverse() for cls in jdict.keys()]
		
		# Change the name of the joints to something they would not use
		# to prevent any naming conflicts in the future.
		roots.extend(self.bind_joints[root_cls])
		function_on_hierarchy(roots, rename, 'FooJoint#')
		
		# Name joints.
		for cls, dj_list in self.drive_joints.items():
			for i, dj in enumerate(dj_list):
				while True:
					self.rename_part(dj)
					if len(ls(dj.nodeName())) == 1:
						bj = self.bind_joints[cls][i]
						dj.bind_joint = bj
						bj.drive_joint = dj
						bj.side_sequence = dj.side_sequence
						self.rename_part(bj)
						break
					dj.side_sequence += 1
	
	def insert_bind_joints(self, cls, amount):
		inserted_joints = []
		for bj in self.bind_joints[cls]:
			nj = bj.getChildren()[0] # next joint
			d = nj.attr('t').get() / (amount + 1)
			parent(nj, world=True)
			ij = bj
			for i in range(amount):
				ns = ij.name_sequence + 1
				ij = ls(insertJoint(ij))[0]
				ij.attr('t').set(d)
				ij.__class__ = cls
				ij.name_sequence = ns
				self.name_helper.rename(ij, jt=bj.jtype, s=bj.side,
					ss=bj.side_sequence, n=bj.__name__, ns=ns)
				inserted_joints.append(ij)
			parent(nj, ij)
			self.set_bone_radii(bj)
		self.bind_joints[cls].extend(inserted_joints)
	
	def rename_part(self, character_part):
		return self.name_helper.rename(character_part,
			jt=character_part.jtype,
			s=character_part.side,
			ss=character_part.side_sequence,
			n=character_part.__name__,
			ns=character_part.name_sequence)
	
	def bone_length(self, joint):
		if joint.numChildren():
			first_child = joint.getChildren()[0]
			return joint.getTranslation(space='world') \
				.distanceTo(first_child.getTranslation(space='world'))
		return 0
	
	def set_bone_radii(self, character_joint, bone_radius=None):
		bl, br = self.bone_length(character_joint), bone_radius
		if br:
			new_radius = hasattr(br, '__call__') and br(bl) or br
		else:
			sbr, sbl = self._short_bone_radius, self._short_bone_length
			lbr, lbl = self._long_bone_radius, self._long_bone_length
			new_radius = sbr + (bl - sbl) / (lbl - sbl) * (lbr - sbr)
		child_joints = character_joint.getChildren()
		character_joint.attr('radius').set(child_joints and new_radius \
			or self._tip_bone_radius)
		[self.set_bone_radii(cj, bone_radius) for cj in child_joints]
	
	def set_bone_length_range(self, character_joint):
		for cj in character_joint.getChildren():
			d = character_joint.getTranslation().distanceTo(cj.getTranslation())
			if d < self._short_bone_length:
				self._short_bone_length = d
			if d > self._long_bone_length:
				self._long_bone_length = d
			self.set_bone_length_range(cj)

class CharacterJoint(nt.Joint):
	"""
	A joint with additional information, defining its relationship to a character.
	"""
	
	label_sides = ('Center', 'Left', 'Right', 'None')
	label_types = (None, 'Root', 'Hip', 'Knee', 'Foot', 'Toe', 'Spine', 'Neck', 'Head',
		'Collar', 'Shoulder', 'Elbow', 'Hand', 'Finger', 'Thumb', 'PropA', 'PropB', 'PropC',
		'Other', 'IndexFinger', 'MiddleFinger', 'RingFinger', 'PinkyFinger',
		'ExtraFinger', 'BigToe', 'IndexToe', 'MiddleToe', 'RingToe', 'PinkyToe',
		'ExtraToe')
	_tol = 0.0001  # tolerance
	
	@property
	def color(self):
		return self.attr('overrideColor').get()
	
	@color.setter
	def color(self, value):
		if value is None:
			self.attr('overrideEnabled').set(False)
		else:
			self.attr('overrideEnabled').set(True)
			self.attr('overrideColor').set(value)
	
	@property
	def side(self):
		return self.label_sides[self._label_joint \
			and self.attr('side').get() or self._side][0]
	
	@side.setter
	def side(self, value):
		if value == 'auto':
			pos = self.getTranslation(space='world')
			if self.character.front == 'z':
				value = pos.x > self._tol and 'L' or pos.x < -self._tol and 'R' or 'C'
			else:   #x
				value = pos.z < -self._tol and 'L' or pos.z > self._tol and 'R' or 'C'
		else:
			value = value is None and 'None' or value.capitalize()
		self._side = dict((s[0], i) for i, s in enumerate(self.label_sides))[value[0]]
		if self._label_joint:
			self.attr('side').set(self._side)
		if self._colorize_joint:
			# Center:Purple(30), Left:Blue(15), Right:Red(4), None:Green(26).
			self.color = (30, 15, 4, 26)[self._side]
	
	@property
	def type(self):
		label_type = self.label_types[self.attr('type').get()]
		return label_type == 'Other' and self.attr('otherType').get() \
			or label_type
	
	@type.setter
	def type(self, value):
		label_types_dict = dict((v, i) for i, v in enumerate(self.label_types))
		try:
			type_index = label_types_dict[value]
			self._type = value
		except KeyError:
			type_index = label_types_dict['Other']
			self.attr('otherType').set(self.__name__)
			self._type = self.__name__
		if self._label_joint:
			self.attr('type').set(type_index)
	
	def __new__(cls, joint, *args, **kwargs):
		joint.__class__ = cls
		return joint
	
	def __init__(self, rules, joint, character, *args, **kwargs):
		"""
		Flags:
			- bind_joint_label: bjl			(string, default:BJ)
				Sets the joint type label for bind joints.
			
			- colorize_joint: cj				(bool, default:True)
				If set, colorizes joint based on side.
			
			- drive_joint_label: djl			(string, default:DJ)
				Sets the joint type label for drive joints.
			
			- jdict: jd							(dict, default:character.drive_joints)
				Sets the joint type dictionary (drive or bind).
			
			- label_joint: lj					(bool, default:True)
				If set, labels joint based on side and type.
			
			- name								(unicode, default:self.__class__.__name__)
				Overrides the CharacterJoint object's __name__, from which the
				naming convention is based.
			
			- name_sequence: ns			(int, default:1)
				Defines the joint's positional sequence, incrementing as new joints
				inherit the same name as their parent. This is used in the naming
				convention.
			
			- orient_joint: oj					(bool, default:True)
				If set, orients joint based on side and type.
			
			- side: s								(unicode, default:'auto')
				Specifies the joint labeling side. 'auto' means that the joint's position
				in world space will be evaluated with respect to the front of the character
				in order to determine the side on which the joint is placed.
		"""
		
		self.character = character
		self.jdict = kwargs.pop('jd',
			kwargs.pop('jdict', character.drive_joints))
		kwargs['jd'] = self.jdict
		djl = kwargs.pop('djl', kwargs.pop('drive_joint_label',
			character.name_helper.ntypes['driveJoint']))
		bjl = kwargs.pop('bjl', kwargs.pop('bind_joint_label',
			character.name_helper.ntypes['bindJoint']))
		kwargs['djl'], kwargs['bjl'] = djl, bjl
		self.jtype = self.jdict == character.drive_joints and djl or bjl
		self.__name__ = kwargs.pop('n', kwargs.pop('name', None))
		if self.__name__:
			kwargs['name'] = self.__name__
		else:
			self.__name__ = self.__class__.__name__
			if self.__name__.startswith('HIK'):
				self.__name__ = self.__name__[3:]
		self.name_sequence = kwargs.pop('ns',
			kwargs.pop('name_sequence', 1))
						
		# Look-ahead and assign the appropriate classes to each child joint.
		nc = self.numChildren()
		if not nc:
			self.name_sequence = 'Tip'
		else:
			clist = [x for x in flatten(self.get_class_list(self, rules))]
			clist = clist[:nc] + [clist[-1]] * (nc - len(clist))
			for i, j in enumerate(self.getChildren()):
				cls = clist[i]
				if cls not in self.jdict:
					self.jdict[cls] = []
				self.jdict[cls].append(cls(j, character,
					name_sequence=(self.__class__ == cls) and \
					self.name_sequence + 1 or 1, *args, **kwargs))
		
		# Label joint.
		self._label_joint = kwargs.pop('lj', kwargs.pop('label_joint', True))
		if self._label_joint:
			self._colorize_joint = kwargs.pop('cj', kwargs.pop('colorize_joint', True))
			self.side = kwargs.pop('s', kwargs.pop('side', 'auto'))
			self.side_sequence = 1
			self.type = self.__name__
		
		# Orient joint.
		"""self._orient_joint = kwargs.pop('oj', kwargs.pop('orient_joint', False))
		if self._orient_joint:
			self.orientJoint(self.side == 'Left' and 'xyz' or '-xyz')
			self.secondaryAxisOrient('yup')"""
		
		# Set default rotation order.
		#self.setRotationOrder('XYZ', True)
		
		# Set default degrees of freedom.
		# TODO: self.setDegreesOfFreedom(True, True, True) # Not working
		"""for axis in 'XYZ':
			self.attr('jointType' + axis).set(True)"""
	
	def lookahead(self, joint, exp):
		if not eval(exp % joint.numChildren()):
			return False
		for j in joint.getChildren():
			if not self.lookahead(j, exp):
				return False
		return True
	
	def get_class_list(self, joint, rules):
		nc = joint.numChildren()
		clist = None
		for k, v in rules.items():
			if k == nc or (isinstance(k, str) and \
				(k.startswith('%d') and eval(k % nc) or \
				k.startswith('~') and self.lookahead(joint, k[1:]))):
					clist = v
					break
		if clist is None:
			assert '*' in rules, '%d joints not supported for %s.' % \
				(nc, self.__name__)
			clist = [rules['*']]
		if not hasattr(clist, '__iter__'):
			return clist
		else:
			return [isinstance(x, dict) and \
				self.get_class_list(joint.getChildren()[i], x) or x \
				for i, x in enumerate(clist)]
		
class DeadEnd(CharacterJoint):
	def __init__(self, *args, **kwargs):
		super(DeadEnd, self).__init__({1:[self.__class__]}, *args, **kwargs)