#=================================================
# external imports
#=================================================

import ctypes
import itertools
import pickle
import platform
import string
import sys
from pymel.core.general import addAttr
from pymel.core.general import objExists
from pymel.core.general import setAttr
from pymel.core.language import mel
from pymel.core.language import melGlobals
from pymel.core.language import scriptJob
from pymel.core.system import Path
from pymel.core.system import workspace
from pymel.mayautils import executeDeferred
from pymel.util import getEnvs
from pymel.util import putEnv

#=================================================
# internal imports
#=================================================

from .menu import LavaMenu
from .menu import rehash_and_reload

#=================================================
# functions
#=================================================

def _fix_path(p):
	return p.normpath().encode().lower().replace('\\', '/')

def compress(data, selectors):
	"""
	itertools.compress was added in Python 2.7 and 3.1; if you need to support <2.7 or
	<3.1, here's an implementation of that function:
	"""
	for d, s in zip(data, selectors):
		if s:
			yield d
itertools.compress = compress

def get_available_drives():
	"""
	http://stackoverflow.com/questions/4188326/in-python-how-do-i-check-if-a-drive-exists-w-o-throwing-an-error-for-removable-d/4790310#4790310
	"""
	if 'Windows' not in platform.system():
		return []
	drive_bitmask = ctypes.cdll.kernel32.GetLogicalDrives()
	return list(itertools.compress(string.ascii_uppercase,
		map(lambda x:ord(x) - ord('0'), bin(drive_bitmask)[:1:-1])))

def _set_working_drive(working_drive):
	#set the working drive if it's not already
	if not working_drive:
		for c in reversed(get_available_drives()):
			d = Path(c + ':')
			if not (d / 'lavaWorkingDrive').isfile(): continue
			working_drive = d.drive
			break
		if not working_drive: return False
	working_drive = Path(working_drive[0] + ':/')
	
	#set the maya path
	maya_path = Path(working_drive) / 'maya'
	if not maya_path.isdir(): return False
	
	#it's too late at this point, unfortunately, to pick up the latest version of pymel,
	#nor does the Maya.env PYTHONPATH seem to work like it should, so,
	#assuming your working drive is Z, your Maya path is z:/maya and you've
	#installed the latest version of pymel in your Maya path, you need to edit the
	#environment variables for your account to include
	#PYTHONPATH: z:/maya/scripts;z:/maya/pymel-1.x.x
	#i wish there was a better way and maybe there is, but i really devoted a lot
	#of time and energy into solving this problem with python scripts and this is
	#the only solution that worked.
	
	#look for and load the maya/plug-ins folder too.
	env_key = 'MAYA_PLUG_IN_PATH'
	pips = getEnvs(env_key)
	for i, p in enumerate(pips):
		pips[i] = _fix_path(Path(p))
	for f in maya_path.listdir():
		if f.name == 'plug-ins':
			f = _fix_path(f)
			if f in pips:
				del pips[pips.index(f)]
			pips.insert(0, f)
			break
	putEnv(env_key, ';'.join(pips))
	
	#set the workspace
	workspace(maya_path / 'projects', openWorkspace=True)
	
	#set the script path
	script_path = maya_path / 'scripts'
	if script_path.isdir():
		
		#prepare some empty dictionaries to store unique
		#folder paths as keys for script locations.
		mels, pys, pymods = {}, {}, {}
		
		#put the file's folder path in the appropriate mel, mods
		#or pys dictionary.
		pats = {'__init__.py*': pymods, '*.mel': mels, '*.py': pys}
		for f in script_path.walkfiles():
			for k, v in pats.items():
				if f.fnmatch(k):
					v[_fix_path(f.dirname())] = None
		
		#remove any pys keys that are also found in pymods.
		#this is the only reason we made pymods in the first place, so
		#delete pymods to make it clear that we're done with it.
		for k in (k for k in pymods.keys() if k in pys):
			del pys[k]
		del pymods
		
		#fix all the sys.paths to make them consistent with pys
		#key-searches and add any py leftovers to the sys.paths.
		pys[_fix_path(script_path)] = None
		sp = []
		for p in sys.path:
			p = _fix_path(Path(p))
			if p in pys:
				del pys[p]
			sp.append(p)
		sys.path = [k for k in reversed(sorted(pys.keys(), key=str.lower))] + sp
		
		#fix all the maya script paths to make them consistent with mels
		#key-searches and add any mel leftovers to the env var.
		mels[_fix_path(script_path)] = None
		env_key = 'MAYA_SCRIPT_PATH'
		sps = getEnvs(env_key)
		for i, p in enumerate(sps):
			sps[i] = _fix_path(Path(p))
			if sps[i] in mels:
				del mels[sps[i]]
		for k in reversed(sorted(mels.keys(), key=str.lower)):
			sps.insert(0, k)
		putEnv(env_key, ';'.join(sps))
		
		#sourcing the scriptEditorPanel, for some reason, will actually check
		#the pymelScrollFieldReporter.py in the Plug-in Manager. if this is not
		#done, it will throw an error whenever the script editor is opened.
		sep = 'scriptEditorPanel.mel'
		if (script_path / sep).isfile():
			mel.source(sep)
	
	return True

def _source_mels(d):
	for file_name in d:
		mel.source(file_name + '.mel')

def _sign_the_scene(author):
	if not objExists('defaultLayer.Author'):
		addAttr('defaultLayer', longName='Author', dataType='string')
		setAttr('defaultLayer.Author', author, type='string', lock=True)

def auto_sign_new_scenes(author):
	"""
	To combat plagiarism, sign the defaultLayer with the author's name every
	time a new scene is created.
	"""
	_sign_the_scene(author)
	scriptJob(event=['NewSceneOpened',
		lambda *args: executeDeferred(lambda *args: _sign_the_scene(author))],
		protected=True)

def init(**kwargs):
	"""
	Flags:
		- load_menu: lm						(bool, default:True)
			Loads the Lava menu bar menu to Maya's menu bar.
		
		- signature: s							(unicode, default:None)
			Signs your name onto any new scene's defaultLayer as a locked attribute.
			This is just an extra measure of security to protect your work against
			plagiarism, making it more difficult, but not impossible to plagiarize.
		
		- source_mels: sm					(list, default:[])
			Sources the provided MEL scripts after everything has been initialized
			(e.g. source_mels=['cometMenu'])
		
		- working_drive: wd					(unicode, default:None)
			Sets the drive from which scripts should be loaded. If set to None,
			automatically searches available drives for a lavaWorkingDrive file.
			If the file is found, that drive will be the working drive. This is especially
			useful for temporary drives (e.g. USB drives).
	"""
	
	# Pop-out all the kwarg flags.
	working_drive = kwargs.pop('wd', kwargs.pop('working_drive', None))
	load_menu = kwargs.pop('lm', kwargs.pop('load_menu', True))
	signature = kwargs.pop('s', kwargs.pop('signature', None))
	source_mels = kwargs.pop('sm', kwargs.pop('source_mels', []))
	
	# Extend gLavaSourcedMels global with the source_mels kwarg.
	melGlobals.initVar('string', 'gLavaSourcedMels')
	mels = melGlobals['gLavaSourcedMels']
	mels = mels and pickle.loads(mels) or {}
	for m in source_mels:
		if m.endswith('.mel'): m = m[:-4]
		mels[m] = None
	melGlobals['gLavaSourcedMels'] = pickle.dumps(mels)
	
	# Keep track of how many times the init function has been called.
	melGlobals.initVar('int', 'gLavaInitialized')
	melGlobals['gLavaInitialized'] += 1
	if melGlobals['gLavaInitialized'] == 1:
		_set_working_drive(working_drive)
		if working_drive != sys.modules[__name__].__file__[0]:
			# If the working drive is different than the current module's drive then
			# we want to assume the working drive has the most recent scripts.
			# Reload all the modules to pickup latest scripts.
			rehash_and_reload(verbose=True)
			return False
	
	if load_menu: executeDeferred(LavaMenu)
	executeDeferred(lambda *args: _source_mels(mels))
	if signature: auto_sign_new_scenes(signature)