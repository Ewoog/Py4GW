# Necessary Imports
import Py4GW        # Miscellaneous functions and classes
import PyImGui      # ImGui wrapper
import PyAgent      # Agent functions and classes
import PyPlayer     # Player functions and classes
import PyParty      # Party functions and classes
import PySkillbar   # Skillbar functions and classes
import traceback    # traceback to log stack traces
# End Necessary Imports

"""
DEMO: Manual Hero Skill Casting

This demo demonstrates how to manually control and cast hero skills in Guild Wars using Py4GW.
Guild Wars allows players to manually trigger hero skills, and this functionality is fully
supported in Py4GW through multiple APIs.

There are three main ways to use hero skills:
1. Using PySkillbar directly: PySkillbar.Skillbar().HeroUseSkill(target_agent_id, skill_number, hero_idx)
2. Using the SkillBar wrapper: SkillBar.HeroUseSkill(target_agent_id, skill_number, hero_number)
3. Using the Party.Heroes wrapper: Party.Heroes.UseSkill(hero_agent_id, slot, target_id)

This demo shows all three methods in action.
"""

module_name = "HeroSkillCasting_DEMO"

# Create instances
party_instance = PyParty.PyParty()
skillbar_instance = PySkillbar.Skillbar()

# Input variables for hero skill casting
hero_index_input = 1  # Hero index (1-7)
skill_slot_input = 1  # Skill slot (1-8)
target_agent_id_input = 0  # Target agent ID (0 for current target)

def draw_window():
    global module_name
    global party_instance, skillbar_instance
    global hero_index_input, skill_slot_input, target_agent_id_input

    # Refresh context
    party_instance.GetContext()
    skillbar_instance.GetContext()
    
    if PyImGui.begin(module_name):
        PyImGui.text("Manual Hero Skill Casting Demo")
        PyImGui.text("This demo shows how to manually cast hero skills.")
        PyImGui.separator()
        
        # Instructions
        if PyImGui.collapsing_header("Instructions", PyImGui.TreeNodeFlags.DefaultOpen):
            PyImGui.text("1. Make sure you have heroes in your party")
            PyImGui.text("2. Select a hero index (1-7)")
            PyImGui.text("3. Select a skill slot (1-8) from that hero's skillbar")
            PyImGui.text("4. Select a target (0 = current target, or specific agent ID)")
            PyImGui.text("5. Click one of the 'Cast Hero Skill' buttons")
            PyImGui.separator()
        
        # Input controls
        if PyImGui.collapsing_header("Casting Controls", PyImGui.TreeNodeFlags.DefaultOpen):
            # Hero index input (1-7)
            PyImGui.text("Hero Index (1-7):")
            hero_index_input = PyImGui.input_int("Hero Index", hero_index_input)
            if hero_index_input < 1:
                hero_index_input = 1
            elif hero_index_input > 7:
                hero_index_input = 7
            
            # Skill slot input (1-8)
            PyImGui.text("Skill Slot (1-8):")
            skill_slot_input = PyImGui.input_int("Skill Slot", skill_slot_input)
            if skill_slot_input < 1:
                skill_slot_input = 1
            elif skill_slot_input > 8:
                skill_slot_input = 8
            
            # Target agent ID input
            PyImGui.text("Target Agent ID (0 for current target):")
            target_agent_id_input = PyImGui.input_int("Target Agent ID", target_agent_id_input)
            
            PyImGui.separator()
            
            # Method 1: Using PySkillbar directly
            if PyImGui.button("Cast Hero Skill (PySkillbar)"):
                try:
                    result = skillbar_instance.HeroUseSkill(
                        target_agent_id_input, 
                        skill_slot_input, 
                        hero_index_input
                    )
                    Py4GW.Console.Log(module_name, f"Cast hero {hero_index_input} skill {skill_slot_input} using PySkillbar: {result}")
                except Exception as e:
                    Py4GW.Console.Log(module_name, f"Error casting skill: {str(e)}")
            
            PyImGui.same_line()
            PyImGui.text("Uses PySkillbar directly")
            
            # Method 2: Using Party.Heroes.UseSkill
            if PyImGui.button("Cast Hero Skill (Party.Heroes)"):
                try:
                    # Get hero agent ID from hero index
                    hero_agent_id = party_instance.GetHeroAgentID(hero_index_input - 1)  # Convert to 0-based
                    if hero_agent_id > 0:
                        party_instance.UseHeroSkill(hero_agent_id, skill_slot_input, target_agent_id_input)
                        Py4GW.Console.Log(module_name, f"Cast hero {hero_index_input} (agent {hero_agent_id}) skill {skill_slot_input} using PyParty")
                    else:
                        Py4GW.Console.Log(module_name, f"Hero {hero_index_input} not found in party")
                except Exception as e:
                    Py4GW.Console.Log(module_name, f"Error casting skill: {str(e)}")
            
            PyImGui.same_line()
            PyImGui.text("Uses PyParty.UseHeroSkill")
            
            PyImGui.separator()
        
        # Display current heroes in party
        if PyImGui.collapsing_header("Current Heroes"):
            if party_instance.party_hero_count > 0:
                for idx, hero in enumerate(party_instance.heroes):
                    if PyImGui.tree_node(f"Hero {idx + 1}: {hero.hero_id.GetName()}"):
                        PyImGui.text(f"Agent ID: {hero.agent_id}")
                        PyImGui.text(f"Hero ID: {hero.hero_id.GetID()}")
                        PyImGui.text(f"Primary: {hero.primary.GetName()}")
                        PyImGui.text(f"Secondary: {hero.secondary.GetName()}")
                        PyImGui.text(f"Level: {hero.level}")
                        
                        # Display hero skillbar
                        PyImGui.separator()
                        PyImGui.text("Hero Skillbar:")
                        hero_skills = skillbar_instance.GetHeroSkillbar(idx + 1)
                        for skill_idx, skill in enumerate(hero_skills):
                            if skill.id.id != 0:
                                PyImGui.text(f"  Slot {skill_idx + 1}: {skill.id.GetName()} (ID: {skill.id.id})")
                        
                        # Quick cast buttons for this hero
                        PyImGui.separator()
                        PyImGui.text("Quick Cast:")
                        for quick_slot in range(1, 9):
                            if PyImGui.button(f"Cast Slot {quick_slot}##hero{idx}"):
                                try:
                                    skillbar_instance.HeroUseSkill(
                                        target_agent_id_input, 
                                        quick_slot, 
                                        idx + 1
                                    )
                                    Py4GW.Console.Log(module_name, f"Cast {hero.hero_id.GetName()} skill slot {quick_slot}")
                                except Exception as e:
                                    Py4GW.Console.Log(module_name, f"Error: {str(e)}")
                            if quick_slot % 4 != 0:
                                PyImGui.same_line()
                        
                        PyImGui.tree_pop()
                    PyImGui.separator()
            else:
                PyImGui.text("No heroes in party")
            
        # Display notes and tips
        if PyImGui.collapsing_header("Notes and Tips"):
            PyImGui.text("Notes:")
            PyImGui.bullet_text("Hero index is 1-based (1-7)")
            PyImGui.bullet_text("Skill slot is 1-based (1-8)")
            PyImGui.bullet_text("Target agent ID of 0 uses current target")
            PyImGui.bullet_text("Skills will only cast if they are available (not recharging, have energy, etc.)")
            PyImGui.separator()
            PyImGui.text("Tips:")
            PyImGui.bullet_text("Use hero AI flags to position heroes optimally")
            PyImGui.bullet_text("Combine with skill templates for powerful hero builds")
            PyImGui.bullet_text("Monitor hero energy and skill recharge before casting")
            PyImGui.bullet_text("Use LoadHeroSkillTemplate() to quickly set up hero builds")

        PyImGui.end()


# main() must exist in every script and is the entry point for your script's execution.
def main():
    try:
        draw_window()

    # Handle specific exceptions to provide detailed error messages
    except ImportError as e:
        Py4GW.Console.Log(module_name, f"ImportError encountered: {str(e)}")
        traceback.print_exc()
    except ValueError as e:
        Py4GW.Console.Log(module_name, f"ValueError encountered: {str(e)}")
        traceback.print_exc()
    except Exception as e:
        Py4GW.Console.Log(module_name, f"Unexpected error encountered: {str(e)}")
        traceback.print_exc()
    finally:
        pass


# This ensures that main() is called when the script is executed directly.
if __name__ == "__main__":
    main()
