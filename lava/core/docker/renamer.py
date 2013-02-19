from pymel.core.general import ls
from pymel.core.general import rename
from pymel.core.system import showHelp
from pymel.core.system import undoInfo
from PyQt4.QtCore import pyqtSlot
import re

from lava.core.general import error
from lava.core.general import result
from lava.core.ui.base import UIDocker


class Renamer(UIDocker):
	
	_renamed = 0
	
	def __init__(self, *args, **kwargs):
		super(Renamer, self).__init__(*args, **kwargs)
		self.assignNewWidget.hide()
	
	def assign_new_names(self):
		new_name = str(self.newName.text())
		if not new_name:
			return error('New name is empty.')
		
		# Solve naming conflicts by first naming everything foo#.
		for n in self._nodes:
			rename(n, 'foo#')
		
		if not new_name.count('%'):
			new_name += '%d'
		for i, n in enumerate(self._nodes):
			self.rename(n, new_name % (i + 1))
	
	def display_renamed_nodes(self):
		result('Renamed %d nodes.' % self._renamed)
		self._renamed = 0
	
	def rename(self, obj, new_name):
		rename(obj, new_name)
		self._renamed += 1
	
	def validate_form(self, skip_replace_with=False):
		search_for = str(self.searchFor.text())
		if not search_for:
			error('"Search for" field is empty.')
		if not skip_replace_with:
			replace_with = str(self.replaceWith.text())
			if not replace_with:
				error('"Replace with" field is empty.')
			return search_for, replace_with
		return search_for
	
	def search_replace_names(self):
		search_for, replace_with = self.validate_form()
		search_pat = re.compile(search_for)
		replace_arglen = replace_with.count('%')
		for i, n in enumerate(self._nodes):
			m = re.search(search_pat, n.nodeName())
			if m:
				#rw = re.sub(search_pat, replace_with, n.nodeName())
				rw = n.nodeName().replace(m.group(0), replace_with)
				print(rw)
				if not m.groups() or search_for in '^$':
					self.rename(n, rw)
					continue
				groups = list(m.groups())
				new_groups = list(m.groupdict().items())
				new_groups.extend([(str(groups.index(g) + 1), g) \
					for g in groups])
				new_groups = dict(new_groups)
				for k, v in new_groups.items():
					try: # to convert values into integers
						new_groups[k] = int(v)
					except TypeError:
						new_groups[k] = ''
					except ValueError:
						pass
				groups = new_groups
				
				try: # starting with the groups dict.
					rw %= groups
				except:
					try: # formatting with just the values.
						rw %= tuple(groups.values())
					except:
						# Try repeating the first group by the right number
						# of arguments.
						for g in groups.values():
							try: # to find a valid integer in the groups.
								rw %= tuple([int(g)] * replace_arglen)
								break
							except ValueError:
								continue
				self.rename(n, rw)
	
	@pyqtSlot()
	def on_searchReplaceRadio_clicked(self):
		self.searchReplaceWidget.show()
		self.assignNewWidget.hide()
		self.runButton.setText('Search and Replace')
	
	@pyqtSlot()
	def on_assignNewRadio_clicked(self):
		self.searchReplaceWidget.hide()
		self.assignNewWidget.show()
		self.runButton.setText('Assign New Names')
	
	@pyqtSlot()
	def on_helpButton_clicked(self):
		showHelp('http://docs.python.org/library/re.html',
			absolute=True)
	
	@pyqtSlot()
	def on_selectButton_clicked(self):
		self._nodes = self.get_affected_nodes()
		search_for = self.validate_form(skip_replace_with=True)
		search_pat = re.compile(search_for)
		select([n for n in self._nodes \
			if re.search(search_pat, n.nodeName())])
	
	@pyqtSlot()
	def on_runButton_clicked(self):
		self._nodes = self.get_affected_nodes()
		if not self._nodes:
			return error('No affected nodes to manipulate.')
		
		# Filter-out shape nodes from the list, but only if their
		# parents are also in the list, because they will get renamed
		# automatically.
		for n in [n for n in ls(self._nodes, geometry=True) \
			if n.getParent(1) in self._nodes]:
			del self._nodes[self._nodes.index(n)]
		
		undoInfo(openChunk=True)
		if self.searchReplaceRadio.isChecked():
			self.search_replace_names()
		else:
			self.assign_new_names()
		undoInfo(closeChunk=True)
		
		self.display_renamed_nodes()
