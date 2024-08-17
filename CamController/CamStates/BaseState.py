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