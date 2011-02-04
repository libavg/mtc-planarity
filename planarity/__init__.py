#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Init script for Planarity package
#
# Copyright (C) 2011
#    Thomas Schott, <scotty at c-base dot org>
#
# This file is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This file is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this file.  If not, see <http://www.gnu.org/licenses/>.

import os
from libavg.AVGAppUtil import getMediaDir, createImagePreviewNode
from planarity import Planarity

__all__ = [ 'apps', 'Planarity']

def createPreviewNode(maxSize):
    filename = os.path.join(getMediaDir(__file__), 'preview.png')
    return createImagePreviewNode(maxSize, absHref = filename)

apps = (
        {'class': Planarity,
            'createPreviewNode': createPreviewNode},
        )
