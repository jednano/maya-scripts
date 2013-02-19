import os
import re
import sys

from maya import cmds as mc
from pymel.core.animation import bakeResults
from pymel.core.animation import parentConstraint
from pymel.core.animation import playbackOptions
from pymel.core.animation import setCurrentTime
from pymel.core.animation import skinPercent
from pymel.core.general import connectionInfo
from pymel.core.general import cycleCheck
from pymel.core.general import delete
from pymel.core.general import disconnectAttr
from pymel.core.general import listRelatives
from pymel.core.general import ls
from pymel.core.general import select
from pymel.core.general import selected
from pymel.core.language import mel
from pymel.core.modeling import polyEvaluate
from pymel.core.nodetypes import SkinCluster
from pymel.core.nodetypes import Transform
from pymel.core.runtime import ExportOptions
from pymel.core.runtime import ExportSelectionOptions
from pymel.core.system import exportAll
from pymel.core.system import exportSelected
from pymel.core.system import fileDialog2
from pymel.core.system import loadPlugin
from pymel.core.system import Path
from pymel.core.system import pluginInfo
from pymel.core.system import showHelp
from pymel.core.system import workspace
from pymel.core.windows import confirmDialog
from pymel.core.windows import getMainProgressBar
from PyQt4.QtCore import pyqtSlot
from PyQt4.QtCore import QString
from PyQt4.QtGui import QCheckBox
from xml.dom import minidom
from xml.etree.ElementTree import Comment
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import ElementTree
from xml.etree.ElementTree import SubElement
from xml.etree.ElementTree import tostring

from lava.core.general import error
from lava.core.general import info
from lava.core.general import result
from lava.core.ui.base import UIDocker


class Exporter(UIDocker):
	"""
	Exports individual files per frame and names them appropriately.
	"""
	
	def __init__(self, *args, **kwargs):
		super(Exporter, self).__init__(*args, **kwargs)
		self.name_pat = re.compile('(%s)')
		self.frame_pat = re.compile('(%[\d\.]*(?:f|d))')
		self.split_pat = re.compile('((?:%s|%[\d\.]*(?:d|f)))')
		self.run_showers = (self.progress, self.status)
		self.run_disablers = (self.reload, self.toolBox, self.exportOptions,
			self.exportButton)
		[o.hide() for o in self.run_showers]
		self.animation_widgets = ()
		for i in range(1, 3):
			self.animation_widgets += ((self.toolBox.widget(i),
				self.toolBox.itemText(i)),)
		self.main_progress = getMainProgressBar()
		self._aborted = False
		
		# Look at the selection to predict what kind of object the user is going
		# to export and auto-select it in the export type combo box.
		kwargs = dict(selection=True, dagObjects=True)
		jroots = len(dict(((j, None) for j in ls(type='joint', **kwargs))).keys())
		cams = len(ls(cameras=True, **kwargs))
		meshes, skins = ls(geometry=True, **kwargs), 0
		del_meshes = []
		for i, m in enumerate(meshes):
			if mel.findRelatedSkinCluster(m):
				skins += 1
				del_meshes.append(i)
		for i in del_meshes:
			del meshes[i]
		if not jroots and not cams and not meshes and not skins:
			comboIndex = 2  # Meshes as default
		else:
			comboIndex = sorted(((i, c) for i, c in enumerate( \
				(jroots, cams, meshes, skins))), key=lambda x: x[1])[-1][0]
		self.exportCombo.setCurrentIndex(comboIndex)
		self.setFromTimeSlider.click()
		self.fix_format()
	
	#===============================================
	# member functions
	#===============================================
	
	def export_skeleton(self):
		pass
	
	def export_camera(self):
		
		start, end = self.start.value(), self.end.value()
		path = Path(self.path.text())
		
		# Validate the selection.
		sel = ls(selection=True, dagObjects=True, cameras=True)
		if not ls(selection=True):
			return error('No cameras in selection.')
		
		# Associate the camera shapes with their parents.
		cams = dict((s, s.getParent()) for s in sel)
		
		# Pull-out only the attributes that are checked.
		shape_atts = []
		for cb in self.cameraChannelsLayout.findChildren(QCheckBox):
			if cb.isChecked():
				[shape_atts.extend(str(cb.property(n).toString()).split('|')) \
					for n in cb.dynamicPropertyNames() if n == 'shortName']
		cam_atts = (cb.objectName() for cb \
			in self.translation.findChildren(QCheckBox) if cb.isChecked())
		attributes = (shape_atts, cam_atts)
		
		# Enable any locked or non-keyable channels.
		for shape, cam in cams.items():
			for i, obj in enumerate((shape, cam)):
				for att in attributes[i]:
					obj.attr(att).set('locked', False)
					obj.attr(att).set('keyable', True)
		
		# Initialize the progress bar.
		lc = len(cams)
		self.progress_init(lc + lc * len([x for x in (self.createStandIn.isChecked(),
			self.oneFile.isChecked() and self.oneFilePerNode.isChecked) if x]))
		
		# Bake the keys to the camera shape.
		frame_range = self.animation.isChecked() and (start, end) or (start,)
		for shape, cam in cams.items():
			if self.aborted: return
			
			info('Baking keys to %s: %d-%d...' % \
				((shape,) + frame_range))
			bakeResults(shape, time=frame_range, simulation=True,
				attribute=shape_atts)
			info('%s keys %d-%d baked.' % ((shape,) + frame_range))
			
			self.progress_step()
		
		# Disable the cycle check warning.
		cycleCheck(evaluation=False)
		
		# Create a null stand-in for the camera and bake keys to it.
		#mel.source('channelBoxCommand.mel')
		if self.createStandIn.isChecked():
			for cam in cams.values():
				if self.aborted: return
				
				stand_in = Transform(name='standInNull')
				parentConstraint(cam, stand_in, name='nullParentConstraint')
				info('Baking keys to the stand-in null...')
				bakeResults(stand_in, time=frame_range, shape=True,
					simulation=True, attribute=cam_atts)
				info('Null keys baked.')
				
				# If the camera is a child, parent it to the world.
				if cam.firstParent2():
					cam.setParent(world=True)
				
				# Break existing connections between the rotate or translate
				# attributes.
				for att in cam_atts:
					if connectionInfo(cam, isExactDestination=True):
						disconnectAttr(connectionInfo(cam,
							getExactDestination=True))
						#mel.CBdeleteConnection(getExactDestination=True)
				
				# Constrain the camera to the null.
				parentConstraint(stand_in, cam, name='cameraParentConstraint')
				
				# Bake the camera translate/rotate keys.
				info('Baking keys to the camera...')
				bakeResults(cam, time=frame_range, disableImplicitControl=True,
					simulation=True, attribute=cam_atts)
				info('Transform keys baked.')
				
				self.progress_step()
				
		# Remove excess elements unless optimize has been disabled.
		if self.optimize.isChecked():
			info('Optimizing scene...')
			delete([s for s in ls(dagObjects=True) if s not in cams.keys() + \
				cams.values() + ls(selection=True, type='animCurve')])
		
		# Save-out the cameras.
		kwargs = dict(force=True, constructionHistory=False, channels=True,
			constraints=False, expressions=False, shader=False,
			type='mayaAscii')
		ext = str(self.formatExt.text())
		if self.oneFile.isChecked():
			if self.oneFilePerNode.isChecked():
				for cam in cams.values():
					if self.aborted: return
					select(cam)
					exportSelected(path / cam.name() + ext, **kwargs)
					self.progress_step()
			else:
				select(cams.values())
				exportSelected(path / 'camera' + ext, **kwargs)
		else:
			error('Not implemented yet. Coming soon...')
	
	def write_mesh(self, path, name, **kwargs):
		output_path = path / name
		self.status.setText('Exporting: ~/%s.' % name)
		if not self.copy_and_replace_all and output_path.exists():
			click_result = confirmDialog(title='Write File',
				message=os.linesep.join(( \
				'There is already a file with the same name at this location.',
				'What would you like to do?')),
				button=('Copy and Replace all', 'Cancel'),
				defaultButton='Copy and Replace all',
				cancelButton='Cancel', dismissString='Cancel')
			if click_result == 'Cancel':
				self.aborted = True
				return False
			else:
				self.copy_and_replace_all = True
		if self.copy_and_replace_all or not output_path.exists():
			# TODO: PyMEL's exportSelected(output_path, **kwargs),
			# but it keeps spitting out mtl files, regardless of settings.
			#from pymel.core.system import exportSelected
			#exportSelected(output_path, force=True, type='OBJexport')
			mc.file(output_path, **kwargs)
		return True
	
	def export_mesh(self, **kwargs):
		
		format, ext = str(self.format.text()), str(self.formatExt.text())
		format = self.name_pat.sub( \
			lambda m: '%(name)' + m.group(1)[1:], format)
		format = self.frame_pat.sub( \
			lambda m: '%(frame)' + m.group(1)[1:], format)
		path = Path(self.path.text())
		
		if not self.animation.isChecked() and self.oneFilePerNode.isChecked():
			sel = ls(selection=True)
			for s in sel:
				select(s)
				name = format % dict(name=s.name().replace('|', '')) + ext
				self.write_mesh(path, name, **kwargs)
			select(sel)
		else:
			
			end, by = self.end.value(), self.by.value()
			frame, renum_frame, renum_by = (self.frame, self.renum_frame,
				self.renum_by)
			
			info('Exporting frames... Press Esc to cancel.')
			self.progress_init(1)
			while (by > 0 and frame <= end) or (by < 0 and frame >= end):
				
				if self.aborted: return
				
				setCurrentTime(frame)
				if self.oneFilePerNode.isChecked():
					sel = ls(selection=True)
					for s in sel:
						select(s)
						name = format % dict(name=s.shortName(),
							frame=renum_frame) + ext
						if not self.write_mesh(path, name):
							break
				else:
					name = format % dict(frame=renum_frame) + ext
					if not self.write_mesh(path, name, **kwargs):
						break
				
				# Prepare for the next iteration.
				frame += by
				renum_frame += renum_by
				self.export_count += 1
				self.progress_step()
	
	def export_skin_weights(self):
		
		format, ext = str(self.format.text()), str(self.formatExt.text())
		format = self.name_pat.sub( \
			lambda m: '%(name)' + m.group(1)[1:], format)
		path = Path(self.path.text())
		
		# Validate selection.
		sel = selected()
		if not sel:
			error('Selection is empty.')
		
		# Find the skin cluster.
		sc = mel.findRelatedSkinCluster(sel[0])
		skin_cluster = None
		for s in sel:
			sc = mel.findRelatedSkinCluster(s)
			if sc:
				skin_cluster = ls(sc)[0]
				break
		if not skin_cluster:
			error('No skin cluster found.')
		
		for mesh in sel:
			
			mesh_element = Element('Mesh', name=mesh)
			xml_tree = ElementTree(mesh_element)
			
			sc = mel.findRelatedSkinCluster(mesh)
			if not sc: continue
			sc = ls(sc)[0]
			
			influences = sc.influenceObjects()
			inf_tag = SubElement(mesh_element, 'Influences')
			for i, inf in enumerate(influences):
				SubElement(inf_tag, 'Influence', index=str(i), name=inf)
			#joints = ls(ios, type='joint')
			#if len(joints) < len(ios):
			#	error('Remove non-joint influences before exporting to Massive.')
			
			# TODO: progress bar
			
			name = format % dict(name=mesh.name().replace('|', '') \
				.replace(':', '.')) + ext
			with open(path / name, 'w') as f:
				
				#f.write(os.linesep + '# influences')
				#for i, inf in enumerate(ios):
				#	if inf in influences:
				#		inf_index = influences.index(j)
				#	else:
				#		influences += (inf,)
				#		inf_index = len(influences)
					#f.write('%sdeformer %d %s' % (os.linesep, i, inf))
				
				#f.write(os.linesep)
				
				vertices = SubElement(mesh_element, 'Vertices')
				
				#f.write(os.linesep + '# weights')
				for i, vtx in enumerate(mesh.vtx):
					vertex = SubElement(vertices, 'Vertex', pos=str(vtx.getPosition()))
					#f.write('%s%d: ' % (os.linesep, vi))
					for ii, inf in enumerate(influences):
						weight_val = skinPercent(sc, '%s.vtx[%d]' % (mesh, i),
							transform=inf, query=True)
						if weight_val:
							SubElement(vertex, 'Weight', influence=str(ii),
								value=str(weight_val))
							#f.write(' %d %f' % (ii, weight_val))
				
				
				
				#f.write(os.linesep + ':')
				rough_string = tostring(xml_tree.getroot(), 'utf-8')
				reparsed = minidom.parseString(rough_string)
				f.write(reparsed.toprettyxml(indent='\t'))
	
	def fix_format(self, ignore_scene=False):
		"""
		Creates a Python string format based on the name already supplied in
		the format text box and the total number of frames that will be exported.
		"""
		
		# Set short names for vars.
		start, end, by, renum_start, renum_by = (self.start.value(),
			self.end.value(), self.by.value(),
			self.renumStart.value(), self.renumBy.value())
		
		# Determine whether to use float values for the string format.
		boxes = self.renumFrames.isChecked() \
			and (renum_start, renum_by) or (start, by) 
		is_float = True in [x != int(x) for x in boxes]
		dorf = is_float and '.2f' or 'd'
		
		# Figure out how much padding to use.
		padding = len(str(self.total_frames()))
		if is_float:
			padding += 3  # Decimal + 2 precision slots count as padding.
		
		# Break-up the format text box into segments and replace any
		# existing string formats with the new one.
		format = str(self.format.text())
		if not self.oneFilePerNode.isChecked():
			format = self.name_pat.sub('', format)
		if not self.animation.isChecked():
			format = self.frame_pat.sub('', format)
		segs = self.split_pat.split(format)
		frame = [s for s in segs if self.frame_pat.match(s)]
		
		if not ignore_scene:
			if self.oneFilePerNode.isChecked():
				if '%s' not in segs:
					if frame:
						i = segs.index(frame[0])
						segs.insert(i, '.')
						segs.insert(i, '%s')
						segs.insert(i, '.')
					elif not segs:
						segs.append('%s')
					else:
						segs.extend(['.', '%s'])
			elif not segs:
				segs.append('geo')
			if self.animation.isChecked():
				if not frame:
					segs.extend(['.', '%d'])
				for i, s in enumerate(segs):
					if self.frame_pat.match(s):
						segs[i] = '%%0%d' % padding + dorf
		
		# Put all the pieces back together.
		format = ''.join(segs).replace('..', '.')
		if format.startswith('.'):
			format = format[1:]
		if format.endswith('.obj'):
			format = format[:-4]
		if format.endswith('.'):
			format = format[:-1]
		self.format.setText(format)
	
	def progress_init(self, loop_checks=1):
		min, max, self.step = self.animation.isChecked() and \
			(int(x.value() * 100) for x in (self.start, self.end, self.by)) or \
			(0, 100 * loop_checks, 100)
		
		# Start the main progress bar.
		self.main_progress.setIsInterruptable(True)
		self.main_progress.setMaxValue(sys.maxsize)
		self.main_progress.setMinValue(-sys.maxsize)
		self.main_progress.setMaxValue(max)
		self.main_progress.setMinValue(min)
		self.main_progress.beginProgress()
		
		# Start the local progress bar.
		self.progress.setRange(min, max)
		self.progress.setValue(min)
	
	def progress_step(self):
		self.main_progress.step(self.step)
		self.progress.setValue(int(self.progress.value()) + self.step)
	
	def set_path(self, sd=workspace.getPath()):
		"""
		Shows a folder browser and assigns the selection to the location
		text box.
		"""
		
		path = fileDialog2(dialogStyle=1, fileMode=2, startingDirectory=sd,
			caption='Select your output directory')
		if path:
			path = path[0]
			self.path.setText(path)
		return path
	
	def total_frames(self):
		start, end, by = (self.start.value(), self.end.value(), self.by.value())
		return int((end - start) / by + by)
	
	#===============================================
	# properties
	#===============================================
	
	@property
	def aborted(self):
		if self.main_progress.getIsCancelled():
			self._aborted = True
		return self._aborted
	
	@aborted.setter
	def aborted(self, value):
		self._aborted = value
	
	#===============================================
	# PyQt slots
	#===============================================
	
	@pyqtSlot(int)
	def on_exportCombo_currentIndexChanged(self, index):
		animation_enabled = index != 3
		self.animation.setEnabled(animation_enabled)
		
		self.objOptions.setHidden(index != 2)
		self.cameraChannels.setHidden(index != 1)
		self.animationChannelsTopLine.setHidden(index != 1)
		
		self.formatExt.setText(('.ma', '.ma', '.obj', '.xml')[index])
		self.oneFilePerNode.setText('One file per ' + \
			('joint chain', 'camera', 'mesh', 'skin')[index])
		self.createStandIn.setChecked(index == 1)
		self.createStandIn.setEnabled(index == 1)
		self.on_animation_clicked(self.animation.isChecked())
		self.exportButton.setText('Export ' + self.exportCombo.currentText())
		
		if not animation_enabled:
			self.animation.setChecked(False)
		if animation_enabled:
			if self.toolBox.count() == 1:
				for w, text in self.animation_widgets:
					self.toolBox.addItem(w, text)
					w.show()
		else:
			if self.toolBox.count() > 1:
				for w, text in self.animation_widgets:
					self.toolBox.removeItem(1)
					w.hide()
	
	@pyqtSlot(bool)
	def on_animation_clicked(self, checked):
		ofpf = checked and self.exportCombo.currentIndex() == 2
		self.oneFilePerFrame.setEnabled(checked)
		self.oneFilePerFrame.setChecked(ofpf)
		self.oneFile.setChecked(not ofpf)
		for w, text in self.animation_widgets:
			w.setEnabled(checked)
		self.setFromTimeSlider.click()
		self.fix_format()
		
	@pyqtSlot()
	def on_reload_clicked(self):
		mod = sys.modules[__name__]
		reload(mod)
		mod.Exporter()
	
	@pyqtSlot()
	def on_enableAll_clicked(self):
		[cb.setChecked(True) for cb \
			in self.channelsFrame.findChildren(QCheckBox) if cb.isEnabled()]
	
	@pyqtSlot()
	def on_disableAll_clicked(self):
		for cb in self.channelsFrame.findChildren(QCheckBox):
			cb.setChecked(False)
	
	@pyqtSlot(float)
	def on_start_valueChanged(self, value):
		if self.end.value() < self.start.value():
			self.end.setValue(self.start.value())
		self.fix_format()
	
	@pyqtSlot(float)
	def on_end_valueChanged(self, value):
		if self.end.value() < self.start.value():
			self.start.setValue(self.end.value())
		self.fix_format()
	
	@pyqtSlot(float)
	def on_by_valueChanged(self, value):
		if self.by.value() == 0:
			self.by.setValue(1)
			error('"By frame" cannot be equal to zero.')
		self.fix_format()
	
	@pyqtSlot(float)
	def on_renumStart_valueChanged(self, value):
		self.fix_format()
	
	@pyqtSlot(float)
	def on_renumBy_valueChanged(self, value):
		if self.renumBy.value() == 0:
			self.renumBy.setValue(1)
			error('"By frame" cannot be equal to zero.')
		self.fix_format()
	
	@pyqtSlot()
	def on_setFromTimeSlider_clicked(self):
		self.start.setValue(playbackOptions(query=True, minTime=True))
		self.end.setValue(playbackOptions(query=True, maxTime=True))
		self.by.setValue(playbackOptions(query=True, by=True))
		self.fix_format()
	
	@pyqtSlot(bool)
	def on_renumFrames_toggled(self, checked):
		for o in (self.renumStartLabel, self.renumStart, self.renumByLabel,
			self.renumBy):
			o.setEnabled(checked)
	
	@pyqtSlot()
	def on_format_editingFinished(self):
		self.fix_format(True)
	
	@pyqtSlot()
	def on_formatExt_editingFinished(self):
		if not str(self.formatExt.text()).startswith('.'):
			self.formatExt.setText('.' + self.formatExt.text())
	
	@pyqtSlot()
	def on_formatButton_clicked(self):
		showHelp('http://diveintopython.org/native_data_types/' + \
			'formatting_strings.html', absolute=True)
	
	@pyqtSlot()
	def on_pathButton_clicked(self):
		self.set_path()
	
	@pyqtSlot(bool)
	def on_oneFilePerNode_clicked(self, checked):
		self.fix_format()
	
	@pyqtSlot(bool)
	def on_exportAll_toggled(self, checked):
		self.export_toggled()
	
	@pyqtSlot(bool)
	def on_exportSelection_toggled(self, checked):
		self.export_toggled()
	
	@pyqtSlot()
	def on_exportOptions_clicked(self):
		if self.exportButton.isChecked():
			ExportSelectionOptions()
		else:
			ExportOptions()
	
	@pyqtSlot()
	def on_loadWeightsButton_clicked(self):
		for mesh in selected():
			sc = mel.findRelatedSkinCluster(mesh)
			if not sc: continue
			sc = ls(sc)[0]
			
			doc = ElementTree(file=path + mesh.nodeName().replace('|', '').replace(':', '.') + '.xml')
			
			influences = [inf.attrib['name'] for inf in doc.findall('//Influence')]
			for i, vtx in enumerate(doc.findall('//Vertex')):
				weights = [(influences[int(w.attrib['influence'])],
					float(w.attrib['value'])) for w in vtx.findall('Weight')]
				skinPercent(sc, '%s.vtx[%d]' % (mesh, i),
					transformValue=weights)
	
	@pyqtSlot()
	def on_exportButton_clicked(self):
		
		if not ls(selection=True):
			return error('Nothing is currently selected.')
		
		# Load the objExport plug-in if it hasn't been already.
		kwargs = {}
		if self.formatExt.text() == '.obj':
			mll = 'objExport.mll'
			if not pluginInfo(mll, query=True, loaded=True):
				try:
					loadPlugin(mll)
					info('Loaded plug-in: ' + mll)
				except:
					return error('Failed loading plug-in: ' + mll)
			#kwargs = dict(force=True, constructionHistory=False,
			#	channels=False, constraints=False, expressions=True,
			#	shader=False, preserveReferences=False, type='OBJexport')
			options = dict(groups=self.groups, ptgroups=self.pointGroups,
				materials=self.materials, smoothing=self.smoothing,
				normals=self.normals)
			options = ';'.join('%s=%d' % (k, cb.isChecked()) \
				for k, cb in options.items())
			kwargs = dict(exportSelected=True, type='OBJexport', force=True,
				options=options)
		elif self.exportCombo.currentIndex() == 2:  # mesh
			return error('Unsupported extension: %s.' % self.formatExt.text())
		
		# Validate the output path.
		output_path = Path(self.path.text())
		if not output_path.exists():
			output_path = Path(self.set_path(workspace.getPath()))
			if not output_path.exists():
				return
		
		# Validate the frame range.
		start, end, by = self.start.value(), self.end.value(), self.by.value()
		remainder = (end - start) % by
		if remainder:
			click_result = confirmDialog(title='Confirm',
				message=os.linesep.join(( \
				'The end frame will not be exported because',
				'the "by frame" overshoots it by %.2f.' % remainder)),
				button=('OK', 'Cancel'), cancelButton='Cancel',
				defaultButton='OK', dismissString='Cancel')
			if click_result == 'Cancel':
				return
		
		# Validate the format.
		format = str(self.format.text())
		try:
			format % (start + by)
		except TypeError:
			return error('Invalid format: "%s". ' % format + \
				'Click the \'...\' tool button for help.' % format)
		
		# Disable UI elements while running.
		[o.show() for o in self.run_showers]
		[o.setEnabled(False) for o in self.run_disablers]
		
		# Set the range.
		if self.renumFrames.isChecked():
			renum_start = self.renumStart.value()
			self.renum_by = self.renumBy.value()
		else:
			renum_start = start
			self.renum_by = by
		self.frame, self.renum_frame = start, renum_start
		
		# Set loop vars.
		self.aborted = False
		self.export_count = 0
		self.copy_and_replace_all = False
		
		# Call the appropriate export function.
		(self.export_skeleton, self.export_camera, self.export_mesh,
			self.export_skin_weights)[self.exportCombo.currentIndex()](**kwargs)
		
		self.main_progress.endProgress()
		
		# Enable UI elements back.
		[o.hide() for o in self.run_showers]
		[o.setEnabled(True) for o in self.run_disablers]
		
		# Report results.
		if self.aborted:
			msg = 'Aborted with %s exported'
		else:
			msg = 'Successfully exported %s'
		plural = self.export_count != 1 and 's' or ''
		frames = '%d frame' % self.export_count + plural
		result(msg % frames + ' to: %s.' % output_path)