import logging
from typing import Dict, Set
from uuid import UUID
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    In-memory registry for active WebSocket connections.

    - user_connections: user_id -> set of active WebSocket connections
      (a user can have multiple tabs/devices connected at once)
    - workspace_members: workspace_id -> set of user_ids currently subscribed
      to that workspace's realtime updates
    """

    def __init__(self):
        self.user_connections: Dict[UUID, Set[WebSocket]] = {}
        self.workspace_members: Dict[UUID, Set[UUID]] = {}

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        self.user_connections.setdefault(user_id, set()).add(websocket)
        logger.info(f"WS connected: user={user_id} total_conns={len(self.user_connections[user_id])}")

    def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        conns = self.user_connections.get(user_id)
        if conns:
            conns.discard(websocket)
            if not conns:
                del self.user_connections[user_id]
        logger.info(f"WS disconnected: user={user_id}")

    def subscribe(self, user_id: UUID, workspace_id: UUID) -> None:
        self.workspace_members.setdefault(workspace_id, set()).add(user_id)

    def unsubscribe(self, user_id: UUID, workspace_id: UUID) -> None:
        members = self.workspace_members.get(workspace_id)
        if members:
            members.discard(user_id)
            if not members:
                del self.workspace_members[workspace_id]

    def get_user_connections(self, user_id: UUID) -> Set[WebSocket]:
        return self.user_connections.get(user_id, set())

    def get_workspace_members(self, workspace_id: UUID) -> Set[UUID]:
        return self.workspace_members.get(workspace_id, set())
    
   

    async def broadcast_to_workspace(self, workspace_id: UUID, message: dict) -> None:
        """
        Sends `message` to every active WebSocket connection belonging to
        users subscribed to this workspace. Dead connections encountered
        along the way are cleaned up from the registry.
     """
        user_ids = self.get_workspace_members(workspace_id)
        if not user_ids:
            return

        dead: list[tuple[UUID, WebSocket]] = []

        for user_id in user_ids:
            for websocket in self.get_user_connections(user_id):
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"Broadcast failed for user={user_id}: {e}")
                    dead.append((user_id, websocket))

        for user_id, websocket in dead:
            self.disconnect(user_id, websocket)
            logger.info(f"Pruned dead connection for user={user_id} during broadcast")
            
    def get_online_users(self, workspace_id: UUID) -> list[str]:
        """Returns user_ids currently connected and subscribed to this workspace."""
        return [str(uid) for uid in self.get_workspace_members(workspace_id)]
    
manager = ConnectionManager()