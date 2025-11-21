"""
Codex Arena Bot for Guild Wars

This bot automates Codex Arena matches for farming Strategist's Zaishen Strongboxes.
It supports multiboxing with two teams of 4 players each:
- Winning team (Equipment Set 1)
- Losing team (Equipment Set 2)

Features:
- Teams queue simultaneously using shared memory synchronization
- Winning team plays to win, losing team returns to outpost after match
- Tracks Strategist's Zaishen Strongboxes earned (1 per 5 consecutive wins)
- Shuts down after earning 5 strongboxes (daily limit)

Setup:
1. Run this script on the leader of each team (8 accounts total, 2 instances)
2. Manually invite team members to each party (4 per team)
3. Toggle "Is Winning Team" in the GUI appropriately for each instance
4. Set up Equipment Set 1 for winning builds, Set 2 for losing builds
5. Start both bots - they will synchronize and queue together

Requirements:
- Both team leaders must be in Codex Arena outpost
- Equipment sets must be configured beforehand
- Multiboxing must be enabled with shared memory
"""

from Py4GWCoreLib import *
import PyImGui, Py4GW
import time
from typing import Generator, Any

BOT_NAME = "Codex Arena Bot"

# Configuration class for tracking bot state
class CodexConfig:
    """Configuration and state tracking for the Codex Arena bot."""
    def __init__(self):
        self.is_winning_team = True  # Toggle: True = winning team, False = losing team
        self.consecutive_wins = 0  # Consecutive wins counter
        self.strongboxes_earned = 0  # Strategist's Zaishen Strongboxes earned
        self.target_strongboxes = 5  # Strongboxes to earn before stopping (max per day)
        self.synced_queue = False  # Flag for synchronization
        self.in_match = False
        self.ready_to_queue = False
        self.initial_strongbox_count = 0  # Track starting strongbox count

config = CodexConfig()

bot = Botting(
    BOT_NAME,
    upkeep_auto_inventory_management_active=False,
    upkeep_auto_combat_active=False,
    upkeep_auto_loot_active=False,
)

# Custom synchronization command for queue timing
SYNC_QUEUE_COMMAND = SharedCommandType.CustomBehaviors  # Use existing custom command type

# Strategist's Zaishen Strongbox model ID
STRATEGISTS_STRONGBOX_MODEL_ID = 36668


def get_strongbox_count() -> int:
    """Get the current count of Strategist's Zaishen Strongboxes in inventory."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    return GLOBAL_CACHE.Inventory.GetModelCount(STRATEGISTS_STRONGBOX_MODEL_ID)


def get_my_email() -> str:
    """Get the current account email."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    return GLOBAL_CACHE.Player.GetAccountEmail()


def send_sync_signal(signal_type: str):
    """Send synchronization signal to other accounts."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    my_email = get_my_email()
    
    # Signal types: "READY_TO_QUEUE", "QUEUE_NOW", "MATCH_START", "MATCH_END"
    if signal_type == "READY_TO_QUEUE":
        params = (1.0, 0.0, 0.0, 0.0)
    elif signal_type == "QUEUE_NOW":
        params = (2.0, 0.0, 0.0, 0.0)
    elif signal_type == "MATCH_START":
        params = (3.0, 0.0, 0.0, 0.0)
    elif signal_type == "MATCH_END":
        params = (4.0, 0.0, 0.0, 0.0)
    else:
        params = (0.0, 0.0, 0.0, 0.0)
    
    # Send to all other accounts in the same map
    all_accounts = GLOBAL_CACHE.ShMem.GetAllAccountData()
    for account in all_accounts:
        if account.AccountEmail != my_email:
            GLOBAL_CACHE.ShMem.SendMessage(my_email, account.AccountEmail, SYNC_QUEUE_COMMAND, params)


def check_sync_signal() -> str:
    """Check for synchronization signals from other accounts."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    my_email = get_my_email()
    
    # Check for next message
    msg_index, msg = GLOBAL_CACHE.ShMem.PreviewNextMessage(my_email, include_running=False)
    
    if msg and msg.Command == SYNC_QUEUE_COMMAND:
        signal_type = ""
        if msg.Params[0] == 1.0:
            signal_type = "READY_TO_QUEUE"
        elif msg.Params[0] == 2.0:
            signal_type = "QUEUE_NOW"
        elif msg.Params[0] == 3.0:
            signal_type = "MATCH_START"
        elif msg.Params[0] == 4.0:
            signal_type = "MATCH_END"
        
        # Mark message as finished
        if signal_type:
            GLOBAL_CACHE.ShMem.MarkMessageAsFinished(my_email, msg_index)
            return signal_type
    
    return ""


def equip_set(set_number: int) -> Generator:
    """Equip the specified equipment set (1 or 2)."""
    from Py4GWCoreLib.Routines import Routines
    yield from Routines.Yield.Keybinds.ActivateWeaponSet(set_number)
    yield from Routines.Yield.wait(500)


def travel_to_codex_arena() -> Generator:
    """Travel to Codex Arena outpost."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    from Py4GWCoreLib import Map
    from Py4GWCoreLib.Routines import Routines
    
    # Codex Arena map ID
    CODEX_ARENA_MAP_ID = 796
    
    current_map = GLOBAL_CACHE.Map.GetMapID()
    if current_map != CODEX_ARENA_MAP_ID:
        yield from bot.Map._coro_travel(target_map_id=CODEX_ARENA_MAP_ID)
        yield from Routines.Yield.wait(2000)


def enter_queue() -> Generator:
    """Enter the arena queue."""
    from Py4GWCoreLib import Map
    from Py4GWCoreLib.Routines import Routines
    
    # Enter challenge/queue
    Map.EnterChallenge()
    yield from Routines.Yield.wait(1000)


def wait_for_match_start(bot: Botting) -> Generator:
    """Wait until match starts (map changes to explorable)."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    from Py4GWCoreLib import Map
    from Py4GWCoreLib.Routines import Routines
    
    timeout = 300  # 5 minute timeout (in seconds)
    start_time = time.time()
    
    while time.time() - start_time < timeout and bot.config.fsm_running:
        instance_type = GLOBAL_CACHE.Map.GetInstanceType()
        if instance_type == Map.InstanceType.Explorable:
            config.in_match = True
            send_sync_signal("MATCH_START")
            Py4GW.Console.Log(BOT_NAME, "Match started!", Py4GW.Console.MessageType.Success)
            return
        yield from Routines.Yield.wait(1000)
    
    # Timeout - match didn't start
    Py4GW.Console.Log(BOT_NAME, "Timeout waiting for match start.", Py4GW.Console.MessageType.Warning)
    config.in_match = False


def winning_team_logic(bot: Botting) -> Generator:
    """Logic for the winning team - wait for match completion and track strongboxes."""
    from Py4GWCoreLib.Routines import Routines
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    from Py4GWCoreLib import Map
    
    # Get initial strongbox count before match ends
    initial_strongboxes = get_strongbox_count()
    
    # Wait in match for some time (simulating play)
    Py4GW.Console.Log(BOT_NAME, "Winning team in match, waiting for completion...", 
                     Py4GW.Console.MessageType.Info)
    yield from Routines.Yield.wait(30000)  # 30 seconds initial wait
    
    # In a real scenario, the team would play and win
    # For automation, we just wait for the match to end naturally
    # or the game mechanics would handle it
    
    # Wait for match to end (return to outpost)
    timeout = 600  # 10 minute timeout for full match (in seconds)
    start_time = time.time()
    
    while time.time() - start_time < timeout and bot.config.fsm_running:
        instance_type = GLOBAL_CACHE.Map.GetInstanceType()
        if instance_type == Map.InstanceType.Outpost:
            # Match ended, we're back in outpost
            config.in_match = False
            
            # Check for new strongboxes
            current_strongboxes = get_strongbox_count()
            new_strongboxes = current_strongboxes - initial_strongboxes
            
            # Increment consecutive wins
            config.consecutive_wins += 1
            
            # Check if we earned a strongbox (every 5 consecutive wins)
            if new_strongboxes > 0:
                config.strongboxes_earned += new_strongboxes
                Py4GW.Console.Log(BOT_NAME, 
                                f"Strongbox earned! Now have {config.strongboxes_earned}/5 strongboxes ({config.consecutive_wins} consecutive wins).", 
                                Py4GW.Console.MessageType.Success)
                # Reset consecutive wins after earning a strongbox
                if config.consecutive_wins >= 5:
                    config.consecutive_wins = 0
            else:
                Py4GW.Console.Log(BOT_NAME, 
                                f"Victory! {config.consecutive_wins} consecutive wins (need 5 for strongbox).", 
                                Py4GW.Console.MessageType.Success)
            
            send_sync_signal("MATCH_END")
            return
        yield from Routines.Yield.wait(2000)
    
    # Timeout - force return to outpost
    if config.in_match:
        Py4GW.Console.Log(BOT_NAME, "Match timeout, forcing return to outpost...", 
                        Py4GW.Console.MessageType.Warning)
        from Py4GWCoreLib import Party
        Party.ReturnToOutpost()
        yield from Routines.Yield.wait(5000)
        config.in_match = False


def losing_team_logic(bot: Botting) -> Generator:
    """Logic for the losing team - return to outpost after match."""
    from Py4GWCoreLib.Routines import Routines
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    from Py4GWCoreLib import Map, Party
    
    Py4GW.Console.Log(BOT_NAME, "Losing team in match, waiting to return...", 
                     Py4GW.Console.MessageType.Info)
    
    # Wait for match to end (should lose)
    timeout = 600  # 10 minute timeout (in seconds)
    start_time = time.time()
    
    while time.time() - start_time < timeout and bot.config.fsm_running:
        instance_type = GLOBAL_CACHE.Map.GetInstanceType()
        if instance_type == Map.InstanceType.Outpost:
            # Back in outpost after losing
            config.in_match = False
            # Reset consecutive wins on loss (losing team loses, so this doesn't apply to winning team)
            # The losing team doesn't track consecutive wins
            Py4GW.Console.Log(BOT_NAME, "Returned to outpost after loss.", 
                            Py4GW.Console.MessageType.Info)
            send_sync_signal("MATCH_END")
            return
        
        # Check if we need to manually return (after 60 seconds in match)
        if time.time() - start_time > 60 and config.in_match:
            Py4GW.Console.Log(BOT_NAME, "Attempting to return to outpost...", 
                            Py4GW.Console.MessageType.Info)
            Party.ReturnToOutpost()
            yield from Routines.Yield.wait(5000)
            
            # Check if we successfully returned
            if GLOBAL_CACHE.Map.GetInstanceType() == Map.InstanceType.Outpost:
                config.in_match = False
                Py4GW.Console.Log(BOT_NAME, "Successfully returned to outpost.", 
                                Py4GW.Console.MessageType.Success)
                send_sync_signal("MATCH_END")
                return
        
        yield from Routines.Yield.wait(2000)
    
    # Timeout handling
    if config.in_match:
        Py4GW.Console.Log(BOT_NAME, "Timeout in losing team logic, forcing return...", 
                        Py4GW.Console.MessageType.Warning)
        config.in_match = False


def run_codex_match(bot: Botting) -> None:
    """Run a single Codex Arena match cycle."""
    def _run_match():
        from Py4GWCoreLib.Routines import Routines
        
        # Check if we should shut down (earned 5 strongboxes)
        if config.strongboxes_earned >= config.target_strongboxes:
            Py4GW.Console.Log(BOT_NAME, 
                            f"Target reached! Earned {config.strongboxes_earned} strongboxes. Shutting down.", 
                            Py4GW.Console.MessageType.Success)
            bot.Stop()
            return
        
        # Travel to Codex Arena if not there
        yield from travel_to_codex_arena()
        
        # Equip appropriate set
        if config.is_winning_team:
            Py4GW.Console.Log(BOT_NAME, "Equipping Set 1 (Winning Team)", Py4GW.Console.MessageType.Info)
            yield from equip_set(1)
        else:
            Py4GW.Console.Log(BOT_NAME, "Equipping Set 2 (Losing Team)", Py4GW.Console.MessageType.Info)
            yield from equip_set(2)
        
        # Synchronization phase: wait for both teams to be ready
        config.ready_to_queue = True
        send_sync_signal("READY_TO_QUEUE")
        
        Py4GW.Console.Log(BOT_NAME, "Waiting for other team to be ready...", Py4GW.Console.MessageType.Info)
        
        # Wait for confirmation from other team OR timeout
        timeout = 120  # 2 minute timeout (in seconds)
        start_time = time.time()
        other_team_ready = False
        
        while time.time() - start_time < timeout:
            signal = check_sync_signal()
            if signal == "READY_TO_QUEUE":
                other_team_ready = True
                Py4GW.Console.Log(BOT_NAME, "Other team is ready!", Py4GW.Console.MessageType.Info)
                break
            yield from Routines.Yield.wait(500)
        
        if not other_team_ready:
            Py4GW.Console.Log(BOT_NAME, "Timeout waiting for other team. Proceeding anyway...", 
                            Py4GW.Console.MessageType.Warning)
        
        # Brief sync delay to ensure both are ready
        yield from Routines.Yield.wait(1000)
        
        # Both teams enter queue simultaneously
        Py4GW.Console.Log(BOT_NAME, "Entering queue NOW!", Py4GW.Console.MessageType.Info)
        send_sync_signal("QUEUE_NOW")
        yield from enter_queue()
        
        # Wait for match to start
        Py4GW.Console.Log(BOT_NAME, "Waiting for match to start...", Py4GW.Console.MessageType.Info)
        yield from wait_for_match_start(bot)
        
        if not config.in_match:
            # Failed to enter match, retry
            Py4GW.Console.Log(BOT_NAME, "Failed to enter match, retrying...", Py4GW.Console.MessageType.Warning)
            yield from Routines.Yield.wait(3000)
            return
        
        # Execute team-specific logic
        if config.is_winning_team:
            Py4GW.Console.Log(BOT_NAME, "Playing as winning team...", Py4GW.Console.MessageType.Info)
            yield from winning_team_logic(bot)
        else:
            Py4GW.Console.Log(BOT_NAME, "Playing as losing team...", Py4GW.Console.MessageType.Info)
            yield from losing_team_logic(bot)
        
        # Log current progress
        Py4GW.Console.Log(BOT_NAME, 
                        f"Progress: {config.strongboxes_earned}/{config.target_strongboxes} strongboxes ({config.consecutive_wins} consecutive wins)", 
                        Py4GW.Console.MessageType.Info)
        
        # Brief pause before next iteration
        yield from Routines.Yield.wait(3000)
    
    bot.States.AddCustomState(lambda: _run_match(), "Run Codex Match")


def create_bot_routine(bot: Botting) -> None:
    """Setup the bot routine."""
    bot.States.AddHeader(f"{BOT_NAME}")
    # Add the match loop - it will keep repeating until bot is stopped
    for _ in range(100):  # Run up to 100 matches (more than enough for 10 strongboxes)
        run_codex_match(bot)


bot.SetMainRoutine(create_bot_routine)


def _draw_settings():
    """Custom settings panel for the bot."""
    import PyImGui
    
    PyImGui.text("Codex Arena Bot Configuration")
    PyImGui.separator()
    
    # Team role toggle
    new_value = PyImGui.checkbox("Is Winning Team", config.is_winning_team)
    if new_value != config.is_winning_team:
        config.is_winning_team = new_value
        Py4GW.Console.Log(BOT_NAME, f"Team role changed to: {'Winning' if config.is_winning_team else 'Losing'}", 
                        Py4GW.Console.MessageType.Info)
    
    PyImGui.separator()
    PyImGui.text("Progress:")
    PyImGui.text(f"Strongboxes Earned: {config.strongboxes_earned}/{config.target_strongboxes}")
    PyImGui.text(f"Consecutive Wins: {config.consecutive_wins}/5")
    
    # Calculate progress percentage
    progress = config.strongboxes_earned / config.target_strongboxes
    PyImGui.progress_bar(progress, 200, 20, f"{config.strongboxes_earned}/{config.target_strongboxes}")
    
    PyImGui.separator()
    PyImGui.text("Status:")
    
    if config.in_match:
        PyImGui.text_colored("IN MATCH", (0, 1, 0, 1))
    elif config.ready_to_queue:
        PyImGui.text_colored("READY TO QUEUE", (1, 1, 0, 1))
    else:
        PyImGui.text_colored("IDLE", (0.5, 0.5, 0.5, 1))
    
    PyImGui.separator()
    
    # Reset button
    if PyImGui.button("Reset Stats", 150, 25):
        config.strongboxes_earned = 0
        config.consecutive_wins = 0
        Py4GW.Console.Log(BOT_NAME, "Stats reset.", Py4GW.Console.MessageType.Info)
    
    PyImGui.separator()
    PyImGui.text_wrapped("Instructions: Set up two teams of 4. Run one instance with 'Is Winning Team' checked, another with it unchecked. Earn 1 Strategist's Zaishen Strongbox per 5 consecutive wins (max 5/day). Bot stops after earning 5 strongboxes.")


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
