import sys, os
from mmgui import App, BrowserWindow

app = App(headless=False)
win = None

def say_hi(msg):
    print("python say: %s" % msg)
    win.webview.send_message_to_js({"msg": "hello javascript"});
    return None

def on_create(ctx):
    global win
    win = BrowserWindow({
        "title": "Demo - mmgui",
        "width": 1200,
        "height": 800,
        "dev_mode": True,
    })
    win.webview.bind_function("say_hi", say_hi)
    win.webview.load_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html"))
    win.show()

app.on("create", on_create)
app.run()
