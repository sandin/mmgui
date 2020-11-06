# MMGUI

Python GUI Library


## Install

```
# pip install mmgui
```

## Usage

```python
import sys, os
from mmgui import App, WebViewWindow

app = App(headless=False)
win = None
def on_create(ctx):
    global win
    win = WebViewWindow({
        "width": 1200,
        "height": 800
    })
    win.load_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html"))
app.on("create", on_create)
app.run()
```