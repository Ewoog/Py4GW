# Hero Skill Casting - Feature Summary

## Question
> Guild Wars allows the player to manually cast players on Heroes skill bars. Does Py4GW have this functionality or can it be implemented?

## Answer
**YES**, Py4GW **already has** full support for manually casting hero skills. This functionality is implemented and ready to use.

## Implementation Details

The hero skill casting feature is available through multiple APIs:

### 1. PySkillbar API (Low-level)
```python
import PySkillbar

skillbar = PySkillbar.Skillbar()
skillbar.GetContext()
result = skillbar.HeroUseSkill(target_agent_id, skill_number, hero_idx)
```

### 2. SkillBar API (High-level wrapper)
```python
from Py4GWCoreLib.Skillbar import SkillBar

SkillBar.HeroUseSkill(target_agent_id, skill_number, hero_number)
```

### 3. Party.Heroes API (Party-focused)
```python
from Py4GWCoreLib.Party import Party

hero_agent_id = Party.party_instance().GetHeroAgentID(hero_index - 1)
Party.Heroes.UseSkill(hero_agent_id, skill_slot, target_id)
```

## Feature Capabilities

The hero skill casting feature supports:

- ✅ **Manual Skill Triggering**: Cast any hero skill at any time
- ✅ **Target Selection**: Cast on specific targets or use current target
- ✅ **Multiple Heroes**: Control all 7 hero slots independently
- ✅ **Full Skillbar Access**: Access all 8 skills on each hero's skillbar
- ✅ **Real-time Control**: Override hero AI for precise timing
- ✅ **Skillbar Management**: Load and manage hero skill templates

## Documentation and Examples

### New Documentation
- **[HERO_SKILL_CASTING.md](HERO_SKILL_CASTING.md)** - Comprehensive guide with:
  - API reference for all three methods
  - Code examples for common use cases
  - Advanced usage patterns
  - Best practices and tips

### Demo Scripts
- **[DEMO_HeroSkillCasting.py](../DEMO/DEMO_HeroSkillCasting.py)** - Interactive demo showing:
  - All three casting methods
  - Real-time hero and skillbar display
  - Quick-cast buttons for each hero
  - Input validation and error handling

- **[DEMO_PySkillbar.py](../DEMO/DEMO_PySkillbar.py)** - Updated with hero casting section

- **[DEMO_PyParty.py](../DEMO/DEMO_PyParty.py)** - Existing party demo with hero skill usage

### Updated README
The main README now highlights hero management as a key feature.

## Technical Implementation

The functionality is implemented in:
- **PySkillbar module** (C++ native): `PySkillbar.Skillbar.HeroUseSkill()`
- **Py4GWCoreLib/Skillbar.py**: High-level wrapper `SkillBar.HeroUseSkill()`
- **Py4GWCoreLib/Party.py**: Party-focused wrapper `Party.Heroes.UseSkill()`

All methods ultimately call the native C++ implementation in the Py4GW.dll.

## Usage Examples

### Basic Example
```python
import PySkillbar

skillbar = PySkillbar.Skillbar()
skillbar.GetContext()

# Make hero 1 use skill slot 1 on current target
result = skillbar.HeroUseSkill(0, 1, 1)
```

### Advanced Example - Healing Combo
```python
import PySkillbar
from Py4GWCoreLib.Player import Player

skillbar = PySkillbar.Skillbar()
skillbar.GetContext()

# Get player agent ID
player_id = Player.GetAgentID()

# Hero 1 casts healing skill on player
skillbar.HeroUseSkill(player_id, 3, 1)
```

## Existing Usage in Codebase

This feature is already used in several places:
- **Widgets/HeroHelper.py**: Uses `SkillBar.HeroUseSkill()` for smart hero control
- **Bots/Nikon Scripts/Kabob_Farm.py**: Uses hero skills for farming automation
- **Bots/chahbek_village_zm.py**: Uses hero skills in mission automation
- **DEMO/DEMO_PyParty.py**: Demonstrates the feature

## Conclusion

The manual hero skill casting functionality **is fully implemented and working** in Py4GW. It has been part of the library and is actively used in various scripts and widgets. The new documentation and examples make this feature more accessible and easier to use for developers.

## References

- Source: `Py4GWCoreLib/Skillbar.py` (lines 308-318)
- Source: `Py4GWCoreLib/Party.py` (lines 500-509)
- Stub: `stubs/PySkillbar.pyi` (line 33)
- Stub: `stubs/PyParty.pyi` (line 142)
