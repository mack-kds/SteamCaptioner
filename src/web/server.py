"""FastAPI web server for caption delivery."""

import asyncio
import threading
from pathlib import Path
from typing import Set, Dict, Optional
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn

from ..feeds.manager import get_feed_manager
from ..feeds.feed import Caption


# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for each feed."""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, feed_id: str):
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        if feed_id not in self.active_connections:
            self.active_connections[feed_id] = set()
        self.active_connections[feed_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, feed_id: str):
        """Remove a WebSocket connection."""
        if feed_id in self.active_connections:
            self.active_connections[feed_id].discard(websocket)
    
    async def broadcast_to_feed(self, feed_id: str, message: dict):
        """Broadcast a message to all connections for a feed."""
        if feed_id in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[feed_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for conn in dead_connections:
                self.active_connections[feed_id].discard(conn)
    
    async def broadcast_caption(self, feed_id: str, caption: Caption):
        """Broadcast a caption to all connections for a feed."""
        await self.broadcast_to_feed(feed_id, caption.to_dict())


# Global connection manager
manager = ConnectionManager()

# Create FastAPI app
app = FastAPI(title="StreamCaptioner", version="0.1.0")

# Static files directory
static_dir = Path(__file__).parent / "static"


@app.on_event("startup")
async def startup_event():
    """Initialize on server startup."""
    # Ensure static directory exists
    static_dir.mkdir(parents=True, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main page."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>StreamCaptioner</h1><p>Static files not found.</p>")


@app.get("/api/feeds")
async def list_feeds():
    """Get list of available feeds."""
    feed_manager = get_feed_manager()
    return {"feeds": feed_manager.get_all_feeds_info()}


@app.get("/api/feeds/{feed_id}")
async def get_feed(feed_id: str):
    """Get information about a specific feed."""
    feed_manager = get_feed_manager()
    feed = feed_manager.get_feed(feed_id)
    if feed:
        return {"feed": feed.to_dict()}
    return {"error": "Feed not found"}, 404


@app.get("/api/feeds/{feed_id}/history")
async def get_feed_history(feed_id: str, minutes: int = Query(default=10, ge=1, le=60)):
    """Get caption history for a feed."""
    feed_manager = get_feed_manager()
    feed = feed_manager.get_feed(feed_id)
    if feed:
        history = feed.get_history(minutes)
        return {"captions": [c.to_dict() for c in history]}
    return {"error": "Feed not found"}, 404


@app.get("/api/feeds/{feed_id}/current")
async def get_current_caption(feed_id: str):
    """Get the current caption for a feed."""
    feed_manager = get_feed_manager()
    feed = feed_manager.get_feed(feed_id)
    if feed:
        return {"text": feed.get_current_text(), "feed_id": feed_id}
    return {"error": "Feed not found"}, 404


@app.websocket("/ws/{feed_id}")
async def websocket_endpoint(websocket: WebSocket, feed_id: str):
    """WebSocket endpoint for real-time caption updates."""
    feed_manager = get_feed_manager()
    feed = feed_manager.get_feed(feed_id)

    if not feed:
        await websocket.close(code=4004, reason="Feed not found")
        return

    await manager.connect(websocket, feed_id)

    try:
        # Send caption history on connect (last 5 minutes, reversed so oldest first)
        history = feed.get_history(minutes=5)
        if history:
            # Send history marker so client knows this is historical data
            await websocket.send_json({
                "type": "history_start",
                "count": len(history)
            })

            # Send captions oldest first so they appear in correct order
            for caption in reversed(history):
                await websocket.send_json(caption.to_dict())

            await websocket.send_json({
                "type": "history_end"
            })

        # Keep connection alive and handle messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Handle ping/pong or other messages
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_text("ping")

    except WebSocketDisconnect:
        manager.disconnect(websocket, feed_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, feed_id)


# Mount static files after routes
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


async def broadcast_caption_async(feed_id: str, caption: Caption):
    """Broadcast caption to WebSocket clients (async)."""
    await manager.broadcast_caption(feed_id, caption)


def broadcast_caption(feed_id: str, caption: Caption):
    """Broadcast caption to WebSocket clients (sync wrapper)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(broadcast_caption_async(feed_id, caption))
        else:
            loop.run_until_complete(broadcast_caption_async(feed_id, caption))
    except RuntimeError:
        # Create new loop if needed
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(broadcast_caption_async(feed_id, caption))

