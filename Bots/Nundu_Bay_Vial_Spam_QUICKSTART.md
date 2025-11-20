# Quick Start Example: Nundu Bay Vial Spam Bot

## Example Configuration

Here's a quick example of how to configure the bot to target "Margonite Priests" in Nundu Bay:

### Step 1: Edit the script

Open `Nundu_Bay_Vial_Spam.py` and find line 139. Change this:

```python
TARGET_NAME = ""  # CHANGE THIS to the target's name
```

To this:

```python
TARGET_NAME = "Margonite"  # Targets any enemy with "Margonite" in their name
```

Or for more precision:

```python
TARGET_NAME = "Margonite Priest"  # Only targets Margonite Priests
```

### Step 2: Equip your skill

Make sure "Vial of Purified Water" is on your skill bar before entering Nundu Bay.

### Step 3: Run the bot

1. Enter Nundu Bay mission
2. Load the script in Py4GW
3. Click "Start" in the bot window

The bot will:
1. Find "Vial of Purified Water" on your skill bar
2. Search for enemies matching "Margonite" (or whatever you specified)
3. Target the first match found
4. Spam the skill on that target until it dies
5. Find the next matching enemy and repeat

## Common Targets in Nundu Bay

You might want to target:
- `"Margonite"` - Any Margonite enemy
- `"Priest"` - Margonite Priests specifically
- `"Anur"` - Anur enemies
- Or any other enemy name/partial name

## Advanced: Using Player Number

If you need to target a specific enemy (not just by name), you can use player number:

```python
TARGET_NAME = ""           # Leave empty when using player number
TARGET_PLAYER_NUMBER = 12345  # Use actual player number from recorder
```

To find the player number:
1. Use a recorder script (like SimpleEnemyModelIdRecorder.py)
2. Target the enemy in-game
3. The recorder will show the player number

## Console Output Example

When running, you'll see messages like:

```
[Vial Spam] Searching for target by name: 'Margonite'
[Vial Spam] Found target: Margonite Priest (Agent ID: 4567). Starting skill spam...
[Vial Spam] Used Vial of Purified Water on target
[Vial Spam] Used Vial of Purified Water on target
[Vial Spam] Used Vial of Purified Water on target
[Vial Spam] Target Margonite Priest is dead. Searching for next target...
[Vial Spam] Found target: Margonite Cleric (Agent ID: 4789). Starting skill spam...
```

## Tips

- **Start Simple**: Use just part of the enemy name (e.g., "Margonite") to target all enemies of that type
- **Energy**: Make sure you have energy regeneration to keep spamming
- **Position**: Position yourself where you can see/reach your targets
- **Safety**: This bot only handles skill spamming - you're responsible for movement and survival

## That's it!

The bot is now ready to spam Vial of Purified Water on your targets in Nundu Bay. Happy farming!
