# Bot Example: Synchronized Equipment Switching

This example demonstrates how to use the key press functionality in a bot to synchronize equipment changes across multiple clients.

## Use Case: Farming Bot with Equipment Set Switching

When farming with multiple clients, you may want all clients to switch equipment sets simultaneously (e.g., switching from farming gear to combat gear when encountering enemies).

## Example Bot Code

```python
"""
Example Bot: Synchronized Equipment Switching
Demonstrates using keypress_helper in a multiboxing bot
"""

import Py4GW
from Py4GWCoreLib import GLOBAL_CACHE
from Py4GWCoreLib import Routines
from Py4GWCoreLib import Console
from Py4GWCoreLib import ConsoleLog
from Widgets.MultiBoxing.keypress_helper import send_keypress_to_all, CommonKeys

MODULE_NAME = "Equipment Sync Bot"

# Bot configuration
FARMING_EQUIPMENT_SET = 1  # F1 key
COMBAT_EQUIPMENT_SET = 2   # F2 key

# Track current state
current_equipment_set = [FARMING_EQUIPMENT_SET]
is_in_combat = [False]


def switch_all_equipment_sets(set_number: int):
    """
    Switch equipment set on all clients in the multiboxing setup.
    
    Args:
        set_number: Equipment set number (1-4 for F1-F4)
    """
    my_email = GLOBAL_CACHE.Player.GetAccountEmail()
    
    if not my_email:
        ConsoleLog(MODULE_NAME, "Could not get account email", Console.MessageType.Error)
        return
    
    # Determine which function key to send (F1-F4)
    if set_number == 1:
        key = CommonKeys.F1
    elif set_number == 2:
        key = CommonKeys.F2
    elif set_number == 3:
        key = CommonKeys.F3
    elif set_number == 4:
        key = CommonKeys.F4
    else:
        ConsoleLog(MODULE_NAME, f"Invalid equipment set: {set_number}", Console.MessageType.Error)
        return
    
    # Send to all clients (including self)
    send_keypress_to_all(my_email, key, repetitions=1, exclude_sender=False)
    
    ConsoleLog(
        MODULE_NAME, 
        f"Switched all clients to equipment set {set_number}",
        Console.MessageType.Info
    )


def check_combat_status():
    """Check if we're in combat and switch equipment accordingly"""
    global current_equipment_set, is_in_combat
    
    # Check if enemies are nearby
    enemies_nearby = len(GLOBAL_CACHE.Agent.GetNearbyFoes(1000)) > 0
    
    # If we just entered combat
    if enemies_nearby and not is_in_combat[0]:
        ConsoleLog(MODULE_NAME, "Enemies detected! Switching to combat equipment", Console.MessageType.Warning)
        switch_all_equipment_sets(COMBAT_EQUIPMENT_SET)
        current_equipment_set[0] = COMBAT_EQUIPMENT_SET
        is_in_combat[0] = True
        yield from Routines.Yield.wait(500)  # Wait for equipment switch
    
    # If we just left combat
    elif not enemies_nearby and is_in_combat[0]:
        ConsoleLog(MODULE_NAME, "Combat ended. Switching to farming equipment", Console.MessageType.Info)
        switch_all_equipment_sets(FARMING_EQUIPMENT_SET)
        current_equipment_set[0] = FARMING_EQUIPMENT_SET
        is_in_combat[0] = False
        yield from Routines.Yield.wait(500)  # Wait for equipment switch


def main():
    """Main bot loop"""
    try:
        # Only run in explorable areas
        if not Routines.Checks.Map.IsExplorable():
            return
        
        # Check combat status every frame
        yield from check_combat_status()
        
    except Exception as e:
        Py4GW.Console.Log(MODULE_NAME, f"Error: {str(e)}", Py4GW.Console.MessageType.Error)


if __name__ == "__main__":
    main()
```

## More Advanced Example: Party Coordination Bot

```python
"""
Advanced Example: Party Coordination Bot
Demonstrates multiple key press use cases in a single bot
"""

import Py4GW
from Py4GWCoreLib import GLOBAL_CACHE
from Py4GWCoreLib import Routines
from Py4GWCoreLib import Console
from Py4GWCoreLib import ConsoleLog
from Widgets.MultiBoxing.keypress_helper import (
    send_keypress_to_all, 
    send_keypress,
    CommonKeys
)

MODULE_NAME = "Party Coordinator"


def accept_quest_on_all_clients():
    """Press ENTER on all clients to accept quest dialog"""
    my_email = GLOBAL_CACHE.Player.GetAccountEmail()
    send_keypress_to_all(my_email, CommonKeys.ENTER, repetitions=1, exclude_sender=False)
    ConsoleLog(MODULE_NAME, "Sent ENTER to all clients for quest acceptance", Console.MessageType.Info)


def flag_all_heroes():
    """Press F8 on all clients to flag all heroes"""
    my_email = GLOBAL_CACHE.Player.GetAccountEmail()
    send_keypress_to_all(my_email, CommonKeys.F8, repetitions=1, exclude_sender=False)
    ConsoleLog(MODULE_NAME, "Flagged all heroes on all clients", Console.MessageType.Info)


def use_skill_on_all_clients(skill_slot: int):
    """
    Use a specific skill slot on all clients
    
    Args:
        skill_slot: Skill slot number (1-8)
    """
    my_email = GLOBAL_CACHE.Player.GetAccountEmail()
    
    # Map skill slot to number key
    skill_keys = {
        1: CommonKeys.NUM_1,
        2: CommonKeys.NUM_2,
        3: CommonKeys.NUM_3,
        4: CommonKeys.NUM_4,
        5: CommonKeys.NUM_5,
        6: CommonKeys.NUM_6,
        7: CommonKeys.NUM_7,
        8: CommonKeys.NUM_8,
    }
    
    if skill_slot in skill_keys:
        send_keypress_to_all(my_email, skill_keys[skill_slot], exclude_sender=False)
        ConsoleLog(MODULE_NAME, f"All clients using skill slot {skill_slot}", Console.MessageType.Info)


def open_inventory_on_follower(follower_email: str):
    """Open inventory (I key) on a specific follower client"""
    my_email = GLOBAL_CACHE.Player.GetAccountEmail()
    send_keypress(my_email, follower_email, CommonKeys.I)
    ConsoleLog(MODULE_NAME, f"Opened inventory on {follower_email}", Console.MessageType.Info)


def main():
    """
    Example usage in a bot
    
    This demonstrates various scenarios where you might use key presses
    """
    
    # Example 1: Accept quest on all clients when NPC dialog appears
    if GLOBAL_CACHE.UI.IsNPCDialogVisible():
        yield from Routines.Yield.wait(500)  # Wait for dialog to fully load
        accept_quest_on_all_clients()
        yield from Routines.Yield.wait(1000)  # Wait after accepting
    
    # Example 2: Flag heroes before entering combat
    enemies = GLOBAL_CACHE.Agent.GetNearbyFoes(1500)
    if len(enemies) > 0 and len(enemies) < 10:  # Only if manageable group
        flag_all_heroes()
        yield from Routines.Yield.wait(500)
    
    # Example 3: Synchronized skill usage (e.g., all clients use skill 1)
    # Uncomment to enable
    # if some_condition:
    #     use_skill_on_all_clients(1)
    #     yield from Routines.Yield.wait(1000)


if __name__ == "__main__":
    main()
```

## Common Bot Use Cases

### 1. Quest Automation
```python
# Accept quest on all clients
send_keypress_to_all(my_email, CommonKeys.ENTER)

# Close quest dialog with ESC
send_keypress_to_all(my_email, CommonKeys.ESCAPE)
```

### 2. Equipment Management
```python
from Widgets.MultiBoxing.keypress_helper import send_equipment_set_key

# Switch all to equipment set 2
for account in all_accounts:
    send_equipment_set_key(my_email, account.AccountEmail, 2)
```

### 3. Hero Control
```python
# Flag hero 1 on all clients
send_keypress_to_all(my_email, CommonKeys.F5)

# Flag all heroes
send_keypress_to_all(my_email, CommonKeys.F8)
```

### 4. Synchronized Skill Usage
```python
# All clients use skill slot 1
send_keypress_to_all(my_email, CommonKeys.NUM_1)

# Wait for skill to activate
yield from Routines.Yield.wait(1000)

# All clients use skill slot 2
send_keypress_to_all(my_email, CommonKeys.NUM_2)
```

### 5. UI Navigation
```python
# Open inventory on all clients
send_keypress_to_all(my_email, CommonKeys.I)

# Open map on all clients
send_keypress_to_all(my_email, CommonKeys.M)

# Open hero panel
send_keypress_to_all(my_email, CommonKeys.H)
```

## Best Practices for Bots

1. **Add Delays**: Always add delays after sending key presses to allow actions to complete
   ```python
   send_keypress_to_all(my_email, CommonKeys.F2)
   yield from Routines.Yield.wait(500)  # Wait for equipment switch
   ```

2. **Check Conditions**: Verify the game state before sending keys
   ```python
   if GLOBAL_CACHE.UI.IsNPCDialogVisible():
       send_keypress_to_all(my_email, CommonKeys.ENTER)
   ```

3. **Error Handling**: Wrap key press calls in try-except blocks
   ```python
   try:
       send_keypress_to_all(my_email, CommonKeys.F1)
   except Exception as e:
       ConsoleLog(MODULE_NAME, f"Error: {e}", Console.MessageType.Error)
   ```

4. **Logging**: Log key press actions for debugging
   ```python
   ConsoleLog(MODULE_NAME, "Switching equipment sets", Console.MessageType.Info)
   send_keypress_to_all(my_email, CommonKeys.F2)
   ```

5. **State Tracking**: Keep track of what state your bot is in
   ```python
   current_equipment_set = [1]
   
   if should_switch_to_combat:
       send_keypress_to_all(my_email, CommonKeys.F2)
       current_equipment_set[0] = 2
   ```

## Integration with Existing Bots

To add key press functionality to an existing bot:

1. Import the helper module:
   ```python
   from Widgets.MultiBoxing.keypress_helper import send_keypress_to_all, CommonKeys
   ```

2. Add key press calls where needed:
   ```python
   # In your existing bot logic
   if need_to_switch_equipment:
       send_keypress_to_all(my_email, CommonKeys.F2)
       yield from Routines.Yield.wait(500)
   ```

3. Test thoroughly with the KeypressDemo widget first

## Troubleshooting

- **Keys not working**: Ensure MultiBoxing is enabled on all clients
- **Delayed execution**: Add longer waits between key presses
- **Wrong key pressed**: Double-check you're using the correct `CommonKeys` constant
- **Self-targeting**: Use `exclude_sender=True` if you don't want to affect your own client

## See Also

- [Main Documentation](../KEYPRESS_CONTROL.md)
- [Helper Module Source](../../Widgets/MultiBoxing/keypress_helper.py)
- [Demo Widget](../../Widgets/KeypressDemo.py)
