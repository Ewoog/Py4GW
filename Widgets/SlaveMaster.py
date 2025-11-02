
# Reload imports
import importlib
import os
from Widgets.frenkey.SlaveMaster import gui

from Py4GWCoreLib import Player, Routines
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from Py4GWCoreLib.GlobalCache.SharedMemory import Py4GWSharedMemoryManager
from Py4GWCoreLib.Py4GWcorelib import ConsoleLog, ThrottledTimer

importlib.reload(gui)

MODULE_NAME = "SlaveMaster"
throttle_timer = ThrottledTimer(250)
script_directory = os.path.dirname(os.path.abspath(__file__))


inventory_frame_hash = 291586130
sharedMemoryManager = Py4GWSharedMemoryManager()

ui = gui.UI()

def configure():
    pass


def main():
    global inventory_frame_hash
    
    if not Routines.Checks.Map.MapValid():
        return
        
    if GLOBAL_CACHE.Player.GetAgentID() != GLOBAL_CACHE.Party.GetPartyLeaderID():
        return                     
                         
    ui.draw()
        

__all__ = ['main', 'configure']
