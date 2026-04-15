# backend/websocket_manager.py

import logging
from typing import List
from fastapi import WebSocket

# --- Import Logger ---
from backend.utils.logger import setup_logger

# Initialize Logger
logger = setup_logger("WebSocketManager", log_file="logs/websocket.log", level=logging.DEBUG)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        logger.info("SYSTEM: WebSocket Manager Initialized.")

    async def connect(self, websocket: WebSocket):
        """
        Accepts a new WebSocket connection and logs it.
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Extract client info for logs (IP:Port)
        client_info = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "Unknown"
        logger.info(f"WS CONNECT: Client {client_info} connected. Total Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """
        Removes a connection from the active list.
        """
        client_info = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "Unknown"
        
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WS DISCONNECT: Client {client_info} disconnected. Total Active: {len(self.active_connections)}")
        else:
            logger.warning(f"WS WARNING: Attempted to disconnect {client_info}, but it was not in the active list.")

    async def broadcast(self, message: str):
        """
        Sends a message to all connected clients.
        Logs the payload size and success count.
        Dead connections are removed automatically on send failure.
        """
        if not self.active_connections:
            logger.debug(f"WS BROADCAST ABORTED: No active clients to receive.")
            return

        logger.debug(f"WS BROADCASTING: To {len(self.active_connections)} clients. Payload: '{message[:100]}'")

        dead_connections = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"WS SEND ERROR: Failed to send to a client. Reason: {e}")
                dead_connections.append(connection)

        for connection in dead_connections:
            self.disconnect(connection)

# Create the single, global instance that the rest of our application will import and use.
manager = ConnectionManager()