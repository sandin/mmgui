import logging
import traceback
from functools import wraps

from PyQt5.QtCore import QObject, pyqtSignal, QThreadPool, QRunnable, pyqtSlot

"""
asyncqt USAGE:
------------------------------------------------------
class DemoController(object):

    def on_refresh_btn_click(self):
        id = 1
        self._load_data_in_background(id)

    @run_on_worker_thread
    def _load_data_in_background(self, id):
        logging.info("_load_data_in_background start, id=" + str(id))
        time.sleep(1) # do some worker in background
        data = ["1", "2", "3"]
        logging.info("_load_data_in_background end")
        self._refresh_ui(data)

    @run_on_ui_thread
    def _refresh_ui(self, data):
        logging.info("_refresh_ui data: " + str(data))
------------------------------------------------------
"""


class UIThreadLoop(QObject):
    _msg_signal = pyqtSignal(tuple)

    def start_loop(self):
        self._msg_signal.connect(self._on_msg)

    def _on_msg(self, async_function):
        #logging.info("[UIThreadLoop] on msg, async_function=%s" % str(async_function))
        func = async_function[0]
        args = async_function[1]
        kwargs = async_function[2]
        func(*args, **kwargs)

    def _send_msg(self, async_function):
        #logging.info("[UIThreadLoop] send msg %s" % str(async_function))
        self._msg_signal.emit(async_function)

    def run_on_ui_thread(self, func, *args, **kwargs):
        async_function = (func, args, kwargs)
        self._send_msg(async_function)


class WorkerRunnable(QRunnable):

    def __init__(self, fn, *args, **kwargs):
        super(WorkerRunnable, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        #logging.info("[WorkerRunnable] fn=%s, args=%s, kwargs=%s" % (str(self.fn), str(self.args), str(self.kwargs)))
        try:
            self.fn(*self.args, **self.kwargs)
        except Exception as e:
            traceback.print_exc()
            logging.exception(e)


class WorkerThreadExecutor(object):

    _thread_pool = QThreadPool()

    def __init__(self):
        self._thread_pool.setMaxThreadCount(20)
        self._thread_pool.setExpiryTimeout(30 * 1000) # default: 30seconds

    def execute(self, func, *args, **kwargs):
        runnable = WorkerRunnable(func, *args, **kwargs)
        self._thread_pool.start(runnable)


asyncqt_ui_thread_loop = UIThreadLoop()
asyncqt_worker_thread_executor = WorkerThreadExecutor()

def run_on_ui_thread(func):
    def wrapper(*args, **kwargs):
        asyncqt_ui_thread_loop.run_on_ui_thread(func, *args, **kwargs)
    return wrapper

def run_on_worker_thread(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        asyncqt_worker_thread_executor.execute(func, *args, **kwargs)
    return wrapper




