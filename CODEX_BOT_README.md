# Codex Arena Bot

A Guild Wars automation bot for farming Strategist's Zaishen Strongboxes using multiboxing.

## Overview

This bot automates Codex Arena matches with two teams of 4 players each:
- **Winning Team**: Uses Equipment Set 1, plays to win matches
- **Losing Team**: Uses Equipment Set 2, designed to lose quickly

The bot tracks Strategist's Zaishen Strongboxes earned (1 per 5 consecutive wins) and shuts down after earning 5 strongboxes (daily limit).

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

1. **Ready Phase**: Both bots signal when they're ready to queue (first match only)
2. **Queue Phase**: Once both are ready, they enter the queue simultaneously
3. **Match Phase**: Bots track when the match starts and ends
4. **Repeat**: Process continues until strongbox targets are met
   - **Note**: After the first match, the losing team immediately re-enters the queue without waiting for synchronization, allowing for faster cycling

### Strongbox Tracking

- **Reward System**: 1 Strategist's Zaishen Strongbox earned per 5 consecutive wins
- **Target**: Earn 5 strongboxes (max per day)
- **Shutdown**: Bot stops after earning 5 strongboxes

### Match Logic

**Winning Team:**
- Enters the match
- **Special Arena Behavior**: In Seabed Arena or Deldrimor Arena, automatically moves to enemy priest location (HeroAI handles combat)
- Plays normally (HeroAI handles combat automatically)
- Waits for natural match completion
- Tracks consecutive wins
- Checks for strongbox acquisition
- Re-queues immediately

**Losing Team:**
- Enters the match
- Does NOT engage in special arena behavior (no priest movement)
- Attempts to return to outpost after a set time
- Does not increment win counter (loss expected)
- **Immediately re-enters queue** after returning to outpost (no synchronization wait on subsequent matches)

### Special Arena Behavior

The bot includes special logic for **Seabed Arena** and **Deldrimor Arena**:

- **Team Detection**: Automatically detects if the player is on the blue or red team based on proximity to spawn points
- **Initial Wait**: Winning team waits 30 seconds after entering the map before moving
- **Priest Targeting**: Winning team moves to the opposite team's priest location
  - If on blue team → moves to red priest
  - If on red team → moves to blue priest
- **HeroAI Combat**: Once at the priest location, HeroAI automatically handles combat
- **Combat Wait**: Bot waits until out of combat before proceeding
- **Normal Flow**: After combat completes, continues with normal match waiting logic
- **Losing Team**: Does nothing special - just returns to outpost as normal

**Arena Map IDs and Priest Locations:**
- **Seabed Arena (Map ID: 829)**
  - Blue Priest: (9737, 4344)
  - Red Priest: (4368, 6953)
- **Deldrimor Arena (Map ID: 830)**
  - Blue Priest: (-9259.12, 2708.83)
  - Red Priest: (-8994.74, 7384.57)

## Configuration Options

### In-Code Settings

Edit `Codex_Arena_Bot.py` to modify:

```python
config.target_strongboxes = 5  # Strongboxes needed before role switch (default: 5, max per day)
```

### GUI Settings

- **Is Winning Team**: Toggle whether this instance is the winning or losing team
- **Strongboxes Earned**: View current strongboxes earned
- **Consecutive Wins**: Track progress toward next strongbox (need 5 consecutive wins)
- **Progress Bar**: Visual progress toward 5 strongbox goal

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
