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

from libavg import avg, Point2D, Grabbable, AVGApp
from libavg.AVGAppUtil import getMediaDir

import math

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
        gameController.addClash()
        edge1.addClash(edge2, self)
        edge2.addClash(edge1, self)
        self.__node = g_player.createNode('image',{'href':'clash.png'})
        gameController.clashDiv.appendChild(self.__node)
        self.goto(pos)

    def goto(self, pos):
        self.__node.pos = pos - self.__node.size/2

    def delete(self):
        self.__gameController.removeClash()
        edge1, edge2 = self.__edges
        edge1.removeClash(edge2, self)
        edge2.removeClash(edge1, self)

        self.__node.unlink()


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
        #v1, v2 = self.__vertices[0].pos, self.__vertices[1].pos
        # this is a trick to avoid clashes at vertex centers
        #p1 = v1 + (v2-v1).getNormalized()
        #p2 = v2 + (v1-v2).getNormalized()
        #return p1, p2

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

    def onVertexMotion(self):
        self.checkCollisions()
        self.__draw()

    def addClash(self, other, clash):
        assert other not in self.__clashes.keys()
        self.__clashes[other] = clash
        self.updateClashState()

    def removeClash(self, other, clash):
        del self.__clashes[other]
        self.updateClashState()

    def __draw(self):
        self.__line.pos1 = self.__vertices[0].pos
        self.__line.pos2 = self.__vertices[1].pos
        if self.isClashed():
            self.__line.color = 'ff0000' # red
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

class Vertex(object):
    def __init__(self, gameController, pos):
        pos = Point2D(pos)
        self.__pos = pos
        self.__edges = []
        self.__node = g_player.createNode('image', {'href':'vertex.png'})
        parent = gameController.vertexDiv
        parent.appendChild(self.__node)
        self.__node.pos = pos - self.__node.size/2
        self.__clashState = True

        def onMotion (pos,size,angle,pivot):
            # TODO: restrict pos to playing area
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
                self.__node.opacity = 1
            else:
                self.__node.opacity = 0.5

    @property
    def pos(self):
        return self.__node.pos + self.__node.size/2

class GameController(object):
    def __init__(self, parentNode):
        self.__numClashes = 0
        self.__edges = []
        self.edgeDiv = g_player.createNode('div',{'sensitive':False})
        self.vertexDiv = g_player.createNode('div',{})
        self.clashDiv = g_player.createNode('div',{'sensitive':False})
        for div in (self.edgeDiv, self.vertexDiv, self.clashDiv):
            parentNode.appendChild(div)
            div.size = parentNode.size

    def addClash(self):
        self.__numClashes +=1

    def removeClash(self):
        assert self.__numClashes > 0
        self.__numClashes -=1
        if self.__numClashes == 0:
            print "WINNER!"

    def addEdge(self, edge):
        self.__edges.append(edge)

    def getEdges(self):
        return self.__edges

    def startLevel(self):
        # XXX create vertices and edges here

        v1 = Vertex(self, (100,300))
        v2 = Vertex(self, (500,300))
        v3 = Vertex(self, (200,100))
        v4 = Vertex(self, (200,500))
        v5 = Vertex(self, (300,500))
        vertices = [v1,v2,v3,v4]

        import random
        for i in range(10):
            x = random.uniform(100,500)
            y = random.uniform(100,500)
            v = Vertex(self, (x,y))
            vertices.append(v)


        edges = []

        for vertex1 in vertices:
            cnt = 0
            for vertex2 in vertices:
                if cnt==2:
                    continue
                if vertex1 is vertex2:
                    continue
                cnt+=1
                edges.append(Edge(self, vertex1, vertex2))
        edges.append(Edge(self, v4, v5))

        for edge in edges: # might be able to remove this if vertex default state is unclashed
            edge.checkCollisions()

        for vertex in vertices + [v5]:
            vertex.updateClashState()


class Planarity(AVGApp):
    multitouch = True
    def init(self):
        self._parentNode.mediadir = getMediaDir(__file__)
        self.__controller = GameController(self._parentNode)

    def _enter(self):
        self.__controller.startLevel()
        pass

    def _leave(self):
        pass

if __name__ == '__main__':
    Planarity.start(resolution = (1280,720))


