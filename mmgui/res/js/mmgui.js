// for nodejs
if (typeof(window) == "undefined") {
    window = {}
}

(function (window) {

    const RPCState = {
        NOT_CONNECTED : 0,
        CONNECTING : 1,
        CONNECTED : 2
    }

    class RPC {

        constructor() {
            this._callbacks = {};
            this._callbackId = 0;
            this.proxy = undefined;
            this._state = RPCState.NOT_CONNECTED;
        }

        connect() {
            this._state = RPCState.CONNECTING;
            return new Promise((resolve, reject) => {
                new QWebChannel(qt.webChannelTransport, (channel) => {
                    //console.log("on qwebchancel connected", qt.webChannelTransport, channel);
                    this.proxy = channel.objects.proxy;

                    this.proxy.on_message.connect(this._onMessage.bind(this));
                    resolve(this.proxy);
                    this._state = RPCState.CONNECTED;
                });
            });
        }

        invokeSync(method, params, callback) {
            //console.log("RPC", "invoke", "method", method, "params", params);
            //return new Promise((resolve, reject) => {
                if (typeof(this.proxy) == "undefined") {
                    this.connect().then((_) => {
                        this.proxy.invoke(method, JSON.stringify(params), callback);
                    });
                } else {
                    this.proxy.invoke(method, JSON.stringify(params), callback);
                }
            //});
        }

        invoke(method, params, callback) {
            return new Promise((resolve, reject) => {
                this.invokeCallback(method, params, (result) => {
                    resolve(result);
                });
            });
        }

        invokeCallback(method, params, callback) {
            const callbackId = ++this._callbackId;
            this._callbacks[callbackId] = callback;
            //console.log("RPC", "invoke", "method=", method, ",params=", params, ",callbackId=", callbackId);

            if (this._state == RPCState.NOT_CONNECTED) {
                this.connect().then((_) => {
                    this.proxy.post_message(callbackId, method, JSON.stringify(params));
                });
            } else if (this._state == RPCState.CONNECTING) {
                setTimeout(() => {
                    if (this.proxy) {
                        this.proxy.post_message(callbackId, method, JSON.stringify(params));
                    }
                }, 300); // TODO: wait connecting
            } else if (this._state == RPCState.CONNECTED) {
                this.proxy.post_message(callbackId, method, JSON.stringify(params));
            } else {
                console.error("invalid state", this._state);
            }
        }

        _onMessage(message) {
            message = message && JSON.parse(message);
            //console.log("RPC", "onMessage", message);
            if (!message) {
                console.error("rpc response message is null");
            }
            if (typeof(this._callbacks[[message.callback_id]]) != "undefined") { // response from rpc call
                const callback = this._callbacks[[message.callback_id]];
                callback(message.result);
                delete this._callbacks[[message.callback_id]];
            } else { // broadcast
                var event = document.createEvent('Event');
                event.initEvent('message', false, true);
                event.data = message.result;
                window.dispatchEvent(event); // window.addEventListener('message', event => { });
            }
        }
    }

    window.RPC = new RPC();
    //required for use with nodejs
    if (typeof module === 'object') {
        module.exports.rpc = window.rpc;
    }

})(window);

(function (window) {

    function isRectHint(rect, x, y) {
        return rect.left <= x && x < rect.right
             && rect.top <= y && y < rect.bottom;
    }

    class DragAndDropHelper {
        constructor() {
            this._onMessage = this._onMessage.bind(this);
            window.addEventListener("message", this._onMessage)
            this._elements = [];
        }

        _onMessage(event) {
            if (event && event.data) {
                var data = event.data;
                if (typeof(data.type) != "undefined") {
                    if (data.type == "onDrop") {
                        console.log("DragAndDropHelper", "onDrop", data.event)
                        const x = data.event.pos[0];
                        const y = data.event.pos[1];
                        this._notifyElements(x, y, "qtDrop", data.event.files);
                    }
                }
            }
        }

        _walkDomTree(node, func) {
            if (node) {
                var consumed = func(node);
                if (!consumed) {
                    var childCount = node.childNodes.length;
                    if (childCount > 0) {
                        for (var i = 0; i < childCount; i++) {
                            var child = node.childNodes[i];
                            if (child.nodeType == 1) {
                                consumed = this._walkDomTree(child, func)
                                if (consumed) {
                                    break
                                }
                            }
                        }
                    }
                }
            }
        }

        _notifyElements(x, y, eventType, eventData) {
            var nodeStack = [];
            this._walkDomTree(document.body, (node) => {
                var hint = isRectHint(node.getBoundingClientRect(), x, y);
                if (hint) {
                    nodeStack.push(node);
                }
                return !hint;
            });

            if (nodeStack.length == 0) {
                return;
            }

            var event = document.createEvent('Event');
            event.initEvent(eventType, false, true);
            event.data = eventData;

            for (var key in nodeStack) {
                var domElement = nodeStack[key];
                domElement.dispatchEvent(event);
                console.log("DragAndDropHelper", "notifyEvent", event.composed, domElement, x, y);
                // TODO: event consumed and break
            }
        }

        registerDropEvent(domElement) {
            console.log("DragAndDropHelper", "registerDropEvent", domElement);
            this._elements.push(domElement);

        }

        unregisterDropEvent(domElement) {
            console.log("DragAndDropHelper", "unregisterDropEvent", domElement);
            var index = this._elements.indexOf(domElement);
            if (index != -1) {
                delete this._elements[index];
            }
        }
    }

    window.DragAndDropHelper = new DragAndDropHelper();

    //required for use with nodejs
    if (typeof module === 'object') {
        module.exports.DragAndDropHelper = window.DragAndDropHelper;
    }
})(window);
