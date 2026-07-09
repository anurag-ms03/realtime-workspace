import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.db.session import SessionLocal
from app.ws.auth import authenticate_ws_token
from app.ws.manager import manager
from app.models.workspace import WorkspaceMember

logger = logging.getLogger(__name__)

router = APIRouter()

WS_CLOSE_UNAUTHORIZED = 4001


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    await websocket.accept()  # accept first so we can always send a proper close code

    db = SessionLocal()
    try:
        user = authenticate_ws_token(token, db)
        if not user:
            await websocket.close(code=WS_CLOSE_UNAUTHORIZED)
            return

        workspace_ids = [
            row.workspace_id
            for row in db.query(WorkspaceMember.workspace_id)
            .filter(WorkspaceMember.user_id == user.id)
            .all()
        ]
    finally:
        db.close()

    await manager.connect(user.id, websocket)
    for workspace_id in workspace_ids:
        manager.subscribe(user.id, workspace_id)
        await manager.broadcast_to_workspace(
            workspace_id,
            {"type": "presence.online", "payload": {"user_id": str(user.id)}},
        )

    logger.info(f"WS session started: user={user.id} workspaces={workspace_ids}")

    try:
        while True:
            try:
                data = await websocket.receive_text()
                logger.info(f"WS message from user={user.id}: {data}")
            except WebSocketDisconnect:
                raise
            except Exception as e:
                logger.warning(f"WS receive error for user={user.id}: {e}")
                break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user.id, websocket)
        for workspace_id in workspace_ids:
            manager.unsubscribe(user.id, workspace_id)
            if not manager.get_user_connections(user.id):
                await manager.broadcast_to_workspace(
                    workspace_id,
                    {"type": "presence.offline", "payload": {"user_id": str(user.id)}},
                )
        logger.info(f"WS session ended: user={user.id}")