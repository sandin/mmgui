import sys, os
from mmgui import App, BrowserWindow

app = App(headless=False)
win = None

def open_file():
    files = win.show_file_dialog_for_file("打开文件", "Text File(*.txt)")
    if files and len(files) > 0:
        return files[0]
    return None

def on_create(ctx):
    global win
    win = BrowserWindow({
        "title": "Demo - mmgui",
        "width": 1200,
        "height": 800,
        "dev_mode": True,
    })
    win.webview.bind_function("open_file", open_file)
    win.webview.load_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html"))
    win.show()
app.on("create", on_create)
app.run()
