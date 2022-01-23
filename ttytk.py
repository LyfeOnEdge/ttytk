import io, math, time
import tkinter as tk
from PIL import Image, ImageTk, ImageOps
from numpy import asarray, zeros, uint8, full

VERSION = "0.0"
CHAR_SIZE = 8
TERMINAL_COLUMNS = 40
TERMINAL_ROWS = 20
WINDOW_BORDER = 25
TERMINAL_BACKGROUND_COLOR = "black"
RENDER_LOOP_DELAY = 50 #50 ms
RENDER_SCALE = 3 #Make everything bigger

#Map corresponding to the tileset image
TILESET = [
	["0", "1","2", "3"],
	["4", "5","6", "7"],
	["8", "9","?", "!"],
	[".", "x","+", "="],

]

TILEMAP = {} #Generate a lookup table to find the atlas position from a char
for y in range(len(TILESET)):
	for x in range(len(TILESET[y])):
		TILEMAP[TILESET[y][x]]=(x,y)
def get_char_location(c): return TILEMAP.get(c,TILEMAP.get('*'))

def merge_layers(top_layer, bottom_layer):
	merged_images = Image.fromarray(bottom_layer.array)
	top_image = Image.fromarray(top_layer.array)
	merged_images.paste(top_image, (0,0), top_image) #The second passed image acts as an alpha mask to preserve transparency 
	return merged_images

class Layer:
	def __init__(self, width, height):
		self.width, self.height = width, height
		#Make array of specified width and height the depth of 4 for rgba, np.Zeros inititalizes image as transparent black
		self.array = zeros((self.height, self.width, 4), dtype=uint8)
		self.image = self.export_image() #Set initial image
	def set_pixel_color(self, x, y, color): self.array[y][x] = color
	def get_pixel_color(self, x, y): return self.array[y][x]
	def export_array(self): return self.array
	def load_array(self, array): self.array = array
	def export_image(self):
		self.image = Image.fromarray(self.array, 'RGBA')
		return self.image

class renderer:
	def __init__(self, columns, rows, char_size, character_atlas, render_scale = RENDER_SCALE):
		self.width,self.height=columns,rows
		self.foreground=Layer(width,height)
		self.background=Layer(width,height)
		self.char_size = char_size
		self.character_atlas = Image.open(character_atlas)
		self.atlas_width = self.character_atlas.size[0]/char_size
		self.atlas_height = self.character_atlas.size[1]/char_size
		self.text_color = (255,255,255)
		self.bg_color = (0,0,0,255)
		self.render_scale = render_scale

	def clear(self):
		del self.foreground #fixes issue with python gc not deleting pil image from memory appropriately
		del self.background #fixes issue with python gc not deleting pil image from memory appropriately
		self.foreground=Layer(self.width,self.height)
		self.background=Layer(self.width,self.height)

	def render_frame(self): 
		im = merge_layers(self.foreground, self.background)
		if not self.render_scale == 1: #If render scale is set rescale the image
			im = im.resize((im.size[0]*self.render_scale,im.size[1]*self.render_scale),Image.BOX)
		return ImageTk.PhotoImage(im)

	def write_char(self, column, row, char): #Writes a char to a given row/position
		x = column * self.char_size
		y = row * self.char_size
		self.foreground.array[y:y+8, x:x+8]=asarray(char)[:][:]

	def write_block(self, column, row): #Fills in a character sized block with the currently set background color
		x = column * self.char_size
		y = row * self.char_size
		self.background.array[y:y+8, x:x+8]=full((self.char_size, self.char_size, 4), asarray(self.bg_color), dtype=uint8)

	def get_atlas_char_at(self, column, row):
		if row > self.atlas_height-1: raise ValueError(f"Row {row} exceeded character atlas height of {self.atlas_height}")
		if column > self.atlas_width-1: raise ValueError(f"Column {column} exceeded character atlas width of {self.atlas_width}")
		x0, y0 = column * self.char_size, row * self.char_size
		x1, y1 = x0 + self.char_size, y0 + self.char_size
		im = asarray(self.character_atlas.crop((x0,y0,x1,y1)))
		red, green, blue, alpha = im.T # Temporarily unpack the bands for readability
		white_areas = (red == 255) & (blue == 255) & (green == 255)
		im[..., :-1][white_areas.T] = self.text_color
		return im

	def render_text(self, column, row, text):
		x_offset = 0
		for t in text:
			self.write_char(column+x_offset,row,self.get_atlas_char_at(*get_char_location(t)))
			x_offset += 1

class app(tk.Tk):
	def __init__(self, *args, **kwargs):
		self.start_time=time.time()
		tk.Tk.__init__(self, *args, **kwargs)
		window_width = 2*WINDOW_BORDER+TERMINAL_COLUMNS*CHAR_SIZE*RENDER_SCALE
		window_height = 2*WINDOW_BORDER+TERMINAL_ROWS*CHAR_SIZE*RENDER_SCALE
		self.geometry(f"{window_width}x{window_height}") #Stupid tk syntax
		self.title("TTY TK %s" % VERSION)
		self.resizable(False, False) #Disable horizontal and vertical resize

		self.renderer = renderer(
			TERMINAL_COLUMNS*CHAR_SIZE,
			TERMINAL_ROWS*CHAR_SIZE,
			CHAR_SIZE,
			"tileset.png",
			RENDER_SCALE
		)

		canvas_frame = tk.Frame(self) #Never actually seen, holds everything
		canvas_frame.place(
			relwidth=1,
			relheight=1,
			width=-2*WINDOW_BORDER,
			height=-2*WINDOW_BORDER,
			x=WINDOW_BORDER,
			y=WINDOW_BORDER,
		)

		#This is where the rendered image gets placed
		self.canvas_label = tk.Label(canvas_frame, background=TERMINAL_BACKGROUND_COLOR)
		self.canvas_label.place(relwidth=1,relheight=1)
		self.canvas_label.image = None
		
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
		im = self.renderer.render_frame()
		#Delete old image instad of relying on gc, helps with a memory leak that crops up sometimes
		if self.canvas_label.image: del self.canvas_label.image
		#Update the label to show the image
		self.canvas_label.configure(image=im)
		#If the image isn't referenced somewhere python garbage collection will delete the image before the tkinter mainloop renders it
		self.canvas_label.image = im

application = app()
application.mainloop()