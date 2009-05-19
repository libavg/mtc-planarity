#!/usr/bin/env python
# Copyright (C) 2009
#    Martin Heistermann, <mh at sponc dot de>
#
# untangle is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# untangle is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with untangle.  If not, see <http://www.gnu.org/licenses/>.

from libavg import avg, Point2D, Grabbable, AVGApp, button, anim
from libavg.AVGAppUtil import getMediaDir

import math
import gzip
import cPickle

g_player = avg.Player.get()


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
        self.__node = g_player.createNode('rect',{
            'width': 20,
            'height': 20,
            'strokewidth': 3,
            'color': 'aa0000'})
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
        self.__gameController.addEdge(self)

        self.__line = g_player.createNode('line',{
            'strokewidth': 3,
            })
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
            elif pos: # new clash
                Clash(self.__gameController, pos, self, other)
        self.__gameController.level.checkWin() # XXX

    def onVertexMotion(self):
        self.checkCollisions()
        self.__draw()

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
        self.__gameController.removeEdge(self)
        self.__line.unlink()
        self.__line = None
        self.__clashes = {}
        pass

class Vertex(object):
    def __init__(self, gameController, pos):
        pos = Point2D(pos)
        self.__pos = pos
        self.__edges = []
        self.__node = g_player.createNode('image', {'href':'vertex.png'})
        parent = gameController.vertexDiv
        parent.appendChild(self.__node)
        self.__node.pos = pos - self.__node.size/2
        self.__clashState = False

        def onMotion (pos,size,angle,pivot):
            width, height = self.__node.size
            pos.x = min(max(pos.x, 0), parent.width - width)
            pos.y = min(max(pos.y, 0), parent.height - height)
            self.__node.pos = pos
            for edge in self.__edges:
                edge.onVertexMotion()

        self.__grabbable = Grabbable(
                node = self.__node,
                minSize = self.__node.size,
                maxSize = self.__node.size,
                onMotion = onMotion,
                inertia = 0,
                torque = 0,
                moveNode = False
                )
        self.__onMotion = []

    def addEdge(self, edge):
        self.__edges.append(edge)

    def updateClashState(self):
        clashState = False
        for edge in self.__edges:
            if edge.isClashed():
                clashState = True

        if clashState != self.__clashState:
            self.__clashState = clashState
            if clashState:
                self.__node.href = 'vertex_clash.png'
            else:
                self.__node.href = 'vertex.png'

    @property
    def pos(self):
        return self.__node.pos + self.__node.size/2

    def delete(self):
        self.__grabbable.delete()
        self.__node.unlink()
        self.__node = None
        self.__edges = None

class Level(object):
    def __init__(self, gameController):
        self.__gameController = gameController
        self.__isRunning = False
        self.__numClashes = 0

    def addClash(self):
        self.__numClashes +=1
        self.__gameController.updateStatus()

    def removeClash(self):
        assert self.__numClashes > 0
        self.__numClashes -=1
        self.__gameController.updateStatus()

    def getStatus(self):
        type_, number = self.__scoring[2:4]
        return "clashes left: %u\tgoal %c %u" % ( self.__numClashes, type_, number)

    def checkWin(self):
        type_, number = self.__scoring[2:4]
        print type, number, self.__numClashes
        if self.__isRunning:
            if ((type_=='=' and self.__numClashes == number)
                    or (type_=='<' and self.__numClashes < number)):
                self.__gameController.levelWon()

    def start(self, levelData):
        self.__scoring = levelData["scoring"]
        self.vertices = []
        for vertexCoord in levelData["vertices"]:
            # transform coord here
            self.vertices.append(Vertex(self.__gameController, vertexCoord))

        self.edges = []
        for v1, v2 in levelData["edges"]:
            self.edges.append(Edge(self.__gameController, self.vertices[v1], self.vertices[v2]))


        for edge in self.edges: # might be able to remove this if vertex default state is unclashed
            edge.checkCollisions()
        for vertex in self.vertices:
            vertex.updateClashState()

        self.__isRunning = True

    def stop(self):
        self.__isRunning = False
        for edge in self.edges:
            edge.delete()
        self.edges = []

        for vertex in self.vertices:
            vertex.delete()
        self.vertices = []

def loadLevels():
    fp = gzip.open('data/levels.pickle.gz')
    levels = cPickle.load(fp)
    fp.close()
    return levels

class GameController(object):
    def __init__(self, parentNode, onExit):
        self.__levels = loadLevels()
        self.__edges = []
        self.gameDiv = g_player.createNode('div',{})
        parentNode.appendChild(self.gameDiv)

        self.edgeDiv = g_player.createNode('div',{'sensitive':False})
        self.vertexDiv = g_player.createNode('div',{})
        self.clashDiv = g_player.createNode('div',{'sensitive':False})
        for div in (self.edgeDiv, self.vertexDiv, self.clashDiv):
            self.gameDiv.appendChild(div)
            div.size = parentNode.size

        self.winnerDiv = g_player.createNode('words', {
            'text': "YOU WON!",
            'size': 100,
            'opacity': 0,
            'sensitive': False,
            })
        parentNode.appendChild(self.winnerDiv)
        self.winnerDiv.pos = (parentNode.size - Point2D(self.winnerDiv.getMediaSize())) / 2

        self.levelMenu = LevelMenu(parentNode)
        infoBar = g_player.createNode('div',{'sensitive':False})
        infoBar.pos = (0,50)
        parentNode.appendChild(infoBar)

        exitButton = LabelButton(infoBar,
                pos = (50,0),
                text = 'exit',
                size = None,
                callback = lambda e: onExit)
        levelButton = LabelButton(infoBar,
                pos = (200,0),
                text = 'levels',
                size = None,
                callback = lambda e:self.levelMenu.open())

        statusNode = g_player.createNode('words', { 'size':17})
        statusNode.pos = (400, 0)
        infoBar.appendChild(statusNode)

        def setStatus(text):
            statusNode.text = text
        self.__statusHandler = setStatus

        self.__curLevel = 2
        self.level = Level(self)
        self.__startNextLevel()

    def addEdge(self, edge):
        self.__edges.append(edge)
    
    def removeEdge(self, edge):
        self.__edges.remove(edge)

    def getEdges(self):
        return self.__edges

    def updateStatus(self):
        self.__statusHandler(self.level.getStatus())

    def __startNextLevel(self):
        level = self.__levels[self.__curLevel]
        self.level.start(level)
        self.__curLevel+=1
        self.__curLevel %= len(self.__levels)

    def levelWon(self):
        def nextLevel():
            self.level.stop()
            self.__startNextLevel()
            anim.ParallelAnim([
                    anim.fadeOut(self.winnerDiv, 400),
                    anim.fadeIn(self.gameDiv, 400),
                    ],
                    onStop = lambda: None
                    ).start()
        anim.ParallelAnim([
                anim.fadeIn(self.winnerDiv, 600),
                anim.fadeOut(self.gameDiv, 600),
                ],
                onStop = lambda: g_player.setTimeout(1000,nextLevel)).start()


class LabelButton(button.Button):
    def __init__(self, parentNode, pos, text, size, callback):
        if size is None:
            size = 17
        mainDiv = g_player.createNode('div',{})
        mainDiv.pos = pos
        parentNode.appendChild(mainDiv)
        for i in range(4):
            labelNode = g_player.createNode('words',{
                'size': size,
                'text': text,
                })
            mainDiv.appendChild(labelNode)
        button.Button.__init__(self, mainDiv, callback)

class LevelMenu:
    def __init__(self, parentNode):
        # main div catches all clicks and disables game underneath
        self.mainDiv = g_player.createNode('div',{
            'active':False,
            'opacity':0})
        self.mainDiv.size = parentNode.size
        parentNode.appendChild(self.mainDiv)

        menuDiv = g_player.createNode('div',{})
        self.mainDiv.appendChild(menuDiv)

        menuDiv.pos = (140,100)
        menuDiv.size = (1000,500)
        bgImage = g_player.createNode('image',
                {'href': 'menubg.png'})
        bgImage.size = menuDiv.size
        menuDiv.appendChild(bgImage)

        xxx = g_player.createNode('words',
                {'text': 'IMPLEMENT ME'})
        menuDiv.appendChild(xxx)

        LabelButton(menuDiv,
                (50,50),
                text = 'close menu',
                size = None,
                callback = lambda e:self.close())


    def open(self):
        self.mainDiv.active = True
        anim.fadeIn(self.mainDiv, 400).start()

    def close(self):
        def setInactive():
            self.mainDiv.active = False
        anim.fadeOut(self.mainDiv, 400, onStop = setInactive).start()

class Planarity(AVGApp):
    multitouch = True
    def init(self):
        self._parentNode.mediadir = getMediaDir(__file__)
        self.__controller = GameController(self._parentNode, onExit = self.leave)

    def _enter(self):
        #self.__controller.startLevel()
        pass

    def _leave(self):
        pass

if __name__ == '__main__':
    Planarity.start(resolution = (1280,720))


