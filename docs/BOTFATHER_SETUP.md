# Telegram Bot Registration Guide

This guide explains how to register your TNSE bot with Telegram's BotFather.

## Prerequisites

- A Telegram account
- The Telegram app installed on your device

## Step-by-Step Registration

### 1. Start a Chat with BotFather

1. Open Telegram
2. Search for `@BotFather` in the search bar
3. Start a conversation by clicking "Start" or sending `/start`

### 2. Create a New Bot

1. Send the command `/newbot` to BotFather
2. BotFather will ask for a **name** for your bot
   - This is the display name users will see
   - Example: `TNSE News Bot`
3. BotFather will ask for a **username** for your bot
   - Must end with `bot` or `Bot`
   - Must be unique across Telegram
   - Example: `tnse_news_bot` or `MyTNSEBot`

### 3. Save Your Bot Token

After successful creation, BotFather will provide you with:

```
Done! Congratulations on your new bot. You will find it at t.me/your_bot_username.
You can now add a description, about section and profile picture for your bot, see /help for a list of commands.

Use this token to access the HTTP API:
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789
```

**IMPORTANT**:
- Copy this token immediately
- Store it securely - anyone with this token can control your bot
- Never commit this token to version control

### 4. Configure Your Environment

Add the token to your `.env` file:

```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789
```

### 5. Optional: Configure Bot Settings

You can use BotFather to customize your bot:

| Command | Description |
|---------|-------------|
| `/setdescription` | Set the bot's description (shown in profile) |
| `/setabouttext` | Set the "About" section text |
| `/setuserpic` | Set the bot's profile picture |
| `/setcommands` | Set the command list shown in Telegram |

### 6. Set Bot Commands

Send `/setcommands` to BotFather, then select your bot and send:

```
start - Start the bot and see welcome message
help - Show available commands and usage
settings - View and configure bot settings
```

These commands will appear in the Telegram command menu when users type `/`.

## Security Recommendations

1. **Restrict Access**: Set `ALLOWED_TELEGRAM_USERS` in your `.env` to limit who can use the bot:
   ```bash
   ALLOWED_TELEGRAM_USERS=123456789,987654321
   ```
   To find your Telegram user ID, you can use bots like `@userinfobot`.

2. **Token Rotation**: If you suspect your token has been compromised, use `/revoke` with BotFather to get a new token.

3. **Environment Separation**: Use different bots for development and production environments.

## Verification

To verify your bot is set up correctly:

1. Ensure `TELEGRAM_BOT_TOKEN` is set in your `.env`
2. Run the bot application
3. Send `/start` to your bot in Telegram
4. You should receive the welcome message

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Unauthorized" error | Check that the token is correct and complete |
| Bot not responding | Verify the bot application is running |
| "Access denied" message | Your Telegram ID may not be in the whitelist |
| Token format error | Ensure no extra spaces or characters in the token |

## Additional Resources

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [python-telegram-bot Documentation](https://python-telegram-bot.readthedocs.io/)
- [BotFather Commands](https://core.telegram.org/bots#botfather)
