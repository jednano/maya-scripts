from pymel.core.animation import ikHandle
from pymel.core.general import ls
from pymel.core.general import select
from pymel.core.general import selected
from pymel.core.language import mel
from pymel.core.modeling import curve
from pymel.core.nodetypes import HairSystem
from pymel.core.runtime import SmoothBindSkin
from PyQt4.QtCore import pyqtSlot

from lava.core.ui.base import UIDocker


class Spliner(UIDocker):
	
	def __init__(self, *args, **kwargs):
		super(Spliner, self).__init__(*args, **kwargs)
		self.bottomWidget.hide()
	
	#========================================#
	# Generate Spline IK System Button
	#========================================#
	
	@pyqtSlot()
	def on_createSplineIKSystemButton_clicked(self):
		self.bottomWidget.show()
		self.topWidget.setEnabled(False)
		
		dj_chains, output_curves = (), ()
		for root in selected():
			dj_chain = (root,)
			while dj_chain[-1].numChildren():
				dj_chain += (dj_chain[-1].getChildren()[0],)
			dj_chains += (dj_chain,)
			
			# Assign a hair system to the driver joint chain.
			output_curves += ( \
				curve(p=[dj.getTranslation(space='world').get() \
				for dj in dj_chain]),)
		
		select(output_curves)
		mel.eval('assignNewHairSystem')
		follicle_curves = selected()
		
		hs = follicle_curves[0].getParent().getShape().attr('outHair') \
			.outputs()[0]
		
		[hs.attr(x).set(0) for x in \
			('drag', 'friction', 'mass', 'gravity', 'dynamicsWeight')]
		
		hs.attr('startCurveAttract').set(0.25)
		
		for i, dj_chain in enumerate(dj_chains):
			oc = output_curves[i]
			select(dj_chain + (oc,))
			SmoothBindSkin()
			bjs = [dj.attr('rotate').outputs()[0].attr('constraintRotateZ') \
				.outputs()[0] for dj in (dj_chain[0], dj_chain[-1])]
			ikHandle(startJoint=bjs[0], endEffector=bjs[1],
				curve=oc, solver='ikSplineSolver',
				parentCurve=False, createCurve=False)
		
		self.topWidget.setEnabled(True)
		self.bottomWidget.hide()
