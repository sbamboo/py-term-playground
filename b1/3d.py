import time

from termobjs import *
from threedimext import *

# Example usage
# 1. Use shutil to get terminal size
import shutil
terminal_size = shutil.get_terminal_size((80, 24))

# 2. Create TermDisplayWithObjects
display = TermDisplayWithObjects(terminal_size.columns, terminal_size.lines)

# 3. Create 3D Context
ctx3d = Context3D(displayWidth=terminal_size.columns, displayHeight=terminal_size.lines, fovDegrees=90)

# 4. Create Objects
beeW = 16
beeH = 16
bee_image_1 = ImageContainer(imagePath="bee.png", width=beeW, height=beeH)
bee_image_2 = ImageContainer(imagePath="bee2.png", width=beeW, height=beeH)
bee_image_3 = ImageContainer(imagePath="bee3.png", width=beeW, height=beeH)
bee_image_4 = ImageContainer(imagePath="bee4.png", width=beeW, height=beeH)
bee_image_5 = ImageContainer(imagePath="bee5.png", width=beeW, height=beeH)
bee_animation = AnimatedPixelContainer(frames=[bee_image_1, bee_image_2, bee_image_3, bee_image_4, bee_image_5], delayMs=200, loop=True, pxScaleFactor=2)


face = Polygon3D(
    ctx3d,
    [
        # Local space vertices of the face, screen is roughly 144x80, Camera is at (0,0,0) looking down -Z
        Vector3(0, 0, -10),
        Vector3(5, 0, -10),
        Vector3(5, 5, -10),
    ],
    RGBAPixel(255, 0, 0, 255)
)
face_id = display.addPixelObj(face, 0, 0)


textured_face = TexturedPolygon3D(
    ctx3d,
    [
        # Local space vertices of the face, screen is roughly 144x80, Camera is at (0,0,0) looking down -Z
        Vector3(0, 0, -10),
        Vector3(5, 0, -10),
        Vector3(5, 5, -10),
    ],
    bee_animation
)
textured_face_id = display.addPixelObj(textured_face, 40, 0)


wireframe_face = WireframePolygon3D(
    ctx3d,
    [
        # Local space vertices of the face, screen is roughly 144x80, Camera is at (0,0,0) looking down -Z
        Vector3(0, 0, -10),
        Vector3(5, 0, -10),
        Vector3(5, 5, -10),
    ],
    1,
    RGBAPixel(0, 255, 0, 255)
)
wireframe_face_id = display.addPixelObj(wireframe_face, 0, 20)


# rectangle = WireframeRectangle3D(
#     ctx3d,
#     # v0 = BottomLeft, v1 = BottomRight, v2 = TopRight, v3 = TopLeft
#     Vector3(0, 0, -10),
#     Vector3(5, 0, -10),
#     Vector3(5, 5, -10),
#     Vector3(0, 5, -10),
#     1,
#     RGBAPixel(0, 0, 255, 255),
#     RGBAPixel(255, 255, 0, 255)
# )
# rectangle_id = display.addCompositeObj(rectangle, 0, 20)


# 5. Render

def printAt(x: int, y: int, text: str):
    print(f"\033[{y};{x}H{text}", end='')

def printAt00(text: str):
    printAt(1, 1, text)

display.render(print, trailingNewline=False)

# running = True
# # hide cursor
# print("\033[?25l", end='')
# # loop
# while running:
#     try:
#         # render
#         display.render(printAt00, trailingNewline=False)

#         # 20 FPS
#         time.sleep(0.05)
#     except KeyboardInterrupt:
#         running = False
#         # show cursor
#         print("\033[?25h\033[0m")
#         # reset colors
#         print("\033[0m")