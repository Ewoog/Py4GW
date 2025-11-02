import os
from Py4GWCoreLib.py4gwcorelib_src.Console import Console, ConsoleLog
from Py4GWCoreLib.py4gwcorelib_src.IniHandler import IniHandler

class Settings:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        base_path = Console.get_projects_path()
        self.ini_handler = IniHandler(os.path.join(base_path, "Widgets", "Config", "HeroAI.ini"))
        
        self.ShowPanelOnlyOnLeaderAccount = False
        self.CombinePanels = False
        self.ShowCommandPanel = True
        self.ShowHeroPanels = True
        self.ShowHeroEffects = True
        self.ShowEffectDurations = False
        self.ShowShortEffectDurations = True
        self.ShowHeroUpkeeps = True
        self.ShowHeroButtons = True
        self.ShowHeroBars = True
        self.ShowHeroSkills = True
        self.ShowFloatingTargets = True
        self.ShowPartyPanelUI = True
        self.HeroPanelPositions : dict[str, tuple[int, int, bool]] = {}
        
        
    def save_settings(self):
        self.ini_handler.write_key("General", "ShowPanelOnlyOnLeaderAccount", str(self.ShowPanelOnlyOnLeaderAccount))
        self.ini_handler.write_key("General", "CombinePanels", str(self.CombinePanels))
        self.ini_handler.write_key("General", "ShowCommandPanel", str(self.ShowCommandPanel))
        self.ini_handler.write_key("General", "ShowHeroPanels", str(self.ShowHeroPanels))
        
        self.ini_handler.write_key("General", "ShowHeroEffects", str(self.ShowHeroEffects))
        self.ini_handler.write_key("General", "ShowEffectDurations", str(self.ShowEffectDurations))
        self.ini_handler.write_key("General", "ShowShortEffectDurations", str(self.ShowShortEffectDurations))
        self.ini_handler.write_key("General", "ShowHeroUpkeeps", str(self.ShowHeroUpkeeps))
        
        self.ini_handler.write_key("General", "ShowHeroButtons", str(self.ShowHeroButtons))
        self.ini_handler.write_key("General", "ShowHeroBars", str(self.ShowHeroBars))
        self.ini_handler.write_key("General", "ShowFloatingTargets", str(self.ShowFloatingTargets))
        self.ini_handler.write_key("General", "ShowHeroSkills", str(self.ShowHeroSkills))
        self.ini_handler.write_key("General", "ShowPartyPanelUI", str(self.ShowPartyPanelUI))

        for hero_email, (x, y, collapsed) in self.HeroPanelPositions.items():
            self.ini_handler.write_key("HeroPanelPositions", hero_email, f"{x},{y},{collapsed}")
        
    def load_settings(self):
        self.ShowPanelOnlyOnLeaderAccount = self.ini_handler.read_bool("General", "ShowPanelOnlyOnLeaderAccount", False)
        self.CombinePanels = self.ini_handler.read_bool("General", "CombinePanels", False)
        self.ShowCommandPanel = self.ini_handler.read_bool("General", "ShowCommandPanel", True)
        self.ShowHeroPanels = self.ini_handler.read_bool("General", "ShowHeroPanels", True)
        
        self.ShowHeroEffects = self.ini_handler.read_bool("General", "ShowHeroEffects", True)
        self.ShowEffectDurations = self.ini_handler.read_bool("General", "ShowEffectDurations", True)
        self.ShowShortEffectDurations = self.ini_handler.read_bool("General", "ShowShortEffectDurations", True)
        self.ShowHeroUpkeeps = self.ini_handler.read_bool("General", "ShowHeroUpkeeps", True)
        
        self.ShowHeroButtons = self.ini_handler.read_bool("General", "ShowHeroButtons", True)
        self.ShowHeroBars = self.ini_handler.read_bool("General", "ShowHeroBars", True)
        self.ShowFloatingTargets = self.ini_handler.read_bool("General", "ShowFloatingTargets", True)
        self.ShowHeroSkills = self.ini_handler.read_bool("General", "ShowHeroSkills", True)
        self.ShowPartyPanelUI = self.ini_handler.read_bool("General", "ShowPartyPanelUI", True)

        self.HeroPanelPositions.clear()        
        items = self.ini_handler.list_keys("HeroPanelPositions")
        
        for key, value in items.items():
            try:
                x_str, y_str, collapsed_str = value.split(",")
                x = int(x_str)
                y = int(y_str)
                collapsed = collapsed_str.lower() == "true"
                self.HeroPanelPositions[key] = (x, y, collapsed)
                
            except Exception as e:
                ConsoleLog("HeroAI", f"Error loading HeroPanelPosition for {key}: {e}")