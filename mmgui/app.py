import sys
import signal

from typing import NoReturn, Callable

from PyQt5.QtCore import QCoreApplication, QSettings
from PyQt5.QtWidgets import QApplication

from .platform import setup_stdio, setup_console


class Context(object):
    pass



class App(Context):

    def __init__(self, headless: bool = False, configs_file = None):
        self._headless = headless
        self._configs_file = configs_file
        self._settings : QSettings = None
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
        setup_stdio()
        setup_console()

        argv = sys.argv[:]
        if self._headless:
            self._qt_application = QCoreApplication(argv)  # Non-GUI
            signal.signal(signal.SIGINT, lambda *a: self._qt_application.quit())
        else:
            self._qt_application = QApplication(argv)

        # configs
        if self._configs_file:
            self._settings = QSettings(self._configs_file, QSettings.IniFormat)
            self._settings.sync()

        self._qt_application.aboutToQuit.connect(self._on_quit)
        self.on_create() # -> create and show the WebView window
        exit_code = self._qt_application.exec_()
        self._qt_application.deleteLater()
        return exit_code
        #sys.exit(exit_code)

    def get_config(self, key, def_val = None):
        if self._settings:
            return self._settings.value(key, def_val)
        return def_val

    def _on_quit(self):
        self.on_destroy()

    def exit(self) -> NoReturn:
        self._qt_application.quit()

    def get_application_dir_path(self):
        return self._qt_application.applicationDirPath()
