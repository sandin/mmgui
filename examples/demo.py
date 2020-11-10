import logging
import os
import sys
import time

from mmgui import App, BrowserWindow, Menu, MenuSeparator

logging.basicConfig(level = logging.INFO,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = App(headless=False)
win = None
win2 = None


def echo(msg):
    return msg


def on_create(ctx):
    print("on_create")
    # menus
    menu = Menu()
    file_menu = Menu(title="File")
    file_menu.append(Menu(title="Open", on_click=lambda e: print("open file")))
    file_menu.append(MenuSeparator())
    file_menu.append(Menu(title="Exit", on_click=lambda e: app.exit()))
    menu.append(file_menu)
    help_menu = Menu(title="Help")
    help_menu.append(Menu(title="About", on_click=lambda e: print("about menu")))
    menu.append(help_menu)

    global win
    win = BrowserWindow({
        "width": 1200,
        "height": 800,
        "dev_mode": True,
        "menu": menu
    })
    win.webview.bind_function("echo", echo)
    win.webview.register_event_listener("on_url_changed", lambda e: print("on_url_changed, url=%s" % e.data))
    win.webview.register_event_listener("on_page_load_finished", lambda e: print("cookie %s" % win.webview.get_cookie(".baidu.com", "BAIDUID")))
    win.webview.load_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html"))
    print("app dir path %s" % app.get_application_dir_path())
    win.show()


def on_destroy(ctx):
    print("on_destroy")
    global win
    if win:
        win.destroy()
        win = None


app.on("create", on_create)
app.on("destroy", on_destroy)
exit_code = app.run()
print("sys.exit code=%d" % exit_code)
sys.exit(exit_code)
