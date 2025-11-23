# Key Press Control via Messaging Widget

## Overview

The Messaging widget system supports sending key press commands between clients in a multiboxing setup. This allows one client to remotely control key presses on another client, which is useful for synchronized actions like equipment switching, skill usage, or UI interactions.

## Features

- **Remote Key Control**: One client can request another to press any key
- **Repetition Support**: Keys can be pressed multiple times with a single command
- **All Keys Are Supported**: Function keys, number keys, letters, control keys, etc.
- **Synchronization**: Built-in delays between repetitions for reliable execution

## How It Works

The key press functionality uses the existing `SharedCommandType.PressKey` message type:

1. **Sender** creates a message with the key code and optional repetition count
2. **Message** is sent via shared memory to the target client
3. **Receiver** processes the message and simulates the key press(es) in-game
4. **Confirmation** is logged when the key press is completed

## Quick Start

### Basic Usage

```python
from Py4GWCoreLib import GLOBAL_CACHE
from Py4GWCoreLib.enums_src.Multiboxing_enums import SharedCommandType
from Py4GWCoreLib.enums_src.IO_enums import Key

# Get your account email
my_email = GLOBAL_CACHE.Player.GetAccountEmail()

# Target account email
target_email = "other_account@example.com"

# Send F2 key press (equipment set 2)
params = (float(Key.F2.value), 1.0, 0.0, 0.0)  # (key_code, repetitions, unused, unused)
GLOBAL_CACHE.ShMem.SendMessage(
    my_email,           # sender
    target_email,       # receiver
    SharedCommandType.PressKey,
    params
)
```

### Using the Helper Module

For easier usage, import the helper module:

```python
from Widgets.MultiBoxing.keypress_helper import send_keypress, CommonKeys

my_email = GLOBAL_CACHE.Player.GetAccountEmail()
target_email = "other_account@example.com"

# Send F2 key press
send_keypress(my_email, target_email, CommonKeys.F2)

# Send ENTER key 3 times
send_keypress(my_email, target_email, CommonKeys.ENTER, repetitions=3)

# Send to all clients
from Widgets.MultiBoxing.keypress_helper import send_keypress_to_all
send_keypress_to_all(my_email, CommonKeys.F1)
```

### Using the Demo Widget

A demo widget is provided in `Widgets/KeypressDemo.py` that shows:
- How to select target accounts
- How to choose keys from a list
- How to set repetition counts
- Real-time testing of key press commands

Enable the widget to test the functionality interactively.

## Common Key Codes

### Function Keys (Equipment Sets, Heroes)
```python
Key.F1.value   # 0x70 - Equipment Set 1
Key.F2.value   # 0x71 - Equipment Set 2
Key.F3.value   # 0x72 - Equipment Set 3
Key.F4.value   # 0x73 - Equipment Set 4
Key.F5.value   # 0x74 - Hero 1
Key.F6.value   # 0x75 - Hero 2
Key.F7.value   # 0x76 - Hero 3
Key.F8.value   # 0x77 - All Heroes
```

### Number Keys (Skill Slots)
```python
Key.One.value    # 0x31 - Skill Slot 1
Key.Two.value    # 0x32 - Skill Slot 2
Key.Three.value  # 0x33 - Skill Slot 3
Key.Four.value   # 0x34 - Skill Slot 4
Key.Five.value   # 0x35 - Skill Slot 5
Key.Six.value    # 0x36 - Skill Slot 6
Key.Seven.value  # 0x37 - Skill Slot 7
Key.Eight.value  # 0x38 - Skill Slot 8
```

### Control Keys
```python
Key.Enter.value    # 0x0D - Confirm dialogs
Key.Escape.value   # 0x1B - Cancel/Close
Key.Space.value    # 0x20 - Jump/Interact
Key.Tab.value      # 0x09 - Target cycling
```

### Letter Keys (UI Shortcuts)
```python
Key.B.value  # 0x42 - Open Bags
Key.H.value  # 0x48 - Open Heroes
Key.I.value  # 0x49 - Open Inventory
Key.M.value  # 0x4D - Open Map
Key.K.value  # 0x4B - Open Skills
Key.P.value  # 0x50 - Open Party
```

## Message Parameters

The `PressKey` message accepts 4 float parameters:

| Index | Name | Type | Description | Required |
|-------|------|------|-------------|----------|
| 0 | key_code | int (as float) | Virtual key code to press | Yes |
| 1 | repetitions | int (as float) | Number of times to press (default: 1) | No |
| 2 | unused | float | Reserved for future use | No |
| 3 | unused | float | Reserved for future use | No |

## Use Cases

### Equipment Set Switching
Synchronize equipment changes across multiple clients:
```python
# Switch all clients to equipment set 2
for account in all_accounts:
    if account.AccountEmail != my_email:
        send_keypress(my_email, account.AccountEmail, CommonKeys.F2)
```

### Hero Management
Control hero positioning on multiple clients:
```python
# Flag all heroes (F8) on all clients
send_keypress_to_all(my_email, CommonKeys.F8, exclude_sender=False)
```

### Skill Activation
Trigger skills on multiple clients:
```python
# Use skill slot 1 on all clients
send_keypress_to_all(my_email, CommonKeys.NUM_1)
```

### Dialog Confirmation
Accept dialogs on all clients:
```python
# Press ENTER on all clients to confirm
send_keypress_to_all(my_email, CommonKeys.ENTER)
```

### UI Navigation
Open inventory on all clients:
```python
# Press I to open inventory
send_keypress_to_all(my_email, Key.I.value)
```

## Implementation Details

### Message Handler

The key press handler is located in `Widgets/Messaging.py`:

```python
def PressKey(index, message):
    ConsoleLog(MODULE_NAME, f"Processing PressKey message: {message}", Console.MessageType.Info, False)
    GLOBAL_CACHE.ShMem.MarkMessageAsRunning(message.ReceiverEmail, index)

    key_id = int(message.Params[0])
    repetition = int(message.Params[1]) if len(message.Params) > 1 else 1

    if key_id:
        for _ in range(repetition):
            Keystroke.PressAndRelease(key_id)
            yield from Routines.Yield.wait(100)

    GLOBAL_CACHE.ShMem.MarkMessageAsFinished(message.ReceiverEmail, index)
    ConsoleLog(MODULE_NAME, "PressKey message processed and finished.", Console.MessageType.Info, False)
```

### Key Press Execution

- Uses `Keystroke.PressAndRelease(key_id)` to simulate the key press
- 100ms delay between repetitions for reliability
- Non-blocking coroutine execution
- Proper message lifecycle management (Running → Finished)

### Timing

- **Message Processing**: Immediate (next frame)
- **Key Press Delay**: 100ms between each repetition
- **Total Time**: ~100ms × repetitions

## Best Practices

1. **Verify Account Emails**: Always check that sender and receiver emails are valid
2. **Avoid Self-Send**: Don't send key press messages to your own account
3. **Use Delays**: When sending multiple different keys, add delays between sends
4. **Test First**: Use the KeypressDemo widget to test before integrating
5. **Handle Errors**: Check that shared memory is available and accounts are online
6. **Use Common Keys**: Prefer the `CommonKeys` enum for readability

## Troubleshooting

### Key Press Not Working

1. **Check Shared Memory**: Ensure MultiBoxing is enabled on both clients
2. **Verify Account Email**: Make sure the target account email is correct
3. **Check Message Queue**: Look at the Messaging widget to see if messages are stuck
4. **Game Focus**: Some keys may only work when the game window has focus

### Delayed Execution

- Key presses are queued and executed in order
- If many messages are pending, there may be a delay
- Each repetition adds 100ms to execution time

### Wrong Key Pressed

- Verify you're using the correct key code (e.g., `Key.F2.value` not just `2`)
- Check the Key enum for the exact value
- Use hex values for debugging (e.g., `0x71` for F2)

## Advanced Usage

### Custom Key Sequences

```python
# Send a sequence of keys with delays
def send_key_sequence(sender, receiver, keys_and_delays):
    for key, delay_ms in keys_and_delays:
        send_keypress(sender, receiver, key)
        yield from Routines.Yield.wait(delay_ms)

# Example: Open heroes (H), select hero 1 (F5), use skill 1 (1)
sequence = [
    (Key.H.value, 500),
    (Key.F5.value, 300),
    (Key.One.value, 100),
]
yield from send_key_sequence(my_email, target_email, sequence)
```

### Conditional Key Presses

```python
# Only send if target is in specific map
target_account = GLOBAL_CACHE.ShMem.GetAccountDataFromEmail(target_email)
if target_account and target_account.MapID == 77:  # House zu Heltzer
    send_keypress(my_email, target_email, CommonKeys.F1)
```

### Broadcasting to Specific Group

```python
# Send to all accounts except specific ones
excluded_emails = {"email1@example.com", "email2@example.com"}

for account in GLOBAL_CACHE.ShMem.GetAllAccountData():
    if account.AccountEmail and account.AccountEmail not in excluded_emails:
        send_keypress(my_email, account.AccountEmail, CommonKeys.F2)
```

## API Reference

### Helper Functions

#### `send_keypress(sender_email, receiver_email, key_code, repetitions=1)`
Send a key press to a specific account.

#### `send_keypress_to_all(sender_email, key_code, repetitions=1, exclude_sender=True)`
Send a key press to all accounts.

#### `send_function_key(sender_email, receiver_email, function_key_number)`
Send function key F1-F12 by number.

#### `send_equipment_set_key(sender_email, receiver_email, equipment_set)`
Send equipment set switch (F1-F4) by set number.

### Constants

#### `CommonKeys`
Enum of frequently used key codes for convenience.

#### `Key`
Full enum of all virtual key codes (from `IO_enums.py`).

## See Also

- `Widgets/Messaging.py` - Message processing implementation
- `Widgets/MultiBoxing/keypress_helper.py` - Helper functions
- `Widgets/KeypressDemo.py` - Interactive demo widget
- `Py4GWCoreLib/enums_src/IO_enums.py` - Full list of key codes
- `Py4GWCoreLib/enums_src/Multiboxing_enums.py` - Message types
