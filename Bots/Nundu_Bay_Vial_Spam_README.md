# Nundu Bay Vial of Purified Water Spam Bot

## Overview

This bot snippet is designed for the Nundu Bay mission in Guild Wars. It continuously targets a specific enemy and spams the skill "Vial of Purified Water" on that target as soon as it comes off cooldown, repeating the process until the target dies.

## Features

- **Simple Configuration**: Target enemies by name (e.g., "Margonite") or player number
- **Automatic Skill Detection**: Finds "Vial of Purified Water" on your skill bar automatically
- **Cooldown Management**: Uses the skill as soon as it's available (spam mode)
- **Auto Re-targeting**: Finds the next matching target when the current one dies
- **Informative Logging**: Provides clear console messages about what the bot is doing

## Prerequisites

1. **Py4GW Framework**: This bot requires the Py4GW framework to be installed and running
2. **Skill Required**: You must have "Vial of Purified Water" equipped on your skill bar
3. **Mission Access**: You need to be in or able to enter the Nundu Bay mission

## Setup Instructions

### Step 1: Equip the Skill

Make sure "Vial of Purified Water" is equipped on your skill bar before entering the mission.

### Step 2: Configure the Target

Open `Nundu_Bay_Vial_Spam.py` and edit the configuration section (around line 139):

**Option A: Target by Name (Recommended)**
```python
TARGET_NAME = "Margonite"  # Change to your target's name
TARGET_PLAYER_NUMBER = 0   # Leave as 0
```

**Option B: Target by Player Number (More Precise)**
```python
TARGET_NAME = ""           # Leave empty
TARGET_PLAYER_NUMBER = 12345  # Change to actual player number
```

### Step 3: Load the Script

1. Start Guild Wars and Py4GW
2. Load the script `Nundu_Bay_Vial_Spam.py` in Py4GW
3. Enter Nundu Bay mission

### Step 4: Start the Bot

1. In the Py4GW interface, find the "Nundu Bay Vial Spam" bot window
2. Click "Start" to begin the bot
3. The bot will automatically:
   - Find the "Vial of Purified Water" skill on your bar
   - Locate the target enemy
   - Spam the skill on the target until it dies
   - Repeat on the next matching target

## How It Works

1. **Initialization**: The bot searches for "Vial of Purified Water" on your skill bar
2. **Target Acquisition**: Scans enemy agents for the configured target (by name or player number)
3. **Skill Spam Loop**:
   - Changes target to the enemy
   - Checks if "Vial of Purified Water" is off cooldown
   - Uses the skill if ready
   - Waits 100ms and checks again (spam mode)
   - Continues until target dies
4. **Repeat**: Searches for the next matching target and repeats the process

## Configuration Options

### TARGET_NAME
- Set this to the name (or part of the name) of the enemy you want to target
- Case-insensitive partial matching (e.g., "Margonite" will match "Margonite Priest")
- Example: `TARGET_NAME = "Priest"`

### TARGET_PLAYER_NUMBER
- Set this if you need to target a specific enemy when multiple have the same name
- Use a recorder script to find the player number
- Example: `TARGET_PLAYER_NUMBER = 12345`

## Troubleshooting

### "Vial of Purified Water not found on skill bar!"
- Make sure you have equipped the skill before starting the bot
- Check that the skill is actually named "Vial of Purified Water" in game

### "Target not found. Waiting..."
- Verify the target name or player number is correct
- Make sure you're in the right area/mission where the enemy spawns
- Check that the enemy is alive and within range

### Bot doesn't use the skill
- Ensure the skill is off cooldown
- Check that you have enough energy to cast the skill
- Verify you're not knocked down or interrupted

## Tips

- **Energy Management**: Make sure you have enough energy regeneration to keep spamming the skill
- **Safety**: This bot doesn't include movement or survival features - use with caution
- **Multiple Targets**: If using TARGET_NAME, the bot will target any enemy matching that name
- **Precision**: Use TARGET_PLAYER_NUMBER if you need to target a specific enemy among many with the same name

## Based On

This bot is modeled after the structure of the Nightfall Leveler bot, using the same Botting framework for consistency and reliability.

## Support

For issues or questions:
1. Check the console log messages for detailed error information
2. Verify all configuration settings are correct
3. Ensure you meet all prerequisites

## License

This bot snippet is part of the Py4GW project. Please refer to the main project license for usage terms.
