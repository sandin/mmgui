import codecs
import json
import logging
import os
from typing import NoReturn, Callable, Any

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QUrl, QObject, pyqtSignal, pyqtSlot, QVariant
from PyQt5.QtWidgets import QMainWindow, QWidget
from PyQt5.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QKeyEvent
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineScript
from PyQt5.QtWebChannel import QWebChannel

from asyncqt import run_on_worker_thread
from .menu import MenuSeparator
from webview_window_ui import Ui_WebViewWindowUI


g_default_configs = {
    "width": 800,
    "height": 600,
    "dev_mode": False,
    "menu": None
}

logger = logging.getLogger("WebView")


class MyQWidget(QWidget):

    on_reload_hotkey = pyqtSignal(object) # Ctrl+R or F5 to reload

    def __init__(self, dev_mode):
        super(MyQWidget, self).__init__()
        self._dev_mode = dev_mode

    def keyPressEvent(self, event):
        if self._dev_mode:
            if (event.modifiers() & QtCore.Qt.ControlModifier and event.key() == QtCore.Qt.Key_R) or event.key() == QtCore.Qt.Key_F5:
                self.on_reload_hotkey.emit({})
        event.accept()


class MyQWebEngineView(QWebEngineView):
    """
    QT doc:
    WebEngineView: https://doc.qt.io/qt-5/qwebengineview.html
    WebEnginePage: https://doc.qt.io/qt-5/qwebenginepage.html
    This version of Qt WebEngine is based on Chromium version 65.0.3325.151, with additional security fixes from newer versions.
    """

    def __init__(self, parent, drop_callback: Callable[[QDropEvent], NoReturn], dev_mode: bool):
        super(MyQWebEngineView, self).__init__(parent)
        self._drop_callback = drop_callback
        self._dev_mode = dev_mode

    def dragEnterEvent(self, event: QDragEnterEvent):
        logger.info("dragEnterEvent %s", event)
        event.acceptProposedAction()

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        logger.info("dragLeaveEvent %s", event)

    def dropEvent(self, event: QDropEvent):
        logger.info("dropEvent %s", event)
        self._drop_callback(event)

    def keyPressEvent(self, event: QKeyEvent):
        if self._dev_mode and \
                ((event.modifiers() & QtCore.Qt.ControlModifier and event.key() == QtCore.Qt.Key_R) or event.key() == QtCore.Qt.Key_F5):
            self.reload()


class CookiesJar(object):

    def __init__(self):
        self._cookies = {}

    def add_cookie(self, cookie):
        domain = cookie.domain()
        name = cookie.name().data().decode("utf-8")
        value = cookie.value().data().decode("utf-8")
        logger.info("[WebView][CookiesJar] add cookie domain=%s, name=%s, value=%s", domain, name, value)
        if domain not in self._cookies:
            self._cookies[domain] = {}
        self._cookies[domain][name] = value

    def remove_cookie(self, cookie):
        domain = cookie.domain()
        name = cookie.name().data().decode("utf-8")
        logger.info("[WebView][CookiesJar] remove cookie domain=%s, name=%s", domain, name)
        try:
            if domain in self._cookies:
                del self._cookies[domain][name]
        except:
            pass

    def get_cookie(self, domain, name):
        value = None
        if domain in self._cookies and name in self._cookies[domain]:
            value = self._cookies[domain][name]
        logger.info("[WebView][CookiesJar] get cookie domain=%s, name=%s, value=%s", domain, name, value)
        return value


class WebViewBridge(QObject):

    on_message = pyqtSignal(str) # py -> js

    def __init__(self, webview_window):
        super().__init__()
        self._webview_window = webview_window
        self._function_map = {}

    def bind_function(self, js_function_name, py_function):
        print("bind_function %s " % js_function_name)
        self._function_map[js_function_name] = py_function

    def unbind_function(self, js_function_name):
        del self._function_map[js_function_name]

    @pyqtSlot(str, str, name='invoke', result=QVariant) # js -> py
    def invoke(self, function_name, params):
        if params:
            params = json.loads(params)
        else:
            params = {}
        result = None
        if function_name in self._function_map:
            result = self._function_map[function_name](**params)
        return result

    @pyqtSlot(str, str, str, name='post_message') # js -> py
    def js_post_message_to_py(self, callback_id, function_name, params):
        self.invoke_on_worker_thread(callback_id, function_name, params)

    @run_on_worker_thread
    def invoke_on_worker_thread(self, callback_id, function_name, params):
        result = self.invoke(function_name, params)
        self.py_reply_message_to_js(callback_id, result)

    def py_reply_message_to_js(self, callback_id, result):
        self.on_message.emit(json.dumps({ "callback_id": callback_id, "result": result}))

    def send_message(self, msg):
        #print("window python send message to js: %s" % str(msg))
        self.on_message.emit(json.dumps({ "callback_id": -1, "result": msg}))


class WebViewWindow(object):

    def __init__(self, configs: dict):
        self._configs = {**g_default_configs, **configs}
        self._menus = []
        self._actions = []
        self._setup_ui()

    def _setup_ui(self) -> NoReturn:
        self._setup_main_window()
        self._setup_menus()
        self._setup_web_engine_view()
        self._setup_web_dev_tools_view()

    def _setup_main_window(self) -> NoReturn:
        self._main_window = QMainWindow()
        self._widget_ui = Ui_WebViewWindowUI()
        self._widget_ui.setupUi(self._main_window)
        if self._configs['width'] != -1 and self._configs['height'] != -1:
            self._main_window.resize(self._configs['width'], self._configs['height'])

        """
        self._qt_menu = QtWidgets.QMenu(self._widget_ui.menubar)
        self._qt_menu.setObjectName("test menu")
        self._qt_menu.setTitle("test menu")
        self._widget_ui.menubar.addAction(self._qt_menu.menuAction())
        self._main_window.setMenuBar(self._widget_ui.menubar)
        """

    def _setup_menus(self) -> NoReturn:
        app_menu = self._configs['menu']
        if app_menu:
            menubar = self._widget_ui.menubar
            qt_menu = QtWidgets.QMenu(menubar)
            qt_menu.setObjectName("test menu")
            qt_menu.setTitle("test menu")

            for menu in app_menu.children():
                qt_menu = QtWidgets.QMenu(menubar)
                qt_menu.setObjectName(menu.title)
                qt_menu.setTitle(menu.title)
                menubar.addAction(qt_menu.menuAction())
                self._menus.append(qt_menu)
                for sub_menu in menu.children():
                    if sub_menu.on_click:
                        qt_action = QtWidgets.QAction(self._main_window)
                        qt_action.setObjectName(sub_menu.title)
                        qt_action.setText(sub_menu.title)
                        qt_action.triggered.connect(sub_menu.on_click)
                        self._actions.append(qt_action)
                        qt_menu.addAction(qt_action)
                    elif type(sub_menu) == MenuSeparator:
                        qt_menu.addSeparator()

            self._main_window.setMenuBar(menubar)

    def _setup_web_engine_view(self) -> NoReturn:
        self._web_engine_wrapper = MyQWidget(self._configs['dev_mode'])
        self._web_engine_view = self._create_web_engine_view(self._main_window, "webEngineView")
        self._web_engine_view.urlChanged.connect(self._on_url_changed)
        self._widget_ui.verticalLayout.addWidget(self._web_engine_view)

        # cookies
        self._cookiesJar = CookiesJar()
        self._web_engine_view.page().profile().cookieStore().cookieAdded.connect(self._on_cookie_added)
        self._web_engine_view.page().profile().cookieStore().cookieRemoved.connect(self._on_cookie_removed)

        # web channel
        self._web_channel = QWebChannel(self._web_engine_view.page())
        self._web_engine_view.page().setWebChannel(self._web_channel)
        self._web_bridge = WebViewBridge(self)
        self._web_channel.registerObject("proxy", self._web_bridge)

        # inject scripts
        self.inject_javascript_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "res", "js", "qwebchannel.js"))
        self.inject_javascript_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "res", "js", "mmgui.js"))

    def _on_url_changed(self, qurl):
        logging.info("[WebView] onUrlChanged %s", qurl.toString())

    def _on_cookie_added(self, cookie):
        self._cookiesJar.add_cookie(cookie)

    def _on_cookie_removed(self, cookie):
        self._cookiesJar.remove_cookie(cookie)

    def _setup_web_dev_tools_view(self) -> NoReturn:
        self._web_dev_tools_view = self._create_web_engine_view(self._main_window, "webDevEngineView")
        self._widget_ui.verticalLayout_3.addWidget(self._web_dev_tools_view)
        self._web_engine_view.page().setDevToolsPage(self._web_dev_tools_view.page()) # bind webEngineView with devTools

    def _create_web_engine_view(self, parent, object_name: str) -> QWebEngineView :
        web_engine_view = MyQWebEngineView(parent, lambda e: self._on_drop(e), self._configs['dev_mode'])
        web_engine_view.setAutoFillBackground(False)
        web_engine_view.setStyleSheet("")
        web_engine_view.setUrl(QtCore.QUrl("about:blank"))
        web_engine_view.setObjectName(object_name)
        web_engine_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu) # 禁用右键菜单
        return web_engine_view

    def _on_drop(self, event: QDropEvent) -> NoReturn:
        pass # TODO

    def bind_function(self, js_function_name: str, py_function: Callable) -> NoReturn:
        self._web_bridge.bind_function(js_function_name, py_function)

    def send_message_to_js(self, msg: Any) -> NoReturn:
        self._web_bridge.send_message(msg)

    def run_javascript_code(self, javascript_code: str) -> NoReturn:
        self._web_engine_view.page().runJavaScript(javascript_code)

    def inject_javascript_file(self, javascript_file: str) -> NoReturn:
        if not os.path.exists(javascript_file):
            raise Exception("javascript file is not exists, filename=%s" % javascript_file)

        script = QWebEngineScript()
        with codecs.open(javascript_file, "r", "utf-8") as f:
            script.setSourceCode(f.read())
        script.setName(os.path.basename(javascript_file))
        script.setWorldId(QWebEngineScript.MainWorld)
        script.setInjectionPoint(QWebEngineScript.DocumentCreation)
        script.setRunsOnSubFrames(False)

        profile = self._web_engine_view.page().profile() # type: QWebEngineProfile
        scripts = profile.scripts() # type: QWebEngineScriptCollection
        scripts.insert(script)
        logger.info("inject javascript file %s" % javascript_file)

    def load_file(self, filename: str) -> NoReturn:
        self._web_engine_view.load(QUrl.fromLocalFile(filename))
        self.show()

    def load_url(self, url: str) -> NoReturn:
        self._web_engine_view.load(QUrl(url))
        self.show()

    def reload(self):
        self._web_engine_view.reload()

    def destroy(self):
        self._web_engine_view.urlChanged.disconnect()
        self._web_engine_view.deleteLater()
        self._web_engine_view.close()

    def show(self) -> NoReturn:
        if self._configs['width'] != -1 and self._configs['height'] != -1:
            self._main_window.show()
        else:
            self._main_window.showMaximized()
