import sys

from pymel.core.general import ls
from pymel.core import uitypes as ui
from PyQt4.QtCore import pyqtSlot
from PyQt4.QtCore import QString

from lava.core.ui.base import UIWidgetBase


_fileBrowser = None
class FileBrowser(UIWidgetBase):
	
	def __new__(cls):
		mod = sys.modules[FileBrowser.__module__]
		if mod._fileBrowser is None:
			self = mod._fileBrowser = super(FileBrowser, cls) \
					.__new__(cls)
			self.initialized = False
		return mod._fileBrowser
	
	def __init__(self):
		if not self.initialized:
			super(FileBrowser, self).__init__()
			self.initialized = True
	
	def on_textureName_changed(self):
		print('texture name changed!')
	
	@pyqtSlot(QString)
	def on_prefixCombo_currentIndexChanged(self, value):
		print('prefix changed to %s.' % value)
