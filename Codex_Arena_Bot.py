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
- Aggressive Mode: When enabled, winning team rushes enemy spawn on all maps

Setup:
1. Run this script on the leader of each team (8 accounts total, 2 instances)
2. Manually invite team members to each party (4 per team)
3. Toggle "Is Winning Team" in the GUI appropriately for each instance
4. Optionally enable "Aggressive Mode" to rush enemy spawn on all maps
5. Set up Equipment Set 1 for winning builds, Set 2 for losing builds
6. Start both bots - they will synchronize and queue together

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

# Arena map IDs and spawn coordinates
CODEX_ARENA_OUTPOST_ID = 796
SEABED_ARENA_MAP_ID = 829
DELDRIMOR_ARENA_MAP_ID = 830

# Additional Codex Arena map IDs
DALESSIO_ARENA_MAP_ID = 823
AMNOON_ARENA_MAP_ID = 824
CHURRANU_ISLAND_ARENA_MAP_ID = 825
FORT_KOGA_MAP_ID = 826
PETRIFIED_ARENA_MAP_ID = 827
HEROES_CRYPT_MAP_ID = 828
BRAWLERS_PIT_MAP_ID = 831
THE_CRAG_MAP_ID = 832
SUNSPEAR_ARENA_MAP_ID = 833
SHING_JEA_ARENA_MAP_ID = 834
ASCALON_ARENA_MAP_ID = 835
SHIVERPEAK_ARENA_MAP_ID = 836

# Movement tolerance for priest location (200 units = close enough to engage)
PRIEST_LOCATION_TOLERANCE = 200

# Movement timeout when traveling to priest location (90 seconds to account for obstacles)
PRIEST_MOVEMENT_TIMEOUT = 90

# Arena spawn coordinates for all Codex Arena maps
# Format: {map_id: {"blue": (x, y), "red": (x, y)}}
PRIEST_COORDINATES = {
    SEABED_ARENA_MAP_ID: {  # [PRIEST] Seabed Arena
        "blue": (9737, 4344),
        "red": (4368, 6953)
    },
    DELDRIMOR_ARENA_MAP_ID: {  # [PRIEST] Deldrimor Arena
        "blue": (-9259.12, 2708.83),
        "red": (-8994.74, 7384.57)
    },
    DALESSIO_ARENA_MAP_ID: {  # D'Alessio Arena
        "blue": (4945.88, -2424.17),
        "red": (4627.75, 3853.27)
    },
    AMNOON_ARENA_MAP_ID: {  # Amnoon Arena
        "blue": (3282.00, 10095.00),
        "red": (-1923.30, 5129.79)
    },
    CHURRANU_ISLAND_ARENA_MAP_ID: {  # Churranu Island Arena
        "blue": (4206.08, -119.03),
        "red": (-886.18, -478.33)
    },
    FORT_KOGA_MAP_ID: {  # Fort Koga
        "blue": (6321.00, 181.00),
        "red": (195.82, -3402.33)
    },
    PETRIFIED_ARENA_MAP_ID: {  # Petrified Arena
        "blue": (1831.88, 1348.83),
        "red": (7198.82, -4076.33)
    },
    HEROES_CRYPT_MAP_ID: {  # Heroes' Crypt
        "blue": (-110.00, -4322.00),
        "red": (3299.88, -5084.17)
    },
    BRAWLERS_PIT_MAP_ID: {  # Brawler's Pit
        "blue": (967.00, 5075.00),
        "red": (4981.82, 5033.67)
    },
    THE_CRAG_MAP_ID: {  # The Crag
        "blue": (6528.88, 4470.83),
        "red": (-2394.18, -2403.33)
    },
    SUNSPEAR_ARENA_MAP_ID: {  # Sunspear Arena
        "blue": (436.00, 2517.00),
        "red": (3731.82, -2301.33)
    },
    SHING_JEA_ARENA_MAP_ID: {  # Shing Jea Arena
        "blue": (-2375.00, -1583.00),
        "red": (2308.82, 2879.67)
    },
    ASCALON_ARENA_MAP_ID: {  # Ascalon Arena
        "blue": (8181.50, -1940.41),
        "red": (4800.82, -6545.33)
    },
    SHIVERPEAK_ARENA_MAP_ID: {  # Shiverpeak Arena
        "blue": (9344.00, 12417.00),
        "red": (4409.82, 16214.67)
    }
}

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
        self.partner_email = ""  # Email of the other team leader to sync with
        self.partner_email_index = 0  # Index for combo box selection
        self.first_match = True  # Track if this is the first match (for losing team immediate requeue)
        self.aggressive_mode = False  # Toggle: When enabled, winning team moves to enemy spawn

config = CodexConfig()

bot = Botting(
    BOT_NAME,
    upkeep_auto_inventory_management_active=False,
    upkeep_auto_combat_active=False,
    upkeep_auto_loot_active=False,
)

# Custom synchronization command for queue timing
SYNC_QUEUE_COMMAND = SharedCommandType.CustomBehaviors  # Use existing custom command type

# Delay (in milliseconds) to wait after map change
MAP_CHANGE_DELAY_MS = 2000


def get_my_email() -> str:
    """Get the current account email."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    return GLOBAL_CACHE.Player.GetAccountEmail()


def get_available_accounts() -> list:
    """Get list of all account emails from shared memory."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    my_email = get_my_email()
    
    try:
        all_accounts = GLOBAL_CACHE.ShMem.GetAllAccountData()
        if not all_accounts:
            return []
        
        account_emails = []
        for account in all_accounts:
            if account.AccountEmail != my_email:
                account_emails.append(account.AccountEmail)
        
        return account_emails
    except Exception as e:
        Py4GW.Console.Log(BOT_NAME, f"Failed to get accounts from shared memory: {e}", 
                         Py4GW.Console.MessageType.Warning)
        return []


def send_sync_signal(signal_type: str):
    """Send synchronization signal to other accounts."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    my_email = get_my_email()
    
    # Only send if partner email is configured and not empty/whitespace
    if not config.partner_email or not config.partner_email.strip():
        return
    
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
    
    # Send only to the configured partner account
    try:
        GLOBAL_CACHE.ShMem.SendMessage(my_email, config.partner_email.strip(), SYNC_QUEUE_COMMAND, params)
    except Exception as e:
        Py4GW.Console.Log(BOT_NAME, f"Failed to send sync signal: {e}", Py4GW.Console.MessageType.Warning)


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


def disable_auto_combat():
    """Disable auto combat for the bot."""
    bot.config.upkeep.auto_combat.set_now("active", False)


def travel_to_codex_arena() -> Generator:
    """Travel to Codex Arena outpost."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    from Py4GWCoreLib import Map
    from Py4GWCoreLib.Routines import Routines
    
    current_map = GLOBAL_CACHE.Map.GetMapID()
    if current_map != CODEX_ARENA_OUTPOST_ID:
        yield from bot.Map._coro_travel(target_map_id=CODEX_ARENA_OUTPOST_ID)
        yield from Routines.Yield.wait(2000)


def enter_queue() -> Generator:
    """Enter the arena queue."""
    from Py4GWCoreLib import Map
    from Py4GWCoreLib.Routines import Routines
    
    # Enter challenge/queue
    Map.EnterChallenge()
    # Wait for queue to process (can take up to 35 seconds to find a match)
    yield from Routines.Yield.wait(35000)


def get_player_team(map_id: int) -> str:
    """
    Determine which team the player is on based on proximity to spawn points.
    Returns 'blue' or 'red' or 'unknown'.
    """
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    from Py4GWCoreLib.Py4GWcorelib import Utils
    
    if map_id not in PRIEST_COORDINATES:
        return "unknown"
    
    player_pos = GLOBAL_CACHE.Player.GetXY()
    blue_spawn = PRIEST_COORDINATES[map_id]["blue"]
    red_spawn = PRIEST_COORDINATES[map_id]["red"]
    
    dist_to_blue = Utils.Distance(player_pos, blue_spawn)
    dist_to_red = Utils.Distance(player_pos, red_spawn)
    
    return "blue" if dist_to_blue < dist_to_red else "red"


def move_to_enemy_priest(bot: Botting, map_id: int) -> Generator:
    """
    Move to the enemy spawn location.
    HeroAI will handle the actual combat automatically.
    Called for winning team in priest maps (Seabed Arena, Deldrimor Arena) 
    or when Aggressive Mode is enabled.
    Only works if spawn coordinates are defined for the current map.
    """
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    from Py4GWCoreLib.Routines import Routines
    from Py4GWCoreLib.routines_src.Movement import Movement
    
    if map_id not in PRIEST_COORDINATES:
        Py4GW.Console.Log(BOT_NAME, 
                         f"Spawn coordinates not defined for map {map_id}. Staying in current position.", 
                         Py4GW.Console.MessageType.Warning)
        return
    
    # Determine our team
    our_team = get_player_team(map_id)
    if our_team == "unknown":
        Py4GW.Console.Log(BOT_NAME, "Could not determine team, skipping spawn movement", 
                         Py4GW.Console.MessageType.Warning)
        yield  # Generator yield required before early return to prevent NoneType iteration errors
        return
    
    # Get enemy spawn location (opposite team)
    enemy_team = "red" if our_team == "blue" else "blue"
    spawn_x, spawn_y = PRIEST_COORDINATES[map_id][enemy_team]
    
    Py4GW.Console.Log(BOT_NAME, 
                     f"Our team: {our_team.upper()} - Moving to {enemy_team.upper()} spawn at ({spawn_x}, {spawn_y})...", 
                     Py4GW.Console.MessageType.Info)
    
    # Move player to enemy spawn location (party members will follow automatically)
    movement_tracker = Movement.FollowXY(tolerance=PRIEST_LOCATION_TOLERANCE)
    movement_tracker.move_to_waypoint(spawn_x, spawn_y)
    
    # Wait until we arrive or timeout
    timeout = PRIEST_MOVEMENT_TIMEOUT
    start_time = time.time()
    while time.time() - start_time < timeout and bot.config.fsm_running:
        movement_tracker.update()
        if movement_tracker.has_arrived():
            break
        yield from Routines.Yield.wait(100)
    
    if movement_tracker.has_arrived():
        Py4GW.Console.Log(BOT_NAME, 
                         f"Arrived at {enemy_team.upper()} spawn location! HeroAI will handle combat.", 
                         Py4GW.Console.MessageType.Success)
    else:
        Py4GW.Console.Log(BOT_NAME, 
                         f"Failed to reach {enemy_team.upper()} spawn location within {timeout} seconds", 
                         Py4GW.Console.MessageType.Warning)


def wait_for_match_start(bot: Botting, outpost_map_id: int) -> Generator:
    """Wait until match starts (map changes from outpost)."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    from Py4GWCoreLib.Routines import Routines
    
    timeout = 300  # 5 minute timeout (in seconds)
    start_time = time.time()
    
    while time.time() - start_time < timeout and bot.config.fsm_running:
        current_map_id = GLOBAL_CACHE.Map.GetMapID()
        
        # Check if map has changed from outpost
        if current_map_id != outpost_map_id:
            if not config.in_match:
                config.in_match = True
                map_name = GLOBAL_CACHE.Map.GetMapName(current_map_id)
                Py4GW.Console.Log(BOT_NAME, 
                                f"Entered the Arena! Map ID: {current_map_id}, Map Name: {map_name}", 
                                Py4GW.Console.MessageType.Success)
            
            # Match started as soon as map changed
            send_sync_signal("MATCH_START")
            Py4GW.Console.Log(BOT_NAME, "Match started!", Py4GW.Console.MessageType.Success)
            return
        
        yield from Routines.Yield.wait(1000)
    
    # Timeout - match didn't start
    Py4GW.Console.Log(BOT_NAME, "Timeout waiting for match start.", Py4GW.Console.MessageType.Warning)
    config.in_match = False


def winning_team_logic(bot: Botting) -> Generator:
    """Logic for the winning team - win matches continuously, staying in map and auto-queued."""
    from Py4GWCoreLib.Routines import Routines
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    
    # Winning team stays in explorable map after victories and is automatically re-queued
    # Loop through multiple matches without returning to outpost
    while bot.config.fsm_running:
        # Check if we should shut down (earned 5 strongboxes)
        if config.strongboxes_earned >= config.target_strongboxes:
            Py4GW.Console.Log(BOT_NAME, 
                            f"Target reached! Earned {config.strongboxes_earned} strongboxes. Returning to outpost.", 
                            Py4GW.Console.MessageType.Success)
            from Py4GWCoreLib import Party
            # Disable auto combat when returning to outpost
            disable_auto_combat()
            Party.ReturnToOutpost()
            yield from Routines.Yield.wait(5000)
            config.in_match = False
            bot.Stop()
            return
        
        # Get current map ID to determine arena type
        current_map_id = GLOBAL_CACHE.Map.GetMapID()
        
        # Check if Map ID is 829 (Seabed Arena) or 830 (Deldrimor Arena) OR Aggressive Mode is enabled
        is_priest_map = current_map_id == SEABED_ARENA_MAP_ID or current_map_id == DELDRIMOR_ARENA_MAP_ID
        if is_priest_map or config.aggressive_mode:
            # Determine wait time based on conditions
            # If Aggressive Mode is on AND we're at 4/5 wins (next win will be 5/5), wait 80 seconds
            # Otherwise, wait 45 seconds for priest maps and 30 seconds for regular aggressive mode
            if config.aggressive_mode and config.consecutive_wins == 4:
                wait_time_ms = 80000
                wait_time_seconds = 80
            elif is_priest_map:
                wait_time_ms = 45000
                wait_time_seconds = 45
            else:
                wait_time_ms = 30000
                wait_time_seconds = 30
            
            # Log appropriate message
            if is_priest_map:
                arena_name = "Seabed Arena" if current_map_id == SEABED_ARENA_MAP_ID else "Deldrimor Arena"
                Py4GW.Console.Log(BOT_NAME, 
                                f"Entered {arena_name} (Map ID: {current_map_id}), waiting {wait_time_seconds} seconds before rushing enemy spawn...", 
                                Py4GW.Console.MessageType.Info)
            else:
                if config.consecutive_wins == 4:
                    Py4GW.Console.Log(BOT_NAME, 
                                    f"Aggressive Mode enabled (Map ID: {current_map_id}), at 4/5 wins - waiting {wait_time_seconds} seconds before rushing enemy spawn...", 
                                    Py4GW.Console.MessageType.Info)
                else:
                    Py4GW.Console.Log(BOT_NAME, 
                                    f"Aggressive Mode enabled (Map ID: {current_map_id}), waiting {wait_time_seconds} seconds before rushing enemy spawn...", 
                                    Py4GW.Console.MessageType.Info)
            
            yield from Routines.Yield.wait(wait_time_ms)
            
            # Rush the enemy spawn location (determine spawn and move to enemy coordinates)
            Py4GW.Console.Log(BOT_NAME, 
                            f"Moving to enemy spawn location...", 
                            Py4GW.Console.MessageType.Info)
            yield from move_to_enemy_priest(bot, current_map_id)
        else:
            # Not a priest map and Aggressive Mode disabled - just wait in spawn
            Py4GW.Console.Log(BOT_NAME, 
                            f"Entered arena (Map ID: {current_map_id}), waiting in spawn...", 
                            Py4GW.Console.MessageType.Info)
        
        # Wait in the arena until the map changes (up to 10 minutes)
        Py4GW.Console.Log(BOT_NAME, "Waiting for map change...", 
                         Py4GW.Console.MessageType.Info)
        
        timeout = 600  # 10 minute timeout (in seconds)
        start_time = time.time()
        map_changed = False
        
        while time.time() - start_time < timeout and bot.config.fsm_running:
            yield from Routines.Yield.wait(2000)
            
            # Check if map has changed
            new_map_id = GLOBAL_CACHE.Map.GetMapID()
            if new_map_id != current_map_id:
                map_changed = True
                Py4GW.Console.Log(BOT_NAME, "Map changed - match ended!", Py4GW.Console.MessageType.Info)
                break
        
        if map_changed:
            # Wait a moment after map change
            yield from Routines.Yield.wait(MAP_CHANGE_DELAY_MS)
            
            # Count this as a win - increment consecutive wins counter
            config.consecutive_wins += 1
            
            # Check if we've reached 5 consecutive wins
            if config.consecutive_wins >= 5:
                # Increment strongbox counter and reset consecutive wins
                config.strongboxes_earned += 1
                config.consecutive_wins = 0
                Py4GW.Console.Log(BOT_NAME, 
                                f"Strongbox earned! Now have {config.strongboxes_earned}/{config.target_strongboxes} strongboxes. Consecutive wins reset.", 
                                Py4GW.Console.MessageType.Success)
            else:
                # Log progress toward next strongbox
                Py4GW.Console.Log(BOT_NAME, 
                                f"Victory! {config.consecutive_wins}/5 consecutive wins.", 
                                Py4GW.Console.MessageType.Success)
            
            # Log current progress
            Py4GW.Console.Log(BOT_NAME, 
                            f"Progress: {config.strongboxes_earned}/{config.target_strongboxes} strongboxes ({config.consecutive_wins}/5 consecutive wins)", 
                            Py4GW.Console.MessageType.Info)
            
            # Check if we transitioned to another arena map (not back to outpost)
            # In Codex Arena, winning teams only transition between arena maps or back to outpost
            # There are no other possible map transitions in this game mode
            new_map_id = GLOBAL_CACHE.Map.GetMapID()
            
            if new_map_id != CODEX_ARENA_OUTPOST_ID:
                # We're already in the next match (arena-to-arena transition)
                # The game automatically re-queues and moves winning team to next arena
                Py4GW.Console.Log(BOT_NAME, 
                                f"Automatically transitioned to next match (Map ID: {new_map_id})", 
                                Py4GW.Console.MessageType.Info)
                config.in_match = True
                # Loop will continue to check for target strongboxes and execute priest rush logic
            else:
                # We're back in the outpost (shouldn't normally happen for winning team)
                Py4GW.Console.Log(BOT_NAME, "Returned to outpost - waiting for next match...", 
                                Py4GW.Console.MessageType.Info)
                config.in_match = False
                
                # Wait for next match to start
                yield from wait_for_match_start(bot, new_map_id)
                
                if not config.in_match:
                    # Failed to enter next match
                    Py4GW.Console.Log(BOT_NAME, "Failed to enter next match.", 
                                    Py4GW.Console.MessageType.Warning)
                    return
        else:
            # Timeout - something went wrong, force return to outpost
            Py4GW.Console.Log(BOT_NAME, "Match timeout, forcing return to outpost...", 
                            Py4GW.Console.MessageType.Warning)
            from Py4GWCoreLib import Party
            # Disable auto combat when returning to outpost
            disable_auto_combat()
            Party.ReturnToOutpost()
            yield from Routines.Yield.wait(5000)
            config.in_match = False
            return
        
        # Continue loop for next match


def losing_team_logic(bot: Botting) -> Generator:
    """Logic for the losing team - return to outpost after match."""
    from Py4GWCoreLib.Routines import Routines
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    from Py4GWCoreLib import Party
    
    Py4GW.Console.Log(BOT_NAME, "Losing team in arena, waiting for map change...", 
                     Py4GW.Console.MessageType.Info)
    
    # Get current map ID to detect map changes
    current_map_id = GLOBAL_CACHE.Map.GetMapID()
    
    # Wait until map changes (up to 10 minutes)
    timeout = 600  # 10 minute timeout (in seconds)
    start_time = time.time()
    map_changed = False
    
    while time.time() - start_time < timeout and bot.config.fsm_running:
        yield from Routines.Yield.wait(2000)
        
        # Check if map has changed
        new_map_id = GLOBAL_CACHE.Map.GetMapID()
        if new_map_id != current_map_id:
            map_changed = True
            Py4GW.Console.Log(BOT_NAME, "Map changed - returned to outpost after loss.", 
                            Py4GW.Console.MessageType.Info)
            config.in_match = False
            send_sync_signal("MATCH_END")
            return
        
        # Check if we need to manually return (after 60 seconds in match)
        if time.time() - start_time > 60 and config.in_match:
            Py4GW.Console.Log(BOT_NAME, "Attempting to return to outpost...", 
                            Py4GW.Console.MessageType.Info)
            Party.ReturnToOutpost()
            yield from Routines.Yield.wait(5000)
            
            # Check if map changed after return attempt
            new_map_id = GLOBAL_CACHE.Map.GetMapID()
            if new_map_id != current_map_id:
                map_changed = True
                config.in_match = False
                Py4GW.Console.Log(BOT_NAME, "Successfully returned to outpost.", 
                                Py4GW.Console.MessageType.Success)
                send_sync_signal("MATCH_END")
                return
    
    # Timeout handling
    if not map_changed:
        Py4GW.Console.Log(BOT_NAME, "Timeout in losing team logic, forcing return...", 
                        Py4GW.Console.MessageType.Warning)
        config.in_match = False


def run_codex_match(bot: Botting) -> None:
    """Run a single Codex Arena match cycle."""
    def _run_match():
        from Py4GWCoreLib.Routines import Routines
        from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
        
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
        # Losing team skips synchronization after first match for immediate requeue
        skip_sync = not config.is_winning_team and not config.first_match
        
        if not skip_sync:
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
        else:
            Py4GW.Console.Log(BOT_NAME, "Losing team re-entering queue immediately (no sync wait)...", 
                            Py4GW.Console.MessageType.Info)
        
        # Get outpost map ID before entering queue
        outpost_map_id = GLOBAL_CACHE.Map.GetMapID()
        
        # Both teams enter queue simultaneously
        Py4GW.Console.Log(BOT_NAME, "Entering queue NOW!", Py4GW.Console.MessageType.Info)
        send_sync_signal("QUEUE_NOW")
        yield from enter_queue()
        
        # Wait for match to start
        Py4GW.Console.Log(BOT_NAME, "Waiting for match to start...", Py4GW.Console.MessageType.Info)
        yield from wait_for_match_start(bot, outpost_map_id)
        
        if not config.in_match:
            # Failed to enter match, retry
            Py4GW.Console.Log(BOT_NAME, "Failed to enter match, retrying...", Py4GW.Console.MessageType.Warning)
            yield from Routines.Yield.wait(3000)
            return
        
        # Execute team-specific logic
        if config.is_winning_team:
            # Enable auto combat for winning team to be aggressive
            bot.config.upkeep.auto_combat.set_now("active", True)
            Py4GW.Console.Log(BOT_NAME, "Playing as winning team (auto combat enabled)...", Py4GW.Console.MessageType.Info)
            yield from winning_team_logic(bot)
            # Winning team logic handles multiple matches internally and only returns when done
            # No need to log progress or wait here
        else:
            Py4GW.Console.Log(BOT_NAME, "Playing as losing team...", Py4GW.Console.MessageType.Info)
            yield from losing_team_logic(bot)
            
            # Mark that first match is complete (losing team will skip sync on subsequent matches)
            config.first_match = False
            
            # Log current progress for losing team
            Py4GW.Console.Log(BOT_NAME, 
                            f"Progress: {config.strongboxes_earned}/{config.target_strongboxes} strongboxes ({config.consecutive_wins} consecutive wins)", 
                            Py4GW.Console.MessageType.Info)
            # Losing team requeues immediately (no delay)
    
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
    
    # Partner email selection
    PyImGui.text("Partner Account Email:")
    available_accounts = get_available_accounts()
    
    if available_accounts:
        # Add empty option at the beginning
        account_options = ["(None)"] + available_accounts
        
        # Update index if current partner email is in the list
        if config.partner_email and config.partner_email in available_accounts:
            config.partner_email_index = available_accounts.index(config.partner_email) + 1
        elif not config.partner_email:
            config.partner_email_index = 0
        
        # Draw combo box
        new_index = PyImGui.combo("##partner_email_combo", config.partner_email_index, account_options)
        
        if new_index != config.partner_email_index:
            config.partner_email_index = new_index
            if new_index == 0:
                config.partner_email = ""
                Py4GW.Console.Log(BOT_NAME, "Partner email cleared.", 
                                Py4GW.Console.MessageType.Info)
            else:
                config.partner_email = available_accounts[new_index - 1]
                Py4GW.Console.Log(BOT_NAME, f"Partner email set to: {config.partner_email}", 
                                Py4GW.Console.MessageType.Info)
    else:
        PyImGui.text_colored("No other accounts detected in shared memory", (1, 0.5, 0, 1))
    
    PyImGui.separator()
    
    # Team role toggle
    new_value = PyImGui.checkbox("Is Winning Team", config.is_winning_team)
    if new_value != config.is_winning_team:
        config.is_winning_team = new_value
        Py4GW.Console.Log(BOT_NAME, f"Team role changed to: {'Winning' if config.is_winning_team else 'Losing'}", 
                        Py4GW.Console.MessageType.Info)
    
    # Aggressive Mode toggle
    new_aggressive = PyImGui.checkbox("Aggressive Mode", config.aggressive_mode)
    if new_aggressive != config.aggressive_mode:
        config.aggressive_mode = new_aggressive
        Py4GW.Console.Log(BOT_NAME, f"Aggressive Mode {'enabled' if config.aggressive_mode else 'disabled'}", 
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
    PyImGui.text_wrapped("Instructions: Set the Partner Account Email to the email of the other team leader. Set up two teams of 4. Run one instance with 'Is Winning Team' checked, another with it unchecked. Enable 'Aggressive Mode' to make the winning team rush to the enemy spawn on all maps (not just priest maps). Earn 1 Strategist's Zaishen Strongbox per 5 consecutive wins (max 5/day). Bot stops after earning 5 strongboxes.")


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
