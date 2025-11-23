"""
Helper module for sending key press commands via the Messaging widget system.

This module provides convenient functions to send key press messages to other clients
in a multiboxing setup. One client can request another client to press specific keys
in-game, which is useful for synchronized actions like equipment switching, skill usage,
or UI interactions.

Example usage:
    from Widgets.MultiBoxing.keypress_helper import send_keypress, CommonKeys
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    
    # Send F2 key press to another account
    my_email = GLOBAL_CACHE.Player.GetAccountEmail()
    target_email = "other_account@example.com"
    send_keypress(my_email, target_email, CommonKeys.F2)
    
    # Send ENTER key press with 3 repetitions
    send_keypress(my_email, target_email, CommonKeys.ENTER, repetitions=3)
"""

from enum import IntEnum
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from Py4GWCoreLib.enums_src.Multiboxing_enums import SharedCommandType
from Py4GWCoreLib.enums_src.IO_enums import Key


class CommonKeys(IntEnum):
    """
    Common key codes for Guild Wars game actions.
    These are the most frequently used keys in multiboxing scenarios.
    """
    # Function keys (commonly used for equipment sets, heroes, etc.)
    F1 = Key.F1.value
    F2 = Key.F2.value
    F3 = Key.F3.value
    F4 = Key.F4.value
    F5 = Key.F5.value
    F6 = Key.F6.value
    F7 = Key.F7.value
    F8 = Key.F8.value
    F9 = Key.F9.value
    F10 = Key.F10.value
    F11 = Key.F11.value
    F12 = Key.F12.value
    
    # Number keys (skill bar slots 1-8)
    NUM_1 = Key.One.value
    NUM_2 = Key.Two.value
    NUM_3 = Key.Three.value
    NUM_4 = Key.Four.value
    NUM_5 = Key.Five.value
    NUM_6 = Key.Six.value
    NUM_7 = Key.Seven.value
    NUM_8 = Key.Eight.value
    NUM_9 = Key.Nine.value
    NUM_0 = Key.Zero.value
    
    # Control keys
    ENTER = Key.Enter.value
    ESCAPE = Key.Escape.value
    SPACE = Key.Space.value
    TAB = Key.Tab.value
    BACKSPACE = Key.Backspace.value
    
    # Arrow keys
    UP = Key.UpArrow.value
    DOWN = Key.DownArrow.value
    LEFT = Key.LeftArrow.value
    RIGHT = Key.RightArrow.value
    
    # Letter keys (for chat commands, etc.)
    B = Key.B.value  # Bags/Inventory
    C = Key.C.value  # Character sheet
    H = Key.H.value  # Heroes
    K = Key.K.value  # Skills
    P = Key.P.value  # Party
    I = Key.I.value  # Inventory
    M = Key.M.value  # Map


def send_keypress(sender_email: str, receiver_email: str, key_code: int, repetitions: int = 1) -> None:
    """
    Send a key press command to another client via shared memory messaging.
    
    Args:
        sender_email: Email of the account sending the message (usually your own account)
        receiver_email: Email of the account that should press the key
        key_code: Virtual key code to press (use CommonKeys enum or Key.*.value)
        repetitions: Number of times to press the key (default: 1)
    
    Example:
        # Send F2 key press to switch equipment set
        send_keypress("my_email@example.com", "target@example.com", CommonKeys.F2)
        
        # Send ENTER key 3 times
        send_keypress("my_email@example.com", "target@example.com", CommonKeys.ENTER, 3)
    """
    if not sender_email or not receiver_email:
        raise ValueError("Both sender_email and receiver_email must be provided")
    
    if key_code <= 0:
        raise ValueError(f"Invalid key_code: {key_code}")
    
    if repetitions < 1:
        repetitions = 1
    
    params = (float(key_code), float(repetitions), 0.0, 0.0)
    GLOBAL_CACHE.ShMem.SendMessage(
        sender_email,
        receiver_email,
        SharedCommandType.PressKey,
        params
    )


def send_keypress_to_all(sender_email: str, key_code: int, repetitions: int = 1, exclude_sender: bool = True) -> None:
    """
    Send a key press command to all clients in the multiboxing setup.
    
    Args:
        sender_email: Email of the account sending the message
        key_code: Virtual key code to press (use CommonKeys enum or Key.*.value)
        repetitions: Number of times to press the key (default: 1)
        exclude_sender: If True, don't send the message to yourself (default: True)
    
    Example:
        # Send F1 to all other clients
        send_keypress_to_all("my_email@example.com", CommonKeys.F1)
        
        # Send SPACE to all clients including yourself
        send_keypress_to_all("my_email@example.com", CommonKeys.SPACE, exclude_sender=False)
    """
    all_accounts = GLOBAL_CACHE.ShMem.GetAllAccountData()
    
    for account in all_accounts:
        if not account.AccountEmail:
            continue
        
        if exclude_sender and account.AccountEmail == sender_email:
            continue
        
        send_keypress(sender_email, account.AccountEmail, key_code, repetitions)


def send_function_key(sender_email: str, receiver_email: str, function_key_number: int) -> None:
    """
    Convenience function to send a function key (F1-F12) press.
    
    Args:
        sender_email: Email of the account sending the message
        receiver_email: Email of the account that should press the key
        function_key_number: Function key number (1-12)
    
    Example:
        # Send F2 key press
        send_function_key("my_email@example.com", "target@example.com", 2)
    """
    if function_key_number < 1 or function_key_number > 12:
        raise ValueError(f"Function key number must be between 1 and 12, got {function_key_number}")
    
    # F1 = 0x70, F2 = 0x71, ..., F12 = 0x7B
    key_code = 0x70 + (function_key_number - 1)
    send_keypress(sender_email, receiver_email, key_code)


# For backwards compatibility and convenience
def send_equipment_set_key(sender_email: str, receiver_email: str, equipment_set: int) -> None:
    """
    Send an equipment set switch command (F1-F4).
    
    Equipment sets in Guild Wars are typically mapped to F1-F4 keys.
    
    Args:
        sender_email: Email of the account sending the message
        receiver_email: Email of the account that should switch equipment
        equipment_set: Equipment set number (1-4)
    
    Example:
        # Switch to equipment set 2
        send_equipment_set_key("my_email@example.com", "target@example.com", 2)
    """
    if equipment_set < 1 or equipment_set > 4:
        raise ValueError(f"Equipment set must be between 1 and 4, got {equipment_set}")
    
    send_function_key(sender_email, receiver_email, equipment_set)


# Export all key codes from the Key enum for advanced usage
__all__ = [
    'CommonKeys',
    'send_keypress',
    'send_keypress_to_all',
    'send_function_key',
    'send_equipment_set_key',
    'Key',  # Re-export for advanced usage
]
