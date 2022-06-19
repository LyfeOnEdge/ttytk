import io, math, time
import tkinter as tk
from PIL import Image, ImageTk, ImageOps
from numpy import array, asarray, zeros, uint8, full
from numba import jit

VERSION = "0.0"
CHAR_SIZE = 8  # Square, In pixels
TERMINAL_COLUMNS = 40
TERMINAL_ROWS = 20
WINDOW_BORDER = 10  # Border between terminal and outer edge of window
WINDOW_BORDER_COLOR = "darkgray"
TERMINAL_BACKGROUND_COLOR = "black"
RENDER_LOOP_DELAY = 50  # ms
RENDER_SCALE = 3  # Scales the terminal

# Map corresponding to the tileset image
CHARACTER_LAYOUT = [
    ["0", "1", "2", "3"],
    ["4", "5", "6", "7"],
    ["8", "9", "?", "!"],
    [".", "x", "+", "="],
]
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


# bottom layer must be equal or greater in size than top layer
def merge_layers(top_layer: array, bottom_layer: array):
    # Make pil image from bottom layer array
    merged_images = Image.fromarray(bottom_layer)
    # Make pil image from top layer array
    top_image = Image.fromarray(top_layer)
    # The second passed top_image acts as an alpha mask to preserve transparency
    # Paste top image on top of bottom
    merged_images.paste(top_image, (0, 0), top_image)
    return merged_images


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
        # Bottom layer
        self.background = zeros((self.height, self.width, 4), dtype=uint8)
        self.char_size = char_size  # Character size in pixels
        self.char_map_image = Image.open(char_map_file)
        self.char_map_width = self.char_map_image.size[0] / char_size
        self.char_map_height = self.char_map_image.size[1] / char_size
        self.text_color = (255, 255, 255)
        self.bg_color = (0, 0, 0, 255)
        self.render_scale = render_scale

    def clear(self):
        # fixes issue with python gc not deleting pil image from memory appropriately
        del self.foreground
        del self.background
        self.foreground = zeros((self.height, self.width, 4), dtype=uint8)
        self.background = zeros((self.height, self.width, 4), dtype=uint8)

    def render_frame(self):
        # Uses pil to convert the arrays to images and overlay the foreground on the background
        im = merge_layers(self.foreground, self.background)
        # If render scale is set rescale the image
        if not self.render_scale == 1:
            im = im.resize(
                (im.size[0] * self.render_scale, im.size[1] * self.render_scale),
                Image.Resampling.BOX,
            )
        return ImageTk.PhotoImage(im)

    def write_char(self, column: int, row: int, char: int):
        """Writes a char to a given row/column"""
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
        x = column * self.char_size
        y = row * self.char_size
        self.background[y : y + 8, x : x + 8] = full(
            (self.char_size, self.char_size, 4), asarray(self.bg_color), dtype=uint8
        )

    def get_atlas_char_at(self, column: int, row: int):
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
        im[..., :-1][white_areas.T] = self.text_color  # Apply color using mask
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
        Setting wrap_x to True will allow text to wrap horizontally shifted one row down
        Setting wrap_y to True will allow text to wrap from the bottom of the screen to the top
        wrap_x must be enabled for wrap_y to have any effect
        if wrap_x is not set and a char is placed offscreen a ValueError will occur in write_char (by design)
        """
        x_offset = 0
        y_offset = 0
        for char in text:
            x = column + x_offset
            if wrap_x:
                if x >= self.columns:
                    y_offset = int(x / self.columns)
                    x %= self.columns
            y = row + y_offset
            if wrap_y:
                if y >= self.rows:
                    y %= self.rows
            self.write_char(
                x,
                y,
                self.get_atlas_char_at(*get_char_location_in_char_map(char)),
            )
            x_offset += 1


class app(tk.Tk):
    def __init__(self, *args, **kwargs):
        self.start_time = time.time()
        tk.Tk.__init__(self, *args, **kwargs)
        window_width = 2 * WINDOW_BORDER + TERMINAL_COLUMNS * CHAR_SIZE * RENDER_SCALE
        window_height = 2 * WINDOW_BORDER + TERMINAL_ROWS * CHAR_SIZE * RENDER_SCALE
        # Stupid stupid STUPID tk syntax... Sets windows size.
        # I'm reviewing this code months later and I still don't
        # understand why this ONE FUNCTION IS LIKE THIS why on
        # earth would you pass integer values as a string like this???
        # especially when the comprable .minsize function takes two integers???
        # .geometry("{width}x{height}") vs .minsize(width,height)
        # even .resizable takes a 0/1 integer at the python/tcl inteface level
        self.geometry(f"{window_width}x{window_height}")  # I hate tkinter sometimes.
        self.minsize(window_width, window_height)
        self.title("TTY TK %s" % VERSION)  # Set window title
        self.resizable(False, False)  # Disable horizontal and vertical resize
        self.configure(background=WINDOW_BORDER_COLOR)  # Set the border color

        self.renderer = renderer(
            TERMINAL_COLUMNS,
            TERMINAL_ROWS,
            CHAR_SIZE,
            "character_map.png",
            RENDER_SCALE,
        )
        # Never actually seen, covered by the canvas it holds
        canvas_frame = tk.Frame(self)
        canvas_frame.pack(
            fill=tk.BOTH, expand=True, padx=WINDOW_BORDER, pady=WINDOW_BORDER
        )
        # This is where the rendered image gets placed
        # Don't confuse this with an actual tk.canvas
        self.canvas = tk.Label(canvas_frame, background=TERMINAL_BACKGROUND_COLOR)
        self.canvas.place(relwidth=1, relheight=1)  # Fill the canvas frame
        self.canvas.image = None  # Set up placeholder

        ###############################################
        # Example
        colors = [
            (255, 0, 0, 255),
            (0, 255, 0, 255),
            (0, 0, 255, 255),
            (255, 255, 0, 255),
        ]
        text_colors = [
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 0),
            (255, 0, 0),
        ]
        for i in range(4):
            self.renderer.text_color = text_colors[i]
            self.renderer.render_text(3 + i, 5 + i, "01234")
            self.renderer.bg_color = colors[i]
            self.renderer.write_block(5 + i, 5 + i)
        self.renderer.text_color = (0, 255, 0)
        self.renderer.render_text(0, 18, "0123456789?.x!=" * 8, wrap_x=True)
        self.after(0, self._sideloop)
        ###############################################

    def _sideloop(self):
        ###############################################
        # Example
        # This is the text string that is getting updated
        t = time.time()
        self.renderer.text_color = (0, 0, 255)
        self.renderer.render_text(10, 11, str(t - self.start_time))
        ###############################################

        self.redraw()  # Get new frame from renderer
        self.update_idletasks()  # Forces tk window redraw
        self.after(RENDER_LOOP_DELAY, self._sideloop)  # Reschedule

    def redraw(self):
        # Delete old image instad of relying on gc, helps with a memory leak that crops up sometimes
        if self.canvas.image:
            del self.canvas.image
        # If the image isn't referenced somewhere python gc will delete the image before the tk mainloop renders it
        self.canvas.image = self.renderer.render_frame()
        # Update the canvas to show the image
        self.canvas.configure(image=self.canvas.image)


application = app()
application.mainloop()
