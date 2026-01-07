#!/usr/bin/env python3
"""
Authenticate Telethon session with user account.

This script creates/updates the tnse_session.session file with user credentials.
Bot tokens CANNOT access channel history - you need a user account.

Usage:
    python scripts/auth_telegram.py

Requirements:
    - TELEGRAM_API_ID and TELEGRAM_API_HASH in .env
    - A phone number associated with a Telegram account
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

SESSION_FILE = "tnse_session.session"


async def main() -> None:
    load_dotenv()

    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        print("Error: TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env")
        sys.exit(1)

    try:
        from telethon import TelegramClient
    except ImportError:
        print("Error: telethon not installed. Run: pip install telethon")
        sys.exit(1)

    print("=" * 60)
    print("Telegram User Authentication")
    print("=" * 60)
    print()

    # Check if existing session is a bot
    if os.path.exists(SESSION_FILE):
        print(f"Found existing session file: {SESSION_FILE}")
        print("Checking if it's a bot session...")
        print()

        client = TelegramClient("tnse_session", int(api_id), api_hash)
        await client.connect()

        if await client.is_user_authorized():
            me = await client.get_me()
            if me.bot:
                print(f"Current session is a BOT: @{me.username}")
                print("Bots cannot read channel history. Need user authentication.")
                print()
                await client.disconnect()

                # Remove the bot session
                response = input("Delete bot session and authenticate as user? [y/N]: ")
                if response.lower() != "y":
                    print("Aborted.")
                    sys.exit(0)

                os.remove(SESSION_FILE)
                print(f"Removed {SESSION_FILE}")
                print()
            else:
                print(f"Session already authenticated as USER: {me.first_name} (@{me.username})")
                print("No action needed.")
                await client.disconnect()
                sys.exit(0)
        else:
            await client.disconnect()

    print("This will authenticate with your phone number (NOT a bot token).")
    print("The session will be saved to: tnse_session.session")
    print()

    # Get phone number
    phone = input("Enter your phone number (with country code, e.g. +1234567890): ").strip()
    if not phone:
        print("Error: Phone number required")
        sys.exit(1)

    client = TelegramClient("tnse_session", int(api_id), api_hash)
    await client.connect()

    # Send code request
    print()
    print("Sending authentication code...")
    await client.send_code_request(phone)

    # Get code from user
    code = input("Enter the code you received: ").strip()
    if not code:
        print("Error: Code required")
        sys.exit(1)

    # Sign in
    try:
        await client.sign_in(phone, code)
    except Exception as e:
        if "Two-step verification" in str(e) or "password" in str(e).lower():
            password = input("Two-factor auth enabled. Enter your password: ").strip()
            await client.sign_in(password=password)
        else:
            raise

    me = await client.get_me()
    print()
    print("=" * 60)
    print(f"Authenticated as: {me.first_name} (@{me.username or 'no username'})")
    print(f"User ID: {me.id}")
    print(f"Is Bot: {me.bot}")
    print("=" * 60)
    print()
    print("Session saved to tnse_session.session")
    print("You can now use /sync to collect channel content.")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
