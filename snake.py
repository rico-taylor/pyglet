from pyglet import app
from pyglet import image
from pyglet.window import Window
from pyglet import clock
from pyglet.window import key
import random

window = Window(500,500)

@window.event
def on_draw():
  window.clear()
  #food
  draw_square(fd_x, fd_y, cell_size, colour = (255,0,0,0))
  #tail
  for coords in tail:
    draw_square(coords[0], coords[1], cell_size, colour = (127, 127, 127, 0))
  #head
  draw_square(snk_x, snk_y, cell_size)

def draw_square(x,y, size, colour = (255,255,255,0)):
  img = image.create(size, size, image.SolidColorImagePattern(colour))
  img.blit(x,y)

def place_food():
  global fd_x, fd_y
  fd_x = random.randint(0, (window.width // cell_size) -1) *cell_size 
  fd_y = random.randint(0, (window.height // cell_size) -1) *cell_size 

@window.event
def on_key_press(symbol, modifiers):
  global snk_dx, snk_dy
  
  if symbol == key.LEFT:
    if snk_dx == 0:
      snk_dx = -cell_size
      snk_dy = 0
  elif symbol == key.RIGHT:
    if snk_dx == 0:
      snk_dx = cell_size
      snk_dy = 0
  elif symbol == key.UP:
    if snk_dy == 0:
      snk_dx = 0
      snk_dy = cell_size
  elif symbol == key.DOWN:
    if snk_dy == 0:
      snk_dx = 0
      snk_dy = -cell_size

snk_dx = 0
snk_dy = 0

def update(dt):
  global snk_x, snk_y, game_over

  #check if game is already over, If so then just return and ignore the press
  if game_over == True:
    return
  
  #Check for game over conditions
  if game_over_condition():
    game_over = True
    return
  
  tail.append((snk_x, snk_y))

  snk_x += snk_dx
  snk_y += snk_dy

  if snk_x == fd_x and snk_y == fd_y:
    place_food()
  else:
    tail.pop(0)

def game_over_condition():
  #collision with edge
  condition1 = snk_x +snk_dx <0 or snk_x + snk_dx > window.width - cell_size or snk_y + snk_dy > window.height - cell_size or snk_y +snk_dy <0
  #collision with self
  condition2 = (snk_x, snk_y) in tail
  return condition1 or condition2

cell_size = 20

snk_x = window.width // cell_size // 2 * cell_size
snk_y = window.height // cell_size // 2 * cell_size

fd_x, fd_y = 0,0

tail = []

place_food()

game_over = False

clock.schedule_interval(update, 1/15)

app.run()