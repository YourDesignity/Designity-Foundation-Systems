const WS_URL = 'ws://127.0.0.1:8000/ws'; 

class WebSocketService {
    constructor() {
        this.socket = null;
        this.reconnectTimer = null;    
        this.shouldReconnect = false;   // Changed from true - don't auto-connect
        this.onMessageCallback = null;
    }

    connect() {
        if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
            console.log('🔌 WebSocket: Already connected');
            return;
        }

        // Check for token before connecting
        const token = localStorage.getItem('access_token');
        if (!token) {
            console.warn('⚠️ WebSocket: No token found, cannot connect');
            return;
        }

        try {
            console.log('🔌 WebSocket: Attempting connection...');
            this.socket = new WebSocket(WS_URL);

            this.socket.onopen = () => {
                console.log('✅ WebSocket Connected');
                this.shouldReconnect = true; // Enable reconnection after successful connection
            };

            this.socket.onmessage = (event) => {
                if (this.onMessageCallback) {
                    try {
                        const data = JSON.parse(event.data);
                        this.onMessageCallback(data);
                    } catch (e) {
                        console.error("WS Parse Error", e);
                    }
                }
            };

            this.socket.onclose = () => {
                console.log('🔌 WebSocket: Connection closed');
                if (this.shouldReconnect) {
                    console.log('🔄 WebSocket Reconnecting in 5s...');
                    clearTimeout(this.reconnectTimer);
                    this.reconnectTimer = setTimeout(() => this.connect(), 5000);
                }
            };

            this.socket.onerror = (err) => {
                console.error("⚠️ WebSocket Error:", err);
                this.socket.close();
            };
        } catch (e) {
            console.error("WS Connection Exception", e);
        }
    }

    register(callback) {
        this.onMessageCallback = callback;
        // Don't call connect() here - it's now called explicitly from AuthContext after login
    }

    disconnect() {
        console.log('🔌 WebSocket: Disconnecting...');
        this.shouldReconnect = false;
        clearTimeout(this.reconnectTimer);
        if (this.socket) {
            this.socket.close(1000, 'Logout');
            this.socket = null;
        }
    }

    unregister() {
        this.shouldReconnect = false;
        clearTimeout(this.reconnectTimer);
        if (this.socket) {
            this.socket.close();
        }
        this.socket = null;
    }
}

const websocketService = new WebSocketService();
export default websocketService;