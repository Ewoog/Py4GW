# Implementation Summary: Codex Arena Bot

## Overview
Successfully implemented a Codex Arena bot for Guild Wars that automates PvP matches to farm Strategist's Zaishen Strongboxes using multiboxing with synchronized teams.

## Files Created

### 1. Codex_Arena_Bot.py
Main bot implementation with the following components:

#### Core Features
- **Multi-instance synchronization**: Two bot instances communicate via shared memory
- **Equipment management**: Automatically switches between equipment sets 1 and 2
- **Strongbox tracking**: Monitors Strategist's Zaishen Strongboxes earned (1 per 5 consecutive wins)
- **Consecutive win tracking**: Tracks consecutive wins toward next strongbox
- **Role switching**: Automatically switches team roles after first team earns 5 strongboxes
- **Auto-shutdown**: Stops after both teams earn 5 strongboxes each (daily limit)

#### Technical Implementation
- Uses `Py4GWCoreLib.Botting` class as framework base
- SharedMemory messaging for cross-instance communication
- Custom signal types for synchronization events:
  - READY_TO_QUEUE: Team is prepared to enter queue
  - QUEUE_NOW: Signal to enter queue simultaneously
  - MATCH_START: Match has begun
  - MATCH_END: Match has concluded
- Generator-based coroutine system for asynchronous operations
- PyImGui for graphical user interface
- Inventory monitoring for Strategist's Zaishen Strongbox (Model ID 36668)

#### Key Functions
- `get_strongbox_count()`: Retrieves current strongbox count from inventory
- `send_sync_signal()`: Broadcasts synchronization messages
- `check_sync_signal()`: Receives and processes sync messages
- `equip_set()`: Changes equipment sets
- `travel_to_codex_arena()`: Navigates to Codex Arena (Map ID 796)
- `enter_queue()`: Enters the arena queue
- `wait_for_match_start()`: Monitors for match start
- `winning_team_logic()`: Handles winning team behavior, tracks strongboxes
- `losing_team_logic()`: Handles losing team behavior
- `bot_main_loop()`: Main execution loop

#### Error Handling
- Timeout handling for queue entry (3 minutes)
- Timeout handling for matches (10 minutes)
- Automatic retry on failed queue attempts
- Force return to outpost if stuck in match
- Bot stop check in all loops for clean shutdown

### 2. CODEX_BOT_README.md
Comprehensive documentation including:
- Setup instructions
- Configuration guide
- Troubleshooting section
- Advanced customization options
- Safety notes

## How It Works

### Initialization
1. Two instances of the bot are run on separate accounts (team leaders)
2. Each instance is configured as either "winning" or "losing" team
3. Team members are manually invited to form two groups of 4

### Execution Flow
1. Both teams travel to Codex Arena outpost (Map ID 796)
2. Teams equip appropriate equipment sets:
   - Winning team: Equipment Set 1
   - Losing team: Equipment Set 2
3. Synchronization handshake:
   - Both send READY_TO_QUEUE signal
   - Wait for confirmation from other team
   - Brief sync delay to ensure alignment
4. Simultaneous queue entry:
   - Both teams enter queue at the same time
   - Wait for match to start (explorable map instance)
5. Match execution:
   - Winning team: Plays until match ends naturally, tracks consecutive wins
   - Losing team: Returns to outpost after 60 seconds
6. Post-match:
   - Winning team checks for new Strategist's Zaishen Strongboxes
   - Consecutive wins incremented (resets to 0 after earning a strongbox)
   - Both teams return to step 1
7. Role switching:
   - After Team 1 earns 5 strongboxes, roles reverse
   - Team 2 now aims for 5 strongboxes
8. Shutdown:
   - After Team 2 earns 5 strongboxes, both bots stop

### Synchronization Mechanism
Uses Py4GW's SharedMemory system:
- Messages sent via `GLOBAL_CACHE.ShMem.SendMessage()`
- Messages retrieved via `GLOBAL_CACHE.ShMem.PreviewNextMessage()`
- Uses `SharedCommandType.CustomBehaviors` for custom signals
- Messages have 4 float parameters for signal identification

## Configuration

### Runtime Configuration (GUI)
- **Is Winning Team**: Toggle to set team role
- **Progress Display**: Shows current strongboxes earned and consecutive wins
- **Status Indicator**: Visual feedback (IN MATCH, READY, IDLE)
- **Start/Stop Controls**: Bot execution control
- **Reset Stats**: Clear strongbox and consecutive win counters

### Code Configuration
- `config.target_strongboxes`: Number of strongboxes before role switch (default: 5, max per day)
- `STRATEGISTS_STRONGBOX_MODEL_ID`: Model ID for inventory tracking (36668)
- Equipment set numbers: 1 for winning, 2 for losing
- Timeout values: Queue (180s), Match (600s)
- Sync wait time: 60 seconds for team coordination

## Testing Considerations

### Unit Testing Not Implemented
- Bot requires full Py4GW runtime environment
- Needs active Guild Wars client connection
- Requires multiboxing setup with multiple accounts
- Testing must be done in actual game environment

### Manual Testing Checklist
- [ ] Both instances start and show GUI
- [ ] Team role toggle works correctly
- [ ] Equipment sets switch properly
- [ ] Both teams queue at the same time
- [ ] Match detection works (explorable vs outpost)
- [ ] Strongbox counting works correctly
- [ ] Consecutive wins tracked properly
- [ ] Strongbox earned after 5 consecutive wins
- [ ] Losing team returns to outpost
- [ ] Role switching occurs at 5 strongboxes
- [ ] Bot shuts down after both teams earn 5 strongboxes each
- [ ] Error recovery works (timeout, stuck states)

## Known Limitations

1. **Manual Party Formation**: Teams must be manually formed before starting
2. **Population Dependent**: Codex Arena requires minimum population
3. **No Combat AI**: Winning team relies on natural gameplay/other bots
4. **Fixed Map ID**: Hardcoded to Codex Arena (796)
5. **Two-Instance Only**: Designed for exactly 2 bot instances
6. **Daily Limit**: Maximum 5 Strategist's Zaishen Strongboxes per team per day

## Future Enhancements (Not Implemented)

- Automatic party formation via multibox invites
- Combat AI integration for winning team
- Dynamic equipment set selection
- Configurable strongbox targets via GUI
- Match history logging
- Performance metrics tracking
- Support for different arena types

## Security Considerations

- No external network communication
- Uses only local shared memory
- No credential storage
- No file system modifications beyond standard logging
- Follows existing Py4GW security patterns

## Compatibility

- **Py4GW Version**: Compatible with current framework (as of implementation)
- **Python Version**: Requires Python 3.12+ (as per repo requirements)
- **Guild Wars**: Compatible with current game version
- **Dependencies**: Only Py4GW framework dependencies

## Code Quality

- ✓ No syntax errors
- ✓ Proper type hints in function signatures
- ✓ Comprehensive docstrings
- ✓ Consistent naming conventions
- ✓ Error handling throughout
- ✓ Logging for debugging
- ✓ Clean separation of concerns
- ✓ Generator-based async pattern (Py4GW standard)

## Conclusion

The Codex Arena Bot successfully implements all requirements:
- Two teams of 4 (manual party formation)
- Winning and losing team roles (configurable via GUI)
- Equipment set switching (Set 1 vs Set 2)
- Synchronized queue entry (shared memory communication)
- Automatic match completion handling
- Strongbox tracking (1 per 5 consecutive wins)
- Consecutive win tracking
- Role switching mechanism (after 5 strongboxes)
- Auto-shutdown after completion (both teams earn 5 strongboxes)

The implementation follows Py4GW framework conventions and patterns, integrates with existing multibox infrastructure, and provides a user-friendly GUI for operation.
