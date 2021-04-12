import sys, os
from mmgui import App, BrowserWindow

def py_func(msg):
    return "hello javascript"

def main():
    app = App(headless=False)
    win = None
    def on_create(ctx):
        global win
        win = BrowserWindow({
            "title": "Demo - mmgui",
            "width": 1200,
            "height": 800,
            "dev_mode": True,
        })
        win.webview.bind_function("py_func", py_func)
        win.webview.load_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "index.html"))
        win.show()
    app.on("create", on_create)
    app.run()

if __name__ == "__main__":
    main()