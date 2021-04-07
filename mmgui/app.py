import sys
# import signal

from typing import NoReturn, Callable

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import QCoreApplication, QSettings
from PyQt5.QtWidgets import QApplication, QSplashScreen

from .platform import setup_stdio, setup_console, run_as_job, STDOUT_STREAMS, STDERR_STREAMS
from .asyncqt import asyncqt_ui_thread_loop


class Context(object):
    pass



class App(Context):

    def __init__(self,
                 headless: bool = False,
                 icon_file = None,
                 splash_file = None,
                 splash_text = None,
                 configs_file = None,
                 log_file = None
                 ):
        self._headless = headless
        self._configs_file = configs_file
        self._icon_file = icon_file
        self._splash_file = splash_file
        self._splash_text = splash_text
        self._log_file = log_file
        self._settings : QSettings = None
        self._qt_application = None
        self._events_callback = {
            "create": [],
            "destroy": []
        }

    def on(self, event: str, callback: Callable[[Context], None]) -> NoReturn:
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
        run_as_job()

        argv = sys.argv[:]
        if self._headless:
            self._qt_application = QCoreApplication(argv)  # Non-GUI
            if sys.platform == 'linux':
                import signal
                signal.signal(signal.SIGINT, lambda *a: self._qt_application.quit())
        else:
            self._qt_application = QApplication(argv)

            # icon
            if self._icon_file:
                self._window_icon = QtGui.QIcon(self._icon_file)
                self._qt_application.setWindowIcon(self._window_icon)

            # splash
            if self._splash_file:
                pixmap = QtGui.QPixmap(self._splash_file)
                self._splash = QSplashScreen(pixmap)
                if self._splash_text:
                    self._set_splash_text(self._splash_text, "#ffffff")
                self._splash.show()

        # asyncqt
        asyncqt_ui_thread_loop.start_loop()

        # configs
        if self._configs_file:
            self._settings = QSettings(self._configs_file, QSettings.IniFormat)
            self._settings.sync()

        # log
        if self._log_file:
            if sys.platform == 'win32':
                logfp = open(self._log_file, 'w')
                STDERR_STREAMS.add(logfp)
                STDOUT_STREAMS.add(logfp)
            else:
                logfp = open(self._log_file, 'a')
                sys.stdout = logfp
                sys.stderr = logfp
        self._qt_application.aboutToQuit.connect(self._on_quit)
        self.on_create() # -> create and show the WebView window
        exit_code = self._qt_application.exec_()
        self._qt_application.deleteLater()
        return exit_code
        #sys.exit(exit_code)

    def _set_splash_text(self, text, color):
        self._splash.showMessage(text, alignment=QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom, color=QtGui.QColor(color))

    def set_main_window(self, window):
        if window:
            self._splash.finish(window)
            window.setWindowIcon(self._window_icon)

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

    def get_headless(self):
        return self._headless
