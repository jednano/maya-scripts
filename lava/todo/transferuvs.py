from pymel.core.general import selected
from pymel.core.modeling import polyTransfer
from pymel.core.nodetypes import Transform
from pymel.core.runtime import BakeNonDefHistory

def transfer_UVs(sel=selected()):
	source, target = sel
	targets = isinstance(target, Transform) and target.getShapes() or [target]
	for t in targets:
		if t.attr('outMesh').exists() and t.attr('outMesh').listConnections():
			continue
		polyTransfer(t, uvSets=True, alternateObject=source)
	BakeNonDefHistory()