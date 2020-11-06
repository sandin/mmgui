// for nodejs
if (typeof(window) == "undefined") {
    window = {}
}

(function (window) {

    class RPC {

        constructor() {
            this._callbacks = {};
            this._callbackId = 0;
            this.proxy = undefined;
        }

        connect() {
            return new Promise((resolve, reject) => {
                new QWebChannel(qt.webChannelTransport, (channel) => {
                    //console.log("on qwebchancel connected", qt.webChannelTransport);
                    this.proxy = channel.objects.proxy;

                    this.proxy.on_message.connect(this._onMessage.bind(this));
                    resolve(this.proxy);
                });
            });
        }

        invokeSync(method, params) {
            console.log("RPC", "invoke", "method", method, "params", params);
            return new Promise((resolve, reject) => {
                if (typeof(this.proxy) == "undefined") {
                    this.connect().then((_) => {
                        this.proxy.invoke(method, JSON.stringify(params), (response) => {
                            console.log("RPC", "invoke", "method", method, "response", response);
                            resolve(response);
                        });
                    });
                } else {
                    this.proxy.invoke(method, JSON.stringify(params), (response) => {
                        console.log("RPC", "invoke", "method", method, "response", response);
                        resolve(response);
                    });
                }
            });
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
            //console.log("RPC", "invoke", "method=", method, ",params=", params);
            if (typeof(this.proxy) == "undefined") {
                this.connect().then((_) => {
                    this.proxy.post_message(callbackId, method, JSON.stringify(params));
                });
            } else {
                this.proxy.post_message(callbackId, method, JSON.stringify(params));
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
