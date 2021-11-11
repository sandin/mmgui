import codecs
import json
import logging
import os
from typing import NoReturn, Callable, Any

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QUrl, QObject, pyqtSignal, pyqtSlot, QVariant, QDir, QEvent, QPoint, QMimeData
from PyQt5.QtWidgets import QMainWindow, QWidget, QMessageBox, QFileDialog, QShortcut
from PyQt5.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QKeyEvent, QKeySequence, QCloseEvent
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineScript, QWebEngineSettings
from PyQt5.QtWebChannel import QWebChannel

from .asyncqt import run_on_worker_thread
from .menu import MenuSeparator
from .webview_window_ui import Ui_WebViewWindowUI


g_default_configs = {
    "width": 800,
    "height": 600,
    "dev_mode": False,
    "frameless": False,
    "statusbar": False,
    "menu": None,
    "title": "mmgui"
}

logger = logging.getLogger("WebView")


class MyQWebEngineView(QWebEngineView):
    """
    QT doc:
    WebEngineView: https://doc.qt.io/qt-5/qwebengineview.html
    WebEnginePage: https://doc.qt.io/qt-5/qwebenginepage.html
    This version of Qt WebEngine is based on Chromium version 65.0.3325.151, with additional security fixes from newer versions.
    """

    def __init__(self, parent, drop_callback: Callable[[QDropEvent], None], dev_mode: bool):
        super(QWebEngineView, self).__init__(parent)
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


class MyQMainWindow(QMainWindow):

    def __init__(self, parent, on_close_callback: Callable):
        super(QMainWindow, self).__init__(parent)
        self._on_close_callback = on_close_callback

    def closeEvent(self, event: QCloseEvent):
        if self._on_close_callback:
            self._on_close_callback()


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

    @pyqtSlot(str, str, name='invoke', result=QVariant) # js -> py, sync call
    def invoke(self, function_name, params):
        if params:
            params = json.loads(params)
        else:
            params = {}
        result = None
        if function_name in self._function_map:
            result = self._function_map[function_name](**params)
        return result

    @pyqtSlot(str, str, str, name='post_message') # js -> py, ansync call(Callback or Promise)
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


class WebViewEvent(object):

    def __init__(self, type, data):
        self.type = type
        self.data = data


class BrowserWindow(object):

    def __init__(self, configs: dict):
        self._configs = {**g_default_configs, **configs}
        self._menus = []
        self._actions = []
        self._setup_ui()
        self._on_window_close_callback = None

    def _setup_ui(self) -> NoReturn:
        self._setup_main_window()
        self._setup_menus()
        self._setup_status_bar()
        self._setup_web_engine_view()
        self._setup_shortcut_keys()

    def _setup_main_window(self) -> NoReturn:
        self._main_window = MyQMainWindow(None, self._on_window_close)
        if self._configs['frameless']:
            self._main_window.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self._widget_ui = Ui_WebViewWindowUI()
        self._widget_ui.setupUi(self._main_window)
        self._main_window.setWindowTitle(self._configs['title'])
        if self._configs['width'] != -1 and self._configs['height'] != -1:
            self._main_window.resize(self._configs['width'], self._configs['height'])

    def get_main_window(self):
        return self._main_window

    def set_on_window_close_callback(self, callback):
        self._on_window_close_callback = callback

    def _on_window_close(self):
        if self._on_window_close_callback:
            self._on_window_close_callback()

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
        else:
            self._main_window.setMenuBar(None)

    def _find_action(self, title):
        for action in self._actions:
            print("menu loop", action.objectName())
            if action.objectName() == title:
                return action
        return None

    def set_menu_visible(self, menu_title, visible):
        action = self._find_action(menu_title)
        if action:
            action.setVisible(visible)

    def _setup_status_bar(self) -> NoReturn:
        if not self._configs['statusbar']:
            self._main_window.setStatusBar(None)

    def _setup_web_engine_view(self) -> NoReturn:
        self.webview = WebView(self._main_window, "webEngineView", self._configs['dev_mode'])
        self._widget_ui.verticalLayout.addWidget(self.webview.get_widget_view())
        if self._configs['dev_mode']:
            self._devtools_web_view = WebView(self._main_window, "webDevEngineView", False)
            self._widget_ui.verticalLayout_3.addWidget(self._devtools_web_view.get_widget_view())
            self.webview.set_web_dev_tools_page(self._devtools_web_view.get_web_engine_view_page()) # bind webEngineView with devTools
            self._widget_ui.consoleLogDockWidget.setVisible(True)
        else:
            self._widget_ui.consoleLogDockWidget.setVisible(False)

    def set_style_sheet(self,  style_sheet_dir) -> NoReturn:
        self._main_window.setStyleSheet(style_sheet_dir)

    def _setup_shortcut_keys(self):
        self._shortcut_refresh = QShortcut(QKeySequence('Ctrl+R'), self._main_window)
        self._shortcut_refresh.activated.connect(self._on_refresh_shortcut_key_pressed)
        self._shortcut_refresh2 = QShortcut(QKeySequence('F5'), self._main_window)
        self._shortcut_refresh2.activated.connect(self._on_refresh_shortcut_key_pressed)
        self._shortcut_fullscreen = QShortcut(QKeySequence('F11'), self._main_window)
        self._shortcut_fullscreen.activated.connect(self._on_fullscreen_shortcut_key_pressed)
        self._shortcut_devtools = QShortcut(QKeySequence('F12'), self._main_window)
        self._shortcut_devtools.activated.connect(self._on_devtools_shortcut_key_pressed)

    def _on_refresh_shortcut_key_pressed(self):
        self.webview.reload()

    def _on_devtools_shortcut_key_pressed(self):
        if self._widget_ui.consoleLogDockWidget.isVisible():
            self._widget_ui.consoleLogDockWidget.hide()
        else:
            self._widget_ui.consoleLogDockWidget.show()

    def _on_fullscreen_shortcut_key_pressed(self):
        if self._main_window.isFullScreen():
            self._main_window.showNormal()
        else:
            self._main_window.showFullScreen()

    def show(self) -> NoReturn:
        if self._configs['width'] != -1 and self._configs['height'] != -1:
            self._main_window.show()
        else:
            self._main_window.showMaximized()

    def show_maximized(self) -> NoReturn:
        self._main_window.showMaximized()

    def show_minimized(self) -> NoReturn:
        self._main_window.showMinimized()

    def show_normal(self) -> NoReturn:
        self._main_window.showNormal()

    def show_full_screen(self) -> NoReturn:
        self._main_window.showFullScreen()

    def is_maximized(self) -> bool:
        return self._main_window.windowState() == QtCore.Qt.WindowMaximized

    def is_full_screen(self) -> bool:
        return self._main_window.windowState() == QtCore.Qt.WindowFullScreen

    def move(self, x, y):
        self._main_window.move(x, y)

    def move_by(self, dx, dy):
        cur_pos: QPoint = self._main_window.pos()
        self._main_window.move(cur_pos.x() + dx, cur_pos.y() + dy)

    def close(self) -> NoReturn:
        if self.webview:
            self.webview.destroy()
        self._main_window.close()

    def show_alert_dialog(self, title: str, msg: str, cancelable: bool = True) -> bool:
        message_box = QMessageBox()
        message_box.setWindowTitle(title)
        message_box.setIcon(QMessageBox.Question)
        message_box.setText(msg)
        message_box.setStandardButtons((QMessageBox.Yes | QMessageBox.Cancel) if cancelable else QMessageBox.Yes)
        result = message_box.exec()
        return result == QMessageBox.Yes

    def show_file_dialog_for_save_file(self, filename: str, msg: str, filter: str) -> list:
        options = QFileDialog.Options()
        files = QFileDialog.getSaveFileName(None,
                                            msg,
                                            filename,
                                            filter=filter,
                                            options=options)
        return files

    def show_file_dialog_for_file(self, title: str, filter: str) -> list:
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(None,
                                                title,
                                                directory=QDir.homePath(),
                                                filter=filter,
                                                options=options)
        return files

    def show_file_dialog_for_dir(self, title: str) -> str:
        options = QFileDialog.Options()
        choose_dir = QFileDialog.getExistingDirectory(None,
                                                      title,
                                                      directory=QDir.homePath(),
                                                      options=options)
        return choose_dir


class WebView(object):

    def __init__(self, parent, object_name, dev_mode: bool):
        self._event_listeners = {}
        self._web_engine_view = None
        self._dev_mode = dev_mode
        self._object_name = object_name
        self._setup_web_engine_view(parent)
        self.move_window_func = None

    def _setup_web_engine_view(self, parent) -> NoReturn:
        self._web_engine_view = self._create_web_engine_view(parent, self._object_name)
        self._web_engine_view.urlChanged.connect(self._on_url_changed)
        self._web_engine_view.page().loadFinished.connect(self._on_page_load_finished)

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

    def register_web_channel_object(self, namespace: str, object: QObject) -> NoReturn:
        self._web_channel.registerObject(namespace, object)

    def get_web_engine_view(self):
        return self._web_engine_view

    def get_web_engine_view_page(self):
        return self._web_engine_view.page()

    def get_widget_view(self):
        return self._web_engine_view

    def register_event_listener(self, event_type: str, listener: Callable[[WebViewEvent], None]) -> NoReturn:
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(listener)

    def unregister_event_listener(self, event_type: str, listener: Callable[[WebViewEvent], None]) -> NoReturn:
        if event_type in self._event_listeners and self._event_listeners[event_type]:
            for item in self._event_listeners[event_type]:
                if item == listener:
                    self._event_listeners[event_type].remove(item)
                    break

    def _notify_event_listeners(self, event: WebViewEvent):
        event_type = event.type
        if event_type in self._event_listeners and self._event_listeners[event_type]:
            for listener in self._event_listeners[event_type]:
                listener(event)

    def _on_url_changed(self, qurl):
        logger.info("_on_url_changed %s", qurl.toString())
        self._notify_event_listeners(WebViewEvent("on_url_changed", qurl.toString()))

    def _on_page_load_finished(self, ok):
        logger.info("_on_page_load_finished %s", ok)
        self._notify_event_listeners(WebViewEvent("on_page_load_finished", ok))

    def _on_cookie_added(self, cookie):
        logger.info("_on_cookie_added %s", cookie)
        self._cookiesJar.add_cookie(cookie)

    def _on_cookie_removed(self, cookie):
        logger.info("_on_cookie_removed %s", cookie)
        self._cookiesJar.remove_cookie(cookie)

    def delete_all_cookies(self):
        self._web_engine_view.page().profile().cookieStore().deleteAllCookies()

    def get_cookie(self, domain, name):
        return self._cookiesJar.get_cookie(domain, name)

    def _create_web_engine_view(self, parent, object_name: str) -> QWebEngineView :
        web_engine_view = MyQWebEngineView(parent, lambda e: self._on_drop(e), self._dev_mode)
        settings = QWebEngineSettings.defaultSettings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        web_engine_view.setAutoFillBackground(False)
        web_engine_view.setStyleSheet("")
        web_engine_view.setUrl(QtCore.QUrl("about:blank"))
        web_engine_view.setObjectName(object_name)
        web_engine_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu) # 禁用右键菜单
        return web_engine_view

    def _on_drop(self, event: QDropEvent) -> NoReturn:
        pos = event.pos()
        mime_data = event.mimeData() # type:QMimeData
        files = []
        if mime_data.hasUrls():
            urls = mime_data.urls()
            for url in urls:
                files.append(url.toLocalFile())
        logging.info("files %s %s", files, pos)
        if self._web_bridge:
            event = {
                "files": files,
                "pos": [pos.x(), pos.y()]
            }
            self.send_message_to_js({"type": "onDrop", "event": event})

    def bind_function(self, js_function_name: str, py_function: Callable) -> NoReturn:
        self._web_bridge.bind_function(js_function_name, py_function)

    def send_message_to_js(self, msg: Any) -> NoReturn:
        self._web_bridge.send_message(msg)

    def run_javascript_code(self, javascript_code: str, callback: Callable[[Any], None]) -> NoReturn:
        self._web_engine_view.page().runJavaScript(javascript_code, callback)

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

    def load_url(self, url: str) -> NoReturn:
        self._web_engine_view.load(QUrl(url))

    def set_web_dev_tools_page(self, page) -> NoReturn:
        self._web_engine_view.page().setDevToolsPage(page)

    def reload(self):
        self._web_engine_view.reload()

    def destroy(self):
        self._web_engine_view.urlChanged.disconnect()
        self._web_engine_view.deleteLater()
        self._web_engine_view.close()


