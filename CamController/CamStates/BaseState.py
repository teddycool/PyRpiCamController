# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

#Parent-class for all state-loops
#https://en.wikipedia.org/wiki/State_pattern
import time

class BaseState(object):

    def __init__(self):
        return

    def initialize(self):
        self.lastUpdate= time.time()
        return

    def update(self, context):
        return

    def dispose(self):
        return