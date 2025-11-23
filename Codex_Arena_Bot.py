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

# Wait time constants (in seconds)
WAIT_TIME_AGGRESSIVE_CRITICAL = 80  # When at 4/5 wins (about to earn strongbox) - applies to all modes
WAIT_TIME_PRIEST_MAP = 45  # For Priest Maps (Seabed Arena, Deldrimor Arena)
WAIT_TIME_AGGRESSIVE_NORMAL = 30  # For regular Aggressive Mode

# Strongbox win tracking constants
WINS_BEFORE_STRONGBOX = 4  # At 4 wins, the next win (5th) earns a strongbox
TOTAL_WINS_FOR_STRONGBOX = 5  # Total consecutive wins needed to earn a strongbox

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
        self.first_queue_completed = False  # Track if initial queue synchronization is complete
        
        # Party configuration
        self.party_members = []  # List of account emails for party members
        self.party_member_indices = []  # List of indices for combo box selections
        
        # Map synchronization
        self.desync_detected = False  # Flag for map desync detection
        self.last_partner_map_id = 0  # Last known partner map ID
        
        # Payback and Resign modes
        self.payback_mode = False  # Toggle: Losing team goes aggressive on desync
        self.resign_mode = False  # Toggle: Winning team resigns on desync
        
        # Resigning routine mode
        self.both_teams_resign_mode = False  # Toggle: Both teams resign instead of playing
        
        # Leader/Support mode
        self.is_leader = True  # Toggle: True = leader (main bot), False = support script

config = CodexConfig()

bot = Botting(
    BOT_NAME,
    upkeep_auto_inventory_management_active=False,
    upkeep_auto_combat_active=False,
    upkeep_auto_loot_active=False,
)

# Custom synchronization command for queue timing
SYNC_QUEUE_COMMAND = SharedCommandType.CustomBehaviors  # Use existing custom command type

# Signal type values for queue synchronization
SIGNAL_READY_TO_QUEUE = 1.0
SIGNAL_QUEUE_NOW = 2.0
SIGNAL_MATCH_START = 3.0
SIGNAL_MATCH_END = 4.0
SIGNAL_MAP_VERIFY = 11.0


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


def send_sync_signal(signal_type: str):
    """Send synchronization signal to other accounts.
    Only sends signals during initial bot startup and first queue entry."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    my_email = get_my_email()
    
    # Only send if partner email is configured and not empty/whitespace
    if not config.partner_email or not config.partner_email.strip():
        return
    
    # Only send sync messages if first queue has not been completed
    # This prevents message stacking after the initial synchronization
    if config.first_queue_completed and signal_type not in ["MAP_VERIFY"]:
        return
    
    # Signal types: "READY_TO_QUEUE", "QUEUE_NOW", "MATCH_START", "MATCH_END", "MAP_VERIFY"
    signal_value = 0.0
    if signal_type == "READY_TO_QUEUE":
        signal_value = SIGNAL_READY_TO_QUEUE
    elif signal_type == "QUEUE_NOW":
        signal_value = SIGNAL_QUEUE_NOW
    elif signal_type == "MATCH_START":
        signal_value = SIGNAL_MATCH_START
    elif signal_type == "MATCH_END":
        signal_value = SIGNAL_MATCH_END
    elif signal_type == "MAP_VERIFY":
        signal_value = SIGNAL_MAP_VERIFY
    
    params = (signal_value, 0.0, 0.0, 0.0)
    
    # Send only to the configured partner account
    try:
        GLOBAL_CACHE.ShMem.SendMessage(my_email, config.partner_email.strip(), SYNC_QUEUE_COMMAND, params)
    except Exception as e:
        Py4GW.Console.Log(BOT_NAME, f"Failed to send sync signal: {e}", Py4GW.Console.MessageType.Warning)


def check_sync_signal() -> tuple[str, int]:
    """Check for synchronization signals from other accounts.
    Only processes signals during initial bot startup and first queue entry.
    Returns tuple of (signal_type, map_id)."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    my_email = get_my_email()
    
    # Only check for sync messages if first queue has not been completed
    if config.first_queue_completed:
        # Still check for MAP_VERIFY messages, but consume ALL of them
        # and only return the most recent one to prevent message stacking
        latest_map_id = 0
        found_map_verify = False
        messages_cleared = 0
        max_iterations = 100  # Safety limit to prevent infinite loops
        
        # Process all pending MAP_VERIFY messages
        for _ in range(max_iterations):
            msg_index, msg = GLOBAL_CACHE.ShMem.PreviewNextMessage(my_email, include_running=False)
            
            if not msg:
                break
            
            # Only process SYNC_QUEUE_COMMAND messages
            if msg.Command != SYNC_QUEUE_COMMAND:
                break
            
            # Check bounds before accessing params - need at least 2 params
            if len(msg.Params) >= 2 and msg.Params[0] == SIGNAL_MAP_VERIFY:
                latest_map_id = int(msg.Params[1])
                found_map_verify = True
                messages_cleared += 1
                GLOBAL_CACHE.ShMem.MarkMessageAsFinished(my_email, msg_index)
            else:
                # Not a MAP_VERIFY message - could be old MATCH_START/MATCH_END from before first_queue_completed
                # Mark it as finished to clear it from the queue and continue processing
                GLOBAL_CACHE.ShMem.MarkMessageAsFinished(my_email, msg_index)
                # Continue to next message instead of breaking
        
        if found_map_verify:
            if messages_cleared > 1:
                Py4GW.Console.Log(BOT_NAME, 
                                f"Cleared {messages_cleared} stacked MAP_VERIFY messages, using latest map ID: {latest_map_id}", 
                                Py4GW.Console.MessageType.Info)
            return ("MAP_VERIFY", latest_map_id)
        
        return ("", 0)
    
    # Check for next message
    msg_index, msg = GLOBAL_CACHE.ShMem.PreviewNextMessage(my_email, include_running=False)
    
    if msg and msg.Command == SYNC_QUEUE_COMMAND:
        signal_type = ""
        map_id = 0
        
        # Check bounds before accessing params
        if len(msg.Params) == 0:
            return ("", 0)
        
        if msg.Params[0] == SIGNAL_READY_TO_QUEUE:
            signal_type = "READY_TO_QUEUE"
        elif msg.Params[0] == SIGNAL_QUEUE_NOW:
            signal_type = "QUEUE_NOW"
        elif msg.Params[0] == SIGNAL_MATCH_START:
            signal_type = "MATCH_START"
        elif msg.Params[0] == SIGNAL_MATCH_END:
            signal_type = "MATCH_END"
        elif msg.Params[0] == SIGNAL_MAP_VERIFY:
            signal_type = "MAP_VERIFY"
            if len(msg.Params) > 1:
                map_id = int(msg.Params[1])
        
        # Mark message as finished
        if signal_type:
            GLOBAL_CACHE.ShMem.MarkMessageAsFinished(my_email, msg_index)
            return (signal_type, map_id)
    
    return ("", 0)


def send_message_to_party(command_type: str, param1: float = 0.0):
    """Send a SharedCommandType message to all party members.
    Party members should run the Messaging.py widget to receive these commands."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    from Py4GWCoreLib.enums_src.Multiboxing_enums import SharedCommandType
    my_email = get_my_email()
    
    if not config.party_members:
        return
    
    # Map command types to SharedCommandType enums
    command = None
    params = (param1, 0.0, 0.0, 0.0)
    
    if command_type == "LEAVE":
        command = SharedCommandType.LeaveParty
    elif command_type == "RESIGN":
        command = SharedCommandType.Resign
    elif command_type == "EQUIP_SET_1":
        # Use PressKey to send F1 for equipment set 1
        command = SharedCommandType.PressKey
        params = (0x70, 0.0, 0.0, 0.0)  # F1 key code
    elif command_type == "EQUIP_SET_2":
        # Use PressKey to send F2 for equipment set 2
        command = SharedCommandType.PressKey
        params = (0x71, 0.0, 0.0, 0.0)  # F2 key code
    elif command_type == "ENABLE_HEROAI":
        command = SharedCommandType.EnableHeroAI
        params = (1.0, 0.0, 0.0, 0.0)  # 1.0 = enable
    elif command_type == "DISABLE_HEROAI":
        command = SharedCommandType.DisableHeroAI
        params = (0.0, 0.0, 0.0, 0.0)
    
    if command is None:
        Py4GW.Console.Log(BOT_NAME, f"Unknown command type: {command_type}", 
                         Py4GW.Console.MessageType.Warning)
        return
    
    Py4GW.Console.Log(BOT_NAME, f"Sending {command_type} to {len(config.party_members)} party members", 
                     Py4GW.Console.MessageType.Info)
    
    for member_email in config.party_members:
        if member_email and member_email.strip():
            try:
                result = GLOBAL_CACHE.ShMem.SendMessage(my_email, member_email.strip(), command, params)
                if result == -1:
                    Py4GW.Console.Log(BOT_NAME, f"Failed to send {command_type} to {member_email}", 
                                     Py4GW.Console.MessageType.Warning)
                else:
                    Py4GW.Console.Log(BOT_NAME, f"Sent {command_type} to {member_email} (msg index: {result})", 
                                     Py4GW.Console.MessageType.Info)
            except Exception as e:
                Py4GW.Console.Log(BOT_NAME, f"Exception sending message to {member_email}: {e}", 
                                 Py4GW.Console.MessageType.Warning)


def send_map_verify_to_partner(map_id: int):
    """Send map verification to partner account."""
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    my_email = get_my_email()
    
    if not config.partner_email or not config.partner_email.strip():
        return
    
    params = (SIGNAL_MAP_VERIFY, float(map_id), 0.0, 0.0)
    
    try:
        GLOBAL_CACHE.ShMem.SendMessage(my_email, config.partner_email.strip(), SYNC_QUEUE_COMMAND, params)
    except Exception as e:
        Py4GW.Console.Log(BOT_NAME, f"Failed to send map verify to partner: {e}", 
                         Py4GW.Console.MessageType.Warning)


def invite_party_members() -> Generator:
    """Invite configured party members to the party.
    Uses HeroAI's mutual invite pattern for reliable party formation."""
    yield  # CRITICAL: Must yield FIRST for generator to start executing
    
    from Py4GWCoreLib import Party
    from Py4GWCoreLib.Routines import Routines
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    from Py4GWCoreLib.enums_src.Multiboxing_enums import SharedCommandType
    
    Py4GW.Console.Log(BOT_NAME, "DEBUG: invite_party_members() function executing", 
                     Py4GW.Console.MessageType.Info)
    
    try:
        if not config.party_members:
            Py4GW.Console.Log(BOT_NAME, "No party members configured", Py4GW.Console.MessageType.Warning)
            yield  # Must yield at least once in a generator
            return
        
        # Filter out empty strings
        valid_members = [m for m in config.party_members if m and m.strip()]
        
        if not valid_members:
            Py4GW.Console.Log(BOT_NAME, "No valid party members configured (all empty)", Py4GW.Console.MessageType.Warning)
            yield  # Must yield at least once in a generator
            return
        
        Py4GW.Console.Log(BOT_NAME, f"Inviting party members... ({len(valid_members)} configured)", 
                         Py4GW.Console.MessageType.Info)
        
        try:
            my_email = get_my_email()
            Py4GW.Console.Log(BOT_NAME, f"DEBUG: my_email = {my_email}", 
                             Py4GW.Console.MessageType.Info)
        except Exception as e:
            Py4GW.Console.Log(BOT_NAME, f"ERROR getting email: {e}", 
                             Py4GW.Console.MessageType.Warning)
            yield
            return
        
        try:
            my_data = GLOBAL_CACHE.ShMem.GetAccountDataFromEmail(my_email)
            Py4GW.Console.Log(BOT_NAME, f"DEBUG: my_data = {my_data}", 
                             Py4GW.Console.MessageType.Info)
        except Exception as e:
            Py4GW.Console.Log(BOT_NAME, f"ERROR getting account data: {e}", 
                             Py4GW.Console.MessageType.Warning)
            yield
            return
        
        if not my_data:
            Py4GW.Console.Log(BOT_NAME, "Failed to get own account data from shared memory", 
                             Py4GW.Console.MessageType.Warning)
            yield  # Must yield at least once in a generator
            return
        
        Py4GW.Console.Log(BOT_NAME, f"Leader: Email={my_email}, PlayerID={my_data.PlayerID}, Map={my_data.MapID}, Region={my_data.MapRegion}, District={my_data.MapDistrict}, Party={my_data.PartyID}", 
                         Py4GW.Console.MessageType.Info)
        
        invited_count = 0
        
        for member_email in valid_members:
            # Get character name from shared memory
            account_data = GLOBAL_CACHE.ShMem.GetAccountDataFromEmail(member_email.strip())
            if not account_data:
                Py4GW.Console.Log(BOT_NAME, f"Could not get account data for {member_email}", 
                                 Py4GW.Console.MessageType.Warning)
                continue
            
            if not account_data.CharacterName:
                Py4GW.Console.Log(BOT_NAME, f"No character name for {member_email}", 
                                 Py4GW.Console.MessageType.Warning)
                continue
            
            char_name = account_data.CharacterName
            
            Py4GW.Console.Log(BOT_NAME, f"Checking {char_name} (Email={member_email}, PlayerID={account_data.PlayerID}, Map={account_data.MapID}, Region={account_data.MapRegion}, District={account_data.MapDistrict}, Party={account_data.PartyID})", 
                             Py4GW.Console.MessageType.Info)
            
            # Check if member is in same map and not in same party
            if not (my_data.MapID == account_data.MapID and
                    my_data.MapRegion == account_data.MapRegion and
                    my_data.MapDistrict == account_data.MapDistrict):
                Py4GW.Console.Log(BOT_NAME, 
                                 f"Skipping {char_name} - different map/region/district (they are in {account_data.MapID}/{account_data.MapRegion}/{account_data.MapDistrict})", 
                                 Py4GW.Console.MessageType.Info)
                continue
            
            if my_data.PartyID == account_data.PartyID:
                Py4GW.Console.Log(BOT_NAME, f"Skipping {char_name} - already in same party ({my_data.PartyID})", 
                                 Py4GW.Console.MessageType.Info)
                continue
            
            Py4GW.Console.Log(BOT_NAME, f"Inviting {char_name}...", Py4GW.Console.MessageType.Info)
            
            # Send invite command to game (HeroAI pattern from windows.py:319-320)
            Party.Players.InvitePlayer(char_name)
            Py4GW.Console.Log(BOT_NAME, f"Called Party.Players.InvitePlayer({char_name})", 
                             Py4GW.Console.MessageType.Info)
            
            # Send shared memory message with sender's PlayerID for mutual invite pattern
            # Messaging widget will send invite back, creating mutual invite that auto-accepts
            Py4GW.Console.Log(BOT_NAME, f"Sending SharedMessage: from={my_email}, to={member_email.strip()}, command=InviteToParty, params=({my_data.PlayerID}, 0, 0, 0)", 
                             Py4GW.Console.MessageType.Info)
            result = GLOBAL_CACHE.ShMem.SendMessage(
                my_email, 
                member_email.strip(), 
                SharedCommandType.InviteToParty, 
                (my_data.PlayerID, 0, 0, 0)
            )
            
            if result == -1:
                Py4GW.Console.Log(BOT_NAME, f"Failed to send invite message to {char_name}", 
                                 Py4GW.Console.MessageType.Warning)
            else:
                Py4GW.Console.Log(BOT_NAME, f"Sent invite message to {char_name} (msg index: {result})", 
                                 Py4GW.Console.MessageType.Success)
                invited_count += 1
            
            yield from Routines.Yield.wait(250)  # Wait between invites (HeroAI uses 250ms)
        
        Py4GW.Console.Log(BOT_NAME, f"Finished inviting {invited_count} party members", Py4GW.Console.MessageType.Info)
        yield  # Final yield to ensure generator completes properly
    
    except Exception as e:
        import traceback
        Py4GW.Console.Log(BOT_NAME, f"EXCEPTION in invite_party_members: {e}", 
                         Py4GW.Console.MessageType.Warning)
        Py4GW.Console.Log(BOT_NAME, f"Traceback: {traceback.format_exc()}", 
                         Py4GW.Console.MessageType.Warning)
        yield  # Must yield at least once in a generator


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
            
            # Send map ID to partner for verification
            send_map_verify_to_partner(current_map_id)
            
            # Wait for partner's map ID and verify
            verify_timeout = 10  # 10 seconds to verify
            verify_start = time.time()
            partner_map_verified = False
            
            while time.time() - verify_start < verify_timeout and bot.config.fsm_running:
                signal, partner_map_id = check_sync_signal()
                if signal == "MAP_VERIFY":
                    config.last_partner_map_id = partner_map_id
                    if partner_map_id == current_map_id:
                        Py4GW.Console.Log(BOT_NAME, "Map IDs match! Teams are synchronized.", 
                                        Py4GW.Console.MessageType.Success)
                        config.desync_detected = False
                        partner_map_verified = True
                    else:
                        Py4GW.Console.Log(BOT_NAME, 
                                        f"DESYNC DETECTED! Our Map: {current_map_id}, Partner Map: {partner_map_id}", 
                                        Py4GW.Console.MessageType.Warning)
                        config.desync_detected = True
                        partner_map_verified = True
                    break
                yield from Routines.Yield.wait(500)
            
            if not partner_map_verified:
                Py4GW.Console.Log(BOT_NAME, "Map verification timeout - assuming no desync", 
                                Py4GW.Console.MessageType.Warning)
                config.desync_detected = False
            
            # Mark first queue as completed after the first match starts
            # This prevents further sync messages from being sent
            if not config.first_queue_completed:
                config.first_queue_completed = True
                Py4GW.Console.Log(BOT_NAME, "Initial synchronization completed - sync messages disabled for subsequent matches.", 
                                Py4GW.Console.MessageType.Info)
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
        
        # Handle desync modes if desync was detected
        if config.desync_detected:
            if config.is_winning_team and config.resign_mode:
                # Resign Mode: Winning team equips Set 2 and returns to outpost
                Py4GW.Console.Log(BOT_NAME, 
                                "DESYNC - Resign Mode active! Equipping Set 2 and returning to outpost...", 
                                Py4GW.Console.MessageType.Warning)
                yield from equip_set(2)
                send_message_to_party("EQUIP_SET_2")
                yield from Routines.Yield.wait(5000)
                from Py4GWCoreLib import Party
                disable_auto_combat()
                Party.ReturnToOutpost()
                yield from Routines.Yield.wait(5000)
                config.in_match = False
                config.desync_detected = False
                # Continue to next iteration - will requeue
                continue
        
        # Check if Map ID is 829 (Seabed Arena) or 830 (Deldrimor Arena) OR Aggressive Mode is enabled
        is_priest_map = current_map_id == SEABED_ARENA_MAP_ID or current_map_id == DELDRIMOR_ARENA_MAP_ID
        if is_priest_map or config.aggressive_mode:
            # Check if we're at the critical win count (about to earn a strongbox)
            # This applies regardless of Aggressive Mode or Priest Map status
            is_critical_win = config.consecutive_wins == WINS_BEFORE_STRONGBOX
            
            # Determine wait time based on conditions
            # Priority: If at 4/5 wins (regardless of mode), wait 80 seconds
            # Otherwise: 45 seconds for priest maps, 30 seconds for regular aggressive mode
            if is_critical_win:
                wait_time_seconds = WAIT_TIME_AGGRESSIVE_CRITICAL
            elif is_priest_map:
                wait_time_seconds = WAIT_TIME_PRIEST_MAP
            else:
                wait_time_seconds = WAIT_TIME_AGGRESSIVE_NORMAL
            
            wait_time_ms = wait_time_seconds * 1000
            
            # Log appropriate message
            if is_critical_win:
                # At 4/5 wins - special message (applies to all modes)
                if is_priest_map:
                    arena_name = "Seabed Arena" if current_map_id == SEABED_ARENA_MAP_ID else "Deldrimor Arena"
                    Py4GW.Console.Log(BOT_NAME, 
                                    f"Entered {arena_name} (Map ID: {current_map_id}), at {WINS_BEFORE_STRONGBOX}/{TOTAL_WINS_FOR_STRONGBOX} wins - waiting {wait_time_seconds} seconds before rushing enemy spawn...", 
                                    Py4GW.Console.MessageType.Info)
                else:
                    Py4GW.Console.Log(BOT_NAME, 
                                    f"Aggressive Mode enabled (Map ID: {current_map_id}), at {WINS_BEFORE_STRONGBOX}/{TOTAL_WINS_FOR_STRONGBOX} wins - waiting {wait_time_seconds} seconds before rushing enemy spawn...", 
                                    Py4GW.Console.MessageType.Info)
            elif is_priest_map:
                # Priest map without special win condition
                arena_name = "Seabed Arena" if current_map_id == SEABED_ARENA_MAP_ID else "Deldrimor Arena"
                Py4GW.Console.Log(BOT_NAME, 
                                f"Entered {arena_name} (Map ID: {current_map_id}), waiting {wait_time_seconds} seconds before rushing enemy spawn...", 
                                Py4GW.Console.MessageType.Info)
            else:
                # Regular aggressive mode
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
            
            # Check if we've reached the required consecutive wins for a strongbox
            if config.consecutive_wins >= TOTAL_WINS_FOR_STRONGBOX:
                # Increment strongbox counter and reset consecutive wins
                config.strongboxes_earned += 1
                config.consecutive_wins = 0
                Py4GW.Console.Log(BOT_NAME, 
                                f"Strongbox earned! Now have {config.strongboxes_earned}/{config.target_strongboxes} strongboxes. Consecutive wins reset.", 
                                Py4GW.Console.MessageType.Success)
            else:
                # Log progress toward next strongbox
                Py4GW.Console.Log(BOT_NAME, 
                                f"Victory! {config.consecutive_wins}/{TOTAL_WINS_FOR_STRONGBOX} consecutive wins.", 
                                Py4GW.Console.MessageType.Success)
            
            # Log current progress
            Py4GW.Console.Log(BOT_NAME, 
                            f"Progress: {config.strongboxes_earned}/{config.target_strongboxes} strongboxes ({config.consecutive_wins}/{TOTAL_WINS_FOR_STRONGBOX} consecutive wins)", 
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
    
    # Get current map ID to detect map changes
    current_map_id = GLOBAL_CACHE.Map.GetMapID()
    
    # Handle desync modes if desync was detected
    if config.desync_detected and config.payback_mode:
        # Payback Mode: Losing team equips Set 1 and goes aggressive
        Py4GW.Console.Log(BOT_NAME, 
                        "DESYNC - Payback Mode active! Equipping Set 1 and going aggressive...", 
                        Py4GW.Console.MessageType.Warning)
        yield from equip_set(1)
        send_message_to_party("EQUIP_SET_1")
        send_message_to_party("ENABLE_HEROAI")
        bot.config.upkeep.auto_combat.set_now("active", True)
        # Rush enemy spawn
        yield from Routines.Yield.wait(30000)  # Wait 30 seconds
        yield from move_to_enemy_priest(bot, current_map_id)
        # Then wait for match to end normally
    else:
        Py4GW.Console.Log(BOT_NAME, "Losing team in arena, waiting for map change...", 
                         Py4GW.Console.MessageType.Info)
    
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
            config.desync_detected = False
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
                config.desync_detected = False
                Py4GW.Console.Log(BOT_NAME, "Successfully returned to outpost.", 
                                Py4GW.Console.MessageType.Success)
                send_sync_signal("MATCH_END")
                return
    
    # Timeout handling
    if not map_changed:
        Py4GW.Console.Log(BOT_NAME, "Timeout in losing team logic, forcing return...", 
                        Py4GW.Console.MessageType.Warning)
        config.in_match = False
        config.desync_detected = False


def resigning_routine_logic(bot: Botting) -> Generator:
    """
    Resigning routine for both teams.
    
    Process:
    1. Check if map is The Crag - if yes, act normally and wait until next map
    2. Otherwise:
       - Disable Aggressive Mode
       - Losing team switches to Equipment Set 1
       - Bot waits for 5 minutes 45 seconds
       - All players execute resign command
       - Both teams wait until back at Codex Arena outpost
    """
    from Py4GWCoreLib.Routines import Routines
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    from Py4GWCoreLib import Party
    
    # Get current map ID
    current_map_id = GLOBAL_CACHE.Map.GetMapID()
    
    # Check if map is The Crag
    if current_map_id == THE_CRAG_MAP_ID:
        Py4GW.Console.Log(BOT_NAME, 
                        "Map is The Crag - acting normally, waiting for next map...", 
                        Py4GW.Console.MessageType.Info)
        
        # Wait for map change (up to 10 minutes)
        timeout = 600  # 10 minute timeout (in seconds)
        start_time = time.time()
        
        while time.time() - start_time < timeout and bot.config.fsm_running:
            yield from Routines.Yield.wait(2000)
            
            # Check if map has changed
            new_map_id = GLOBAL_CACHE.Map.GetMapID()
            if new_map_id != current_map_id:
                Py4GW.Console.Log(BOT_NAME, "Map changed from The Crag!", 
                                Py4GW.Console.MessageType.Info)
                config.in_match = False
                return
        
        # Timeout - force return
        Py4GW.Console.Log(BOT_NAME, "Timeout waiting for map change from The Crag, forcing return...", 
                        Py4GW.Console.MessageType.Warning)
        disable_auto_combat()
        Party.ReturnToOutpost()
        yield from Routines.Yield.wait(5000)
        config.in_match = False
        return
    
    # Not The Crag - proceed with resign routine
    Py4GW.Console.Log(BOT_NAME, 
                    "Both teams resigning - executing resignation routine...", 
                    Py4GW.Console.MessageType.Info)
    
    # Note: Aggressive Mode is implicitly disabled because resigning_routine_logic is called
    # instead of winning_team_logic which would normally handle aggressive movement.
    # The config.aggressive_mode setting is not changed so it can be used in future matches.
    if config.aggressive_mode:
        Py4GW.Console.Log(BOT_NAME, "Skipping Aggressive Mode behavior for resign routine...", 
                        Py4GW.Console.MessageType.Info)
    
    # Losing team switches to Equipment Set 1
    if not config.is_winning_team:
        Py4GW.Console.Log(BOT_NAME, "Losing team switching to Equipment Set 1...", 
                        Py4GW.Console.MessageType.Info)
        yield from equip_set(1)
        send_message_to_party("EQUIP_SET_1")
        yield from Routines.Yield.wait(1000)
    
    # Wait for 5 minutes 45 seconds (345 seconds)
    wait_time_seconds = 345
    Py4GW.Console.Log(BOT_NAME, 
                    f"Waiting {wait_time_seconds} seconds before resigning...", 
                    Py4GW.Console.MessageType.Info)
    yield from Routines.Yield.wait(wait_time_seconds * 1000)
    
    # All players execute resign command
    Py4GW.Console.Log(BOT_NAME, "Executing resign command for all players...", 
                    Py4GW.Console.MessageType.Info)
    
    # Send resign command to party members
    send_message_to_party("RESIGN")
    
    # Execute resign for self (using HeroAI pattern)
    Party.Resign()
    
    yield from Routines.Yield.wait(2000)
    
    # Wait until back at Codex Arena outpost
    Py4GW.Console.Log(BOT_NAME, "Waiting to return to Codex Arena outpost...", 
                    Py4GW.Console.MessageType.Info)
    
    timeout = 60  # 60 second timeout to return to outpost
    start_time = time.time()
    
    while time.time() - start_time < timeout and bot.config.fsm_running:
        yield from Routines.Yield.wait(2000)
        
        # Check if we're back at outpost
        new_map_id = GLOBAL_CACHE.Map.GetMapID()
        if new_map_id == CODEX_ARENA_OUTPOST_ID:
            Py4GW.Console.Log(BOT_NAME, "Successfully returned to Codex Arena outpost!", 
                            Py4GW.Console.MessageType.Success)
            config.in_match = False
            return
    
    # Timeout - not back at outpost yet, force return
    Py4GW.Console.Log(BOT_NAME, "Timeout waiting for return to outpost, forcing return...", 
                    Py4GW.Console.MessageType.Warning)
    disable_auto_combat()
    Party.ReturnToOutpost()
    yield from Routines.Yield.wait(5000)
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
        
        # On first match, invite party members if leader
        if config.is_leader and config.first_match and config.party_members:
            Py4GW.Console.Log(BOT_NAME, "First match - inviting party members...", 
                            Py4GW.Console.MessageType.Info)
            yield from invite_party_members()
            yield from Routines.Yield.wait(5000)  # Wait for party to form
        
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
                signal, _ = check_sync_signal()
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
        
        # Check if both teams resign mode is enabled
        if config.both_teams_resign_mode:
            Py4GW.Console.Log(BOT_NAME, "Both Teams Resign Mode active - executing resign routine...", 
                            Py4GW.Console.MessageType.Info)
            yield from resigning_routine_logic(bot)
            
            # Mark that first match is complete
            config.first_match = False
            
            # Log current progress
            Py4GW.Console.Log(BOT_NAME, 
                            f"Progress: {config.strongboxes_earned}/{config.target_strongboxes} strongboxes ({config.consecutive_wins} consecutive wins)", 
                            Py4GW.Console.MessageType.Info)
            return
        
        # Execute team-specific logic
        if config.is_winning_team:
            # Enable auto combat for winning team to be aggressive
            bot.config.upkeep.auto_combat.set_now("active", True)
            # Enable HeroAI for party members so they are aggressive
            send_message_to_party("ENABLE_HEROAI")
            Py4GW.Console.Log(BOT_NAME, "Playing as winning team (HeroAI enabled for party)...", Py4GW.Console.MessageType.Info)
            yield from winning_team_logic(bot)
            # Winning team logic handles multiple matches internally and only returns when done
            # No need to log progress or wait here
        else:
            # Disable HeroAI for losing team so they are passive
            send_message_to_party("DISABLE_HEROAI")
            Py4GW.Console.Log(BOT_NAME, "Playing as losing team (HeroAI disabled for party)...", Py4GW.Console.MessageType.Info)
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
    
    # Partner email selection with character names
    PyImGui.text("Partner Account Email:")
    available_accounts_data = get_available_accounts_with_names()
    
    if available_accounts_data:
        # Add empty option at the beginning
        account_display = ["(None)"] + [display for _, display in available_accounts_data]
        account_emails = [email for email, _ in available_accounts_data]
        
        # Update index if current partner email is in the list
        if config.partner_email and config.partner_email in account_emails:
            config.partner_email_index = account_emails.index(config.partner_email) + 1
        elif not config.partner_email:
            config.partner_email_index = 0
        else:
            # Partner email is set but not in list - reset to None
            config.partner_email_index = 0
            config.partner_email = ""
        
        # Draw combo box
        new_index = PyImGui.combo("##partner_email_combo", config.partner_email_index, account_display)
        
        if new_index != config.partner_email_index:
            config.partner_email_index = new_index
            if new_index == 0:
                config.partner_email = ""
                Py4GW.Console.Log(BOT_NAME, "Partner email cleared.", 
                                Py4GW.Console.MessageType.Info)
            else:
                config.partner_email = account_emails[new_index - 1]
                Py4GW.Console.Log(BOT_NAME, f"Partner email set to: {config.partner_email}", 
                                Py4GW.Console.MessageType.Info)
    else:
        PyImGui.text_colored("No other accounts detected in shared memory", (1, 0.5, 0, 1))
    
    PyImGui.separator()
    
    # Party Configuration Tab
    if PyImGui.collapsing_header("Party Configuration", True):
        PyImGui.text("Party Members (select 3 accounts to invite):")
        
        # Ensure party_members list has 3 slots
        while len(config.party_members) < 3:
            config.party_members.append("")
        while len(config.party_member_indices) < 3:
            config.party_member_indices.append(0)
        
        for i in range(3):
            PyImGui.text(f"Member {i+1}:")
            
            if available_accounts_data:
                member_display = ["(None)"] + [display for _, display in available_accounts_data]
                member_emails = [email for email, _ in available_accounts_data]
                
                # Update index if current member email is in the list
                if config.party_members[i] and config.party_members[i] in member_emails:
                    config.party_member_indices[i] = member_emails.index(config.party_members[i]) + 1
                elif not config.party_members[i]:
                    config.party_member_indices[i] = 0
                else:
                    # Member email is set but not in list - reset to None
                    config.party_member_indices[i] = 0
                    config.party_members[i] = ""
                
                new_index = PyImGui.combo(f"##party_member_{i}", config.party_member_indices[i], member_display)
                
                if new_index != config.party_member_indices[i]:
                    config.party_member_indices[i] = new_index
                    if new_index == 0:
                        config.party_members[i] = ""
                    else:
                        config.party_members[i] = member_emails[new_index - 1]
                        Py4GW.Console.Log(BOT_NAME, f"Party member {i+1} set to: {config.party_members[i]}", 
                                        Py4GW.Console.MessageType.Info)
        
        # Button to invite party members
        if PyImGui.button("Invite Party Members", 200, 25):
            if config.is_leader:
                # Add log before to confirm button was clicked
                Py4GW.Console.Log(BOT_NAME, "Button clicked - starting invite process", Py4GW.Console.MessageType.Info)
                # Instead of using AddCustomState, schedule it as a coroutine directly
                from Py4GWCoreLib import GLOBAL_CACHE
                GLOBAL_CACHE.Coroutines.append(invite_party_members())
                Py4GW.Console.Log(BOT_NAME, "Inviting party members...", Py4GW.Console.MessageType.Info)
            else:
                Py4GW.Console.Log(BOT_NAME, "Only leaders can invite party members!", 
                                Py4GW.Console.MessageType.Warning)
    
    PyImGui.separator()
    
    # Leader/Support mode toggle
    new_leader = PyImGui.checkbox("Is Leader (uncheck for Support script)", config.is_leader)
    if new_leader != config.is_leader:
        config.is_leader = new_leader
        Py4GW.Console.Log(BOT_NAME, f"Mode changed to: {'Leader' if config.is_leader else 'Support'}", 
                        Py4GW.Console.MessageType.Info)
    
    # Team role toggle (only for leaders)
    if config.is_leader:
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
        
        # Payback Mode toggle (for losing team)
        if not config.is_winning_team:
            new_payback = PyImGui.checkbox("Payback Mode (go aggressive on desync)", config.payback_mode)
            if new_payback != config.payback_mode:
                config.payback_mode = new_payback
                Py4GW.Console.Log(BOT_NAME, f"Payback Mode {'enabled' if config.payback_mode else 'disabled'}", 
                                Py4GW.Console.MessageType.Info)
        
        # Resign Mode toggle (for winning team)
        if config.is_winning_team:
            new_resign = PyImGui.checkbox("Resign Mode (return on desync)", config.resign_mode)
            if new_resign != config.resign_mode:
                config.resign_mode = new_resign
                Py4GW.Console.Log(BOT_NAME, f"Resign Mode {'enabled' if config.resign_mode else 'disabled'}", 
                                Py4GW.Console.MessageType.Info)
        
        # Both Teams Resign Mode toggle
        PyImGui.separator()
        new_both_resign = PyImGui.checkbox("Both Teams Resign Mode", config.both_teams_resign_mode)
        if new_both_resign != config.both_teams_resign_mode:
            config.both_teams_resign_mode = new_both_resign
            Py4GW.Console.Log(BOT_NAME, f"Both Teams Resign Mode {'enabled' if config.both_teams_resign_mode else 'disabled'}", 
                            Py4GW.Console.MessageType.Info)
        
        if config.both_teams_resign_mode:
            PyImGui.text_colored("Both Teams Resign Mode Active!", (1, 1, 0, 1))
            PyImGui.text_wrapped("When enabled: Check if map is The Crag (act normally), otherwise disable Aggressive Mode, losing team switches to Set 1, wait 5m45s, all resign, wait for outpost.")
    
    PyImGui.separator()
    
    # Status display
    if config.is_leader:
        PyImGui.text("Progress:")
        PyImGui.text(f"Strongboxes Earned: {config.strongboxes_earned}/{config.target_strongboxes}")
        PyImGui.text(f"Consecutive Wins: {config.consecutive_wins}/{TOTAL_WINS_FOR_STRONGBOX}")
        
        # Calculate progress percentage
        progress = config.strongboxes_earned / config.target_strongboxes
        PyImGui.progress_bar(progress, 200, 20, f"{config.strongboxes_earned}/{config.target_strongboxes}")
        
        PyImGui.separator()
    
    PyImGui.text("Status:")
    
    # Desync indicator
    if config.desync_detected:
        PyImGui.text_colored("DESYNC DETECTED!", (1, 0, 0, 1))
        PyImGui.text(f"Partner Map ID: {config.last_partner_map_id}")
    
    if config.in_match:
        PyImGui.text_colored("IN MATCH", (0, 1, 0, 1))
    elif config.ready_to_queue:
        PyImGui.text_colored("READY TO QUEUE", (1, 1, 0, 1))
    else:
        PyImGui.text_colored("IDLE", (0.5, 0.5, 0.5, 1))
    
    PyImGui.separator()
    
    # Reset button (only for leaders)
    if config.is_leader:
        if PyImGui.button("Reset Stats", 150, 25):
            config.strongboxes_earned = 0
            config.consecutive_wins = 0
            config.first_queue_completed = False
            config.desync_detected = False
            Py4GW.Console.Log(BOT_NAME, "Stats reset.", Py4GW.Console.MessageType.Info)
    
    PyImGui.separator()
    PyImGui.text_wrapped("Instructions: Leaders run the main bot with team configuration. Support scripts run on non-leader accounts to receive commands. Enable Payback Mode (losing team) to go aggressive on desync. Enable Resign Mode (winning team) to return to outpost on desync.")


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
