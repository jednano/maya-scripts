import sys
from pymel.core.system import rehash
from pymel.core.system import showHelp

from lava.core import shapes as sh
from lava.core.general import result
from lava.core.docker import exporter
from lava.core.docker import jointhelper
from lava.core.docker import renamer
from lava.core.docker import rigger
from lava.core.docker import spliner
from lava.core.dynamics import ncloth
from lava.core.ui.base import UIMenu


class LavaMenu(UIMenu):
	
	def on_exporter_clicked(self, *args):
		'Shows the range exporter docker.'
		reload(exporter)
		exporter.Exporter()
	
	def on_jointHelper_clicked(self, *args):
		'Shows you how to make joints.'
		reload(jointhelper)
		jointhelper.JointHelper()
	
	def on_renamer_clicked(self, *args):
		reload(renamer)
		renamer.Renamer()
	
	def on_rigger_clicked(self, *args):
		reload(rigger)
		rigger.Rigger()
	
	def on_spliner_clicked(self, *args):
		reload(spliner)
		spliner.Spliner()
	
	def on_nullAction_clicked(self, *args):
		sh.create_shapes(sh.Null)
	
	def on_locator_clicked(self, *args):
		sh.create_shapes(sh.Locator)
	
	def on_plus_clicked(self, *args):
		sh.create_shapes(sh.Plus)
	
	def on_circle_clicked(self, *args):
		sh.create_shapes(sh.Circle)
	
	def on_square_clicked(self, *args):
		sh.create_shapes(sh.Square)
	
	def on_cube_clicked(self, *args):
		sh.create_shapes(sh.Cube)
	
	def on_sphere_clicked(self, *args):
		sh.create_shapes(sh.Sphere)
	
	def on_arrow_clicked(self, *args):
		sh.create_shapes(sh.Arrow)
	
	def on_cross_clicked(self, *args):
		sh.create_shapes(sh.Cross)
	
	def on_orient_clicked(self, *args):
		sh.create_shapes(sh.Orient)
	
	def on_bulb_clicked(self, *args):
		sh.create_shapes(sh.Bulb)
	
	def on_joint_clicked(self, *args):
		sh.create_shapes(sh.Joint)
	
	def on_custom_clicked(self, *args):
		sh.create_shapes(sh.Custom)
	
	def on_createSnCloth_clicked(self, *args):
		ncloth.create_scaled_ncloth_prompt()
	
	def on_rehashAndReload_clicked(self, *args):
		'Re-source MEL scripts, reload Python modules and re-build menu.'
		self.deleteAllItems()
		self.delete()
		from lava.core import menu
		reload(menu)
		menu.rehash_and_reload(verbose=True)
	
	def on_visitWebsite_clicked(self, *args):
		'Visit jediscode.blogspot.com'
		showHelp('http://jediscode.blogspot.com', absolute=True)


def rehash_and_reload(**kwargs):
	"""
	Flags:
		- verbose: v				(bool, default:False)
			If set, displays messages about which modules are reloaded.
	"""
	
	verbose = kwargs.pop('v', kwargs.pop('verbose', False))
	rehash()
	for k in sorted(k for k, m in sys.modules.items() \
		if m and k.startswith('lava')):
		if verbose:
			print('reloading: %s' % sys.modules[k])
		del sys.modules[k]
	try:
		import userSetup
		reload(userSetup)
	except ImportError:
		pass
