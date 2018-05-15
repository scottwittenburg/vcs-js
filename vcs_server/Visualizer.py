"""This module exposes methods for finding and creating visualizations."""

import json
from wslink import register as exportRpc
# import vtk modules.
import vtk
from vtk.web import protocols
# vcs modules
import vcs
import cdms2
import genutil
import cdutil
import sys
import traceback
from VcsPlot import VcsPlot, updateGraphicsMethodProps


class Visualizer(protocols.vtkWebProtocol):

    _canvas = {}

    @exportRpc('vcs.canvas.plot')
    def plot(self, prevWindowId, varSpecs, method, template, width, height, opts={}):
        canvas = self._canvas[prevWindowId] if prevWindowId != 0 else None
        plot = VcsPlot(canvas, width=width, height=height)
        plot.setGraphicsMethod(method)
        plot.setTemplate(template)
        all_vars = []
        for varSpec in varSpecs:
            f = cdms2.open(varSpec['uri'])
            # use [] so that the var is not read.
            var = f[varSpec['variable']]
            if ('operations' in varSpec):
                for op in varSpec['operations']:
                    if ('subRegion' in op):
                        kargs = op['subRegion']
                        var = var.subRegion(**kargs)
                    elif ('subSlice' in op):
                        kargs = op['subSlice']
                        # fill in None with begin and end of the current axis
                        for axis in kargs.keys():
                            values = kargs[axis]
                            newValues = values
                            axisIndex = var.getAxisIndex(axis)
                            if values[0] is None:
                                newValues[0] = 0
                            if values[1] is None:
                                newValues[1] = var.shape[axisIndex] - 1
                            kargs[axis] = slice(*newValues)
                        var = var.subSlice(**kargs)
                    elif ('transform' in op):
                        for axis in op["transform"]:
                            method = op["transform"][axis]
                            if method == "avg":
                                var = cdutil.averager(var,axis="({})".format(axis))
                            elif method == "std":
                                # .std does not work with a FileVariable
                                # var[:] turns var into a transientVariable which can be used in .std()
                                var = genutil.statistics.std(var[:], axis="({})".format(axis))
                            else:
                                print "Got {} as a transform method".format(method)
            if ('axis_order' in varSpec):
                indexOrder = varSpec['axis_order']
                axisOrder = var.getAxisIds()
                stringOrder = ''.join(["({})".format(axisOrder[i]) for i in indexOrder])
                var = var(order=stringOrder)
            all_vars.append(var)
        plot.loadVariable(all_vars)
        canvas = plot.getCanvas()
        windowId = self.getGlobalId(plot.getWindow())
        self._canvas[windowId] = canvas
        return [windowId]

    @exportRpc('vcs.canvas.clear')
    def clear(self, windowId):
        if windowId in self._canvas:
            self._canvas[windowId].clear()
            return True
        return False

    @exportRpc('vcs.canvas.resize')
    def resize(self, windowId, width, height):
        if windowId in self._canvas:
            canvas = self._canvas[windowId];
            canvas.geometry(width, height)
            return True
        return False

    @exportRpc('vcs.canvas.close')
    def close(self, windowId):
        canvas = self._canvas.pop(windowId)
        if canvas:
            canvas.close()
            del canvas
            return True
        return False

    # ======================================================================
    # Common elements routines
    @exportRpc('vcs.listelements')
    def listelements(self, typeName):
        """Returns a list of element names"""
        return vcs.listelements(typeName)

    @exportRpc('vcs.removeelement')
    def removeelement(self, typeName, name):
        """Removes the element [typeName, name]."""
        name = str(name)
        typeName = str(typeName)
        vcs.removeG(name, typeName)
        return True

    # ======================================================================
    # Colormap routines
    @exportRpc('vcs.getcolormap')
    def getcolormap(self, name):
        """Returns the color values in a colormap"""
        name = str(name)
        return vcs.getcolormap(name).getindex().values()

    @exportRpc('vcs.setcolormap')
    def setcolormap(self, name, values):
        """Sets color values in a specified colormap"""
        name = str(name)
        cm = vcs.getcolormap(name)
        for i, value in enumerate(values):
            cm.setcolorcell(i, value[0], value[1], value[2], value[3])

    @exportRpc('vcs.createcolormap')
    def createcolormap(self, name, nameSource):
        """Creates a colormap 'name' as a copy of 'nameSource'"""
        name = str(name)
        if (nameSource is None):
            nameSource = 'default'
        else:
            nameSource = str(nameSource)
        cm = vcs.createcolormap(name, nameSource)
        return cm.getindex().values()

    # ======================================================================
    # Graphics method routines
    @exportRpc('vcs.getgraphicsmethod')
    def getgraphicsmethod(self, typeName, name):
        """Returns the graphics method object"""
        typeName = str(typeName)
        name = str(name)
        gm = vcs.getgraphicsmethod(typeName, name)
        if (gm is None):
            raise ValueError('Cannot find graphics method [%s, %s]' % (typeName, name))
        propertyNames = [i for i in gm.__slots__ if not i[0] == '_' and hasattr(gm, i)]
        properties = {k:getattr(gm, k) for k in propertyNames}
        return properties

    @exportRpc('vcs.creategraphicsmethod')
    def creategraphicsmethod(self, typeName, name, nameSource):
        """Creates a graphicsmethod 'name' with type 'typeName' as a copy of 'nameSource'"""
        typeName = str(typeName)
        name = str(name)
        if (nameSource is None):
            nameSource = 'default'
        else:
            nameSource = str(nameSource)
        vcs.creategraphicsmethod(typeName, nameSource, name)
        return self.getgraphicsmethod(typeName, name)

    @exportRpc('vcs.getgraphicsmethodtypes')
    def getgraphicsmethodtypes(self):
        """Returns a list of available graphics methods"""
        return vcs.graphicsmethodlist()

    @exportRpc('vcs.getgraphicsmethodvariablecount')
    def getgraphicsmethodvariablecount(self, typeName):
        return vcs.xmldocs.obj_details['graphics method'][typeName]['slabs']

    @exportRpc('vcs.setgraphicsmethod')
    def setgraphicsmethod(self, typeName, name, nameValueMap):
        gm = vcs.getgraphicsmethod(typeName, name)
        updateGraphicsMethodProps(nameValueMap, gm)

    # ======================================================================
    # Template Method routines
    @exportRpc('vcs.gettemplates')
    def gettemplates(self):
        templates = {}
        for tname in vcs.elements['template'].keys():
            templates[tname] = vcs.utils.dumpToDict(vcs.elements['template'][tname])[0]
        return templates

