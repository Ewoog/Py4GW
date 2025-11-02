
from collections.abc import Callable
import math
import os
import random
from Py4GW import Console
import PyImGui
from HeroAI import windows
from HeroAI.cache_data import CacheData
from HeroAI.settings import Settings
from HeroAI.utils import DrawHeroFlag, IsHeroFlagged
from HeroAI.windows import DrawFlags, SubmitGameOptions
from Py4GWCoreLib import Agent, ImGui
from Py4GWCoreLib.Effect import Effects
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from Py4GWCoreLib.GlobalCache.SharedMemory import AccountData, SharedMessage
from Py4GWCoreLib.ImGui_src.IconsFontAwesome5 import IconsFontAwesome5
from Py4GWCoreLib.ImGui_src.Textures import MapTexture, SplitTexture, TextureState, ThemeTexture, ThemeTextures
from Py4GWCoreLib.ImGui_src.WindowModule import WindowModule
from Py4GWCoreLib.ImGui_src.types import TEXTURE_FOLDER, StyleTheme
from Py4GWCoreLib.Overlay import Overlay
from Py4GWCoreLib.Player import Player
from Py4GWCoreLib.Routines import Routines
from Py4GWCoreLib.Skill import Skill
from Py4GWCoreLib.Skillbar import SkillBar
from Py4GWCoreLib.enums_src.GameData_enums import Allegiance, Attribute, Profession, ProfessionShort
from Py4GWCoreLib.enums_src.Multiboxing_enums import SharedCommandType
from Py4GWCoreLib.py4gwcorelib_src.Color import Color
from Py4GWCoreLib.py4gwcorelib_src.Console import ConsoleLog
from Py4GWCoreLib.py4gwcorelib_src.Timer import ThrottledTimer, Timer
from Py4GWCoreLib.py4gwcorelib_src.Utils import Utils


class CachedSkillInfo:
    def __init__(self, skill_id: int):
        self.skill_id = skill_id
        self.name = GLOBAL_CACHE.Skill.GetNameFromWiki(skill_id)
        self.description = GLOBAL_CACHE.Skill.GetDescription(skill_id)
        self.texture_path = GLOBAL_CACHE.Skill.ExtraData.GetTexturePath(skill_id)
        self.is_elite = GLOBAL_CACHE.Skill.Flags.IsElite(skill_id)
        self.is_hex = GLOBAL_CACHE.Skill.Flags.IsHex(skill_id)
        self.is_title = GLOBAL_CACHE.Skill.Flags.IsTitle(skill_id)
        self.is_enchantment = GLOBAL_CACHE.Skill.Flags.IsEnchantment(skill_id)
        self.is_shout = GLOBAL_CACHE.Skill.Flags.IsShout(skill_id)
        self.is_skill = GLOBAL_CACHE.Skill.Flags.IsSkill(skill_id)
        self.is_condition = GLOBAL_CACHE.Skill.Flags.IsCondition(skill_id)
        
        self.adrenaline_cost = GLOBAL_CACHE.Skill.Data.GetAdrenaline(skill_id)

        frame_texture, texture_state, progress_color = get_frame_texture_for_effect(
            skill_id)
        self.frame_texture = frame_texture
        self.texture_state = texture_state
        self.progress_color = progress_color

        self.recharge_time = GLOBAL_CACHE.Skill.Data.GetRecharge(skill_id)


skill_cache: dict[int, CachedSkillInfo] = {}
message_cache : dict[str, dict[SharedCommandType, dict[int, tuple]]] = {}
template_popup_open: bool = False
template_account: str = ""
template_code = ""

flag_account = ""
settings = Settings()
casting_animation_timer = Timer()
casting_animation_timer.Start()

def get_frame_texture_for_effect(skill_id: int) -> tuple[(SplitTexture | MapTexture), TextureState, int]:
    is_elite = GLOBAL_CACHE.Skill.Flags.IsElite(skill_id)
    texture_state = TextureState.Normal if not is_elite else TextureState.Active

    theme = ImGui.get_style().Theme
    if not theme in ImGui.Textured_Themes:
        theme = StyleTheme.Guild_Wars

    if GLOBAL_CACHE.Skill.Flags.IsHex(skill_id):
        frame_texture = ThemeTextures.Effect_Frame_Hex.value.get_texture(theme)
        progress_color = Color(215, 31, 158, 255).color_int

    elif GLOBAL_CACHE.Skill.Flags.IsTitle(skill_id):
        frame_texture = ThemeTextures.Effect_Frame_Skill.value.get_texture(theme)
        progress_color = Color(75, 139, 69, 255).color_int

    elif GLOBAL_CACHE.Skill.Flags.IsEnchantment(skill_id):
        frame_texture = ThemeTextures.Effect_Frame_Enchantment.value.get_texture(theme)
        progress_color = Color(178, 225, 47, 255).color_int

        profession, _ = GLOBAL_CACHE.Skill.GetProfession(skill_id)
        if profession == Profession.Dervish:
            frame_texture = ThemeTextures.Effect_Frame_Blue.value.get_texture()
            progress_color = Color(74, 163, 193, 255).color_int

    elif GLOBAL_CACHE.Skill.Flags.IsCondition(skill_id):
        frame_texture = ThemeTextures.Effect_Frame_Condition.value.get_texture(theme)
        progress_color = Color(221, 175, 52, 255).color_int

    else:
        frame_texture = ThemeTextures.Effect_Frame_Skill.value.get_texture(theme)
        progress_color = Color(75, 139, 69, 255).color_int

    return frame_texture, texture_state, progress_color

def draw_health_bar(width: float, height: float, max_health: float, current_health: float, regen: float) -> bool:
    style = ImGui.get_style()
    draw_textures = style.Theme in ImGui.Textured_Themes
    pips = Utils.calculate_health_pips(max_health, regen)

    if not draw_textures:
        style.PlotHistogram.push_color((204, 0, 0, 255))
        style.FrameRounding.push_style_var(0)
        ImGui.progress_bar(current_health, width, height)
        style.FrameRounding.pop_style_var()
        style.PlotHistogram.pop_color()            
    else:
        ImGui.dummy(width, height)

    fraction = (max(0.0, min(1.0, current_health))
                if max_health > 0 else 0.0)
    item_rect_min = PyImGui.get_item_rect_min()
    item_rect_max = PyImGui.get_item_rect_max()

    width = item_rect_max[0] - item_rect_min[0]
    height = item_rect_max[1] - item_rect_min[1]
    item_rect = (item_rect_min[0], item_rect_min[1], width, height)

    progress_rect = (item_rect[0] + 1, item_rect[1] + 1,
                     (width - 2) * fraction, height - 2)
    background_rect = (
        item_rect[0] + 1, item_rect[1] + 1, width - 2, height - 2)
    cursor_rect = (item_rect[0] - 2 + (width - 2) * fraction, item_rect[1] + 1, 4, height -
                   2) if fraction > 0 else (item_rect[0] + (width - 2) * fraction, item_rect[1] + 1, 4, height - 2)

    if draw_textures:
        ThemeTextures.HealthBarEmpty.value.get_texture().draw_in_drawlist(
            background_rect[0],
            background_rect[1],
            (background_rect[2], background_rect[3]),
        )

        ThemeTextures.HealthBarFill.value.get_texture().draw_in_drawlist(
            progress_rect[0],
            progress_rect[1],
            (progress_rect[2], progress_rect[3]),
        )

        if current_health * max_health != max_health:
            ThemeTextures.HealthBarCursor.value.get_texture().draw_in_drawlist(
                cursor_rect[0],
                cursor_rect[1],
                (cursor_rect[2], cursor_rect[3]),
            )

    display_label = str(int(current_health * max_health))
    textsize = PyImGui.calc_text_size(display_label)
    text_rect = (item_rect[0] + ((width - textsize[0]) / 2), item_rect[1] +
                 ((height - textsize[1]) / 2) + 3, textsize[0], textsize[1])

    ImGui.push_font("Regular", 12)
    PyImGui.draw_list_add_text(
        text_rect[0],
        text_rect[1],
        style.Text.color_int,
        display_label,
    )
    ImGui.pop_font()

    if draw_textures:
        pip_texture = ThemeTextures.Pip_Regen if pips > 0 else ThemeTextures.Pip_Degen

        if pips > 0:
            pip_pos = text_rect[0] + text_rect[2] + 5

            for i in range(int(pips)):
                pip_texture.value.get_texture().draw_in_drawlist(
                    pip_pos + (i * 8),
                    item_rect[1],
                    (10 * (height / 16), height),
                )

        elif pips < 0:
            pip_pos = text_rect[0] - 5 - 10

            for i in range(abs(int(pips))):
                pip_texture.value.get_texture().draw_in_drawlist(
                    pip_pos - (i * 8),
                    item_rect[1],
                    (10 * (height / 16), height),
                )

        ThemeTextures.ProgressBarFrame.value.get_texture().draw_in_drawlist(
            item_rect[0],
            item_rect[1],
            (item_rect[2], item_rect[3]),
        )
    else:
        pip_char = IconsFontAwesome5.ICON_ANGLE_RIGHT if pips > 0 else IconsFontAwesome5.ICON_ANGLE_LEFT
        pip_string = "".join([pip_char for _ in range(abs(int(pips)))])

        ImGui.push_font("Regular", 8)
        if pips > 0:
            PyImGui.draw_list_add_text(
                text_rect[0] + text_rect[2] + 5,
                item_rect[1] + 3,
                style.Text.color_int,
                pip_string
            )
        elif pips < 0:
            text_size = PyImGui.calc_text_size(pip_string)
            PyImGui.draw_list_add_text(
                text_rect[0] - 5 - text_size[0],
                item_rect[1] + 3,
                style.Text.color_int,
                pip_string
            )
        ImGui.pop_font()
        
    return PyImGui.is_item_clicked(0)

def draw_energy_bar(width: float, height: float, max_energy: float, current_energy: float, regen: float) -> bool:
    style = ImGui.get_style()
    pips = Utils.calculate_energy_pips(max_energy, regen)

    draw_textures = style.Theme in ImGui.Textured_Themes

    if not draw_textures:
        style.PlotHistogram.push_color((30, 94, 153, 255))
        style.FrameRounding.push_style_var(0)
        ImGui.progress_bar(current_energy, width, height)
        style.FrameRounding.pop_style_var()
        style.PlotHistogram.pop_color()
    else:
        ImGui.dummy(width, height)

    fraction = (max(0.0, min(1.0, current_energy))
                if max_energy > 0 else 0.0)
    item_rect_min = PyImGui.get_item_rect_min()
    item_rect_max = PyImGui.get_item_rect_max()

    width = item_rect_max[0] - item_rect_min[0]
    height = item_rect_max[1] - item_rect_min[1]
    item_rect = (item_rect_min[0], item_rect_min[1], width, height)

    progress_rect = (item_rect[0] + 1, item_rect[1] + 1,
                     (width - 2) * fraction, height - 2)
    background_rect = (
        item_rect[0] + 1, item_rect[1] + 1, width - 2, height - 2)
    cursor_rect = (item_rect[0] - 2 + (width - 2) * fraction, item_rect[1] + 1, 4, height -
                   2) if fraction > 0 else (item_rect[0] + (width - 2) * fraction, item_rect[1] + 1, 4, height - 2)

    if draw_textures:
        ThemeTextures.EnergyBarEmpty.value.get_texture().draw_in_drawlist(
            background_rect[0],
            background_rect[1],
            (background_rect[2], background_rect[3]),
        )

        ThemeTextures.EnergyBarFill.value.get_texture().draw_in_drawlist(
            progress_rect[0],
            progress_rect[1],
            (progress_rect[2], progress_rect[3]),
        )

        if current_energy * max_energy != max_energy:
            ThemeTextures.EnergyBarCursor.value.get_texture().draw_in_drawlist(
                cursor_rect[0],
                cursor_rect[1],
                (cursor_rect[2], cursor_rect[3]),
            )

    display_label = str(int(current_energy * max_energy))
    textsize = PyImGui.calc_text_size(display_label)
    text_rect = (item_rect[0] + ((width - textsize[0]) / 2), item_rect[1] +
                 ((height - textsize[1]) / 2) + 3, textsize[0], textsize[1])

    ImGui.push_font("Regular", 12)
    PyImGui.draw_list_add_text(
        text_rect[0],
        text_rect[1],
        style.Text.color_int,
        display_label,
    )
    ImGui.pop_font()

    if draw_textures:
        pip_texture = ThemeTextures.Pip_Regen if pips > 0 else ThemeTextures.Pip_Degen

        if pips > 0:
            pip_pos = text_rect[0] + text_rect[2] + 5

            for i in range(int(pips)):
                pip_texture.value.get_texture().draw_in_drawlist(
                    pip_pos + (i * 8),
                    item_rect[1],
                    (10 * (height / 16), height),
                )

        elif pips < 0:
            pip_pos = text_rect[0] - 5 - 10

            for i in range(abs(int(pips))):
                pip_texture.value.get_texture().draw_in_drawlist(
                    pip_pos - (i * 8),
                    item_rect[1],
                    (10 * (height / 16), height),
                )

        ThemeTextures.ProgressBarFrame.value.get_texture().draw_in_drawlist(
            item_rect[0],
            item_rect[1],
            (item_rect[2], item_rect[3]),
        )
    else:
        pip_char = IconsFontAwesome5.ICON_ANGLE_RIGHT if pips > 0 else IconsFontAwesome5.ICON_ANGLE_LEFT
        pip_string = "".join([pip_char for _ in range(abs(int(pips)))])

        ImGui.push_font("Regular", 8)
        if pips > 0:
            PyImGui.draw_list_add_text(
                text_rect[0] + text_rect[2] + 5,
                item_rect[1] + 3,
                style.Text.color_int,
                pip_string
            )
        elif pips < 0:
            text_size = PyImGui.calc_text_size(pip_string)
            PyImGui.draw_list_add_text(
                text_rect[0] - 5 - text_size[0],
                item_rect[1] + 3,
                style.Text.color_int,
                pip_string
            )
        ImGui.pop_font()

    return PyImGui.is_item_clicked(0)

def DrawSquareCooldownEx(button_pos, button_size, progress, tint=0.1):
    """Smooth, non-overlapping, counter-clockwise square cooldown effect."""
    if isinstance(button_size, (int, float)):
        button_size = (button_size, button_size)

    if progress <= 0 or progress >= 1.0:
        return

    center_x = button_pos[0] + button_size[0] / 2.0
    center_y = button_pos[1] + button_size[1] / 2.0
    half_w = button_size[0] / 2.0
    half_h = button_size[1] / 2.0
    color = (int(255 * tint) << 24)

    # Angles
    start_angle = -math.pi / 2.0  # top center
    end_angle = start_angle - 2.0 * math.pi * progress

    # Pre-calculate points
    segments = max(32, min(64, int(64 + 128 * (1 - progress))))
    points = [(center_x, center_y)]

    # Function to compute intersection with square boundary
    def intersection(angle):
        dx, dy = math.cos(angle), math.sin(angle)
        tx = half_w / abs(dx) if dx != 0 else float("inf")
        ty = half_h / abs(dy) if dy != 0 else float("inf")
        t = min(tx, ty)
        return (center_x + dx * t, center_y + dy * t)

    # Always include corners at boundary crossings to prevent overlap
    # Define corner angles in CCW order (starting from top-right)
    corner_angles = [
        -math.pi / 4,     # top-right
        -3 * math.pi / 4,  # bottom-right
        -5 * math.pi / 4,  # bottom-left
        -7 * math.pi / 4,  # top-left
        -math.pi / 4 - 2 * math.pi  # wrap
    ]

    # Generate wedge path
    a = start_angle
    for corner in corner_angles:
        if end_angle < corner < a:
            points.append(intersection(corner))
        elif end_angle >= corner >= a:
            points.append(intersection(corner))
    # Uniform segment sampling for smoothness
    for i in range(segments + 1):
        angle = start_angle + (end_angle - start_angle) * (i / segments)
        points.append(intersection(angle))

    # Remove potential duplicates to prevent triangle overlap
    unique_points = []
    for p in points:
        if not unique_points or (abs(unique_points[-1][0] - p[0]) > 0.1 or abs(unique_points[-1][1] - p[1]) > 0.1):
            unique_points.append(p)

    # Draw filled triangle fan (no overlaps)
    for i in range(1, len(unique_points) - 1):
        x1, y1 = unique_points[0]
        x2, y2 = unique_points[i]
        x3, y3 = unique_points[i + 1]
        PyImGui.draw_list_add_triangle_filled(x1, y1, x2, y2, x3, y3, color)

def get_skill_target(account_data: AccountData, cached_skill: CachedSkillInfo) -> int | None:
    py_io = PyImGui.get_io()
    
    if not cached_skill or cached_skill.skill_id == 0:
        return None
    
    target_id = GLOBAL_CACHE.Player.GetTargetID()
    is_gadget = GLOBAL_CACHE.Agent.IsGadget(target_id)
    is_item = GLOBAL_CACHE.Agent.IsItem(target_id)
    
    if cached_skill.is_enchantment or cached_skill.is_shout:
        allegiance, _ = GLOBAL_CACHE.Agent.GetAllegiance(target_id) if target_id != 0 else (Allegiance.Neutral, None)
        
        if allegiance in [Allegiance.Ally, Allegiance.Minion, Allegiance.SpiritPet]:
            return target_id
        else:
            return GLOBAL_CACHE.Player.GetAgentID() if py_io.key_ctrl else account_data.PlayerID
    else:
        return GLOBAL_CACHE.Player.GetAgentID() if py_io.key_ctrl else target_id if not is_item and target_id else account_data.PlayerID

def draw_casting_animation(
    pos: tuple[float, float],
    size: tuple[float, float],
    min_alpha: int = 40
):
    """Draws lightweight concentric circles moving from outside toward the center (casting animation)."""
    global casting_animation_timer

    # Get elapsed time (ms → s)
    t = casting_animation_timer.GetElapsedTime() / 1000.0

    # Animation parameters
    num_circles = 3               # number of simultaneous circles
    cycle_duration = 1.25         # seconds per full travel (outside → center)
    max_radius = max(size) * 0.75 # start slightly outside item bounds
    min_radius = max(size) * 0.05 # small inner limit (center end)
    center_x = pos[0] + size[0] / 2
    center_y = pos[1] + size[1] / 2

    # Clamp the minimum alpha to valid range
    min_alpha = max(0, min(255, min_alpha))

    for i in range(num_circles):
        # Each circle’s start offset — evenly staggered
        offset = i / num_circles

        # Normalized progress (0 → 1), wraps every cycle
        progress = (t / cycle_duration + offset) % 1.0

        # Radius interpolates from max_radius → min_radius
        radius = max_radius - (max_radius - min_radius) * progress

        # Alpha goes from 255 → min_alpha (instead of fading to zero)
        alpha = int(min_alpha + (255 - min_alpha) * (1.0 - progress) ** 1.5)
        alpha = max(0, min(255, alpha))  # safety clamp

        # Optional subtle rotation effect
        swirl_angle = math.sin((t + i) * 2.0) * 0.1
        cx = center_x + math.cos(swirl_angle) * 0.0
        cy = center_y + math.sin(swirl_angle) * 0.0

        color = Color.from_tuple((0, 0, 0, alpha / 255.0))

        PyImGui.push_clip_rect(pos[0], pos[1], pos[0] + size[0], pos[1] + size[1], True)
        PyImGui.draw_list_add_circle(cx, cy, radius, color.color_int, 36, 6.0)
        PyImGui.pop_clip_rect()


def draw_skill_bar(height: float, account_data: AccountData, cached_data: CacheData, message_queue: list[tuple[int, SharedMessage]]):
    global skill_cache, messages
    style = ImGui.get_style()
    draw_textures = style.Theme in ImGui.Textured_Themes

    for slot, skill_id in enumerate(account_data.PlayerSkillIDs):
        
        if skill_id not in skill_cache:
            skill_cache[skill_id] = CachedSkillInfo(skill_id)

        skill = skill_cache[skill_id]
        skill_texture = skill.texture_path

        if not skill_texture:
            ImGui.dummy(height, height)
            item_rect_min = PyImGui.get_item_rect_min()

            PyImGui.draw_list_add_rect(
                item_rect_min[0],
                item_rect_min[1],
                item_rect_min[0] + height,
                item_rect_min[1] + height,
                Color(50, 50, 50, 255).color_int,
                0,
                0,
                2
            )
            PyImGui.same_line(0, 0)
            continue

        skill_recharge = account_data.PlayerSkillRecharge[slot]
        adrenaline = account_data.PlayerSkillAdrenaline[slot]
        enough_adrenaline = adrenaline >= skill.adrenaline_cost
        
        ImGui.image(skill_texture, (height, height), uv0=(
            0.0625, 0.0625) if draw_textures else (0, 0), uv1=(0.9375, 0.9375) if draw_textures else (1, 1))

        if PyImGui.is_item_hovered():
            PyImGui.set_next_window_size((300, 0), PyImGui.ImGuiCond.Always)
            if ImGui.begin_tooltip():
                ImGui.push_font("Regular", 14)
                ImGui.text_colored(
                    f"{skill.name} (ID: {skill.skill_id})",
                    Color(227, 211, 165, 255).color_tuple                    
                )
                ImGui.pop_font()

                ImGui.separator()
                if skill.description:
                    ImGui.text_wrapped(skill.description)
                
                PyImGui.spacing()
                
                gray_color = Color(150, 150, 150, 255)
                
                ImGui.push_font("Regular", 12)
                ImGui.text_colored(
                    "Click to use on current target",
                    gray_color.color_tuple                  
                )
                PyImGui.set_cursor_pos_y(PyImGui.get_cursor_pos_y() - 2)
                
                ImGui.text_colored(
                    "Ctrl + Click to use on self",
                    gray_color.color_tuple                
                )
                PyImGui.set_cursor_pos_y(PyImGui.get_cursor_pos_y() - 2)
                
                ImGui.text_colored(
                    "Shift + Click to toggle active/inactive",
                    gray_color.color_tuple              
                )
                ImGui.pop_font()

                ImGui.end_tooltip()

        item_rect_min = PyImGui.get_item_rect_min()
        casting_skill = account_data.PlayerCastingSkillID
        
        if skill_recharge > 0:
                DrawSquareCooldownEx(
                    (item_rect_min[0], item_rect_min[1]),
                    height,
                    skill_recharge/(skill.recharge_time * 1000.0),
                    tint=0.6
                )

                text_size = PyImGui.calc_text_size(
                    f"{int(skill_recharge/1000)}")
                offset_x = (height - text_size[0]) / 2
                offset_y = (height - text_size[1]) / 2

                PyImGui.draw_list_add_text(
                    item_rect_min[0] + offset_x,
                    item_rect_min[1] + offset_y,
                    ImGui.get_style().Text.color_int,
                    f"{int(skill_recharge/1000)}"
                )
        elif casting_skill == skill.skill_id:
            draw_casting_animation(item_rect_min, (height, height))
        
        if not enough_adrenaline:             
            adrenaline_fraction = adrenaline / skill.adrenaline_cost if skill.adrenaline_cost > 0 else 0.0
            adrenaline_fraction = max(0.0, min(adrenaline_fraction, 1.0))  # Clamp between 0–1       
                   
            fill_rect = (item_rect_min[0], item_rect_min[1], height, height - (height * adrenaline_fraction))
            
            PyImGui.draw_list_add_rect_filled(
                fill_rect[0],
                fill_rect[1],
                fill_rect[0] + fill_rect[2],
                fill_rect[1] + fill_rect[3],
                Color(0, 0, 0, 150).color_int,
                0,
                0
            )
            
            PyImGui.draw_list_add_line(
                fill_rect[0],
                fill_rect[1] + fill_rect[3],
                fill_rect[0] + fill_rect[2],
                fill_rect[1] + fill_rect[3],
                Color(0, 0, 0, 255).color_int,
                1
            )
                
        hero_options = cached_data.HeroAI_vars.all_game_option_struct[account_data.PartyPosition]
        if not hero_options.Skills[slot].Active:
            hovered = PyImGui.is_item_hovered()
            ThemeTextures.Cancel.value.get_texture().draw_in_drawlist(
                PyImGui.get_item_rect_min()[0],
                PyImGui.get_item_rect_min()[1],
                (height, height),
                state=TextureState.Hovered if hovered else TextureState.Normal
            )

        account_email = GLOBAL_CACHE.Player.GetAccountEmail()
        queued_skill_messages = message_cache.get(account_email, {}).get(SharedCommandType.UseSkill, {})
        if queued_skill_messages:
            queued_skill_usage = {index: msg for index, msg in message_queue if msg.Command == SharedCommandType.UseSkill and msg.ReceiverEmail == account_email and msg.Params[1] == float(skill.skill_id) and index in queued_skill_messages}
                    
            if queued_skill_usage:
                hovered = PyImGui.is_item_hovered()
                ThemeTextures.Check.value.get_texture().draw_in_drawlist(
                    PyImGui.get_item_rect_min()[0],
                    PyImGui.get_item_rect_min()[1],
                    (height, height),
                    state=TextureState.Hovered if hovered else TextureState.Normal
                )
            else:
                #delete all queued messages for this skill that were not found in new messages (probably failed)
                indices_to_delete = [index for index, msg in queued_skill_messages.items() if msg[1] == skill.skill_id]
                for index in indices_to_delete:
                    del queued_skill_messages[index]

        if PyImGui.is_item_clicked(0) and enough_adrenaline:
            io = PyImGui.get_io()
            if io.key_shift:
                hero_ai_data = GLOBAL_CACHE.ShMem.GetGerHeroAIOptionsByPartyNumber(
                    account_data.PartyPosition)
                if hero_ai_data:
                    hero_ai_data.Skills[slot] = not hero_options.Skills[slot].Active

            else:
                target_id = get_skill_target(account_data, skill)
                
                if target_id is not None:
                    message_index = GLOBAL_CACHE.ShMem.SendMessage(GLOBAL_CACHE.Player.GetAccountEmail(
                    ), account_data.AccountEmail, SharedCommandType.UseSkill, (target_id, float(skill.skill_id)))

                    if account_data.AccountEmail not in message_cache:
                        message_cache[account_data.AccountEmail] = {}
                        
                    if SharedCommandType.UseSkill not in message_cache[account_data.AccountEmail]:
                        message_cache[account_data.AccountEmail][SharedCommandType.UseSkill] = {}

                    message_cache[account_data.AccountEmail][SharedCommandType.UseSkill][message_index] = (target_id, skill.skill_id)

        if draw_textures:
            texture_state = TextureState.Normal if not skill.is_elite else TextureState.Active

            ThemeTextures.Skill_Frame.value.get_texture().draw_in_drawlist(
                item_rect_min[0],
                item_rect_min[1],
                (height, height),
                state=texture_state
            )

        PyImGui.same_line(0, 0)

    pass  # Implementation of skill bar drawing logic goes here

def draw_buffs_bar(account_data: AccountData, win_pos: tuple, win_size: tuple, message_queue: list[tuple[int, SharedMessage]], skill_size: float = 28):
    if not settings.ShowHeroEffects and not settings.ShowHeroUpkeeps:
        return

    style = ImGui.get_style()

    invis_flags = ImGui.PushTransparentWindow()
    PyImGui.set_next_window_pos(
        (win_pos[0], win_pos[1] + win_size[1] + (13 if style.Theme == StyleTheme.Guild_Wars else 4)), PyImGui.ImGuiCond.Always)

    open = PyImGui.begin("##Buffs Bar" + account_data.AccountEmail, True, invis_flags)
    ImGui.PopTransparentWindow()

    if open:
        draw_buffs_and_upkeeps(account_data, skill_size)
        
    PyImGui.end()
    pass  # Implementation of buffs bar drawing logic goes here

def draw_buffs_and_upkeeps(account_data: AccountData, skill_size: float = 28):
    style = ImGui.get_style()
    
    def draw_buff(effect: CachedSkillInfo, duration: float, remaining: float, draw_effect_frame: bool = True, skill_size: float = skill_size):
        if not effect.texture_path:
            ImGui.dummy(skill_size, skill_size)
        else:
            ImGui.image(effect.texture_path, (skill_size, skill_size), uv0=(0.125, 0.125) if not draw_effect_frame else (
                0.0625, 0.0625), uv1=(0.875, 0.875) if not draw_effect_frame else (0.9375, 0.9375))
            
        item_rect_min = PyImGui.get_item_rect_min()
        item_rect_max = PyImGui.get_item_rect_max()

        if draw_effect_frame:
            frame_texture, texture_state = effect.frame_texture, effect.texture_state
            frame_texture.draw_in_drawlist(
                item_rect_min[0],
                item_rect_min[1],
                (skill_size, skill_size),
                state=texture_state
            )

        if settings.ShowEffectDurations or settings.ShowShortEffectDurations:
            duration = account_data.PlayerEffectsDuration[index]
            remaining = account_data.PlayerEffectsRemaining[index]

            if duration > 0 and remaining and (not settings.ShowShortEffectDurations or remaining < 60000):
                progress_background_rect = (
                    item_rect_min[0] + 2, item_rect_max[1] - 4, item_rect_max[0] - 2, item_rect_max[1] - 1)

                PyImGui.draw_list_add_rect_filled(
                    progress_background_rect[0],
                    progress_background_rect[1],
                    progress_background_rect[2],
                    progress_background_rect[3],
                    Color(0, 0, 0, 255).color_int,
                    0,
                    0
                )

                progress_rect = (
                    progress_background_rect[0] + 1,
                    progress_background_rect[1] + 1,
                    progress_background_rect[2] - 2,
                    progress_background_rect[3] - 1
                )

                fraction = remaining / (duration * 1000.0)
                progress_width = (
                    progress_rect[2] - progress_rect[0]) * fraction
                PyImGui.draw_list_add_rect_filled(
                    progress_rect[0],
                    progress_rect[1],
                    progress_rect[0] + progress_width,
                    progress_rect[3],
                    effect.progress_color,
                    0,
                    0
                )

                text_size = PyImGui.calc_text_size(f"{int(remaining/1000)}")
                offset_x = (skill_size - text_size[0]) / 2
                offset_y = (skill_size - text_size[1]) / 2

                PyImGui.draw_list_add_rect_filled(
                    item_rect_min[0] + offset_x - 1,
                    item_rect_min[1] + offset_y - 1,
                    item_rect_min[0] + offset_x + text_size[0] + 1,
                    item_rect_min[1] + offset_y + text_size[1] + 1,
                    Color(0, 0, 0, 150).color_int,
                    2,
                    0
                )
                PyImGui.draw_list_add_text(
                    item_rect_min[0] + offset_x,
                    item_rect_min[1] + offset_y,
                    style.Text.color_int,
                    f"{int(remaining/1000)}"
                )

        PyImGui.show_tooltip(
            f"Effect ID: {effect.skill_id}\nName: {effect.name}")
        PyImGui.same_line(0, 0)

    if settings.ShowHeroUpkeeps:
        ImGui.dummy(0, 24)
        PyImGui.same_line(0, 0)
        
        for index, upkeep_id in enumerate(account_data.PlayerUpkeeps):
            if upkeep_id == 0:
                continue

            if not upkeep_id in skill_cache:
                skill_cache[upkeep_id] = CachedSkillInfo(upkeep_id)

            effect = skill_cache[upkeep_id]
            duration = account_data.PlayerEffectsDuration[index]
            remaining = account_data.PlayerEffectsRemaining[index]

            draw_buff(effect, duration, remaining, False, 24)

        if any(account_data.PlayerUpkeeps) and any(account_data.PlayerEffects) and settings.ShowHeroEffects:
            PyImGui.new_line()
            PyImGui.set_cursor_pos_y(PyImGui.get_cursor_pos_y() - 4)

    if settings.ShowHeroEffects:                        
        ImGui.dummy(0, 28)
        PyImGui.same_line(0, 0)
        
        for index, effect_id in enumerate(account_data.PlayerEffects):
            if effect_id == 0:
                continue
            
            if not effect_id in skill_cache:
                skill_cache[effect_id] = CachedSkillInfo(effect_id)

            effect = skill_cache[effect_id]
            duration = account_data.PlayerEffectsDuration[index]
            remaining = account_data.PlayerEffectsRemaining[index]

            draw_buff(effect, duration, remaining, True, 28)
        
        PyImGui.new_line()

def enter_skill_template_code(account_data : AccountData):
    global template_popup_open, template_code, template_account
    
    if not template_popup_open:
        return
    
    if template_popup_open:
        PyImGui.open_popup("Enter Skill Template Code")
    
    # PyImGui.set_next_window_size((300, 100), PyImGui.ImGuiCond.Always)
    PyImGui.set_window_pos(500 , 100, PyImGui.ImGuiCond.Always)
    if PyImGui.begin_popup("Enter Skill Template Code"):
        template_code = ImGui.input_text("##template_code", template_code)

        if ImGui.button("Load"):
            GLOBAL_CACHE.ShMem.SendMessage(
                GLOBAL_CACHE.Player.GetAccountEmail(),
                account_data.AccountEmail,           
                SharedCommandType.LoadSkillTemplate,
                ExtraData=(template_code, 0, 0, 0)
            )
            
            template_popup_open = False
            PyImGui.close_current_popup() 
            
        PyImGui.same_line(0, 10)
        if ImGui.button("Cancel"):
            PyImGui.close_current_popup()             
            template_popup_open = False

        if PyImGui.is_mouse_clicked(0) and not PyImGui.is_any_item_hovered():
            PyImGui.close_current_popup()             
            template_popup_open = False
            
        PyImGui.end_popup()
        
def flag_hero(account_data: AccountData, cached_data: CacheData):    
    global flag_account
    
    windows.capture_flag_all = False
    windows.capture_hero_flag = True
    windows.capture_hero_index = account_data.PartyPosition
    
    DrawFlags(cached_data)
    
    if not windows.capture_hero_flag:
        flag_account = ""
    
def draw_buttons(account_data: AccountData, cached_data: CacheData, message_queue: list[tuple[int, SharedMessage]], btn_size: float = 28):
    global message_cache
    style = ImGui.get_style()
    draw_textures = style.Theme in ImGui.Textured_Themes
    
    global template_popup_open, template_account, flag_account
    is_explorable = GLOBAL_CACHE.Map.IsExplorable()
    if not ImGui.begin_child("##buttons" + account_data.AccountEmail, (84, 58), False,
                             PyImGui.WindowFlags.NoScrollbar | PyImGui.WindowFlags.NoScrollWithMouse):
        ImGui.end_child()
        return

    style = ImGui.get_style()
    same_map = GLOBAL_CACHE.Map.GetMapID() == account_data.MapID
    player_email = GLOBAL_CACHE.Player.GetAccountEmail()
    account_email = account_data.AccountEmail

    btn_size = btn_size if draw_textures else btn_size - 1

    def is_queued(command: SharedCommandType, clear: bool = False) -> bool:
        cached_commands = message_cache.get(account_email, {}).get(command, {})

        if cached_commands:
            queued_commands = {index: msg for index, msg in message_queue if msg.Command == command and msg.ReceiverEmail == account_email and index in cached_commands} 
            if not queued_commands:
                if clear:
                    cached_commands.clear()
                           
            return len(queued_commands) > 0
        
        return False
            
    def draw_button(id_suffix: str, icon: str, tooltip: str, command: SharedCommandType, send_message: Callable[[], int] = lambda: False, get_status: Callable[[], bool] = lambda: False, new_line: bool = False):        
        """Reusable button creation logic with hover, icon, and tooltip."""
        btn_id = f"##{id_suffix}{account_email}"
        status = get_status()
        is_command_queued = is_queued(command, clear=True)
        
        if (draw_textures and PyImGui.invisible_button(btn_id, btn_size, btn_size)) or (not draw_textures and ImGui.button(btn_id, btn_size, btn_size)):
            if is_command_queued:
                ConsoleLog("HERO AI", f"Command {command.name} already queued for {account_email}, skipping send.")
                return               
            
            message_index = send_message()            
            if message_index > -1:
                if account_data.AccountEmail not in message_cache:
                    message_cache[account_data.AccountEmail] = {}
                    
                if command not in message_cache[account_data.AccountEmail]:
                    message_cache[account_data.AccountEmail][command] = {}
                
                message_cache[account_data.AccountEmail][command][message_index] = ()


        hovered = PyImGui.is_item_hovered()
        item_rect_min = PyImGui.get_item_rect_min()
        if draw_textures:
            ThemeTextures.HeroPanelButtonBase.value.get_texture().draw_in_drawlist(
                item_rect_min[0], item_rect_min[1], (btn_size, btn_size),
                state=TextureState.Active if status else TextureState.Normal,
                tint=(255, 255, 255, 255) if hovered else (200, 200, 200, 255)
            )

        ImGui.push_font("Regular", 10)
        text_size = PyImGui.calc_text_size(icon)
        PyImGui.draw_list_add_text(
            item_rect_min[0] + (btn_size - text_size[0]) / 2,
            item_rect_min[1] + (btn_size - text_size[1]) / 2,
            style.Text.color_int,
            icon
        )
        ImGui.pop_font()
        ImGui.show_tooltip(tooltip)
        
        if not new_line:
            PyImGui.same_line(0, 0 if draw_textures else 1)
        else:
            PyImGui.set_cursor_pos_y(PyImGui.get_cursor_pos_y() - 4)

    if not is_explorable:
        player_x, player_y = GLOBAL_CACHE.Player.GetXY()
        target_id = Player.GetTargetID() or Player.GetAgentID()

        def invite_player():
            same_map = GLOBAL_CACHE.Map.GetMapID() == account_data.MapID
            
            if same_map:
                GLOBAL_CACHE.Party.Players.InvitePlayer(account_data.CharacterName)
                
            return GLOBAL_CACHE.ShMem.SendMessage(
                player_email,
                account_email,
                SharedCommandType.InviteToParty if same_map else SharedCommandType.TravelToMap,
                (account_data.PlayerID, 0, 0, 0) if same_map else (
                    GLOBAL_CACHE.Map.GetMapID(),
                    GLOBAL_CACHE.Map.GetRegion()[0],
                    GLOBAL_CACHE.Map.GetDistrict(),
                    0,
                )
            )
        
        def load_template():
            global template_popup_open, template_code, template_account
            template_popup_open = True  
            template_code = ""
            template_account = account_data.AccountEmail
            
            return -1       
            
        buttons = [
            (
                "pixel_stack",
                IconsFontAwesome5.ICON_COMPRESS_ARROWS_ALT,
                "Pixel Stack",
                SharedCommandType.PixelStack,
                lambda: GLOBAL_CACHE.ShMem.SendMessage(player_email, account_email, SharedCommandType.PixelStack, (player_x, player_y, 0, 0)),
                lambda: is_queued(SharedCommandType.PixelStack),
            ),
            (
                "interact",
                IconsFontAwesome5.ICON_HAND_POINT_RIGHT,
                "Interact with Target",
                SharedCommandType.InteractWithTarget,
                lambda: GLOBAL_CACHE.ShMem.SendMessage(player_email, account_email, SharedCommandType.InteractWithTarget, (target_id, 0, 0, 0)),
                lambda: is_queued(SharedCommandType.InteractWithTarget),
            ),
            (
                "dialog",
                IconsFontAwesome5.ICON_COMMENT_DOTS,
                "Dialog with Target",
                SharedCommandType.TakeDialogWithTarget,
                lambda: GLOBAL_CACHE.ShMem.SendMessage(player_email, account_email, SharedCommandType.TakeDialogWithTarget, (target_id, 1, 0, 0)),
                lambda: is_queued(SharedCommandType.TakeDialogWithTarget),
                True,
            ),
            (
                "load_template",
                IconsFontAwesome5.ICON_FILE_IMPORT,
                "Load Skill Template",
                SharedCommandType.LoadSkillTemplate,
                load_template,
                lambda: is_queued(SharedCommandType.LoadSkillTemplate),
            ),
            (
                "invite_summon",
                IconsFontAwesome5.ICON_USER_PLUS,
                "Invite" if same_map else "Summon",
                SharedCommandType.InviteToParty if same_map else SharedCommandType.TravelToMap,
                invite_player,
                lambda: is_queued(SharedCommandType.InviteToParty) if same_map else is_queued(SharedCommandType.TravelToMap),
            ),
            (
                "focus_client",
                IconsFontAwesome5.ICON_DESKTOP,
                "Focus client",
                SharedCommandType.SetWindowActive,
                lambda: GLOBAL_CACHE.ShMem.SendMessage(
                    player_email,
                    account_email,
                    SharedCommandType.SetWindowActive,
                    (0, 0, 0, 0),
                ),
                lambda: is_queued(SharedCommandType.SetWindowActive),
            ),
        ]


        for btn in buttons:
            draw_button(*btn)
        
        if template_account == account_data.AccountEmail and template_account:    
            enter_skill_template_code(account_data)  

    else:        
        player_x, player_y = GLOBAL_CACHE.Player.GetXY()
        target_id = Player.GetTargetID() or Player.GetAgentID()
        
        def flag_hero_account():
            global flag_account
            flag_account = account_data.AccountEmail
            ConsoleLog("HERO AI", "Flagging hero...")
            return -1
        
        def clear_hero_flag():
            cached_data.HeroAI_vars.shared_memory_handler.set_player_property(account_data.PartyPosition, "IsFlagged", False)
            cached_data.HeroAI_vars.shared_memory_handler.set_player_property(account_data.PartyPosition, "FlagPosX", 0.0)
            cached_data.HeroAI_vars.shared_memory_handler.set_player_property(account_data.PartyPosition, "FlagPosY", 0.0)
            cached_data.HeroAI_vars.shared_memory_handler.set_player_property(account_data.PartyPosition, "FollowAngle", 0.0)
            return -1
        
        buttons = [
            # (id_suffix, icon, tooltip, command, args)
            ("pixel_stack", IconsFontAwesome5.ICON_COMPRESS_ARROWS_ALT, "Pixel Stack",
             SharedCommandType.PixelStack, lambda: GLOBAL_CACHE.ShMem.SendMessage(player_email, account_email, SharedCommandType.PixelStack, (player_x, player_y, 0, 0)), lambda: is_queued(SharedCommandType.PixelStack)),

            ("interact", IconsFontAwesome5.ICON_HAND_POINT_RIGHT, "Interact with Target",
             SharedCommandType.InteractWithTarget, lambda: GLOBAL_CACHE.ShMem.SendMessage(player_email, account_email, SharedCommandType.InteractWithTarget, (target_id, 0, 0, 0)), lambda: is_queued(SharedCommandType.InteractWithTarget)),

            ("dialog", IconsFontAwesome5.ICON_COMMENT_DOTS, "Dialog with Target",
             SharedCommandType.TakeDialogWithTarget, lambda: GLOBAL_CACHE.ShMem.SendMessage(player_email, account_email, SharedCommandType.TakeDialogWithTarget, (target_id, 1, 0, 0)), lambda: is_queued(SharedCommandType.TakeDialogWithTarget), True),

            ("flag", IconsFontAwesome5.ICON_FLAG, "Flag Target",
             SharedCommandType.NoCommand, flag_hero_account, lambda: IsHeroFlagged(cached_data, account_data.PartyPosition)),

            ("clear flag", IconsFontAwesome5.ICON_CIRCLE_XMARK, "Clear Flag",
             SharedCommandType.NoCommand, clear_hero_flag, lambda: False),
            
            ("focus client",
             IconsFontAwesome5.ICON_DESKTOP,
             "Focus client",
             SharedCommandType.SetWindowActive, lambda: GLOBAL_CACHE.ShMem.SendMessage(
                player_email,
                account_email,
                SharedCommandType.SetWindowActive,
                (0, 0, 0, 0),
             )),
        ]
        
        for btn in buttons:
            draw_button(*btn)
                        
    ImGui.end_child()

title_names: dict[str, str] = {}

def get_display_name(account_data: AccountData) -> str:    
    name = account_data.CharacterName
    titles = [
        "the Brave",
        "the Mighty",
        "the Swift",
        "the Cunning",
        "the Wise",
        "the Fearless",
        "the Valiant",
        "the Bold",
        "the Fierce",
        "the Gallant",
        "the Noble",
        "the Daring",
        "the Resolute",
        "the Stalwart",
        "the Intrepid",
        "the Dauntless",
        "the Adventurous",
        "the Courageous",
        "the Heroic",
        "the Legendary"
    ]
    
    if not name in title_names:
        title_names[name] = "Frenkey " + random.choice(titles)
        
    name = title_names[name]
    return account_data.CharacterName

def draw_combined_hero_panel(account_data: AccountData, cached_data: CacheData, messages: list[tuple[int, SharedMessage]], open: bool = True):
    name = get_display_name(account_data)
    
    style = ImGui.get_style()
    ImGui.dummy(PyImGui.get_content_region_avail()[0], 22)
    
    item_rect_min = PyImGui.get_item_rect_min()
    item_rect_max = PyImGui.get_item_rect_max()
    item_rect = (item_rect_min[0], item_rect_min[1] + 5, item_rect_max[0] - item_rect_min[0], item_rect_max[1] - item_rect_min[1])
    
    ThemeTextures.HeaderLabelBackground.value.get_texture().draw_in_drawlist(
        item_rect[0],
        item_rect[1] - 0,
        (item_rect[2], item_rect[3]),
        tint=(225, 225, 225, 200) if style.Theme is StyleTheme.Guild_Wars else (255, 255, 255, 255)
    )
    
    text_size = PyImGui.calc_text_size(name)
    text_pos = (item_rect[0] + (item_rect[2] - text_size[0]) / 2, item_rect[1] + 2 + (item_rect[3] - text_size[1]) / 2)
    ImGui.push_font("Regular", 14)
    PyImGui.draw_list_add_text(
        text_pos[0],
        text_pos[1],
        style.Text.color_int,
        name
    )
    ImGui.pop_font()
    
    height = 28 if settings.ShowHeroSkills else 0
    height += 28 if settings.ShowHeroBars else 0
    height += 4 if settings.ShowHeroBars and settings.ShowHeroSkills else 0

    if height > 0:
        if ImGui.begin_child("##bars" + account_data.AccountEmail, (225, height)):
            curr_avail = PyImGui.get_content_region_avail()
            if settings.ShowHeroBars:
                health_clicked = draw_health_bar(curr_avail[0], 13, account_data.PlayerMaxHP,
                                account_data.PlayerHP, account_data.PlayerHealthRegen)                        
                PyImGui.set_cursor_pos_y(PyImGui.get_cursor_pos_y() - 4)
                energy_clicked = draw_energy_bar(curr_avail[0], 13, account_data.PlayerMaxEnergy,
                                account_data.PlayerEnergy, account_data.PlayerEnergyRegen)
                
                if health_clicked or energy_clicked:
                            ConsoleLog("HERO AI", f"Switching target to hero {account_data.CharacterName}...")
                            
                            if GLOBAL_CACHE.Map.GetMapID() == account_data.MapID:
                                GLOBAL_CACHE.Player.ChangeTarget(account_data.PlayerID)
                                
            if settings.ShowHeroSkills:
                if settings.ShowHeroBars:
                    PyImGui.set_cursor_pos_y(PyImGui.get_cursor_pos_y() - 4)
                
                draw_skill_bar(28, account_data, cached_data, messages)

        ImGui.end_child()

    if (settings.ShowHeroBars or settings.ShowHeroSkills) and settings.ShowHeroButtons:
        PyImGui.same_line(0, 2)
        
    if settings.ShowHeroButtons:
        draw_buttons(account_data, cached_data, messages, 28)

    draw_buffs_and_upkeeps(account_data, 28)    

def draw_hero_panel(window: WindowModule, account_data: AccountData, cached_data: CacheData, messages: list[tuple[int, SharedMessage]], open: bool = True):
    global flag_account, title_names
    style = ImGui.get_style()
    style.WindowPadding.push_style_var(4, 1)
    
    collapsed = window.collapse
    open = window.begin(open, PyImGui.WindowFlags.AlwaysAutoResize)
    style.WindowPadding.pop_style_var()

    prof_primary, prof_secondary = "", ""
    prof_primary = ProfessionShort(
        account_data.PlayerProfession).name if account_data.PlayerProfession != 0 else ""
    prof_secondary = ProfessionShort(
        account_data.PlayerSecondaryProfession).name if account_data.PlayerSecondaryProfession != 0 else ""
    win_size = PyImGui.get_window_size()
    win_pos = PyImGui.get_window_pos()

    text_pos = (win_pos[0] + 25, win_pos[1] - 23 +
                7) if style.Theme == StyleTheme.Guild_Wars else (win_pos[0] + 25, win_pos[1] + 7)

    PyImGui.push_clip_rect(
        win_pos[0], win_pos[1] - 20, win_size[0] - 30, 50, False)
    ImGui.push_font("Regular", 13)
        
    name = get_display_name(account_data)

    PyImGui.draw_list_add_text(text_pos[0], text_pos[1], style.Text.color_int,
                               f"{prof_primary}{("/" if prof_secondary else "")}{prof_secondary}{account_data.PlayerLevel} {name}")
    ImGui.pop_font()
    PyImGui.pop_clip_rect()

    pos = window.window_pos
    collapsed = window.collapse
    
    if open and window.open and not window.collapse:
        if style.Theme == StyleTheme.Guild_Wars:
            PyImGui.spacing()

        avail = PyImGui.get_content_region_avail()

        height = 28 if settings.ShowHeroSkills else 0
        height += 28 if settings.ShowHeroBars else 0
        height += 4 if settings.ShowHeroBars and settings.ShowHeroSkills else 0

        if height > 0:
            if ImGui.begin_child("##bars" + account_data.AccountEmail, (225, height)):
                curr_avail = PyImGui.get_content_region_avail()
                if settings.ShowHeroBars:
                    health_clicked = draw_health_bar(curr_avail[0], 13, account_data.PlayerMaxHP,
                                    account_data.PlayerHP, account_data.PlayerHealthRegen)
                    PyImGui.set_cursor_pos_y(PyImGui.get_cursor_pos_y() - 4)
                    energy_clicked = draw_energy_bar(curr_avail[0], 13, account_data.PlayerMaxEnergy,
                                                       account_data.PlayerEnergy, account_data.PlayerEnergyRegen)
                    if health_clicked or energy_clicked:
                        ConsoleLog("HERO AI", f"Switching target to hero {account_data.CharacterName}...")
                        
                        if GLOBAL_CACHE.Map.GetMapID() == account_data.MapID:
                            GLOBAL_CACHE.Player.ChangeTarget(account_data.PlayerID)
                            
                if settings.ShowHeroSkills:
                    if settings.ShowHeroBars:
                        PyImGui.set_cursor_pos_y(PyImGui.get_cursor_pos_y() - 4)
                    
                    draw_skill_bar(28, account_data, cached_data, messages)

            ImGui.end_child()

        if (settings.ShowHeroBars or settings.ShowHeroSkills) and settings.ShowHeroButtons:
            PyImGui.same_line(0, 2)
            
        if settings.ShowHeroButtons:
            draw_buttons(account_data, cached_data, messages, 28)

        draw_buffs_bar(account_data, win_pos, win_size, messages, 28)
        window.process_window()
    
    collapsed = PyImGui.is_window_collapsed()
    pos = PyImGui.get_window_pos()
    
    window.process_window()
    
    if window.collapse != collapsed or window.window_pos != pos:
        window.window_pos = pos
        window.collapse = collapsed if style.Theme != StyleTheme.Guild_Wars else window.collapse
            
        if Console.is_window_active():
            settings.HeroPanelPositions[account_data.AccountEmail] = (int(pos[0]), int(pos[1]), window.collapse)
            settings.save_settings()
        
    window.end()
    
    if flag_account == account_data.AccountEmail and flag_account:    
        flag_hero(account_data, cached_data)      
        
    pass  # Implementation of hero panel drawing logic goes here
