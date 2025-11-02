
import ctypes
from ctypes import wintypes
import math
import os
import Py4GW
import PyImGui
from Py4GWCoreLib import IconsFontAwesome5, ImGui, UIManager, Style
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from Py4GWCoreLib.GlobalCache.SharedMemory import HeroAIOptionStruct
from Py4GWCoreLib.Player import Player
from Py4GWCoreLib.Py4GWcorelib import ConsoleLog
import Widgets.frenkey.SlaveMaster.commands
from Widgets.frenkey.SlaveMaster.ui_manager_extensions import UIManagerExtensions
import importlib


importlib.reload(Widgets.frenkey.SlaveMaster.commands)


class UI:
    instance = None

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super(UI, cls).__new__(cls)
            cls.instance._initialized = False
        return cls.instance

    def __init__(self):
        if self._initialized:
            return

        self.command_bar : ImGui.WindowModule = ImGui.WindowModule(
            "Slave Master",
            "Slave Master",
            (0,0),
            (100, 100),
            PyImGui.WindowFlags(PyImGui.WindowFlags.NoMove | PyImGui.WindowFlags.NoResize | PyImGui.WindowFlags.NoCollapse | PyImGui.WindowFlags.NoTitleBar),
            can_close=False,
        )
        self._initialized = True
        self.commands = Widgets.frenkey.SlaveMaster.commands.Commands()
        self.commands_list = self.commands.commands
        self.account_mail = GLOBAL_CACHE.Player.GetAccountEmail()
        file_directory = os.path.dirname(os.path.abspath(__file__))
        self.icon_textures_path = os.path.join(file_directory, "textures")
        self.skill_textures_path = os.path.join(Py4GW.Console.get_projects_path(), "Textures", "Items")
        self.skill_textures_path = os.path.join(Py4GW.Console.get_projects_path(), "Textures", "Skill_Icons")
        self.options = HeroAIOptionStruct()

    def draw(self):
        """Draw the main UI components."""
        self.draw_window()
        self.draw_command_bar()

    def draw_window(self):
        """Draw the main window."""

        pass

    def draw_command_bar(self):
        """Draw the main window."""

        skill_bar_hash = 641635682
        self.frame_id = UIManager.GetFrameIDByHash(skill_bar_hash)

        if UIManagerExtensions.IsElementVisible(self.frame_id):
            self.left, self.top, self.right, self.bottom = UIManager.GetFrameCoords(
                self.frame_id)
            
            style = ImGui.get_style()

            style.WindowPadding.push_style_var(4, 4)
            style.ItemSpacing.push_style_var(2, 2)

            button_size = 38
            button_full_size = button_size + ((style.ItemSpacing.get_current().value2 or 0) * 2)
            height = ((button_full_size) * 2) + (style.WindowPadding.get_current().value2 or 0) * 2
            width = ((button_full_size) * math.ceil((len(self.commands_list)))) + ((style.ItemSpacing.get_current().value1 or 0) * 2 + (style.WindowPadding.get_current().value1 or 0) * 2)
            spacing = 25 if style.Theme is Style.StyleTheme.Guild_Wars else 20
            columns = math.floor(width / button_full_size)

            self.command_bar.window_pos = (self.left - width - spacing, self.bottom - (height) - (10 if style.Theme is Style.StyleTheme.Guild_Wars else 0))
            self.command_bar.window_size = (width + 10, height)

            PyImGui.set_next_window_pos(self.command_bar.window_pos)
            PyImGui.set_next_window_size(self.command_bar.window_size)

            self.command_bar.begin()
            if PyImGui.is_rect_visible(1, 1):
                PyImGui.push_style_var2(ImGui.ImGuiStyleVar.CellPadding, 2, 2)
                
                if PyImGui.begin_table("Commands Table", columns, PyImGui.TableFlags.NoFlag):
                    self.options.Following = ImGui.toggle_icon_button(IconsFontAwesome5.ICON_RUNNING + "##Following", self.options.Following,button_size,button_size)
                    ImGui.show_tooltip("Following")
                    PyImGui.table_next_column()
                    self.options.Avoidance = ImGui.toggle_icon_button(IconsFontAwesome5.ICON_PODCAST + "##Avoidance", self.options.Avoidance,button_size,button_size)
                    ImGui.show_tooltip("Avoidance")
                    PyImGui.table_next_column()
                    self.options.Looting = ImGui.toggle_icon_button(IconsFontAwesome5.ICON_COINS + "##Looting", self.options.Looting,button_size,button_size)
                    ImGui.show_tooltip("Looting")
                    PyImGui.table_next_column()
                    self.options.Targeting = ImGui.toggle_icon_button(IconsFontAwesome5.ICON_BULLSEYE + "##Targeting", self.options.Targeting,button_size,button_size)
                    ImGui.show_tooltip("Targeting")
                    PyImGui.table_next_column()
                    self.options.Combat = ImGui.toggle_icon_button(IconsFontAwesome5.ICON_SKULL_CROSSBONES + "##Combat", self.options.Combat,button_size,button_size)
                    ImGui.show_tooltip("Combat")
                                
                    if not self.account_mail or self.account_mail != GLOBAL_CACHE.Player.GetAccountEmail():
                        # ConsoleLog("SlaveMaster", "No current account set, cannot handle messages.")
                        self.account_mail = GLOBAL_CACHE.Player.GetAccountEmail()  
                    
                    options = GLOBAL_CACHE.ShMem.GetHeroAIOptions(self.account_mail) if self.account_mail else None
                    if options is not None:
                        options.Following = self.options.Following
                        options.Avoidance = self.options.Avoidance
                        options.Looting = self.options.Looting
                        options.Targeting = self.options.Targeting
                        options.Combat = self.options.Combat
                        # GLOBAL_CACHE.ShMem.SetHeroAIOptions(self.account_mail, options)
                        
                    # PyImGui.table_next_column()
                    # PyImGui.table_next_column()
                    # if PyImGui.button(IconsFontAwesome5.ICON_SKULL_CROSSBONES + f"##MoveWindows", button_size, button_size):
                    #     user32 = ctypes.WinDLL('user32', use_last_error=True)
                    #     SetWindowTextW = user32.SetWindowTextW
                    #     SetWindowTextW.restype = wintypes.BOOL
                    #     SetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
                                            
                    #     MoveWindow = user32.MoveWindow
                    #     MoveWindow.restype = wintypes.BOOL
                    #     MoveWindow.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.BOOL]

                        
                    #     window_handle = Py4GW.Console.get_gw_window_handle() 
                    
                    #     ConsoleLog("SlaveMaster", f"Moving window: {window_handle}", Py4GW.Console.MessageType.Info)
                    #     MoveWindow(
                    #         window_handle, 
                    #         0,  # x position #1273
                    #         0,  # y position
                    #         2574,  # width
                    #         1399,  # height
                    #         True  # repaint the window
                    #     )       

                    #     ConsoleLog("SlaveMaster", f"Moved window: {window_handle}", Py4GW.Console.MessageType.Info)
                    #     ConsoleLog("SlaveMaster", f"Setting window title: {Player.GetName()} - Guild Wars", Py4GW.Console.MessageType.Info)
                    #     ## Set window title 
                    #     SetWindowTextW(
                    #         window_handle, 
                    #         "ASDASD ASD ASD ASD ASD "
                    #     )
                    
                    #     pass
                    
                    PyImGui.table_next_column()
                    
                    if ImGui.image_button("##SpiritPrep", os.path.join(self.skill_textures_path, "[1240] - Soul Twisting.jpg"), button_size, button_size):
                        self.commands.prep_spirits()
                        
                    PyImGui.table_next_row()    
                                            
                    for command in self.commands_list:
                        PyImGui.table_next_column()
                        if ImGui.icon_button(command.icon + f"##{command.name}", button_size, button_size):
                            command.execute()
                        
                        ImGui.show_tooltip(command.name)

                    PyImGui.end_table()
                    
                PyImGui.pop_style_var(1)

            self.command_bar.end()
            style.WindowPadding.pop_style_var()
            style.ItemSpacing.pop_style_var()

        pass
