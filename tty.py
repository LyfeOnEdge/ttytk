import io, math, time, random

# import tkinter as tk
from direct.showbase.ShowBase import (
    ShowBase,
    WindowProperties,
    ClockObject,
    CardMaker,
    SamplerState,
    Texture,
    TextureStage,
)
from pandac.PandaModules import loadPrcFileData
from PIL import Image, ImageTk, ImageOps
from numpy import array, asarray, zeros, uint8, full

# Disable window resize
loadPrcFileData("", "win-fixed-size 1")
loadPrcFileData("", "sync-video False")

VERSION = "0.0"
CHAR_SIZE = 8  # Square, In pixels
TERMINAL_COLUMNS = 40
TERMINAL_ROWS = 20
WINDOW_BORDER = 10  # Border between terminal and outer edge of window
WINDOW_BORDER_COLOR = (0.5, 0.5, 0.5)
RENDER_SCALE = 3  # Scales the terminal
BACKGROUND_COLOR = (0, 0, 0, 0)

# Map corresponding to the tileset image
CHARACTER_LAYOUT = [
    [" ", "!", '"', "#", "$", "%", "&", "'", "(", ")", "*", "+", ",", "-", ".", "/"],
    ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ":", ";", "<", "=", ">", "?"],
    ["@", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O"],
    ["P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "[", "\\", "]", "^", "_"],
    ["`", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o"],
    ["p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "{", "|", "}", "~", "\t"],
]
CHAR_MAP_STRING = ""
for r in CHARACTER_LAYOUT:
    for c in r:
        CHAR_MAP_STRING += f" {c}"
    CHAR_MAP_STRING += "\n"
CHAR_MAP_STRING = CHAR_MAP_STRING.rstrip("\n")
# Generate a lookup table to easily find the position in the map from a char
CHARACTER_MAP = {}
for y in range(len(CHARACTER_LAYOUT)):
    for x in range(len(CHARACTER_LAYOUT[y])):
        CHARACTER_MAP[CHARACTER_LAYOUT[y][x]] = (x, y)


def get_char_location_in_char_map(c, return_unknown="?"):
    """
    Gets a character's position in the char map
    Defaults to ? for unknown characters
    Set to None to raise error on unknown character
    """
    if return_unknown:
        return CHARACTER_MAP.get(c, CHARACTER_MAP.get(return_unknown))
    else:
        try:
            return CHARACTER_MAP[c]
        except KeyError:
            raise ValueError(f"Unable to determine map space for character - {c}")


class renderer:
    def __init__(
        self,
        columns: int,  # Terminal columns
        rows: int,  # Terminal rows
        char_size: int,  # Character size in pixels
        char_map_file: str,  # Path to charmap file (supports PNG, JPG, BMP, and more)
        render_scale: int = RENDER_SCALE,  # Integer window scale
    ):
        self.rows, self.columns = rows, columns
        self.width, self.height = columns * char_size, rows * char_size
        # Top layer
        self.foreground = zeros((self.height, self.width, 4), dtype=uint8)
        self.fg_changed = True
        self.fg_image = None  # placeholder
        # Bottom layer
        self.background = zeros((self.height, self.width, 4), dtype=uint8)
        self.bg_changed = True
        self.bg_image = None  # placeholder
        self.char_size = char_size  # Character size in pixels
        self.char_map_image = Image.open(char_map_file)
        self.char_map_width = self.char_map_image.size[0] / char_size
        self.char_map_height = self.char_map_image.size[1] / char_size
        self.text_color = (255, 255, 255, 255)
        self.bg_color = (0, 0, 0, 0)
        self.render_scale = render_scale

    def clear(self):
        # fixes issue with python gc not deleting pil image from memory appropriately
        del self.foreground
        del self.background
        self.fg_changed, self.bg_changed = True, True
        self.foreground = zeros((self.height, self.width, 4), dtype=uint8)
        self.background = zeros((self.height, self.width, 4), dtype=uint8)

    def render_fg(self):
        if self.fg_changed:
            self.fg_image = Image.fromarray(self.foreground, mode="RGBA")
            self.fg_changed = False
            return self.fg_image
        else:
            return self.fg_image

    def render_bg(self):
        if self.bg_changed:
            self.bg_image = Image.fromarray(self.background, mode="RGBA")
            self.bg_changed = False
            return self.bg_image
        else:
            return self.bg_image

    def write_char(self, column: int, row: int, char: int):
        """Writes a char to a given row/column"""
        self.fg_changed = True
        x = column * self.char_size
        y = row * self.char_size
        try:
            self.foreground[y : y + 8, x : x + 8] = asarray(char)[:][:]
        except Exception as e:
            if column >= self.columns:
                raise ValueError(f"Column {column} outside of rendered range")
            elif row > self.row:
                raise ValueError(f"Row {row} outside of rendered range")
            else:
                raise

    def write_block(self, column: int, row: int):
        """Fills in a character sized block with the currently set background color"""
        self.bg_changed = True
        x = column * self.char_size
        y = row * self.char_size
        self.background[y : y + 8, x : x + 8] = full(
            (self.char_size, self.char_size, 4), asarray(self.bg_color), dtype=uint8
        )

    def _get_atlas_char_at(self, column: int, row: int):
        """Gets a numpy array containing the rgb values of a char at a given column / row value"""
        if row > self.char_map_height - 1:
            raise ValueError(
                f"Row {row} exceeded character map height of {self.char_map_height}"
            )
        if column > self.char_map_width - 1:
            raise ValueError(
                f"Column {column} exceeded character map width of {self.char_map_width}"
            )
        x0, y0 = column * self.char_size, row * self.char_size
        x1, y1 = x0 + self.char_size, y0 + self.char_size
        im = asarray(self.char_map_image.crop((x0, y0, x1, y1)))
        red, green, blue, alpha = im.T  # Temporarily unpack the bands
        white_areas = (red == 255) & (blue == 255) & (green == 255)  # Create a b/w mask
        im[..., :][white_areas.T] = self.text_color  # Apply color using mask
        return im

    def render_text(
        self,
        column: int,
        row: int,
        text: str,
        wrap_x: bool = False,
        wrap_y: bool = True,
    ):
        """
        Draws a text string to the screen
        Column defines the leftmost column printed on, including after newlines
        Setting wrap_x to True will allow text to wrap horizontally shifted one row down
        Setting wrap_y to True will allow text to wrap from the bottom of the screen to the top
        wrap_x must be enabled for wrap_y to have any effect
        if wrap_x is not set and a char is placed offscreen a ValueError will occur in write_char (by design)
        """
        x_offset = 0
        y_offset = 0
        newlines = 0
        new_tab = True
        for char in text:
            if char == "\n":
                newlines += 1
                x_offset = 0
                continue
            else:
                new_tab = True
            x = column + x_offset
            if wrap_x:
                if x >= self.columns:
                    y_offset = int(x / self.columns)
                    x %= self.columns
            y = row + y_offset + newlines
            if wrap_y:
                if y >= self.rows:
                    y %= self.rows
            self.write_char(
                x,
                y,
                self._get_atlas_char_at(*get_char_location_in_char_map(char)),
            )
            x_offset += 1


class app(ShowBase):
    def __init__(self, *args, framerate=-1, **kwargs):
        self.start_time = time.time()
        ShowBase.__init__(self)
        globalClock.setMode(ClockObject.M_limited)
        self.set_target_fps(framerate)
        window_width = TERMINAL_COLUMNS * CHAR_SIZE * RENDER_SCALE
        window_height = TERMINAL_ROWS * CHAR_SIZE * RENDER_SCALE
        props = WindowProperties()
        props.set_title("TTY TK %s" % VERSION)
        props.set_size(window_width, window_height)
        self.win.requestProperties(props)
        self.setBackgroundColor(BACKGROUND_COLOR)
        self.setFrameRateMeter(True)

        # Add redraw to task loop
        taskMgr.add(self.update, "update_task")

        self.renderer = renderer(
            TERMINAL_COLUMNS,
            TERMINAL_ROWS,
            CHAR_SIZE,
            "character_map.png",
            RENDER_SCALE,
        )

        card = CardMaker("bg")
        im = self.renderer.render_bg().convert("RGBA")
        self.bg_texture = Texture()
        self.bg_texture.setup2dTexture(
            im.width, im.height, Texture.TUnsignedByte, Texture.FRgba
        )
        self.bg_texture.setRamImageAs(im.tobytes(), im.mode)
        self.bg_texture.setMagfilter(SamplerState.FT_nearest)
        self.bg_texture.setMinfilter(SamplerState.FT_nearest)
        self.bg_display = self.render2d.attachNewNode(card.generate())
        self.bg_display.set_texture(self.bg_texture, 1)
        self.bg_display.setTexScale(TextureStage.getDefault(), 1, -1)
        self.bg_display.setScale(2, 1, 2)
        self.bg_display.setPos(-1, 2, -1)
        self.bg_display.setTransparency(True)  # allows transparency blending

        self.fg_texture = Texture()
        self.fg_texture.setup2dTexture(
            im.width, im.height, Texture.TUnsignedByte, Texture.FRgba
        )
        self.fg_texture.setRamImageAs(im.tobytes(), im.mode)
        self.fg_texture.setMagfilter(SamplerState.FT_nearest)
        self.fg_texture.setMinfilter(SamplerState.FT_nearest)
        self.fg_display = self.render2d.attachNewNode(card.generate())
        self.fg_display.set_texture(self.fg_texture, 1)
        self.fg_display.setTexScale(TextureStage.getDefault(), 1, -1)
        self.fg_display.setScale(2, 1, 2)
        self.fg_display.setPos(-1, 0, -1)
        self.fg_display.setTransparency(True)

    def redraw(self):
        if self.renderer.fg_changed:
            fg_image = self.renderer.render_fg()
            self.fg_texture.setRamImageAs(fg_image.tobytes(), fg_image.mode)
        if self.renderer.bg_changed:
            bg_image = self.renderer.render_bg()
            self.bg_texture.setRamImageAs(bg_image.tobytes(), bg_image.mode)

    def set_target_fps(self, target=60):
        print(f"Setting target FPS to {target}")
        globalClock.setFrameRate(target)

    def update(self, task):
        self.redraw()
        return task.cont


######## Demo ########
if __name__ == "__main__":
    application = app()

    start_time = time.time()
    bg_colors = [
        (255, 0, 0, 255),
        (0, 255, 0, 255),
        (0, 0, 255, 255),
        (255, 255, 0, 255),
    ]
    text_colors = [
        (0, 255, 0, 255),
        (0, 0, 255, 255),
        (255, 255, 0, 255),
        (255, 0, 0, 255),
    ]

    def prep_task(task):
        application.renderer.clear()
        for i in range(4):
            application.renderer.text_color = text_colors[i]
            application.renderer.render_text(3 + i, 5 + i, "01234")
            application.renderer.bg_color = bg_colors[i]
            application.renderer.write_block(5 + i, 5 + i)
        application.renderer.text_color = (0, 255, 0, 255)
        # Draw wrapping text floor / ceiling
        application.renderer.render_text(0, 18, "0123456789?.x!=" * 8, wrap_x=True)
        return task.done

    def work_task(task):  # This will be your mainloop
        application.renderer.text_color = (
            random.uniform(0, 255),
            random.uniform(0, 255),
            random.uniform(0, 255),
            random.uniform(0, 255),
        )
        t = time.time()
        # application.renderer.text_color = (0, 0, 255, 255)
        application.renderer.render_text(13, 11, str(t - start_time)[:16])
        # Delay at least 1/100th of a second
        taskMgr.doMethodLater(0.008, work_task, "update_task")
        return task.done

    application.renderer.text_color = (127, 127, 255, 255)
    application.renderer.render_text(
        10, 2, "--------------------\nAvailable Characters\n--------------------"
    )
    application.renderer.text_color = (255, 255, 255, 255)
    application.renderer.render_text(3, 8, CHAR_MAP_STRING)

    taskMgr.doMethodLater(4.9, prep_task, "prep_task")
    taskMgr.doMethodLater(5, work_task, "update_task")
    application.run()  # Window Mainloop
