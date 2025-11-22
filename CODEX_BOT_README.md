# Codex Arena Bot

A Guild Wars automation bot for farming Strategist's Zaishen Strongboxes using multiboxing.

## Overview

This bot automates Codex Arena matches with two teams of 4 players each:
- **Winning Team**: Uses Equipment Set 1, plays to win matches with HeroAI enabled
- **Losing Team**: Uses Equipment Set 2, designed to lose quickly with HeroAI disabled

The bot tracks Strategist's Zaishen Strongboxes earned (1 per 5 consecutive wins) and shuts down after earning 5 strongboxes (daily limit).

## Features

- **Character Name Display**: Partner and party member selection shows character names alongside emails
- **Party Configuration**: Leaders can configure and auto-invite 3 party members
- **Messaging Integration**: Uses Messaging.py widget for party commands (no separate support script needed)
- **HeroAI Control**: Winning team enables HeroAI for aggressive play, losing team disables it
- **Map Verification**: Two leaders verify they're in the same map to detect desyncs
- **Desync Detection**: GUI displays when teams are in different maps
- **Payback Mode**: Losing team equips Set 1 and enables HeroAI when desync detected
- **Resign Mode**: Winning team returns to outpost with Set 2 when desync detected

## Requirements

- Py4GW framework installed and configured
- 8 Guild Wars accounts (4 per team)
- Multiboxing enabled with shared memory support
- Both equipment sets configured in-game
- **Messaging.py widget** running on all non-leader accounts

## Setup Instructions

### 1. Equipment Sets

Before running the bot, configure your equipment sets in Guild Wars:

**Equipment Set 1 (Winning Team):**
- Set up your competitive PvP build
- Ensure weapons and armor are optimized for winning
- Bind to F1 key

**Equipment Set 2 (Losing Team):**
- Can use minimal equipment or default setup
- This team is designed to lose quickly
- Bind to F2 key

### 2. Account Configuration

1. Launch 8 Guild Wars clients
2. On the 2 team leader accounts:
   - Load `Codex_Arena_Bot.py`
3. On the 6 party member accounts:
   - Load and enable **Messaging.py widget**
   - This widget handles all party commands automatically

### 3. Bot Configuration

**Winning Team Leader:**
- Check "Is Winning Team"
- Select the losing team leader's email as partner
- Configure 3 party members in the Party Configuration tab
- Optional: Enable "Resign Mode" to return to outpost on desync
- Click "Invite Party Members" button to auto-invite configured members

**Losing Team Leader:**
- Uncheck "Is Winning Team"
- Select the winning team leader's email as partner
- Configure 3 party members in the Party Configuration tab
- Optional: Enable "Payback Mode" to go aggressive on desync
- Click "Invite Party Members" button to auto-invite configured members

**Party Member Accounts:**
- Enable **Messaging.py widget**
- The widget automatically handles:
  - Party invites (accept automatically)
  - Leave/Resign commands
  - Equipment set switching (F1/F2 keys)
  - HeroAI enable/disable for aggressive mode

### 4. Starting the Bot

1. Ensure both team leaders are in Codex Arena outpost (Map ID: 796)
### 4. Starting the Bot

1. Ensure both team leaders are in Codex Arena outpost (Map ID: 796)
2. Enable **Messaging.py widget** on all 6 party member accounts
3. Click "Start Bot" on both team leaders
4. Leaders will automatically invite their configured party members
5. The bots will synchronize and begin queueing together

## How It Works

### Synchronization

The bots use Py4GW's shared memory system to communicate:

1. **Ready Phase**: Both leaders signal when they're ready to queue (first match only)
2. **Queue Phase**: Once both are ready, they enter the queue simultaneously
3. **Match Phase**: Leaders track when the match starts and ends
4. **Map Verification**: Upon entering arena, leaders exchange map IDs to detect desync
5. **HeroAI Control**: Leaders send commands to party members via Messaging widget
6. **Repeat**: Process continues until strongbox targets are met
   - **Note**: After the first match, the losing team immediately re-enters the queue without waiting for synchronization, allowing for faster cycling

### Map Verification and Desync Detection

When entering an arena map (not the outpost):
1. Both leaders send their current map ID to their partner
2. Each leader verifies they received the same map ID
3. If map IDs don't match, a **DESYNC** is detected and displayed in the GUI
4. Desync triggers special behavior based on configured modes:
   - **Payback Mode** (Losing Team): Equips Set 1, enables HeroAI, and rushes enemy spawn
   - **Resign Mode** (Winning Team): Equips Set 2 and returns to outpost

### Party Command System

Leaders send commands to party members via **SharedCommandType** messages (handled by Messaging.py widget):
- **InviteToParty**: Uses mutual invite pattern for automatic party formation
  - Leader sends chat invite to member
  - Leader sends SharedMessage with sender's agent ID
  - Messaging widget receives message and sends invite back to leader
  - Guild Wars sees mutual invites and automatically forms the party
- **LeaveParty**: Leave the current party
- **Resign**: Return to outpost
- **PressKey**: Switch equipment sets (F1 for Set 1, F2 for Set 2)
- **EnableHeroAI**: Enable HeroAI for aggressive combat (winning team)
- **DisableHeroAI**: Disable HeroAI for passive play (losing team)

### Strongbox Tracking

- **Reward System**: 1 Strategist's Zaishen Strongbox earned per 5 consecutive wins
- **Target**: Earn 5 strongboxes (max per day)
- **Shutdown**: Bot stops after earning 5 strongboxes

### Match Logic

**Winning Team:**
- Enters the match with **HeroAI enabled** for party members
- **Map Verification**: Checks map ID with partner team
- **Special Arena Behavior**: In Seabed Arena or Deldrimor Arena, automatically moves to enemy priest location (HeroAI handles combat)
- **Aggressive Mode**: When enabled, rushes enemy spawn on all maps
- **Desync Handling**: If Resign Mode is active and desync detected, equips Set 2 and returns to outpost
- Waits for natural match completion
- Tracks consecutive wins
- Checks for strongbox acquisition
- Re-queues immediately

**Losing Team:**
- Enters the match with **HeroAI disabled** for party members (passive play)
- **Map Verification**: Checks map ID with partner team
- **Desync Handling**: If Payback Mode is active and desync detected, equips Set 1, enables HeroAI, and goes aggressive
- Does NOT engage in special arena behavior normally (no priest movement)
- Attempts to return to outpost after a set time
- Does not increment win counter (loss expected)
- **Immediately re-enters queue** after returning to outpost (no synchronization wait on subsequent matches)

### Special Arena Behavior

**All Maps:**
- **Initial Wait**: Winning team waits 30 seconds after entering any arena map before taking action (80 seconds if at 4/5 wins)

**Seabed Arena and Deldrimor Arena:**

- **Team Detection**: Automatically detects if the player is on the blue or red team based on proximity to spawn points
- **Priest Targeting**: Winning team moves to the opposite team's priest location
  - If on blue team → moves to red priest
  - If on red team → moves to blue priest
- **HeroAI Combat**: Once at the priest location, HeroAI automatically handles combat
- **Combat Wait**: Bot waits until out of combat before proceeding
- **Normal Flow**: After combat completes, continues with normal match waiting logic
- **Losing Team**: Does nothing special normally - just returns to outpost

**Aggressive Mode:**
- When enabled on winning team, rushes enemy spawn on ALL maps (not just priest maps)
- Uses 30-second initial wait (80 seconds if at 4/5 wins)

**Arena Map IDs and Priest Locations:**
- **Seabed Arena (Map ID: 829)**
  - Blue Priest: (9737, 4344)
  - Red Priest: (4368, 6953)
- **Deldrimor Arena (Map ID: 830)**
  - Blue Priest: (-9259.12, 2708.83)
  - Red Priest: (-8994.74, 7384.57)

## Configuration Options

### GUI Settings (Main Bot)

**Leader Settings:**
- **Partner Account Email**: Select the other team leader (displays character name with email)
- **Party Configuration**: Configure 3 party members to auto-invite
- **Is Leader**: Toggle between leader and support mode
- **Is Winning Team**: Toggle whether this instance is the winning or losing team
- **Aggressive Mode**: Make winning team rush enemy spawn on all maps
- **Payback Mode** (Losing Team): Go aggressive when desync detected
- **Resign Mode** (Winning Team): Return to outpost when desync detected

**Progress Tracking:**
- **Strongboxes Earned**: View current strongboxes earned
- **Consecutive Wins**: Track progress toward next strongbox (need 5 consecutive wins)
- **Progress Bar**: Visual progress toward 5 strongbox goal
- **Desync Indicator**: Shows when map IDs don't match between leaders

**Actions:**
- **Invite Party Members**: Manually trigger party member invites
- **Reset Stats**: Reset strongbox and win counters

### GUI Settings (Support Script)

- **Party Leader Email**: Select your party leader (displays character name with email)
- **Last Command**: Shows the most recent command received
- **Auto Combat Status**: Displays current auto combat state

## Troubleshooting

### Bots Don't Queue Together

- Ensure both leaders are in the same outpost
- Check that shared memory is working (other multibox features work)
- Verify both leaders show "ready" status in logs
- Make sure partner emails are configured correctly

### Desync Detected

- This is normal if teams get matched against different opponents
- Payback Mode (losing team) will equip Set 1, enable HeroAI, and go aggressive
- Resign Mode (winning team) will equip Set 2 and return to outpost
- If desync happens frequently, check network stability

### Party Members Not Invited

- Ensure party member emails are configured in Party Configuration tab
- Verify the accounts are online and in shared memory
- Check that character names are showing up in the dropdowns
- Ensure party members are in the same map/district
- Click "Invite Party Members" button manually if auto-invite fails

### Party Members Not Responding to Commands

- Verify **Messaging.py widget** is enabled on party member accounts
- Check that shared memory is working between accounts
- Look for error messages in the Messaging widget console
- Ensure equipment sets are bound to F1 and F2 keys

### Match Doesn't Start

- Codex Arena may have population requirements
- Try queueing during peak hours
- Check that you have the minimum party size (4 per team)

### Equipment Sets Don't Switch

- Verify equipment sets are configured in-game
- Check that F1 = Set 1 and F2 = Set 2 in keybinds
- Ensure Messaging.py widget is processing PressKey commands

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
