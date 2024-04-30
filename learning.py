import pyglet


animation = pyglet.image.load_animation('simple.gif')
animSprite = pyglet.sprite.Sprite(animation)

w = animSprite.width
h = animSprite.height

window = pyglet.window.Window(width=w, height=h, resizable=True, style=pyglet.window.Window.WINDOW_STYLE_DIALOG)
window.set_minimum_size(400,300)

label1 = pyglet.text.Label("hello pyglet", font_name='Times New Roman', font_size = 40, x=window.width/2, y = window.height/2, anchor_x='center', anchor_y='center')

label2 = pyglet.text.Label("helloello", font_name='Times New Roman', font_size = 40, x=(window.width/2)-20, y = (window.height/2)-20, anchor_x='center', anchor_y='center', color=(201, 242, 155, 1000))

image = pyglet.resource.image('dog.png')



@window.event
def on_draw():
  window.clear()
  image.blit(100,10)
  label1.draw()
  label2.draw()
  animSprite.draw()


pyglet.app.run()