#=================================================
# external imports
#=================================================

from .base import Character
from .base import CharacterJoint
from .base import DeadEnd

#=================================================
# classes
#=================================================

class Other(DeadEnd): pass

class OtherProp(Character):
	def __init__(self, *args, **kwargs):
		super(OtherProp, self).__init__(Other, side=None, *args, **kwargs)