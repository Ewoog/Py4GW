import datetime
from Widgets.frenkey.LootEx import data_collector, enum, inventory_handling, settings
from Py4GWCoreLib import Inventory, Player
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from Py4GWCoreLib.GlobalCache.SharedMemory import Py4GWSharedMemoryManager
from Py4GWCoreLib.Py4GWcorelib import ActionQueueNode, ConsoleLog
from Py4GWCoreLib.enums import SharedCommandType

from Py4GW_widget_manager import WidgetHandler

from Widgets.frenkey.LootEx.data import Data
data = Data()

sharedMemoryManager = Py4GWSharedMemoryManager()
current_account = Player.GetAccountEmail()
action_node = ActionQueueNode(150)


start : datetime.datetime = datetime.datetime.now()
is_collecting = False

def ResetMessages():
    messages = sharedMemoryManager.GetAllMessages()
    messages = [msg for msg in messages if msg[1].Command == SharedCommandType.LootEx]
    
    for index, message in messages:
        receiverEmail = message.ReceiverEmail
        sharedMemoryManager.MarkMessageAsFinished(receiverEmail, index)

def SendReloadProfiles():
    global current_account
    
    ResetMessages()
    
    for acc in sharedMemoryManager.GetAllAccountData():
        if acc.AccountEmail == current_account:
            continue
    
        sharedMemoryManager.SendMessage(current_account, acc.AccountEmail, SharedCommandType.LootEx, (enum.MessageActions.ReloadProfiles, 0, 0))

def SendMergingMessage():
    global is_collecting
    
    ResetMessages()
    
    for acc in sharedMemoryManager.GetAllAccountData():
        if acc.AccountEmail == current_account:
            continue
    
        sharedMemoryManager.SendMessage(current_account, acc.AccountEmail, SharedCommandType.LootEx, (enum.MessageActions.PauseDataCollection, 0, 0))
        
    MergeWhenCollectionPaused()
        
def MergeWhenCollectionPaused():    
    messages = sharedMemoryManager.GetAllMessages()
    messages = [msg for msg in messages if msg[1].Command == SharedCommandType.LootEx]
    
    for index, message in messages:
        if message.Command == SharedCommandType.LootEx:
            param = int(message.Params[0] if len(message.Params) > 0 else 0)
            
            if param == enum.MessageActions.PauseDataCollection:                
                action_node.add_action(
                    MergeWhenCollectionPaused
                )
                
                return False
    
    data.MergeDiffItems()
    
    for acc in sharedMemoryManager.GetAllAccountData():
        if acc.AccountEmail == current_account:
            continue
        
        sharedMemoryManager.SendMessage(current_account, acc.AccountEmail, SharedCommandType.LootEx, (enum.MessageActions.ReloadData, 0, 0))
        sharedMemoryManager.SendMessage(current_account, acc.AccountEmail, SharedCommandType.LootEx, (enum.MessageActions.ResumeDataCollection, 0, 0))
            
    return True

def SendStart(exclude_self: bool = False):    
    for acc in sharedMemoryManager.GetAllAccountData():
        if exclude_self and acc.AccountEmail == current_account:
            continue
    
        sharedMemoryManager.SendMessage(current_account, acc.AccountEmail, SharedCommandType.LootEx, (enum.MessageActions.Start, 0, 0))

def SendStop(exclude_self: bool = False):    
    for acc in sharedMemoryManager.GetAllAccountData():
        if exclude_self and acc.AccountEmail == current_account:
            continue
    
        sharedMemoryManager.SendMessage(current_account, acc.AccountEmail, SharedCommandType.LootEx, (enum.MessageActions.Stop, 0, 0))

def SendLootingStart(exclude_self: bool = False):    
    for acc in sharedMemoryManager.GetAllAccountData():
        if exclude_self and acc.AccountEmail == current_account:
            continue
    
        sharedMemoryManager.SendMessage(current_account, acc.AccountEmail, SharedCommandType.LootEx, (enum.MessageActions.LootStart, 0, 0))

def SendLootingStop(exclude_self: bool = False):    
    for acc in sharedMemoryManager.GetAllAccountData():
        if exclude_self and acc.AccountEmail == current_account:
            continue
    
        sharedMemoryManager.SendMessage(current_account, acc.AccountEmail, SharedCommandType.LootEx, (enum.MessageActions.LootStop, 0, 0))

def SendShowLootExWindow(exclude_self: bool = False):
    for acc in sharedMemoryManager.GetAllAccountData():
        if exclude_self and acc.AccountEmail == current_account:
            continue
    
        sharedMemoryManager.SendMessage(current_account, acc.AccountEmail, SharedCommandType.LootEx, (enum.MessageActions.ShowLootExWindow, 0, 0))
        
def SendHideLootExWindow(exclude_self: bool = False):
    for acc in sharedMemoryManager.GetAllAccountData():
        if exclude_self and acc.AccountEmail == current_account:
            continue
    
        sharedMemoryManager.SendMessage(current_account, acc.AccountEmail, SharedCommandType.LootEx, (enum.MessageActions.HideLootExWindow, 0, 0))

def SendOpenXunlai(exclude_self: bool = False):
    for acc in sharedMemoryManager.GetAllAccountData():
        if exclude_self and acc.AccountEmail == current_account:
            continue
    
        sharedMemoryManager.SendMessage(current_account, acc.AccountEmail, SharedCommandType.LootEx, (enum.MessageActions.OpenXunlai, 0, 0))

def SendStartDataCollection(exclude_self: bool = False):
    global is_collecting
    
    for acc in sharedMemoryManager.GetAllAccountData():
        if exclude_self and acc.AccountEmail == current_account:
            continue
    
        sharedMemoryManager.SendMessage(current_account, acc.AccountEmail, SharedCommandType.LootEx, (enum.MessageActions.StartDataCollection, 0, 0))
    
def SendPauseDataCollection(exclude_self: bool = False):
    global is_collecting
    
    for acc in sharedMemoryManager.GetAllAccountData():
        if exclude_self and acc.AccountEmail == current_account:
            continue
    
        sharedMemoryManager.SendMessage(current_account, acc.AccountEmail, SharedCommandType.LootEx, (enum.MessageActions.PauseDataCollection, 0, 0))
        
def SendReloadWidgets(exclude_self: bool = False):
    for acc in sharedMemoryManager.GetAllAccountData():
        if exclude_self and acc.AccountEmail == current_account:
            continue
    
        sharedMemoryManager.SendMessage(current_account, acc.AccountEmail, SharedCommandType.LootEx, (enum.MessageActions.ReloadWidgets, 0, 0))

def ReloadWidgets():    
    widgetHandler = WidgetHandler()
    widgetHandler.discover_widgets()

def HandleMessages():
    action_node.ProcessQueue()    
    HandleReceivedMessages()
    
def HandleReceivedMessages():
    from Widgets.frenkey.LootEx.settings import Settings
    settings = Settings()
    
    global is_collecting, current_account
    
    if not current_account or current_account != GLOBAL_CACHE.Player.GetAccountEmail():
        # ConsoleLog("LootEx", "No current account set, cannot handle messages.")
        current_account = GLOBAL_CACHE.Player.GetAccountEmail()
        return
    
    messages = sharedMemoryManager.GetAllMessages()
    messages = [msg for msg in messages if msg[1].Command == SharedCommandType.LootEx]

    for index, message in messages:
        if message.Command == SharedCommandType.LootEx:
            if message.ReceiverEmail == current_account:
                param = int(message.Params[0] if len(message.Params) > 0 else 0)
                
                if param > 0:
                    # action : enum.MessageActions = enum.MessageActions(param)
                    
                    match param:
                        case enum.MessageActions.ReloadProfiles:
                            sharedMemoryManager.MarkMessageAsRunning(current_account, index)
                            
                            if settings.current_character:
                                ConsoleLog("LootEx", "Reloading profiles...")
                                settings.ReloadProfiles()
                                settings.SetProfile(settings.character_profiles[settings.current_character])
                            else:
                                ConsoleLog("LootEx", "Reloading profiles failed because no current character is set ...")
                                
                            sharedMemoryManager.MarkMessageAsFinished(current_account, index)
                            
                        case enum.MessageActions.PauseDataCollection:
                            sharedMemoryManager.MarkMessageAsRunning(current_account, index)     
                            is_collecting = settings.collect_items
                                                   
                            data_collector.instance.stop_collection()                            
                            sharedMemoryManager.MarkMessageAsFinished(current_account, index)
                            
                        case enum.MessageActions.ResumeDataCollection:
                            sharedMemoryManager.MarkMessageAsRunning(current_account, index)
                            
                            if is_collecting:
                                data_collector.instance.start_collection()
                            
                            sharedMemoryManager.MarkMessageAsFinished(current_account, index)
                            
                        case enum.MessageActions.StartDataCollection:
                            sharedMemoryManager.MarkMessageAsRunning(current_account, index)
                            
                            data_collector.instance.start_collection()
                            
                            sharedMemoryManager.MarkMessageAsFinished(current_account, index)
                        
                        case enum.MessageActions.Start:
                            inventory_handling.InventoryHandler().Start()
                            sharedMemoryManager.MarkMessageAsFinished(current_account, index)
                            
                        case enum.MessageActions.Stop:
                            inventory_handling.InventoryHandler().Stop()
                            sharedMemoryManager.MarkMessageAsFinished(current_account, index)
                            
                        case enum.MessageActions.LootStart:
                            inventory_handling.loot_handling.LootHandler().Start()
                            sharedMemoryManager.MarkMessageAsFinished(current_account, index)
                            
                        case enum.MessageActions.LootStop:
                            inventory_handling.loot_handling.LootHandler().Stop()
                            sharedMemoryManager.MarkMessageAsFinished(current_account, index)
                                
                        case enum.MessageActions.ReloadData:
                            sharedMemoryManager.MarkMessageAsRunning(current_account, index)
                            
                            ConsoleLog("LootEx", "Reloading data...")
                            data.Reload()
                            sharedMemoryManager.MarkMessageAsFinished(current_account, index)
                            
                        case enum.MessageActions.ShowLootExWindow:
                            settings.manual_window_visible = True
                            sharedMemoryManager.MarkMessageAsFinished(current_account, index)
                            
                        case enum.MessageActions.HideLootExWindow:
                            settings.manual_window_visible = False
                            sharedMemoryManager.MarkMessageAsFinished(current_account, index)
                            
                        case enum.MessageActions.OpenXunlai:    
                            Inventory.OpenXunlaiWindow()                            
                            sharedMemoryManager.MarkMessageAsFinished(current_account, index)
                                                
                        case enum.MessageActions.ReloadWidgets:
                            sharedMemoryManager.MarkMessageAsFinished(current_account, index)
                            ReloadWidgets()
                        
                        case _:
                            sharedMemoryManager.MarkMessageAsFinished(current_account, index)
                            return