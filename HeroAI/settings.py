import os

from PyPlayer import PyPlayer
from HeroAI.commands import HeroAICommands
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from Py4GWCoreLib.Player import Player
from Py4GWCoreLib.py4gwcorelib_src.Console import Console, ConsoleLog
from Py4GWCoreLib.py4gwcorelib_src.IniHandler import IniHandler

class Settings:
    class CommandHotBar:
        def __init__(self, identifier: str = ""):
            self.identifier: str = identifier
            self.commands: dict[int, dict[int, str]] = {0: {0: HeroAICommands().Empty.name}}
            self.position: tuple[int, int] = (0, 0)   
            self.visible: bool = True
            self.button_size: int = 32
        
        def to_ini_string(self) -> str:
            #save the position, visible state and combine commands into string into a single row
            ini_string = ""
            ini_string += f"{self.position[0]},{self.position[1]};"
            ini_string += f"{self.visible};"
            ini_string += f"{self.button_size};"
            
            #combine commands into rows
            for row in sorted(self.commands.keys()):
                cmd_row = self.commands[row]
                row_str = "|".join(cmd_row.get(col, HeroAICommands().Empty.name) for col in sorted(cmd_row.keys()))
                ini_string += f"{row_str};"
            
            return ini_string

        @staticmethod
        def from_ini_string(identifier: str, ini_string: str) -> 'Settings.CommandHotBar':
            hotbar = Settings.CommandHotBar()
            hotbar.identifier = identifier
            hotbar.commands = {}
            
            ConsoleLog("HeroAI", f"Parsing CommandHotBar from ini string: {ini_string}")
            
            try:
                position_str, visible_str, button_size_str, *command_rows_str = ini_string.split(";")
                x_str, y_str = position_str.split(",")[:2]
                hotbar.position = (int(x_str), int(y_str))
                                
                hotbar.visible = visible_str.lower() == "true"
                hotbar.button_size = int(button_size_str)

                row = 0
                if command_rows_str:
                    for row_str in command_rows_str:
                        command_names = {col: cmd_name for col, cmd_name in enumerate(row_str.split("|"))}  

                        if any(name for name in command_names.values()):
                            hotbar.commands[row] = command_names
                            row += 1
                    
                ConsoleLog("HeroAI", f"Loaded CommandHotBar '{identifier}' with {len(hotbar.commands)} rows.")
                
                if len(hotbar.commands) == 0:
                    hotbar.commands = {0: {0: HeroAICommands().Empty.name}}
                else:
                    pass
                    
            except Exception as e:
                ConsoleLog("HeroAI", f"Error parsing CommandHotBar from ini string: {e}")
                
            return hotbar

    _instance = None
    _instance_initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._instance_initialized:
            return
        
        self._instance_initialized = True
        
        self.save_requested = False
        
        self.ShowCommandPanel = True
        self.ShowCommandPanelOnlyOnLeaderAccount = True
        
        self.ShowPanelOnlyOnLeaderAccount = False
        self.DisableAutomationOnLeaderAccount = False
        
        # Designated leader settings for multibox
        self.UseDesignatedLeader = False
        self.DesignatedLeaderEmail = ""
        
        self.CombinePanels = False
        self.ShowHeroPanels = True
        self.ShowHeroEffects = True
        self.ShowEffectDurations = False
        self.ShowShortEffectDurations = True
        self.ShowHeroUpkeeps = True
        self.MaxEffectRows = 2
        
        self.ShowHeroButtons = True
        self.ShowHeroBars = True
        self.ShowHeroSkills = True
        self.ShowFloatingTargets = True
        self.ShowPartyPanelUI = True
        self.HeroPanelPositions : dict[str, tuple[int, int, int, int, bool]] = {}
        self.CommandHotBars : dict[str, Settings.CommandHotBar] = {}
        
        # Mesmer skill configurations (skill slot index, 0-based)
        self.ArcaneEchoSkillSlot = 0  # Which skill to copy with Arcane Echo
        self.AuspiciousIncantationSkillSlot = 0  # Which skill to use after Auspicious Incantation
        self.ArcaneMimicrySkillSlot = 0  # Which skill to steal with Arcane Mimicry (deprecated, keeping for compatibility)
        self.ArcaneMimicryTargetPartySlot = -1  # Which party member (by slot index 0-7) to target with Arcane Mimicry
        # Deprecated fields kept for backwards compatibility
        self.ArcaneMimicryTargetAgentID = 0
        self.ArcaneMimicryTargetEmail = ""
        self.ArcaneMimicryTargetHeroID = 0
        self.ArcaneMimicryEliteSkillID = 0  # Which elite skill to copy with Arcane Mimicry
        
        # Buff targeting configuration for multiple skills
        # Each skill has: mode ('profession' or 'player'), profession dict, and player set
        self.BuffTargetingConfig = {
            'Dark_Aura': {
                'mode': 'profession',  # 'profession' or 'player'
                'professions': {i: True for i in range(1, 11)},  # All professions enabled by default
                'players': set()  # Set of player emails/names when in player mode
            },
            'Great_Dwarf_Weapon': {
                'mode': 'profession',
                'professions': {i: True for i in range(1, 11)},
                'players': set()
            },
            'Strength_of_Honor': {
                'mode': 'profession',
                'professions': {i: True for i in range(1, 11)},
                'players': set()
            },
            'Spell_Breaker': {
                'mode': 'profession',
                'professions': {i: True for i in range(1, 11)},
                'players': set()
            }
        }
        
        base_path = Console.get_projects_path()
        self.ini_path = os.path.join(base_path, "Widgets", "Config", "HeroAI.ini")
        self.ini_handler = IniHandler(self.ini_path)
        
        self.account_email = ""        
        self.account_ini_path = ""    
        self._initialized = False    

    def reset(self): 
        self.account_email = ""
        pass 
    
    def ensure_initialized(self) -> bool: 
        account_email = PyPlayer().account_email
        initialized = True if account_email and account_email == self.account_email else False
        
        if not initialized:
            self.initialize_account_config()
        
        return self._initialized == initialized

    def initialize_account_config(self):
        base_path = Console.get_projects_path()        
        account_email = PyPlayer().account_email
        
        if account_email:
            config_dir = os.path.join(base_path, "Widgets", "Config", "Accounts", account_email)
            os.makedirs(config_dir, exist_ok=True)
            self.account_ini_path = os.path.join(config_dir, "HeroAI.ini")
            self.account_ini_handler = IniHandler(self.account_ini_path)
            self.account_email = account_email
                    
        self._initialized = True if account_email and account_email == self.account_email else False
        
        if self._initialized and account_email and self.account_email == account_email:
            if not os.path.exists(self.account_ini_path):
                self.save_requested = True
                self.write_settings()
            else:
                self.load_settings()
                
    def save_settings(self):
        self.save_requested = True
    
    def delete_hotbar(self, hotbar_id: str):
        if hotbar_id in self.CommandHotBars:
            del self.CommandHotBars[hotbar_id]
            self.account_ini_handler.delete_key("CommandHotBars", hotbar_id)
    
    def write_settings(self):               
        if not self.save_requested:
            return
        
        ConsoleLog("HeroAI", "Saving HeroAI settings...")
        
        self.ini_handler.write_key("General", "ShowCommandPanel", str(self.ShowCommandPanel))
        self.ini_handler.write_key("General", "ShowCommandPanelOnlyOnLeaderAccount", str(self.ShowCommandPanelOnlyOnLeaderAccount))
        
        self.ini_handler.write_key("General", "ShowPanelOnlyOnLeaderAccount", str(self.ShowPanelOnlyOnLeaderAccount))
        self.ini_handler.write_key("General", "DisableAutomationOnLeaderAccount", str(self.DisableAutomationOnLeaderAccount))
        
        # Designated leader settings
        self.ini_handler.write_key("General", "UseDesignatedLeader", str(self.UseDesignatedLeader))
        self.ini_handler.write_key("General", "DesignatedLeaderEmail", self.DesignatedLeaderEmail)
        
        self.ini_handler.write_key("General", "CombinePanels", str(self.CombinePanels))
        self.ini_handler.write_key("General", "ShowHeroPanels", str(self.ShowHeroPanels))
        
        
        self.ini_handler.write_key("General", "ShowHeroEffects", str(self.ShowHeroEffects))
        self.ini_handler.write_key("General", "ShowEffectDurations", str(self.ShowEffectDurations))
        self.ini_handler.write_key("General", "ShowShortEffectDurations", str(self.ShowShortEffectDurations))
        self.ini_handler.write_key("General", "ShowHeroUpkeeps", str(self.ShowHeroUpkeeps))
        self.ini_handler.write_key("General", "MaxEffectRows", str(self.MaxEffectRows))
        
        self.ini_handler.write_key("General", "ShowHeroButtons", str(self.ShowHeroButtons))
        self.ini_handler.write_key("General", "ShowHeroBars", str(self.ShowHeroBars))
        self.ini_handler.write_key("General", "ShowFloatingTargets", str(self.ShowFloatingTargets))
        self.ini_handler.write_key("General", "ShowHeroSkills", str(self.ShowHeroSkills))
        self.ini_handler.write_key("General", "ShowPartyPanelUI", str(self.ShowPartyPanelUI))
        
        # Mesmer skill settings
        self.account_ini_handler.write_key("MesmerSkills", "ArcaneEchoSkillSlot", str(self.ArcaneEchoSkillSlot))
        self.account_ini_handler.write_key("MesmerSkills", "AuspiciousIncantationSkillSlot", str(self.AuspiciousIncantationSkillSlot))
        self.account_ini_handler.write_key("MesmerSkills", "ArcaneMimicryTargetPartySlot", str(self.ArcaneMimicryTargetPartySlot))
        # Legacy fields
        self.account_ini_handler.write_key("MesmerSkills", "ArcaneMimicrySkillSlot", str(self.ArcaneMimicrySkillSlot))
        self.account_ini_handler.write_key("MesmerSkills", "ArcaneMimicryEliteSkillID", str(self.ArcaneMimicryEliteSkillID))
        
        # Buff targeting settings for all supported skills
        for skill_name, config in self.BuffTargetingConfig.items():
            section_name = f"BuffTargeting_{skill_name}"
            self.account_ini_handler.write_key(section_name, "mode", config['mode'])
            
            # Save profession configuration
            for profession_id, enabled in config['professions'].items():
                self.account_ini_handler.write_key(section_name, f"Profession_{profession_id}", str(enabled))
            
            # Save player list (convert set to comma-separated string)
            player_list = ','.join(config['players']) if config['players'] else ''
            self.account_ini_handler.write_key(section_name, "players", player_list)

        for hero_email, (x, y, w, h, collapsed) in self.HeroPanelPositions.items():
            self.account_ini_handler.write_key("HeroPanelPositions", hero_email, f"{x},{y},{w},{h},{collapsed}")
            
        for hotbar_id, hotbar in self.CommandHotBars.items():
            self.account_ini_handler.write_key("CommandHotBars", hotbar_id, hotbar.to_ini_string())
        
        self.save_requested = False
        
    def load_settings(self):          
        ConsoleLog("HeroAI", "Loading HeroAI settings...")      
        self.ShowCommandPanel = self.ini_handler.read_bool("General", "ShowCommandPanel", True)
        self.ShowCommandPanelOnlyOnLeaderAccount = self.ini_handler.read_bool("General", "ShowCommandPanelOnlyOnLeaderAccount", True)
        
        self.ShowPanelOnlyOnLeaderAccount = self.ini_handler.read_bool("General", "ShowPanelOnlyOnLeaderAccount", False)
        self.DisableAutomationOnLeaderAccount = self.ini_handler.read_bool("General", "DisableAutomationOnLeaderAccount", False)
        
        # Designated leader settings
        self.UseDesignatedLeader = self.ini_handler.read_bool("General", "UseDesignatedLeader", False)
        self.DesignatedLeaderEmail = self.ini_handler.read_string("General", "DesignatedLeaderEmail", "")
        
        self.CombinePanels = self.ini_handler.read_bool("General", "CombinePanels", False)
        self.ShowHeroPanels = self.ini_handler.read_bool("General", "ShowHeroPanels", True)
        
        self.ShowHeroEffects = self.ini_handler.read_bool("General", "ShowHeroEffects", True)
        self.ShowEffectDurations = self.ini_handler.read_bool("General", "ShowEffectDurations", True)
        self.ShowShortEffectDurations = self.ini_handler.read_bool("General", "ShowShortEffectDurations", True)
        self.ShowHeroUpkeeps = self.ini_handler.read_bool("General", "ShowHeroUpkeeps", True)
        self.MaxEffectRows = self.ini_handler.read_int("General", "MaxEffectRows", 2)
        
        self.ShowHeroButtons = self.ini_handler.read_bool("General", "ShowHeroButtons", True)
        self.ShowHeroBars = self.ini_handler.read_bool("General", "ShowHeroBars", True)
        self.ShowFloatingTargets = self.ini_handler.read_bool("General", "ShowFloatingTargets", True)
        self.ShowHeroSkills = self.ini_handler.read_bool("General", "ShowHeroSkills", True)
        self.ShowPartyPanelUI = self.ini_handler.read_bool("General", "ShowPartyPanelUI", True)
        
        # Mesmer skill settings
        self.ArcaneEchoSkillSlot = self.account_ini_handler.read_int("MesmerSkills", "ArcaneEchoSkillSlot", 0)
        self.AuspiciousIncantationSkillSlot = self.account_ini_handler.read_int("MesmerSkills", "AuspiciousIncantationSkillSlot", 0)
        self.ArcaneMimicryTargetPartySlot = self.account_ini_handler.read_int("MesmerSkills", "ArcaneMimicryTargetPartySlot", -1)
        # Legacy fields
        self.ArcaneMimicrySkillSlot = self.account_ini_handler.read_int("MesmerSkills", "ArcaneMimicrySkillSlot", 0)
        self.ArcaneMimicryTargetAgentID = self.account_ini_handler.read_int("MesmerSkills", "ArcaneMimicryTargetAgentID", 0)
        self.ArcaneMimicryTargetEmail = self.account_ini_handler.read_key("MesmerSkills", "ArcaneMimicryTargetEmail", "")
        self.ArcaneMimicryTargetHeroID = self.account_ini_handler.read_int("MesmerSkills", "ArcaneMimicryTargetHeroID", 0)
        self.ArcaneMimicryEliteSkillID = self.account_ini_handler.read_int("MesmerSkills", "ArcaneMimicryEliteSkillID", 0)
        
        # Buff targeting settings for all supported skills
        for skill_name in self.BuffTargetingConfig.keys():
            section_name = f"BuffTargeting_{skill_name}"
            
            # Load mode
            mode = self.account_ini_handler.read_string(section_name, "mode", "profession")
            self.BuffTargetingConfig[skill_name]['mode'] = mode
            
            # Load profession configuration
            for profession_id in range(1, 11):
                enabled = self.account_ini_handler.read_bool(section_name, f"Profession_{profession_id}", True)
                self.BuffTargetingConfig[skill_name]['professions'][profession_id] = enabled
            
            # Load player list
            player_list_str = self.account_ini_handler.read_string(section_name, "players", "")
            if player_list_str:
                self.BuffTargetingConfig[skill_name]['players'] = set(player_list_str.split(','))
            else:
                self.BuffTargetingConfig[skill_name]['players'] = set()

        self.HeroPanelPositions.clear()        
        self.import_hero_panel_positions(self.account_ini_handler)
        
        self.CommandHotBars.clear()
        self.import_command_hotbars(self.account_ini_handler)
            
    def import_hero_panel_positions(self, ini_handler: IniHandler):
        items = ini_handler.list_keys("HeroPanelPositions")
        request_save = False

        for key, value in items.items():
            try:
                x_str, y_str, w_str, h_str, collapsed_str = value.split(",")
                x = int(x_str)
                y = int(y_str)
                w = int(w_str)
                h = int(h_str)
                collapsed = collapsed_str.lower() == "true"
                request_save = key not in self.HeroPanelPositions or self.HeroPanelPositions[key] != (x, y, w, h, collapsed) or request_save
                self.HeroPanelPositions[key] = (x, y, w, h, collapsed)
                
            except Exception as e:
                ConsoleLog("HeroAI", f"Error loading HeroPanelPosition for {key}: {e}")
        
        if request_save:
            self.save_requested = True
    
    def import_command_hotbars(self, ini_handler: IniHandler):
        items = ini_handler.list_keys("CommandHotBars")
        request_save = False

        for key, value in items.items():
            try:
                hotbar = Settings.CommandHotBar.from_ini_string(key, value)
                # request_save = key not in self.CommandHotBars or self.CommandHotBars[key] != hotbar.to_ini_string() or request_save
                self.CommandHotBars[key] = hotbar
                
            except Exception as e:
                ConsoleLog("HeroAI", f"Error loading CommandHotBar for {key}: {e}")
        
        if request_save:
            self.save_requested = True