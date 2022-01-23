import io, math, time
import tkinter as tk
from PIL import Image, ImageTk, ImageOps
from numpy import array, asarray, zeros, uint8, full

VERSION = "0.0"
CHAR_SIZE = 8 #Character size both on the character map image and rendered on the screen
TERMINAL_COLUMNS = 40
TERMINAL_ROWS = 20
WINDOW_BORDER = 10 #Border between terminal and outer edge of window
WINDOW_BORDER_COLOR = "darkgray"
TERMINAL_BACKGROUND_COLOR = "black"
RENDER_LOOP_DELAY = 50 #50 ms
RENDER_SCALE = 3 #Scales the terminal

#Map corresponding to the tileset image
CHARACTER_LAYOUT = [
	["0", "1","2", "3"],
	["4", "5","6", "7"],
	["8", "9","?", "!"],
	[".", "x","+", "="],
]
CHARACTER_MAP = {} #Generate a lookup table to easily find the position in the map from a char
for y in range(len(CHARACTER_LAYOUT)):
	for x in range(len(CHARACTER_LAYOUT[y])):
		CHARACTER_MAP[CHARACTER_LAYOUT[y][x]]=(x,y) #The rows and 

def get_char_location_in_atlas(c): return CHARACTER_MAP.get(c,CHARACTER_MAP.get('?')) #Default to ? for unknown characters

#bottom layer must be equal or greater in size than top layer
def merge_layers(top_layer:array, bottom_layer:array):
	merged_images = Image.fromarray(bottom_layer) #Make pil image from array
	top_image = Image.fromarray(top_layer) #Make pil image from array
	#The second passed top_image acts as an alpha mask to preserve transparency 
	merged_images.paste(top_image, (0,0), top_image) #Paste top image on top of bottom
	return merged_images
 
class renderer:
	def __init__(self, columns:int, rows:int, char_size:int, char_map_file:str, render_scale:int=RENDER_SCALE):
		self.width,self.height=columns*char_size,rows*char_size
		self.foreground=zeros((self.height, self.width, 4), dtype=uint8) #Top layer
		self.background=zeros((self.height, self.width, 4), dtype=uint8) #Bottom layer
		self.char_size = char_size #Character size in pixels
		self.char_map_image = Image.open(char_map_file)
		self.char_map_width = self.char_map_image.size[0]/char_size
		self.char_map_height = self.char_map_image.size[1]/char_size
		self.text_color = (255,255,255)
		self.bg_color = (0,0,0,255)
		self.render_scale = render_scale

	def clear(self):
		del self.foreground; del self.background  #fixes issue with python gc not deleting pil image from memory appropriately
		self.foreground=zeros((self.height, self.width, 4), dtype=uint8)
		self.background=zeros((self.height, self.width, 4), dtype=uint8)

	def render_frame(self): 
		im = merge_layers(self.foreground, self.background)
		if not self.render_scale == 1: #If render scale is set rescale the image
			im = im.resize((im.size[0]*self.render_scale,im.size[1]*self.render_scale),Image.BOX)
		return ImageTk.PhotoImage(im)

	def write_char(self, column:int, row:int, char:int): #Writes a char to a given row/column
		x = column * self.char_size
		y = row * self.char_size
		self.foreground[y:y+8, x:x+8]=asarray(char)[:][:]

	def write_block(self, column:int, row:int): #Fills in a character sized block with the currently set background color
		x = column * self.char_size
		y = row * self.char_size
		self.background[y:y+8, x:x+8]=full((self.char_size, self.char_size, 4), asarray(self.bg_color), dtype=uint8)

	def get_atlas_char_at(self, column:int, row:int):
		if row > self.char_map_height-1: raise ValueError(f"Row {row} exceeded character map height of {self.char_map_height}")
		if column > self.char_map_width-1: raise ValueError(f"Column {column} exceeded character map width of {self.char_map_width}")
		x0, y0 = column * self.char_size, row * self.char_size
		x1, y1 = x0 + self.char_size, y0 + self.char_size
		im = asarray(self.char_map_image.crop((x0,y0,x1,y1)))
		red, green, blue, alpha = im.T # Temporarily unpack the bands
		white_areas = (red == 255) & (blue == 255) & (green == 255) #Create a b/w mask 
		im[..., :-1][white_areas.T] = self.text_color #Apply color using mask
		return im

	def render_text(self, column:int, row:int, text:str):
		x_offset = 0
		for char in text:
			self.write_char(column+x_offset,row,self.get_atlas_char_at(*get_char_location_in_atlas(char)))
			x_offset += 1

class app(tk.Tk):
	def __init__(self, *args, **kwargs):
		self.start_time=time.time()
		tk.Tk.__init__(self, *args, **kwargs)
		window_width = 2*WINDOW_BORDER+TERMINAL_COLUMNS*CHAR_SIZE*RENDER_SCALE
		window_height = 2*WINDOW_BORDER+TERMINAL_ROWS*CHAR_SIZE*RENDER_SCALE
		self.geometry(f"{window_width}x{window_height}") #Stupid tk syntax, resizes 
		self.title("TTY TK %s" % VERSION) #Set window title
		self.resizable(False, False) #Disable horizontal and vertical resize
		self.configure(background=WINDOW_BORDER_COLOR) #Set the border color

		self.renderer = renderer(
			TERMINAL_COLUMNS,
			TERMINAL_ROWS,
			CHAR_SIZE,
			"character_map.png",
			RENDER_SCALE
		)

		canvas_frame = tk.Frame(self) #Never actually seen, covered by the canvas it holds
		canvas_frame.place(
			relwidth=1,
			relheight=1,
			width=-2*WINDOW_BORDER,
			height=-2*WINDOW_BORDER,
			x=WINDOW_BORDER,
			y=WINDOW_BORDER,
		)

		#This is where the rendered image gets placed
		#Don't confuse this with an actual tk.canvas
		self.canvas = tk.Label(canvas_frame, background=TERMINAL_BACKGROUND_COLOR)
		self.canvas.place(relwidth=1,relheight=1) #Fill the canvas frame
		self.canvas.image = None
		
		###############################################
		#Example
		colors = [
			(255,0,0,255),
			(0,255,0,255),
			(0,0,255,255),
			(255,255,0,255)
		]
		text_colors = [
			(0,255,0),
			(0,0,255),
			(255,255,0),
			(255,0,0),
		]
		for i in range(4):
			self.renderer.text_color = text_colors[i]
			self.renderer.render_text(1+i,3+i, "01234")
			self.renderer.bg_color = colors[i]
			self.renderer.write_block(3+i,3+i)
			self._sideloop()
		###############################################

	def _sideloop(self):
		###############################################
		#Example
		#This is the text string that is getting updated
		self.renderer.render_text(10,10, str(time.time()-self.start_time))
		###############################################

		self.redraw() #Get new frame from renderer
		self.update_idletasks() #Forces tk window redraw
		self.after(RENDER_LOOP_DELAY,self._sideloop) #Reschedule

	def redraw(self):
		#Delete old image instad of relying on gc, helps with a memory leak that crops up sometimes
		if self.canvas.image: del self.canvas.image
		#If the image isn't referenced somewhere python garbage collection will delete the image before the tkinter mainloop renders it
		self.canvas.image = self.renderer.render_frame()
		#Update the canvas to show the image
		self.canvas.configure(image=self.canvas.image)

application = app()
application.mainloop()