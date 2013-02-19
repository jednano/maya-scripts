import re
import sys

from maya import OpenMayaUI as mui
from pymel.core.general import listRelatives
from pymel.core.general import ls
from pymel.core.general import selected
from pymel.core.language import melGlobals
from pymel.core.system import Path
from pymel.core.uitypes import Menu
from pymel.core.uitypes import toQtObject
from pymel.core.uitypes import toQtLayout
from pymel.core.windows import currentParent
from pymel.core.windows import deleteUI
from pymel.core.windows import dockControl
from pymel.core.windows import menuItem
from pymel.core.windows import setParent
from pymel.core.windows import window
from PyQt4 import uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import sip
from xml.etree.ElementTree import ElementTree

from lava.core.general import error
from lava.core.general import info


class UIBase(object):

    def __new__(cls):
        uiClass, baseClass = uic.loadUiType(cls.getUIPath().abspath())
        cls.__bases__ += (uiClass,)
        self = super(UIBase, cls).__new__(cls)
        self.uiClass, self.baseClass = uiClass, baseClass
        return self
    
    def __init__(self):
        self.baseClass.__init__(self)
    
    @classmethod
    def getUIPath(cls):
        """This method is intended to be overridden in cases when the UI file
        is located somewhere other than the same folder.
        """
        clsFile = sys.modules[cls.__module__].__file__
        return Path(clsFile).stripext() + '.ui'


def getMayaWindow():
    """
    Get the main Maya window as a QtGui.QMainWindow instance
    @return: QtGui.QMainWindow instance of the top level Maya windows
    """
    ptr = mui.MQtUtil.mainWindow()
    if ptr is not None:
        return sip.wrapinstance(long(ptr), QObject)


class UIDialogBase(UIBase, QDialog): pass


class UIWidgetBase(UIBase, QWidget):
    def __init__(self, parent=None):
        super(UIWidgetBase, self).__init__()
        self.qtParent = toQtLayout(currentParent()) if parent is None \
                else toQtObject(parent)
        self.qtLayout = self.qtParent.layout()
        
        super(self.uiClass, self).__init__(self.qtParent)
        
        self.setupUi(self)
        self.qtLayout.insertWidget(6, self)


class UIDocker(QMainWindow):
    """
    TODO:
    """
    
    def __new__(cls, *args, **kwargs):
        """
        Flags:
            - ui_file: f                (unicode, default:Subclass module's .pyc filename.ui)
                Full path to a user interface file to load.
        """
        
        form_class, base_class = uic.loadUiType(get_ui_path(cls, **kwargs))
        if QMainWindow not in cls.__bases__:
            cls.__bases__ += (form_class, base_class)
        return super(UIDocker, cls).__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        """
        Flags:
            - parent: p                (QMainWindow, default:Wrapped Maya main window)
                The parent layout for this control.
        """
        
        # Get the maya main window as a QMainWindow instance.
        parent = kwargs.pop('p', kwargs.pop('parent',
            sip.wrapinstance(long(mui.MQtUtil.mainWindow()), QObject)))
        super(QMainWindow, self).__init__(parent)
        # uic adds a function to our class called setupUi, calling this creates all the
        # widgets from the .ui file.
        self.setupUi(self)
        self.__name__ = self.__class__.__name__
        g_name = 'g%sDocker' % self.__name__
        melGlobals.initVar('string', g_name)
        
        docker = melGlobals[g_name]
        if docker and dockControl(docker, exists=True):
            info('Deleting docker: ' + docker)
            deleteUI(docker, control=True)
        docker = dockControl(allowedArea=['left', 'right'], area='right',
            floating=False, content=self.__name__,
            parent='MayaWindow|formLayout1',
            label=str(self.windowTitle()), width=self.width())
        melGlobals[g_name] = docker.split('|')[-1]
    
    def get_affected_nodes(self, dagObjects=True, **kwargs):
        """
        Reads the UI's "Affecting: Hierarchy, Selected, All" radios and
        returns the appropriate selection of nodes.
        """
        if self.affectingAllRadio.isChecked():
            nodes = ls(dagObjects=dagObjects, **kwargs)
        else:
            nodes = selected(dagObjects=dagObjects, **kwargs)
            if nodes and self.affectingHierarchyRadio.isChecked():
                nodes += [n for n in \
                    listRelatives(allDescendents=True, **kwargs) \
                    if n not in nodes]
        return nodes
    
    @pyqtSlot()
    def on_reloadButton_clicked(self):
        mod = self.__module__
        reload(sys.modules[mod])
        eval('sys.modules[mod].%s()' % self.__class__.__name__)


class UIMenu(Menu):
    """
    Takes a Qt UI file and converts everything into Maya menuItems and
    separators.
    """
    
    def __new__(cls, *args, **kwargs):
        """Creates the new menu and return it."""
        return super(UIMenu, cls).__new__(cls, create=True,
            tearOff=True, name='main' + cls.__name__,
            parent=melGlobals['gMainWindow'], label='')
    
    def __init__(self, *args, **kwargs):
        super(UIMenu, self).__init__(*args, **kwargs)
        doc = ElementTree(file=get_ui_path(self.__class__, **kwargs))
        
        # The action text is separate from the addaction tags in the ui file, so
        # load each action text into a dictionary to make it accessible from
        # the traverse function.
        actions = {}
        for act in doc.findall('//action'):
            actions[act.attrib['name']] = act.find('property/string').text
        
        # Parse the entire ui file, looking specifically for menus and actions.
        # This also generates the Maya menu bar.
        self.traverse(doc.findall('*'), actions)
    
    def traverse(self, elements, actions):
        """
        Traverses through XML elements looking for menu items and
        actions, which are then translated into Maya's UI.
        """
        
        for element in elements:
            if element.tag == 'addaction':
                name = element.attrib['name']
                if name == 'separator':
                    menuItem(divider=True)
                elif name in actions:
                    try:
                        cmd = eval('self.on_%s_clicked' % name)
                        menuItem(name, label=actions[name], command=cmd,
                            annotation=cmd.__doc__)
                    except AttributeError:
                        menuItem(name, label=actions[name])
            elif element.tag == 'widget' and element.attrib['class'] == 'QMenu':
                if self.getLabel() != '':
                    mi = menuItem(element.attrib['name'],
                        subMenu=True, tearOff=True,
                        label=element.find('property/string').text)
                    self.traverse(element.findall('*'), actions)
                    setParent(mi.parent(), menu=True)
                else:
                    self.setLabel(element.find('property/string').text)
                    setParent(self, menu=True)
                    self.traverse(element.findall('*'), actions)
            else:
                self.traverse(element.findall('*'), actions)


class UICustomContextMenu(QMenu):
    """
    By setting a QWidget's contextMenuPolicy to CustomContextMenu, you can use
    this class to make the context menu creation more simple. For example:
    
    @pyqtSlot(QPoint)
    def on_myWidget_customContextMenuRequested(self, point):
        UICustomContextMenu(self.myWidget, point, (
            ('Action Text 1', 'Status Tip 1'),
            ('Action Text 2', 'Status Tip 2')
        ))
    
    TODO: Add the click command too.
    """
    
    def __init__(self, sender, point, actions):
        super(UICustomContextMenu, self).__init__()
        for text, tip in actions:
            act = self.addAction(self.tr(text))
            act.setStatusTip(self.tr(tip))
        self.exec_(sender.mapToGlobal(point))


def get_ui_path(cls, **kwargs):
    """
    Flags:
        - ui_file: f                (unicode, default:Subclass module's .pyc filename.ui)
            Full path to a user interface file to load.
    """
    pat = re.compile('^(.+)\.pyc?$')
    ui_path = kwargs.pop('f', kwargs.pop('ui_file', pat.match( \
        sys.modules[cls.__module__].__file__).group(1) + '.ui'))
    info('Loading ui file: ' + ui_path)
    return ui_path
