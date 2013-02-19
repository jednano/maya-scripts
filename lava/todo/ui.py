from inspect import getfile

from PyQt4 import uic
from PyQt4.QtGui import QDialog


class UIBase(object):

   def __new__(cls, *args, **kwargs):
       uiClass, baseClass = uic.loadUiType(cls.getUIPath().abspath())
       cls.__bases__ += (uiClass,)
       result = super(UIBase, cls).__new__(cls, *args, **kwargs)
       result.uiClass, result.baseClass = uiClass, baseClass
       return result

   def __init__(self, *args, **kwargs):
       self.__name__ = self.__class__.__name__
       self.baseClass.__init__(self)
       self.setupUi(self)
       self.open()

   @classmethod
   def getUIPath(cls):
       """This method is intended to be overridden in cases when the UI files are located
       in a special place that deviates from the modulePath/Ui/SubclassName.ui convention.
       """
       pass


class UIDialogBase(UIBase, QDialog): pass