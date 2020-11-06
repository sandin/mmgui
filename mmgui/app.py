import sys
import signal

from typing import NoReturn, Callable

from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import QApplication

import platform


class Context(object):
    pass


class App(Context):

    def __init__(self, headless: bool = False):
        self._headless = headless
        self._qt_application = None
        self._events_callback = {
            "create": [],
            "destroy": []
        }

    def on(self, event: str, callback: Callable[[Context], NoReturn]) -> NoReturn:
        if event not in self._events_callback:
            raise Exception("unsupported event %s" % event)
        self._events_callback[event].append(callback)

    def _notify_callback(self, event: str) -> NoReturn:
        if event not in self._events_callback:
            raise Exception("unsupported event %s" % event)
        for callback in self._events_callback[event]:
            callback(self)

    def on_create(self) -> NoReturn:
        self._notify_callback("create")

    def on_destroy(self) -> NoReturn:
        self._notify_callback("destroy")

    def run(self) -> int:
        platform.setup_stdio()
        platform.setup_console()

        argv = sys.argv[:]
        if self._headless:
            self._qt_application = QCoreApplication(argv)  # Non-GUI
            signal.signal(signal.SIGINT, lambda *a: self._qt_application.quit())
        else:
            self._qt_application = QApplication(argv)

        self.on_create() # -> create and show the WebView window
        exit_code = self._qt_application.exec_()
        self._qt_application.deleteLater()
        self.on_destroy()
        return exit_code
        #sys.exit(exit_code)

    def exit(self) -> NoReturn:
        self._qt_application.quit()
        self.on_destroy()
