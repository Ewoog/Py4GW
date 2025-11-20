# Codex Arena Bot

A Guild Wars automation bot for farming Codex Arena wins using multiboxing.

## Overview

This bot automates Codex Arena matches with two teams of 4 players each:
- **Winning Team**: Uses Equipment Set 1, plays to win matches
- **Losing Team**: Uses Equipment Set 2, designed to lose quickly

The bot runs until each team achieves 27 wins, then automatically shuts down.

## Requirements

- Py4GW framework installed and configured
- 8 Guild Wars accounts (4 per team)
- Multiboxing enabled with shared memory support
- Both equipment sets configured in-game

## Setup Instructions

### 1. Equipment Sets

Before running the bot, configure your equipment sets in Guild Wars:

**Equipment Set 1 (Winning Team):**
- Set up your competitive PvP build
- Ensure weapons and armor are optimized for winning

**Equipment Set 2 (Losing Team):**
- Can use minimal equipment or default setup
- This team is designed to lose quickly

### 2. Party Formation

1. Launch 8 Guild Wars clients (2 will run the bot as leaders)
2. Manually invite 3 other players to each leader's party
3. You should have two groups of 4 players each

### 3. Bot Configuration

Run the bot on both team leaders:

**Instance 1 (Winning Team):**
```bash
# Load Codex_Arena_Bot.py on the winning team leader
# In the bot GUI, check "Is Winning Team"
```

**Instance 2 (Losing Team):**
```bash
# Load Codex_Arena_Bot.py on the losing team leader  
# In the bot GUI, uncheck "Is Winning Team"
```

### 4. Starting the Bot

1. Ensure both team leaders are in Codex Arena outpost (Map ID: 796)
2. Click "Start Bot" in both instances
3. The bots will synchronize and begin queueing together

## How It Works

### Synchronization

The bots use Py4GW's shared memory system to communicate:

1. **Ready Phase**: Both bots signal when they're ready to queue
2. **Queue Phase**: Once both are ready, they enter the queue simultaneously
3. **Match Phase**: Bots track when the match starts and ends
4. **Repeat**: Process continues until win targets are met

### Win Tracking

- **Phase 1**: Team 1 plays until 27 wins
- **Role Switch**: Teams automatically switch roles
- **Phase 2**: Team 2 (now with switched roles) plays until 27 wins
- **Shutdown**: Bot stops after both teams complete their runs

### Match Logic

**Winning Team:**
- Enters the match
- Plays normally (automated combat if configured)
- Waits for natural match completion
- Increments win counter
- Re-queues immediately

**Losing Team:**
- Enters the match
- Attempts to return to outpost after a set time
- Does not increment win counter (loss expected)
- Re-queues after returning to outpost

## Configuration Options

### In-Code Settings

Edit `Codex_Arena_Bot.py` to modify:

```python
config.target_wins = 27  # Wins needed before role switch (default: 27)
```

### GUI Settings

- **Is Winning Team**: Toggle whether this instance is the winning or losing team
- **Team Stats**: View current wins for Team 1 and Team 2
- **Start/Stop**: Control the bot execution

## Troubleshooting

### Bots Don't Queue Together

- Ensure both bots are in the same outpost
- Check that shared memory is working (other multibox features work)
- Verify both bots show "ready" status in logs

### Match Doesn't Start

- Codex Arena may have population requirements
- Try queueing during peak hours
- Check that you have the minimum party size

### Equipment Sets Don't Switch

- Verify equipment sets are configured in-game
- Check the keybind for "Activate Weapon Set" is set
- Ensure the bot has proper permissions

### Bot Gets Stuck

- Check the console logs for error messages
- Verify map ID is correct (796 for Codex Arena)
- Restart both bot instances if necessary

## Advanced Configuration

### Custom Synchronization Delay

If teams are not queueing at the exact same time, adjust the sync delay:

```python
# In bot_main_loop function, modify:
yield from Routines.Yield.wait(1000)  # Increase if needed
```

### Match Duration

Adjust how long the winning team waits in a match:

```python
# In winning_team_logic function:
yield from Routines.Yield.wait(30000)  # 30 seconds, increase if needed
```

## Safety Notes

- This bot is for educational purposes
- Use at your own risk
- Multiboxing and automation may violate game terms of service
- Always supervise automated gameplay

## Support

For issues or questions:
1. Check the Py4GW documentation
2. Review console logs for error messages
3. Ensure all dependencies are properly installed

## Version History

- **1.0.0**: Initial release with basic Codex Arena automation
  - Multibox synchronization
  - Equipment set switching
  - Win tracking and role switching
  - Auto-shutdown after completion
