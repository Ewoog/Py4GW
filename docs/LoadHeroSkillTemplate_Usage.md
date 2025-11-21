# Loading Hero Skill Templates - Usage Guide

## Overview
The `LoadHeroSkillTemplate` function allows you to load a skill build (template code) onto a hero in your party.

## Important Note
The function expects a **Hero ID**, not a party position. Hero IDs are unique identifiers for each hero (e.g., Koss = 6, Norgu = 1, etc.).

## Usage Methods

### Method 1: Using Hero ID directly (with HeroType enum)
```python
from Py4GWCoreLib import SkillBar
from PyParty import HeroType

# Load a template on Koss
result = SkillBar.LoadHeroSkillTemplate(HeroType.Koss, "OQATEjpUjIACVAAAAAAAAAA")
if result:
    print("Template loaded successfully!")
else:
    print("Failed to load template")
```

### Method 2: Using Hero Name
```python
from Py4GWCoreLib import SkillBar

# Load a template on Koss by name
result = SkillBar.LoadHeroSkillTemplateByName("Koss", "OQATEjpUjIACVAAAAAAAAAA")
```

### Method 3: Getting Hero ID from Party Position
```python
from Py4GWCoreLib import Party, SkillBar

# Get the hero ID of the first hero in your party (position 0)
hero_id = Party.Heroes.GetHeroIDByPartyPosition(0)

# Load template on that hero
result = SkillBar.LoadHeroSkillTemplate(hero_id, "OQATEjpUjIACVAAAAAAAAAA")
```

### Method 4: Using in a loop for all heroes
```python
from Py4GWCoreLib import Party, SkillBar

# Get all heroes in party
heroes = Party.GetHeroes()

# Load templates on each hero
for hero in heroes:
    hero_id = hero.hero_id.GetID()
    hero_name = Party.Heroes.GetHeroNameById(hero_id)
    
    # Load different templates based on hero
    if hero_name == "Koss":
        SkillBar.LoadHeroSkillTemplate(hero_id, "OQATEjpUjIACVAAAAAAAAAA")
    elif hero_name == "Tahlkora":
        SkillBar.LoadHeroSkillTemplate(hero_id, "OQASEDqEC1vcNABWAAAA")
```

## Hero ID Reference
You can find hero IDs in the `PyParty.HeroType` enum:
- Norgu = 1
- Goren = 2  
- Tahlkora = 3
- Master Of Whispers = 4
- Acolyte Jin = 5
- Koss = 6
- Dunkoro = 7
- Acolyte Sousuke = 8
- Melonni = 9
- Zhed Shadowhoof = 10
- General Morgahn = 11
- Magrid The Sly = 12
- Zenmai = 13
- Olias = 14
- Razah = 15
- MOX = 16
- And more... (see PyParty.pyi for complete list)

## Common Mistakes

### ❌ Wrong: Using party position directly
```python
# This will try to load the template on hero with ID=1 (Norgu), not the first hero in party!
SkillBar.LoadHeroSkillTemplate(1, "OQATEjpUjIACVAAAAAAAAAA")
```

### ✅ Correct: Use HeroType enum or get the actual hero ID
```python
# Method A: Use enum
from PyParty import HeroType
SkillBar.LoadHeroSkillTemplate(HeroType.Koss, "OQATEjpUjIACVAAAAAAAAAA")

# Method B: Get ID from party position
hero_id = Party.Heroes.GetHeroIDByPartyPosition(0)  # First hero in party
SkillBar.LoadHeroSkillTemplate(hero_id, "OQATEjpUjIACVAAAAAAAAAA")

# Method C: Use the helper function with name
SkillBar.LoadHeroSkillTemplateByName("Koss", "OQATEjpUjIACVAAAAAAAAAA")
```

## Return Value
The function returns `True` if successful, `False` otherwise. Always check the return value:
```python
result = SkillBar.LoadHeroSkillTemplate(HeroType.Koss, "OQATEjpUjIACVAAAAAAAAAA")
if not result:
    print("Failed - ensure Koss is in your party and the template is valid")
```

## Troubleshooting
If the function returns `False`, check:
1. The hero is actually in your party
2. The template code is valid
3. The hero ID is correct (not confusing it with party position)
4. You have the skills unlocked for that template
