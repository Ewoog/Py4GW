from Py4GWCoreLib import *
import PyImGui, Py4GW
from typing import Generator, Any

BOT_NAME = "Codex PvP Bot"

# Map IDs for Codex Arena
CODEX_ARENA_OUTPOST = 796

# Known arena map IDs (these are the actual PvP arena instances)
# Note: These may vary - the bot will detect the actual arena map ID dynamically
KNOWN_ARENA_MAPS = {
    # Random Arenas that can be used in Codex
    308: "Ascalon Arena",
    314: "Shiverpeak Arena",
    318: "D'Alessio Arena",
    319: "Amnoon Arena",
    322: "Shiverpeak Arena",
    339: "D'Alessio Arena",
    340: "Amnoon Arena",
    343: "Shiverpeak Arena",
    353: "Petrified Arena",
    354: "Seabed Arena",
}

# Arena spawn detection - we'll detect team spawn by finding allied players
# Enemy spawn is typically opposite side of the map

bot = Botting(
    BOT_NAME,
    upkeep_auto_inventory_management_active=False,
    upkeep_auto_combat_active=True,  # Enable auto-combat for PvP
    upkeep_auto_loot_active=False,
)

class CodexPvPState:
    """Track state of the Codex PvP bot"""
    def __init__(self):
        self.current_arena_map_id = 0
        self.team_spawn_location = (0.0, 0.0)
        self.enemy_spawn_location = (0.0, 0.0)
        self.in_arena = False
        self.match_count = 0
        
codex_state = CodexPvPState()


def detect_arena_and_spawns() -> tuple[int, tuple[float, float], tuple[float, float]]:
    """
    Detect which arena we're in and identify team/enemy spawn locations.
    
    Analyzes the current map and agent positions to determine:
    - Arena map ID
    - Team spawn location (average of allied player positions)
    - Enemy spawn location (from enemy positions or estimated from map bounds)
    
    Returns: (map_id, team_spawn, enemy_spawn)
    """
    map_id = GLOBAL_CACHE.Map.GetMapID()
    
    # Get player position as initial team spawn reference
    player_x, player_y = GLOBAL_CACHE.Player.GetXY()
    team_spawn = (player_x, player_y)
    
    # Find allied players to refine team spawn location
    agent_array = GLOBAL_CACHE.AgentArray.GetAgentArray()
    ally_positions = []
    enemy_positions = []
    
    for agent_id in agent_array:
        if not GLOBAL_CACHE.Agent.IsValid(agent_id):
            continue
        
        if not GLOBAL_CACHE.Agent.IsLiving(agent_id):
            continue
            
        _, allegiance = GLOBAL_CACHE.Agent.GetAllegiance(agent_id)
        
        if allegiance == "Ally":
            # This is a teammate
            x, y = GLOBAL_CACHE.Agent.GetXY(agent_id)
            ally_positions.append((x, y))
        elif allegiance == "Enemy":
            # This is an enemy player
            x, y = GLOBAL_CACHE.Agent.GetXY(agent_id)
            enemy_positions.append((x, y))
    
    # Calculate average team spawn from allied positions
    if ally_positions:
        avg_x = sum(pos[0] for pos in ally_positions) / len(ally_positions)
        avg_y = sum(pos[1] for pos in ally_positions) / len(ally_positions)
        team_spawn = (avg_x, avg_y)
    
    # Calculate average enemy spawn if we can see enemies
    if enemy_positions:
        avg_x = sum(pos[0] for pos in enemy_positions) / len(enemy_positions)
        avg_y = sum(pos[1] for pos in enemy_positions) / len(enemy_positions)
        enemy_spawn = (avg_x, avg_y)
    else:
        # If we can't see enemies yet, estimate opposite side of map
        # This is a rough estimate - in practice, we'd navigate until we find them
        map_bounds = GLOBAL_CACHE.Map.GetMapBoundaries()
        if map_bounds != (0.0, 0.0, 0.0, 0.0):
            min_x, min_y, max_x, max_y = map_bounds
            # Estimate enemy spawn as opposite corner from team spawn
            if team_spawn[0] < (min_x + max_x) / 2:
                enemy_x = max_x - 500  # Near max boundary
            else:
                enemy_x = min_x + 500  # Near min boundary
                
            if team_spawn[1] < (min_y + max_y) / 2:
                enemy_y = max_y - 500
            else:
                enemy_y = min_y + 500
            enemy_spawn = (enemy_x, enemy_y)
        else:
            # Fallback if no map boundaries
            enemy_spawn = (-team_spawn[0], -team_spawn[1])
    
    return map_id, team_spawn, enemy_spawn


def wait_for_arena_entry(bot: Botting) -> Generator:
    """Wait until we enter an arena (map changes from outpost to explorable PvP)"""
    while True:
        yield
        
        if not GLOBAL_CACHE.Map.IsMapReady():
            continue
            
        current_map_id = GLOBAL_CACHE.Map.GetMapID()
        
        # Check if we're in an arena (not the outpost)
        if current_map_id != CODEX_ARENA_OUTPOST and GLOBAL_CACHE.Map.IsPVP():
            # We're in an arena!
            ConsoleLog(BOT_NAME, f"Entered arena: {current_map_id}", Console.MessageType.Info)
            break
        
        Py4GW.Console.Log(BOT_NAME, "Waiting for arena entry...", Console.MessageType.Info)
        yield from bot.Wait._coro_for_time(2000)


def navigate_to_enemies(bot: Botting, enemy_location: tuple[float, float]) -> Generator:
    """Navigate toward enemy spawn location"""
    target_x, target_y = enemy_location
    
    # Use auto-pathing if available, otherwise move directly
    try:
        yield from bot.Move._coro_get_path_to(target_x, target_y)
        yield from bot.Move._coro_follow_path_to()
    except:
        # Fallback to direct movement
        ConsoleLog(BOT_NAME, f"Moving directly to enemies at ({target_x}, {target_y})", Console.MessageType.Info)
        yield from bot.Move._coro_xy(target_x, target_y, "Move to enemy spawn")


def engage_combat(bot: Botting) -> Generator:
    """Engage in combat with enemies - use auto-combat system"""
    ConsoleLog(BOT_NAME, "Engaging in combat", Console.MessageType.Info)
    
    # Combat loop - continue until we win or lose
    while True:
        yield
        
        # Check if we're back in outpost (lost/won)
        current_map_id = GLOBAL_CACHE.Map.GetMapID()
        if current_map_id == CODEX_ARENA_OUTPOST:
            ConsoleLog(BOT_NAME, "Match ended - back in outpost", Console.MessageType.Info)
            break
        
        # Check if we're dead
        player_id = GLOBAL_CACHE.Player.GetAgentID()
        if GLOBAL_CACHE.Agent.IsDead(player_id):
            ConsoleLog(BOT_NAME, "Player is dead, waiting for respawn or match end", Console.MessageType.Warning)
            yield from bot.Wait._coro_for_time(5000)
            continue
        
        # The auto-combat system will handle targeting and skill usage
        # Just need to ensure we're in combat range
        
        # Find nearest enemy
        enemy_id = Routines.Targeting.GetEnemyAttacking(max_distance=Range.Compass.value)
        if enemy_id and enemy_id > 0:
            # Move toward enemy if too far
            enemy_x, enemy_y = GLOBAL_CACHE.Agent.GetXY(enemy_id)
            player_x, player_y = GLOBAL_CACHE.Player.GetXY()
            
            distance = ((enemy_x - player_x)**2 + (enemy_y - player_y)**2)**0.5
            
            if distance > Range.Compass.value:
                # Too far, move closer
                yield from bot.Move._coro_xy(enemy_x, enemy_y, "Approach enemy")
        
        yield from bot.Wait._coro_for_time(500)


def handle_loss_or_victory(bot: Botting) -> Generator:
    """Handle returning to outpost after match"""
    ConsoleLog(BOT_NAME, "Waiting for return to outpost", Console.MessageType.Info)
    
    # Wait for map to stabilize
    while GLOBAL_CACHE.Map.IsMapLoading():
        yield
    
    yield from bot.Wait._coro_for_time(2000)
    
    # Verify we're in outpost
    current_map_id = GLOBAL_CACHE.Map.GetMapID()
    if current_map_id == CODEX_ARENA_OUTPOST:
        codex_state.match_count += 1
        ConsoleLog(BOT_NAME, f"Match {codex_state.match_count} completed. Ready for next match.", Console.MessageType.Success)
    else:
        ConsoleLog(BOT_NAME, f"Unexpected map after match: {current_map_id}", Console.MessageType.Error)


def codex_pvp_match_routine(bot: Botting) -> Generator:
    """Main routine for a single Codex PvP match"""
    
    # Step 1: Wait for arena entry
    ConsoleLog(BOT_NAME, "Waiting to enter arena...", Console.MessageType.Info)
    yield from wait_for_arena_entry(bot)
    
    # Step 2: Detect arena and spawn locations
    ConsoleLog(BOT_NAME, "Detecting arena and spawn locations...", Console.MessageType.Info)
    yield from bot.Wait._coro_for_time(2000)  # Wait for map to fully load
    
    map_id, team_spawn, enemy_spawn = detect_arena_and_spawns()
    codex_state.current_arena_map_id = map_id
    codex_state.team_spawn_location = team_spawn
    codex_state.enemy_spawn_location = enemy_spawn
    codex_state.in_arena = True
    
    arena_name = KNOWN_ARENA_MAPS.get(map_id, f"Unknown Arena {map_id}")
    ConsoleLog(BOT_NAME, f"Arena: {arena_name}", Console.MessageType.Info)
    ConsoleLog(BOT_NAME, f"Team spawn: {team_spawn}", Console.MessageType.Info)
    ConsoleLog(BOT_NAME, f"Enemy spawn: {enemy_spawn}", Console.MessageType.Info)
    
    # Step 3: Navigate to enemy location
    ConsoleLog(BOT_NAME, "Moving toward enemy team...", Console.MessageType.Info)
    yield from navigate_to_enemies(bot, enemy_spawn)
    
    # Step 4: Engage in combat
    yield from engage_combat(bot)
    
    # Step 5: Handle post-match (loss or victory)
    codex_state.in_arena = False
    yield from handle_loss_or_victory(bot)


def multibox_coordination(bot: Botting) -> Generator:
    """Coordinate multiple accounts for team play"""
    
    # Invite all accounts to party if we're the leader
    # This assumes accounts are configured in the multibox system
    try:
        bot.Multibox.InviteAllAccounts()
        yield from bot.Wait._coro_for_time(3000)
        
        ConsoleLog(BOT_NAME, "Multibox accounts invited to party", Console.MessageType.Success)
    except Exception as e:
        ConsoleLog(BOT_NAME, f"Multibox coordination note: {e}", Console.MessageType.Warning)
    
    yield


def create_bot_routine(bot: Botting) -> None:
    """Main bot routine - runs continuously"""
    bot.States.AddHeader(f"{BOT_NAME}")
    
    # Initial setup
    bot.States.AddCustomState(lambda: multibox_coordination(bot), "Multibox Setup")
    
    # Ensure we're in Codex Arena outpost
    def check_location():
        current_map = GLOBAL_CACHE.Map.GetMapID()
        if current_map != CODEX_ARENA_OUTPOST:
            ConsoleLog(BOT_NAME, f"Not in Codex Arena outpost. Please travel there first (Map ID: {CODEX_ARENA_OUTPOST})", Console.MessageType.Error)
            # Could add auto-travel here if needed
            yield from bot.Wait._coro_for_time(5000)
        yield
    
    bot.States.AddCustomState(lambda: check_location(), "Verify Location")
    
    # Main match loop - run matches continuously
    # Each iteration is one complete match
    def match_loop():
        while True:
            yield from codex_pvp_match_routine(bot)
            # Brief pause between matches
            yield from bot.Wait._coro_for_time(3000)
    
    bot.States.AddCustomState(lambda: match_loop(), "Codex PvP Match Loop")


# Set up the bot
bot.SetMainRoutine(create_bot_routine)


def configure():
    """Configuration UI"""
    global bot
    bot.UI.draw_configure_window()


def main():
    """Main update function called every frame"""
    bot.Update()
    
    # Draw custom UI
    if PyImGui.begin(f"{BOT_NAME} - Status"):
        PyImGui.text(f"Matches Played: {codex_state.match_count}")
        PyImGui.text(f"In Arena: {'Yes' if codex_state.in_arena else 'No'}")
        
        if codex_state.in_arena:
            PyImGui.text(f"Arena Map ID: {codex_state.current_arena_map_id}")
            arena_name = KNOWN_ARENA_MAPS.get(codex_state.current_arena_map_id, "Unknown")
            PyImGui.text(f"Arena Name: {arena_name}")
            PyImGui.text(f"Team Spawn: ({codex_state.team_spawn_location[0]:.1f}, {codex_state.team_spawn_location[1]:.1f})")
            PyImGui.text(f"Enemy Spawn: ({codex_state.enemy_spawn_location[0]:.1f}, {codex_state.enemy_spawn_location[1]:.1f})")
        
        PyImGui.separator()
        PyImGui.text("Instructions:")
        PyImGui.text("1. Be in Codex Arena outpost (Map ID 796)")
        PyImGui.text("2. Have 4 accounts in party via multibox")
        PyImGui.text("3. Enter the arena queue")
        PyImGui.text("4. Bot will detect arena and navigate to enemies")
        
    PyImGui.end()
    
    bot.UI.draw_window()


if __name__ == "__main__":
    main()
