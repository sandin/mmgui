# MMGUI

Python GUI Library


## Install

```
# pip install mmgui
```

## Usage

```python
import sys, os
from mmgui import App, BrowserWindow

def py_func():
    return "hi from py"

app = App(headless=False)
win = None
def on_create(ctx):
    global win
    win = BrowserWindow({
        "title": "Demo - mmgui",
        "width": 1200,
        "height": 800
    })
    win.webview.bind_function("py_func", py_func)
    win.webview.load_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html"))
    win.show()
app.on("create", on_create)
app.run()
```

See [wiki](../../wiki) or [examples](../../tree/master/examples) for more details.



