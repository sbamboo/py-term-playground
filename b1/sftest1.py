from termobjs import *

# Example usage
# 1. Use shutil to get terminal size
import shutil
terminal_size = shutil.get_terminal_size((80, 24))

# 2. Create TermDisplayWithObjects
display = TermDisplayWithObjects(terminal_size.columns, terminal_size.lines)

# 3. Add objects

text = TextContainer("Experiemental StreamedBinaryFile Support! Showing: gif_100.sf", RGBPixel(255, 255, 0)) # yellow text
textObjID = display.addTextObj(text, 0, 0)

scaleFactor = 1

gif = StreamedFileAnimatedPixelContainer(filePath="gif_100.sf")
gifObjID = display.addPixelObj(gif, 0, 2)

# 4. Test loop to render the display
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