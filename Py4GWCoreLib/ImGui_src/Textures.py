from dataclasses import dataclass
from enum import IntEnum, Enum, IntFlag, auto
from typing import Optional
from .types import TEXTURE_FOLDER, MINIMALUS_FOLDER, StyleTheme
from ..Overlay import Overlay
import os

class TextureState(IntEnum):
    Normal = 0
    Hovered = 1
    Active = 2
    Disabled = 3
    
class TextureSliceMode(IntEnum):
    FULL = 1
    THREE_HORIZONTAL = 3
    THREE_VERTICAL = 4
    NINE = 9

class RegionFlags(IntFlag):
    NONE   = 0
    LEFT   = auto()
    CENTER = auto()
    RIGHT  = auto()
    TOP    = auto()
    MIDDLE = auto()
    BOTTOM = auto()
    FULL   = auto()

class UVRegion:
    __slots__ = ("x0", "y0", "x1", "y1")

    def __init__(self, x0: float, y0: float, x1: float, y1: float):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1

    def uv0(self) -> tuple[float, float]:
        return (self.x0, self.y0)

    def uv1(self) -> tuple[float, float]:
        return (self.x1, self.y1)

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)

class GameTexture:
    """
    Unified class supporting:
    - Atlas state maps (Normal, Hovered, Active, Disabled)
    - 1/3/9-slice scalable rendering
    - Precomputed UVs for all states
    """

    def __init__(
        self,
        texture: str,
        texture_size: tuple[float, float],
        mode: TextureSliceMode = TextureSliceMode.NINE,
        element_size: Optional[tuple[float, float]] = None,
        margin: Optional[tuple[float, float]] = None,
        state_map: Optional[dict[TextureState, tuple[float, float]]] = None,
    ):
        self.texture = texture
        self.tex_width, self.tex_height = texture_size
        self.mode = mode
        self.element_width, self.element_height = element_size if element_size else (texture_size[0], texture_size[1])

        self.margin_x = margin[0] if margin else self._compute_margin(self.element_height)
        self.margin_y = margin[1] if margin else self._compute_margin(self.element_height)

        # atlas state → pixel offset
        self.state_map = state_map or {
            TextureState.Normal: (0, 0),
        }

        # per-state, precomputed uv maps for all regions
        self.state_uvs: dict[TextureState, dict[RegionFlags, Optional[UVRegion]]] = {}

        # build all precomputed UVs once
        self._build_all_state_uvs()

    # --- helpers ---------------------------------------------------------------

    def _compute_margin(self, size: float) -> float:
        if size <= 32:
            return 10.0
        elif size >= 64:
            return 40.0
        else:
            return 10.0 + (size - 32.0) * (30.0 / 32.0)

    def _uv(self, x0: float, y0: float, x1: float, y1: float) -> UVRegion:
        """Convert absolute pixel coordinates to normalized UVs."""
        return UVRegion(x0 / self.tex_width, y0 / self.tex_height, x1 / self.tex_width, y1 / self.tex_height)

    def _build_state_uv(self, offset_x: float, offset_y: float) -> dict[RegionFlags, Optional[UVRegion]]:
        """Build UV regions for one atlas state."""
        sx, sy, w, h = self.margin_x, self.margin_y, self.element_width, self.element_height
        ox, oy = offset_x, offset_y
        uvs: dict[RegionFlags, Optional[UVRegion]] = {}
        
        if self.mode == TextureSliceMode.FULL:
            uvs[RegionFlags.FULL] = self._uv(ox, oy, ox + w, oy + h)

        elif self.mode == TextureSliceMode.THREE_HORIZONTAL:
            uvs[RegionFlags.LEFT] = self._uv(ox, oy, ox + sx, oy + h)
            uvs[RegionFlags.CENTER] = self._uv(ox + sx, oy, ox + w - sx, oy + h)
            uvs[RegionFlags.RIGHT] = self._uv(ox + w - sx, oy, ox + w, oy + h)

        elif self.mode == TextureSliceMode.THREE_VERTICAL:
            uvs[RegionFlags.TOP] = self._uv(ox, oy, ox + w, oy + sy)
            uvs[RegionFlags.MIDDLE] = self._uv(ox, oy + sy, ox + w, oy + h - sy)
            uvs[RegionFlags.BOTTOM] = self._uv(ox, oy + h - sy, ox + w, oy + h)

        elif self.mode == TextureSliceMode.NINE:
            uvs[RegionFlags.TOP | RegionFlags.LEFT] = self._uv(ox, oy, ox + sx, oy + sy)
            uvs[RegionFlags.TOP | RegionFlags.CENTER] = self._uv(ox + sx, oy, ox + w - sx, oy + sy)
            uvs[RegionFlags.TOP | RegionFlags.RIGHT] = self._uv(ox + w - sx, oy, ox + w, oy + sy)
            uvs[RegionFlags.MIDDLE | RegionFlags.LEFT] = self._uv(ox, oy + sy, ox + sx, oy + h - sy)
            uvs[RegionFlags.MIDDLE | RegionFlags.CENTER] = self._uv(ox + sx, oy + sy, ox + w - sx, oy + h - sy)
            uvs[RegionFlags.MIDDLE | RegionFlags.RIGHT] = self._uv(ox + w - sx, oy + sy, ox + w, oy + h - sy)
            uvs[RegionFlags.BOTTOM | RegionFlags.LEFT] = self._uv(ox, oy + h - sy, ox + sx, oy + h)
            uvs[RegionFlags.BOTTOM | RegionFlags.CENTER] = self._uv(ox + sx, oy + h - sy, ox + w - sx, oy + h)
            uvs[RegionFlags.BOTTOM | RegionFlags.RIGHT] = self._uv(ox + w - sx, oy + h - sy, ox + w, oy + h)
        return uvs

    def _build_all_state_uvs(self):
        """Precompute all per-state UV sets."""
        for state, (ox, oy) in self.state_map.items():
            self.state_uvs[state] = self._build_state_uv(ox, oy)

    # --- drawing ---------------------------------------------------------------

    def draw_in_drawlist(
        self,
        pos: tuple[float, float],
        size: tuple[float, float],
        state: TextureState = TextureState.Normal,
        tint: tuple[int, int, int, int] = (255, 255, 255, 255),
    ):
        """Draw the precomputed state UVs with slicing."""
        from .ImGuisrc import ImGui

        x, y = pos
        w, h = size
        sx, sy = self.margin_x, self.margin_y
        uvs = self.state_uvs.get(state) or self.state_uvs[TextureState.Normal]
        
        if not uvs:
            return  # no UVs to draw
        
        def draw(region: RegionFlags, dx: float, dy: float, dw: float, dh: float):
            uv_region = uvs.get(region, None)
            if uv_region:
                ImGui.DrawTextureInDrawList(
                    pos=(x + dx, y + dy),
                    size=(dw, dh),
                    texture_path=self.texture,
                    uv0=uv_region.uv0(),
                    uv1=uv_region.uv1(),
                    tint=tint
                )

        if self.mode == TextureSliceMode.FULL:
            draw(RegionFlags.FULL, 0, 0, w, h)

        elif self.mode == TextureSliceMode.THREE_HORIZONTAL:
            lw, rw = sx, sx
            mw = max(0, w - lw - rw)
            draw(RegionFlags.LEFT, 0, 0, lw, h)
            draw(RegionFlags.CENTER, lw, 0, mw, h)
            draw(RegionFlags.RIGHT, lw + mw, 0, rw, h)

        elif self.mode == TextureSliceMode.THREE_VERTICAL:
            th, bh = sy, sy
            mh = max(0, h - th - bh)
            draw(RegionFlags.TOP, 0, 0, w, th)
            draw(RegionFlags.MIDDLE, 0, th, w, mh)
            draw(RegionFlags.BOTTOM, 0, th + mh, w, bh)

        elif self.mode == TextureSliceMode.NINE:
            cw, ch = sx, sy
            mw, mh = max(0, w - 2 * cw), max(0, h - 2 * ch)

            draw(RegionFlags.TOP | RegionFlags.LEFT, 0, 0, cw, ch)
            draw(RegionFlags.TOP | RegionFlags.CENTER, cw, 0, mw, ch)
            draw(RegionFlags.TOP | RegionFlags.RIGHT, cw + mw, 0, cw, ch)
            draw(RegionFlags.MIDDLE | RegionFlags.LEFT, 0, ch, cw, mh)
            draw(RegionFlags.MIDDLE | RegionFlags.CENTER, cw, ch, mw, mh)
            draw(RegionFlags.MIDDLE | RegionFlags.RIGHT, cw + mw, ch, cw, mh)
            draw(RegionFlags.BOTTOM | RegionFlags.LEFT, 0, ch + mh, cw, ch)
            draw(RegionFlags.BOTTOM | RegionFlags.CENTER, cw, ch + mh, mw, ch)
            draw(RegionFlags.BOTTOM | RegionFlags.RIGHT, cw + mw, ch + mh, cw, ch)

class MapTexture:
    """
    Represents a UI element with multiple states (Normal, Hovered, etc.)
    mapped to different regions of a texture atlas.
    """

    def __init__(
        self,
        texture: str,
        texture_size: tuple[float, float],
        size: tuple[float, float],
        normal: tuple[float, float] = (0, 0),
        hovered: tuple[float, float] | None = None,
        active: tuple[float, float] | None = None,
        disabled: tuple[float, float] | None = None,
    ):
        self.texture = texture
        self.texture_size = texture_size
        self.size = size
        self.width, self.height = size

        self.normal_offset = self._make_uv(normal)
        self.hovered_offset = self._make_uv(hovered) if hovered else (0, 0, 1, 1)
        self.active_offset = self._make_uv(active) if active else (0, 0, 1, 1)
        self.disabled_offset = self._make_uv(disabled) if disabled else (0, 0, 1, 1)

    def _make_uv(self, pos: tuple[float, float]) -> tuple[float, float, float, float]:
        x, y = pos
        w, h = self.texture_size
        sx, sy = self.size
        return x / w, y / h, (x + sx) / w, (y + sy) / h

    def get_uv(self, state: TextureState) -> tuple[float, float, float, float]:
        match state:
            case TextureState.Normal: return self.normal_offset
            case TextureState.Hovered: return self.hovered_offset
            case TextureState.Active: return self.active_offset
            case TextureState.Disabled: return self.disabled_offset
        return self.normal_offset  # Fallback in case of unexpected state

    def draw_in_drawlist(
        self,
        pos: tuple[float, float],
        size: tuple[float, float],
        state: TextureState = TextureState.Normal,
        tint=(255, 255, 255, 255)
    ):
        from .ImGuisrc import ImGui
        uv = self.get_uv(state)
        ImGui.DrawTextureInDrawList(
            pos=pos,
            size=size,
            texture_path=self.texture,
            uv0=uv[:2],
            uv1=uv[2:],
            tint=tint,
        )

class ThemeTexture:
    PlaceHolderTexture = MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "missing_texture.png"),
        texture_size = (1, 1),
        size = (1, 1),
        normal=(0, 0)
    )

    def __init__(
        self,
        *args: tuple[StyleTheme, GameTexture | MapTexture],
    ):
        self.textures: dict[StyleTheme, GameTexture | MapTexture] = {}

        for theme, texture in args:
            self.textures[theme] = texture

    def get_texture(self, theme: StyleTheme | None = None) -> GameTexture | MapTexture:
        from .ImGuisrc import ImGui
        theme = theme or ImGui.get_style().Theme
        return self.textures.get(theme, ThemeTexture.PlaceHolderTexture)

class ThemeTextures(Enum):  
    Empty_Pixel = MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "empty_pixel.png"),
        texture_size = (1, 1),
        size = (1, 1),
        normal=(0, 0)
    )

    TravelCursor = MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "Cursor", "travel_cursor.png"),
        texture_size=(32, 32),
        size=(32, 32),
        normal=(0, 0)
    )

    ScrollGrab_Top = GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_scrollgrab.png"),
        texture_size=(16, 16),
    )

    ScrollGrab_Middle = MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_scrollgrab.png"),
        texture_size=(16, 16),
        size=(16, 2),
        normal=(0, 7)
    )

    Scroll_Bg = MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_scroll_background.png"),
        texture_size=(16, 16),
        size=(16, 16),
        normal=(0, 0)
    )

    ScrollGrab_Bottom = GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_scrollgrab.png"),
        texture_size=(16, 16), 
    )            

    RightButton = MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_left_right.png"),
        texture_size=(64, 16),
        size=(14, 16),
        normal=(1, 0)
    )

    LeftButton = MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_left_right.png"),
        texture_size=(64, 16),
        size=(14, 16),
        normal = (17, 0),
        active = (49, 0),
    )

    Horizontal_ScrollGrab_Top = MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_horizontal_scrollgrab.png"),
        texture_size=(16, 16),
        size=(7, 16),
        normal=(0, 0),
    )

    Horizontal_ScrollGrab_Middle = MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_horizontal_scrollgrab.png"),
        texture_size=(16, 16),
        size=(2, 16),
        normal=(7, 0)
    )

    Horizontal_ScrollGrab_Bottom = MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_horizontal_scrollgrab.png"),
        texture_size=(16, 16),
        size=(7, 16),
        normal=(9, 0),   
    )   

    Horizontal_Scroll_Bg = MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_horizontal_scroll_background.png"),
        texture_size=(16, 16),
        size=(16, 16),
        normal=(0, 0)
    )                         

    CircleButtons = MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_profession_circle_buttons.png"),
        texture_size=(256, 128),
        size=(32, 32),
        active=(192, 96),
        normal=(224, 96)
    )

    UpButton = MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_up_down.png"),
        texture_size=(64, 16),
        size=(14, 16),
        normal=(1, 0)
    )

    DownButton = MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_up_down.png"),
        texture_size=(64, 16),
        size=(14, 16),
        normal = (17, 0),
        active = (49, 0),
    )

    Combo_Arrow = ThemeTexture(
        (StyleTheme.Minimalus, GameTexture(
            texture=os.path.join(MINIMALUS_FOLDER, "ui_combo_arrow.png"),
            texture_size=(128, 32),
            mode=TextureSliceMode.FULL,
        )),

        (StyleTheme.Guild_Wars, GameTexture(
            texture=os.path.join(TEXTURE_FOLDER, "ui_combo_arrow.png"),
            texture_size=(128, 32),
            mode=TextureSliceMode.FULL,
        ))
    )

    Combo_Background = ThemeTexture(
        (StyleTheme.Minimalus, GameTexture(
            texture=os.path.join(MINIMALUS_FOLDER, "ui_combo_background.png"),
            texture_size=(128, 32),
            margin=(36, 8),
        )),

        (StyleTheme.Guild_Wars, GameTexture(
            texture=os.path.join(
                TEXTURE_FOLDER, "ui_combo_background.png"),
            texture_size=(128, 32),
            margin=(36, 8),
        ))
    )

    Combo_Frame = ThemeTexture(
        (StyleTheme.Minimalus, GameTexture(
            texture=os.path.join(MINIMALUS_FOLDER, "ui_combo_frame.png"),
            texture_size=(128, 32),
            margin=(36, 8),
        )),

        (StyleTheme.Guild_Wars, GameTexture(
            texture=os.path.join(TEXTURE_FOLDER, "ui_combo_frame.png"),
            texture_size=(128, 32),
            margin=(36, 8),
        ))
    )
    ArrowCollapsed = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_arrow_collapse_expand.png"),
        texture_size = (32, 16),
        size = (16, 16),
        normal = (16, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_arrow_collapse_expand.png"),
        texture_size = (32, 16),
        size = (16, 16),
        normal = (16, 0),
    )),
    )  

    ArrowExpanded = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_arrow_collapse_expand.png"),
        texture_size = (32, 16),
        size = (16, 16),
        normal = (0, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_arrow_collapse_expand.png"),
        texture_size = (32, 16),
        size = (16, 16),
        normal = (0, 0),
    )),
    )    
    
    CollapsingHeader_Background = ThemeTexture(
        (StyleTheme.Minimalus, GameTexture(
            texture=os.path.join(MINIMALUS_FOLDER, "ui_collapsing_header_background.png"),
            texture_size=(128, 32),
        )),

        (StyleTheme.Guild_Wars, GameTexture(
            texture=os.path.join(
                TEXTURE_FOLDER, "ui_collapsing_header_background.png"),
            texture_size=(128, 32),
        ))
    )

    CollapsingHeader_Frame = ThemeTexture(
        (StyleTheme.Minimalus, GameTexture(
            texture=os.path.join(MINIMALUS_FOLDER, "ui_collapsing_header_frame.png"),
            texture_size=(128, 32),
        )),

        (StyleTheme.Guild_Wars, GameTexture(
            texture=os.path.join(TEXTURE_FOLDER, "ui_collapsing_header_frame.png"),
            texture_size=(128, 32),
        ))
    )

    Button_Frame = ThemeTexture(
        (StyleTheme.Minimalus, GameTexture(
            texture=os.path.join(MINIMALUS_FOLDER, "ui_button_frame.png"),
            texture_size=(32, 32),
        )),

        (StyleTheme.Guild_Wars, GameTexture(
            texture=os.path.join(TEXTURE_FOLDER, "ui_button_frame.png"),
            texture_size=(32, 32),
        ))
    )

    Button_Background = ThemeTexture(
        (StyleTheme.Minimalus, GameTexture(
            texture=os.path.join(MINIMALUS_FOLDER, "ui_button_background.png"),
            texture_size=(32, 32),
        )),

        (StyleTheme.Guild_Wars, GameTexture(
            texture=os.path.join(TEXTURE_FOLDER, "ui_button_background.png"),
            texture_size=(32, 32),
        ))
    )

    CheckBox_Unchecked = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_checkbox.png"),
        texture_size = (128, 32),
        size = (17, 17),
        normal=(2, 2),
        active=(23, 2),
        disabled=(107, 2),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_checkbox.png"),
        texture_size = (128, 32),
        size = (17, 17),
        normal=(2, 2),
        active=(23, 2),
        disabled=(107, 2),
    )),
    )

    CheckBox_Checked = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_checkbox.png"),
        texture_size = (128, 32),
        size = (17, 18),
        normal=(44, 1),
        active=(65, 1),
        disabled=(86, 1),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_checkbox.png"),
        texture_size = (128, 32),
        size = (17, 18),
        normal=(44, 1),
        active=(65, 1),
        disabled=(86, 1),
    )),
    )

    SliderBar = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_slider_bar.png"),
        texture_size=(32, 16),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_slider_bar.png"),
        texture_size=(32, 16),
    )),
    )

    SliderGrab = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_slider_grab.png"),
        texture_size=(32, 32),
        size=(18, 18),
        normal=(7, 7)
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_slider_grab.png"),
        texture_size=(32, 32),
        size=(18, 18),
        normal=(7, 7)
    )),
    )

    Input_Inactive = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_input_inactive.png"),
        texture_size=(32, 16),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_input_inactive.png"),
        texture_size=(32, 16),
    )),
    )

    Input_Active = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_input_active.png"),
        texture_size=(32, 16),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_input_active.png"),
        texture_size=(32, 16),
    )),
    )

    Expand = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_collapse_expand.png"),
        texture_size = (32, 32),
        size = (13, 12),
        normal = (0, 3),
        hovered = (16, 3),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_collapse_expand.png"),
        texture_size = (32, 32),
        size = (12, 12),
        normal = (1, 3),
        hovered = (17, 3),
    )),
    )

    Collapse = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_collapse_expand.png"),
        texture_size = (32, 32),
        size = (13, 12),
        normal = (0, 19),
        hovered = (16, 19),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_collapse_expand.png"),
        texture_size = (32, 32),
        size = (12, 12),
        normal = (1, 19),
        hovered = (17, 19),
    )),
    )        

    Tab_Frame = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_tab_bar_frame.png"),
        texture_size=(32, 32),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_tab_bar_frame.png"),
        texture_size=(32, 32),
    )),
    )
    
    Tab_Active = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_tab_active.png"),
        texture_size=(32, 32),
        margin=(8, 0),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_tab_active.png"),
        texture_size=(32, 32),
        margin=(8, 0),
    )),
    )

    Tab_Inactive = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_tab_inactive.png"),
        texture_size=(32, 32),
        margin=(8, 0),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_tab_inactive.png"),
        texture_size=(32, 32),
        margin=(8, 0),
    )),
    )

    Quest_Objective_Bullet_Point = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_quest_objective_bullet_point.png"),
        texture_size = (32, 16),
        size = (13, 13),
        normal=(0, 0),
        active=(13, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_quest_objective_bullet_point.png"),
        texture_size = (32, 16),
        size = (13, 13),
        normal=(0, 0),
        active=(13, 0),
    )),
    )

    Pip_Regen = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_pips.png"),
        texture_size = (32, 16),
        size = (10, 16),
        normal=(10, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_pips.png"),
        texture_size = (32, 16),
        size = (10, 16),
        normal=(10, 0),
    )),
    )

    Pip_Degen = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_pips.png"),
        texture_size = (32, 16),
        size = (10, 16),
        normal=(0, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_pips.png"),
        texture_size = (32, 16),
        size = (10, 16),
        normal=(0, 0),
    )),
    )

    Close_Button = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_close_button_atlas.png"),
        texture_size = (64, 16),
        size = (12, 12),
        normal=(1, 1),
        hovered=(17, 1),
        active=(33, 1),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_close_button_atlas.png"),
        texture_size = (64, 16),
        size = (12, 12),
        normal=(1, 1),
        hovered=(17, 1),
        active=(33, 1),
    )),
    )

    Title_Bar = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_titlebar.png"),
        texture_size=(128, 32),
        margin=(18, 0),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_titlebar.png"),
        texture_size=(128, 32),
        margin=(18, 0),
    )),
    )
    
    Title_Bar_Collapsed = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_titlebar_collapsed.png"),
        texture_size=(128, 32),
        margin=(18, 0),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_titlebar_collapsed.png"),
        texture_size=(128, 32),
        margin=(18, 0),
    )),
    )

    Window = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_window.png"),
        texture_size=(128, 128),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_window.png"),
        texture_size=(128, 128),
    )),
    )
    
    Window_NoResize_NoTitleBar = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_window_notitlebar_noresize.png"),
        texture_size=(128, 128),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_window_notitlebar_noresize.png"),
        texture_size=(128, 128),
    )),
    )

    Window_NoResize = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_window_noresize.png"),
        texture_size=(128, 128),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_window_noresize.png"),
        texture_size=(128, 128),
    )),
    )

    Window_NoTitleBar = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_window_notitlebar.png"),
        texture_size=(128, 128),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_window_notitlebar.png"),
        texture_size=(128, 128),
    )),
    )

    Window_NoResize_NoTitlebar = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_window.png"),
        texture_size=(128, 128),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_window.png"),
        texture_size=(128, 128),
    )),
    )





    Window_Frame_Top = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_window.png"),
        texture_size=(128, 128),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_window.png"),
        texture_size=(128, 128),
    )),
    )

    Window_Frame_Center = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_window.png"),
        texture_size=(128, 128),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_window.png"),
        texture_size=(128, 128),
    )),
    )

    Window_Frame_Bottom = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_window.png"),
        texture_size=(128, 128),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_window.png"),
        texture_size=(128, 128),
    )),
    )

    Window_Frame_Top_NoTitleBar = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_window_no_titlebar.png"),
        texture_size=(128, 128),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_window_no_titlebar.png"),
        texture_size=(128, 128),
    )),
    )

    Window_Frame_Bottom_No_Resize = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_window_noresize.png"),
        texture_size=(128, 128),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_window_noresize.png"),
        texture_size=(128, 128),
    )),
    )


    Separator = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_separator.png"),
        texture_size = (32, 4),
        size = (32, 4),
        normal = (0, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_separator.png"),
        texture_size = (32, 4),
        size = (32, 4),
        normal = (0, 0),
    )),
    )

    ProgressBarFrame = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_progressbar_frame.png"),
        texture_size=(16, 16),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_progressbar_frame.png"),
        texture_size=(16, 16),
    )),
    )
    
    HealthBarFill = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER,"Progressbar", "ui_progress_health.png"),
        texture_size=(16, 16),
        size=(3, 16),
        normal= (0, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER,"Progressbar", "ui_progress_health.png"),
        texture_size=(16, 16),
        size=(3, 16),
        normal= (0, 0),
    )),
    )
    
    HealthBarCursor = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER,"Progressbar", "ui_progress_health.png"),
        texture_size=(16, 16),
        size=(4, 16),
        normal= (3, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "Progressbar", "ui_progress_health.png"),
        texture_size=(16, 16),
        size=(4, 16),
        normal= (3, 0),
    )),
    )
    
    HealthBarEmpty = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER,"Progressbar", "ui_progress_health.png"),
        texture_size=(16, 16),
        size=(9, 16),
        normal= (7, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER,"Progressbar", "ui_progress_health.png"),
        texture_size=(16, 16),
        size=(9, 16),
        normal= (7, 0),
    )),
    )
    
    EnergyBarFill = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER,"Progressbar", "ui_progress_energy.png"),
        texture_size=(16, 16),
        size=(3, 16),
        normal= (0, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER,"Progressbar", "ui_progress_energy.png"),
        texture_size=(16, 16),
        size=(3, 16),
        normal= (0, 0),
    )),
    )
    
    EnergyBarCursor = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER,"Progressbar", "ui_progress_energy.png"),
        texture_size=(16, 16),
        size=(4, 16),
        normal= (3, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "Progressbar", "ui_progress_energy.png"),
        texture_size=(16, 16),
        size=(4, 16),
        normal= (3, 0),
    )),
    )
    
    EnergyBarEmpty = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER,"Progressbar", "ui_progress_energy.png"),
        texture_size=(16, 16),
        size=(9, 16),
        normal= (7, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER,"Progressbar", "ui_progress_energy.png"),
        texture_size=(16, 16),
        size=(9, 16),
        normal= (7, 0),
    )),
    )
    
    ProgressBarProgressCursor = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_progress_highlight.png"),
        texture_size=(16, 16),
        size= (16, 16),
        normal = (0, 0)
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_progress_highlight.png"),
        texture_size=(16, 16),
        size= (16, 16),
        normal = (0, 0)
    )),
    )

    ProgressBarProgress = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_progress_default.png"),
        texture_size=(16, 16),
        size=(6, 16),
        normal= (0, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_progress_default.png"),
        texture_size=(16, 16),
        size=(6, 16),
        normal= (0, 0),
    )),
    )

    ProgressBarBackground = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_progress_default.png"),
        texture_size=(16, 16),
        size=(6, 16),
        normal= (6, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_progress_default.png"),
        texture_size=(16, 16),
        size=(6, 16),
        normal= (6, 0),
    )),
    )   

    BulletPoint = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_bullet_point.png"),
        texture_size = (16, 16),
        size = (16, 16),
        normal = (0, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_bullet_point.png"),
        texture_size = (16, 16),
        size = (16, 16),
        normal = (0, 0),
    )),
    )   

    #Skill
    Skill_Slot_Empty = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_empty_skill_slot.png"),
        texture_size = (64, 64),
        size = (56, 56),
        normal = (4, 4),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_empty_skill_slot.png"),
        texture_size = (64, 64),
        size = (56, 56),
        normal = (4, 4),
    )),
    )
    
    Skill_Frame = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_skill_frames.png"),
        texture_size = (256, 256),
        size = (56, 56),
        normal = (0, 0),
        active = (56, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_skill_frames.png"),
        texture_size = (256, 256),
        size = (56, 56),
        normal = (0, 0),
        active = (56, 0),
    )),
    )
    
    Effect_Frame_Skill = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_skill_frames.png"),
        texture_size = (256, 256),
        size = (56, 56),
        normal = (112, 0),
        active= (168, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_skill_frames.png"),
        texture_size = (256, 256),
        size = (56, 56),
        normal = (112, 0),
        active= (168, 0),
    )),
    )
    
    Effect_Frame_Condition = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_skill_frames.png"),
        texture_size = (256, 256),
        size = (56, 56),
        normal = (0, 56),
        active = (56, 56),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_skill_frames.png"),
        texture_size = (256, 256),
        size = (56, 56),
        normal = (0, 56),
        active = (56, 56),
    )),
    )
    
    Effect_Frame_Enchantment = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_skill_frames.png"),
        texture_size = (256, 256),
        size = (56, 56),
        normal = (112, 56),
        active = (168, 56),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_skill_frames.png"),
        texture_size = (256, 256),
        size = (56, 56),
        normal = (112, 56),
        active = (168, 56),
    )),
    )

    Effect_Frame_Hex = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_skill_frames.png"),
        texture_size = (256, 256),
        size = (56, 56),
        normal = (0, 112),
        active = (56, 112),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_skill_frames.png"),
        texture_size = (256, 256),
        size = (56, 56),
        normal = (0, 112),
        active = (56, 112),
    )),
    )
    
    Effect_Frame_Blue = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "ui_skill_frames.png"),
        texture_size = (256, 256),
        size = (56, 56),
        normal = (112, 112),
        active= (168, 112),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_skill_frames.png"),
        texture_size = (256, 256),
        size = (56, 56),
        normal = (112, 112),
        active= (168, 112),
    )),
    )

    Dropdown_Button_Base = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_dropdown_button.png"),
        texture_size = (64, 32),
        size = (21, 21),
        normal = (1, 1),
        active= (25, 1),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_dropdown_button.png"),
        texture_size = (64, 32),
        size = (21, 21),
        normal = (1, 1),
        active= (25, 1),
    )),
    )
    
    Hero_Panel_Toggle_Base = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_hero_panel_toggle.png"),
        texture_size = (64, 32),
        size = (17, 17),
        normal = (1, 2),
        active= (22, 2),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_hero_panel_toggle.png"),
        texture_size = (64, 32),
        size = (17, 17),
        normal = (1, 2),
        active= (22, 2),
    )),
    )
    
    Check = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_check_cancel.png"),
        texture_size = (64, 64),
        size = (32, 32),
        normal = (0, 0),
        hovered= (32, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_check_cancel.png"),
        texture_size = (64, 64),
        size = (32, 32),
        normal = (0, 0),
        hovered= (32, 0),
    )),
    )
    
    Cancel = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_check_cancel.png"),
        texture_size = (64, 64),
        size = (32, 32),
        normal = (0, 32),
        hovered= (32, 32),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_check_cancel.png"),
        texture_size = (64, 64),
        size = (32, 32),
        normal = (0, 32),
        hovered= (32, 32),
    )),
    )
    
    TemplateAction = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_template_actions.png"),
        texture_size = (128, 64),
        size = (21, 21),
        hovered = (1, 1),
        normal= (25, 1),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_template_actions.png"),
        texture_size = (128, 64),
        size = (21, 21),
        hovered = (1, 1),
        normal= (25, 1),
    )),
    )
    
    TemplateLoad = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_template_actions.png"),
        texture_size = (128, 64),
        size = (21, 21),
        hovered = (49, 1),
        normal= (74, 1),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_template_actions.png"),
        texture_size = (128, 64),
        size = (21, 21),
        hovered = (49, 1),
        normal= (74, 1),
    )),
    )
    
    TemplateSave = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_template_actions.png"),
        texture_size = (128, 64),
        size = (21, 21),
        hovered = (97, 1),
        normal= (2, 25),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_template_actions.png"),
        texture_size = (128, 64),
        size = (21, 21),
        hovered = (97, 1),
        normal= (2, 25),
    )),
    )
    
    TemplateManage = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_template_actions.png"),
        texture_size = (128, 64),
        size = (21, 21),
        hovered = (25, 25),
        normal= (50, 25),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_template_actions.png"),
        texture_size = (128, 64),
        size = (21, 21),
        hovered = (25, 25),
        normal= (50, 25),
    )),
    )
    
    TemplateCode = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_template_actions.png"),
        texture_size = (128, 64),
        size = (22, 22),
        hovered = (72, 23),
        normal= (97, 23),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_template_actions.png"),
        texture_size = (128, 64),
        size = (22, 22),
        hovered = (72, 23),
        normal= (97, 23),
    )),
    )
    
    HeroPanelButtonBase = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_aggression.png"),
        texture_size = (128, 64),
        size = (27, 29),
        normal= (67, 34),
        active= (99, 34),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_aggression.png"),
        texture_size = (128, 64),
        size = (27, 29),
        normal= (67, 34),
        active= (99, 34),
    )),
    )

    HeaderLabelBackground = ThemeTexture(
    (StyleTheme.Minimalus,  GameTexture(
        texture = os.path.join(MINIMALUS_FOLDER, "header_label.png"),
        texture_size = (128, 32),
    )),
    (StyleTheme.Guild_Wars,  GameTexture(
        texture = os.path.join(TEXTURE_FOLDER, "header_label.png"),
        texture_size = (128, 32),
    )),
    )
    
    AdrenalineBarFill = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_adrenaline_effect.png"),
        texture_size = (64, 64),
        size = (64, 64),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_adrenaline_effect.png"),
        texture_size = (64, 64),
        size = (64, 64),
    )),
    )
    
    Inventory_Slots = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_iventory_slots.png"),
        texture_size = (128, 128),
        size = (52, 64),
        normal= (0, 0),
        active = (0, 64),      
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_iventory_slots.png"),
        texture_size = (128, 128),
        size = (52, 64),
        normal= (0, 0),
        active = (0, 64),      
    )),
    )
    
    Inventory_Slot_Blue = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_iventory_slots.png"),
        texture_size = (128, 128),
        size = (52, 64),  
        normal= (52, 0),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_iventory_slots.png"),
        texture_size = (128, 128),
        size = (52, 64),     
        normal= (52, 0),
    )),
    )
    
    Inventory_Slot_Red = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_iventory_slots.png"),
        texture_size = (128, 128),
        size = (52, 64),
        normal= (52, 64),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "ui_iventory_slots.png"),
        texture_size = (128, 128),
        size = (52, 64),        
        normal= (52, 64),
    )),
    )
    
    MoraleBoost = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "morale_boost_effect.png"),
        texture_size = (64, 64),
        size = (64, 64),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "morale_boost_effect.png"),
        texture_size = (64, 64),
        size = (64, 64),
    )),
    )
    
    DeathPenalty = ThemeTexture(
    (StyleTheme.Minimalus,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "death_penalty_effect.png"),
        texture_size = (64, 64),
        size = (64, 64),
    )),
    (StyleTheme.Guild_Wars,  MapTexture(
        texture = os.path.join(TEXTURE_FOLDER, "death_penalty_effect.png"),
        texture_size = (64, 64),
        size = (64, 64),
    )),
    )
