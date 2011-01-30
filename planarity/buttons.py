#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009
#    Martin Heistermann, <mh at sponc dot de>
#
# This library is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.
#
# Original author of this file: Thomas Schott, <scotty at c-base dot org>

from libavg import avg

g_player = avg.Player.get()


class Button(object):
    def __init__(self, node):
        self._cursorID = None
        self._node = node
        self._node.setEventHandler(avg.CURSORDOWN, avg.MOUSE | avg.TOUCH, self.__onDown)

    def __onDown(self, event):
        assert self._cursorID is None
        self._node.setEventHandler(avg.CURSORDOWN, avg.MOUSE | avg.TOUCH, None)
        self._cursorID = event.cursorid
        self._node.setEventCapture(self._cursorID)
        self._node.setEventHandler(avg.CURSORUP, avg.MOUSE | avg.TOUCH, self.__onUp)
        self._onDown(event)
        return True  # stop event propagation

    def __onUp(self, event):
        if not self._cursorID == event.cursorid:
            return
        self._node.setEventHandler(avg.CURSORUP, avg.MOUSE | avg.TOUCH, None)
        self._node.releaseEventCapture(self._cursorID)
        self._cursorID = None
        self._node.setEventHandler(avg.CURSORDOWN, avg.MOUSE | avg.TOUCH, self.__onDown)
        self._onUp(event)

    def delete(self):
        if not self._cursorID is None:
            self._node.releaseEventCapture(self._cursorID)
        self._node.setEventHandler(avg.CURSORUP, avg.MOUSE | avg.TOUCH, None)
        self._node.setEventHandler(avg.CURSORDOWN, avg.MOUSE | avg.TOUCH, None)


class LabelButton(Button):
    def __init__(self, parentNode, text, size, callback, pos=(0, 0)):
        node = g_player.createNode('words', {
                'pos':pos,
                'fontsize':size,
                'text':text})
        parentNode.appendChild(node)
        self.__callback = callback
        self.__isActive = True
        self.__isOver = False
        super(LabelButton, self).__init__(node)

    @property
    def size(self):
        return self._node.getMediaSize()

    def setPos(self, pos):
        self._node.pos = pos

    def _onDown(self, event):
        self._node.setEventHandler(avg.CURSOROUT, avg.MOUSE | avg.TOUCH, self.__onOut)
        if self.__isActive:
            self._node.color = 'ff6000' # red
        self.__isOver = True

    def _onUp(self, event):
        self._node.setEventHandler(avg.CURSOROUT, avg.MOUSE | avg.TOUCH, None)
        self._node.setEventHandler(avg.CURSOROVER, avg.MOUSE | avg.TOUCH, None)
        if self.__isActive:
            self._node.color = 'ffffff' # white
            if self.__isOver:
                self.__callback()
        self.__isOver = False

    def __onOut(self, event):
        if not self._cursorID == event.cursorid:
            return
        self._node.setEventHandler(avg.CURSOROUT, avg.MOUSE | avg.TOUCH, None)
        self._node.setEventHandler(avg.CURSOROVER, avg.MOUSE | avg.TOUCH, self.__onOver)
        if self.__isActive:
            self._node.color = 'ffffff' # white
        self.__isOver = False

    def __onOver(self, event):
        if not self._cursorID == event.cursorid:
            return
        self._node.setEventHandler(avg.CURSOROVER, avg.MOUSE | avg.TOUCH, None)
        self._node.setEventHandler(avg.CURSOROUT, avg.MOUSE | avg.TOUCH, self.__onOut)
        if self.__isActive:
            self._node.color = 'ff6000' # red
        self.__isOver = True

    def setActive(self, active):
        self.__isActive = active
        if self.__isActive:
            if self.__isOver:
                self._node.color = 'ff6000' # red
            else:
                self._node.color = 'ffffff' # white
        else:
            self._node.color = '7f7f7f' # gray


class MoveButton(Button):
    def __init__(self, node, onDown=None, onUp=None, onMotion=None):
        self.__onDownCallback = onDown or (lambda event: False)
        self.__onUpCallback = onUp or (lambda event: False)
        self.__onMotionCallback = onMotion or (lambda event: False)
        self.__slowdownID = None
        super(MoveButton, self).__init__(node)

    def delete(self):
        super(MoveButton, self).delete()
        self.__stopSlowdown()
        self._node.setEventHandler(avg.CURSORMOTION, avg.MOUSE | avg.TOUCH, None)

    def _onDown(self, event):
        self.__stopSlowdown()
        self._node.setEventHandler(avg.CURSORMOTION, avg.MOUSE | avg.TOUCH,
                self.__onMotion)
        self.__lastPos = event.pos
        self.__onDownCallback(event)

    def _onUp(self, event):
        self._node.setEventHandler(avg.CURSORMOTION, avg.MOUSE | avg.TOUCH, None)
        self.__onUpCallback(event)
        if event.speed.x or event.speed.y:
            self.__startSlowdown(event)

    def __onMotion(self, event):
        if not self._cursorID == event.cursorid:
            return
        event.motion = event.pos - self.__lastPos
        if event.motion.x or event.motion.y: # avoid (0,0) motion events when using the mouse
            self.__lastPos = event.pos
            self.__onMotionCallback(event)

    def __onSlowdownMotion(self):
        self.__speed *= 0.95
        if self.__speed.getNorm() < 1:
            self.__stopSlowdown()
        else:
            self.__motionDiff += self.__speed
            motion = avg.Point2D(round(self.__motionDiff.x), round(self.__motionDiff.y))
            if motion.x or motion.y:
                fakeEvent = avg.Event
                fakeEvent.motion = motion
                self.__motionDiff -= motion
                self.__onMotionCallback(fakeEvent)

    def __startSlowdown(self, event):
        self.__speed = event.speed * 10.0
        self.__motionDiff = avg.Point2D(0, 0)
        if self.__slowdownID is None:
            self.__slowdownID = g_player.setInterval(10, self.__onSlowdownMotion)

    def __stopSlowdown(self):
        if not self.__slowdownID is None:
            g_player.clearInterval(self.__slowdownID)
            self.__slowdownID = None

