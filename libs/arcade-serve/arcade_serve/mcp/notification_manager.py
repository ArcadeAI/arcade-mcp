"""
MCP Notification Manager

Centralized component for managing notifications across all transport types.
Handles subscription management, rate limiting, debouncing, and delivery.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from logging import getLogger
from typing import Any, Protocol

from arcade_serve.mcp.types import (
    CancelledNotification,
    CancelledNotificationParams,
    EnhancedProgressNotification,
    EnhancedProgressNotificationParams,
    LoggingMessageNotification,
    LoggingMessageNotificationParams,
    LogLevel,
    Notification,
    NotificationCapability,
    NotificationSubscription,
    ProgressToken,
    ResourceListChangedNotification,
    ResourceListChangedNotificationParams,
    ResourceUpdatedNotification,
    ResourceUpdatedNotificationParams,
    ToolListChangedNotification,
    ToolListChangedNotificationParams,
)

logger = getLogger("arcade.mcp.notifications")


class NotificationType(str, Enum):
    """Supported notification types."""

    INITIALIZED = "notifications/initialized"
    PROGRESS = "notifications/progress"
    RESOURCE_LIST_CHANGED = "notifications/resources/list_changed"
    RESOURCE_UPDATED = "notifications/resources/updated"
    TOOL_LIST_CHANGED = "notifications/tools/list_changed"
    MESSAGE = "notifications/message"
    CANCELLED = "notifications/cancelled"


class NotificationSender(Protocol):
    """Protocol for sending notifications to clients."""

    async def send_notification(
        self, client_id: str, notification: dict[str, Any]
    ) -> bool:
        """Send a notification to a specific client.

        Args:
            client_id: The client/session ID
            notification: The notification data

        Returns:
            True if successfully sent, False otherwise
        """
        ...


@dataclass
class NotificationClient:
    """Represents a connected client with notification capabilities."""

    client_id: str
    capabilities: list[NotificationCapability]
    subscriptions: dict[str, NotificationSubscription] = field(default_factory=dict)
    last_notification: float = field(default_factory=time.time)
    notification_count: int = 0
    rate_limit_window_start: float = field(default_factory=time.time)
    rate_limit_count: int = 0


@dataclass
class DebouncedNotification:
    """Represents a debounced notification waiting to be sent."""

    notification: Notification
    clients: set[str]
    created_at: float
    send_after: float


class NotificationManager:
    """
    Manages MCP notifications with rate limiting, debouncing, and subscription management.
    """

    def __init__(
        self,
        sender: NotificationSender,
        rate_limit_per_minute: int = 60,
        default_debounce_ms: int = 100,
        max_queued_notifications: int = 1000,
    ):
        """
        Initialize the notification manager.

        Args:
            sender: The notification sender implementation
            rate_limit_per_minute: Maximum notifications per minute per client
            default_debounce_ms: Default debounce time in milliseconds
            max_queued_notifications: Maximum queued notifications per client
        """
        self.sender = sender
        self.rate_limit_per_minute = rate_limit_per_minute
        self.default_debounce_ms = default_debounce_ms
        self.max_queued_notifications = max_queued_notifications

        # Client management
        self.clients: dict[str, NotificationClient] = {}
        self.clients_lock = asyncio.Lock()

        # Debouncing
        self.debounced: dict[str, DebouncedNotification] = {}
        self.debounce_lock = asyncio.Lock()

        # Background tasks
        self._tasks: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        """Start the notification manager background tasks."""
        if self._running:
            return

        self._running = True
        self._tasks.append(
            asyncio.create_task(self._process_debounced_notifications())
        )
        self._tasks.append(asyncio.create_task(self._cleanup_inactive_clients()))
        logger.info("Notification manager started")

    async def stop(self) -> None:
        """Stop the notification manager and clean up."""
        self._running = False

        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        # Clear all pending notifications
        async with self.debounce_lock:
            self.debounced.clear()

        logger.info("Notification manager stopped")

    async def register_client(
        self,
        client_id: str,
        capabilities: list[NotificationCapability] | None = None,
    ) -> None:
        """
        Register a new client for notifications.

        Args:
            client_id: Unique client identifier
            capabilities: Client's notification capabilities
        """
        async with self.clients_lock:
            self.clients[client_id] = NotificationClient(
                client_id=client_id,
                capabilities=capabilities or [],
            )
            logger.debug(
                f"Registered client {client_id} with {len(capabilities or [])} capabilities"
            )

    async def unregister_client(self, client_id: str) -> None:
        """
        Unregister a client and clean up its subscriptions.

        Args:
            client_id: Client identifier to unregister
        """
        async with self.clients_lock:
            if client_id in self.clients:
                del self.clients[client_id]
                logger.debug(f"Unregistered client {client_id}")

    async def subscribe(
        self,
        client_id: str,
        notification_types: list[str],
        filters: dict[str, Any] | None = None,
    ) -> list[NotificationSubscription]:
        """
        Subscribe a client to notification types.

        Args:
            client_id: Client identifier
            notification_types: List of notification methods to subscribe to
            filters: Optional filters for notifications

        Returns:
            List of created subscriptions
        """
        async with self.clients_lock:
            client = self.clients.get(client_id)
            if not client:
                raise ValueError(f"Client {client_id} not registered")

            subscriptions = []
            for notification_type in notification_types:
                # Check if client has capability for this notification type
                if any(
                    cap.method == notification_type for cap in client.capabilities
                ):
                    subscription_id = str(uuid.uuid4())
                    subscription = NotificationSubscription(
                        subscription_id=subscription_id,
                        method=notification_type,
                        created_at=time.time(),
                        filters=filters,
                    )
                    client.subscriptions[subscription_id] = subscription
                    subscriptions.append(subscription)
                    logger.debug(
                        f"Client {client_id} subscribed to {notification_type}"
                    )
                else:
                    logger.warning(
                        f"Client {client_id} lacks capability for {notification_type}"
                    )

            return subscriptions

    async def unsubscribe(self, client_id: str, subscription_ids: list[str]) -> bool:
        """
        Unsubscribe a client from specific subscriptions.

        Args:
            client_id: Client identifier
            subscription_ids: List of subscription IDs to remove

        Returns:
            True if all unsubscriptions were successful
        """
        async with self.clients_lock:
            client = self.clients.get(client_id)
            if not client:
                return False

            success = True
            for sub_id in subscription_ids:
                if sub_id in client.subscriptions:
                    del client.subscriptions[sub_id]
                    logger.debug(f"Client {client_id} unsubscribed from {sub_id}")
                else:
                    success = False

            return success

    async def notify_progress(
        self,
        progress_token: ProgressToken,
        progress: float,
        total: float | None = None,
        message: str | None = None,
        client_ids: list[str] | None = None,
        debounce_key: str | None = None,
        debounce_ms: int | None = None,
    ) -> None:
        """
        Send a progress notification.

        Args:
            progress_token: Unique token identifying the operation
            progress: Progress value (0.0 to 1.0)
            total: Optional total value
            message: Optional progress message
            client_ids: Specific clients to notify (None for all subscribed)
            debounce_key: Key for debouncing (uses progress_token if None)
            debounce_ms: Debounce time in ms (uses default if None)
        """
        notification = EnhancedProgressNotification(
            method="notifications/progress",
            params=EnhancedProgressNotificationParams(
                progressToken=progress_token,
                progress=progress,
                total=total,
                message=message,
            ),
        )

        await self._send_notification(
            notification,
            NotificationType.PROGRESS,
            client_ids,
            debounce_key or str(progress_token),
            debounce_ms,
        )

    async def notify_message(
        self,
        level: LogLevel,
        data: Any,
        logger_name: str | None = None,
        client_ids: list[str] | None = None,
    ) -> None:
        """
        Send a log/message notification.

        Args:
            level: Log level
            data: Log data/message
            logger_name: Optional logger name
            client_ids: Specific clients to notify (None for all subscribed)
        """
        notification = LoggingMessageNotification(
            method="notifications/message",
            params=LoggingMessageNotificationParams(
                level=level,
                data=data,
                logger=logger_name,
            ),
        )

        # Don't debounce log messages
        await self._send_notification(
            notification,
            NotificationType.MESSAGE,
            client_ids,
            debounce_ms=0,
        )

    async def notify_resource_updated(
        self,
        uri: str,
        timestamp: str | None = None,
        client_ids: list[str] | None = None,
        debounce_key: str | None = None,
        debounce_ms: int | None = None,
    ) -> None:
        """
        Send a resource updated notification.

        Args:
            uri: Resource URI that was updated
            timestamp: Optional update timestamp
            client_ids: Specific clients to notify (None for all subscribed)
            debounce_key: Key for debouncing (uses uri if None)
            debounce_ms: Debounce time in ms (uses default if None)
        """
        notification = ResourceUpdatedNotification(
            method="notifications/resources/updated",
            params=ResourceUpdatedNotificationParams(
                uri=uri,
                timestamp=timestamp,
            ),
        )

        await self._send_notification(
            notification,
            NotificationType.RESOURCE_UPDATED,
            client_ids,
            debounce_key or uri,
            debounce_ms,
        )

    async def notify_resource_list_changed(
        self,
        client_ids: list[str] | None = None,
    ) -> None:
        """
        Send a resource list changed notification.

        Args:
            client_ids: Specific clients to notify (None for all subscribed)
        """
        notification = ResourceListChangedNotification(
            method="notifications/resources/list_changed",
            params=ResourceListChangedNotificationParams(),
        )

        await self._send_notification(
            notification,
            NotificationType.RESOURCE_LIST_CHANGED,
            client_ids,
        )

    async def notify_tool_list_changed(
        self,
        client_ids: list[str] | None = None,
    ) -> None:
        """
        Send a tool list changed notification.

        Args:
            client_ids: Specific clients to notify (None for all subscribed)
        """
        notification = ToolListChangedNotification(
            method="notifications/tools/list_changed",
            params=ToolListChangedNotificationParams(),
        )

        await self._send_notification(
            notification,
            NotificationType.TOOL_LIST_CHANGED,
            client_ids,
        )

    async def notify_cancelled(
        self,
        request_id: str | int,
        reason: str | None = None,
        client_ids: list[str] | None = None,
    ) -> None:
        """
        Send a cancelled notification.

        Args:
            request_id: ID of the cancelled request
            reason: Optional cancellation reason
            client_ids: Specific clients to notify (None for all subscribed)
        """
        notification = CancelledNotification(
            method="notifications/cancelled",
            params=CancelledNotificationParams(
                requestId=request_id,
                reason=reason,
            ),
        )

        # Don't debounce cancellation notifications
        await self._send_notification(
            notification,
            NotificationType.CANCELLED,
            client_ids,
            debounce_ms=0,
        )

    async def _send_notification(
        self,
        notification: Notification,
        notification_type: NotificationType,
        client_ids: list[str] | None = None,
        debounce_key: str | None = None,
        debounce_ms: int | None = None,
    ) -> None:
        """
        Internal method to send or queue a notification.

        Args:
            notification: The notification to send
            notification_type: Type of notification
            client_ids: Specific clients to notify (None for all subscribed)
            debounce_key: Key for debouncing
            debounce_ms: Debounce time in ms
        """
        # Determine target clients
        if client_ids is None:
            async with self.clients_lock:
                # Find all clients subscribed to this notification type
                client_ids = [
                    client.client_id
                    for client in self.clients.values()
                    if any(
                        sub.method == notification_type.value
                        for sub in client.subscriptions.values()
                    )
                ]

        if not client_ids:
            return  # No clients to notify

        # Handle debouncing
        if debounce_key and (debounce_ms is None or debounce_ms > 0):
            await self._debounce_notification(
                notification,
                set(client_ids),
                debounce_key,
                debounce_ms or self.default_debounce_ms,
            )
        else:
            # Send immediately
            await self._send_to_clients(notification, client_ids)

    async def _debounce_notification(
        self,
        notification: Notification,
        client_ids: set[str],
        debounce_key: str,
        debounce_ms: int,
    ) -> None:
        """
        Debounce a notification.

        Args:
            notification: The notification to debounce
            client_ids: Set of client IDs to notify
            debounce_key: Key for debouncing
            debounce_ms: Debounce time in milliseconds
        """
        async with self.debounce_lock:
            now = time.time()
            send_after = now + (debounce_ms / 1000.0)

            if debounce_key in self.debounced:
                # Update existing debounced notification
                existing = self.debounced[debounce_key]
                existing.notification = notification
                existing.clients.update(client_ids)
                existing.send_after = send_after
            else:
                # Create new debounced notification
                self.debounced[debounce_key] = DebouncedNotification(
                    notification=notification,
                    clients=client_ids,
                    created_at=now,
                    send_after=send_after,
                )

    async def _process_debounced_notifications(self) -> None:
        """Background task to process debounced notifications."""
        while self._running:
            try:
                await asyncio.sleep(0.05)  # Check every 50ms

                now = time.time()
                to_send: list[tuple[str, DebouncedNotification]] = []

                async with self.debounce_lock:
                    for key, debounced in list(self.debounced.items()):
                        if now >= debounced.send_after:
                            to_send.append((key, debounced))
                            del self.debounced[key]

                # Send notifications outside the lock
                for _, debounced in to_send:
                    await self._send_to_clients(
                        debounced.notification,
                        list(debounced.clients),
                    )

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error processing debounced notifications")

    async def _send_to_clients(
        self,
        notification: Notification,
        client_ids: list[str],
    ) -> None:
        """
        Send a notification to specific clients with rate limiting.

        Args:
            notification: The notification to send
            client_ids: List of client IDs to send to
        """
        # Convert notification to dict
        notification_data = notification.model_dump(exclude_none=True)

        # Add jsonrpc field if not present
        if "jsonrpc" not in notification_data:
            notification_data["jsonrpc"] = "2.0"

        tasks = []
        for client_id in client_ids:
            if await self._check_rate_limit(client_id):
                tasks.append(self._send_to_client(client_id, notification_data))
            else:
                logger.warning(f"Rate limit exceeded for client {client_id}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_to_client(
        self,
        client_id: str,
        notification_data: dict[str, Any],
    ) -> None:
        """
        Send a notification to a single client.

        Args:
            client_id: Client ID
            notification_data: Notification data as dict
        """
        try:
            success = await self.sender.send_notification(
                client_id, notification_data
            )
            if success:
                async with self.clients_lock:
                    if client_id in self.clients:
                        client = self.clients[client_id]
                        client.last_notification = time.time()
                        client.notification_count += 1
            else:
                logger.warning(f"Failed to send notification to client {client_id}")
        except Exception:
            logger.exception(f"Error sending notification to client {client_id}")

    async def _check_rate_limit(self, client_id: str) -> bool:
        """
        Check if a client has exceeded the rate limit.

        Args:
            client_id: Client ID to check

        Returns:
            True if within rate limit, False if exceeded
        """
        async with self.clients_lock:
            client = self.clients.get(client_id)
            if not client:
                return False

            now = time.time()
            window_duration = 60.0  # 1 minute window

            # Reset window if needed
            if now - client.rate_limit_window_start >= window_duration:
                client.rate_limit_window_start = now
                client.rate_limit_count = 0

            # Check limit
            if client.rate_limit_count >= self.rate_limit_per_minute:
                return False

            client.rate_limit_count += 1
            return True

    async def _cleanup_inactive_clients(self) -> None:
        """Background task to clean up inactive clients."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Check every minute

                now = time.time()
                inactive_threshold = 300  # 5 minutes

                async with self.clients_lock:
                    inactive_clients = [
                        client_id
                        for client_id, client in self.clients.items()
                        if now - client.last_notification > inactive_threshold
                        and not client.subscriptions
                    ]

                for client_id in inactive_clients:
                    await self.unregister_client(client_id)
                    logger.debug(f"Cleaned up inactive client {client_id}")

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error cleaning up inactive clients")
