# Manual Hero Skill Casting in Py4GW

## Overview

Guild Wars allows players to manually trigger hero skills, overriding the hero AI. This is useful for precise skill timing, combos, and strategic gameplay. Py4GW fully supports this functionality through multiple APIs.

## Features

- **Manual Skill Triggering**: Cast any hero skill at any time
- **Target Selection**: Cast skills on specific targets or use current target
- **Multiple Heroes**: Control all 7 hero slots independently
- **Full Skillbar Access**: Access all 8 skills on each hero's skillbar

## API Methods

### Method 1: PySkillbar Direct

The most direct way to use hero skills:

```python
import PySkillbar

skillbar = PySkillbar.Skillbar()
skillbar.GetContext()

# Cast hero skill
result = skillbar.HeroUseSkill(target_agent_id, skill_slot, hero_index)
```

**Parameters:**
- `target_agent_id` (int): The agent ID to target (0 = current target)
- `skill_slot` (int): Skill slot number (1-8)
- `hero_index` (int): Hero index (1-7)

**Returns:** bool - True if skill was successfully cast

### Method 2: SkillBar Wrapper

Using the high-level SkillBar API:

```python
from Py4GWCoreLib.Skillbar import SkillBar

# Cast hero skill
SkillBar.HeroUseSkill(target_agent_id, skill_number, hero_number)
```

**Parameters:**
- `target_agent_id` (int): The agent ID to target
- `skill_number` (int): Skill slot number (1-8)
- `hero_number` (int): Hero index (1-7)

### Method 3: Party.Heroes Wrapper

Using the Party API for hero management:

```python
from Py4GWCoreLib.Party import Party

# Get hero agent ID
hero_agent_id = Party.party_instance().GetHeroAgentID(hero_index - 1)

# Cast hero skill
Party.Heroes.UseSkill(hero_agent_id, skill_slot, target_id)
```

**Parameters:**
- `hero_agent_id` (int): The agent ID of the hero
- `skill_slot` (int): Skill slot number (1-8)
- `target_id` (int): The agent ID to target

## Complete Examples

### Basic Hero Skill Cast

```python
import PySkillbar

skillbar = PySkillbar.Skillbar()
skillbar.GetContext()

# Make hero 1 use skill slot 1 on current target
result = skillbar.HeroUseSkill(0, 1, 1)
if result:
    print("Skill cast successfully!")
```

### Cast Hero Skill on Specific Target

```python
import PySkillbar
from Py4GWCoreLib.Player import Player

skillbar = PySkillbar.Skillbar()
skillbar.GetContext()

# Get player's agent ID
player_id = Player.GetAgentID()

# Make hero 1 cast skill 3 on the player (e.g., a healing skill)
result = skillbar.HeroUseSkill(player_id, 3, 1)
```

### Cast Multiple Hero Skills in Sequence

```python
import PySkillbar
import time

skillbar = PySkillbar.Skillbar()

def cast_hero_combo(target_id):
    """Cast a combo using multiple hero skills"""
    skillbar.GetContext()
    
    # Hero 1 casts skill 1
    skillbar.HeroUseSkill(target_id, 1, 1)
    time.sleep(0.5)
    
    # Hero 2 casts skill 2
    skillbar.HeroUseSkill(target_id, 2, 2)
    time.sleep(0.5)
    
    # Hero 1 casts skill 3
    skillbar.HeroUseSkill(target_id, 3, 1)

# Execute combo on current target
cast_hero_combo(0)
```

### Using Hero Skills with Party Management

```python
from Py4GWCoreLib.Party import Party
from Py4GWCoreLib.Player import Player

# Get all heroes in party
heroes = Party.GetHeroes()

# Make each hero cast their first skill on the player
player_id = Player.GetAgentID()

for idx, hero in enumerate(heroes):
    Party.Heroes.UseSkill(hero.agent_id, 1, player_id)
```

### Checking Hero Skillbar Before Casting

```python
import PySkillbar

skillbar = PySkillbar.Skillbar()
skillbar.GetContext()

# Get hero 1's skillbar
hero_skills = skillbar.GetHeroSkillbar(1)

# Check if skill exists before casting
if len(hero_skills) > 0 and hero_skills[0].id.id != 0:
    skill_name = hero_skills[0].id.GetName()
    print(f"Casting {skill_name}")
    skillbar.HeroUseSkill(0, 1, 1)
else:
    print("No skill in slot 1")
```

## Important Notes

1. **Hero Index**: Hero indices are 1-based (1-7), not 0-based
2. **Skill Slots**: Skill slots are 1-based (1-8)
3. **Target Selection**: 
   - Use `0` for the current target
   - Use a specific agent ID to target that agent
4. **Skill Availability**: Skills will only cast if:
   - The hero has enough energy
   - The skill is not recharging
   - The skill is not disabled
   - The target is valid for the skill
5. **Hero AI**: Manual casting does not disable hero AI; heroes will continue to use skills automatically unless AI is disabled

## Advanced Usage

### Disable Hero AI for Manual Control

```python
from Py4GWCoreLib.Party import Party

# Set hero to Guard mode (less aggressive AI)
hero_agent_id = Party.party_instance().GetHeroAgentID(0)  # First hero
Party.Heroes.SetHeroBehavior(hero_agent_id, 1)  # 0=Fight, 1=Guard, 2=Avoid
```

### Load Hero Skill Template

```python
from Py4GWCoreLib.Skillbar import SkillBar

# Load a specific build for hero 1
template_code = "OQASEDqEC1vcNABWAAAA"
SkillBar.LoadHeroSkillTemplate(1, template_code)
```

### Get Hero Skillbar Information

```python
import PySkillbar

skillbar = PySkillbar.Skillbar()
skillbar.GetContext()

# Get all skills for hero 1
hero_skills = skillbar.GetHeroSkillbar(1)

for idx, skill in enumerate(hero_skills):
    if skill.id.id != 0:
        print(f"Slot {idx + 1}: {skill.id.GetName()}")
        print(f"  Recharge: {skill.recharge}")
        print(f"  Adrenaline: {skill.adrenaline_a}/{skill.adrenaline_b}")
```

## Common Use Cases

1. **Precision Healing**: Manually cast hero healing skills on injured allies
2. **Skill Combos**: Chain multiple hero skills for maximum effect
3. **Interrupt Control**: Use hero interrupt skills at precise moments
4. **Protection**: Cast protective skills on specific targets before damage
5. **Energy Management**: Control when heroes use high-energy skills
6. **PvP Control**: Precise timing of shutdown and support skills

## See Also

- [DEMO_HeroSkillCasting.py](../DEMO/DEMO_HeroSkillCasting.py) - Interactive demo
- [DEMO_PySkillbar.py](../DEMO/DEMO_PySkillbar.py) - Skillbar demo with hero casting
- [DEMO_PyParty.py](../DEMO/DEMO_PyParty.py) - Party management demo
- [Skillbar.py](../Py4GWCoreLib/Skillbar.py) - Skillbar API source
- [Party.py](../Py4GWCoreLib/Party.py) - Party API source
