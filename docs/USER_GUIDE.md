# TNSE Bot User Guide

This guide explains how to use the Telegram News Search Engine (TNSE) bot for monitoring public Telegram channels and searching news content.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Basic Commands](#basic-commands)
3. [Channel Management](#channel-management)
4. [Search Commands](#search-commands)
5. [Topic Management](#topic-management)
6. [Export Functionality](#export-functionality)
7. [Advanced Features](#advanced-features)
8. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Finding the Bot

1. Open Telegram
2. Search for your TNSE bot by its username (provided by your administrator)
3. Click "Start" or send `/start` to begin

### First Steps

After starting the bot, you will receive a welcome message. Use `/help` to see all available commands.

If the bot has access control enabled, only authorized users (by Telegram user ID) will be able to use it.

---

## Basic Commands

### /start

Starts the bot and displays a welcome message.

```
/start
```

**Response:** Welcome message with basic instructions.

### /help

Shows all available commands and their descriptions.

```
/help
```

**Response:** List of all commands with usage examples.

### /settings

Displays current bot settings including access mode and your user ID.

```
/settings
```

**Response:**
```
Bot Settings

Access Mode: Restricted (whitelist of 2 users)
Connection Mode: Polling

Your User ID: 123456789

To modify settings, update the environment configuration and restart the bot.
```

---

## Channel Management

### /addchannel

Adds a public Telegram channel to be monitored.

**Usage:**
```
/addchannel @channel_username
/addchannel https://t.me/channel_username
```

**Examples:**
```
/addchannel @telegram_news
/addchannel @bbc_news
/addchannel https://t.me/reuters
```

**Response on success:**
```
Channel successfully added!

Title: Telegram News
Username: @telegram_news
Subscribers: 1.2M

The channel is now being monitored for content.
```

**Notes:**
- Only public channels can be added
- The channel must be accessible to the bot
- Content collection begins after adding a channel

### /removechannel

Removes a channel from monitoring.

**Usage:**
```
/removechannel @channel_username
```

**Example:**
```
/removechannel @telegram_news
```

**Response:**
```
Channel removed successfully!

Title: Telegram News
Username: @telegram_news

Content from this channel will no longer be collected.
```

### /channels

Lists all currently monitored channels.

**Usage:**
```
/channels
```

**Response:**
```
Monitored Channels (3):

1. BBC News
   @bbc_news | 5.2M subscribers
   [Active]

2. Reuters
   @reuters | 2.1M subscribers
   [Active]

3. Local News
   @local_news | 50K subscribers
   [Active]

Use /channelinfo @username for detailed information.
```

### /channelinfo

Shows detailed information about a specific monitored channel.

**Usage:**
```
/channelinfo @channel_username
```

**Example:**
```
/channelinfo @bbc_news
```

**Response:**
```
Channel Information

Title: BBC News
Username: @bbc_news
Subscribers: 5.2M
Status: Active
Description: Official BBC News channel

Health Status: Healthy
Last Check: 2025-12-26 10:30 UTC

Added: 2025-12-01
```

---

## Search Commands

### /search

Searches for posts matching keywords within the last 24 hours.

**Usage:**
```
/search <keywords>
```

**Examples:**
```
/search corruption news
/search political scandal
/search breaking news ukraine
```

**Response:**
```
Search: "corruption news"
Found 47 results (showing 1-5)

1. [BBC News] - 12.5K views
   Preview: Minister caught accepting bribes from...
   Reactions: [thumbs_up] 150 | [heart] 89 | [fire] 34
   Score: 0.25 | 2h ago
   [View Post](https://t.me/bbc_news/12345)

2. [Reuters] - 8.2K views
   Preview: Investigation reveals widespread...
   Score: 0.18 | 4h ago
   [View Post](https://t.me/reuters/23456)

[<< Prev] [1/10] [Next >>]
```

**Pagination:**
- Use the "Next >>" and "<< Prev" buttons to navigate through results
- Results are sorted by engagement score (views + reactions, weighted by recency)

**Search Tips:**
- Use multiple keywords for more specific results
- Both English and Russian/Ukrainian keywords are supported
- Results are limited to the last 24 hours

---

## Topic Management

### /savetopic

Saves your current search as a named topic for quick access.

**Usage:**
```
/savetopic <name>
```

**Example:**
```
/search corruption news
/savetopic corruption
```

**Response:**
```
Topic saved successfully!

Name: corruption
Keywords: corruption news

Use /topic corruption to run this search again.
```

**Notes:**
- You must run a search before saving a topic
- Topic names should be simple (alphanumeric, underscores)

### /topics

Lists all your saved topics.

**Usage:**
```
/topics
```

**Response:**
```
Your Saved Topics:

- corruption
  Keywords: corruption news

- politics
  Keywords: political scandal investigation

Use /topic <name> to run a saved search.
Use /deletetopic <name> to delete a topic.
```

### /topic

Runs a saved topic search.

**Usage:**
```
/topic <name>
```

**Example:**
```
/topic corruption
```

**Response:** Same format as `/search` results.

### /deletetopic

Deletes a saved topic.

**Usage:**
```
/deletetopic <name>
```

**Example:**
```
/deletetopic old_topic
```

**Response:**
```
Topic 'old_topic' has been deleted.
```

### /templates

Shows pre-built topic templates for common searches.

**Usage:**
```
/templates
```

**Response:**
```
Pre-built Topic Templates:

Use these templates for quick searches:

- corruption
  Keywords: corruption bribery scandal
  Description: Government and business corruption

- politics
  Keywords: election vote parliament government
  Description: Political news and events

- technology
  Keywords: tech startup innovation AI
  Description: Technology and innovation news

To use a template, run a search with those keywords:
Example: /search corruption bribery scandal

Or save your own topics with /savetopic after searching.
```

### /usetemplate

Runs a search using a pre-built template.

**Usage:**
```
/usetemplate <template_name>
```

**Example:**
```
/usetemplate corruption
```

**Response:** Same format as `/search` results.

---

## Export Functionality

### /export

Exports your last search results to a file.

**Usage:**
```
/export              # Exports as CSV (default)
/export csv          # Exports as CSV
/export json         # Exports as JSON
/export help         # Shows help
```

**Example:**
```
/search corruption news
/export csv
```

**Response:** Bot sends a file containing:
- Channel information (username, title)
- Post content
- View count and engagement metrics
- Direct links to original Telegram posts

**CSV Format:**
```csv
channel_username,channel_title,text_content,view_count,reaction_score,published_at,telegram_link
bbc_news,BBC News,"Minister caught...",12500,89.0,2025-12-26 08:30:00,https://t.me/bbc_news/12345
```

**JSON Format:**
```json
{
  "query": "corruption news",
  "exported_at": "2025-12-26T10:30:00Z",
  "result_count": 47,
  "results": [
    {
      "channel_username": "bbc_news",
      "channel_title": "BBC News",
      "text_content": "Minister caught...",
      "view_count": 12500,
      "reaction_score": 89.0,
      "relative_engagement": 0.25,
      "published_at": "2025-12-26T08:30:00Z",
      "telegram_link": "https://t.me/bbc_news/12345"
    }
  ]
}
```

---

## Advanced Features

### /import

Bulk imports channels from a file.

**Usage:** Send `/import` with an attached file.

**Supported formats:**
- **CSV:** One column with channel usernames or URLs
- **JSON:** Array of channels or `{"channels": [...]}`
- **TXT:** One channel per line

**Example CSV:**
```csv
channel_url
@channel_one
@channel_two
https://t.me/channel_three
```

**Response:**
```
Import completed!

Added: 3 channels
Skipped (already exist): 1 channel
Failed: 0 channels
```

### /health

Shows health status of all monitored channels.

**Usage:**
```
/health
```

**Response:**
```
Channel Health Status

Total: 5 channels
Healthy: 4 | Warnings: 1 | Errors: 0 | Pending: 0

Issues:
  [WARNING] @slow_channel
     Status: Rate Limited
     Error: Temporarily limited by Telegram
     Last check: 2025-12-26 09:45 UTC

Healthy (4):
  [OK] @bbc_news - Last: 2025-12-26 10:30 UTC
  [OK] @reuters - Last: 2025-12-26 10:30 UTC
  [OK] @local_news - Last: 2025-12-26 10:30 UTC
  [OK] @tech_news - Last: 2025-12-26 10:30 UTC
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Access denied" | Your Telegram user ID is not in the whitelist. Use `/settings` to find your ID and contact the administrator. |
| "Channel service not available" | The bot's backend services are not running. Contact the administrator. |
| "Search service not available" | The search backend is temporarily unavailable. Wait a few minutes and try again. |
| "No results found" | Try different keywords, check if channels are monitored with `/channels`, or verify channel health with `/health`. |
| "Cannot add channel" | Ensure the channel is public and the username is correct (case-sensitive). |
| "Rate limited" | Too many requests. Wait 30-60 seconds before retrying. |

### Quick Diagnostics

Use these commands to diagnose issues:

| Command | What It Checks |
|---------|----------------|
| `/settings` | Your user ID and access mode |
| `/health` | Status of all monitored channels |
| `/channels` | List of active channels |

### Understanding Engagement Scores

The bot ranks results using a combined score that considers:

1. **View Count:** Number of post views
2. **Reaction Score:** Weighted sum of emoji reactions (thumbs up, hearts, fire, etc.)
3. **Relative Engagement:** Engagement divided by subscriber count (accounts for channel size)
4. **Recency:** Newer posts get a boost in ranking

Formula: `combined_score = relative_engagement * (1 - hours_since_post / 24)`

### Getting Help

- Use `/help` or `/h` for command reference
- Use `/export help` for export-specific help
- Check `/health` for channel issues
- See [BOT_TROUBLESHOOTING.md](BOT_TROUBLESHOOTING.md) for detailed troubleshooting
- Contact your bot administrator for access or technical issues

---

## Quick Reference

| Command | Alias | Description |
|---------|-------|-------------|
| `/start` | - | Start the bot |
| `/help` | `/h` | Show all commands |
| `/settings` | - | View bot settings |
| `/addchannel @name` | - | Add channel to monitor |
| `/removechannel @name` | - | Stop monitoring channel |
| `/channels` | `/ch` | List monitored channels |
| `/channelinfo @name` | - | Show channel details |
| `/search <query>` | `/s` | Search for posts |
| `/export [csv\|json]` | `/e` | Export search results |
| `/savetopic <name>` | - | Save current search |
| `/topics` | `/t` | List saved topics |
| `/topic <name>` | - | Run saved topic |
| `/deletetopic <name>` | - | Delete saved topic |
| `/templates` | - | Show pre-built templates |
| `/usetemplate <name>` | - | Run template search |
| `/import` | - | Bulk import channels (with file) |
| `/health` | - | Show channel health status |

---

## Command Aliases

For faster access, the following command aliases are available:

| Full Command | Short Alias |
|--------------|-------------|
| `/search` | `/s` |
| `/channels` | `/ch` |
| `/help` | `/h` |
| `/topics` | `/t` |
| `/export` | `/e` |

**Example:**
```
/s corruption news    # Same as /search corruption news
/ch                   # Same as /channels
/e json               # Same as /export json
```
