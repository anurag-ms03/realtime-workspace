import asyncio
import logging
from typing import Optional
import aio_pika
from aio_pika import Connection, Channel
from aio_pika.abc import AbstractRobustConnection
from app.core.config import settings

logger = logging.getLogger(__name__)


class RabbitMQManager:
    """
    Manages a single robust RabbitMQ connection for the app lifetime.
    Uses aio_pika's RobustConnection — auto-reconnects on drop.
    """

    def __init__(self):
        self._connection: Optional[AbstractRobustConnection] = None
        self._channel: Optional[Channel] = None

    async def connect(self) -> None:
        """Call once at app startup."""
        logger.info("Connecting to RabbitMQ...")
        self._connection = await aio_pika.connect_robust(
            settings.RABBITMQ_URL,
            reconnect_interval=5,       # seconds between reconnect attempts
            heartbeat=60,
        )
        # One long-lived channel; publisher can open more if needed
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=10)
        logger.info("RabbitMQ connected ✓")

    async def disconnect(self) -> None:
        """Call once at app shutdown."""
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        logger.info("RabbitMQ disconnected.")

    async def get_channel(self) -> Channel:
        """
        Returns a fresh channel per operation — safer than sharing one channel
        across concurrent coroutines (channels are not thread/task safe).
        """
        if not self._connection or self._connection.is_closed:
            raise RuntimeError("RabbitMQ connection is not open. Was connect() called?")
        return await self._connection.channel()

    @property
    def is_connected(self) -> bool:
        return (
            self._connection is not None
            and not self._connection.is_closed
        )


# Module-level singleton — imported everywhere
rabbitmq_manager = RabbitMQManager()