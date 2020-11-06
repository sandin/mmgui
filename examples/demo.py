import sys, os
from mmgui import App, WebViewWindow, Menu, MenuSeparator

app = App(headless=False)
win = None


def echo(msg):
    return msg


def on_create(ctx):
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
    win = WebViewWindow({
        "width": 1200,
        "height": 800,
        "dev_mode": True,
        "menu": menu
    })
    win.bind_function("echo", echo)
    win.load_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html"))


def on_destroy(ctx):
    pass


app.on("create", on_create)
app.on("destroy", on_destroy)
exit_code = app.run()
sys.exit(exit_code)
