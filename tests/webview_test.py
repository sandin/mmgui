from mmgui import WebView, BrowserWindow


def test_load_url(qtbot):
    target_url = "http://www.baidu.com"
    webview = WebView(None, "testWebEngineView", True)
    qtbot.addWidget(webview.get_web_engine_view())
    with qtbot.waitCallback() as cb:
        def on_url_changed(url):
            print("on_page_load_finished")
            assert url == target_url
            cb(1)
        webview.register_event_listener("on_url_changed", on_url_changed)
        webview.load_url(target_url)
    cb.assert_called_with(1)
    webview.destroy()


def test_get_cookie(qtbot):
    webview = WebView(None, "testWebEngineView", True)
    qtbot.addWidget(webview.get_web_engine_view())
    with qtbot.waitCallback() as cb:
        def on_page_load_finished(event):
            print("on_page_load_finished")
            cookie = webview.get_cookie(".baidu.com", "BAIDUID")
            print("cookie: %s" % cookie)
            assert cookie is not None
            cb(1)
        webview.register_event_listener("on_page_load_finished", on_page_load_finished)
        webview.load_url("http://www.baidu.com")
    cb.assert_called_with(1)
    webview.destroy()


def test_run_javascript_code(qtbot):
    webview = WebView(None, "testWebEngineView", True)
    qtbot.addWidget(webview.get_web_engine_view())
    with qtbot.waitCallback(timeout=60*1000) as cb:
        def on_page_load_finished(event):
            print("on_page_load_finished")
            def callback(e):
                cb(1)
            webview.run_javascript_code("alert(1)", callback)
        webview.register_event_listener("on_page_load_finished", on_page_load_finished)
        webview.load_url("http://www.baidu.com")
    cb.assert_called_with(1)
    webview.destroy()


def test_show_alert_dialog(qtbot):
    win = BrowserWindow({})
    win.show()
    win.show_alert_dialog("title", "content")


def test_show_file_dialog_for_dir(qtbot):
    win = BrowserWindow({})
    win.show()
    win.show_file_dialog_for_dir("title")


def test_show_file_dialog_for_file(qtbot):
    win = BrowserWindow({})
    win.show()
    win.show_file_dialog_for_file("title", "*.txt")


def test_show_file_dialog_for_save_file(qtbot):
    win = BrowserWindow({})
    win.show()
    win.show_file_dialog_for_save_file("filename", "content", "*.txt")