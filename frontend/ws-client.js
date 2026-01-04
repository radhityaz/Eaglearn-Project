/**
 * WebSocket Client with Heartbeat and Reconnection Support
 * Handles real-time streaming for gaze, pose, and stress data
 */

class WebSocketClient {
    constructor(channel, url) {
        this.channel = channel;
        this.url = url;
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.maxReconnectDelay = 30000; // Max 30 seconds
        this.isIntentionallyClosed = false;
        this.messageQueue = [];
        this.maxQueueSize = 100;
        this.listeners = {
            message: [],
            open: [],
            close: [],
            error: [],
            reconnecting: [],
            reconnected: []
        };
        this.heartbeatInterval = null;
        this.lastHeartbeatTime = Date.now();
    }

    connect() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            console.log(`[${this.channel}] Already connected`);
            return;
        }

        this.isIntentionallyClosed = false;
        
        try {
            this.socket = new WebSocket(this.url);
            this.setupEventHandlers();
        } catch (error) {
            console.error(`[${this.channel}] Connection error:`, error);
            this.scheduleReconnect();
        }
    }

    setupEventHandlers() {
        this.socket.onopen = () => {
            console.log(`[${this.channel}] Connected`);
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            
            // Start heartbeat
            this.startHeartbeat();
            
            // Send queued messages
            this.flushMessageQueue();
            
            // Notify listeners
            this.emit('open');
            
            if (this.reconnectAttempts > 0) {
                this.emit('reconnected');
            }
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.type === 'heartbeat') {
                    this.registerHeartbeat();
                    this.sendPong(data.timestamp);
                    return;
                }

                if (data.type === 'status' && data.channel === this.channel) {
                    this.emit('message', data);
                    return;
                }

                this.emit('message', data);
            } catch (error) {
                console.error(`[${this.channel}] Message parse error:`, error);
            }
        };

        this.socket.onclose = (event) => {
            console.log(`[${this.channel}] Disconnected:`, event.code, event.reason);
            this.stopHeartbeat();
            this.emit('close', event);
            
            if (!this.isIntentionallyClosed) {
                this.scheduleReconnect();
            }
        };

        this.socket.onerror = (error) => {
            console.error(`[${this.channel}] Error:`, error);
            this.emit('error', error);
        };
    }

    startHeartbeat() {
        this.registerHeartbeat();

        this.heartbeatInterval = setInterval(() => {
            const timeSinceLastHeartbeat = Date.now() - this.lastHeartbeatTime;
            if (timeSinceLastHeartbeat > 45000) {
                console.warn(`[${this.channel}] Heartbeat timeout, reconnecting...`);
                this.socket.close();
            }
        }, 10000); // Check every 10 seconds
    }

    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    registerHeartbeat() {
        this.lastHeartbeatTime = Date.now();
    }

    sendPong(timestamp) {
        this.registerHeartbeat();
        const pongMessage = {
            type: 'pong',
            timestamp: timestamp,
            client_timestamp: Date.now()
        };
        this.send(pongMessage);
    }

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error(`[${this.channel}] Max reconnection attempts reached`);
            this.emit('error', new Error('Max reconnection attempts reached'));
            return;
        }

        this.reconnectAttempts++;
        
        // Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 30s
        const delay = Math.min(
            this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
            this.maxReconnectDelay
        );

        console.log(`[${this.channel}] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        
        this.emit('reconnecting', {
            attempt: this.reconnectAttempts,
            maxAttempts: this.maxReconnectAttempts,
            delay: delay
        });

        setTimeout(() => {
            this.connect();
        }, delay);
    }

    send(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(data));
        } else {
            // Queue message if not connected
            if (this.messageQueue.length < this.maxQueueSize) {
                this.messageQueue.push(data);
            } else {
                console.warn(`[${this.channel}] Message queue full, dropping oldest message`);
                this.messageQueue.shift();
                this.messageQueue.push(data);
            }
        }
    }

    flushMessageQueue() {
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.send(message);
        }
    }

    close() {
        this.isIntentionallyClosed = true;
        this.stopHeartbeat();
        
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
    }

    on(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event].push(callback);
        }
    }

    off(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
        }
    }

    emit(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`[${this.channel}] Listener error:`, error);
                }
            });
        }
    }

    getState() {
        if (!this.socket) return 'CLOSED';
        
        switch (this.socket.readyState) {
            case WebSocket.CONNECTING: return 'CONNECTING';
            case WebSocket.OPEN: return 'OPEN';
            case WebSocket.CLOSING: return 'CLOSING';
            case WebSocket.CLOSED: return 'CLOSED';
            default: return 'UNKNOWN';
        }
    }
}

// Global WebSocket manager
window.eaglearnWS = {
    clients: {},
    
    init(baseUrl) {
        const base = baseUrl || window.wsConfig?.getBaseUrl?.() || 'ws://localhost:8000';
        const normalized = base.replace(/\/$/, '');
        this.clients.gaze = new WebSocketClient('gaze', `${normalized}/ws/gaze`);
        this.clients.pose = new WebSocketClient('pose', `${normalized}/ws/pose`);
        this.clients.stress = new WebSocketClient('stress', `${normalized}/ws/stress`);
    },
    
    connect(channel) {
        if (this.clients[channel]) {
            this.clients[channel].connect();
        }
    },
    
    connectAll() {
        Object.values(this.clients).forEach(client => client.connect());
    },
    
    disconnect(channel) {
        if (this.clients[channel]) {
            this.clients[channel].close();
        }
    },
    
    disconnectAll() {
        Object.values(this.clients).forEach(client => client.close());
    },
    
    on(channel, event, callback) {
        if (this.clients[channel]) {
            this.clients[channel].on(event, callback);
        }
    },
    
    send(channel, data) {
        if (this.clients[channel]) {
            this.clients[channel].send(data);
        }
    }
};

// Auto-initialize on load
if (typeof window !== 'undefined') {
    window.addEventListener('DOMContentLoaded', () => {
        window.eaglearnWS.init();
    });
}
