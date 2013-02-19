from pymel.core.animation import aimConstraint
from pymel.core.animation import orientConstraint
from pymel.core.datatypes import Vector
from pymel.core.general import delete
from pymel.core.general import duplicate
from pymel.core.general import group
from pymel.core.general import makeIdentity
from pymel.core.general import parent
from pymel.core.general import rename
from pymel.core.general import select
from pymel.core.general import selected
from pymel.core.general import toggle
from pymel.core.general import upAxis
from pymel.core.general import xform
from pymel.core.nodetypes import Joint
from pymel.core.runtime import ResetTransformations
from pymel.core.system import undoInfo
from PyQt4.QtCore import pyqtSlot

from lava.core.general import result
from lava.core.general import snap
from lava.core.ui.base import UIDocker


class JointHelper(UIDocker):
	
	def get_affected_joints(self):
		return self.get_affected_nodes(dagObjects=False,
			type='joint')
	
	# Section: Select/Buffer ========================
	
	@pyqtSlot()
	def on_selectButton_clicked(self):
		select(self.get_affected_joints())
	
	@pyqtSlot()
	def on_bufferButton_clicked(self):
		undoInfo(openChunk=True)
		for j in self.get_affected_joints():
			buf = group(empty=True, world=True,
				name='BUF_' + j.nodeName())
			p = j.getParent(1)
			if p: parent(buf, p)
			dupe = duplicate(j, renameChildren=True,
				returnRootsOnly=True)[0]
			snap(dupe, buf, space='object')
			delete(dupe)
			parent(j, buf)
		undoInfo(closeChunk=True)
	
	# Section: Orient Joints ========================
	
	def get_cross_dir(a, b, c):
		"""
		Returns the cross product of the directions
		b > a and b > c.
		"""
		a, b, c = [x.getRotatePivot(space='world') \
			for x in (a, b, c)]
		return (a - b).cross(c - b).normal()
	
	def aimAxisXYZRadio_clicked(self):
		if not self.upAxisNoneRadio.isChecked():
			self.worldUpWidget.setEnabled(True)
	
	@pyqtSlot(bool)
	def on_aimAxisXRadio_clicked(self, bool):
		self.aimAxisXYZRadio_clicked()
		if self.upAxisXRadio.isChecked():
			self.upAxisYRadio.setChecked(True)
	
	@pyqtSlot(bool)
	def on_aimAxisYRadio_clicked(self, bool):
		self.aimAxisXYZRadio_clicked()
		if self.upAxisYRadio.isChecked():
			self.upAxisZRadio.setChecked(True)
	
	@pyqtSlot(bool)
	def on_aimAxisZRadio_clicked(self, bool):
		self.aimAxisXYZRadio_clicked()
		if self.upAxisZRadio.isChecked():
			self.upAxisXRadio.setChecked(True)
	
	@pyqtSlot(bool)
	def on_upAxisXRadio_clicked(self, bool):
		if self.aimAxisXRadio.isChecked():
			self.aimAxisYRadio.setChecked(True)
	
	@pyqtSlot(bool)
	def on_upAxisYRadio_clicked(self, bool):
		if self.aimAxisYRadio.isChecked():
			self.aimAxisZRadio.setChecked(True)
	
	@pyqtSlot(bool)
	def on_upAxisZRadio_clicked(self, bool):
		if self.aimAxisZRadio.isChecked():
			self.aimAxisXRadio.setChecked(True)
	
	@pyqtSlot()
	def on_orientJointsButton_clicked(self):
		undoInfo(openChunk=True)
		sel = selected()
		
		kwargs = {}
		if self.zeroScaleOrientCB.isChecked():
			kwargs.update({'zeroScaleOrient': True})
		if self.aimAxisNoneRadio.isChecked():
			val = 'none'
		else:
			for i, radio in enumerate((self.aimAxisXRadio,
				self.aimAxisYRadio, self.aimAxisZRadio)):
				if radio.isChecked():
					xyz = 'xyz'
					if self.upAxisNoneRadio.isChecked():
						val = xyz[i:] + xyz[:i]
					else:
						val = str(radio.text()).lower()
						for up_radio in (self.upAxisXRadio,
							self.upAxisYRadio, self.upAxisZRadio):
							if up_radio.isChecked():
								val += str(up_radio.text()).lower()
								break
						for c in xyz:
							if c not in val:
								val += c
								break
						sao = self.worldUpYRadio.isChecked() and 'y' \
							or self.worldUpZRadio.isChecked() and 'z' \
							or upAxis(query=True, axis=True)
						sao += self.worldUpReverseCB.isChecked() \
							and 'down' or 'up'
						kwargs.update({'secondaryAxisOrient': sao})
					break
		
		reverse_aim = self.aimAxisReverseCB.isChecked() \
			and Vector([val[1] == c for c in 'xyz']) * 180 or None
		reverse_up = self.upAxisReverseCB.isChecked() \
			and Vector([val[0] == c for c in 'xyz']) * 180 or None
		
		for j in self.get_affected_joints():
			if j.numChildren():
				j.orientJoint(val, **kwargs)
			else:
				p = j.getParent()
				if p:
					delete(orientConstraint(p, j))
				else:
					self.freeze(j, jointOrient=True)
				if self.zeroScaleOrientCB.isChecked():
					j.zeroScaleOrient()
			if reverse_aim:
				self.tweak_joint_orientation(1, rotateAxis=reverse_aim)
			if reverse_up:
				self.tweak_joint_orientation(1, rotateAxis=reverse_up)
		
		select(sel)
		undoInfo(closeChunk=True)
	
	# Section: Reset/Freeze ========================
	
	@pyqtSlot()
	def on_resetButton_clicked(self):
		undoInfo(openChunk=True)
		skip_locked = self.skipRadio.isChecked()
		joints = self.get_affected_joints()
		for cb in (self.rotateCB, self.scaleCB):
			if not cb.isChecked(): continue
			rs = str(cb.text()[0]).lower()
			v = rs == 's' and 1 or 0
			for j in joints:
				for axis in 'xyz':
					a = j.attr(rs + axis)
					if a.isLocked():
						if skip_locked: continue
						a.unlock()
						a.set(v)
						a.lock()
					else:
						a.set(v)
		undoInfo(closeChunk=True)
	
	def freeze(self, node, **kwargs):
		
		sel = selected()
		
		kwargs['rotate'] = kwargs.pop('r', kwargs.pop('rotate', True))
		kwargs['scale'] = kwargs.pop('s', kwargs.pop('scale', True))
		skip_locked = kwargs.pop('skip_locked', True)
		
		# Unparent all the joint's children to prevent any locked
		# attribute errors.
		children = dict([(c, c.listRelatives(allParents=True)) \
			for c in node.getChildren(type=['transform', 'joint'])])
		[c.setParent(world=True) for c in children.keys()]
		
		# Unlock any locked rotate or scale attributes, save their
		# values for later and set them to zero for now, so they
		# aren't affected by the freeze.
		atts = {}
		for rs in ('rotate', 'scale'):
			if not kwargs[rs]: continue
			for axis in 'xyz':
				a = node.attr(rs[0] + axis)
				if a.isLocked():
					atts[a] = a.get()
					a.unlock()
					if skip_locked: a.set(0)
		
		# Perform the freeze.
		select(node)
		makeIdentity(apply=True, **kwargs)
		
		# Restore and lock any rotate or scale attributes that
		# were locked before.
		for a, v in atts.items():
			if skip_locked: a.set(v)
			a.lock()
		
		# Restore children to their original parents and delete any
		# automatically-generated parent buffers.
		for c, parents in children.items():
			p = c.getParent()
			c.setParent(parents)
			if p: delete(p)
		
		select(sel)
	
	@pyqtSlot()
	def on_freezeButton_clicked(self):
		undoInfo(openChunk=True)
		kwargs = dict( \
			rotate=self.rotateCB.isChecked(),
			scale=self.scaleCB.isChecked(),
			jointOrient=self.orientCB.isChecked(),
			skip_locked=self.skipRadio.isChecked())
		[self.freeze(j, **kwargs) for j in self.get_affected_joints()]
		undoInfo(closeChunk=False)
	
	# Section: Tweak ============================
	
	@pyqtSlot()
	def on_tweakZeroButton_clicked(self):
		self.tweakXDouble.setValue(0)
		self.tweakYDouble.setValue(0)
		self.tweakZDouble.setValue(0)
	
	def tweak_joint_orientation(self, mult, **kwargs):
		kwargs.update({'rotateAxis': kwargs.pop('ra',
			kwargs.pop('rotateAxis', Vector( \
			self.tweakXDouble.value(), self.tweakYDouble.value(),
			self.tweakZDouble.value()) * mult))})
		zso = self.zeroScaleOrientCB.isChecked()
		for j in self.get_affected_joints():
			xform(j, objectSpace=True, relative=True, **kwargs)
			if zso: j.zeroScaleOrient()
			self.freeze(j)
	
	@pyqtSlot()
	def on_tweakPlusButton_clicked(self):
		undoInfo(openChunk=True)
		self.tweak_joint_orientation(1)
		undoInfo(closeChunk=True)
	
	@pyqtSlot()
	def on_tweakMinusButton_clicked(self):
		undoInfo(openChunk=True)
		self.tweak_joint_orientation(-1)
		undoInfo(closeChunk=True)
	
	# Section: Axes, Labels and Handles buttons ===========
	
	@pyqtSlot()
	def on_axesShowButton_clicked(self):
		undoInfo(openChunk=True)
		sel = selected()
		select(self.get_affected_joints())
		toggle(localAxis=True, state=True)
		select(sel)
		undoInfo(closeChunk=True)
	
	@pyqtSlot()
	def on_axesHideButton_clicked(self):
		undoInfo(openChunk=True)
		sel = selected()
		select(self.get_affected_joints())
		toggle(localAxis=True, state=False)
		select(sel)
		undoInfo(closeChunk=True)
	
	@pyqtSlot()
	def on_axesToggleButton_clicked(self):
		undoInfo(openChunk=True)
		sel = selected()
		select(self.get_affected_joints())
		toggle(localAxis=True)
		select(sel)
		undoInfo(closeChunk=True)
	
	@pyqtSlot()
	def on_labelsShowButton_clicked(self):
		undoInfo(openChunk=True)
		for j in self.get_affected_joints():
			j.attr('drawLabel').set(1)
		undoInfo(closeChunk=True)
	
	@pyqtSlot()
	def on_labelsHideButton_clicked(self):
		undoInfo(openChunk=True)
		for j in self.get_affected_joints():
			j.attr('drawLabel').set(0)
		undoInfo(closeChunk=True)
	
	@pyqtSlot()
	def on_labelsToggleButton_clicked(self):
		undoInfo(openChunk=True)
		for j in self.get_affected_joints():
			j.attr('drawLabel').set(1 - j.attr('drawLabel').get())
		undoInfo(closeChunk=True)
	
	@pyqtSlot()
	def on_handlesShowButton_clicked(self):
		undoInfo(openChunk=True)
		sel = selected()
		select(self.get_affected_joints())
		toggle(selectHandle=True, state=True)
		select(sel)
		undoInfo(closeChunk=True)
	
	@pyqtSlot()
	def on_handlesHideButton_clicked(self):
		undoInfo(openChunk=True)
		sel = selected()
		select(self.get_affected_joints())
		toggle(selectHandle=True, state=False)
		select(sel)
		undoInfo(closeChunk=True)
	
	@pyqtSlot()
	def on_handlesToggleButton_clicked(self):
		undoInfo(openChunk=True)
		sel = selected()
		select(self.get_affected_joints())
		toggle(selectHandle=True)
		select(sel)
		undoInfo(closeChunk=True)
