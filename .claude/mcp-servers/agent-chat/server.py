"""
Agent Chat MCP Server - NATS JetStream-based chat for Claude agents.

Provides Slack-like chat functionality with persistent channels:
- roadmap: Discussions about the project roadmap
- coordination: Parallel work coordination between agents
- errors: Error reporting and debugging discussions
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import nats
from nats.js.api import ConsumerConfig, DeliverPolicy, StreamConfig
from mcp.server.fastmcp import FastMCP

# Channel definitions
CHANNELS = {
    "roadmap": "Discussions about the project roadmap",
    "coordination": "Parallel work coordination between agents",
    "errors": "Error reporting and debugging discussions",
}

STREAM_NAME = "AGENT_CHAT"
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")

# Initialize FastMCP server
mcp = FastMCP("agent-chat")

# Global state
_nats_client: nats.NATS | None = None
_jetstream: Any = None
_agent_handle: str | None = None


async def get_nats() -> tuple[nats.NATS, Any]:
    """Get or create NATS connection and JetStream context."""
    global _nats_client, _jetstream

    if _nats_client is None or not _nats_client.is_connected:
        _nats_client = await nats.connect(NATS_URL)
        _jetstream = _nats_client.jetstream()

        # Ensure stream exists
        try:
            await _jetstream.stream_info(STREAM_NAME)
        except nats.js.errors.NotFoundError:
            # Create stream for all channels
            subjects = [f"chat.{channel}" for channel in CHANNELS.keys()]
            await _jetstream.add_stream(
                StreamConfig(
                    name=STREAM_NAME,
                    subjects=subjects,
                    max_age=60 * 60 * 24 * 30,  # 30 days retention
                    max_msgs=10000,
                    storage="file",
                )
            )

    return _nats_client, _jetstream


@mcp.tool()
async def set_handle(handle: str) -> str:
    """
    Set your agent handle for chat messages.

    Args:
        handle: Your unique handle/nickname for the chat (e.g., 'tdd-coder', 'explorer-1')

    Returns:
        Confirmation message with your handle
    """
    global _agent_handle

    if not handle or not handle.strip():
        return "Error: Handle cannot be empty"

    _agent_handle = handle.strip()
    return f"Handle set to: {_agent_handle}"


@mcp.tool()
async def get_handle() -> str:
    """
    Get your current agent handle.

    Returns:
        Your current handle or a message if not set
    """
    if _agent_handle:
        return f"Your handle is: {_agent_handle}"
    return "No handle set. Use set_handle() to set one."


@mcp.tool()
async def list_channels() -> str:
    """
    List all available chat channels.

    Returns:
        List of channels with descriptions
    """
    lines = ["Available channels:"]
    for name, description in CHANNELS.items():
        lines.append(f"  #{name} - {description}")
    return "\n".join(lines)


@mcp.tool()
async def send_message(channel: str, message: str) -> str:
    """
    Send a message to a channel.

    Args:
        channel: Channel name (roadmap, coordination, or errors)
        message: The message content to send

    Returns:
        Confirmation or error message
    """
    global _agent_handle

    if channel not in CHANNELS:
        return f"Error: Unknown channel '{channel}'. Use list_channels() to see available channels."

    if not message or not message.strip():
        return "Error: Message cannot be empty"

    handle = _agent_handle or f"anonymous-{uuid.uuid4().hex[:6]}"

    try:
        _, jetstream = await get_nats()

        # Create message payload
        timestamp = datetime.now(timezone.utc).isoformat()
        payload = f"[{timestamp}] <{handle}> {message.strip()}"

        # Publish to JetStream
        subject = f"chat.{channel}"
        ack = await jetstream.publish(subject, payload.encode())

        return f"Message sent to #{channel} (seq: {ack.seq})"

    except Exception as error:
        return f"Error sending message: {error}"


@mcp.tool()
async def read_messages(channel: str, count: int = 20) -> str:
    """
    Read recent messages from a channel.

    Args:
        channel: Channel name (roadmap, coordination, or errors)
        count: Number of recent messages to retrieve (default: 20, max: 100)

    Returns:
        Recent messages from the channel
    """
    if channel not in CHANNELS:
        return f"Error: Unknown channel '{channel}'. Use list_channels() to see available channels."

    count = min(max(1, count), 100)

    try:
        _, jetstream = await get_nats()

        subject = f"chat.{channel}"

        # Get stream info to determine start sequence for last N messages
        stream_info = await jetstream.stream_info(STREAM_NAME)

        # Get subject-specific message count from state
        subjects_state = stream_info.state.subjects or {}
        subject_msg_count = subjects_state.get(subject, 0)

        if subject_msg_count == 0:
            return f"No messages in #{channel}"

        # Create ephemeral consumer to read ALL messages from the start
        consumer = await jetstream.pull_subscribe(
            subject,
            durable=None,
            config=ConsumerConfig(
                deliver_policy=DeliverPolicy.ALL,
                filter_subject=subject,
            ),
        )

        # Fetch all available messages for this subject
        all_messages = []
        try:
            # Fetch in batches to get all messages
            fetched = await consumer.fetch(subject_msg_count, timeout=5)
            for msg in fetched:
                all_messages.append(msg.data.decode())
                await msg.ack()
        except asyncio.TimeoutError:
            pass  # Timeout after getting some messages
        except nats.errors.TimeoutError:
            pass  # NATS timeout

        await consumer.unsubscribe()

        if not all_messages:
            return f"No messages in #{channel}"

        # Return only the last 'count' messages
        recent_messages = all_messages[-count:]
        header = f"=== #{channel} ({len(recent_messages)} of {len(all_messages)} messages) ==="
        return header + "\n" + "\n".join(recent_messages)

    except Exception as error:
        return f"Error reading messages: {error}"


@mcp.tool()
async def read_all_channels(count: int = 10) -> str:
    """
    Read recent messages from all channels.

    Args:
        count: Number of recent messages per channel (default: 10, max: 50)

    Returns:
        Recent messages from all channels
    """
    count = min(max(1, count), 50)

    results = []
    for channel in CHANNELS.keys():
        channel_messages = await read_messages(channel, count)
        results.append(channel_messages)

    return "\n\n".join(results)


@mcp.tool()
async def broadcast(message: str) -> str:
    """
    Send a message to all channels (use sparingly).

    Args:
        message: The message to broadcast

    Returns:
        Confirmation of broadcast
    """
    if not message or not message.strip():
        return "Error: Message cannot be empty"

    results = []
    for channel in CHANNELS.keys():
        result = await send_message(channel, f"[BROADCAST] {message}")
        results.append(result)

    return "Broadcast sent to all channels:\n" + "\n".join(results)


@mcp.tool()
async def connection_status() -> str:
    """
    Check NATS connection status.

    Returns:
        Connection status information
    """
    global _nats_client, _agent_handle

    lines = ["NATS Connection Status:"]
    lines.append(f"  Server: {NATS_URL}")
    lines.append(f"  Handle: {_agent_handle or 'Not set'}")

    if _nats_client and _nats_client.is_connected:
        lines.append("  Status: Connected")
        lines.append(f"  Client ID: {_nats_client.client_id}")
    else:
        lines.append("  Status: Disconnected")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
