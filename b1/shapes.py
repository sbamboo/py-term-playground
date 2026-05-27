import time

from termobjs import *

# Example usage
# 1. Use shutil to get terminal size
import shutil
terminal_size = shutil.get_terminal_size((80, 24))

# 2. Create TermDisplayWithObjects
display = TermDisplayWithObjects(terminal_size.columns, terminal_size.lines)

# 3. Create some PixelContainers and TextContainers and add them to display.objects
red_square = PixelContainer(8, 8)
red_square.fill(RGBAPixel(255, 0, 0, 255))

blue_square = PixelContainer(8, 8)
blue_square.fill(RGBAPixel(0, 0, 255, 128)) # semi-transparent

hello_text = TextContainer("Hello, World!", RGBPixel(255, 255, 0)) # yellow text

red_square_id = display.addPixelObj(red_square, 2, 2)
blue_square_id = display.addPixelObj(blue_square, 6, 6)

hello_text_id = display.addTextObj(hello_text, 1, 3)

diagonal_line = Line(20, 10, 1, RGBAPixel(0, 255, 0, 128)) # green line
line_id = display.addPixelObj(diagonal_line, 0, 4)

text_with_bg = TextWithBg("Text with BG and transparency", RGBAPixel(255, 0, 0, 100), RGBAPixel(255, 255, 255, 255))
text_with_bg_ids = display.addCompositeObj(text_with_bg, 10, 6)

dot = Dot(RGBAPixel(255, 255, 255, 255))
dot_id = display.addPixelObj(dot, 40, 12)

rect = Rectangle(10, 5, RGBAPixel(0, 255, 255, 200))
rect_id = display.addPixelObj(rect, 50, 10)

boxOutline = BoxOutline(12, 6, 1, RGBAPixel(255, 0, 255, 255))
box_outline_id = display.addPixelObj(boxOutline, 2, 18)

boxOutline2 = BoxOutline(15, 8, 2, RGBAPixel(255, 255, 0, 255))
box_outline2_id = display.addPixelObj(boxOutline2, 20, 20)

ellipsis = Ellipsis(5, 3, RGBAPixel(100, 100, 255, 180))
ellipsis_id = display.addPixelObj(ellipsis, 70, 15)

ellipsisOutline = EllipsisOutline(6, 6, 1, RGBAPixel(255, 100, 100, 255))
ellipsis_outline_id = display.addPixelObj(ellipsisOutline, 2, 30)

polygon = Polygon([(0,0), (10,2), (8,8), (2,6)], RGBAPixel(150, 50, 150, 200))
polygon_id = display.addPixelObj(polygon, 90, 10)

polygon_wireframe = PolygonWireframe([(0,0), (10,2), (8,8), (2,6)], 1, RGBAPixel(255, 255, 255, 255))
polygon_wireframe_id = display.addPixelObj(polygon_wireframe, 20, 35)

triangle = Triangle((0,0), (10,0), (10,10), RGBAPixel(0, 150, 150, 200))
triangle_id = display.addPixelObj(triangle, 40, 35)

triangle_wireframe = TriangleWireframe((0,0), (10,0), (10,10), 1, RGBAPixel(255, 255, 0, 255))
triangle_wireframe_id = display.addPixelObj(triangle_wireframe, 60, 30)

# 4. Render

def printAt(x: int, y: int, text: str):
    print(f"\033[{y};{x}H{text}", end='')

def printAt00(text: str):
    printAt(1, 1, text)

display.render(printAt00, trailingNewline=False)