from typing import Callable
from Py4GWCoreLib import IconsFontAwesome5, Map
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from Py4GWCoreLib.GlobalCache.SharedMemory import Py4GWSharedMemoryManager
from Py4GWCoreLib.Py4GWcorelib import ConsoleLog
from Py4GWCoreLib.enums import CombatPrepSkillsType, Key, SharedCommandType


class Command:
    def __init__(self, name: str, icon: str, action: Callable, *args):
        self.name : str = name
        self.action : Callable = action
        self.icon : str = icon
        self.args : tuple = args
        
    def execute(self):
        try:
            if callable(self.action):
                
                ##Check if the action is callable with parameters
                if self.args:
                    ConsoleLog("SlaveMaster", f"Executing command '{self.name}' with args: {self.args}")
                    return self.action(*self.args)
                
                ##If no parameters are provided, just call the action
                return self.action()
            
        except Exception as e:
            ConsoleLog("SlaveMaster", f"Error executing command '{self.name}': {e}")
            return False
            
class Commands:
    instance = None
    
    def __new__(cls):
        if cls.instance is None:
            cls.instance = super(Commands, cls).__new__(cls)
            cls.instance._initialized = False
        return cls.instance

    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.current_account = GLOBAL_CACHE.Player.GetAccountEmail()
        self.commands : list[Command] = [
            Command("Resign", IconsFontAwesome5.ICON_FLAG, self.resign_command),
            Command("Stack on me", IconsFontAwesome5.ICON_RUNNING, self.stack_on_me),
            Command("Leave party", IconsFontAwesome5.ICON_DOOR_OPEN, self.leave_party),
            Command("Interact with Target", IconsFontAwesome5.ICON_HAND_POINT_LEFT, self.interact_with_taget),
            Command("Donate Faction", IconsFontAwesome5.ICON_DONATE, self.donate_faction),
            # Command("Reload", self.reload, IconsFontAwesome5.ICON_SYNC),
            # Command("Weaponset 1",  "1", self.change_weaponset, 1),
            # Command("Weaponset 2",  "2", self.change_weaponset, 2),
            # Command("ESC",  "ESC", self.press_escape),
        ]

    def donate_faction(self):
        faction = (1 if Map.GetMapID() == 193 else 2 if Map.GetMapID() == 77 else 0)
        
        if faction:
            accounts = GLOBAL_CACHE.ShMem.GetAllAccountData()
            for acc in accounts:
                # if acc.AccountEmail == self.current_account:
                #     continue

                GLOBAL_CACHE.ShMem.SendMessage(
                    self.current_account,
                    acc.AccountEmail,
                    SharedCommandType.DonateToGuild,
                    (faction, 0, 0, 0),
                )

    def prep_spirits(self):
        accounts = GLOBAL_CACHE.ShMem.GetAllAccountData()
        for acc in accounts:
            if acc.AccountEmail == self.current_account:
                continue
            
            GLOBAL_CACHE.ShMem.SendMessage(
                self.current_account, 
                acc.AccountEmail,
                SharedCommandType.UseSkill,
                (CombatPrepSkillsType.SpiritsPrep, 0, 0, 0),
            )
                            
    def press_escape(self):
        for acc in GLOBAL_CACHE.ShMem.GetAllAccountData():
            if acc.AccountEmail == self.current_account:
                continue

            GLOBAL_CACHE.ShMem.SendMessage(
                self.current_account, acc.AccountEmail, SharedCommandType.PressKey, (Key.Escape.value, 1, 0, 0))
                    
    def change_weaponset(self, weaponset: int):        
        for acc in GLOBAL_CACHE.ShMem.GetAllAccountData():            
            key = (Key.F1.value - 1) + weaponset            
            GLOBAL_CACHE.ShMem.SendMessage(
                self.current_account, acc.AccountEmail, SharedCommandType.PressKey, (key, 3, 0, 0))
        
    def resign_command(self, exclude_self: bool = False):
        for acc in GLOBAL_CACHE.ShMem.GetAllAccountData():
            if exclude_self and acc.AccountEmail == self.current_account:
                continue
            
            GLOBAL_CACHE.ShMem.SendMessage(
                self.current_account, acc.AccountEmail, SharedCommandType.Resign)            
        
            
    def interact_with_taget(self):
        target = GLOBAL_CACHE.Player.GetTargetID()
        if target == 0:
            return
        
        self_account = GLOBAL_CACHE.ShMem.GetAccountDataFromEmail(self.current_account)
        if not self_account:
            return
        
        accounts = GLOBAL_CACHE.ShMem.GetAllAccountData()
        sender_email = self.current_account
        
        for account in accounts:
            if self_account.AccountEmail == account.AccountEmail:
                continue
            GLOBAL_CACHE.ShMem.SendMessage(sender_email, account.AccountEmail, SharedCommandType.InteractWithTarget, (target,0,0,0))
        
    def reload(self, exclude_self: bool = True):
        for acc in GLOBAL_CACHE.ShMem.GetAllAccountData():
            if exclude_self and acc.AccountEmail == self.current_account:
                continue

        GLOBAL_CACHE.ShMem.SendMessage(
            self.current_account, self.current_account, SharedCommandType.LootEx, (10,0,0,0))
        
    def leave_party(self, exclude_self: bool = True):
        for acc in GLOBAL_CACHE.ShMem.GetAllAccountData():
            if exclude_self and acc.AccountEmail == self.current_account:
                continue

            GLOBAL_CACHE.ShMem.SendMessage(
                self.current_account, acc.AccountEmail, SharedCommandType.LeaveParty)
            
    def stack_on_me(self):
        for acc in GLOBAL_CACHE.ShMem.GetAllAccountData():
            if acc.AccountEmail == self.current_account:
                continue
            
            agent = GLOBAL_CACHE.Player.GetAgent()
            GLOBAL_CACHE.ShMem.SendMessage(
                self.current_account, acc.AccountEmail, SharedCommandType.PixelStack, (agent.x, agent.y, 0, 0))
