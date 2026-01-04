# WS-9.1: Bot Menu Button

## Overview

**Work Stream ID:** WS-9.1
**Status:** Complete
**Started:** 2026-01-04
**Completed:** 2026-01-04

## Summary

Implemented the bot menu button feature to improve command discoverability in the Telegram bot. Users can now click a menu button in the chat interface to see all available commands organized by category.

## Implementation Details

### Files Created/Modified

1. **`src/tnse/bot/menu.py`** (already existed, now fully functional)
   - Defined `COMMAND_CATEGORIES` dictionary with 6 categories: Basic, Channel, Search, Topic, Export, Advanced
   - `get_command_categories()` - Returns commands organized by category
   - `get_bot_commands()` - Returns flat list of BotCommand objects for Telegram API
   - `setup_bot_commands(bot)` - Calls `bot.set_my_commands()` to register commands
   - `setup_menu_button(bot)` - Calls `bot.set_chat_menu_button()` with MenuButtonCommands
   - `setup_bot_menu(bot)` - Orchestrates both setups with proper error handling

2. **`src/tnse/bot/application.py`** (modified)
   - Added import for `setup_bot_menu` from `menu` module
   - Added `_post_init(application)` async callback function
   - Modified `create_bot_application()` to use `.post_init(_post_init)` on builder

3. **`tests/unit/bot/test_menu_setup.py`** (already existed, test fix applied)
   - Fixed `test_menu_setup_logged_on_startup` to patch logger object directly instead of `get_logger` function

### Command Categories

The bot now organizes 18 commands into 6 logical categories:

| Category | Commands |
|----------|----------|
| Basic | start, help, settings |
| Channel | addchannel, removechannel, channels, channelinfo |
| Search | search |
| Topic | savetopic, topics, topic, deletetopic, templates, usetemplate |
| Export | export |
| Advanced | import, health |

### Technical Decisions

1. **Post-Init Callback Pattern**: Used `Application.builder().post_init()` rather than manually calling setup in `run_polling()`. This ensures menu setup happens automatically regardless of how the application is run.

2. **Error Handling**: Both `setup_bot_commands()` and `setup_menu_button()` return boolean success indicators and log errors rather than raising exceptions. This prevents menu setup issues from crashing the bot.

3. **MenuButtonCommands Type**: Used `MenuButtonCommands()` which instructs Telegram to show the command list when the menu button is clicked, rather than a web app or default behavior.

### Testing

- 30 unit tests covering:
  - Command definitions (10 tests)
  - Command categories (6 tests)
  - Bot commands registration (4 tests)
  - Menu button setup (4 tests)
  - Integration of both features (4 tests)
  - Application lifecycle integration (2 tests)

All 30 tests pass successfully.

### TDD Approach

Following TDD methodology:
1. **RED Phase**: Tests were written first (commit 5b9054d)
2. **GREEN Phase**: Implementation added to make tests pass
3. **REFACTOR Phase**: Code quality maintained, no refactoring needed

## Challenges and Solutions

### Challenge 1: Logger Mocking in Tests

The test `test_menu_setup_logged_on_startup` was failing because it patched `get_logger` in the menu module, but the logger was already created at module import time.

**Solution**: Changed the test to patch `src.tnse.bot.menu.logger` directly instead of `get_logger`.

### Challenge 2: Application Post-Init

The test expected `app.post_init` to be set, but the application wasn't being built with a post_init callback.

**Solution**: Added `_post_init` async function and registered it using `.post_init(_post_init)` on the ApplicationBuilder.

## Verification

```bash
# Run menu setup tests
pytest tests/unit/bot/test_menu_setup.py -v
# Result: 30 passed

# Run full test suite
pytest tests/ --no-cov -q
# Result: 1099 passed, 6 failed (pre-existing failures), 2 skipped
```

## User Impact

When users open the bot chat in Telegram:
1. A menu button appears at the bottom of the chat
2. Clicking the button shows a list of all available commands
3. Commands are organized logically making them easier to discover
4. Users can tap any command to execute it

## Related Documentation

- Telegram Bot API setMyCommands: https://core.telegram.org/bots/api#setmycommands
- Telegram MenuButton: https://core.telegram.org/bots/api#menubutton
