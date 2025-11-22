import Py4GW
from Py4GWCoreLib import GLOBAL_CACHE, SpiritModelID, Timer, ThrottledTimer, Routines, Range, Allegiance, AgentArray
from Py4GWCoreLib import Weapon
from Py4GWCoreLib.enums import SPIRIT_BUFF_MAP
from .custom_skill import CustomSkillClass
from .targeting import TargetLowestAlly, TargetLowestAllyEnergy, TargetClusteredEnemy, TargetLowestAllyCaster, TargetLowestAllyMartial, TargetLowestAllyMelee, TargetLowestAllyRanged, GetAllAlliesArray
from .targeting import GetEnemyAttacking, GetEnemyCasting, GetEnemyCastingSpell, GetEnemyInjured, GetEnemyConditioned, GetEnemyHealthy
from .targeting import GetEnemyHexed, GetEnemyDegenHexed, GetEnemyEnchanted, GetEnemyMoving, GetEnemyKnockedDown
from .targeting import GetEnemyBleeding, GetEnemyPoisoned, GetEnemyCrippled
from .types import SkillNature, Skilltarget, SkillType
from .constants import MAX_NUM_PLAYERS
from typing import Optional


MAX_SKILLS = 8
custom_skill_data_handler = CustomSkillClass()

#region CombatClass
class CombatClass:
    global MAX_SKILLS, custom_skill_data_handler

    class SkillData:
        def __init__(self, slot):
            self.skill_id = GLOBAL_CACHE.SkillBar.GetSkillIDBySlot(slot)  # slot is 1 based
            self.skillbar_data = GLOBAL_CACHE.SkillBar.GetSkillData(slot)  # Fetch additional data from the skill bar
            self.custom_skill_data = custom_skill_data_handler.get_skill(self.skill_id)  # Retrieve custom skill data

    def __init__(self):
        import HeroAI.shared_memory_manager as shared_memory_manager
        """
        Initializes the CombatClass with an empty skill set and order.
        """
        self.skills = []
        self.skill_order = [0] * MAX_SKILLS
        self.skill_pointer = 0
        self.in_casting_routine = False
        self.aftercast = 0
        self.aftercast_timer = Timer()
        self.aftercast_timer.Start()
        self.ping_handler = Py4GW.PingHandler()
        self.oldCalledTarget = 0
        self.shared_memory_handler = shared_memory_manager.SharedMemoryManager()
        
        # Track follow-up skills for Arcane Echo and Auspicious Incantation
        self.pending_followup_skill_slot = -1  # -1 means no follow-up pending
        self.followup_skill_timer = Timer()
        
        self.in_aggro = False
        self.is_targeting_enabled = False
        self.is_combat_enabled = False
        self.is_skill_enabled = []
        self.fast_casting_exists = False
        self.fast_casting_level = 0
        self.expertise_exists = False
        self.expertise_level = 0
        
        self.nearest_enemy = Routines.Agents.GetNearestEnemy(self.get_combat_distance())
        self.lowest_ally = TargetLowestAlly()
        self.lowest_ally_energy = TargetLowestAllyEnergy()
        self.nearest_npc = Routines.Agents.GetNearestNPC(Range.Spellcast.value)
        self.nearest_spirit = Routines.Agents.GetNearestSpirit(Range.Spellcast.value)
        self.lowest_minion = Routines.Agents.GetLowestMinion(Range.Spellcast.value)
        self.nearest_corpse = Routines.Agents.GetNearestCorpse(Range.Spellcast.value)
        
        self.energy_drain = GLOBAL_CACHE.Skill.GetID("Energy_Drain") 
        self.energy_tap = GLOBAL_CACHE.Skill.GetID("Energy_Tap")
        self.ether_lord = GLOBAL_CACHE.Skill.GetID("Ether_Lord")
        self.essence_strike = GLOBAL_CACHE.Skill.GetID("Essence_Strike")
        self.glowing_signet = GLOBAL_CACHE.Skill.GetID("Glowing_Signet")
        self.clamor_of_souls = GLOBAL_CACHE.Skill.GetID("Clamor_of_Souls")
        self.waste_not_want_not = GLOBAL_CACHE.Skill.GetID("Waste_Not_Want_Not")
        self.mend_body_and_soul = GLOBAL_CACHE.Skill.GetID("Mend_Body_and_Soul")
        self.grenths_balance = GLOBAL_CACHE.Skill.GetID("Grenths_Balance")
        self.deaths_retreat = GLOBAL_CACHE.Skill.GetID("Deaths_Retreat")
        self.plague_sending = GLOBAL_CACHE.Skill.GetID("Plague_Sending")
        self.plague_signet = GLOBAL_CACHE.Skill.GetID("Plague_Signet")
        self.plague_touch = GLOBAL_CACHE.Skill.GetID("Plague_Touch")
        self.golden_fang_strike = GLOBAL_CACHE.Skill.GetID("Golden_Fang_Strike")
        self.golden_fox_strike = GLOBAL_CACHE.Skill.GetID("Golden_Fox_Strike")
        self.golden_lotus_strike = GLOBAL_CACHE.Skill.GetID("Golden_Lotus_Strike")
        self.golden_phoenix_strike = GLOBAL_CACHE.Skill.GetID("Golden_Phoenix_Strike")
        self.golden_skull_strike = GLOBAL_CACHE.Skill.GetID("Golden_Skull_Strike")
        self.brutal_weapon = GLOBAL_CACHE.Skill.GetID("Brutal_Weapon")
        self.signet_of_removal = GLOBAL_CACHE.Skill.GetID("Signet_of_Removal")
        self.dwaynas_kiss = GLOBAL_CACHE.Skill.GetID("Dwaynas_Kiss")
        self.unnatural_signet = GLOBAL_CACHE.Skill.GetID("Unnatural_Signet")
        self.toxic_chill = GLOBAL_CACHE.Skill.GetID("Toxic_Chill")
        self.discord = GLOBAL_CACHE.Skill.GetID("Discord")
        self.empathic_removal = GLOBAL_CACHE.Skill.GetID("Empathic_Removal")
        self.iron_palm = GLOBAL_CACHE.Skill.GetID("Iron_Palm")
        self.melandrus_resilience = GLOBAL_CACHE.Skill.GetID("Melandrus_Resilience")
        self.necrosis = GLOBAL_CACHE.Skill.GetID("Necrosis")
        self.peace_and_harmony = GLOBAL_CACHE.Skill.GetID("Peace_and_Harmony")
        self.purge_signet = GLOBAL_CACHE.Skill.GetID("Purge_Signet")
        self.resilient_weapon = GLOBAL_CACHE.Skill.GetID("Resilient_Weapon")
        self.gaze_from_beyond = GLOBAL_CACHE.Skill.GetID("Gaze_from_Beyond")
        self.spirit_burn = GLOBAL_CACHE.Skill.GetID("Spirit_Burn")
        self.signet_of_ghostly_might = GLOBAL_CACHE.Skill.GetID("Signet_of_Ghostly_Might")
        self.burning = GLOBAL_CACHE.Skill.GetID("Burning")
        self.blind = GLOBAL_CACHE.Skill.GetID("Blind")
        self.cracked_armor = GLOBAL_CACHE.Skill.GetID("Cracked_Armor")
        self.crippled = GLOBAL_CACHE.Skill.GetID("Crippled")
        self.dazed = GLOBAL_CACHE.Skill.GetID("Dazed")
        self.deep_wound = GLOBAL_CACHE.Skill.GetID("Deep_Wound")
        self.disease = GLOBAL_CACHE.Skill.GetID("Disease")
        self.poison = GLOBAL_CACHE.Skill.GetID("Poison")
        self.weakness = GLOBAL_CACHE.Skill.GetID("Weakness")
        self.comfort_animal = GLOBAL_CACHE.Skill.GetID("Comfort_Animal")
        self.heal_as_one = GLOBAL_CACHE.Skill.GetID("Heal_as_One")
        self.heroic_refrain = GLOBAL_CACHE.Skill.GetID("Heroic_Refrain")
        self.natures_blessing = GLOBAL_CACHE.Skill.GetID("Natures_Blessing")
        self.relentless_assault = GLOBAL_CACHE.Skill.GetID("Relentless_Assault")
        self.arcane_mimicry = GLOBAL_CACHE.Skill.GetID("Arcane_Mimicry")
        self.arcane_echo = GLOBAL_CACHE.Skill.GetID("Arcane_Echo")
        self.auspicious_incantation = GLOBAL_CACHE.Skill.GetID("Auspicious_Incantation")
        #junundu
        self.junundu_wail = GLOBAL_CACHE.Skill.GetID("Junundu_Wail")
        self.unknown_junundu_ability = GLOBAL_CACHE.Skill.GetID("Unknown_Junundu_Ability")
        self.leave_junundu = GLOBAL_CACHE.Skill.GetID("Leave_Junundu")
        self.junundu_tunnel = GLOBAL_CACHE.Skill.GetID("Junundu_Tunnel")
        
    def Update(self, cached_data):
        self.in_aggro = cached_data.in_aggro
        self.is_targeting_enabled = cached_data.is_targeting_enabled
        self.is_combat_enabled = cached_data.is_combat_enabled
        self.is_skill_enabled = cached_data.is_skill_enabled
        self.fast_casting_exists = cached_data.fast_casting_exists
        self.fast_casting_level = cached_data.fast_casting_level
        self.expertise_exists = cached_data.expertise_exists
        self.expertise_level = cached_data.expertise_level
        

    def PrioritizeSkills(self):
        """
        Create a priority-based skill execution order.
        """
        #initialize skillbar
        original_skills = []
        for i in range(MAX_SKILLS):
            original_skills.append(self.SkillData(i+1))

        # Initialize the pointer and tracking list
        ptr = 0
        ptr_chk = [False] * MAX_SKILLS
        ordered_skills = []
        
        priorities = [
            SkillNature.CustomA,
            SkillNature.Interrupt,
            SkillNature.CustomB,
            SkillNature.Enchantment_Removal,
            SkillNature.CustomC,
            SkillNature.Healing,
            SkillNature.CustomD,
            SkillNature.Resurrection,
            SkillNature.CustomE,
            SkillNature.Hex_Removal,
            SkillNature.CustomF,
            SkillNature.Condi_Cleanse,
            SkillNature.CustomG,
            SkillNature.SelfTargeted,
            SkillNature.CustomH,
            SkillNature.EnergyBuff,
            SkillNature.CustomI,
            SkillNature.Buff,
            SkillNature.CustomJ,
            SkillNature.OffensiveA,
            SkillNature.CustomK,
            SkillNature.OffensiveB,
            SkillNature.CustomL,
            SkillNature.OffensiveC,
            SkillNature.CustomM,
            SkillNature.Offensive,
            SkillNature.CustomN,
        ]

        for priority in priorities:
            #for i in range(ptr,MAX_SKILLS):
            for i in range(MAX_SKILLS):
                skill = original_skills[i]
                if not ptr_chk[i] and skill.custom_skill_data.Nature == priority.value:
                    self.skill_order[ptr] = i
                    ptr_chk[i] = True
                    ptr += 1
                    ordered_skills.append(skill)
        
        skill_types = [
            SkillType.Form,
            SkillType.Enchantment,
            SkillType.EchoRefrain,
            SkillType.WeaponSpell,
            SkillType.Chant,
            SkillType.Preparation,
            SkillType.Ritual,
            SkillType.Ward,
            SkillType.Well,
            SkillType.Stance,
            SkillType.Shout,
            SkillType.Glyph,
            SkillType.Signet,
            SkillType.Hex,
            SkillType.Trap,
            SkillType.Spell,
            SkillType.Skill,
            SkillType.PetAttack,
            SkillType.Attack,
        ]

        
        for skill_type in skill_types:
            #for i in range(ptr,MAX_SKILLS):
            for i in range(MAX_SKILLS):
                skill = original_skills[i]
                if not ptr_chk[i] and skill.custom_skill_data.SkillType == skill_type.value:
                    self.skill_order[ptr] = i
                    ptr_chk[i] = True
                    ptr += 1
                    ordered_skills.append(skill)

        combos = [3, 2, 1]  # Dual attack, off-hand attack, lead attack
        for combo in combos:
            #for i in range(ptr,MAX_SKILLS):
            for i in range(MAX_SKILLS):
                skill = original_skills[i]
                if not ptr_chk[i] and GLOBAL_CACHE.Skill.Data.GetCombo(skill.skill_id) == combo:
                    self.skill_order[ptr] = i
                    ptr_chk[i] = True
                    ptr += 1
                    ordered_skills.append(skill)
        
        # Fill in remaining unprioritized skills
        for i in range(MAX_SKILLS):
            if not ptr_chk[i]:
                self.skill_order[ptr] = i
                ptr_chk[i] = True
                ptr += 1
                ordered_skills.append(original_skills[i])
        
        self.skills = ordered_skills
        
        
    def GetSkills(self):
        """
        Retrieve the prioritized skill set.
        """
        return self.skills
        

    def GetOrderedSkill(self, index:int)-> Optional[SkillData]:
        """
        Retrieve the skill at the given index in the prioritized order.
        """
        if 0 <= index < MAX_SKILLS:
            return self.skills[index]
        return None  # Return None if the index is out of bounds

    def AdvanceSkillPointer(self):
        self.skill_pointer += 1
        if self.skill_pointer >= MAX_SKILLS:
            self.skill_pointer = 0
            
    def ResetSkillPointer(self):
        self.skill_pointer = 0
        
    def SetSkillPointer(self, pointer):
        if 0 <= pointer < MAX_SKILLS:
            self.skill_pointer = pointer
        else:
            self.skill_pointer = 0
            
    def GetSkillPointer(self):
        return self.skill_pointer
            
    def GetEnergyValues(self,agent_id):
        for i in range(MAX_NUM_PLAYERS):
            player_data = self.shared_memory_handler.get_player(i)
            if player_data and player_data["IsActive"] and player_data["PlayerID"] == agent_id:
                return player_data["Energy"]
        return 1.0 #default return full energy to prevent issues

    def IsSkillReady(self, slot):
        original_index = self.skill_order[slot] 
        
        if self.skills[slot].skill_id == 0:
            return False

        if self.skills[slot].skillbar_data.recharge != 0:
            return False
        
        return self.is_skill_enabled[original_index]
        
    def InCastingRoutine(self):
        if self.aftercast_timer.HasElapsed(self.aftercast):
            self.in_casting_routine = False
            self.aftercast_timer.Reset()

        return self.in_casting_routine
 
    def GetPartyTargetID(self):
        if not GLOBAL_CACHE.Party.IsPartyLoaded():
            return 0

        players = GLOBAL_CACHE.Party.GetPlayers()
        target = players[0].called_target_id

        if GLOBAL_CACHE.Agent.IsValid(target):
            return target  
        
        return 0 

    def SafeChangeTarget(self, target_id):
        if GLOBAL_CACHE.Agent.IsValid(target_id):
            GLOBAL_CACHE.Player.ChangeTarget(target_id)
            
    def SafeInteract(self, target_id):
        if GLOBAL_CACHE.Agent.IsValid(target_id):
            GLOBAL_CACHE.Player.ChangeTarget(target_id)
            GLOBAL_CACHE.Player.Interact(target_id, False)


    def GetPartyTarget(self):
        party_target = self.GetPartyTargetID()
        if self.is_targeting_enabled and party_target != 0:
            current_target = GLOBAL_CACHE.Player.GetTargetID()
            if current_target != party_target:
                if GLOBAL_CACHE.Agent.IsLiving(party_target):
                    allegiance_value, _ = GLOBAL_CACHE.Agent.GetAllegiance(party_target)
                    # Only target if it's an enemy (allegiance 3)
                    # Don't target: Ally (1), Neutral (2), SpiritPet (4), Minion (5), or NpcMinipet (6)
                    if allegiance_value == Allegiance.Enemy.value and self.is_combat_enabled:
                        self.SafeChangeTarget(party_target)
                        return party_target
        return 0

    def get_combat_distance(self):
        return Range.Spellcast.value if self.in_aggro else Range.Earshot.value

    def _resolve_party_slot_to_agent_id(self, party_slot: int) -> int:
        """Resolve a party slot (0-7) to the current agent ID."""
        if party_slot < 0 or party_slot > 7:
            return 0
        try:
            # Get all party members (players + heroes)
            party_members = []
            
            # Add player characters first
            players = GLOBAL_CACHE.Party.GetPlayers()
            for player in players:
                agent_id = GLOBAL_CACHE.Party.Players.GetAgentIDByLoginNumber(player.login_number)
                if agent_id > 0:
                    party_members.append(agent_id)
            
            # Add heroes
            heroes = GLOBAL_CACHE.Party.GetHeroes()
            for hero in heroes:
                if hero.agent_id > 0:
                    party_members.append(hero.agent_id)
            
            # Return agent ID at the specified slot
            if 0 <= party_slot < len(party_members):
                return party_members[party_slot]
        except Exception:
            pass
        return 0

    def GetAppropiateTarget(self, slot):
        v_target = 0

        if not self.is_targeting_enabled:
            return GLOBAL_CACHE.Player.GetTargetID()

        targeting_strict = self.skills[slot].custom_skill_data.Conditions.TargetingStrict
        target_allegiance = self.skills[slot].custom_skill_data.TargetAllegiance
        
        
        nearest_enemy = Routines.Agents.GetNearestEnemy(self.get_combat_distance())
        lowest_ally = TargetLowestAlly(filter_skill_id=self.skills[slot].skill_id)

        if self.skills[slot].skill_id == self.heroic_refrain:
            if not self.HasEffect(GLOBAL_CACHE.Player.GetAgentID(), self.heroic_refrain):
                return GLOBAL_CACHE.Player.GetAgentID()

        # Special handling for Arcane Mimicry - target specific ally based on party slot
        if self.skills[slot].skill_id == self.arcane_mimicry:
            from HeroAI.settings import Settings
            settings = Settings()
            # Use the configured target agent ID if available
            if settings.ArcaneMimicryTargetAgentID > 0:
                # Verify the target is still valid (alive, ally, and in party)
                target_id = settings.ArcaneMimicryTargetAgentID
                if GLOBAL_CACHE.Agent.IsLiving(target_id):
                    # Additional validation: ensure target is actually an ally in our party
                    allegiance_value, _ = GLOBAL_CACHE.Agent.GetAllegiance(target_id)
                    if allegiance_value == Allegiance.Ally.value:
                        return target_id
            # If no valid target configured, fall through to default OtherAlly targeting
        
        # Special handling for buff skills - use buff targeting configuration
        buff_skill_names = {
            GLOBAL_CACHE.Skill.GetID("Dark_Aura"): 'Dark_Aura',
            GLOBAL_CACHE.Skill.GetID("Great_Dwarf_Weapon"): 'Great_Dwarf_Weapon',
            GLOBAL_CACHE.Skill.GetID("Strength_of_Honor"): 'Strength_of_Honor',
            GLOBAL_CACHE.Skill.GetID("Spell_Breaker"): 'Spell_Breaker'
        }
        
        if self.skills[slot].skill_id in buff_skill_names:
            from HeroAI.settings import Settings
            from Py4GWCoreLib.enums_src.GameData_enums import Profession
            settings = Settings()
            settings.ensure_initialized()
            
            skill_name = buff_skill_names[self.skills[slot].skill_id]
            config = settings.BuffTargetingConfig.get(skill_name, {})
            
            if config:
                mode = config.get('mode', 'profession')
                
                if mode == 'player':
                    # Player-based targeting - find lowest health ally that's in the player list
                    players_set = config.get('players', set())
                    
                    # Debug logging
                    from Py4GWCoreLib.py4gwcorelib_src.Console import ConsoleLog
                    ConsoleLog("HeroAI", f"Buff targeting for {skill_name}: mode={mode}, players_set={players_set}")
                    
                    if not players_set:
                        # No players selected - don't cast the buff
                        ConsoleLog("HeroAI", f"No players selected for {skill_name}, returning 0")
                        return 0
                    
                    # Get all party members
                    party_members = []
                    
                    # Add current player (self)
                    my_agent_id = GLOBAL_CACHE.Player.GetAgentID()
                    my_name = GLOBAL_CACHE.Player.GetName()
                    ConsoleLog("HeroAI", f"Checking self: {my_name} in {players_set}? {my_name in players_set}")
                    if my_name in players_set and GLOBAL_CACHE.Agent.IsLiving(my_agent_id):
                        has_effect = self.HasEffect(my_agent_id, self.skills[slot].skill_id)
                        ConsoleLog("HeroAI", f"Self ({my_name}) has effect? {has_effect}")
                        if not has_effect:
                            party_members.append(my_agent_id)
                            ConsoleLog("HeroAI", f"Added self ({my_name}) to party_members")
                        else:
                            ConsoleLog("HeroAI", f"Self ({my_name}) already has buff, skipping")
                    
                    # Add heroes
                    heroes = GLOBAL_CACHE.Party.GetHeroes()
                    for hero in heroes:
                        if hero.agent_id != 0 and GLOBAL_CACHE.Agent.IsLiving(hero.agent_id):
                            hero_name = hero.hero_id.GetName() if hasattr(hero, 'hero_id') else "Hero"
                            ConsoleLog("HeroAI", f"Checking hero: {hero_name} in {players_set}? {hero_name in players_set}")
                            if hero_name in players_set:
                                has_effect = self.HasEffect(hero.agent_id, self.skills[slot].skill_id)
                                ConsoleLog("HeroAI", f"Hero ({hero_name}) has effect? {has_effect}")
                                if not has_effect:
                                    party_members.append(hero.agent_id)
                                    ConsoleLog("HeroAI", f"Added hero ({hero_name}) to party_members")
                                else:
                                    ConsoleLog("HeroAI", f"Hero ({hero_name}) already has buff, skipping")
                    
                    # Add other players
                    players = GLOBAL_CACHE.Party.GetPlayers()
                    for player in players:
                        player_agent_id = GLOBAL_CACHE.Party.Players.GetAgentIDByLoginNumber(player.login_number)
                        # Skip self (already added above) and invalid agents
                        if player_agent_id == 0 or player_agent_id == my_agent_id:
                            continue
                        if GLOBAL_CACHE.Agent.IsLiving(player_agent_id):
                            player_name = GLOBAL_CACHE.Party.Players.GetPlayerNameByLoginNumber(player.login_number)
                            ConsoleLog("HeroAI", f"Checking player: {player_name} in {players_set}? {player_name in players_set}")
                            if player_name in players_set:
                                has_effect = self.HasEffect(player_agent_id, self.skills[slot].skill_id)
                                ConsoleLog("HeroAI", f"Player ({player_name}) has effect? {has_effect}")
                                if not has_effect:
                                    party_members.append(player_agent_id)
                                    ConsoleLog("HeroAI", f"Added player ({player_name}) to party_members")
                                else:
                                    ConsoleLog("HeroAI", f"Player ({player_name}) already has buff, skipping")
                    
                    # Return lowest health ally from the selected players
                    ConsoleLog("HeroAI", f"Total party_members for {skill_name}: {len(party_members)}")
                    if party_members:
                        lowest_health = 2.0  # Initialize to > 1.0 so any health value will be lower
                        lowest_agent = 0
                        for agent_id in party_members:
                            health = GLOBAL_CACHE.Agent.GetHealth(agent_id)
                            ConsoleLog("HeroAI", f"Agent {agent_id} health: {health}")
                            if health < lowest_health:
                                lowest_health = health
                                lowest_agent = agent_id
                        ConsoleLog("HeroAI", f"Returning target agent_id: {lowest_agent} with health {lowest_health}")
                        return lowest_agent
                    ConsoleLog("HeroAI", f"No valid party members found, returning 0")
                    return 0
                    
                else:  # profession mode
                    # Profession-based targeting - find lowest health ally of enabled profession
                    professions_dict = config.get('professions', {})
                    if not any(professions_dict.values()):
                        # No professions selected - don't cast the buff
                        return 0
                    
                    # Get all party members of enabled professions
                    party_members = []
                    
                    # Add heroes
                    heroes = GLOBAL_CACHE.Party.GetHeroes()
                    for hero in heroes:
                        if hero.agent_id != 0 and GLOBAL_CACHE.Agent.IsLiving(hero.agent_id):
                            prof_id, _ = GLOBAL_CACHE.Agent.GetProfessionIDs(hero.agent_id)  # Returns (primary, secondary)
                            if professions_dict.get(prof_id, False) and not self.HasEffect(hero.agent_id, self.skills[slot].skill_id):
                                party_members.append(hero.agent_id)
                    
                    # Add other players
                    players = GLOBAL_CACHE.Party.GetPlayers()
                    my_agent_id = GLOBAL_CACHE.Player.GetAgentID()
                    for player in players:
                        player_agent_id = GLOBAL_CACHE.Party.Players.GetAgentIDByLoginNumber(player.login_number)
                        if player_agent_id != 0 and GLOBAL_CACHE.Agent.IsLiving(player_agent_id):
                            prof_id, _ = GLOBAL_CACHE.Agent.GetProfessionIDs(player_agent_id)  # Returns (primary, secondary)
                            if professions_dict.get(prof_id, False) and not self.HasEffect(player_agent_id, self.skills[slot].skill_id):
                                party_members.append(player_agent_id)
                    
                    # Return lowest health ally from enabled professions
                    if party_members:
                        lowest_health = 2.0  # Initialize to > 1.0 so any health value will be lower
                        lowest_agent = 0
                        for agent_id in party_members:
                            health = GLOBAL_CACHE.Agent.GetHealth(agent_id)
                            if health < lowest_health:
                                lowest_health = health
                                lowest_agent = agent_id
                        return lowest_agent
                    return 0

        if target_allegiance == Skilltarget.Enemy:
            v_target = self.GetPartyTarget()
            if v_target == 0:
                v_target = nearest_enemy
        elif target_allegiance == Skilltarget.EnemyCaster:
            v_target = Routines.Agents.GetNearestEnemyCaster(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target =nearest_enemy
        elif target_allegiance == Skilltarget.EnemyMartial:
            v_target = Routines.Agents.GetNearestEnemyMartial(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target = nearest_enemy
        elif target_allegiance == Skilltarget.EnemyMartialMelee:
            v_target = Routines.Agents.GetNearestEnemyMelee(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target = nearest_enemy
        elif target_allegiance == Skilltarget.EnemyClustered:
            v_target = TargetClusteredEnemy(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target = nearest_enemy
        elif target_allegiance == Skilltarget.EnemyAttacking:
            v_target = GetEnemyAttacking(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target = nearest_enemy
        elif target_allegiance == Skilltarget.EnemyCasting:
            v_target = GetEnemyCasting(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target = nearest_enemy          
        elif target_allegiance == Skilltarget.EnemyCastingSpell:
            v_target = GetEnemyCastingSpell(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target = nearest_enemy
        elif target_allegiance == Skilltarget.EnemyInjured:
            v_target = GetEnemyInjured(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target = nearest_enemy
        elif target_allegiance == Skilltarget.EnemyConditioned:
            v_target = GetEnemyConditioned(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target = nearest_enemy
        elif target_allegiance == Skilltarget.EnemyBleeding:
            v_target = GetEnemyBleeding(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target = nearest_enemy
        elif target_allegiance == Skilltarget.EnemyPoisoned:
            v_target = GetEnemyPoisoned(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target = nearest_enemy
        elif target_allegiance == Skilltarget.EnemyCrippled:
            v_target = GetEnemyCrippled(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target = nearest_enemy
        elif target_allegiance == Skilltarget.EnemyHexed:
            v_target = GetEnemyHexed(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target = nearest_enemy
        elif target_allegiance == Skilltarget.EnemyDegenHexed:
            v_target = GetEnemyDegenHexed(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target = nearest_enemy
        elif target_allegiance == Skilltarget.EnemyEnchanted:
            v_target = GetEnemyEnchanted(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target = nearest_enemy
        elif target_allegiance == Skilltarget.EnemyMoving:
            v_target = GetEnemyMoving(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target = nearest_enemy
        elif target_allegiance == Skilltarget.EnemyKnockedDown:
            v_target = GetEnemyKnockedDown(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target = nearest_enemy           
        elif target_allegiance == Skilltarget.AllyMartialRanged:
            v_target = Routines.Agents.GetNearestEnemyRanged(self.get_combat_distance())
            if v_target == 0 and not targeting_strict:
                v_target = nearest_enemy
        elif target_allegiance == Skilltarget.Ally:
            v_target = lowest_ally
        elif target_allegiance == Skilltarget.AllyCaster:
            v_target = TargetLowestAllyCaster(filter_skill_id=self.skills[slot].skill_id)
            if v_target == 0 and not targeting_strict:
                v_target = lowest_ally
        elif target_allegiance == Skilltarget.AllyMartial:
            v_target = TargetLowestAllyMartial(filter_skill_id=self.skills[slot].skill_id)
            if v_target == 0 and not targeting_strict:
                v_target = lowest_ally
        elif target_allegiance == Skilltarget.AllyMartialMelee:
            v_target = TargetLowestAllyMelee(filter_skill_id=self.skills[slot].skill_id)
            if v_target == 0 and not targeting_strict:
                v_target = lowest_ally
        elif target_allegiance == Skilltarget.AllyMartialRanged:
            v_target = TargetLowestAllyRanged(filter_skill_id=self.skills[slot].skill_id)
            if v_target == 0 and not targeting_strict:
                v_target = lowest_ally
        elif target_allegiance == Skilltarget.OtherAlly:
            if self.skills[slot].custom_skill_data.Nature == SkillNature.EnergyBuff.value:
                v_target = TargetLowestAllyEnergy(other_ally=True, filter_skill_id=self.skills[slot].skill_id)
                #print("Energy Buff Target: ", RawAgentArray().get_name(v_target))
            else:
                v_target = TargetLowestAlly(other_ally=True, filter_skill_id=self.skills[slot].skill_id)
        elif target_allegiance == Skilltarget.Self:
            v_target = GLOBAL_CACHE.Player.GetAgentID()
        elif target_allegiance == Skilltarget.Pet:
            v_target = GLOBAL_CACHE.Party.Pets.GetPetID(GLOBAL_CACHE.Player.GetAgentID())
        elif target_allegiance == Skilltarget.DeadAlly:
            v_target = Routines.Agents.GetDeadAlly(Range.Spellcast.value)
        elif target_allegiance == Skilltarget.Spirit:
            v_target = Routines.Agents.GetNearestSpirit(Range.Spellcast.value)
        elif target_allegiance == Skilltarget.Minion:
            v_target = Routines.Agents.GetLowestMinion(Range.Spellcast.value)
        elif target_allegiance == Skilltarget.Corpse:
            v_target = Routines.Agents.GetNearestCorpse(Range.Spellcast.value)
        else:
            v_target = self.GetPartyTarget()
            if v_target == 0:
                v_target = nearest_enemy
        return v_target

    def IsPartyMember(self, agent_id):
        for i in range(MAX_NUM_PLAYERS):
            player_data = self.shared_memory_handler.get_player(i)
            if player_data and player_data["IsActive"] and player_data["PlayerID"] == agent_id:
                return True
            
        allegiance , _ = GLOBAL_CACHE.Agent.GetAllegiance(agent_id)
        if (allegiance == Allegiance.SpiritPet.value and 
            not GLOBAL_CACHE.Agent.IsSpawned(agent_id)):
            return True
        
        return False
        
    def HasEffect(self, agent_id, skill_id, exact_weapon_spell=False):

        result = False
        custom_skill_data = custom_skill_data_handler.get_skill(skill_id)
        shared_effects = getattr(custom_skill_data.Conditions, "SharedEffects", []) if custom_skill_data else []


        if self.IsPartyMember(agent_id):
            player_buffs = self.shared_memory_handler.get_agent_buffs(agent_id)
            for buff in player_buffs:                
                if buff == skill_id or buff in shared_effects:
                    result = True
        else:
            result = (
                GLOBAL_CACHE.Effects.BuffExists(agent_id, skill_id) 
                or GLOBAL_CACHE.Effects.EffectExists(agent_id, skill_id)
                or any(GLOBAL_CACHE.Effects.BuffExists(agent_id, shared_buff) or GLOBAL_CACHE.Effects.EffectExists(agent_id, shared_buff) for shared_buff in shared_effects))

        if not result and not exact_weapon_spell:
           skilltype, _ = GLOBAL_CACHE.Skill.GetType(skill_id)
           if skilltype == SkillType.WeaponSpell.value:
               result = GLOBAL_CACHE.Agent.IsWeaponSpelled(agent_id)

        return result


    def AreCastConditionsMet(self, slot, vTarget):
        number_of_features = 0
        feature_count = 0

        Conditions = self.skills[slot].custom_skill_data.Conditions

        """ Check if the skill is a resurrection skill and the target is dead """
        if self.skills[slot].custom_skill_data.Nature == SkillNature.Resurrection.value:
            return True if GLOBAL_CACHE.Agent.IsDead(vTarget) else False


        if self.skills[slot].custom_skill_data.Conditions.UniqueProperty:
            """ check all UniqueProperty skills """
            if (self.skills[slot].skill_id == self.energy_drain or 
                self.skills[slot].skill_id == self.energy_tap or
                self.skills[slot].skill_id == self.ether_lord 
                ):
                return self.GetEnergyValues(GLOBAL_CACHE.Player.GetAgentID()) < Conditions.LessEnergy
        
            if (self.skills[slot].skill_id == self.essence_strike):
                energy = self.GetEnergyValues(GLOBAL_CACHE.Player.GetAgentID()) < Conditions.LessEnergy
                return energy and (Routines.Agents.GetNearestSpirit(Range.Spellcast.value) != 0)

            if (self.skills[slot].skill_id == self.glowing_signet):
                energy= self.GetEnergyValues(GLOBAL_CACHE.Player.GetAgentID()) < Conditions.LessEnergy
                return energy and self.HasEffect(vTarget, self.burning)

            if (self.skills[slot].skill_id == self.clamor_of_souls):
                energy = self.GetEnergyValues(GLOBAL_CACHE.Player.GetAgentID()) < Conditions.LessEnergy
                weapon_type, _ = GLOBAL_CACHE.Agent.GetWeaponType(GLOBAL_CACHE.Player.GetAgentID())
                return energy and weapon_type == 0

            if (self.skills[slot].skill_id == self.waste_not_want_not):
                energy= self.GetEnergyValues(GLOBAL_CACHE.Player.GetAgentID()) < Conditions.LessEnergy
                return energy and not GLOBAL_CACHE.Agent.IsCasting(vTarget) and not GLOBAL_CACHE.Agent.IsAttacking(vTarget)

            if (self.skills[slot].skill_id == self.mend_body_and_soul):
                spirits_exist = Routines.Agents.GetNearestSpirit(Range.Earshot.value)
                life = GLOBAL_CACHE.Agent.GetHealth(GLOBAL_CACHE.Player.GetAgentID()) < Conditions.LessLife
                return life or (spirits_exist and GLOBAL_CACHE.Agent.IsConditioned(vTarget))

            if (self.skills[slot].skill_id == self.grenths_balance):
                life = GLOBAL_CACHE.Agent.GetHealth(GLOBAL_CACHE.Player.GetAgentID()) < Conditions.LessLife
                return life and GLOBAL_CACHE.Agent.GetHealth(GLOBAL_CACHE.Player.GetAgentID()) < GLOBAL_CACHE.Agent.GetHealth(vTarget)

            if (self.skills[slot].skill_id == self.deaths_retreat):
                return GLOBAL_CACHE.Agent.GetHealth(GLOBAL_CACHE.Player.GetAgentID()) < GLOBAL_CACHE.Agent.GetHealth(vTarget)

            if (self.skills[slot].skill_id == self.plague_sending or
                self.skills[slot].skill_id == self.plague_signet or
                self.skills[slot].skill_id == self.plague_touch
                ):
                return GLOBAL_CACHE.Agent.IsConditioned(GLOBAL_CACHE.Player.GetAgentID())

            if (self.skills[slot].skill_id == self.golden_fang_strike or
                self.skills[slot].skill_id == self.golden_fox_strike or
                self.skills[slot].skill_id == self.golden_lotus_strike or
                self.skills[slot].skill_id == self.golden_phoenix_strike or
                self.skills[slot].skill_id == self.golden_skull_strike
                ):
                return GLOBAL_CACHE.Agent.IsEnchanted(GLOBAL_CACHE.Player.GetAgentID())

            if (self.skills[slot].skill_id == self.brutal_weapon):
                return not GLOBAL_CACHE.Agent.IsEnchanted(GLOBAL_CACHE.Player.GetAgentID())

            if (self.skills[slot].skill_id == self.signet_of_removal):
                return not GLOBAL_CACHE.Agent.IsEnchanted(vTarget) and GLOBAL_CACHE.Agent.IsConditioned(vTarget)

            if (self.skills[slot].skill_id == self.dwaynas_kiss or
                self.skills[slot].skill_id == self.unnatural_signet or
                self.skills[slot].skill_id == self.toxic_chill
                ):
                return GLOBAL_CACHE.Agent.IsHexed(vTarget) or GLOBAL_CACHE.Agent.IsEnchanted(vTarget)

            if (self.skills[slot].skill_id == self.discord):
                return (GLOBAL_CACHE.Agent.IsHexed(vTarget) and GLOBAL_CACHE.Agent.IsConditioned(vTarget)) or (GLOBAL_CACHE.Agent.IsEnchanted(vTarget))

            if (self.skills[slot].skill_id == self.empathic_removal or
                self.skills[slot].skill_id == self.iron_palm or
                self.skills[slot].skill_id == self.melandrus_resilience or
                self.skills[slot].skill_id == self.necrosis or
                self.skills[slot].skill_id == self.peace_and_harmony or
                self.skills[slot].skill_id == self.purge_signet or
                self.skills[slot].skill_id == self.resilient_weapon
                ):
                return GLOBAL_CACHE.Agent.IsHexed(vTarget) or GLOBAL_CACHE.Agent.IsConditioned(vTarget)
            
            if (self.skills[slot].skill_id == self.gaze_from_beyond or
                self.skills[slot].skill_id == self.spirit_burn or
                self.skills[slot].skill_id == self.signet_of_ghostly_might
                ):
                return True if Routines.Agents.GetNearestSpirit(Range.Spellcast.value) != 0 else False
            
            if (self.skills[slot].skill_id == self.comfort_animal or
                self.skills[slot].skill_id == self.heal_as_one
                ):
                LessLife = GLOBAL_CACHE.Agent.GetHealth(vTarget) < Conditions.LessLife
                dead = GLOBAL_CACHE.Agent.IsDead(vTarget)
                return LessLife or dead
                
            if (self.skills[slot].skill_id == self.natures_blessing):
                player_life = GLOBAL_CACHE.Agent.GetHealth(GLOBAL_CACHE.Player.GetAgentID()) < Conditions.LessLife
                nearest_npc = Routines.Agents.GetNearestNPC(Range.Spirit.value)
                if nearest_npc == 0:
                    return player_life

                nearest_NPC_life = GLOBAL_CACHE.Agent.GetHealth(nearest_npc) < Conditions.LessLife
                return player_life or nearest_NPC_life
            
            if (self.skills[slot].skill_id == self.relentless_assault
                ):
                return GLOBAL_CACHE.Agent.IsHexed(GLOBAL_CACHE.Player.GetAgentID()) or GLOBAL_CACHE.Agent.IsConditioned(GLOBAL_CACHE.Player.GetAgentID())
            
            if (self.skills[slot].skill_id == self.junundu_wail):
                nearest_corpse = Routines.Agents.GetDeadAlly(Range.Earshot.value)
                if nearest_corpse != 0:
                    return True
                
                life = GLOBAL_CACHE.Agent.GetHealth(GLOBAL_CACHE.Player.GetAgentID()) < Conditions.LessLife
                nearest = Routines.Agents.GetNearestEnemy(Range.Earshot.value)
                if nearest == 0:
                    return life
                
                return False


            if (self.skills[slot].skill_id == self.junundu_tunnel):
                return Routines.Agents.GetNearestEnemy(Range.Earshot.value) == 0

            if ((self.skills[slot].skill_id == self.unknown_junundu_ability) or
                (self.skills[slot].skill_id == self.leave_junundu)
                ):
                return False


            return True  # if no unique property is configured, return True for all UniqueProperty
        

        feature_count += (1 if Conditions.IsAlive else 0)
        feature_count += (1 if Conditions.HasCondition else 0)
        feature_count += (1 if Conditions.HasBleeding else 0)
        feature_count += (1 if Conditions.HasBlindness else 0)
        feature_count += (1 if Conditions.HasBurning else 0)
        feature_count += (1 if Conditions.HasCrackedArmor else 0)
        feature_count += (1 if Conditions.HasCrippled else 0)
        feature_count += (1 if Conditions.HasDazed else 0)
        feature_count += (1 if Conditions.HasDeepWound else 0)
        feature_count += (1 if Conditions.HasDisease else 0)
        feature_count += (1 if Conditions.HasPoison else 0)
        feature_count += (1 if Conditions.HasWeakness else 0)
        feature_count += (1 if Conditions.HasWeaponSpell else 0)
        feature_count += (1 if Conditions.HasEnchantment else 0)
        feature_count += (1 if Conditions.HasDervishEnchantment else 0)
        feature_count += (1 if Conditions.HasHex else 0)
        feature_count += (1 if Conditions.HasChant else 0)
        feature_count += (1 if Conditions.IsCasting else 0)
        feature_count += (1 if Conditions.IsKnockedDown else 0)
        feature_count += (1 if Conditions.IsMoving else 0)
        feature_count += (1 if Conditions.IsAttacking else 0)
        feature_count += (1 if Conditions.IsHoldingItem else 0)
        feature_count += (1 if Conditions.LessLife > 0 else 0)
        feature_count += (1 if Conditions.MoreLife > 0 else 0)
        feature_count += (1 if Conditions.LessEnergy > 0 else 0)
        feature_count += (1 if Conditions.Overcast > 0 else 0)
        feature_count += (1 if Conditions.IsPartyWide else 0)
        feature_count += (1 if Conditions.RequiresSpiritInEarshot else 0)
        feature_count += (1 if Conditions.EnemiesInRange > 0 else 0)
        feature_count += (1 if Conditions.AlliesInRange > 0 else 0)
        feature_count += (1 if Conditions.SpiritsInRange > 0 else 0)
        feature_count += (1 if Conditions.MinionsInRange > 0 else 0)

        if Conditions.IsAlive:
            if GLOBAL_CACHE.Agent.IsAlive(vTarget):
                number_of_features += 1

        is_conditioned = GLOBAL_CACHE.Agent.IsConditioned(vTarget)
        is_bleeding = GLOBAL_CACHE.Agent.IsBleeding(vTarget)
        is_blind = self.HasEffect(vTarget, self.blind)
        is_burning = self.HasEffect(vTarget, self.burning)
        is_cracked_armor = self.HasEffect(vTarget, self.cracked_armor)
        is_crippled = GLOBAL_CACHE.Agent.IsCrippled(vTarget)
        is_dazed = self.HasEffect(vTarget, self.dazed)
        is_deep_wound = self.HasEffect(vTarget, self.deep_wound)
        is_disease = self.HasEffect(vTarget, self.disease)
        is_poison = GLOBAL_CACHE.Agent.IsPoisoned(vTarget)
        is_weakness = self.HasEffect(vTarget, self.weakness)
        
        if Conditions.HasCondition:
            if (is_conditioned or 
                is_bleeding or 
                is_blind or 
                is_burning or 
                is_cracked_armor or 
                is_crippled or 
                is_dazed or 
                is_deep_wound or 
                is_disease or 
                is_poison or 
                is_weakness):
                number_of_features += 1


        if Conditions.HasBleeding:
            if is_bleeding:
                number_of_features += 1

        if Conditions.HasBlindness:
            if is_blind:
                number_of_features += 1

        if Conditions.HasBurning:
            if is_burning:
                number_of_features += 1

        if Conditions.HasCrackedArmor:
            if is_cracked_armor:
                number_of_features += 1
          
        if Conditions.HasCrippled:
            if is_crippled:
                number_of_features += 1
                
        if Conditions.HasDazed:
            if is_dazed:
                number_of_features += 1
          
        if Conditions.HasDeepWound:
            if is_deep_wound:
                number_of_features += 1
                
        if Conditions.HasDisease:
            if is_disease:
                number_of_features += 1

        if Conditions.HasPoison:
            if is_poison:
                number_of_features += 1

        if Conditions.HasWeakness:
            if is_weakness:
                number_of_features += 1
         
        if Conditions.HasWeaponSpell:
            if GLOBAL_CACHE.Agent.IsWeaponSpelled(vTarget):
                if len(Conditions.WeaponSpellList) == 0:
                    number_of_features += 1
                else:
                    for skill_id in Conditions.WeaponSpellList:
                        if self.HasEffect(vTarget, skill_id, exact_weapon_spell=True):
                            number_of_features += 1
                            break

        if Conditions.HasEnchantment:
            if GLOBAL_CACHE.Agent.IsEnchanted(vTarget):
                if len(Conditions.EnchantmentList) == 0:
                    number_of_features += 1
                else:
                    for skill_id in Conditions.EnchantmentList:
                        if self.HasEffect(vTarget, skill_id):
                            number_of_features += 1
                            break

        if Conditions.HasDervishEnchantment:
            buff_list = self.shared_memory_handler.get_agent_buffs(GLOBAL_CACHE.Player.GetAgentID())
            for buff in buff_list:
                skill_type, _ = GLOBAL_CACHE.Skill.GetType(buff)
                if skill_type == SkillType.Enchantment.value:
                    _, profession = GLOBAL_CACHE.Skill.GetProfession(buff)
                    if profession == "Dervish":
                        number_of_features += 1
                        break

        if Conditions.HasHex:
            if GLOBAL_CACHE.Agent.IsHexed(vTarget):
                if len(Conditions.HexList) == 0:
                    number_of_features += 1
                else:
                    for skill_id in Conditions.HexList:
                        if self.HasEffect(vTarget, skill_id):
                            number_of_features += 1
                            break

        if Conditions.HasChant:
            if self.IsPartyMember(vTarget):
                buff_list = self.shared_memory_handler.get_agent_buffs(vTarget)
                for buff in buff_list:
                    skill_type, _ = GLOBAL_CACHE.Skill.GetType(buff)
                    if skill_type == SkillType.Chant.value:
                        if len(Conditions.ChantList) == 0:
                            number_of_features += 1
                        else:
                            if buff in Conditions.ChantList:
                                number_of_features += 1
                                break
                                
        if Conditions.IsCasting:
            if GLOBAL_CACHE.Agent.IsCasting(vTarget):
                casting_skill_id = GLOBAL_CACHE.Agent.GetCastingSkill(vTarget)
                if GLOBAL_CACHE.Skill.Data.GetActivation(casting_skill_id) >= 0.250:
                    if len(Conditions.CastingSkillList) == 0:
                        number_of_features += 1
                    else:
                        if casting_skill_id in Conditions.CastingSkillList:
                            number_of_features += 1

        if Conditions.IsKnockedDown:
            if GLOBAL_CACHE.Agent.IsKnockedDown(vTarget):
                number_of_features += 1
                            
        if Conditions.IsMoving:
            if GLOBAL_CACHE.Agent.IsMoving(vTarget):
                number_of_features += 1
        
        if Conditions.IsAttacking:
            if GLOBAL_CACHE.Agent.IsAttacking(vTarget):
                number_of_features += 1

        if Conditions.IsHoldingItem:
            weapon_type, _ = GLOBAL_CACHE.Agent.GetWeaponType(vTarget)
            if weapon_type == 0:
                number_of_features += 1

        if Conditions.LessLife != 0:
            if GLOBAL_CACHE.Agent.GetHealth(vTarget) < Conditions.LessLife:
                number_of_features += 1

        if Conditions.MoreLife != 0:
            if GLOBAL_CACHE.Agent.GetHealth(vTarget) > Conditions.MoreLife:
                number_of_features += 1
        
        if Conditions.LessEnergy != 0:
            if self.IsPartyMember(vTarget):
                for i in range(MAX_NUM_PLAYERS):
                    player_data = self.shared_memory_handler.get_player(i)
                    if player_data and player_data["IsActive"] and player_data["PlayerID"] == vTarget:
                        if player_data["Energy"] < Conditions.LessEnergy:
                            number_of_features += 1
            else:
                number_of_features += 1 #henchmen, allies, pets or something else thats not reporting energy

        if Conditions.Overcast != 0:
            if GLOBAL_CACHE.Player.GetAgentID() == vTarget:
                if GLOBAL_CACHE.Agent.GetOvercast(vTarget) < Conditions.Overcast:
                    number_of_features += 1
                    
        if Conditions.IsPartyWide:
            area = Range.SafeCompass.value if Conditions.PartyWideArea == 0 else Conditions.PartyWideArea
            less_life = Conditions.LessLife
            
            allies_array = GetAllAlliesArray(area)
            total_group_life = 0.0
            for agent in allies_array:
                total_group_life += GLOBAL_CACHE.Agent.GetHealth(agent)
                
            total_group_life /= len(allies_array)
            
            if total_group_life < less_life:
                number_of_features += 1
                                    
        if Conditions.RequiresSpiritInEarshot:            
            distance = Range.Earshot.value
            spirit_array = GLOBAL_CACHE.AgentArray.GetSpiritPetArray()
            spirit_array = AgentArray.Filter.ByDistance(spirit_array, GLOBAL_CACHE.Player.GetXY(), distance)            
            spirit_array = AgentArray.Filter.ByCondition(spirit_array, lambda agent_id: GLOBAL_CACHE.Agent.IsAlive(agent_id))
            
            if(len(spirit_array) > 0):
                number_of_features += 1
                    
        if self.skills[slot].custom_skill_data.SkillType == SkillType.PetAttack.value:
            pet_id = GLOBAL_CACHE.Party.Pets.GetPetID(GLOBAL_CACHE.Player.GetAgentID())
            if GLOBAL_CACHE.Agent.IsDead(pet_id):
                return False
            
            pet_attack_list = [GLOBAL_CACHE.Skill.GetID("Bestial_Mauling"),
                               GLOBAL_CACHE.Skill.GetID("Bestial_Pounce"),
                               GLOBAL_CACHE.Skill.GetID("Brutal_Strike"),
                               GLOBAL_CACHE.Skill.GetID("Disrupting_Lunge"),
                               GLOBAL_CACHE.Skill.GetID("Enraged_Lunge"),
                               GLOBAL_CACHE.Skill.GetID("Feral_Lunge"),
                               GLOBAL_CACHE.Skill.GetID("Ferocious_Strike"),
                               GLOBAL_CACHE.Skill.GetID("Maiming_Strike"),
                               GLOBAL_CACHE.Skill.GetID("Melandrus_Assault"),
                               GLOBAL_CACHE.Skill.GetID("Poisonous_Bite"),
                               GLOBAL_CACHE.Skill.GetID("Pounce"),
                               GLOBAL_CACHE.Skill.GetID("Predators_Pounce"),
                               GLOBAL_CACHE.Skill.GetID("Savage_Pounce"),
                               GLOBAL_CACHE.Skill.GetID("Scavenger_Strike")
                               ]
            
            for skill_id in pet_attack_list:
                if self.skills[slot].skill_id == skill_id:
                    if self.HasEffect(pet_id,self.skills[slot].skill_id ):
                        return False
            
        if Conditions.EnemiesInRange != 0:
            player_pos = GLOBAL_CACHE.Player.GetXY()
            enemy_array = enemy_array = Routines.Agents.GetFilteredEnemyArray(player_pos[0], player_pos[1], Conditions.EnemiesInRangeArea)
            if len(enemy_array) >= Conditions.EnemiesInRange:
                number_of_features += 1
            else:
                number_of_features = 0
                
        if Conditions.AlliesInRange != 0:
            player_pos = GLOBAL_CACHE.Player.GetXY()
            ally_array = ally_array = Routines.Agents.GetFilteredAllyArray(player_pos[0], player_pos[1], Conditions.AlliesInRangeArea,other_ally=True)
            if len(ally_array) >= Conditions.AlliesInRange:
                number_of_features += 1
            else:
                number_of_features = 0
                
        if Conditions.SpiritsInRange != 0:
            player_pos = GLOBAL_CACHE.Player.GetXY()
            ally_array = ally_array = Routines.Agents.GetFilteredSpiritArray(player_pos[0], player_pos[1], Conditions.SpiritsInRangeArea)
            if len(ally_array) >= Conditions.SpiritsInRange:
                number_of_features += 1
            else:
                number_of_features = 0
                
        if Conditions.MinionsInRange != 0:
            player_pos = GLOBAL_CACHE.Player.GetXY()
            ally_array = ally_array = Routines.Agents.GetFilteredMinionArray(player_pos[0], player_pos[1], Conditions.MinionsInRangeArea)
            if len(ally_array) >= Conditions.MinionsInRange:
                number_of_features += 1
            else:
                number_of_features = 0
            

        #Py4GW.Console.Log("AreCastConditionsMet", f"feature count: {feature_count}, No of features {number_of_features}", Py4GW.Console.MessageType.Info)
        
        if feature_count == number_of_features:
            return True

        return False


    def SpiritBuffExists(self, skill_id):
        spirit_array = GLOBAL_CACHE.AgentArray.GetSpiritPetArray()
        distance = Range.Earshot.value
        spirit_array = AgentArray.Filter.ByDistance(spirit_array, GLOBAL_CACHE.Player.GetXY(), distance)
        spirit_array = AgentArray.Filter.ByCondition(spirit_array, lambda agent_id: GLOBAL_CACHE.Agent.IsAlive(agent_id))

        for spirit_id in spirit_array:
            model_value = GLOBAL_CACHE.Agent.GetPlayerNumber(spirit_id)

            # Check if model_value is valid for SpiritModelID Enum
            if model_value in SpiritModelID._value2member_map_:
                spirit_model_id = SpiritModelID(model_value)
                if SPIRIT_BUFF_MAP.get(spirit_model_id) == skill_id:
                    return True


        return False



    def IsReadyToCast(self, slot):
        # Check if the player is already casting
         # Validate target
        v_target = self.GetAppropiateTarget(slot)

        if v_target is None or v_target == 0:
            self.in_casting_routine = False
            return False, 0

        if GLOBAL_CACHE.Agent.IsCasting(GLOBAL_CACHE.Player.GetAgentID()):
            self.in_casting_routine = False
            return False, v_target
        #if GLOBAL_CACHE.Agent.GetCastingSkill(GLOBAL_CACHE.Player.GetAgentID()) != 0:
        #    self.in_casting_routine = False
        #    return False, v_target
        if GLOBAL_CACHE.SkillBar.GetCasting() != 0:
            self.in_casting_routine = False
            return False, v_target
        # Check if no skill is assigned to the slot
        if self.skills[slot].skill_id == 0:
            self.in_casting_routine = False
            return False, v_target
        # Check if the skill is recharging

        if not Routines.Checks.Skills.IsSkillIDReady(self.skills[slot].skill_id):
            self.in_casting_routine = False
            return False, v_target
        
        # Check if there is enough energy
        current_energy = self.GetEnergyValues(GLOBAL_CACHE.Player.GetAgentID()) * GLOBAL_CACHE.Agent.GetMaxEnergy(GLOBAL_CACHE.Player.GetAgentID())
        energy_cost = Routines.Checks.Skills.GetEnergyCostWithEffects(self.skills[slot].skill_id,GLOBAL_CACHE.Player.GetAgentID())
          
        if self.expertise_exists:
            energy_cost = Routines.Checks.Skills.apply_expertise_reduction(energy_cost, self.expertise_level, self.skills[slot].skill_id)
        
        if current_energy < energy_cost:
            self.in_casting_routine = False
            return False, v_target
        # Check if there is enough health
        current_hp = GLOBAL_CACHE.Agent.GetHealth(GLOBAL_CACHE.Player.GetAgentID())
        target_hp = self.skills[slot].custom_skill_data.Conditions.SacrificeHealth
        health_cost = GLOBAL_CACHE.Skill.Data.GetHealthCost(self.skills[slot].skill_id)
        if (current_hp < target_hp) and health_cost > 0:
            self.in_casting_routine = False
            return False, v_target
     
        # Check if there is enough adrenaline
        adrenaline_required = GLOBAL_CACHE.Skill.Data.GetAdrenaline(self.skills[slot].skill_id)
        if adrenaline_required > 0 and self.skills[slot].skillbar_data.adrenaline_a < adrenaline_required:
            self.in_casting_routine = False
            return False, v_target

        """
        # Check overcast conditions
        current_overcast = Agent.GetOvercast(Player.GetAgentID())
        overcast_target = self.skills[slot].custom_skill_data.Conditions.Overcast
        skill_overcast = Skill.Data.GetOvercast(self.skills[slot].skill_id)
        if (current_overcast >= overcast_target) and (skill_overcast > 0):
            self.in_casting_routine = False
            return False, 0
        """
                
        # Check combo conditions
        combo_type = GLOBAL_CACHE.Skill.Data.GetCombo(self.skills[slot].skill_id)
        dagger_status = GLOBAL_CACHE.Agent.GetDaggerStatus(v_target)
        if ((combo_type == 1 and dagger_status not in (0, 3)) or
            (combo_type == 2 and dagger_status != 1) or
            (combo_type == 3 and dagger_status != 2)):
            self.in_casting_routine = False
            return False, v_target
        
        # Check if the skill has the required conditions
        if not self.AreCastConditionsMet(slot, v_target):
            self.in_casting_routine = False
            return False, v_target
        
        if self.SpiritBuffExists(self.skills[slot].skill_id):
            self.in_casting_routine = False
            return False, v_target

        if self.HasEffect(v_target,self.skills[slot].skill_id):
            self.in_casting_routine = False
            return False, v_target
        
        return True, v_target

    def IsOOCSkill(self, slot):
        if self.skills[slot].custom_skill_data.Conditions.IsOutOfCombat:
            return True

        skill_type = self.skills[slot].custom_skill_data.SkillType
        skill_nature = self.skills[slot].custom_skill_data.Nature

        if(skill_type == SkillType.Form.value or
           skill_type == SkillType.Preparation.value or
           skill_nature == SkillNature.Healing.value or
           skill_nature == SkillNature.Hex_Removal.value or
           skill_nature == SkillNature.Condi_Cleanse.value or
           skill_nature == SkillNature.EnergyBuff.value or
           skill_nature == SkillNature.Resurrection.value
        ):
            return True

        return False

    def ChooseTarget(self, interact=True):       
        if not self.is_targeting_enabled:
            return False

        if not self.in_aggro:
            return False

            
        called_target = self.GetPartyTarget()
        #if GLOBAL_CACHE.Agent.IsAlive(called_target):
        if called_target != 0:
            self.SafeInteract(called_target)
            return True
            
        nearest = Routines.Agents.GetNearestEnemy(self.get_combat_distance())
        if nearest != 0:
            self.SafeInteract(nearest)
            return True
        
        
        
    def GetWeaponAttackAftercast(self):
        """
        Returns the attack speed of the current weapon.
        """
        weapon_type,_ = GLOBAL_CACHE.Agent.GetWeaponType(GLOBAL_CACHE.Player.GetAgentID())
        player = GLOBAL_CACHE.Agent.GetAgentByID(GLOBAL_CACHE.Player.GetAgentID())
        if player is None:
            return 0
        
        attack_speed = player.living_agent.weapon_attack_speed
        attack_speed_modifier = player.living_agent.attack_speed_modifier if player.living_agent.attack_speed_modifier != 0 else 1.0
        
        if attack_speed == 0:
            match weapon_type:
                case Weapon.Bow.value:
                    attack_speed = 2.475
                case Weapon.Axe.value:
                    attack_speed = 1.33
                case Weapon.Hammer.value:
                    attack_speed = 1.75
                case Weapon.Daggers.value:
                    attack_speed = 1.33
                case Weapon.Scythe.value:
                    attack_speed = 1.5
                case Weapon.Spear.value:
                    attack_speed = 1.5
                case Weapon.Sword.value:
                    attack_speed = 1.33
                case Weapon.Scepter.value:
                    attack_speed = 1.75
                case Weapon.Scepter2.value:
                    attack_speed = 1.75
                case Weapon.Wand.value:
                    attack_speed = 1.75
                case Weapon.Staff1.value:
                    attack_speed = 1.75
                case Weapon.Staff.value:
                    attack_speed = 1.75
                case Weapon.Staff2.value:
                    attack_speed = 1.75
                case Weapon.Staff3.value:
                    attack_speed = 1.75
                case _:
                    attack_speed = 1.75
                    
        return int((attack_speed / attack_speed_modifier) * 1000)

    def HandleCombat(self,ooc=False):
        """
        tries to Execute the next skill in the skill order.
        """
        
        # Check if we have a pending follow-up skill that should be cast immediately
        # This takes ABSOLUTE priority - must cast immediately after Echo/Auspicious, no other actions allowed
        if self.pending_followup_skill_slot >= 0:
            slot = self.pending_followup_skill_slot
            skill_id = self.skills[slot].skill_id
            skill_name = GLOBAL_CACHE.Skill.GetName(skill_id)
            
            Py4GW.Console.Log("EchoFollowup", f"Pending follow-up detected: slot={slot}, skill={skill_name} (ID:{skill_id})", Py4GW.Console.MessageType.Info)
            
            # Check if we're still in aftercast from the previous spell (Echo/Auspicious)
            # If so, wait for it to complete before casting the follow-up
            if self.in_casting_routine:
                # Still in aftercast, return False to wait
                elapsed = self.aftercast_timer.GetElapsedTime()
                Py4GW.Console.Log("EchoFollowup", f"Waiting for aftercast to complete (elapsed: {elapsed}ms, target: {self.aftercast}ms)", Py4GW.Console.MessageType.Warning)
                return False
            
            # Not in aftercast anymore, attempt to cast the follow-up immediately
            # We skip most checks here because we already validated the skill was ready before casting Echo/Auspicious
            
            Py4GW.Console.Log("EchoFollowup", "Aftercast complete, proceeding with follow-up cast checks", Py4GW.Console.MessageType.Info)
            
            # Only do minimal validation: check if player can cast and target is valid
            if GLOBAL_CACHE.Agent.IsCasting(GLOBAL_CACHE.Player.GetAgentID()):
                # Player is casting, wait
                Py4GW.Console.Log("EchoFollowup", "Player is currently casting, waiting...", Py4GW.Console.MessageType.Warning)
                return False
            
            if GLOBAL_CACHE.SkillBar.GetCasting() != 0:
                # Something is being cast, wait
                casting_skill = GLOBAL_CACHE.SkillBar.GetCasting()
                Py4GW.Console.Log("EchoFollowup", f"SkillBar shows casting in progress (skill: {casting_skill}), waiting...", Py4GW.Console.MessageType.Warning)
                return False
            
            # Get target for the follow-up skill
            target_agent_id = self.GetAppropiateTarget(slot)
            if target_agent_id == 0 or not GLOBAL_CACHE.Agent.IsLiving(target_agent_id):
                # Target not valid, clear pending and continue
                Py4GW.Console.Log("EchoFollowup", f"Target not valid (ID: {target_agent_id}), clearing pending follow-up", Py4GW.Console.MessageType.Error)
                self.pending_followup_skill_slot = -1
                return False
            
            # Cast the follow-up skill immediately
            Py4GW.Console.Log("EchoFollowup", f"CASTING FOLLOW-UP: {skill_name} on target {target_agent_id}", Py4GW.Console.MessageType.Success)
            self.in_casting_routine = True
            
            if self.fast_casting_exists:
                activation, recharge = Routines.Checks.Skills.apply_fast_casting(skill_id, self.fast_casting_level)
            else:
                activation = GLOBAL_CACHE.Skill.Data.GetActivation(skill_id)
            
            self.aftercast = activation * 1000
            self.aftercast += GLOBAL_CACHE.Skill.Data.GetAftercast(skill_id) * 1000
            
            skill_type, _ = GLOBAL_CACHE.Skill.GetType(skill_id)
            if skill_type == SkillType.Attack.value:
                self.aftercast += self.GetWeaponAttackAftercast()
            
            self.aftercast += self.ping_handler.GetCurrentPing()
            self.aftercast_timer.Reset()
            
            GLOBAL_CACHE.SkillBar.UseSkill(self.skill_order[slot]+1, target_agent_id)
            
            # Clear the pending follow-up
            self.pending_followup_skill_slot = -1
            self.ResetSkillPointer()
            Py4GW.Console.Log("EchoFollowup", "Follow-up cast complete, pending cleared", Py4GW.Console.MessageType.Success)
            return True
       
        slot = self.skill_pointer
        skill_id = self.skills[slot].skill_id
        
        is_skill_ready = self.IsSkillReady(slot)
            
        if not is_skill_ready:
            self.AdvanceSkillPointer()
            return False
        
        is_ooc_skill = self.IsOOCSkill(slot)

        if ooc and not is_ooc_skill:
            self.AdvanceSkillPointer()
            return False
         
        is_read_to_cast, target_agent_id = self.IsReadyToCast(slot)
 
        if not is_read_to_cast:
            self.AdvanceSkillPointer()
            return False
        

        if target_agent_id == 0:
            self.AdvanceSkillPointer()
            return False

        if not GLOBAL_CACHE.Agent.IsLiving(target_agent_id):
            return False
        
        # Special check for Arcane Echo: ensure target spell is ready
        if skill_id == self.arcane_echo:
            from HeroAI.settings import Settings
            settings = Settings()
            followup_skillbar_slot = settings.ArcaneEchoSkillSlot  # This is the SKILLBAR slot (0-7), not prioritized index
            
            Py4GW.Console.Log("EchoFollowup", f"Pre-cast check for Arcane Echo (configured skillbar slot={followup_skillbar_slot})", Py4GW.Console.MessageType.Info)
            
            # Get the skill ID from the skillbar slot (1-based for GetSkillIDBySlot)
            followup_skill_id = GLOBAL_CACHE.SkillBar.GetSkillIDBySlot(followup_skillbar_slot + 1)
            
            if followup_skill_id > 0:
                followup_skill_name = GLOBAL_CACHE.Skill.GetName(followup_skill_id)
                Py4GW.Console.Log("EchoFollowup", f"Target skill in skillbar slot {followup_skillbar_slot}: {followup_skill_name} (ID: {followup_skill_id})", Py4GW.Console.MessageType.Info)
                
                # Priority check: If Auspicious Incantation is configured to target Arcane Echo and is ready,
                # skip Arcane Echo to let Auspicious cast first
                # 
                # Desired order: Auspicious Incantation > Arcane Echo > Target Spell
                # - Auspicious reduces next spell energy cost
                # - Arcane Echo benefits from reduced cost
                # - Arcane Echo then copies the target spell
                auspicious_followup_slot = settings.AuspiciousIncantationSkillSlot
                arcane_echo_skillbar_slot = self.skill_order[self.skill_pointer]  # Skillbar slot where Arcane Echo currently is
                
                if 0 <= auspicious_followup_slot < 8:  # Skillbar slots are 0-7
                    # Check if Auspicious is configured to target Arcane Echo itself
                    if auspicious_followup_slot == arcane_echo_skillbar_slot:
                        # Auspicious targets Arcane Echo slot
                        is_auspicious_ready = Routines.Checks.Skills.IsSkillIDReady(self.auspicious_incantation)
                        if is_auspicious_ready:
                            Py4GW.Console.Log("EchoFollowup", f"Auspicious Incantation is ready and targeting Arcane Echo - giving priority to Auspicious, skipping Arcane Echo", Py4GW.Console.MessageType.Info)
                            self.AdvanceSkillPointer()
                            return False
                
                # Check if the followup skill is ready (not on cooldown)
                is_ready = Routines.Checks.Skills.IsSkillIDReady(followup_skill_id)
                Py4GW.Console.Log("EchoFollowup", f"Target spell {followup_skill_name} ready check: {is_ready}", Py4GW.Console.MessageType.Info)
                
                if not is_ready:
                    Py4GW.Console.Log("EchoFollowup", f"Target spell {followup_skill_name} NOT READY - skipping Arcane Echo cast", Py4GW.Console.MessageType.Warning)
                    self.AdvanceSkillPointer()
                    return False
                else:
                    Py4GW.Console.Log("EchoFollowup", f"Target spell {followup_skill_name} is ready - proceeding with Arcane Echo cast", Py4GW.Console.MessageType.Success)
            else:
                Py4GW.Console.Log("EchoFollowup", f"No skill found in skillbar slot {followup_skillbar_slot}", Py4GW.Console.MessageType.Error)
        
        # Special check for Auspicious Incantation: ensure we have enough energy for both
        # Auspicious Incantation AND the target spell
        if skill_id == self.auspicious_incantation:
            from HeroAI.settings import Settings
            settings = Settings()
            followup_skillbar_slot = settings.AuspiciousIncantationSkillSlot  # This is skillbar slot (0-7)
            
            Py4GW.Console.Log("EchoFollowup", f"Pre-cast check for Auspicious Incantation (configured skillbar slot={followup_skillbar_slot})", Py4GW.Console.MessageType.Info)
            
            # Get the skill ID from the skillbar slot (1-based for GetSkillIDBySlot)
            followup_skill_id = GLOBAL_CACHE.SkillBar.GetSkillIDBySlot(followup_skillbar_slot + 1)
            
            if followup_skill_id > 0:
                followup_skill_name = GLOBAL_CACHE.Skill.GetName(followup_skill_id)
                Py4GW.Console.Log("EchoFollowup", f"Target skill in skillbar slot {followup_skillbar_slot}: {followup_skill_name} (ID: {followup_skill_id})", Py4GW.Console.MessageType.Info)
                
                # Check if the followup skill is ready (not on cooldown)
                is_ready = Routines.Checks.Skills.IsSkillIDReady(followup_skill_id)
                if not is_ready:
                    Py4GW.Console.Log("EchoFollowup", f"Target spell {followup_skill_name} NOT READY - skipping Auspicious Incantation cast", Py4GW.Console.MessageType.Warning)
                    self.AdvanceSkillPointer()
                    return False
                
                # Check if we have enough energy for both spells
                current_energy = self.GetEnergyValues(GLOBAL_CACHE.Player.GetAgentID()) * GLOBAL_CACHE.Agent.GetMaxEnergy(GLOBAL_CACHE.Player.GetAgentID())
                
                # Energy cost for Auspicious Incantation itself
                auspicious_cost = Routines.Checks.Skills.GetEnergyCostWithEffects(skill_id, GLOBAL_CACHE.Player.GetAgentID())
                if self.expertise_exists:
                    auspicious_cost = Routines.Checks.Skills.apply_expertise_reduction(auspicious_cost, self.expertise_level, skill_id)
                
                # Energy cost for the followup spell
                followup_cost = Routines.Checks.Skills.GetEnergyCostWithEffects(followup_skill_id, GLOBAL_CACHE.Player.GetAgentID())
                if self.expertise_exists:
                    followup_cost = Routines.Checks.Skills.apply_expertise_reduction(followup_cost, self.expertise_level, followup_skill_id)
                
                total_energy_needed = auspicious_cost + followup_cost
                
                Py4GW.Console.Log("EchoFollowup", f"Energy check: Current={current_energy:.0f}, Needed={total_energy_needed:.0f} (Auspicious={auspicious_cost:.0f} + Target={followup_cost:.0f})", Py4GW.Console.MessageType.Info)
                
                if current_energy < total_energy_needed:
                    Py4GW.Console.Log("EchoFollowup", f"Not enough energy - skipping Auspicious Incantation cast", Py4GW.Console.MessageType.Warning)
                    self.AdvanceSkillPointer()
                    return False
                else:
                    Py4GW.Console.Log("EchoFollowup", f"Energy sufficient - proceeding with Auspicious Incantation cast", Py4GW.Console.MessageType.Success)
            else:
                Py4GW.Console.Log("EchoFollowup", f"No skill found in skillbar slot {followup_skillbar_slot}", Py4GW.Console.MessageType.Error)
        
        # Check if this is a target spell for Arcane Echo or Auspicious Incantation
        # If so, and the Echo/Auspicious spell is available, skip this spell
        # Priority: Auspicious (highest) -> Arcane -> target spell
        from HeroAI.settings import Settings
        settings = Settings()
        
        # Check if current skill is the Auspicious target and Auspicious is ready
        if (settings.AuspiciousIncantationSkillSlot < len(self.skills) and 
            skill_id == self.skills[settings.AuspiciousIncantationSkillSlot].skill_id and
            skill_id != self.auspicious_incantation):
            # Check if Auspicious Incantation is ready
            if Routines.Checks.Skills.IsSkillIDReady(self.auspicious_incantation):
                # Skip this spell, let Auspicious cast first
                self.AdvanceSkillPointer()
                return False
        
        # Check if current skill is the Arcane Echo target and Arcane Echo is ready
        if (settings.ArcaneEchoSkillSlot < len(self.skills) and 
            skill_id == self.skills[settings.ArcaneEchoSkillSlot].skill_id and
            skill_id != self.arcane_echo):
            # Check if Arcane Echo is ready
            if Routines.Checks.Skills.IsSkillIDReady(self.arcane_echo):
                # Skip this spell, let Arcane Echo cast first
                self.AdvanceSkillPointer()
                return False
            
        self.in_casting_routine = True
        
        # Log when we're about to cast a skill (to detect if other skills are being cast when they shouldn't)
        skill_name = GLOBAL_CACHE.Skill.GetName(skill_id)
        if self.pending_followup_skill_slot >= 0:
            # This should NEVER happen - if there's a pending follow-up, we should have handled it above
            Py4GW.Console.Log("EchoFollowup", f"ERROR: Casting {skill_name} while pending_followup_skill_slot={self.pending_followup_skill_slot}! This is a bug!", Py4GW.Console.MessageType.Error)
        
        if skill_id == self.arcane_echo or skill_id == self.auspicious_incantation:
            Py4GW.Console.Log("EchoFollowup", f"Casting {skill_name} (will set up follow-up after)", Py4GW.Console.MessageType.Info)

        
        if self.fast_casting_exists:
            activation, recharge = Routines.Checks.Skills.apply_fast_casting(skill_id, self.fast_casting_level)
        else:
            activation = GLOBAL_CACHE.Skill.Data.GetActivation(skill_id)

        self.aftercast = activation * 1000
        self.aftercast += GLOBAL_CACHE.Skill.Data.GetAftercast(skill_id) * 1000 #750
        
        skill_type, _ = GLOBAL_CACHE.Skill.GetType(skill_id)
        if skill_type == SkillType.Attack.value:
            self.aftercast += self.GetWeaponAttackAftercast()
            
            
        self.aftercast += self.ping_handler.GetCurrentPing()

        self.aftercast_timer.Reset()
        
        GLOBAL_CACHE.SkillBar.UseSkill(self.skill_order[self.skill_pointer]+1, target_agent_id)
        
        # Check if we just cast Arcane Echo or Auspicious Incantation
        # If so, schedule the configured follow-up skill to be cast next
        if skill_id == self.arcane_echo or skill_id == self.auspicious_incantation:
            echo_spell_name = GLOBAL_CACHE.Skill.GetName(skill_id)
            Py4GW.Console.Log("EchoFollowup", f"Just cast {echo_spell_name}, setting up follow-up...", Py4GW.Console.MessageType.Info)
            
            from HeroAI.settings import Settings
            settings = Settings()
            
            if skill_id == self.arcane_echo:
                followup_skillbar_slot = settings.ArcaneEchoSkillSlot  # This is skillbar slot (0-7)
            else:  # auspicious_incantation
                followup_skillbar_slot = settings.AuspiciousIncantationSkillSlot  # This is skillbar slot (0-7)
            
            Py4GW.Console.Log("EchoFollowup", f"Configured follow-up skillbar slot: {followup_skillbar_slot}", Py4GW.Console.MessageType.Info)
            
            # Get the skill ID from the skillbar slot
            followup_skill_id = GLOBAL_CACHE.SkillBar.GetSkillIDBySlot(followup_skillbar_slot + 1)  # +1 because GetSkillIDBySlot uses 1-based indexing
            
            if followup_skill_id > 0 and followup_skill_id != skill_id:
                followup_skill_name = GLOBAL_CACHE.Skill.GetName(followup_skill_id)
                
                # Find the prioritized slot index for this skill ID
                followup_prioritized_slot = -1
                for i in range(len(self.skills)):
                    if self.skills[i].skill_id == followup_skill_id:
                        followup_prioritized_slot = i
                        break
                
                if followup_prioritized_slot >= 0:
                    Py4GW.Console.Log("EchoFollowup", f"Found {followup_skill_name} at prioritized slot {followup_prioritized_slot} (skillbar slot {followup_skillbar_slot})", Py4GW.Console.MessageType.Info)
                    self.pending_followup_skill_slot = followup_prioritized_slot
                    self.followup_skill_timer.Reset()
                    self.followup_skill_timer.Start()
                    Py4GW.Console.Log("EchoFollowup", f"PENDING FOLLOW-UP SET: Will cast {followup_skill_name} next (aftercast: {self.aftercast}ms)", Py4GW.Console.MessageType.Success)
                else:
                    Py4GW.Console.Log("EchoFollowup", f"Could not find {followup_skill_name} in prioritized skill list!", Py4GW.Console.MessageType.Error)
            else:
                if followup_skill_id == 0:
                    Py4GW.Console.Log("EchoFollowup", f"No skill in skillbar slot {followup_skillbar_slot}", Py4GW.Console.MessageType.Error)
                elif followup_skill_id == skill_id:
                    Py4GW.Console.Log("EchoFollowup", f"Follow-up skill is same as Echo spell, not setting pending", Py4GW.Console.MessageType.Error)
        
        self.ResetSkillPointer()
        return True