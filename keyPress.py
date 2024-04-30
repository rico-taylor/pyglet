import pyglet

window = pyglet.window.Window(resizable=True)
label = pyglet.text.Label("A Key Was Pressed", font_size=40, x=window.width/2, y=window.height/2, color = (201, 242, 155, 1000), anchor_x='center', anchor_y='center' )

press = False
keyCount = -1

@window.event
def on_key_press(symbol,modifiers):
  global press
  global keyCount
  keyCount += 1
  print("A Key Was Pressed")
  press = True

@window.event
def on_draw():
  window.clear()
  string = ''
  for x in range (0, keyCount):
    string = string + str(' again')
  if press == True:
    label = pyglet.text.Label("A Key Was Pressed" + str(string), font_size=40, x=window.width/2, y=window.height/2, color = (201, 242, 155, 1000), anchor_x='center', anchor_y='center' )
    label.draw()







pyglet.app.run()