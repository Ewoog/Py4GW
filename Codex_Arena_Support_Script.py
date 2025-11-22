"""
Codex Arena Support Script for Guild Wars

This script runs on non-leader accounts in a party and listens for commands from the leader.
It handles:
- Leaving party
- Resigning
- Equipment Set switching
- Auto Combat enabling/disabling

The support script should be run on all accounts except the two team leaders.
"""

from Py4GWCoreLib import *
import PyImGui, Py4GW
import time
from typing import Generator, Any

BOT_NAME = "Codex Arena Support"

# Support script commands - must match main bot
SUPPORT_COMMAND = SharedCommandType.CustomBehaviors

# Signal type values - must match main bot
SIGNAL_LEAVE_PARTY = 5.0
SIGNAL_RESIGN = 6.0
SIGNAL_EQUIP_SET_1 = 7.0
SIGNAL_EQUIP_SET_2 = 8.0
SIGNAL_AUTO_COMBAT_ON = 9.0
SIGNAL_AUTO_COMBAT_OFF = 10.0

# Configuration class for support script
class SupportConfig:
    """Configuration for the support script."""
    def __init__(self):
        self.leader_email = ""  # Email of the party leader to listen to
        self.leader_email_index = 0  # Index for combo box selection
        self.last_command = ""  # Last command received
        self.auto_combat_enabled = False  # Current auto combat state

config = SupportConfig()

bot = Botting(
    BOT_NAME,
    upkeep_auto_inventory_management_active=False,
    upkeep_auto_combat_active=False,
    upkeep_auto_loot_active=False,
)


def get_my_email() -> str:
    """Get the current account email."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    return GLOBAL_CACHE.Player.GetAccountEmail()


def get_available_accounts_with_names() -> list:
    """Get list of all account emails with character names from shared memory."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    my_email = get_my_email()
    
    try:
        all_accounts = GLOBAL_CACHE.ShMem.GetAllAccountData()
        if not all_accounts:
            return []
        
        account_data = []
        for account in all_accounts:
            if account.AccountEmail != my_email:
                char_name = account.CharacterName if account.CharacterName else "Unknown"
                display_name = f"{char_name} ({account.AccountEmail})"
                account_data.append((account.AccountEmail, display_name))
        
        return account_data
    except Exception as e:
        Py4GW.Console.Log(BOT_NAME, f"Failed to get accounts from shared memory: {e}", 
                         Py4GW.Console.MessageType.Warning)
        return []


def check_leader_commands() -> tuple[str, float]:
    """Check for commands from the leader.
    Returns tuple of (command_type, param1)."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    my_email = get_my_email()
    
    # Check for next message
    msg_index, msg = GLOBAL_CACHE.ShMem.PreviewNextMessage(my_email, include_running=False)
    
    if msg and msg.Command == SUPPORT_COMMAND:
        command_type = ""
        param1 = 0.0
        
        # Check bounds before accessing params
        if len(msg.Params) == 0:
            return ("", 0.0)
        
        if msg.Params[0] == SIGNAL_LEAVE_PARTY:
            command_type = "LEAVE"
        elif msg.Params[0] == SIGNAL_RESIGN:
            command_type = "RESIGN"
        elif msg.Params[0] == SIGNAL_EQUIP_SET_1:
            command_type = "EQUIP_SET_1"
        elif msg.Params[0] == SIGNAL_EQUIP_SET_2:
            command_type = "EQUIP_SET_2"
        elif msg.Params[0] == SIGNAL_AUTO_COMBAT_ON:
            command_type = "AUTO_COMBAT_ON"
        elif msg.Params[0] == SIGNAL_AUTO_COMBAT_OFF:
            command_type = "AUTO_COMBAT_OFF"
        
        if command_type:
            if len(msg.Params) > 1:
                param1 = msg.Params[1]
            GLOBAL_CACHE.ShMem.MarkMessageAsFinished(my_email, msg_index)
            return (command_type, param1)
    
    return ("", 0.0)


def equip_set(set_number: int) -> Generator:
    """Equip the specified equipment set (1 or 2)."""
    from Py4GWCoreLib.Routines import Routines
    yield from Routines.Yield.Keybinds.ActivateWeaponSet(set_number)
    yield from Routines.Yield.wait(500)


def handle_leave_party() -> Generator:
    """Leave the current party."""
    from Py4GWCoreLib import Party
    from Py4GWCoreLib.Routines import Routines
    
    Py4GW.Console.Log(BOT_NAME, "Received LEAVE command - leaving party...", 
                     Py4GW.Console.MessageType.Info)
    Party.LeaveParty()
    yield from Routines.Yield.wait(2000)


def handle_resign() -> Generator:
    """Return to outpost (resign)."""
    from Py4GWCoreLib import Party
    from Py4GWCoreLib.Routines import Routines
    
    Py4GW.Console.Log(BOT_NAME, "Received RESIGN command - returning to outpost...", 
                     Py4GW.Console.MessageType.Info)
    Party.ReturnToOutpost()
    yield from Routines.Yield.wait(5000)


def support_main_loop(bot: Botting) -> None:
    """Main loop for the support script - listens for commands from leader."""
    def _support_loop():
        from Py4GWCoreLib.Routines import Routines
        
        while bot.config.fsm_running:
            # Check for commands from leader
            command, param1 = check_leader_commands()
            
            if command:
                config.last_command = command
                
                if command == "LEAVE":
                    yield from handle_leave_party()
                elif command == "RESIGN":
                    yield from handle_resign()
                elif command == "EQUIP_SET_1":
                    Py4GW.Console.Log(BOT_NAME, "Received EQUIP SET 1 command", 
                                     Py4GW.Console.MessageType.Info)
                    yield from equip_set(1)
                elif command == "EQUIP_SET_2":
                    Py4GW.Console.Log(BOT_NAME, "Received EQUIP SET 2 command", 
                                     Py4GW.Console.MessageType.Info)
                    yield from equip_set(2)
                elif command == "AUTO_COMBAT_ON":
                    Py4GW.Console.Log(BOT_NAME, "Received AUTO COMBAT ON command", 
                                     Py4GW.Console.MessageType.Info)
                    bot.config.upkeep.auto_combat.set_now("active", True)
                    config.auto_combat_enabled = True
                elif command == "AUTO_COMBAT_OFF":
                    Py4GW.Console.Log(BOT_NAME, "Received AUTO COMBAT OFF command", 
                                     Py4GW.Console.MessageType.Info)
                    bot.config.upkeep.auto_combat.set_now("active", False)
                    config.auto_combat_enabled = False
            
            # Wait before checking again
            yield from Routines.Yield.wait(500)
    
    bot.States.AddCustomState(lambda: _support_loop(), "Support Script Loop")


def create_support_routine(bot: Botting) -> None:
    """Setup the support script routine."""
    bot.States.AddHeader(f"{BOT_NAME}")
    support_main_loop(bot)


bot.SetMainRoutine(create_support_routine)


def _draw_settings():
    """Custom settings panel for the support script."""
    import PyImGui
    
    PyImGui.text("Codex Arena Support Script")
    PyImGui.separator()
    
    # Leader email selection with character names
    PyImGui.text("Party Leader Email:")
    available_accounts_data = get_available_accounts_with_names()
    
    if available_accounts_data:
        # Add empty option at the beginning
        account_display = ["(None)"] + [display for _, display in available_accounts_data]
        account_emails = [email for email, _ in available_accounts_data]
        
        # Update index if current leader email is in the list
        if config.leader_email and config.leader_email in account_emails:
            config.leader_email_index = account_emails.index(config.leader_email) + 1
        elif not config.leader_email:
            config.leader_email_index = 0
        
        # Draw combo box
        new_index = PyImGui.combo("##leader_email_combo", config.leader_email_index, account_display)
        
        if new_index != config.leader_email_index:
            config.leader_email_index = new_index
            if new_index == 0:
                config.leader_email = ""
                Py4GW.Console.Log(BOT_NAME, "Leader email cleared.", 
                                Py4GW.Console.MessageType.Info)
            else:
                config.leader_email = account_emails[new_index - 1]
                Py4GW.Console.Log(BOT_NAME, f"Leader email set to: {config.leader_email}", 
                                Py4GW.Console.MessageType.Info)
    else:
        PyImGui.text_colored("No other accounts detected in shared memory", (1, 0.5, 0, 1))
    
    PyImGui.separator()
    PyImGui.text("Status:")
    
    if config.last_command:
        PyImGui.text(f"Last Command: {config.last_command}")
    
    if config.auto_combat_enabled:
        PyImGui.text_colored("Auto Combat: ENABLED", (0, 1, 0, 1))
    else:
        PyImGui.text_colored("Auto Combat: DISABLED", (1, 0, 0, 1))
    
    PyImGui.separator()
    PyImGui.text_wrapped("Instructions: Select your party leader's email and start the script. This account will listen for commands from the leader and execute them automatically.")


# Override the settings tab with custom UI
bot.UI.override_draw_config(lambda: _draw_settings())


def configure():
    """Configure window - called by the framework."""
    global bot
    bot.UI.draw_configure_window()


def main():
    """Main update function - called every frame."""
    bot.Update()
    bot.UI.draw_window()


if __name__ == "__main__":
    main()
