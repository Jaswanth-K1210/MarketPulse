"""
WebSocket Handler
Real-time alert broadcasting to connected clients
"""

from fastapi import WebSocket, WebSocketDisconnect
import logging
import json
from typing import List
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        """Initialize connection manager"""
        self.active_connections: List[WebSocket] = []
        logger.info("WebSocket Connection Manager initialized")

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")

        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.now().isoformat(),
            "message": "Connected to MarketPulse-X real-time alerts"
        })

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {str(e)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {str(e)}")
                disconnected.append(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_alert(self, alert_dict: dict):
        """Broadcast new alert to all clients"""
        message = {
            "type": "alert",
            "data": alert_dict,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Broadcasting alert to {len(self.active_connections)} clients")
        await self.broadcast(message)

    async def broadcast_opportunity(self, opportunity_dict: dict):
        """Broadcast new opportunity to all clients"""
        message = {
            "type": "opportunity",
            "data": opportunity_dict,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Broadcasting opportunity to {len(self.active_connections)} clients")
        await self.broadcast(message)

    async def broadcast_status(self, status: str, details: dict = None):
        """Broadcast system status update"""
        message = {
            "type": "status",
            "status": status,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }

        await self.broadcast(message)


# Create singleton instance
manager = ConnectionManager()


# WebSocket endpoint handler
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections"""
    await manager.connect(websocket)

    try:
        while True:
            # Receive messages from client (for future interactivity)
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get('type')

                # Handle different message types
                if message_type == 'ping':
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }, websocket)

                elif message_type == 'subscribe':
                    # Future: Handle subscription preferences
                    await manager.send_personal_message({
                        "type": "subscribed",
                        "message": "Subscription preferences updated",
                        "timestamp": datetime.now().isoformat()
                    }, websocket)

                else:
                    logger.warning(f"Unknown message type: {message_type}")

            except json.JSONDecodeError:
                logger.error("Received invalid JSON from client")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected normally")

    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket)
