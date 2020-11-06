from typing import Callable


class Menu(object):

    def __init__(self, title = None, on_click: Callable = None):
        self.title = title
        self.on_click = on_click
        self._children = []

    def append(self, menu):
        self._children.append(menu)

    def remove(self, menu):
        self._children.remove(menu)

    def children(self):
        return self._children


class MenuSeparator(Menu):

    def __init__(self):
        Menu.__init__(self)