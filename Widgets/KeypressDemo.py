"""
Keypress Demo Widget - Demonstrates remote key press functionality

This widget shows how to use the Messaging system to send key press commands
to other clients in a multiboxing setup. 

Use this as a reference for implementing key press functionality in your own widgets.
"""

import PyImGui
from Py4GWCoreLib import GLOBAL_CACHE
from Py4GWCoreLib import Console
from Py4GWCoreLib import ConsoleLog
from Py4GWCoreLib.enums_src.Multiboxing_enums import SharedCommandType
from Py4GWCoreLib.enums_src.IO_enums import Key

MODULE_NAME = "KeypressDemo"

# State variables
selected_account_index = [0]
selected_key_index = [0]
repetition_count = [1]

# Common keys that users might want to send
COMMON_KEYS = [
    ("F1 (Equipment Set 1)", Key.F1.value),
    ("F2 (Equipment Set 2)", Key.F2.value),
    ("F3 (Equipment Set 3)", Key.F3.value),
    ("F4 (Equipment Set 4)", Key.F4.value),
    ("F5 (Hero 1)", Key.F5.value),
    ("F6 (Hero 2)", Key.F6.value),
    ("F7 (Hero 3)", Key.F7.value),
    ("F8 (All Heroes)", Key.F8.value),
    ("1 (Skill Slot 1)", Key.One.value),
    ("2 (Skill Slot 2)", Key.Two.value),
    ("3 (Skill Slot 3)", Key.Three.value),
    ("4 (Skill Slot 4)", Key.Four.value),
    ("5 (Skill Slot 5)", Key.Five.value),
    ("6 (Skill Slot 6)", Key.Six.value),
    ("7 (Skill Slot 7)", Key.Seven.value),
    ("8 (Skill Slot 8)", Key.Eight.value),
    ("ENTER", Key.Enter.value),
    ("ESCAPE", Key.Escape.value),
    ("SPACE", Key.Space.value),
    ("B (Bags)", Key.B.value),
    ("H (Heroes)", Key.H.value),
    ("I (Inventory)", Key.I.value),
    ("M (Map)", Key.M.value),
]

def send_keypress_message(sender_email: str, receiver_email: str, key_code: int, repetitions: int = 1):
    """
    Send a key press command to another client.
    
    Args:
        sender_email: Your account email
        receiver_email: Target account email
        key_code: Virtual key code to press
        repetitions: Number of times to press the key
    """
    if not sender_email or not receiver_email:
        ConsoleLog(MODULE_NAME, "Invalid sender or receiver email", Console.MessageType.Error)
        return
    
    if sender_email == receiver_email:
        ConsoleLog(MODULE_NAME, "Cannot send key press to yourself", Console.MessageType.Warning)
        return
    
    params = (float(key_code), float(repetitions), 0.0, 0.0)
    GLOBAL_CACHE.ShMem.SendMessage(
        sender_email,
        receiver_email,
        SharedCommandType.PressKey,
        params
    )
    
    ConsoleLog(
        MODULE_NAME, 
        f"Sent key press command (code: {hex(key_code)}, reps: {repetitions}) to {receiver_email}",
        Console.MessageType.Info
    )


def main():
    """Main function called every frame when widget is enabled"""
    global selected_account_index, selected_key_index, repetition_count
    
    if PyImGui.begin("Keypress Demo"):
        PyImGui.text_wrapped(
            "This widget demonstrates how to send key press commands to other clients "
            "in a multiboxing setup. Select a target account, choose a key, and click Send."
        )
        PyImGui.separator()
        
        # Get current account
        my_email = GLOBAL_CACHE.Player.GetAccountEmail()
        if not my_email:
            PyImGui.text_colored(1.0, 0.0, 0.0, 1.0, "Error: Could not get account email")
            PyImGui.end()
            return
        
        PyImGui.text(f"Your account: {my_email}")
        PyImGui.separator()
        
        # Get all accounts
        all_accounts = GLOBAL_CACHE.ShMem.GetAllAccountData()
        if not all_accounts:
            PyImGui.text_colored(1.0, 1.0, 0.0, 1.0, "No other accounts found in shared memory")
            PyImGui.end()
            return
        
        # Filter out current account and create list of targets
        target_accounts = [
            (acc.AccountEmail, acc.CharacterName) 
            for acc in all_accounts 
            if acc.AccountEmail and acc.AccountEmail != my_email
        ]
        
        if not target_accounts:
            PyImGui.text_colored(1.0, 1.0, 0.0, 1.0, "No other accounts available")
            PyImGui.text_wrapped("Make sure other clients are running with MultiBoxing enabled")
            PyImGui.end()
            return
        
        # Account selection
        PyImGui.text("Select target account:")
        account_names = [f"{email} ({char})" for email, char in target_accounts]
        
        # Ensure index is valid
        if selected_account_index[0] >= len(target_accounts):
            selected_account_index[0] = 0
        
        selected_account_index[0] = PyImGui.combo(
            "##account", 
            selected_account_index[0], 
            account_names
        )
        
        PyImGui.separator()
        
        # Key selection
        PyImGui.text("Select key to send:")
        key_names = [name for name, _ in COMMON_KEYS]
        
        # Ensure index is valid
        if selected_key_index[0] >= len(COMMON_KEYS):
            selected_key_index[0] = 0
        
        selected_key_index[0] = PyImGui.combo(
            "##key",
            selected_key_index[0],
            key_names
        )
        
        PyImGui.separator()
        
        # Repetition count
        PyImGui.text("Repetitions:")
        repetition_count[0] = PyImGui.slider_int(
            "##reps",
            repetition_count[0],
            1,
            10
        )
        
        PyImGui.separator()
        
        # Send button
        if PyImGui.button("Send Key Press", 200, 30):
            target_email = target_accounts[selected_account_index[0]][0]
            key_code = COMMON_KEYS[selected_key_index[0]][1]
            
            send_keypress_message(
                my_email,
                target_email,
                key_code,
                repetition_count[0]
            )
        
        PyImGui.separator()
        
        # Info section
        if PyImGui.collapsing_header("How to use"):
            PyImGui.text_wrapped(
                "1. Make sure MultiBoxing is enabled on all clients\n"
                "2. Select the target account you want to control\n"
                "3. Choose which key to press (e.g., F2 for equipment set 2)\n"
                "4. Set the number of repetitions if needed\n"
                "5. Click 'Send Key Press'\n\n"
                "The target client will receive the message and press the key in-game."
            )
        
        if PyImGui.collapsing_header("Common Use Cases"):
            PyImGui.text_wrapped(
                "• Equipment Set Switching (F1-F4)\n"
                "• Hero Management (F5-F8)\n"
                "• Skill Activation (1-8)\n"
                "• Opening Inventory/Map/Heroes (B/M/H)\n"
                "• Dialog Confirmation (ENTER)\n"
                "• Closing Windows (ESCAPE)"
            )
        
        if PyImGui.collapsing_header("Example Code"):
            PyImGui.text_wrapped(
                "# Send F2 key press to another account\n"
                "from Py4GWCoreLib import GLOBAL_CACHE\n"
                "from Py4GWCoreLib.enums_src.Multiboxing_enums import SharedCommandType\n"
                "from Py4GWCoreLib.enums_src.IO_enums import Key\n\n"
                "my_email = GLOBAL_CACHE.Player.GetAccountEmail()\n"
                "target_email = 'other@example.com'\n"
                "params = (float(Key.F2.value), 1.0, 0.0, 0.0)\n"
                "GLOBAL_CACHE.ShMem.SendMessage(\n"
                "    my_email, target_email,\n"
                "    SharedCommandType.PressKey, params\n"
                ")"
            )
    
    PyImGui.end()


if __name__ == "__main__":
    main()
