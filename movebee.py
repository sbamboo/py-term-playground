import time

from termobjs import *

# Example usage
# 1. Use shutil to get terminal size
import shutil
terminal_size = shutil.get_terminal_size((80, 24))

# 2. Create TermDisplayWithObjects
display = TermDisplayWithObjects(terminal_size.columns, terminal_size.lines)

# 3. Create objects

beeW = 16
beeH = 16
bee_image_1 = ImageContainer(imagePath="bee.png", width=beeW, height=beeH)
bee_image_2 = ImageContainer(imagePath="bee2.png", width=beeW, height=beeH)
bee_image_3 = ImageContainer(imagePath="bee3.png", width=beeW, height=beeH)
bee_image_4 = ImageContainer(imagePath="bee4.png", width=beeW, height=beeH)
bee_image_5 = ImageContainer(imagePath="bee5.png", width=beeW, height=beeH)
bee_animation = AnimatedPixelContainer(frames=[bee_image_1, bee_image_2, bee_image_3, bee_image_4, bee_image_5], delayMs=200, loop=True)
bee_animation_id = display.addPixelObj(bee_animation, 100, 20)

# 4. Define simple input system
from pynput import keyboard
pressedKeys = set()
def on_press(key):
    try:
        pressedKeys.add(key.char)  # letters/numbers
    except AttributeError:
        pressedKeys.add(key.name)  # special keys
def on_release(key):
    try:
        pressedKeys.discard(key.char)
    except AttributeError:
        pressedKeys.discard(key.name)
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

# 5. Test loop to render the display
import os
running = True

def printAt(x: int, y: int, text: str):
    print(f"\033[{y};{x}H{text}", end='')

def printAt00(text: str):
    printAt(1, 1, text)

# hide cursor
print("\033[?25l", end='')
# loop
while running:
    try:
        # update
        speed = 4
        xSpeed = 2 * speed
        ySpeed = 1 * speed

        if 'up' in pressedKeys:
            (x, y) = display.getObjectPos(bee_animation_id)
            display.moveObject(bee_animation_id, x, max(0, y - ySpeed))
        
        if 'down' in pressedKeys:
            (x, y) = display.getObjectPos(bee_animation_id)
            display.moveObject(bee_animation_id, x, min(display.getCellDimentions()[1] - beeH, y + ySpeed))
    
        if 'left' in pressedKeys:
            (x, y) = display.getObjectPos(bee_animation_id)
            display.moveObject(bee_animation_id, max(0, x - xSpeed), y)
        
        if 'right' in pressedKeys:
            (x, y) = display.getObjectPos(bee_animation_id)
            display.moveObject(bee_animation_id, min(display.getCellDimentions()[0] - beeW, x + xSpeed), y)


        # render
        display.render(printAt00, trailingNewline=False)

        # 20 FPS
        time.sleep(0.05)
    except KeyboardInterrupt:
        running = False
        # show cursor
        print("\033[?25h\033[0m")
        # reset colors
        print("\033[0m")