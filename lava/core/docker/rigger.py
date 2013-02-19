from pymel.core.runtime import SmoothBindSkinOptions
from PyQt4.QtCore import pyqtSlot
from PyQt4.QtCore import QEvent
from PyQt4.QtCore import QObject
from PyQt4.QtCore import QPoint
from PyQt4.QtGui import QCheckBox
from PyQt4.QtGui import QMenu
from PyQt4.QtGui import QSlider
from PyQt4.QtGui import QSpinBox

from lava.core.general import result
from lava.core.rigging.character import base
from lava.core.rigging.character import polyped
from lava.core.ui.base import UIDocker


class Rigger(UIDocker):
	
	def __init__(self, *args, **kwargs):
		super(Rigger, self).__init__(*args, **kwargs)
		self.bottomWidget.hide()
	
	#========================================#
	# Bone Radius Settings
	#========================================#
	
	def brSB_round(self, sb):
		return round(sb.value() * 20) / 20
	
	def brSlider_valueChanged(self, sb, i):
		sb.setValue(i / 20.0)
	
	def brSB_editingFinished(self, sb, slider):
		f = self.brSB_round(sb)
		sb.setValue(f)
		slider.setValue(int(f * 20))
	
	@pyqtSlot(int)
	def on_longBoneRadiusSlider_valueChanged(self, i):
		self.brSlider_valueChanged(self.longBoneRadiusSpinBox, i)
	
	@pyqtSlot()
	def on_longBoneRadiusSpinBox_editingFinished(self):
		self.brSB_editingFinished(self.longBoneRadiusSpinBox,
			self.longBoneRadiusSlider)
	
	@pyqtSlot(int)
	def on_shortBoneRadiusSlider_valueChanged(self, i):
		self.brSlider_valueChanged(self.shortBoneRadiusSpinBox, i)
	
	@pyqtSlot()
	def on_shortBoneRadiusSpinBox_editingFinished(self):
		self.brSB_editingFinished(self.shortBoneRadiusSpinBox,
			self.shortBoneRadiusSlider)
	
	@pyqtSlot(int)
	def on_tipBoneRadiusSlider_valueChanged(self, i):
		self.brSlider_valueChanged(self.tipBoneRadiusSpinBox, i)
	
	@pyqtSlot()
	def on_tipBoneRadiusSpinBox_editingFinished(self):
		self.brSB_editingFinished(self.tipBoneRadiusSpinBox,
			self.tipBoneRadiusSlider)
	
	@pyqtSlot()
	def on_testBoneRadiusButton_clicked(self):
		base.Character( \
			lbr=self.longBoneRadiusSpinBox.value(),
			sbr=self.shortBoneRadiusSpinBox.value(),
			tbr=self.tipBoneRadiusSpinBox.value(),
			tebr=True)
	
	#========================================#
	# Joint Naming
	#========================================#
	
	
	
	#========================================#
	# Stretchy Settings
	#========================================#
	
	def stretchyEnableDisableAll(self, b):
		for cb in self.stretchyPage.findChildren(QCheckBox):
			cb.setChecked(b)
		for slider in self.stretchyPage.findChildren(QSlider):
			slider.setEnabled(b)
		for sb in self.stretchyPage.findChildren(QSpinBox):
			sb.setEnabled(b)
	
	@pyqtSlot()
	def on_stretchyEnableAllButton_clicked(self):
		self.stretchyEnableDisableAll(True)
	
	@pyqtSlot()
	def on_stretchyDisableAllButton_clicked(self):
		self.stretchyEnableDisableAll(False)
	
	#========================================#
	# Generate Rig Button
	#========================================#
	
	@pyqtSlot()
	def on_smoothBindOptionsButton_clicked(self):
		SmoothBindSkinOptions()
	
	@pyqtSlot()
	def on_rigAndSmoothBindButton_clicked(self):
		self.bottomWidget.show()
		self.topWidget.setEnabled(False)
		
		character = polyped.Polyped( \
			vbr=True,
			lbr=self.longBoneRadiusSpinBox.value(),
			sbr=self.shortBoneRadiusSpinBox.value(),
			tbr=self.tipBoneRadiusSpinBox.value(),
			#===========================
			djl=str(self.driveJointLineEdit.text()),
			bjl=str(self.bindJointLineEdit.text()),
			nhpat=str(self.nhpatLineEdit.text()),
			#===========================
			ss=self.stretchySpineCheckBox.isChecked(),
			sn=self.stretchyNeckCheckBox.isChecked(),
			st=self.stretchyTailCheckBox.isChecked(),
			sap=self.stretchyAppendageCheckBox.isChecked(),
			sa=self.stretchyShoulderCheckBox.isChecked(),
			sl=self.stretchyHipCheckBox.isChecked(),
			eshj=self.insertShoulderJointsSpinBox.value(),
			efj=self.insertForearmJointsSpinBox.value(),
			ehj=self.insertHipJointsSpinBox.value(),
			eknj=self.insertKneeJointsSpinBox.value())
		
		self.topWidget.setEnabled(True)
		self.bottomWidget.hide()
