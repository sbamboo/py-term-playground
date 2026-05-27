import time

from termobjs import *

# Example usage
# 1. Use shutil to get terminal size
import shutil
terminal_size = shutil.get_terminal_size((80, 24))

# 2. Create TermDisplayWithObjects
display = TermDisplayWithObjects(terminal_size.columns, terminal_size.lines)

# 3. Create some PixelContainers and TextContainers and add them to display.objects
beeW = 16
beeH = 16
bee_image_1 = ImageContainer(imagePath="bee.png", width=beeW, height=beeH)
bee_image_2 = ImageContainer(imagePath="bee2.png", width=beeW, height=beeH)
bee_image_3 = ImageContainer(imagePath="bee3.png", width=beeW, height=beeH)
bee_image_4 = ImageContainer(imagePath="bee4.png", width=beeW, height=beeH)
bee_image_5 = ImageContainer(imagePath="bee5.png", width=beeW, height=beeH)
bee_animation = AnimatedPixelContainer(frames=[bee_image_1, bee_image_2, bee_image_3, bee_image_4, bee_image_5], delayMs=200, loop=True)

dot = TexturedDot(bee_animation)
dot_id = display.addPixelObj(dot, 40, 12)

diagonal_line = TexturedLine(20, 10, 1, bee_animation)
line_id = display.addPixelObj(diagonal_line, 0, 4)

rect = TexturedRectangle(10, 5, bee_animation)
rect_id = display.addPixelObj(rect, 50, 10)

square = TexturedSquare(6, bee_animation)
square_id = display.addPixelObj(square, 20, 5)

ellipsis = TexturedEllipsis(5, 3, bee_animation)
ellipsis_id = display.addPixelObj(ellipsis, 70, 15)

circle = TexturedCircle(4, bee_animation)
circle_id = display.addPixelObj(circle, 10, 15)

polygon = TexturedPolygon([(0,0), (10,2), (8,8), (2,6)], bee_animation)
polygon_id = display.addPixelObj(polygon, 90, 10)

triangle = TexturedTriangle((0,0), (10,0), (10,10), bee_animation)
triangle_id = display.addPixelObj(triangle, 40, 35)

# 4. Render

def printAt(x: int, y: int, text: str):
    print(f"\033[{y};{x}H{text}", end='')

def printAt00(text: str):
    printAt(1, 1, text)

#display.render(printAt00, trailingNewline=False)

running = True
# hide cursor
print("\033[?25l", end='')
# loop
while running:
    try:
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