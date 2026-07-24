/**
 * WebSocketManager — Consolidated single connection for all components.
 * Replaces duplicate WS connections in living-interface, command-map, unified-timeline.
 */
class WebSocketManager {
    constructor() {
        this._ws = null;
        this._listeners = new Map();
        this._reconnectTimer = null;
        this._reconnectDelay = 1000;
        this._maxReconnectDelay = 30000;
        this._intentionalClose = false;
    }

    connect(url) {
        if (this._ws && (this._ws.readyState === WebSocket.OPEN || this._ws.readyState === WebSocket.CONNECTING)) {
            return;
        }

        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = url || `${protocol}//${location.host}/ws/agents`;
        this._intentionalClose = false;

        this._ws = new WebSocket(wsUrl);

        this._ws.onopen = () => {
            this._reconnectDelay = 1000;
            this._emit('open');
        };

        this._ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this._emit('message', data);
                if (data.type) {
                    this._emit(data.type, data);
                }
            } catch (_) {}
        };

        this._ws.onclose = () => {
            this._emit('close');
            if (!this._intentionalClose) {
                this._scheduleReconnect();
            }
        };

        this._ws.onerror = () => {
            this._emit('error');
        };
    }

    _scheduleReconnect() {
        clearTimeout(this._reconnectTimer);
        this._reconnectTimer = setTimeout(() => {
            this.connect();
            this._reconnectDelay = Math.min(this._reconnectDelay * 2, this._maxReconnectDelay);
        }, this._reconnectDelay);
    }

    on(event, callback) {
        if (!this._listeners.has(event)) {
            this._listeners.set(event, new Set());
        }
        this._listeners.get(event).add(callback);
        return () => this._listeners.get(event)?.delete(callback);
    }

    off(event, callback) {
        this._listeners.get(event)?.delete(callback);
    }

    _emit(event, ...args) {
        this._listeners.get(event)?.forEach(cb => {
            try { cb(...args); } catch (_) {}
        });
    }

    send(data) {
        if (this._ws && this._ws.readyState === WebSocket.OPEN) {
            this._ws.send(typeof data === 'string' ? data : JSON.stringify(data));
        }
    }

    close() {
        this._intentionalClose = true;
        clearTimeout(this._reconnectTimer);
        if (this._ws) {
            this._ws.close();
            this._ws = null;
        }
    }

    get connected() {
        return this._ws && this._ws.readyState === WebSocket.OPEN;
    }
}

window.JarvisWS = new WebSocketManager();
