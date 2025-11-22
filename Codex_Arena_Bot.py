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

# Arena map IDs
SEABED_ARENA_MAP_ID = 829
DELDRIMOR_ARENA_MAP_ID = 830
CHURRANU_ISLAND_ARENA_MAP_ID = 825
SHIVERPEAK_ARENA_MAP_ID = 836
PETRIFIED_ARENA_MAP_ID = 827
AMNOON_ARENA_MAP_ID = 824
FORT_KOGA_MAP_ID = 826
BRAWLERS_PIT_MAP_ID = 831
DALESSIO_ARENA_MAP_ID = 823
ASCALON_ARENA_MAP_ID = 835
SHING_JEA_ARENA_MAP_ID = 834
SUNSPEAR_ARENA_MAP_ID = 833
THE_CRAG_MAP_ID = 832
HEROES_CRYPT_MAP_ID = 828

# Movement tolerance for spawn location (200 units = close enough to engage)
SPAWN_LOCATION_TOLERANCE = 200

# Movement timeout when traveling to enemy spawn location (90 seconds to account for obstacles)
SPAWN_MOVEMENT_TIMEOUT = 90

# Spawn coordinates for arenas
# Format: {map_id: {"blue": (x, y), "red": (x, y)}}
ARENA_SPAWN_COORDINATES = {
    SEABED_ARENA_MAP_ID: {
        "blue": (9737, 4344),
        "red": (4368, 6953)
    },
    DELDRIMOR_ARENA_MAP_ID: {
        "blue": (-9259.12, 2708.83),
        "red": (-8994.74, 7384.57)
    },
    CHURRANU_ISLAND_ARENA_MAP_ID: {
        "blue": (4206.08, -119.03),
        "red": (-886.18, -478.33)
    },
    SHIVERPEAK_ARENA_MAP_ID: {
        "blue": (9344.00, 12417.00),
        "red": (4409.82, 16214.67)
    },
    PETRIFIED_ARENA_MAP_ID: {
        "blue": (1831.88, 1348.83),
        "red": (7198.82, -4076.33)
    },
    AMNOON_ARENA_MAP_ID: {
        "blue": (3282.00, 10095.00),
        "red": (-1923.30, 5129.79)
    },
    FORT_KOGA_MAP_ID: {
        "blue": (6321.00, 181.00),
        "red": (195.82, -3402.33)
    },
    BRAWLERS_PIT_MAP_ID: {
        "blue": (967.00, 5075.00),
        "red": (4981.82, 5033.67)
    },
    DALESSIO_ARENA_MAP_ID: {
        "blue": (4945.88, -2424.17),
        "red": (4627.75, 3853.27)
    },
    ASCALON_ARENA_MAP_ID: {
        "blue": (8181.50, -1940.41),
        "red": (4800.82, -6545.33)
    },
    SHING_JEA_ARENA_MAP_ID: {
        "blue": (-2375.00, -1583.00),
        "red": (2308.82, 2879.67)
    },
    SUNSPEAR_ARENA_MAP_ID: {
        "blue": (436.00, 2517.00),
        "red": (3731.82, -2301.33)
    },
    THE_CRAG_MAP_ID: {
        "blue": (6528.88, 4470.83),
        "red": (-2394.18, -2403.33)
    },
    HEROES_CRYPT_MAP_ID: {
        "blue": (-110.00, -4322.00),
        "red": (3299.88, -5084.17)
    }
}

# Priest arena map IDs (subset of arenas with priests - for backwards compatibility)
PRIEST_ARENA_MAP_IDS = {SEABED_ARENA_MAP_ID, DELDRIMOR_ARENA_MAP_ID}

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
        self.aggressive_mode = False  # Toggle: True = rush enemy spawn, False = only for priest maps

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
    # Wait for queue to process (can take up to 35 seconds to find a match)
    yield from Routines.Yield.wait(35000)


def get_player_team(map_id: int) -> str:
    """
    Determine which team the player is on based on proximity to spawn points.
    Returns 'blue' or 'red' or 'unknown'.
    """
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    from Py4GWCoreLib.Py4GWcorelib import Utils
    
    if map_id not in ARENA_SPAWN_COORDINATES:
        return "unknown"
    
    player_pos = GLOBAL_CACHE.Player.GetXY()
    blue_spawn = ARENA_SPAWN_COORDINATES[map_id]["blue"]
    red_spawn = ARENA_SPAWN_COORDINATES[map_id]["red"]
    
    dist_to_blue = Utils.Distance(player_pos, blue_spawn)
    dist_to_red = Utils.Distance(player_pos, red_spawn)
    
    return "blue" if dist_to_blue < dist_to_red else "red"


def move_to_enemy_spawn(bot: Botting, map_id: int) -> Generator:
    """
    Move to the enemy spawn location.
    HeroAI will handle the actual combat automatically.
    Called for winning team when aggressive mode is enabled or for priest maps.
    """
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    from Py4GWCoreLib.Routines import Routines
    from Py4GWCoreLib.routines_src.Movement import Movement
    
    if map_id not in ARENA_SPAWN_COORDINATES:
        Py4GW.Console.Log(BOT_NAME, 
                         f"Map ID {map_id} not recognized. Staying in spawn.", 
                         Py4GW.Console.MessageType.Warning)
        return
    
    # Determine our team
    our_team = get_player_team(map_id)
    if our_team == "unknown":
        Py4GW.Console.Log(BOT_NAME, "Could not determine team, skipping spawn movement", 
                         Py4GW.Console.MessageType.Warning)
        return
    
    # Get enemy spawn location (opposite team)
    enemy_team = "red" if our_team == "blue" else "blue"
    spawn_x, spawn_y = ARENA_SPAWN_COORDINATES[map_id][enemy_team]
    
    Py4GW.Console.Log(BOT_NAME, 
                     f"Our team: {our_team.upper()} - Moving to {enemy_team.upper()} spawn at ({spawn_x}, {spawn_y})...", 
                     Py4GW.Console.MessageType.Info)
    
    # Move player to enemy spawn location (party members will follow automatically)
    movement_tracker = Movement.FollowXY(tolerance=SPAWN_LOCATION_TOLERANCE)
    movement_tracker.move_to_waypoint(spawn_x, spawn_y)
    
    # Wait until we arrive or timeout
    timeout = SPAWN_MOVEMENT_TIMEOUT
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
        # HeroAI will automatically engage enemies in range
        # Wait until combat is complete
        Py4GW.Console.Log(BOT_NAME, "Waiting until out of combat...", Py4GW.Console.MessageType.Info)
        yield from bot.Wait.UntilOutOfCombat()
        Py4GW.Console.Log(BOT_NAME, "Out of combat, proceeding with match.", Py4GW.Console.MessageType.Success)
    else:
        Py4GW.Console.Log(BOT_NAME, 
                         f"Failed to reach {enemy_team.upper()} spawn location within {timeout} seconds", 
                         Py4GW.Console.MessageType.Warning)


def wait_for_match_start(bot: Botting, outpost_map_id: int) -> Generator:
    """Wait until match starts (map changes from outpost) or at least 1 minute."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    from Py4GWCoreLib.Routines import Routines
    
    min_wait_time = 60  # Minimum 1 minute wait
    timeout = 300  # 5 minute timeout (in seconds)
    start_time = time.time()
    map_changed = False
    
    while time.time() - start_time < timeout and bot.config.fsm_running:
        current_map_id = GLOBAL_CACHE.Map.GetMapID()
        elapsed = time.time() - start_time
        
        # Check if map has changed from outpost
        if current_map_id != outpost_map_id:
            map_changed = True
            if not config.in_match:
                config.in_match = True
                map_name = GLOBAL_CACHE.Map.GetMapName(current_map_id)
                Py4GW.Console.Log(BOT_NAME, 
                                f"Entered the Arena! Map ID: {current_map_id}, Map Name: {map_name}", 
                                Py4GW.Console.MessageType.Success)
        
        # Exit when map changed AND at least 1 minute has passed
        if map_changed and elapsed >= min_wait_time:
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
        
        # Get current map ID to detect map changes
        current_map_id = GLOBAL_CACHE.Map.GetMapID()
        
        # Wait 30 seconds after entering any map
        Py4GW.Console.Log(BOT_NAME, 
                        f"Entered map (Map ID: {current_map_id}), waiting 30 seconds...", 
                        Py4GW.Console.MessageType.Info)
        yield from Routines.Yield.wait(30000)
        
        # Check if we should move to enemy spawn
        is_priest_map = current_map_id in PRIEST_ARENA_MAP_IDS
        should_rush_spawn = (config.aggressive_mode and current_map_id in ARENA_SPAWN_COORDINATES) or is_priest_map
        
        if should_rush_spawn:
            if is_priest_map:
                arena_name = "Seabed Arena" if current_map_id == SEABED_ARENA_MAP_ID else "Deldrimor Arena"
                Py4GW.Console.Log(BOT_NAME, 
                                f"Detected {arena_name}, moving to enemy priest...", 
                                Py4GW.Console.MessageType.Info)
            else:
                map_name = GLOBAL_CACHE.Map.GetMapName(current_map_id)
                Py4GW.Console.Log(BOT_NAME, 
                                f"Aggressive mode enabled - moving to enemy spawn in {map_name}...", 
                                Py4GW.Console.MessageType.Info)
            yield from move_to_enemy_spawn(bot, current_map_id)
        
        # Wait in the arena until the map changes (up to 10 minutes)
        Py4GW.Console.Log(BOT_NAME, "Winning team in arena, waiting for map change...", 
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
            
            # Winning team stays in map and is automatically re-queued by the game
            Py4GW.Console.Log(BOT_NAME, "Waiting for automatic re-queue and next match...", 
                            Py4GW.Console.MessageType.Info)
            config.in_match = False
            
            # Log current progress
            Py4GW.Console.Log(BOT_NAME, 
                            f"Progress: {config.strongboxes_earned}/{config.target_strongboxes} strongboxes ({config.consecutive_wins}/5 consecutive wins)", 
                            Py4GW.Console.MessageType.Info)
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
        
        # Get the current outpost map ID for next match detection
        outpost_map_id = GLOBAL_CACHE.Map.GetMapID()
        
        # Wait for next match to start (automatically queued by game)
        Py4GW.Console.Log(BOT_NAME, "Waiting for next match to start...", Py4GW.Console.MessageType.Info)
        yield from wait_for_match_start(bot, outpost_map_id)
        
        if not config.in_match:
            # Failed to enter next match, return to outpost
            Py4GW.Console.Log(BOT_NAME, "Failed to enter next match, returning to outpost...", 
                            Py4GW.Console.MessageType.Warning)
            from Py4GWCoreLib import Party
            # Disable auto combat when returning to outpost
            disable_auto_combat()
            Party.ReturnToOutpost()
            yield from Routines.Yield.wait(5000)
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
    
    # Aggressive mode toggle
    new_aggressive = PyImGui.checkbox("Aggressive Mode (Rush Enemy Spawn)", config.aggressive_mode)
    if new_aggressive != config.aggressive_mode:
        config.aggressive_mode = new_aggressive
        Py4GW.Console.Log(BOT_NAME, f"Aggressive mode: {'Enabled' if config.aggressive_mode else 'Disabled'}", 
                        Py4GW.Console.MessageType.Info)
    
    if config.aggressive_mode:
        PyImGui.text_colored("Winning team will rush to enemy spawn on all maps", (1, 1, 0, 1))
    else:
        PyImGui.text_colored("Winning team will only rush on priest maps", (0.7, 0.7, 0.7, 1))
    
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
    PyImGui.text_wrapped("Instructions: Set the Partner Account Email to the email of the other team leader. Set up two teams of 4. Run one instance with 'Is Winning Team' checked, another with it unchecked. Enable 'Aggressive Mode' to have the winning team rush enemy spawn on all maps. Earn 1 Strategist's Zaishen Strongbox per 5 consecutive wins (max 5/day). Bot stops after earning 5 strongboxes.")


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
