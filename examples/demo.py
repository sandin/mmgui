import logging
import os
import sys

from mmgui import App, BrowserWindow, Menu, MenuSeparator

logging.basicConfig(level = logging.INFO,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = App(headless=False)
win = None


def move_window(dx, dy):
    win.move_by(dx, dy)


def close_window():
    win.close()


def toggle_maximized_window():
    if win.is_maximized():
        win.show_normal()
    else:
        win.show_maximized()


def show_minimized_window():
    win.show_minimized()


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

    window_menu = Menu(title="Window")
    window_menu.append(Menu(title="Min", on_click=lambda e: win.show_minimized()))
    window_menu.append(Menu(title="Normal", on_click=lambda e: win.show_normal()))
    window_menu.append(Menu(title="Max", on_click=lambda e: win.show_maximized()))
    window_menu.append(Menu(title="FullScreen", on_click=lambda e: win.show_full_screen()))
    menu.append(window_menu)

    help_menu = Menu(title="Help")
    help_menu.append(Menu(title="About", on_click=lambda e: print("about menu")))
    menu.append(help_menu)

    global win
    win = BrowserWindow({
        "title": "Demo - mmgui",
        "width": 1200,
        "height": 800,
        "dev_mode": True,
        #"frameless": True,
        #"menu": menu
    })
    win.webview.bind_function("echo", echo)
    win.webview.bind_function("toggle_maximized_window", toggle_maximized_window)
    win.webview.bind_function("show_minimized_window", show_minimized_window)
    win.webview.bind_function("close_window", close_window)
    win.webview.bind_function("move_window", move_window)
    win.webview.register_event_listener("on_url_changed", lambda e: print("on_url_changed, url=%s" % e.data))
    win.webview.register_event_listener("on_page_load_finished", lambda e: print("cookie %s" % win.webview.get_cookie(".baidu.com", "BAIDUID")))
    win.webview.load_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html"))
    print("app dir path %s" % app.get_application_dir_path())
    win.show()


def on_destroy(ctx):
    print("on_destroy")
    global win
    if win:
        win.close()
        win = None


app.on("create", on_create)
app.on("destroy", on_destroy)
exit_code = app.run()
print("sys.exit code=%d" % exit_code)
sys.exit(exit_code)
