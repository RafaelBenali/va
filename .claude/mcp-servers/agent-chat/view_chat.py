#!/usr/bin/env python
"""Simple CLI to view agent chat messages."""

import asyncio
import sys

import nats
from nats.js.api import ConsumerConfig, DeliverPolicy, StreamConfig
from nats.js.errors import NotFoundError

NATS_URL = "nats://localhost:4222"
STREAM_NAME = "AGENT_CHAT"
CHANNELS = ["roadmap", "coordination", "errors"]


async def ensure_stream(js) -> bool:
    """Ensure the AGENT_CHAT stream exists. Returns True if stream exists/created."""
    try:
        await js.stream_info(STREAM_NAME)
        return True
    except NotFoundError:
        try:
            await js.add_stream(
                config=StreamConfig(
                    name=STREAM_NAME,
                    subjects=["chat.*"],
                    max_msgs=10000,
                    max_age=60 * 60 * 24 * 7,  # 7 days
                )
            )
            print(f"Created stream '{STREAM_NAME}'")
            return True
        except Exception as e:
            print(f"Could not create stream: {e}")
            return False


async def view_channel(channel: str, count: int = 20):
    """View recent messages from a channel."""
    nc = await nats.connect(NATS_URL)
    js = nc.jetstream()

    subject = f"chat.{channel}"
    print(f"\n=== #{channel} ===")

    # Ensure stream exists
    if not await ensure_stream(js):
        print("(stream not available)")
        await nc.close()
        return

    try:
        consumer = await js.pull_subscribe(
            subject,
            durable=None,
            config=ConsumerConfig(
                deliver_policy=DeliverPolicy.ALL,
                filter_subject=subject,
            ),
        )

        msgs = []
        try:
            msgs = await consumer.fetch(count, timeout=2)
            for msg in msgs:
                print(msg.data.decode())
                await msg.ack()
        except nats.errors.TimeoutError:
            pass

        if not msgs:
            print("(no messages)")

        await consumer.unsubscribe()
    except Exception as e:
        print(f"Error: {e}")

    await nc.close()


async def view_all(count: int = 20):
    """View all channels."""
    for channel in CHANNELS:
        await view_channel(channel, count)


async def main():
    if len(sys.argv) > 1:
        channel = sys.argv[1]
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        if channel == "all":
            await view_all(count)
        elif channel in CHANNELS:
            await view_channel(channel, count)
        else:
            print(f"Unknown channel: {channel}")
            print(f"Available: {', '.join(CHANNELS)}, all")
    else:
        print("Usage: python view_chat.py <channel> [count]")
        print(f"Channels: {', '.join(CHANNELS)}, all")
        print("\nExamples:")
        print("  python view_chat.py coordination")
        print("  python view_chat.py all 50")


if __name__ == "__main__":
    asyncio.run(main())
