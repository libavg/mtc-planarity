#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009
#    Martin Heistermann, <mh at sponc dot de>
#
# planarity (aka untangle) is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# planarity is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with planarity.  If not, see <http://www.gnu.org/licenses/>.

from libavg import avg, gameapp, Point2D
from libavg.AVGAppUtil import getMediaDir

import math
import gzip
import cPickle
from hashlib import md5

from buttons import *

BASE_SIZE = (1280, 720)
DS_STATUS_TAG = 'planarity'[::-1]

g_player = avg.Player.get()
g_scale = 1.0


def getDelta(motion, topLeft, bottomRight, boundingSize):
    xDelta = min(max(motion.x, -topLeft.x), boundingSize.x - bottomRight.x)
    yDelta = min(max(motion.y, -topLeft.y), boundingSize.y - bottomRight.y)
    return Point2D(xDelta, yDelta)


class VertexGroup(object):
    def __init__(self, gameController, polygon, vertices):
        self._polygon = g_player.createNode("polygon", {
            'color': 'ffff00',
            'strokewidth': 3*g_scale,
            'opacity': 0.3,
            'pos': polygon
            })
        self._vertices = vertices
        self._gameController = gameController
        self._gameController.level.addVertexGroup(self)
        self._gameController.vertexDiv.appendChild(self._polygon)

        self._button = g_player.createNode('image', {'href': 'close-button.png'})
        self._gameController.vertexDiv.appendChild(self._button)
        self._button.size *= g_scale
        self._button.pos = polygon[0] - self._button.size/2
        self._button.setEventHandler(avg.CURSORDOWN, avg.TOUCH | avg.MOUSE,
                lambda event: self.delete())

        xCoords = [vertex.pos.x for vertex in vertices]
        yCoords = [vertex.pos.y for vertex in vertices]
        self.topLeft = Point2D(min(xCoords), min(yCoords)) - vertices[0].size/2
        self.bottomRight = Point2D(max(xCoords), max(yCoords)) + vertices[0].size/2

        def onMotion(event):
            delta = getDelta(event.motion, self.topLeft, self.bottomRight,
                self._gameController.vertexDiv.size)
            for i, vertex in enumerate(self._vertices):
                vertex.pos += delta
            self._polygon.pos = [pos + delta for pos in self._polygon.pos]
            self._button.pos += delta
            self.topLeft += delta
            self.bottomRight += delta

        self._mover = MoveButton(self._polygon, onMotion=onMotion)

    def delete(self):
        self._mover.delete()
        self._gameController.ungroupVertices(self._vertices)
        self._polygon.unlink()
        self._button.unlink()


class GroupDetector(object):
    """use this as an event handler"""
    def __init__(self, gameController, event):
        self._gameController = gameController
        self._polyline = g_player.createNode("polyline", {
            'color': 'ffff00',
            'strokewidth': 1
            })
        gameController.groupDiv.appendChild(self._polyline)

        self._cursorid = event.cursorid
        self._polyline.setEventCapture(self._cursorid)
        self._polyline.setEventHandler(avg.CURSORMOTION, avg.TOUCH | avg.MOUSE,
            self._onMotion)
        self._polyline.setEventHandler(avg.CURSORUP, avg.TOUCH | avg.MOUSE,
            lambda event: self.delete())

        self._onMotion(event)
        pass

    def getClosedPolygon(self):
        """If the last edge intersects any edge, return a cleaned-up polygon
        representing the enclosed region."""
        points = self._polyline.pos  # in-Python object copy
        if len(points) < 4:
            return False
        last_edge = points[-2:]
        for i in range(len(points) - 2):
            edge = [points[i], points[i + 1]]
            intersection = line_intersect(edge, last_edge)
            if intersection:
                # include the intersection point itself, plus all the edges
                # after the intersecting edge, omitting the last edge
                return [intersection] + points[i + 1:-1]
        return False

    def _onMotion(self, event):
        self._polyline.pos += [event.pos]
        polygon = self.getClosedPolygon()
        if polygon:
            vertices = self._gameController.groupVertices(polygon)
            if vertices:
                self.delete()
                VertexGroup(self._gameController, polygon, vertices)

    def delete(self):
        self._polyline.releaseEventCapture(self._cursorid)
        self._polyline.setEventHandler(avg.CURSORMOTION, avg.TOUCH | avg.MOUSE, None)
        self._polyline.unlink()


def in_between(val,b1,b2):
    """return True if val is between b1 and b2"""
    return((b1>=val and val>=b2) or (b1<=val and val<=b2))

def line_collide(line1,line2):
    a=line1[0].x
    b=line1[0].y
    c=line1[1].x-line1[0].x
    d=line1[1].y-line1[0].y
    e=line2[0].x
    f=line2[0].y
    g=line2[1].x-line2[0].x
    h=line2[1].y-line2[0].y

    dem=g*d-c*h
    if dem==0: # parallel 
        return False

    s=(a*d+f*c-b*c-e*d)/dem
    x=e+s*g
    y=f+s*h
    return Point2D(x,y)

def line_intersect(line1, line2):
    ka, kb = line1
    la, lb = line2
    if (ka == la
            or ka == lb
            or kb == la
            or kb == lb):
        return False
    p = line_collide(line1, line2)
    if(p and in_between(p.x,ka.x,kb.x) # do line segments match?
            and in_between(p.x,la.x,lb.x)
            and in_between(p.y,ka.y,kb.y)
            and in_between(p.y,la.y,lb.y)):
        return p

    return False


class Clash(object):
    def __init__(self, gameController, pos, edge1, edge2):
        self.__edges = edge1, edge2
        self.__gameController = gameController
        gameController.level.addClash() #XXX
        edge1.addClash(edge2, self)
        edge2.addClash(edge1, self)
        #self.__node = g_player.createNode('image',{
        #    'href':'clash.png',
        #    'opacity': 0.7})
        """
        self.__node = g_player.createNode('circle',{
            'r': 10,
            'strokewidth': 5,
            'color': 'aa0000'})
        """
        self.__node = g_player.createNode('rect', {
                'size':Point2D(20,20)*g_scale,
                'strokewidth':3*g_scale,
                'color':'aa0000'})
        gameController.clashDiv.appendChild(self.__node)
        self.goto(pos)

    def goto(self, pos):
        self.__node.pos = pos - self.__node.size/2

    def delete(self):
        edge1, edge2 = self.__edges
        edge1.removeClash(edge2)
        edge2.removeClash(edge1)
        self.__node.unlink()
        self.__node = None
        self.__gameController.level.removeClash() #XXX


class Edge(object):
    def __init__(self, gameController, vertex1, vertex2):
        self.__vertices = vertex1, vertex2
        for vertex in self.__vertices:
            vertex.addEdge(self)
        self.__clashes = {}
        self.__gameController = gameController

        self.__line = g_player.createNode('line', {'strokewidth':3*g_scale})
        gameController.edgeDiv.appendChild(self.__line)
        self.__draw()
        self.__clashState = False

    def getLine(self):
        return [v.pos for v in self.__vertices]

    def checkCollisions(self):
        for other in self.__gameController.getEdges():
            pos = line_intersect(self.getLine(), other.getLine())
            if other in self.__clashes.keys():
                if pos:
                    self.__clashes[other].goto(pos)
                else:
                    self.__clashes[other].delete()
                    return True
            elif pos: # new clash
                Clash(self.__gameController, pos, self, other)
        return False

    def onVertexMotion(self):
        clashRemoved = self.checkCollisions()
        self.__draw()
        return clashRemoved

    def addClash(self, other, clash):
        assert other not in self.__clashes.keys()
        self.__clashes[other] = clash
        self.updateClashState()

    def removeClash(self, other):
        del self.__clashes[other]
        self.updateClashState()

    def __draw(self):
        self.__line.pos1 = self.__vertices[0].pos
        self.__line.pos2 = self.__vertices[1].pos
        if self.isClashed():
            self.__line.color = 'ff6000' # red
        else:
            self.__line.color = 'ffffff' # white

    def updateClashState(self):
        clashState = self.isClashed()
        if clashState != self.__clashState:
            self.__clashState = clashState
            self.__draw()
            for vertex in self.__vertices:
                vertex.updateClashState()

    def isClashed(self):
        return len(self.__clashes) > 0

    def delete(self):
        for clash in self.__clashes.values():
            clash.delete()
        self.__line.unlink()
        self.__line = None
        self.__clashes = {}


class Vertex(object):
    def __init__(self, gameController, pos):
        self._gameController = gameController
        self.__edges = []
        self.__node = g_player.createNode('image', {'href':'vertex.png'})
        parent = gameController.vertexDiv
        parent.appendChild(self.__node)
        self.__node.size *= g_scale
        self.__nodeOffset = self.__node.size / 2
        self.__node.pos = pos - self.__nodeOffset
        self.__clashState = False
        self._highlight = False
        self.draggable = True

        def onMotion(event):
            if not self.draggable:
                return
            delta = getDelta(event.motion, self.__node.pos,
                self.__node.pos + self.__node.size, parent.size)
            self.pos += delta

        self.__button = MoveButton(self.__node, onMotion=onMotion)

    def addEdge(self, edge):
        self.__edges.append(edge)

    def updateClashState(self):
        clashState = False
        for edge in self.__edges:
            if edge.isClashed():
                clashState = True
                break

        if clashState != self.__clashState:
            self.__clashState = clashState
            self.__setNodeImage()

    def highlight(self, addHighlighter):
        self._highlight = addHighlighter
        self.__setNodeImage()

    def __setNodeImage(self):
        if self._highlight:
            href = 'vertex_hl'
        else:
            href = 'vertex'
        if self.__clashState:
            self.__node.href = href + '_clash.png'
        else:
            self.__node.href = href + '.png'

    def getPos(self):
        return self.__node.pos + self.__nodeOffset

    def setPos(self, value):
        self.__node.pos = value - self.__nodeOffset
        clashRemoved = False
        for edge in self.__edges:
            clashRemoved |= edge.onVertexMotion()
        if clashRemoved:
            self._gameController.level.checkWin()

    pos = property(getPos, setPos)

    @property
    def size(self):
        return self.__node.size

    def delete(self):
        self.__button.delete()
        self.__button = None
        self.__node.unlink()
        self.__node = None
        self.__edges = None


class Level(object):
    def __init__(self, gameController):
        self.__gameController = gameController
        self.__isRunning = False
        self.__numClashes = 0
        self._vertexGroups = []

    def addClash(self):
        self.__numClashes +=1
        self.__gameController.updateStatus()

    def removeClash(self):
        assert self.__numClashes > 0
        self.__numClashes -=1
        self.__gameController.updateStatus()

    def getStatus(self):
        type_, number = self.__scoring[2:4]
        if type_ == '*':
            type_ = '&lt;='
        return "clashes left: %u<br/>goal: %s %u" %(self.__numClashes, type_, number)

    def getName(self):
        return self.__levelData['name']

    def checkWin(self):
        if self.__isRunning:
            type_, number = self.__scoring[2:4]
            # possible types: '=' (==) and '*' (<=)
            if ((type_=='=' and self.__numClashes == number)
                    or (self.__numClashes <= number)):
                self.__gameController.levelWon()

    def start(self, levelData):
        self.__levelData = levelData
        self.__scoring = levelData["scoring"]

        self.vertices = []
        for vertexCoord in levelData["vertices"]:
            self.vertices.append(Vertex(self.__gameController, vertexCoord))

        self.edges = []
        for v1, v2 in levelData["edges"]:
            self.edges.append(Edge(self.__gameController, self.vertices[v1], self.vertices[v2]))

        for edge in self.edges:
            edge.checkCollisions()

        self.__isRunning = True

    def pause(self):
        self.__isRunning = False

    def stop(self):
        self.__isRunning = False
        for edge in self.edges:
            edge.delete()
        self.edges = []
        for group in self._vertexGroups:
            group.delete()
        self._vertexGroups = []

        for vertex in self.vertices:
            vertex.delete()
        self.vertices = []

    def getEnclosedVertices(self, polygon):
        return [vertex for vertex in self.vertices
                if avg.pointInPolygon(vertex.pos, polygon)]

    def addVertexGroup(self, group):
        self._vertexGroups.append(group)


def loadLevels(size):
    fp = gzip.open(getMediaDir(__file__, 'data/levels.pickle.gz'))
    levels = cPickle.load(fp)
    fp.close()

    currentLevel = None
    app = Planarity.get()
    savedHash = app.getDatastore(DS_STATUS_TAG).data
    levelHash = md5(app.getUserdataPath(''))
    for levelIdx, level in enumerate(levels):
        vertices = level['vertices']
        minPos = Point2D(size)
        maxPos = Point2D(0, 0)
        for i in xrange(len(vertices)):
            levelHash.update(str(vertices[i]))
            vertices[i] = Point2D(vertices[i][0]*g_scale, vertices[i][1]*g_scale)
            if vertices[i].x < minPos.x:
                minPos.x = vertices[i].x
            if vertices[i].y < minPos.y:
                minPos.y = vertices[i].y
            if vertices[i].x > maxPos.x:
                maxPos.x = vertices[i].x
            if vertices[i].y > maxPos.y:
                maxPos.y = vertices[i].y
        level['hash'] = levelHash.hexdigest()
        if currentLevel is None and level['hash'] == savedHash:
            currentLevel = levelIdx

        # center level on screen
        levelSize = maxPos - minPos
        levelOffset = (size - levelSize) / 2 - minPos
        for i in xrange(len(vertices)):
            vertices[i] += levelOffset

    return levels, 0 if currentLevel is None else currentLevel


class GameController(object):
    def __init__(self, parentNode, onExit):
        self.__ds = Planarity.get().initDatastore(DS_STATUS_TAG, '', lambda s: type(s) == str)

        self.node = parentNode
        self.__levels, self.__curLevel = loadLevels(parentNode.size)

        background = g_player.createNode('image', {'href':'black.png'})
        background.size = parentNode.size
        parentNode.appendChild(background)

        self.gameDiv = g_player.createNode('div', {})
        parentNode.appendChild(self.gameDiv)

        self.edgeDiv = g_player.createNode('div', {'sensitive':False})
        self.groupDiv = g_player.createNode('div', {'sensitive':False})
        self.vertexDiv = g_player.createNode('div', {})
        self.vertexDiv.setEventHandler(avg.CURSORDOWN, avg.TOUCH | avg.MOUSE,
                self._onDraw)
        self.clashDiv = g_player.createNode('div', {'sensitive':False})

        self._groupedVertices = set()

        for div in (self.edgeDiv, self.vertexDiv, self.clashDiv, self.groupDiv):
            self.gameDiv.appendChild(div)
            div.size = parentNode.size

        self.winnerDiv = g_player.createNode('words', {
                'text':"YOU WON!",
                'fontsize':100*g_scale,
                'opacity':0,
                'sensitive':False})
        parentNode.appendChild(self.winnerDiv)
        self.winnerDiv.pos = (parentNode.size - self.winnerDiv.getMediaSize()) / 2

        LabelButton(parentNode, 'exit', 30*g_scale, onExit, Point2D(50, 50)*g_scale)
        LabelButton(parentNode, 'about', 30*g_scale,
                lambda:self.aboutBox.open(), Point2D(50, 100)*g_scale)
        LabelButton(parentNode, 'levels', 30*g_scale,
                lambda:self.levelMenu.open(self.__curLevel-1), Point2D(50, 150)*g_scale)

        statusNode = g_player.createNode('words', {
                'pos':(parentNode.width-50*g_scale, 50*g_scale),
                'fontsize':30*g_scale,
                'alignment':'right',
                'sensitive':False})
        parentNode.appendChild(statusNode)

        def setStatus(text):
            statusNode.text = text
        self.__statusHandler = setStatus

        levelNameDiv = g_player.createNode('div', {'sensitive':False})
        self.gameDiv.appendChild(levelNameDiv)
        bgImage = g_player.createNode('image', {'href':'menubg.png'})
        levelNameDiv.appendChild(bgImage)
        levelNameNode = g_player.createNode('words', {
                'fontsize':30*g_scale,
                'pos':Point2D(20, 20)*g_scale,
                'sensitive':False})
        levelNameDiv.appendChild(levelNameNode)

        def setLevelName(text):
            levelNameNode.text = text
            levelNameSize = levelNameNode.getMediaSize()
            bgImage.size = levelNameSize + Point2D(40, 40) * g_scale
            levelNameDiv.pos = parentNode.size / 2 - bgImage.size / 2
            levelNameDiv.opacity = 1
            avg.fadeOut(levelNameDiv, 6000)
        self.__levelNameHandler = setLevelName

        self.levelMenu = LevelMenu(parentNode, self.__levels, self.__curLevel,
                self.switchLevel)
        self.aboutBox = AboutBox(self.levelMenu.menuSize, self.levelMenu.listHeight,
                parent=parentNode)

        self.level = Level(self)
        self.__startNextLevel()

    def getEdges(self):
        return self.level.edges

    def updateStatus(self):
        self.__statusHandler(self.level.getStatus())

    def switchLevel(self, levelIndex):
        self.__curLevel = levelIndex
        self.levelWon(False)

    def __startNextLevel(self):
        self.__curLevel %= len(self.__levels)
        level = self.__levels[self.__curLevel]
        self.level.start(level)
        self.__levelNameHandler(self.level.getName())
        self.__curLevel += 1

    def levelWon(self, showWinnerDiv=True):
        def nextLevel():
            self.level.stop()
            self.__startNextLevel()
            if showWinnerDiv:
                avg.fadeOut(self.winnerDiv, 400)
            avg.fadeIn(self.gameDiv, 400)
        self.level.pause()
        level = self.__levels[self.__curLevel]
        if level['menuItem'].color == '7f7f7f':
            # unlock level
            level['menuItem'].color = 'ffffff'
            self.__ds.data = level['hash']
        if showWinnerDiv:
            avg.fadeIn(self.winnerDiv, 600)
            avg.fadeOut(self.gameDiv, 600, lambda: g_player.setTimeout(1000, nextLevel))
        else:
            avg.fadeOut(self.gameDiv, 600, nextLevel)

    def groupVertices(self, polygon):
        vertices = set(self.level.getEnclosedVertices(polygon))
        newGroup = vertices - self._groupedVertices
        self._groupedVertices = self._groupedVertices.union(newGroup)
        for vertex in newGroup:
            vertex.highlight(True)
            vertex.draggable = False
        return list(newGroup)

    def ungroupVertices(self, vertices):
        for vertex in vertices:
            vertex.highlight(False)
            vertex.draggable = True
        self._groupedVertices -= set(vertices)

    def _onDraw(self, event):
        GroupDetector(self, event)
        return False


class LevelMenu(object):
    VISIBLE_LEVELS = 11

    def __init__(self, parentNode, levels, curLevel, callback):
        # main div catches all clicks and disables game underneath
        mainDiv = g_player.createNode('div', {
                'size':parentNode.size,
                'active':False,
                'opacity':0})
        parentNode.appendChild(mainDiv)

        fontSize = round(16 * g_scale)
        itemHeight = fontSize * 3
        self.listHeight = itemHeight * self.VISIBLE_LEVELS

        self.menuSize = Point2D(round(mainDiv.width*0.75), self.listHeight+itemHeight)
        menuDiv = g_player.createNode('div', {
                'pos':(mainDiv.size-self.menuSize)/2,
                'size':self.menuSize})
        mainDiv.appendChild(menuDiv)

        bgImage = g_player.createNode('image', {
                'href':'menubg.png',
                'size':menuDiv.size})
        menuDiv.appendChild(bgImage)

        listFrameDiv = g_player.createNode('div', {
                'size':(menuDiv.width, self.listHeight),
                'crop':True})
        menuDiv.appendChild(listFrameDiv)

        selectionBg = g_player.createNode('rect', {
                'pos':(-1, (listFrameDiv.height-itemHeight)/2),
                'size':(listFrameDiv.width+2, itemHeight),
                'fillcolor':'ff6000'}) # red
        listFrameDiv.appendChild(selectionBg)

        listDiv = g_player.createNode('div', {
                'sensitive':False})
        listFrameDiv.appendChild(listDiv)

        pos = Point2D(listFrameDiv.width/2, 0)
        for levelIdx, level in enumerate(levels):
            menuItem = g_player.createNode('words', {
                    'text':level['name'],
                    'fontsize':fontSize,
                    'color':'7f7f7f' if levelIdx > curLevel else 'ffffff',
                    'alignment':'center'})
            menuItem.pos = pos + Point2D(0, (itemHeight-menuItem.getMediaSize().y)/2)
            level['menuItem'] = menuItem
            listDiv.appendChild(menuItem)
            pos.y += itemHeight

        separatorLine = g_player.createNode('line', {
                'pos1':(0, self.listHeight),
                'pos2':(menuDiv.width, self.listHeight)})
        menuDiv.appendChild(separatorLine)

        listDivMaxPos = selectionBg.pos.y
        listDivMinPos = -pos.y + listDivMaxPos + itemHeight

        def onOpen(levelIndex):
            mainDiv.active = True
            self.__selectedLevelIndex = levelIndex
            listDiv.pos = (0, listDivMaxPos - levelIndex * itemHeight)
            selectionBg.fillopacity = 0.5
            self.__motionDiff = 0
            self.__lastTargetPos = listDiv.pos.y
            avg.fadeIn(mainDiv, 400)
        self.__onOpenHandler = onOpen

        def onClose():
            def setInactive():
                mainDiv.active = False
            avg.fadeOut(mainDiv, 400, setInactive)

        def onStart():
            callback(self.__selectedLevelIndex)
            onClose()

        def onUpDown(event):
            self.__motionDiff = 0

        def onMotion(event):
            self.__motionDiff += event.motion.y
            motion = round(self.__motionDiff / itemHeight) * itemHeight
            if motion:
                pos = (0, min(max(self.__lastTargetPos+motion, listDivMinPos), listDivMaxPos))
                avg.LinearAnim(listDiv, 'pos', 200, listDiv.pos, pos).start()
                self.__motionDiff -= motion
                self.__lastTargetPos = pos[1]
                self.__selectedLevelIndex = int((listDivMaxPos-self.__lastTargetPos) / itemHeight)
                if levels[self.__selectedLevelIndex]['menuItem'].color == 'ffffff':
                    startBtn.setActive(True)
                    avg.LinearAnim(selectionBg, 'fillopacity', 200,
                            selectionBg.fillopacity, 0.5).start()
                else:
                    startBtn.setActive(False)
                    avg.LinearAnim(selectionBg, 'fillopacity', 200,
                            selectionBg.fillopacity, 0).start()

        MoveButton(listFrameDiv, onUpDown, onUpDown, onMotion)
        startBtn = LabelButton(menuDiv, 'start level', 20*g_scale, onStart)
        startBtn.setPos((itemHeight*2, self.listHeight+(itemHeight-startBtn.size.y)/2))
        closeBtn = LabelButton(menuDiv, 'close menu', 20*g_scale, onClose)
        closeBtn.setPos((menuDiv.width-itemHeight*2-closeBtn.size.x,
                self.listHeight+(itemHeight-closeBtn.size.y)/2))

    def open(self, levelIndex):
        self.__onOpenHandler(levelIndex)


class AboutBox(avg.DivNode):
    ABOUT_TEXT = [
        (32, 'Planarity'),
        (24, 'A multitouch adaption of the popular<br/>' \
             'game Planarity, aka Untangle'),
        (20, 'Authors:<br/>' \
             'Martin Heistermann &lt;mh@sponc.de&gt;<br/>' \
             'Thomas Schott &lt;scotty@c-base.org&gt;<br/>' \
             'Ka-Ping Yee &lt;ping@zesty.ca&gt;'),
        (20, 'levels borrowed from gPlanarity by Monty &lt;monty@xiph.org&gt;<br/>' \
             'based on libavg &lt;www.libavg.de&gt;')
    ]

    def __init__(self, boxSize, aboutHeight, **kwargs):
        kwargs['size'] = kwargs['parent'].size
        kwargs['active'] = False
        kwargs['opacity'] = 0
        super(AboutBox, self).__init__(**kwargs)

        boxDiv = avg.DivNode(pos=(self.size-boxSize)/2, size=boxSize, parent=self)
        avg.ImageNode(href='menubg.png', size=boxSize, parent=boxDiv)
        avg.LineNode(pos1=(0, aboutHeight), pos2=(boxSize.x, aboutHeight), parent=boxDiv)

        def onClose():
            def setInactive():
                self.active = False
            avg.fadeOut(self, 400, setInactive)

        closeBtn = LabelButton(boxDiv, 'close about', 20*g_scale, onClose)
        closeBtn.setPos(((boxDiv.width-closeBtn.size.x) / 2,
                aboutHeight + (boxSize.y-aboutHeight-closeBtn.size.y) / 2))

        aboutDiv = avg.DivNode(size=(boxSize.x, aboutHeight), sensitive=False,
                parent=boxDiv)
        pos = Point2D(aboutDiv.width / 2, 0)
        for size, txt in self.ABOUT_TEXT:
            node = avg.WordsNode(text=txt, pos=pos, fontsize=size*g_scale,
                    alignment='center', parent=aboutDiv)
            pos.y += node.height + node.getLineExtents(0).y
        aboutDiv.pos = (0, (aboutHeight - pos.y) / 2)

    def open(self):
        self.active = True
        avg.fadeIn(self, 400)


class Planarity(gameapp.GameApp):
    def init(self):
        self._parentNode.mediadir = getMediaDir(__file__)

        global g_scale
        size = self._parentNode.size
        g_scale = min(size.x / BASE_SIZE[0], size.y / BASE_SIZE[1])
        self.__controller = GameController(self._parentNode,
                onExit = self.quit)


if __name__ == '__main__':
    Planarity.start()
