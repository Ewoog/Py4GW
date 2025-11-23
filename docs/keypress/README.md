# Keypress Control Feature

This directory contains documentation and examples for the keypress control functionality added to the Messaging widget system.

## Files Added

### Helper Module
- **`Widgets/MultiBoxing/keypress_helper.py`**
  - Helper functions for sending key press commands
  - `CommonKeys` enum with frequently used keys
  - Convenience functions for common operations

### Demo Widget
- **`Widgets/KeypressDemo.py`**
  - Interactive widget to test key press functionality
  - Shows how to send keys to other clients
  - Includes embedded documentation and examples

### Documentation
- **`docs/KEYPRESS_CONTROL.md`**
  - Comprehensive guide to using key press control
  - API reference
  - Common use cases and examples
  - Troubleshooting guide

### Tests
- **`Legacy code and tests/test_keypress_functionality.py`**
  - Validation tests for the keypress functionality
  - Note: Must be run in the game's Python environment

## Quick Start

1. **Enable MultiBoxing** on all clients you want to control
2. **Load the KeypressDemo widget** to test interactively
3. **Use the helper module** in your own widgets:

```python
from Widgets.MultiBoxing.keypress_helper import send_keypress, CommonKeys
from Py4GWCoreLib import GLOBAL_CACHE

my_email = GLOBAL_CACHE.Player.GetAccountEmail()
target_email = "other_account@example.com"

# Send F2 key press to switch equipment set
send_keypress(my_email, target_email, CommonKeys.F2)
```

## Core Implementation

The key press functionality is implemented in:
- **`Widgets/Messaging.py`** - Lines 573-587: `PressKey()` handler
- **`Widgets/Messaging.py`** - Line 1292-1293: Message routing
- **`Py4GWCoreLib/enums_src/Multiboxing_enums.py`** - Line 24: `SharedCommandType.PressKey`
- **`Py4GWCoreLib/enums_src/IO_enums.py`** - Lines 12-216: `Key` enum with all key codes

## How It Works

1. Sender creates a message with key code and repetition count
2. Message is sent via shared memory using `GLOBAL_CACHE.ShMem.SendMessage()`
3. Receiver's Messaging widget processes the message
4. `Keystroke.PressAndRelease()` simulates the key press in-game
5. Message is marked as finished

## Use Cases

- **Equipment Set Switching**: Synchronize gear changes across clients (F1-F4)
- **Hero Management**: Control hero positioning (F5-F8)
- **Skill Activation**: Trigger skills on multiple clients (1-8)
- **Dialog Confirmation**: Accept dialogs simultaneously (ENTER)
- **UI Navigation**: Open windows on all clients (B, H, I, M, etc.)

## See Also

- [Full Documentation](../KEYPRESS_CONTROL.md)
- [Helper Module Source](../../Widgets/MultiBoxing/keypress_helper.py)
- [Demo Widget Source](../../Widgets/KeypressDemo.py)
