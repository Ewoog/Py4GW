# Codex PvP Bot

A bot for playing Codex Arena PvP mode in Guild Wars with 4-account multibox support.

## Features

- **Arena Detection**: Automatically detects which random arena you're in
- **Team Spawn Detection**: Identifies your team's spawn location by analyzing allied player positions
- **Enemy Location Detection**: Finds enemy spawn by detecting enemy positions or estimating from map boundaries
- **Auto Navigation**: Uses pathfinding to navigate to the enemy team
- **Auto Combat**: Engages in PvP combat using the built-in combat system
- **Loss/Victory Handling**: Automatically handles returning to the Codex Arena outpost after matches
- **Multibox Support**: Coordinates up to 4 accounts in a party for team PvP

## Requirements

1. Guild Wars client with Py4GW installed
2. 4 Guild Wars accounts (for full multibox functionality)
3. Characters that can enter Codex Arena (PvP characters or PvE characters with unlocked skills)

## Setup

1. Navigate to Codex Arena outpost (Map ID 796) with all 4 accounts
2. Use multibox to party all accounts together
3. Run the `Codex_PvP_Bot.py` script on all accounts
4. Enter the Codex Arena queue

## How It Works

### Match Flow

1. **Wait for Arena Entry**: Bot waits for the party to enter an arena instance
2. **Arena Detection**: Once in an arena, the bot:
   - Detects the current arena map ID
   - Identifies team spawn location from allied player positions
   - Locates enemy spawn (from enemy positions or estimates from map bounds)
3. **Navigation**: Bot navigates toward the enemy spawn location
4. **Combat**: Engages enemies using the auto-combat system
5. **Match End**: Returns to Codex Arena outpost after victory or defeat

### Arena Detection

The bot recognizes these Codex arenas:

- Ascalon Arena (308)
- Shiverpeak Arena (314, 322, 343)
- D'Alessio Arena (318, 339)
- Amnoon Arena (319, 340)
- Petrified Arena (353)
- Seabed Arena (354)

If an unrecognized arena is encountered, the bot will still function but display "Unknown Arena [Map ID]".

### Spawn Detection

**Team Spawn**: Calculated as the average position of all allied players

**Enemy Spawn**: 
- If enemies are visible: average position of enemy players
- If enemies not yet visible: estimated as opposite corner from team spawn based on map boundaries

## Usage

### Running the Bot

Load the script in Py4GW:

```python
from Bots.Codex_PvP_Bot import main, configure

# Call main() in your update loop
# Call configure() for configuration UI
```

Or run directly:
```bash
python Bots/Codex_PvP_Bot.py
```

### UI Information

The bot displays a status window showing:
- Number of matches played
- Whether currently in an arena
- Current arena map ID and name
- Team and enemy spawn coordinates

### Multibox Coordination

The bot includes multibox coordination:
```python
bot.Multibox.InviteAllAccounts()  # Invites all configured accounts to party
```

Make sure your accounts are configured in the Py4GW multibox system.

## Configuration

The bot uses the standard Botting class configuration with:

- **Auto Combat**: Enabled (for PvP engagement)
- **Auto Loot**: Disabled (not needed in PvP)
- **Auto Inventory Management**: Disabled (not needed in PvP)

You can customize these settings in the bot configuration UI.

## Troubleshooting

### Bot doesn't move toward enemies
- Ensure the arena map has valid pathing data
- Check that enemy spawn detection is working (visible in status UI)
- Verify auto-pathing is enabled in configuration

### Bot doesn't enter combat
- Ensure auto-combat is enabled in configuration
- Check that your skillbar is loaded with appropriate PvP skills
- Verify the bot can find enemies (check targeting system)

### Multibox not working
- Ensure all accounts are configured in Py4GW multibox settings
- Verify all accounts are in the same district/region
- Check that party invites are being sent/accepted

### Bot stuck after match
- The bot should automatically return to outpost after a match
- If stuck, manually return to Codex Arena outpost (Map ID 796)
- Check console logs for error messages

## Technical Details

### Code Structure

- `CodexPvPState`: Tracks current match state (arena, spawns, match count)
- `detect_arena_and_spawns()`: Analyzes map and agents to determine locations
- `wait_for_arena_entry()`: Waits for map transition to arena
- `navigate_to_enemies()`: Pathfinding to enemy location
- `engage_combat()`: Combat loop until match ends
- `handle_loss_or_victory()`: Post-match cleanup
- `codex_pvp_match_routine()`: Main match flow orchestrator

### Dependencies

- `Py4GWCoreLib`: Core library with Botting class
- `PyImGui`: UI rendering
- `Py4GW`: Game interaction APIs
- `GLOBAL_CACHE`: Access to game state (Map, Agent, Player)
- `Routines`: Movement, targeting, and combat routines

## Known Limitations

1. **Skill Usage**: The bot relies on the auto-combat system for skill usage. You need to configure appropriate PvP builds.
2. **Strategy**: The bot uses a simple "rush enemy spawn" strategy. More complex tactics would require additional logic.
3. **Terrain**: Some arenas may have terrain obstacles that affect pathfinding.
4. **Party Coordination**: While multibox support exists, coordinated team tactics are limited to basic grouping.

## Future Improvements

Potential enhancements:

- Build templates for different professions
- More sophisticated combat strategies
- Terrain and obstacle avoidance
- Party role assignment (tank, healer, damage)
- Skill cooldown optimization
- Target prioritization
- Resurrection handling

## License

This bot is part of the Py4GW project. See the main repository for license information.

## Credits

Created using the Py4GW framework by the Py4GW community.
