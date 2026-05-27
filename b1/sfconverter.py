from termobjs import *

# class StreamedFileMaker():
#     # StreamableFiles contain pixel data stored in a binary file on disk
#     # Each pixel is stored as 4 bytes (RGBA)
#     # First the width and height is stored as 4 byte unsigned integers (big-endian)
#     # Followed by each PixelContainer's pixel data in row-major order
#     @staticmethod
#     def createStreamedFile(filePath: str, pixelContainers: list[PixelContainer]):
#         with open(filePath, "wb") as f:
#             for pc in pixelContainers:
#                 # Write width and height as 4 byte unsigned integers (big-endian)
#                 f.write(pc.width.to_bytes(4, byteorder='big', signed=False))
#                 f.write(pc.height.to_bytes(4, byteorder='big', signed=False))
#                 # Write pixel data
#                 for y in range(pc.height):
#                     for x in range(pc.width):
#                         pixel = pc.pixels[y][x]
#                         f.write(bytes([pixel.r, pixel.g, pixel.b, pixel.a]))
    
#     @staticmethod
#     def writePixelContainerToStreamableFile(filePath: str, pixelContainer: PixelContainer):
#         StreamedFileMaker.createStreamedFile(filePath, [pixelContainer])
    
#     @staticmethod
#     def writeAnimatedPixelContainerToStreamableFile(filePath: str, animatedPixelContainer: AnimatedPixelContainer):
#         StreamedFileMaker.createStreamedFile(filePath, animatedPixelContainer.frames)

#     @staticmethod
#     def writePillowImageToStreamableFile(filePath: str, image: Image.Image):
#         width, height = image.size
#         # Manually write bytes
#         with open(filePath, "wb") as f:
#             # Write width and height as 4 byte unsigned integers (big-endian)
#             f.write(width.to_bytes(4, byteorder='big', signed=False))
#             f.write(height.to_bytes(4, byteorder='big', signed=False))
#             # Write pixel data
#             for y in range(height):
#                 for x in range(width):
#                     r, g, b, a = image.getpixel((x, y))
#                     f.write(bytes([r, g, b, a]))
    
#     @staticmethod
#     def writePillowGifToStreamableFile(filePath: str, gif: Image.Image):
#         # Get dimensions from first frame
#         gif.seek(0)
#         width, height = gif.size

#         # Write
#         with open(filePath, "wb") as f:
#             # Write just header bytes once
#             f.write(width.to_bytes(4, byteorder='big', signed=False))
#             f.write(height.to_bytes(4, byteorder='big', signed=False))

#             # Now write each frame's pixel data
#             try:
#                 while True:
#                     frame = gif.convert("RGBA")
#                     for y in range(height):
#                         for x in range(width):
#                             r, g, b, a = frame.getpixel((x, y))
#                             f.write(bytes([r, g, b, a]))
#                     gif.seek(gif.tell() + 1)
#             except EOFError:
#                 pass

# Usage: python sfconverter.py <image_or_gif_filepath> <output_streamed_filepath>
# Both paths can be relative or absolute

import sys
from PIL import Image
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python sfconverter.py <image_or_gif_filepath> <output_streamed_filepath>")
        sys.exit(1)

    inputPath = sys.argv[1]
    outputPath = sys.argv[2]

    # Check if input is a GIF
    if inputPath.lower().endswith(".gif"):
        gif = Image.open(inputPath)
        StreamedFileMaker.writePillowGifToStreamableFile(outputPath, gif)
        print(f"Converted GIF '{inputPath}' to StreamedFile '{outputPath}'")
    else:
        # Assume it's an image
        image = Image.open(inputPath).convert("RGBA")
        StreamedFileMaker.writePillowImageToStreamableFile(outputPath, image)
        print(f"Converted Image '{inputPath}' to StreamedFile '{outputPath}'")