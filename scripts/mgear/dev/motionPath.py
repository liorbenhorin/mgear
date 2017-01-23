import logging

logger = logging.getLogger(__name__)

import mgear.maya.curve as crv
import mgear.maya.applyop as applyop
import mgear.maya.transform as trns
import mgear.maya.synoptic.utils as utils
import mgear.maya.icon as ic

import maya.OpenMaya as OpenMaya
import maya.cmds as cmds
import pymel.core as pm


def start(*args):
    Motion_path_rig.create()


def deleteConnection(plug):
    if cmds.connectionInfo(plug, isDestination=True):
        plug = cmds.connectionInfo(plug, getExactDestination=True)
        readOnly = cmds.ls(plug, ro=True)
        # delete -icn doesn't work if destination attr is readOnly
        if readOnly:
            source = cmds.connectionInfo(plug, sourceFromDestination=True)
            cmds.disconnectAttr(source, plug)
        else:
            cmds.delete(plug, icn=True)


def simpllify_curve(path, subd, degree, keep_locators = False):
    spline = path

    stp = 0
    listOfMotionPath = []
    listOfVectors = []
    listOfLocators = []
    for i in range(0, subd, 1):
        print stp
        x = cmds.spaceLocator(n="simple_" + spline + "_loc_" + str(i))
        cmds.setAttr(x[0] + ".visibility", 0)
        # path2 = cmds.pathAnimation(x[0], c=spline, fractionMode=True, followAxis="x", upAxis="y", worldUpType="object", worldUpObject=upVector)

        path2 = cmds.pathAnimation(x[0], c=spline, fractionMode=True, followAxis="x", upAxis="y")

        deleteConnection(path2 + ".uValue")
        cmds.setAttr("{}.uValue".format(path2), stp)
        listOfMotionPath.append(path2)
        listOfVectors.append(cmds.xform(x, q=1, ws=1, t=1))
        listOfLocators.append(x)
        stp += 1 / float(subd - 1)
        cmds.select(cl=1)

    crv = cmds.curve(d=degree, n=spline + "_simplified", p=listOfVectors)
    cmds.delete(listOfMotionPath)
    if not keep_locators:
        for loc in listOfLocators:
            cmds.delete(loc)
        return crv

    else:
        return crv, listOfLocators

def joints_from_curve(curve):
    returnCV = []
    cmds.select(curve + '.cv[*]')
    cvs = cmds.ls(selection=True)

    rf = cvs[0].rfind(':')
    lenCVs = len(cvs[0])
    number = int(cvs[0][(rf + 1):(lenCVs - 1)])
    cvName = cvs[0][0:rf - 2]
    listOfJoints = list()

    for i in range(0, number + 1, 1):
        cmds.select(cl=True)
        returnCV.append(str(cvName) + '[' + str(i) + ']')
        jnt = cmds.joint()
        pos = cmds.pointPosition(str(curve) + '.cv[' + str(i) + ']')
        cmds.xform(jnt, a=1, t=pos)
        listOfJoints.append(jnt)

    return listOfJoints




def nulls_from_curve(curve):

    returnCV = []
    cmds.select(curve + '.cv[*]')
    cvs = cmds.ls(selection=True)

    rf = cvs[0].rfind(':')
    lenCVs = len(cvs[0])
    number = int(cvs[0][(rf + 1):(lenCVs - 1)])
    cvName = cvs[0][0:rf - 2]
    listOfLocators = list()


    for i in range(0, number + 1, 1):
        returnCV.append(str(cvName) + '[' + str(i) + ']')
        loc = cmds.spaceLocator()

        pos = cmds.pointPosition(str(curve) + '.cv[' + str(i) + ']')
        cmds.xform(loc, a=1, t=pos)

        listOfLocators.append(loc)


    return listOfLocators



###########################################
# Name: 		getUParam
# Description:
# Input:
# Returns: 		none
###########################################
def getUParam(pnt=[], crv=None):
    point = OpenMaya.MPoint(pnt[0], pnt[1], pnt[2])
    curveFn = OpenMaya.MFnNurbsCurve(getMObject(crv))

    scriptU = OpenMaya.MScriptUtil()
    paramPt = scriptU.asDoublePtr()

    point = curveFn.closestPoint(point, paramPt, 0.001, OpenMaya.MSpace.kObject)
    curveFn.getParamAtPoint(point, paramPt, 0.001, OpenMaya.MSpace.kObject)

    param = scriptU.getDouble(paramPt)
    return param


'''
This function let you get an MObject from a string rappresenting the object name
@param[in] objectName : string , the name of the object you want to work on
'''


def getMObject(objectName):
    if isinstance(objectName, list) == True:
        oNodeList = []
        for o in objectName:
            selectionList = OpenMaya.MSelectionList()
            selectionList.add(o)
            oNode = OpenMaya.MObject()
            selectionList.getDependNode(0, oNode)
            oNodeList.append(oNode)
        return oNodeList
    else:
        selectionList = OpenMaya.MSelectionList()
        selectionList.add(objectName)
        oNode = OpenMaya.MObject()
        selectionList.getDependNode(0, oNode)
        return oNode


def curve_pci_attach(path, items):

    crv = cmds.listRelatives(path, s=True)[0]

    for s in items:
        pos = cmds.xform(s, q=1, ws=1, t=1)
        u = getUParam(pos, crv)
        name = crv + "_pci"
        pci = cmds.createNode("pointOnCurveInfo", n=name)
        cmds.connectAttr(crv + '.worldSpace', pci + '.inputCurve')
        cmds.setAttr(pci + '.parameter', u)
        cmds.connectAttr(pci + '.position', s[0] + '.t')



class Motion_path_rig(object):
    def __init__(self):

        main_curve = simpllify_curve('curve1', 9,  3)
        main_positions = nulls_from_curve(main_curve)
        curve_pci_attach(main_curve, main_positions)
        up_curve = cmds.offsetCurve(main_curve, n = 'up_curve', d=-1.5, ugn=False, ch=False)[0]
        up_positions = nulls_from_curve(up_curve)
        curve_pci_attach(up_curve, up_positions)
        bind_joints = joints_from_curve(main_curve)

        for index, j in enumerate(bind_joints):

            cmds.pointConstraint(main_positions[index], j, mo=False)

            if index != len(bind_joints)-1:
                cmds.aimConstraint(main_positions[index+1], j, wuo = up_positions[index][0], wut = 'object')
            else:
                cmds.aimConstraint(main_positions[index-1],j, wuo=up_positions[index][0], wut='object', aim = [-1,0,0])


    @staticmethod
    def create():
        Motion_path_rig()
