"""
Nundu Bay Vial of Purified Water Spam Bot

This bot snippet continuously targets a specific enemy in Nundu Bay mission
and spams the skill "Vial of Purified Water" on that target as soon as it's
off cooldown until the target dies.

Usage:
1. Equip "Vial of Purified Water" skill on your skill bar
2. Enter Nundu Bay mission
3. Edit this script:
   - Set TARGET_NAME to the name of the enemy you want to target
     Example: TARGET_NAME = "Margonite Priest"
   OR
   - Set TARGET_PLAYER_NUMBER to the specific player number of the enemy
     (Use this if multiple enemies have the same name)
4. Load this script in Py4GW
5. Start the bot

The bot will:
- Find the target enemy by name or player number
- Continuously spam "Vial of Purified Water" on the target
- Use the skill as soon as it comes off cooldown
- Repeat on the next target with the same name when current target dies

Note: Similar to Nightfall Leveler bot structure but simplified for single skill spam.
"""

from __future__ import annotations
from typing import Generator, Any
from Py4GWCoreLib import (GLOBAL_CACHE, Routines, Py4GW, ConsoleLog, Botting)


# Initialize the bot
bot = Botting("Nundu Bay Vial Spam",
              upkeep_birthday_cupcake_restock=0,
              upkeep_honeycomb_restock=0,
              upkeep_war_supplies_restock=0,
              upkeep_auto_inventory_management_active=False,
              upkeep_auto_combat_active=False,
              upkeep_auto_loot_active=False)


def find_target_by_name(target_name: str) -> int:
    """
    Find an enemy agent by its name.
    
    Args:
        target_name: The name of the target enemy (case-insensitive, partial match)
        
    Returns:
        agent_id of the target, or 0 if not found
    """
    enemy_array = GLOBAL_CACHE.AgentArray.GetEnemyArray()
    
    for agent_id in enemy_array:
        agent_name = GLOBAL_CACHE.Agent.GetName(agent_id)
        if agent_name and target_name.lower() in agent_name.lower():
            if GLOBAL_CACHE.Agent.IsAlive(agent_id):
                return agent_id
    
    return 0


def find_target_by_player_number(player_number: int) -> int:
    """
    Find an enemy agent by its player number.
    
    Args:
        player_number: The player number of the target enemy
        
    Returns:
        agent_id of the target, or 0 if not found
    """
    enemy_array = GLOBAL_CACHE.AgentArray.GetEnemyArray()
    
    for agent_id in enemy_array:
        if GLOBAL_CACHE.Agent.GetPlayerNumber(agent_id) == player_number:
            if GLOBAL_CACHE.Agent.IsAlive(agent_id):
                return agent_id
    
    return 0


def get_vial_skill_slot() -> int:
    """
    Find the skill slot containing "Vial of Purified Water".
    
    Returns:
        Skill slot number (1-8), or 0 if not found
    """
    vial_skill_id = GLOBAL_CACHE.Skill.GetID("Vial_of_Purified_Water")
    
    for slot in range(1, 9):
        skill_id = GLOBAL_CACHE.SkillBar.GetSkillIDBySlot(slot)
        if skill_id == vial_skill_id:
            return slot
    
    return 0


def spam_vial_on_target(target_agent_id: int, vial_slot: int) -> Generator[Any, None, None]:
    """
    Continuously use Vial of Purified Water on the target.
    
    Args:
        target_agent_id: The agent ID of the target
        vial_slot: The skill slot number containing Vial of Purified Water
    """
    while GLOBAL_CACHE.Agent.IsAlive(target_agent_id):
        # Check if the skill is ready to use
        if GLOBAL_CACHE.SkillBar.IsSkillReady(vial_slot):
            # Change target to ensure we're targeting the right enemy
            yield from Routines.Yield.Agents.ChangeTarget(target_agent_id)
            yield from Routines.Yield.wait(100)
            
            # Use the skill
            GLOBAL_CACHE.SkillBar.UseSkill(vial_slot, target_agent_id)
            ConsoleLog("Vial Spam", f"Used Vial of Purified Water on target", 
                      Py4GW.Console.MessageType.Info, log=True)
            
            # Wait a bit for the skill to cast
            yield from Routines.Yield.wait(250)
        else:
            # Skill is on cooldown, wait a bit before checking again
            yield from Routines.Yield.wait(100)
        
        yield


def create_bot_routine(bot: Botting) -> None:
    """
    Main bot routine that finds the target and spams the skill.
    """
    bot.States.AddHeader("Nundu Bay Vial of Purified Water Spam")
    
    # Configuration: Set either the target name OR player number
    # Option 1: Find target by name (easier, recommended)
    TARGET_NAME = ""  # CHANGE THIS to the target's name (e.g., "Margonite" or "Priest")
    
    # Option 2: Find target by player number (more precise if multiple enemies have same name)
    TARGET_PLAYER_NUMBER = 0  # Leave as 0 if using TARGET_NAME
    
    # Validate configuration
    if not TARGET_NAME and TARGET_PLAYER_NUMBER == 0:
        bot.States.AddHeader("ERROR: No Target Specified!")
        ConsoleLog("Vial Spam", 
                  "Please edit the script and set either TARGET_NAME or TARGET_PLAYER_NUMBER",
                  Py4GW.Console.MessageType.Error, log=True)
        ConsoleLog("Vial Spam",
                  "Example: TARGET_NAME = 'Margonite' or TARGET_PLAYER_NUMBER = 12345",
                  Py4GW.Console.MessageType.Warning, log=True)
        return
    
    # Find the Vial of Purified Water skill slot
    def FindVialSlot() -> Generator[Any, None, int]:
        vial_slot = get_vial_skill_slot()
        
        if vial_slot == 0:
            ConsoleLog("Vial Spam", 
                      "ERROR: Vial of Purified Water not found on skill bar!",
                      Py4GW.Console.MessageType.Error, log=True)
            ConsoleLog("Vial Spam",
                      "Please equip the skill on your skill bar and restart the bot",
                      Py4GW.Console.MessageType.Warning, log=True)
            return 0
        
        ConsoleLog("Vial Spam", 
                  f"Found Vial of Purified Water in slot {vial_slot}",
                  Py4GW.Console.MessageType.Info, log=True)
        yield
        return vial_slot
    
    # Get the skill slot
    bot.States.AddCustomState(FindVialSlot, "Find Vial Skill Slot")
    vial_slot = get_vial_skill_slot()
    
    if vial_slot == 0:
        return
    
    # Main loop: Find target and spam skill
    def MainSpamLoop() -> Generator[Any, None, None]:
        if TARGET_NAME:
            ConsoleLog("Vial Spam", f"Searching for target by name: '{TARGET_NAME}'", 
                      Py4GW.Console.MessageType.Info, log=True)
        else:
            ConsoleLog("Vial Spam", f"Searching for target by player number: {TARGET_PLAYER_NUMBER}", 
                      Py4GW.Console.MessageType.Info, log=True)
        
        while True:
            # Find the target using the configured method
            if TARGET_NAME:
                target_id = find_target_by_name(TARGET_NAME)
            else:
                target_id = find_target_by_player_number(TARGET_PLAYER_NUMBER)
            
            if target_id == 0:
                if TARGET_NAME:
                    ConsoleLog("Vial Spam", 
                              f"Target '{TARGET_NAME}' not found. Waiting...",
                              Py4GW.Console.MessageType.Warning, log=True)
                else:
                    ConsoleLog("Vial Spam", 
                              f"Target with player number {TARGET_PLAYER_NUMBER} not found. Waiting...",
                              Py4GW.Console.MessageType.Warning, log=True)
                yield from Routines.Yield.wait(1000)
                continue
            
            # Log the target found
            target_name = GLOBAL_CACHE.Agent.GetName(target_id)
            ConsoleLog("Vial Spam", 
                      f"Found target: {target_name} (Agent ID: {target_id}). Starting skill spam...",
                      Py4GW.Console.MessageType.Info, log=True)
            
            # Spam the skill on the target until it dies
            yield from spam_vial_on_target(target_id, vial_slot)
            
            ConsoleLog("Vial Spam", 
                      f"Target {target_name} is dead. Searching for next target...",
                      Py4GW.Console.MessageType.Info, log=True)
            
            # Wait a bit before searching for the next target
            yield from Routines.Yield.wait(1000)
    
    bot.States.AddCustomState(MainSpamLoop, "Spam Vial on Target")


# Configure the bot
bot.SetMainRoutine(create_bot_routine)


def main():
    """Main update loop"""
    bot.Update()
    bot.UI.draw_window()


if __name__ == "__main__":
    main()
