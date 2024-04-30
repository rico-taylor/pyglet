import pyglet
from pyglet.window import Window
from pyglet.window import key
from pyglet.window import mouse

window = Window()


leftSignal = False
rightSignal = False

@window.event
def on_mouse_press(x,y, button, modifier):
  if button == mouse.LEFT:
    global leftSignal
    global label1
    print("The left mouse button was pressed")
    label1 = pyglet.text.Label("LEFT", font_size=20, x=x, y=y)
    leftSignal = True
  elif button == mouse.RIGHT:
    global rightSignal
    global lable2
    print("Right Mouse Was ")
    lable2 = pyglet.text.Label("RIGHT", font_size=20, x=x, y=y)
    rightSignal = True

@window.event
def on_key_press(symbol, modifiers):
  if symbol == key.A:
    print("A Key Was pressed")
  elif symbol == key.B:
    print("B Key Was Pressed")
  elif symbol == key.ENTER:
    print("Enter Key was pressed")

@window.event
def on_draw():
  window.clear()
  if leftSignal == True:
    label1.draw()
  if rightSignal == True:
    lable2.draw()






pyglet.app.run()
