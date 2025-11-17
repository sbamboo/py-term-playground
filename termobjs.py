# Terminal Display Buffer with Alpha-Blended Pixel Layers, Text characters and on top of that a basic Object handler
#
# Requires: Pillow (PIL) for image handling
#
# Author: Simon Kalmi Claesson
# License: Private use only, no commercial use without permission
# No warranty, use at your own risk
#
# Version: 0.0.1
# Date: 2025-11-16
#

import os
import math
import sys
import time
from PIL import Image

class RGBPixel():
    def __init__(self, r: int, g: int, b: int):
        self.r = r
        self.g = g
        self.b = b

    def toRGBA(self, a: int = 255):
        return RGBAPixel(self.r, self.g, self.b, a)
    
    def toTuple(self) -> tuple:
        return (self.r, self.g, self.b)

class RGBAPixel():
    def __init__(self, r: int, g: int, b: int, a: int = 255):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def toRGB(self) -> RGBPixel:
        return RGBPixel(self.r, self.g, self.b)

    def toRGBRespectingAlpha(self) -> RGBPixel:
        alpha = self.a / 255.0
        r = int(self.r * alpha)
        g = int(self.g * alpha)
        b = int(self.b * alpha)
        return RGBPixel(r, g, b)

    def toTuple(self) -> tuple:
        return (self.r, self.g, self.b, self.a)


def overlayRGBAs(pixels: list) -> RGBAPixel:
    r_accum, g_accum, b_accum = 0.0, 0.0, 0.0
    alpha_accum = 0.0

    for pixel in pixels:  # bottom-to-top
        alpha = pixel.a / 255.0
        r_accum = pixel.r * alpha + r_accum * (1 - alpha)
        g_accum = pixel.g * alpha + g_accum * (1 - alpha)
        b_accum = pixel.b * alpha + b_accum * (1 - alpha)
        alpha_accum = alpha + alpha_accum * (1 - alpha)

    return RGBAPixel(int(r_accum), int(g_accum), int(b_accum), int(alpha_accum*255))


def overlayRGBs(pixels: list) -> RGBPixel:
    r_accum, g_accum, b_accum = 0, 0, 0

    for pixel in pixels:  # bottom-to-top
        r_accum = pixel.r + r_accum * (1 - 1)
        g_accum = pixel.g + g_accum * (1 - 1)
        b_accum = pixel.b + b_accum * (1 - 1)
    
    return RGBPixel(int(r_accum), int(g_accum), int(b_accum))


# ChannelByChannel averaging - simple mean
def averageRGBAs_cbc(pixels: list) -> RGBAPixel:
    n = len(pixels)
    if n == 0:
        return RGBAPixel(0, 0, 0, 0)

    r = sum(p.r for p in pixels) / n
    g = sum(p.g for p in pixels) / n
    b = sum(p.b for p in pixels) / n
    a = sum(p.a for p in pixels) / n

    return RGBAPixel(int(r), int(g), int(b), int(a))


# Alpha-Weighted averaging
def averageRGBAs_awa(pixels: list) -> RGBAPixel:
    total_alpha = sum(p.a for p in pixels)
    if total_alpha == 0:
        return RGBAPixel(0, 0, 0, 0)

    r = sum(p.r * p.a for p in pixels) / total_alpha
    g = sum(p.g * p.a for p in pixels) / total_alpha
    b = sum(p.b * p.a for p in pixels) / total_alpha
    a = total_alpha / len(pixels)

    return RGBAPixel(int(r), int(g), int(b), int(a))


# Premultiplied RGBA averaging - correct compositing
def averageRGBAs_pma(pixels: list) -> RGBAPixel:
    n = len(pixels)
    if n == 0:
        return RGBAPixel(0, 0, 0, 0)

    r_premul = sum(p.r * (p.a / 255) for p in pixels)
    g_premul = sum(p.g * (p.a / 255) for p in pixels)
    b_premul = sum(p.b * (p.a / 255) for p in pixels)
    a_avg = sum(p.a for p in pixels) / n

    if a_avg == 0:
        return RGBAPixel(0, 0, 0, 0)

    alpha = a_avg / 255
    r = r_premul / n / alpha
    g = g_premul / n / alpha
    b = b_premul / n / alpha

    return RGBAPixel(int(r), int(g), int(b), int(a_avg))


# Perceptual color averaging
def averageRGBAs_pca(pixels: list) -> RGBAPixel:
    def srgb_to_linear(c: float) -> float:
        return (c / 255.0) ** 2.2

    def linear_to_srgb(c: float) -> int:
        return int(max(0, min(255, (c ** (1/2.2)) * 255)))

    n = len(pixels)
    if n == 0:
        return RGBAPixel(0, 0, 0, 0)

    # convert to linear
    r_lin = sum(srgb_to_linear(p.r) for p in pixels) / n
    g_lin = sum(srgb_to_linear(p.g) for p in pixels) / n
    b_lin = sum(srgb_to_linear(p.b) for p in pixels) / n
    a = sum(p.a for p in pixels) / n

    # convert back to sRGB
    r = linear_to_srgb(r_lin)
    g = linear_to_srgb(g_lin)
    b = linear_to_srgb(b_lin)

    return RGBAPixel(r, g, b, int(a))


# Root-mean-square averaging
def averageRGBAs_rms(pixels: list) -> RGBAPixel:
    n = len(pixels)
    if n == 0:
        return RGBAPixel(0, 0, 0, 0)

    r = math.sqrt(sum((p.r ** 2) for p in pixels) / n)
    g = math.sqrt(sum((p.g ** 2) for p in pixels) / n)
    b = math.sqrt(sum((p.b ** 2) for p in pixels) / n)
    a = math.sqrt(sum((p.a ** 2) for p in pixels) / n)

    return RGBAPixel(int(r), int(g), int(b), int(a))


# Physiucally corrcect RGBA averaging - linear + premultiplied
def averageRGBAs_phy(pixels: list) -> RGBAPixel:
    def srgb_to_linear(c: float) -> float:
        """Convert 0–255 sRGB channel to linear-light 0–1."""
        c = c / 255.0
        if c <= 0.04045:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4


    def linear_to_srgb(c: float) -> int:
        """Convert linear-light 0–1 to 0–255 sRGB."""
        if c <= 0.0031308:
            c = 12.92 * c
        else:
            c = 1.055 * (c ** (1 / 2.4)) - 0.055
        return int(max(0, min(255, c * 255)))

    if not pixels:
        return RGBAPixel(0, 0, 0, 0)

    # Accumulators for premultiplied *linear* RGB
    r_acc = 0.0
    g_acc = 0.0
    b_acc = 0.0
    a_acc = 0.0

    for p in pixels:
        a = p.a / 255.0

        # Convert each channel to linear-light
        rl = srgb_to_linear(p.r)
        gl = srgb_to_linear(p.g)
        bl = srgb_to_linear(p.b)

        # Premultiply by alpha
        r_acc += rl * a
        g_acc += gl * a
        b_acc += bl * a
        a_acc += a

    n = len(pixels)
    a_avg = a_acc / n  # averaged alpha in 0–1

    # If the result is fully transparent (or nearly), return transparent black
    if a_avg <= 1e-8:
        return RGBAPixel(0, 0, 0, 0)

    # Unpremultiply
    rl = (r_acc / n) / a_avg
    gl = (g_acc / n) / a_avg
    bl = (b_acc / n) / a_avg

    # Convert back to sRGB
    r = linear_to_srgb(rl)
    g = linear_to_srgb(gl)
    b = linear_to_srgb(bl)
    a = int(a_avg * 255)

    return RGBAPixel(r, g, b, a)

def nearestNeighborScale2DArray(pixels: list, scaleFactor: int) -> list:
    # Nearest neighbor scaling of 2D array of pixels, that expands the size of the 2D array aswell
    if scaleFactor <= 1:
        return pixels
    
    originalHeight = len(pixels)
    originalWidth = len(pixels[0]) if originalHeight > 0 else 0

    newHeight = originalHeight * scaleFactor
    newWidth = originalWidth * scaleFactor

    newPixels = [[None for _ in range(newWidth)] for _ in range(newHeight)]
    for y in range(newHeight):
        for x in range(newWidth):
            origX = x // scaleFactor
            origY = y // scaleFactor
            newPixels[y][x] = pixels[origY][origX]

    return newPixels

class LayeredPixels():
    def __init__(self):
        self.layers = []

    def setLayers(self, pixels: list):
        self.layers = pixels

    def getLayers(self) -> list:
        return self.layers

    def hasLayerIndex(self, index: int) -> bool:
        return 0 <= index < len(self.layers)

    def setPixelAtLayer(self, index: int, pixel: RGBAPixel):
        if self.hasLayerIndex(index):
            self.layers[index] = pixel
        else:
            # Ensure layer
            while len(self.layers) <= index:
                self.layers.append(RGBAPixel(0, 0, 0, 0))
            
            # set
            self.layers[index] = pixel


    def getPixelAtLayer(self, index: int) -> RGBAPixel:
        if self.hasLayerIndex(index):
            return self.layers[index]
        else:
            raise IndexError("Layer index out of range")
    
    def removePixelAtLayer(self, index: int):
        if self.hasLayerIndex(index):
            del self.layers[index]
        else:
            raise IndexError("Layer index out of range")

    def getDepth(self) -> int:
        return len(self.layers)

    def getOverlayed(self) -> RGBAPixel | None:
        if not self.layers or self.getDepth() == 0:
            return None
        return overlayRGBAs(self.layers)

    def clear(self):
        self.layers = []

    def collapse(self):
        overlayed = self.getOverlayed()
        if (overlayed is not None):
            self.setLayers([overlayed])
        else:
            self.clear()

class TermCell():
    def __init__(self, char: str | None, charColor: RGBPixel | RGBAPixel | None, topPixel : LayeredPixels, bottomPixel: LayeredPixels, blendMode = "perceptual-average", respectAlpha = True, defaultBgColor: RGBPixel | None = RGBPixel(0, 0, 0), defaultFgColor: RGBPixel = RGBPixel(255, 255, 255), defaultNoneBgColorBlendBg: RGBPixel = RGBPixel(0, 0, 0)):
        self.char = char
        self.charColor = charColor
        self.topPixel = topPixel
        self.bottomPixel = bottomPixel
        self.blendMode = blendMode
        self.respectAlpha = respectAlpha
        self.defaultBgColor = defaultBgColor
        self.defaultFgColor = defaultFgColor

    def _getOverlayedPixel(self, layeredPixels: LayeredPixels) -> RGBAPixel | None:
        overlayed = layeredPixels.getOverlayed()
        if (overlayed is None):
            if (self.defaultBgColor is None):
                return None
            return self.defaultBgColor.toRGBA(255)
        else:
            return overlayed

    def _toRGB(self, pixel: RGBAPixel | None) -> RGBPixel | None:
        if (pixel is None):
            if (self.defaultBgColor is None):
                return None
            return self.defaultBgColor
        if (self.respectAlpha):
            return pixel.toRGBRespectingAlpha()
        else:
            return pixel.toRGB()

    def blendTextBackground(self) -> RGBPixel | None:
        topPixelOv = self._getOverlayedPixel(self.topPixel)
        bottomPixelOv = self._getOverlayedPixel(self.bottomPixel)

        if (topPixelOv is None and bottomPixelOv is None):
            return None
        if (topPixelOv is None):
            return self._toRGB(bottomPixelOv)
        if (bottomPixelOv is None):
            return self._toRGB(topPixelOv)

        if (self.blendMode == "top"):
            bgPixel = topPixelOv
        elif (self.blendMode == "bottom" or self.blendMode == "bot"):
            bgPixel = bottomPixelOv
        elif (self.blendMode == "average" or self.blendMode == "avg" or self.blendMode == "pca" or self.blendMode == "perceptual" or self.blendMode == "perceptual-average"):
            bgPixel = averageRGBAs_pca([topPixelOv, bottomPixelOv])
        elif (self.blendMode == "cbc" or self.blendMode == "channel-by-channel"):
            bgPixel = averageRGBAs_cbc([topPixelOv, bottomPixelOv])
        elif (self.blendMode == "awa" or self.blendMode == "alpha-weighted"):
            bgPixel = averageRGBAs_awa([topPixelOv, bottomPixelOv])
        elif (self.blendMode == "pma" or self.blendMode == "premultiplied"):
            bgPixel = averageRGBAs_pma([topPixelOv, bottomPixelOv])
        elif (self.blendMode == "rms" or self.blendMode == "root-mean-square"):
            bgPixel = averageRGBAs_rms([topPixelOv, bottomPixelOv])
        elif (self.blendMode == "phy" or self.blendMode == "physical" or self.blendMode == "physically-correct"):
            bgPixel = averageRGBAs_phy([topPixelOv, bottomPixelOv])
        # blendMode = "blend"
        else:
            bgPixel = overlayRGBs([topPixelOv, bottomPixelOv])

        bgPixel = self._toRGB(bgPixel)
        
        return bgPixel

    def toANSI(self):

        # If no character use half-block (▀) where the top pixel is foreground and bottom pixel is background (both converted to RGB)
        # else we blendTextBackground and use the charColor as foreground color
        if (self.char is None):
            if (self.topPixel.getDepth() == 0 and self.bottomPixel.getDepth() == 0):
                return " "

            fgPixel = self._toRGB(self._getOverlayedPixel(self.topPixel))
            bgPixel = self._toRGB(self._getOverlayedPixel(self.bottomPixel))
            if (fgPixel is None):
                # Use other half-block (▄) instead
                char = "▄"
                fgPixel = bgPixel
                bgPixel = None
            else:
                char = "▀"
        else:
            fgPixel = self.charColor if self.charColor is not None else self.defaultFgColor
            bgPixel = self.blendTextBackground()
            if isinstance(fgPixel, RGBAPixel):
                if (bgPixel is None):
                    bgPixel = self.defaultNoneBgColorBlendBg
                fgPixel = self._toRGB(
                    overlayRGBAs([bgPixel.toRGBA(255), fgPixel])
                )
            char = self.char
        
        toReturn = ""
        if (bgPixel is not None):
            toReturn += f"\033[48;2;{bgPixel.r};{bgPixel.g};{bgPixel.b}m"
        if (fgPixel is not None):
            toReturn += f"\033[38;2;{fgPixel.r};{fgPixel.g};{fgPixel.b}m"
        toReturn += char + "\033[0m"
        return toReturn

class TermDisplayBuffer():
    # 2D grid of TermCells
    def __init__(self, width: int, height: int, defaultBlendMode = "perceptual-average", respectAlpha = True, defaultBgColor: RGBPixel | None = RGBPixel(0, 0, 0), defaultFgColor: RGBPixel = RGBPixel(255, 255, 255), defaultNoneBgColorBlendBg: RGBPixel = RGBPixel(0, 0, 0)):
        self.width = width
        self.height = height

        self.defaultBlendMode = defaultBlendMode
        self.respectAlpha = respectAlpha
        self.defaultBgColor = defaultBgColor
        self.defaultFgColor = defaultFgColor
        self.defaultNoneBgColorBlendBg = defaultNoneBgColorBlendBg

        self.clear()
    
    def _getDefaultCell(self) -> TermCell:
        return TermCell(None, None, LayeredPixels(), LayeredPixels(), self.defaultBlendMode, self.respectAlpha, self.defaultBgColor, self.defaultFgColor, self.defaultNoneBgColorBlendBg)

    def clear(self):
        self.grid = [[self._getDefaultCell() for _ in range(self.width)] for _ in range(self.height)]
    
    def setBlendMode(self, blendMode: str):
        self.defaultBlendMode = blendMode
        for y in range(self.height):
            for x in range(self.width):
                cell = self.getCell(x, y)
                cell.blendMode = blendMode
                self.setCell(x, y, cell)

    def setRespectAlpha(self, respectAlpha: bool):
        self.respectAlpha = respectAlpha
        for y in range(self.height):
            for x in range(self.width):
                cell = self.getCell(x, y)
                cell.respectAlpha = respectAlpha
                self.setCell(x, y, cell)

    def setDefaultBgColor(self, color: RGBPixel):
        self.defaultBgColor = color
        for y in range(self.height):
            for x in range(self.width):
                cell = self.getCell(x, y)
                cell.defaultBgColor = color
                self.setCell(x, y, cell)

    def setDefaultFgColor(self, color: RGBPixel):
        self.defaultFgColor = color
        for y in range(self.height):
            for x in range(self.width):
                cell = self.getCell(x, y)
                cell.defaultFgColor = color
                self.setCell(x, y, cell)

    def setCell(self, x: int, y: int, cell: TermCell):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = cell
        else:
            raise IndexError("Cell coordinates out of range")

    def getCell(self, x: int, y: int) -> TermCell:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x]
        else:
            raise IndexError("Cell coordinates out of range")

    def clearCell(self, x: int, y: int):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = self._getDefaultCell()
        else:
            raise IndexError("Cell coordinates out of range")

    def getRenderedCell(self, x: int, y: int) -> str:
        cell = self.getCell(x, y)
        return cell.toANSI()

    def getRenderedBuffer(self) -> str:
        if self.defaultBgColor is None:
            defaultBgAnsi = ""
        else:
            defaultBgAnsi = f"\033[48;2;{self.defaultBgColor.r};{self.defaultBgColor.g};{self.defaultBgColor.b}m"

        rendered_lines = []
        for row in self.grid:
            rendered_line = ''
            for cell in row:
                ansi = cell.toANSI()
                if ansi is None or ansi == '' or ansi == ' ':
                    rendered_line += ' '
                else:
                    rendered_line += ansi + defaultBgAnsi
            rendered_lines.append(rendered_line)

        # Append backgroundColor default at start
        return defaultBgAnsi + '\n'.join(rendered_lines) + "\033[0m"

class TermDisplay(TermDisplayBuffer):
    def __init__(self, width: int, height: int, defaultBlendMode = "perceptual-average", respectAlpha = True, defaultBgColor: RGBPixel | None = RGBPixel(0, 0, 0), defaultFgColor: RGBPixel = RGBPixel(255, 255, 255), defaultNoneBgColorBlendBg: RGBPixel = RGBPixel(0, 0, 0)):
        super().__init__(width, height, defaultBlendMode, respectAlpha, defaultBgColor, defaultFgColor, defaultNoneBgColorBlendBg)

    def getBuffer(self) -> TermDisplayBuffer:
        return self

    def _getCellOfPixelCoords(self, px: int, py: int) -> tuple[int, int]:
        # OOB check
        if px < 0 or py < 0 or px >= self.width or py >= self.height * 2:
            raise IndexError("Pixel coordinates out of range")

        # The emulated "PixelBuffer" is double height of the TermDisplayBuffer but same width
        cellX = px
        cellY = py // 2
        return (cellX, cellY)

    def _getPixelCoordsOfCell(self, x: int, y: int) -> tuple[int, int, int, int]: # returns (topPx, topPy, bottomPx, bottomPy)
        # OOB check
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            raise IndexError("Cell coordinates out of range")

        # Get cell
        cell = self.getCell(x, y)
        cellTopPixel = cell.topPixel
        cellBottomPixel = cell.bottomPixel

        # The emulated "PixelBuffer" is double height of the TermDisplayBuffer, this means everyother pixel row is part of the same cell
        # Width is the same
        topPx = x
        topPy = y * 2
        bottomPx = x
        bottomPy = y * 2 + 1

        return (topPx, topPy, bottomPx, bottomPy)

    def _getCellAndTBByPixelCoords(self, px: int, py: int) -> tuple[int, int, str]:
        cellX, cellY = self._getCellOfPixelCoords(px, py)
        tb = "top" if (py % 2 == 0) else "bottom"
        return (cellX, cellY, tb)

    # Main methods
    def resize(self, newWidth: int, newHeight: int):
        # If smaller cut off excess
        # If larger add default cells but keep existing Top-Left aligned

        newGrid = [[self._getDefaultCell() for _ in range(newWidth)] for _ in range(newHeight)]
        minWidth = min(self.width, newWidth)
        minHeight = min(self.height, newHeight)
        for y in range(minHeight):
            for x in range(minWidth):
                newGrid[y][x] = self.grid[y][x]
        self.width = newWidth
        self.height = newHeight
        self.grid = newGrid

    def getRendered(self) -> str:
        return self.getRenderedBuffer()

    def render(self, printer=print, trailingNewline=True):
        rendered = self.getRenderedBuffer()
        printer(rendered + ("\n" if trailingNewline else ""))

    def renderIO(self, ioStream=sys.stdout):
        rendered = self.getRenderedBuffer()
        ioStream.write(rendered + "\n")


    # Text char methods (TermCell)
    def setChar(self, x: int, y: int, char: str | None):
        cell = self.getCell(x, y)
        cell.char = char
        self.setCell(x, y, cell)

    def setCharColor(self, x: int, y: int, color: RGBPixel | RGBAPixel | None):
        cell = self.getCell(x, y)
        cell.charColor = color
        self.setCell(x, y, cell)

    def getChar(self, x: int, y: int) -> str | None:
        cell = self.getCell(x, y)
        return cell.char

    def getCharColor(self, x: int, y: int) -> RGBPixel | RGBAPixel | None:
        cell = self.getCell(x, y)
        return cell.charColor

    def clearChar(self, x: int, y: int):
        cell = self.getCell(x, y)
        cell.char = None
        cell.charColor = None
        self.setCell(x, y, cell)

    def clearCharColor(self, x: int, y: int):
        cell = self.getCell(x, y)
        cell.charColor = None
        self.setCell(x, y, cell)

    # Pixel Layer methods (TermCell/LayeredPixels)
    def setPixelLayers(self, px: int, py: int, layers: list):
        cellX, cellY, tb = self._getCellAndTBByPixelCoords(px, py)
        cell = self.getCell(cellX, cellY)

        if tb == "top":
            cell.topPixel.setLayers(layers)
        else:
            cell.bottomPixel.setLayers(layers)

        self.setCell(cellX, cellY, cell)

    def getPixelLayers(self, px: int, py: int) -> list:
        cellX, cellY, tb = self._getCellAndTBByPixelCoords(px, py)
        cell = self.getCell(cellX, cellY)

        if tb == "top":
            return cell.topPixel.getLayers()
        else:
            return cell.bottomPixel.getLayers()
        
    def getPixelDepth(self, px: int, py: int) -> int:
        cellX, cellY, tb = self._getCellAndTBByPixelCoords(px, py)
        cell = self.getCell(cellX, cellY)

        if tb == "top":
            return cell.topPixel.getDepth()
        else:
            return cell.bottomPixel.getDepth()
    
    def getPixelOverlayed(self, px: int, py: int) -> RGBAPixel | None:
        cellX, cellY, tb = self._getCellAndTBByPixelCoords(px, py)
        cell = self.getCell(cellX, cellY)

        if tb == "top":
            return cell.topPixel.getOverlayed()
        else:
            return cell.bottomPixel.getOverlayed()

    def clearPixel(self, px: int, py: int):
        cellX, cellY, tb = self._getCellAndTBByPixelCoords(px, py)
        cell = self.getCell(cellX, cellY)

        if tb == "top":
            cell.topPixel.clear()
        else:
            cell.bottomPixel.clear()

        self.setCell(cellX, cellY, cell)

    def collapsePixel(self, px: int, py: int):
        cellX, cellY, tb = self._getCellAndTBByPixelCoords(px, py)
        cell = self.getCell(cellX, cellY)

        if tb == "top":
            cell.topPixel.collapse()
        else:
            cell.bottomPixel.collapse()

        self.setCell(cellX, cellY, cell)

    def setPixelCollapsing(self, px: int, py: int, pixel: RGBAPixel):
        cellX, cellY, tb = self._getCellAndTBByPixelCoords(px, py)
        cell = self.getCell(cellX, cellY)

        # Is the pixel transparent? in that case append to layers then collapse
        if pixel.a < 255:
            if tb == "top":
                cell.topPixel.layers.append(pixel)
                cell.topPixel.collapse()
            else:
                cell.bottomPixel.layers.append(pixel)
                cell.bottomPixel.collapse()

        # Else just set as single layer
        else:
            if tb == "top":
                cell.topPixel.setLayers([pixel])
            else:
                cell.bottomPixel.setLayers([pixel])

        self.setCell(cellX, cellY, cell)

    def replacePixel(self, px: int, py: int, pixel: RGBAPixel):
        self.setPixelLayers(px, py, [pixel])

    # Pixel methods (TermCell/LayeredPixels/levelIndex)
    def pixelHasLayerIndex(self, px: int, py: int, index: int) -> bool:
        cellX, cellY, tb = self._getCellAndTBByPixelCoords(px, py)
        cell = self.getCell(cellX, cellY)

        if tb == "top":
            return cell.topPixel.hasLayerIndex(index)
        else:
            return cell.bottomPixel.hasLayerIndex(index)

    def setPixelAtLayer(self, px: int, py: int, index: int, pixel: RGBAPixel):
        cellX, cellY, tb = self._getCellAndTBByPixelCoords(px, py)
        cell = self.getCell(cellX, cellY)

        if tb == "top":
            cell.topPixel.setPixelAtLayer(index, pixel)
        else:
            cell.bottomPixel.setPixelAtLayer(index, pixel)

        self.setCell(cellX, cellY, cell)

    def getPixelAtLayer(self, px: int, py: int, index: int) -> RGBAPixel:
        cellX, cellY, tb = self._getCellAndTBByPixelCoords(px, py)
        cell = self.getCell(cellX, cellY)

        if tb == "top":
            return cell.topPixel.getPixelAtLayer(index)
        else:
            return cell.bottomPixel.getPixelAtLayer(index)

    def removePixelAtLayer(self, px: int, py: int, index: int):
        cellX, cellY, tb = self._getCellAndTBByPixelCoords(px, py)
        cell = self.getCell(cellX, cellY)

        if tb == "top":
            cell.topPixel.removePixelAtLayer(index)
        else:
            cell.bottomPixel.removePixelAtLayer(index)

        self.setCell(cellX, cellY, cell)

    # Text Helpers
    def placeStringAt(self, x: int, y: int, string: str, charColor: RGBPixel | RGBAPixel | None = None):
        for i, char in enumerate(string):
            if x + i < self.width:
                self.setChar(x + i, y, char)
                if charColor is not None:
                    self.setCharColor(x + i, y, charColor)

    def textFillArea(self, x: int, y: int, width: int, height: int, char: str, onlyIfEmpty: bool = False):
        for j in range(height):
            for i in range(width):
                if 0 <= x + i < self.width and 0 <= y + j < self.height:
                    if onlyIfEmpty:
                        if self.getChar(x + i, y + j) is None:
                            self.setChar(x + i, y + j, char)
                    else:
                        self.setChar(x + i, y + j, char)

    def textClearArea(self, x: int, y: int, width: int, height: int):
        for j in range(height):
            for i in range(width):
                if 0 <= x + i < self.width and 0 <= y + j < self.height:
                    self.clearChar(x + i, y + j)

    def textColorFillArea(self, x: int, y: int, width: int, height: int, charColor: RGBPixel | RGBAPixel):
        for j in range(height):
            for i in range(width):
                if 0 <= x + i < self.width and 0 <= y + j < self.height:
                    self.setCharColor(x + i, y + j, charColor)

    def textColorClearArea(self, x: int, y: int, width: int, height: int):
        for j in range(height):
            for i in range(width):
                if 0 <= x + i < self.width and 0 <= y + j < self.height:
                    self.clearCharColor(x + i, y + j)

    def textFill(self, char: str, onlyIfEmpty: bool = False):
        self.textFillArea(0, 0, self.width, self.height, char, onlyIfEmpty)

    def textClear(self):
        self.textClearArea(0, 0, self.width, self.height)
    
    def textColorFill(charColor: RGBPixel | RGBAPixel):
        self.textColorFillArea(0, 0, self.width, self.height, charColor)
    
    def textColorClear(self):
        self.textColorClearArea(0, 0, self.width, self.height)

    # Pixel Layer Helpers
    def pixelLayerFillArea(self, x: int, y: int, width: int, height: int, layers: list):
        for j in range(height):
            for i in range(width):
                px = x + i
                py = y + j
                if 0 <= px < self.width and 0 <= py < self.height * 2:
                    self.setPixelLayers(px, py, layers)

    def pixelLayerClearArea(self, x: int, y: int, width: int, height: int):
        for j in range(height):
            for i in range(width):
                px = x + i
                py = y + j
                if 0 <= px < self.width and 0 <= py < self.height * 2:
                    self.clearPixel(px, py)

    def pixelLayerCollapseArea(self, x: int, y: int, width: int, height: int):
        for j in range(height):
            for i in range(width):
                px = x + i
                py = y + j
                if 0 <= px < self.width and 0 <= py < self.height * 2:
                    self.collapsePixel(px, py)

    def pixelLayerFill(self, layers: list):
        self.pixelLayerFillArea(0, 0, self.width, self.height * 2, layers)

    def pixelLayerClear(self):
        self.pixelLayerClearArea(0, 0, self.width, self.height * 2)

    def pixelLayerCollapse(self):
        self.pixelLayerCollapseArea(0, 0, self.width, self.height * 2)

    def collapseAllPixels(self):
        for py in range(self.height * 2):
            for px in range(self.width):
                self.collapsePixel(px, py)

    def clearAllPixelLayers(self):
        for py in range(self.height * 2):
            for px in range(self.width):
                self.clearPixel(px, py)

    # Pixel Helpers
    def pixelFillArea(self, x: int, y: int, width: int, height: int, index: int, pixel: RGBAPixel):
        for j in range(height):
            for i in range(width):
                px = x + i
                py = y + j
                if 0 <= px < self.width and 0 <= py < self.height * 2:
                    self.setPixelAtLayer(px, py, index, pixel)

    def pixelClearArea(self, x: int, y: int, width: int, height: int, index: int):
        for j in range(height):
            for i in range(width):
                px = x + i
                py = y + j
                if 0 <= px < self.width and 0 <= py < self.height * 2:
                    self.removePixelAtLayer(px, py, index)
    
    def pixelFillAtLayer(index: int, pixel: RGBAPixel):
        self.pixelFillArea(0, 0, self.width, self.height * 2, index, pixel)

    def pixelClearAtLayer(index: int):
        self.pixelClearArea(0, 0, self.width, self.height * 2, index)

    def getCellDimentions(self) -> tuple[int, int]:
        return (self.width, self.height)

    def getPixelDimentions(self) -> tuple[int, int]:
        return (self.width, self.height * 2)

    

class _2DArray(list):
    pass

class PixelContainer():
    def __init__(self, width: int, height: int, pxScaleFactor: int = 1):
        self.hasChanged = False # Used when PixelContainer is texture
        self.width = width
        self.height = height
        self.pxScaleFactor = pxScaleFactor
        self.clear()
        self.hasBeenSetPixelPositions = [] # List of (x, y) tuples where pixels have been set
        self.positionsSetByScaling = [] # Positions that have been set due to scaling
        self.scaledSetPositions = [] # Positions that have been scaled, i.e their counterparts exists in positionsSetByScaling

    def getHasChanged(self) -> bool:
        return self.hasChanged

    def resetHasChanged(self):
        self.hasChanged = False

    def getPosMarkedAsSet(self) -> list:
        return self.hasBeenSetPixelPositions + self.positionsSetByScaling

    def markPixelPosAsSet(self, x: int, y: int):
        if (x, y) not in self.hasBeenSetPixelPositions:
            self.hasBeenSetPixelPositions.append((x, y))
    
    def unmarkPixelPosAsSet(self, x: int, y: int):
        if (x, y) in self.hasBeenSetPixelPositions:
            self.hasBeenSetPixelPositions.remove((x, y))

    def markAllPixelPosAsSet(self):
        self.hasBeenSetPixelPositions = []
        self.positionsSetByScaling = []
        self.scaledSetPositions = []
        for y in range(self.height):
            for x in range(self.width):
                self.hasBeenSetPixelPositions.append((x, y))
    
    def unmarkAllPixelPosAsSet(self):
        self.hasBeenSetPixelPositions = []
        self.positionsSetByScaling = []
        self.scaledSetPositions = []

    def clear(self):
        self.pixels = [[None for _ in range(self.width)] for _ in range(self.height)]
        self.unmarkAllPixelPosAsSet()
        self.hasChanged = True

    def _getScaledPixels(self) -> _2DArray:
        # Scale the hasBeenSetPixelPositions aswell
        if (self.pxScaleFactor != 1):
            for (x, y) in self.hasBeenSetPixelPositions:
                if (x, y) in self.scaledSetPositions:
                    # Already scaled
                    continue
                for sy in range(self.pxScaleFactor):
                    for sx in range(self.pxScaleFactor):
                        scaledX = x * self.pxScaleFactor + sx
                        scaledY = y * self.pxScaleFactor + sy
                        if (scaledX, scaledY) not in self.positionsSetByScaling:
                            self.positionsSetByScaling.append((scaledX, scaledY))
                            self.scaledSetPositions.append((scaledX, scaledY))
        
        # Return scaled pixels
        return nearestNeighborScale2DArray(self.pixels, self.pxScaleFactor)

    def getScaledDimentions(self) -> tuple[int, int]:
        return (self.width * self.pxScaleFactor, self.height * self.pxScaleFactor)

    def getPixels(self) -> _2DArray:
        if (self.pxScaleFactor != 1):
            return self._getScaledPixels()
        else:
            return self.pixels
    
    def setPixels(self, _2Darray: _2DArray):
        self.height = len(_2Darray)
        self.width = len(_2Darray[0]) if self.height > 0 else 0
        self.pixels = _2Darray
        self.markAllPixelPosAsSet()
        self.hasChanged = True

    def setPixelsNonDimUpdate(self, _2Darray: _2DArray):
        self.pixels = _2Darray
        self.hasChanged = True
        self.markAllPixelPosAsSet()

    def setPixel(self, x: int, y: int, pixel: RGBAPixel):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y][x] = pixel
        else:
            raise IndexError("Pixel coordinates out of range")
        self.markPixelPosAsSet(x, y)
        self.hasChanged = True

    def fill(self, pixel: RGBAPixel):
        for y in range(self.height):
            for x in range(self.width):
                self.pixels[y][x] = pixel
        self.markAllPixelPosAsSet()
        self.hasChanged = True
    
    def setPxScaleFactor(self, scaleFactor: int):
        self.pxScaleFactor = scaleFactor

class TextContainer():
    def __init__(self, string: str, charColor: RGBPixel | RGBAPixel | None = None):
        self.string = string
        self.charColor = charColor
        self.length = len(string)

    def clear(self):
        self.string = ""
        self.charColor = None
        self.length = 0

    def getString(self) -> str:
        return self.string

    def setString(self, string: str):
        self.string = string
        self.length = len(string)

    def getColor(self) -> RGBPixel | RGBAPixel | None:
        return self.charColor
    
    def getLength(self) -> int:
        return self.length

class CompositeContainer():
    # Holds both PixelContainer(s) and TextContainer(s) in a ordered list
    def __init__(self):
        self.objects = []
    
    def addObject(self, obj: PixelContainer | TextContainer):
        self.objects.append(obj)

        return len(self.objects) - 1
    
    def getObject(self, index: int) -> PixelContainer | TextContainer:
        if 0 <= index < len(self.objects):
            return self.objects[index]
        else:
            raise IndexError("Object index out of range")

    def removeObject(self, index: int):
        if 0 <= index < len(self.objects):
            del self.objects[index]
        else:
            raise IndexError("Object index out of range")

    def getObjects(self) -> list:
        return self.objects

class TermDisplayWithObjects():
    # Adds object management above a TermDisplay

    def __init__(self, width: int, height: int, defaultBlendMode = "perceptual-average", respectAlpha = True, defaultBgColor: RGBPixel | None = RGBPixel(0, 0, 0), defaultFgColor: RGBPixel = RGBPixel(255, 255, 255), defaultNoneBgColorBlendBg: RGBPixel = RGBPixel(0, 0, 0)):
        self.termDisplay = TermDisplay(width, height, defaultBlendMode, respectAlpha, defaultBgColor, defaultFgColor, defaultNoneBgColorBlendBg)
        self.objects = {} # Either a PixelContainer or TextContainer
        self.nextObjectID = 0

    def getRenderer(self) -> TermDisplay:
        return self.termDisplay

    def addTextObj(self, obj: TextContainer, topLeftCellX: int, topLeftCellY: int, parent = None) -> int:
        objectID = self.nextObjectID
        self.nextObjectID += 1
        self.objects[objectID] = (obj, topLeftCellX, topLeftCellY, None, None, None, parent) # (obj, cellX, cellY, px, py, "top"/"bottom", parent)
        return objectID

    def addPixelObj(self, obj: PixelContainer, topLeftPX: int, topLeftPY: int, parent = None) -> int:
        # Convert topLeftPX, topLeftPY to cell coords handling the double-height pixel mapping using ._getCellAndTBByPixelCoords
        (cellX, cellY, tb) = self.termDisplay._getCellAndTBByPixelCoords(topLeftPX, topLeftPY)
        objectID = self.nextObjectID
        self.nextObjectID += 1
        self.objects[objectID] = (obj, cellX, cellY, topLeftPX, topLeftPY, tb, parent) # (obj, cellX, cellY, px, py, "top"/"bottom", parent)
        return objectID

    # Return a list of objectIDs added (in order) for all objects in the CompositeContainer
    def addCompositeObj(self, obj: CompositeContainer, topLeftCellX: int, topLeftCellY: int) -> list:
        objectIDs = []
        for subObj in obj.getObjects():
            self.addObject(subObj, topLeftCellX, topLeftCellY, parent=obj)
        return objectIDs

    # Return a list of objectIDs added (in order) for all objects added
    def addObject(self, obj: PixelContainer | TextContainer | CompositeContainer, topLeftCellX: int, topLeftCellY: int, parent = None) -> list:
        if isinstance(obj, TextContainer):
            objectID = self.addTextObj(obj, topLeftCellX, topLeftCellY, parent)
            return [objectID]
        elif isinstance(obj, PixelContainer):
            (topLeftPX, topLeftPY, _, _) = self.termDisplay._getPixelCoordsOfCell(topLeftCellX, topLeftCellY)
            objectID = self.addPixelObj(obj, topLeftPX, topLeftPY, parent)
            return [objectID]
        elif isinstance(obj, CompositeContainer):
            return self.addCompositeObj(obj, topLeftCellX, topLeftCellY)
        else:
            raise TypeError("Object must be a PixelContainer, TextContainer, or CompositeContainer")

    def hasObject(self, objectID: int) -> bool:
        return objectID in self.objects

    def _moveObject(self, objectID: int, newTopLeftCellX: int, newTopLeftCellY: int):
        if objectID in self.objects:
            obj = self.objects[objectID]
            if isinstance(obj[0], TextContainer):
                self.objects[objectID] = (obj[0], newTopLeftCellX, newTopLeftCellY, None, None, None, obj[6])
            elif isinstance(obj[0], PixelContainer):
                (newTopLeftPX, newTopLeftPY, _, _) = self.termDisplay._getPixelCoordsOfCell(newTopLeftCellX, newTopLeftCellY)
                self.objects[objectID] = (obj[0], newTopLeftCellX, newTopLeftCellY, newTopLeftPX, newTopLeftPY, obj[5], obj[6])
        else:
            raise IndexError("Object ID not found")

    def moveObject(self, objectID: int, newTopLeftCellX: int, newTopLeftCellY: int):
        if objectID in self.objects:
            obj = self.objects[objectID]
            parent = obj[6]
            # Does the object have a parent if so move all with the same parent
            if parent is not None:
                for oid, o in self.objects.items():
                    if o[6] == parent:
                        offsetX = o[1] - obj[1]
                        offsetY = o[2] - obj[2]
                        self._moveObject(oid, newTopLeftCellX + offsetX, newTopLeftCellY + offsetY)
            else:
                self._moveObject(objectID, newTopLeftCellX, newTopLeftCellY)
        else:
            raise IndexError("Object ID not found")

    def removeObject(self, objectID: int):
        if objectID in self.objects:
            obj = self.objects[objectID]
            parent = obj[6]
            # Does the object have a parent if so remove all with the same parent
            if parent is not None:
                toRemove = [oid for oid, o in self.objects.items() if o[6] == parent]
                for oid in toRemove:
                    del self.objects[oid]
            else:
                del self.objects[objectID]
        else:
            raise IndexError("Object ID not found")

    def getObjectPos(self, objectID: int) -> tuple[int, int] | list[tuple[int, int]]:
        if objectID in self.objects:
            obj = self.objects[objectID]
            parent = obj[6]
            # Does the object have a parent if so return all with the same parent
            if parent is not None:
                positions = []
                for oid, o in self.objects.items():
                    if o[6] == parent:
                        positions.append((o[1], o[2]))
                return positions
            else:
                return (obj[1], obj[2])
        else:
            raise IndexError("Object ID not found")

    def objectsIntersectingCell(self, cellX: int, cellY: int) -> list[int]:
        objectIDs = []
        for oid, obj in self.objects.items():
            if isinstance(obj[0], TextContainer):
                textObj = obj[0]
                topLeftX = obj[1]
                topLeftY = obj[2]
                lines = textObj.getString().split('\n')
                for j, line in enumerate(lines):
                    for i, char in enumerate(line):
                        if (topLeftX + i == cellX) and (topLeftY + j == cellY):
                            objectIDs.append(oid)
                            break
            elif isinstance(obj[0], PixelContainer):
                pixelObj = obj[0]
                topLeftPX = obj[3]
                topLeftPY = obj[4]
                (scaledWidth, scaledHeight) = pixelObj.getScaledDimentions()
                (cellTopLeftX, cellTopLeftY, _, _) = self.termDisplay._getPixelCoordsOfCell(cellX, cellY)

                # Check if cell overlaps with pixel object's area
                if (cellTopLeftX >= topLeftPX and cellTopLeftX < topLeftPX + scaledWidth and
                    cellTopLeftY >= topLeftPY and cellTopLeftY < topLeftPY + scaledHeight):
                    # Is the pixel at this position None?
                    pixels = pixelObj.getPixels()
                    pixelX = cellTopLeftX - topLeftPX
                    pixelY = cellTopLeftY - topLeftPY
                    if pixels[pixelY][pixelX] is not None:
                        objectIDs.append(oid)

        return objectIDs

    def objectsIntersectingPixel(self, px: int, py: int) -> list[int]:
        objectIDs = []
        for oid, obj in self.objects.items():
            if isinstance(obj[0], PixelContainer):
                pixelObj = obj[0]
                topLeftPX = obj[3]
                topLeftPY = obj[4]
                (scaledWidth, scaledHeight) = pixelObj.getScaledDimentions()

                # Check if pixel overlaps with pixel object's area
                if (px >= topLeftPX and px < topLeftPX + scaledWidth and
                    py >= topLeftPY and py < topLeftPY + scaledHeight):
                    # Is the pixel at this position None?
                    pixels = pixelObj.getPixels()
                    pixelX = px - topLeftPX
                    pixelY = py - topLeftPY
                    if pixels[pixelY][pixelX] is not None:
                        objectIDs.append(oid)
            
            if isinstance(obj[0], TextContainer):
                textObj = obj[0]
                topLeftX = obj[1]
                topLeftY = obj[2]
                (cellTopLeftX, cellTopLeftY, _) = self.termDisplay._getCellAndTBByPixelCoords(px, py)

                # Check if cell overlaps with text object's area
                lines = textObj.getString().split('\n')
                for j, line in enumerate(lines):
                    for i, char in enumerate(line):
                        if (topLeftX + i == cellTopLeftX) and (topLeftY + j == cellTopLeftY):
                            objectIDs.append(oid)
                            break

        return objectIDs

    def textOverlapCheck(self, checkerObjectID: int, checkedAgainstObjectID: int) -> bool:
        # Are both object IDs valid
        if (checkerObjectID not in self.objects or checkedAgainstObjectID not in self.objects):
            raise IndexError("One or both Object IDs not found")

        checkerObj = self.objects[checkerObjectID]
        checkedAgainstObj = self.objects[checkedAgainstObjectID]

        # Both objects must be TextContainers
        if not (isinstance(checkerObj[0], TextContainer) and isinstance(checkedAgainstObj[0], TextContainer)):
            raise TypeError("Both objects must be TextContainers for textOverlapCheck")

        checkerTextObj = checkerObj[0]
        checkerTopLeftX = checkerObj[1]
        checkerTopLeftY = checkerObj[2]
        checkerLines = checkerTextObj.getString().split('\n')

        checkedAgainstTextObj = checkedAgainstObj[0]
        checkedAgainstTopLeftX = checkedAgainstObj[1]
        checkedAgainstTopLeftY = checkedAgainstObj[2]
        checkedAgainstLines = checkedAgainstTextObj.getString().split('\n')

        # Check for overlap
        for j1, line1 in enumerate(checkerLines):
            for i1, char1 in enumerate(line1):
                if char1.isspace():
                    continue
                x1 = checkerTopLeftX + i1
                y1 = checkerTopLeftY + j1

                for j2, line2 in enumerate(checkedAgainstLines):
                    for i2, char2 in enumerate(line2):
                        if char2.isspace():
                            continue
                        x2 = checkedAgainstTopLeftX + i2
                        y2 = checkedAgainstTopLeftY + j2

                        if x1 == x2 and y1 == y2:
                            return True

        return False

    def pixelOverlapCheck(self, checkerObjectID: int, checkedAgainstObjectID: int) -> bool:
        # Get all pixels for both objects
        # If they overlap in any pixel position where both pixels are not None return True else False

        # Are both object IDs valid
        if (checkerObjectID not in self.objects or checkedAgainstObjectID not in self.objects):
            raise IndexError("One or both Object IDs not found")

        checkerObj = self.objects[checkerObjectID]
        checkedAgainstObj = self.objects[checkedAgainstObjectID]

        # Both objects must be PixelContainers
        if not (isinstance(checkerObj[0], PixelContainer) and isinstance(checkedAgainstObj[0], PixelContainer)):
            raise TypeError("Both objects must be PixelContainers for pixelOverlapCheck")

        # Do both objects have getPosMarkedAsSet set? if so just iterate those positions
        checkerObjMarkedPositions = checkerObj[0].getPosMarkedAsSet()
        checkedAgainstObjMarkedPositions = checkedAgainstObj[0].getPosMarkedAsSet()
        if (len(checkerObjMarkedPositions) > 0 and len(checkedAgainstObjMarkedPositions) > 0):
            checkerPixelObj = checkerObj[0]
            checkerPixelObjPixels = checkerPixelObj.getPixels()
            checkerTopLeftPX = checkerObj[3]
            checkerTopLeftPY = checkerObj[4]

            checkedAgainstPixelObj = checkedAgainstObj[0]
            checkedAgainstPixelObjPixels = checkedAgainstPixelObj.getPixels()
            checkedAgainstTopLeftPX = checkedAgainstObj[3]
            checkedAgainstTopLeftPY = checkedAgainstObj[4]

            for (px1, py1) in checkerObjMarkedPositions:
                termPX1 = checkerTopLeftPX + px1
                termPY1 = checkerTopLeftPY + py1
                pixel1 = checkerPixelObjPixels[py1][px1]
                if pixel1 is None:
                    continue

                for (px2, py2) in checkedAgainstObjMarkedPositions:
                    termPX2 = checkedAgainstTopLeftPX + px2
                    termPY2 = checkedAgainstTopLeftPY + py2
                    pixel2 = checkedAgainstPixelObjPixels[py2][px2]
                    if pixel2 is None:
                        continue

                    if termPX1 == termPX2 and termPY1 == termPY2:
                        return True
            return False

        checkerPixelObj = checkerObj[0]
        checkerTopLeftPX = checkerObj[3]
        checkerTopLeftPY = checkerObj[4]
        checkerPixels = checkerPixelObj.getPixels()
        (checkerScaledWidth, checkerScaledHeight) = checkerPixelObj.getScaledDimentions()

        checkedAgainstPixelObj = checkedAgainstObj[0]
        checkedAgainstTopLeftPX = checkedAgainstObj[3]
        checkedAgainstTopLeftPY = checkedAgainstObj[4]
        checkedAgainstPixels = checkedAgainstPixelObj.getPixels()
        (checkedAgainstScaledWidth, checkedAgainstScaledHeight) = checkedAgainstPixelObj.getScaledDimentions()

        # Check for overlap
        for py1 in range(checkerScaledHeight):
            for px1 in range(checkerScaledWidth):
                pixel1 = checkerPixels[py1][px1]
                if pixel1 is None:
                    continue
                termPX1 = checkerTopLeftPX + px1
                termPY1 = checkerTopLeftPY + py1

                for py2 in range(checkedAgainstScaledHeight):
                    for px2 in range(checkedAgainstScaledWidth):
                        pixel2 = checkedAgainstPixels[py2][px2]
                        if pixel2 is None:
                            continue
                        termPX2 = checkedAgainstTopLeftPX + px2
                        termPY2 = checkedAgainstTopLeftPY + py2

                        if termPX1 == termPX2 and termPY1 == termPY2:
                            return True
        return False

    def textAndPixelOverlapCheck(self, textObjectID: int, pixelObjectID: int) -> bool:
        # Are both object IDs valid
        if (textObjectID not in self.objects or pixelObjectID not in self.objects):
            raise IndexError("One or both Object IDs not found")

        textObj = self.objects[textObjectID]
        pixelObj = self.objects[pixelObjectID]

        # Get the pixels covered by the TextContainer
        if not isinstance(textObj[0], TextContainer):
            raise TypeError("First object must be a TextContainer for textAndPixelOverlapCheck")

        textTextObj = textObj[0]

        textTopLeftX = textObj[1]
        textTopLeftY = textObj[2]
        textLines = textTextObj.getString().split('\n')
        coveredPixels = set()
        for j, line in enumerate(textLines):
            for i, char in enumerate(line):
                cellX = textTopLeftX + i
                cellY = textTopLeftY + j
                # use _getPixelCoordsOfCell
                (topPx, topPy, bottomPx, bottomPy) = self.termDisplay._getPixelCoordsOfCell(cellX, cellY)
                coveredPixels.add((topPx, topPy))
                coveredPixels.add((bottomPx, bottomPy))

        # Now check if any of these pixels overlap with non-None pixels in the PixelContainer
        if not isinstance(pixelObj[0], PixelContainer):
            raise TypeError("Second object must be a PixelContainer for textAndPixelOverlapCheck")

        pixelPixelObj = pixelObj[0]

        pixelTopLeftPX = pixelObj[3]
        pixelTopLeftPY = pixelObj[4]
        pixelPixels = pixelPixelObj.getPixels()
        (pixelScaledWidth, pixelScaledHeight) = pixelPixelObj.getScaledDimentions()

        for py in range(pixelScaledHeight):
            for px in range(pixelScaledWidth):
                pixel = pixelPixels[py][px]
                if pixel is None:
                    continue
                termPX = pixelTopLeftPX + px
                termPY = pixelTopLeftPY + py

                if (termPX, termPY) in coveredPixels:
                    return True
        
        return False

    def overlapCheck(self, checkerObjectID: int, checkedAgainstObjectID: int) -> bool:
        # Are both object IDs valid
        if (checkerObjectID not in self.objects or checkedAgainstObjectID not in self.objects):
            raise IndexError("One or both Object IDs not found")
            
        checkerObj = self.objects[checkerObjectID]
        checkedAgainstObj = self.objects[checkedAgainstObjectID]

        # If both objects are text containers do a cell overlap check
        if isinstance(checkerObj[0], TextContainer) and isinstance(checkedAgainstObj[0], TextContainer):
            return self.textOverlapCheck(checkerObjectID, checkedAgainstObjectID)
        
        # If one container is a text container and the other a pixel container, convert text-cells to pixels and do pixel overlap check
        elif isinstance(checkerObj[0], TextContainer) and isinstance(checkedAgainstObj[0], PixelContainer):
            return self.textAndPixelOverlapCheck(checkerObjectID, checkedAgainstObjectID)
        elif isinstance(checkerObj[0], PixelContainer) and isinstance(checkedAgainstObj[0], TextContainer):
            return self.textAndPixelOverlapCheck(checkedAgainstObjectID, checkerObjectID)
        
        # If both containers are pixel containers do a pixel overlap check
        elif isinstance(checkerObj[0], PixelContainer) and isinstance(checkedAgainstObj[0], PixelContainer):
            return self.pixelOverlapCheck(checkerObjectID, checkedAgainstObjectID)

    def isComposite(self, objectID: int) -> bool:
        if objectID in self.objects:
            obj = self.objects[objectID]
            parent = obj[6]
            return parent is not None
        else:
            raise IndexError("Object ID not found")

    def draw(self):
        # If we on draw set the char and charColor .clearText() suffices
        # and for pixels .clearAllPixelLayers() suffices
        self.termDisplay.textClear()
        self.termDisplay.clearAllPixelLayers()

        # Re-apply all objects in order of their objectID (lowest first)
        # Also setting the char and charColor for TextContainers
        for objectID in sorted(self.objects.keys()):
            obj = self.objects[objectID] # (obj, cellX, cellY, px, py, "top"/"bottom")

            if isinstance(obj[0], TextContainer):
                textObj = obj[0]
                cellX = obj[1]
                cellY = obj[2]

                # Split by newline
                lines = textObj.getString().split('\n')

                for j, line in enumerate(lines):
                    # Cut if out of bounds
                    if cellY + j >= self.termDisplay.height:
                        break

                    for i, char in enumerate(line):
                        # Cut if out of bounds
                        if cellX + i >= self.termDisplay.width:
                            break

                        # Is the char a whitespace if so skip
                        if char.isspace():
                            continue

                        if textObj.getString() == "":
                            continue

                        self.termDisplay.setChar(cellX + i, cellY + j, char)
                        if textObj.getColor() is not None:
                            self.termDisplay.setCharColor(cellX + i, cellY + j, textObj.getColor())

            elif isinstance(obj[0], PixelContainer):
                pixelObj = obj[0]
                topLeftPX = obj[3]
                topLeftPY = obj[4]
                # use ID to determine layer index
                layerIndex = objectID

                pixels = pixelObj.getPixels()

                (width, height) = pixelObj.getScaledDimentions() # Ensure we are using scaled dimentions since getPixels() returns scaled pixels for pxScaleFactor != 1

                for py in range(height):
                    for px in range(width):
                        termPX = topLeftPX + px
                        termPY = topLeftPY + py

                        # OOB check
                        if termPX < 0 or termPY < 0 or termPX >= self.termDisplay.width or termPY >= self.termDisplay.height * 2:
                            continue

                        # If py px not exist in pixels continue
                        if py >= len(pixels) or px >= len(pixels[py]):
                            continue

                        pixel = pixels[py][px]
                        if pixel is not None:
                            self.termDisplay.setPixelAtLayer(termPX, termPY, layerIndex, pixel)

    def render(self, printer=print, trailingNewline=True):
        # draw
        self.draw()

        # render
        self.termDisplay.render(printer, trailingNewline)
    
    def renderIO(self, ioStream=sys.stdout):
        # draw
        self.draw()

        # render
        self.termDisplay.renderIO(ioStream)

    def getCellDimentions(self) -> tuple[int, int]:
        return self.termDisplay.getCellDimentions()

    def getPixelDimentions(self) -> tuple[int, int]:
        return self.termDisplay.getPixelDimentions()

class TextWithBg(CompositeContainer):
    def __init__(self, string: str, charColor: RGBPixel, bgColor: RGBAPixel):
        super().__init__()

        # Create PixelContainer for bgColor
        bgPixelContainer = PixelContainer(len(string), 2)
        bgPixelContainer.fill(bgColor)
        self.addObject(bgPixelContainer)

        textObj = TextContainer(string, charColor)
        self.addObject(textObj)

# PixelContainer Builder classes
class Dot(PixelContainer):
    def __init__(self, color: RGBAPixel, pxScaleFactor: int = 1):
        super().__init__(1, 1, pxScaleFactor)
        self.setPixel(0, 0, color)

class Rectangle(PixelContainer):
    def __init__(self, width: int, height: int, color: RGBAPixel, pxScaleFactor: int = 1):
        super().__init__(width, height, pxScaleFactor)
        self.fill(color)

class Square(Rectangle):
    def __init__(self, size: int, color: RGBAPixel):
        super().__init__(size, size, color)

class BoxOutline(PixelContainer):
    def __init__(self, width: int, height: int, thickness: int, color: RGBAPixel, pxScaleFactor: int = 1):
        super().__init__(width, height, pxScaleFactor)
        # Top border
        for y in range(thickness):
            for x in range(width):
                self.setPixel(x, y, color)
        # Bottom border
        for y in range(height - thickness, height):
            for x in range(width):
                self.setPixel(x, y, color)
        # Left border
        for x in range(thickness):
            for y in range(height):
                self.setPixel(x, y, color)
        # Right border
        for x in range(width - thickness, width):
            for y in range(height):
                self.setPixel(x, y, color)

class Line(PixelContainer):
    def __init__(self, xLength: int, yLength: int, thickness: int, color: RGBAPixel, pxScaleFactor: int = 1):
        thickness = thickness//2
        # Bresenham's line algorithm with thickness
        width = abs(xLength) + thickness
        height = abs(yLength) + thickness
        super().__init__(width, height, pxScaleFactor)
        x0, y0 = thickness // 2, thickness // 2
        x1, y1 = xLength + thickness // 2, yLength + thickness // 2
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            # Draw a square of size thickness x thickness centered at (x0, y0)
            for ty in range(-thickness // 2, thickness // 2 + 1):
                for tx in range(-thickness // 2, thickness // 2 + 1):
                    px = x0 + tx
                    py = y0 + ty
                    if 0 <= px < width and 0 <= py < height:
                        self.setPixel(px, py, color)
            if x0 == x1 and y0 == y1:
                break
            err2 = err * 2
            if err2 > -dy:
                err -= dy
                x0 += sx
            if err2 < dx:
                err += dx
                y0 += sy

class Ellipsis(PixelContainer):
    def __init__(self, radiusX: int, radiusY: int, color: RGBAPixel, pxScaleFactor: int = 1):
        width = radiusX * 2 + 1
        height = radiusY * 2 + 1
        super().__init__(width, height, pxScaleFactor)
        cx = radiusX
        cy = radiusY
        for y in range(height):
            for x in range(width):
                # Check if the point is inside the ellipse using the ellipse equation
                if ((x - cx) ** 2) / (radiusX ** 2) + ((y - cy) ** 2) / (radiusY ** 2) <= 1:
                    self.setPixel(x, y, color)

class EllipsisOutline(PixelContainer):
    def __init__(self, radiusX: int, radiusY: int, thickness: int, color: RGBAPixel, pxScaleFactor: int = 1):
        width = radiusX * 2 + 1
        height = radiusY * 2 + 1
        super().__init__(width, height, pxScaleFactor)
        cx = radiusX
        cy = radiusY
        for y in range(height):
            for x in range(width):
                # Check if the point is on the ellipse outline using the ellipse equation
                value = ((x - cx) ** 2) / (radiusX ** 2) + ((y - cy) ** 2) / (radiusY ** 2)
                if 1 - (thickness / max(radiusX, radiusY)) <= value <= 1 + (thickness / max(radiusX, radiusY)):
                    self.setPixel(x, y, color)

class Circle(Ellipsis):
    def __init__(self, radius: int, color: RGBAPixel):
        super().__init__(radius, radius, color)

class CircleOutline(EllipsisOutline):
    def __init__(self, radius: int, thickness: int, color: RGBAPixel):
        super().__init__(radius, radius, thickness, color)

class Polygon(PixelContainer):
    def __init__(self, vertices: list[tuple[int, int]], color: RGBAPixel, pxScaleFactor: int = 1):

        self.vertices = vertices

        minX = min(v[0] for v in vertices)
        maxX = max(v[0] for v in vertices)
        minY = min(v[1] for v in vertices)
        maxY = max(v[1] for v in vertices)

        width = maxX - minX
        height = maxY - minY
        super().__init__(width, height, pxScaleFactor)

        local = [(x - minX, y - minY) for (x, y) in vertices]

        for y in range(height):
            xs = []

            for i in range(len(local)):
                y1 = local[i][1]
                y2 = local[(i + 1) % len(local)][1]

                # ⬅ FIXED edge rule
                if (y1 > y >= y2) or (y2 > y >= y1):
                    x1 = local[i][0]
                    x2 = local[(i + 1) % len(local)][0]
                    t = (y - y1) / (y2 - y1)
                    xs.append(x1 + t * (x2 - x1))

            xs.sort()

            for i in range(0, len(xs), 2):
                x_start = math.ceil(xs[i])
                x_end   = math.floor(xs[i + 1])
                for x in range(x_start, x_end + 1):
                    if 0 <= x < width:
                        self.setPixel(x, y, color)

class PolygonWireframe(PixelContainer):
    def __init__(self, vertices: list[tuple[int, int]], thickness: int, color: RGBAPixel, pxScaleFactor: int = 1):
        # Keep the thickness as-is (centered on lines)
        half_thickness = thickness // 2

        # Calculate bounding box of vertices
        minX = min(v[0] for v in vertices)
        maxX = max(v[0] for v in vertices)
        minY = min(v[1] for v in vertices)
        maxY = max(v[1] for v in vertices)

        # Expand the bounding box by half the thickness to fit all pixels
        width = (maxX - minX + 1) + thickness
        height = (maxY - minY + 1) + thickness
        super().__init__(width, height, pxScaleFactor)

        # Translate vertices to local coordinates inside the expanded bounds
        localVertices = [(x - minX + half_thickness, y - minY + half_thickness) for (x, y) in vertices]

        # Draw edges using Bresenham's line algorithm
        for i in range(len(localVertices)):
            x0, y0 = localVertices[i]
            x1, y1 = localVertices[(i + 1) % len(localVertices)]

            dx = abs(x1 - x0)
            dy = abs(y1 - y0)
            sx = 1 if x0 < x1 else -1
            sy = 1 if y0 < y1 else -1
            err = dx - dy

            while True:
                # Draw a square of size thickness x thickness centered at the pixel
                for ty in range(-half_thickness, half_thickness + 1):
                    for tx in range(-half_thickness, half_thickness + 1):
                        px = x0 + tx
                        py = y0 + ty
                        if 0 <= px < width and 0 <= py < height:
                            self.setPixel(px, py, color)

                if x0 == x1 and y0 == y1:
                    break
                err2 = err * 2
                if err2 > -dy:
                    err -= dy
                    x0 += sx
                if err2 < dx:
                    err += dx
                    y0 += sy


class Triangle(Polygon):
    def __init__(self, vertex1: tuple[int, int], vertex2: tuple[int, int], vertex3: tuple[int, int], color: RGBAPixel):
        super().__init__([vertex1, vertex2, vertex3], color)

class TriangleWireframe(PolygonWireframe):
    def __init__(self, vertex1: tuple[int, int], vertex2: tuple[int, int], vertex3: tuple[int, int], thickness: int, color: RGBAPixel):
        super().__init__([vertex1, vertex2, vertex3], thickness, color)

class ImageContainer(PixelContainer):
    def __init__(self, imagePath: str, width = None, height = None, scalerAlgorithm = Image.NEAREST, cullInvisPixels = True, pxScaleFactor: int = 1):
        if imagePath is not None:
            img = Image.open(imagePath).convert("RGBA")
            if width is not None and height is not None:
                img = img.resize((width, height), scalerAlgorithm)
            elif width is not None:
                aspectRatio = img.height / img.width
                height = int(width * aspectRatio)
                img = img.resize((width, height), scalerAlgorithm)
            elif height is not None:
                aspectRatio = img.width / img.height
                width = int(height * aspectRatio)
                img = img.resize((width, height), scalerAlgorithm)
            else:
                width, height = img.size
            super().__init__(width, height, pxScaleFactor)
            for y in range(height):
                for x in range(width):
                    r, g, b, a = img.getpixel((x, y))
                    if cullInvisPixels and a == 0:
                        continue
                    self.setPixel(x, y, RGBAPixel(r, g, b, a))


class AnimatedPixelContainer(PixelContainer):
    def __init__(self, frames: list, delayMs = 100, loop = True, pxScaleFactor: int = 1):
        self.frames = frames
        self.delayMs = delayMs
        self.loop = loop
        self.currentFrameIndex = 0
        self.lastFrameTime = time.time()
        self.running = True

        super().__init__(frames[0].width, frames[0].height, pxScaleFactor)

    def getPixels(self) -> _2DArray:
        if self.running:
            currentTime = time.time()
            if currentTime - self.lastFrameTime >= self.delayMs / 1000.0:
                self.currentFrameIndex += 1
                if self.currentFrameIndex >= len(self.frames):
                    if self.loop:
                        self.currentFrameIndex = 0
                    else:
                        self.currentFrameIndex = len(self.frames) - 1
                self.lastFrameTime = currentTime
    
        self.setPixelsNonDimUpdate(self.frames[self.currentFrameIndex].getPixels())
        if (self.pxScaleFactor != 1):
            return self._getScaledPixels()
        else:
            return self.pixels

    def reset(self):
        self.currentFrameIndex = 0
        self.lastFrameTime = time.time()
    
    def getFrameCount(self) -> int:
        return len(self.frames)
    
    def stop(self):
        self.running = False

    def start(self):
        self.running = True

def printNoNewline(text: str):
    print(text, end='')

class GIFImageContainer(AnimatedPixelContainer):
    def __init__(self, gifPath: str, width = None, height = None, scalerAlgorithm = Image.NEAREST, defaultDelayMs = 100, loop = True, cullInvisPixels = True, pxScaleFactor: int = 1, printProgress = False, printer=lambda x: print(x, end='')):
        img = Image.open(gifPath)
        frames = []
        processedFrames = 0
        try:
            while True:
                frame = img.convert("RGBA")
                if width is not None and height is not None:
                    frame = frame.resize((width, height), scalerAlgorithm)
                elif width is not None:
                    aspectRatio = frame.height / frame.width
                    height = int(width * aspectRatio)
                    frame = frame.resize((width, height), scalerAlgorithm)
                elif height is not None:
                    aspectRatio = frame.width / frame.height
                    width = int(height * aspectRatio)
                    frame = frame.resize((width, height), scalerAlgorithm)
                else:
                    width, height = frame.size

                pixelContainer = PixelContainer(width, height)
                for y in range(height):
                    for x in range(width):
                        r, g, b, a = frame.getpixel((x, y))
                        if cullInvisPixels and a == 0:
                            continue
                        pixelContainer.setPixel(x, y, RGBAPixel(r, g, b, a))
                frames.append(pixelContainer)

                processedFrames += 1
                if printProgress:
                    printer(f"\rProcessed frame {processedFrames}/{img.n_frames} {(processedFrames/img.n_frames)*100:.2f}%")
            
                img.seek(img.tell() + 1)
        except EOFError:
            if printProgress:
                printer(f"\rFinished processing {frame_count} frames\n")

        # Get delay from GIF info (in milliseconds)
        delayMs = img.info.get('duration', defaultDelayMs)

        super().__init__(frames, delayMs, loop, pxScaleFactor)

class StreamedFileMaker():
    # StreamableFiles contain pixel data stored in a binary file on disk
    # Each pixel is stored as 4 bytes (RGBA)
    # First the width and height is stored as 4 byte unsigned integers (big-endian)
    # Followed by each PixelContainer's pixel data in row-major order
    @staticmethod
    def createStreamedFile(filePath: str, pixelContainers: list[PixelContainer]):
        with open(filePath, "wb") as f:
            for pc in pixelContainers:
                # Write width and height as 4 byte unsigned integers (big-endian)
                f.write(pc.width.to_bytes(4, byteorder='big', signed=False))
                f.write(pc.height.to_bytes(4, byteorder='big', signed=False))
                # Write pixel data
                for y in range(pc.height):
                    for x in range(pc.width):
                        pixel = pc.pixels[y][x]
                        if pixel is None:
                            f.write(bytes([0, 0, 0, 0]))
                        else:
                            f.write(bytes([pixel.r, pixel.g, pixel.b, pixel.a]))
    
    @staticmethod
    def writePixelContainerToStreamableFile(filePath: str, pixelContainer: PixelContainer):
        StreamedFileMaker.createStreamedFile(filePath, [pixelContainer])
    
    @staticmethod
    def writeAnimatedPixelContainerToStreamableFile(filePath: str, animatedPixelContainer: AnimatedPixelContainer):
        StreamedFileMaker.createStreamedFile(filePath, animatedPixelContainer.frames)

    @staticmethod
    def writePillowImageToStreamableFile(filePath: str, image: Image.Image):
        width, height = image.size
        # Manually write bytes
        with open(filePath, "wb") as f:
            # Write width and height as 4 byte unsigned integers (big-endian)
            f.write(width.to_bytes(4, byteorder='big', signed=False))
            f.write(height.to_bytes(4, byteorder='big', signed=False))
            # Write pixel data
            for y in range(height):
                for x in range(width):
                    r, g, b, a = image.getpixel((x, y))
                    f.write(bytes([r, g, b, a]))
    
    @staticmethod
    def writePillowGifToStreamableFile(filePath: str, gif: Image.Image):
        # Get dimensions from first frame
        gif.seek(0)
        width, height = gif.size

        # Write
        with open(filePath, "wb") as f:
            # Write just header bytes once
            f.write(width.to_bytes(4, byteorder='big', signed=False))
            f.write(height.to_bytes(4, byteorder='big', signed=False))

            # Now write each frame's pixel data
            try:
                while True:
                    frame = gif.convert("RGBA")
                    for y in range(height):
                        for x in range(width):
                            r, g, b, a = frame.getpixel((x, y))
                            f.write(bytes([r, g, b, a]))
                    gif.seek(gif.tell() + 1)
            except EOFError:
                pass
        

def readStreamedFileNext(filePath: str, frameIndex = 0, width:int=0,height:int=0) -> tuple[int, int, PixelContainer]: # Returns (width, height, PixelContainer)
    # True stream in the file without loading all frames into memory
    # If frameIndex is 0 read the width/height header from the file then read one single frame (width*height*4 bytes) then return
    #   else read the requested frame (width*height*4 bytes) and return
    with open(filePath, "rb") as f:
        if frameIndex == 0:
            widthBytes = f.read(4)
            heightBytes = f.read(4)
            width = int.from_bytes(widthBytes, byteorder='big', signed=False)
            height = int.from_bytes(heightBytes, byteorder='big', signed=False)
        else:
            if width == 0 or height == 0:
                raise ValueError("Width and Height must be provided for non-zero frameIndex")

        # Seek to the requested frame
        frameSize = width * height * 4
        f.seek((frameIndex) * (frameSize + 8) + 8) # +8 to skip the first width/height header

        pixelContainer = PixelContainer(width, height)

        for y in range(height):
            for x in range(width):
                pixelBytes = f.read(4)
                r = pixelBytes[0]
                g = pixelBytes[1]
                b = pixelBytes[2]
                a = pixelBytes[3]
                pixelContainer.setPixel(x, y, RGBAPixel(r, g, b, a))

        return (width, height, pixelContainer)

class StreamedFilePixelContainer(PixelContainer):
    # Reads a single frame from a StreamedFile apon load
    def __init__(self, filePath: str, frameIndex = 0, cullInvisPixels = True, pxScaleFactor: int = 1):
        (width, height, pixelContainer) = readStreamedFileNext(filePath, frameIndex)
        super().__init__(width, height, pxScaleFactor)
        if cullInvisPixels:
            for y in range(height):
                for x in range(width):
                    pixel = pixelContainer.pixels[y][x]
                    if pixel is not None and pixel.a != 0:
                        self.setPixel(x, y, pixel)
        else:
            self.setPixelsNonDimUpdate(pixelContainer.pixels)

class StreamedFileAnimatedPixelContainer(AnimatedPixelContainer):
    # Read first frame to get width,height,firstFrame on load then inside getPixels read next frames on demand
    def __init__(self, filePath: str, delayMs = 100, loop = True, cullInvisPixels = True, pxScaleFactor: int = 1):
        (width, height, firstFrame) = readStreamedFileNext(filePath, 0)
        self.filePath = filePath
        self.totalFrames = self._getTotalFrames()
        frames = [firstFrame]
        super().__init__(frames, delayMs, loop, pxScaleFactor)

    def _getTotalFrames(self) -> int:
        fileSize = os.path.getsize(self.filePath)
        # Each frame is width*height*4 + 8 bytes (width and height header)
        # So totalFrames is fileSize - header, divided by frameSize
        with open(self.filePath, "rb") as f:
            widthBytes = f.read(4)
            heightBytes = f.read(4)
            width = int.from_bytes(widthBytes, byteorder='big', signed=False)
            height = int.from_bytes(heightBytes, byteorder='big', signed=False)
            frameSize = width * height * 4 + 8
            totalFrames = (fileSize - 8) // frameSize
            self.width = width
            self.height = height
        
        return totalFrames

    def getPixels(self) -> _2DArray:
        if self.running:
            currentTime = time.time()
            if currentTime - self.lastFrameTime >= self.delayMs / 1000.0:
                self.currentFrameIndex += 1
                if self.currentFrameIndex >= self.totalFrames:
                    if self.loop:
                        self.currentFrameIndex = 0
                    else:
                        self.currentFrameIndex = self.totalFrames - 1
                self.lastFrameTime = currentTime

        (width, height, pixelContainer) = readStreamedFileNext(self.filePath, self.currentFrameIndex, self.width, self.height)
        if cullInvisPixels:
            for y in range(height):
                for x in range(width):
                    pixel = pixelContainer.pixels[y][x]
                    if pixel is not None and pixel.a != 0:
                        self.setPixel(x, y, pixel)
                    else:
                        self.pixels[y][x] = None
        else:
            self.setPixelsNonDimUpdate(pixelContainer.pixels)

        if (self.pxScaleFactor != 1):
            return self._getScaledPixels()
        else:
            return self.pixels

class TexturedLine(PixelContainer):
    # Anchors: "center", "topleft", "topright", "bottomleft", "bottomright"
    def __init__(self, xLength: int, yLength: int, thickness: int, texture: PixelContainer, anchor = "center", pxScaleFactor: int = 1):
        self.texture = texture
        self.anchor = anchor
        self.xLength = xLength
        self.yLength = yLength
        self.thickness = thickness

        width = abs(xLength) + 1
        height = abs(yLength) + 1
        super().__init__(width, height, pxScaleFactor)

        self._applyTexture()
    
    def _applyTexture(self):
        self.clear()

        textureWidth = self.texture.width
        textureHeight = self.texture.height
        texturePixels = self.texture.getPixels()

        # Determine texture offset based on anchor
        if self.anchor == "center":
            offsetX = (self.width - textureWidth) // 2
            offsetY = (self.height - textureHeight) // 2
        elif self.anchor == "topleft":
            offsetX = 0
            offsetY = 0
        elif self.anchor == "topright":
            offsetX = self.width - textureWidth
            offsetY = 0
        elif self.anchor == "bottomleft":
            offsetX = 0
            offsetY = self.height - textureHeight
        elif self.anchor == "bottomright":
            offsetX = self.width - textureWidth
            offsetY = self.height - textureHeight
        else:
            raise ValueError("Invalid anchor value")

        # Bresenham's line algorithm with thickness
        thickness = self.thickness // 2
        x0, y0 = thickness // 2, thickness // 2
        x1, y1 = self.xLength + thickness // 2, self.yLength + thickness // 2
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            # Draw a square of size thickness x thickness centered at (x0, y0)
            for ty in range(-thickness // 2, thickness // 2 + 1):
                for tx in range(-thickness // 2, thickness // 2 + 1):
                    px = x0 + tx
                    py = y0 + ty
                    if 0 <= px < self.width and 0 <= py < self.height:
                        texX = px - offsetX
                        texY = py - offsetY
                        if 0 <= texX < textureWidth and 0 <= texY < textureHeight:
                            pixel = texturePixels[texY][texX]
                            if pixel is not None:
                                self.setPixel(px, py, pixel)
            if x0 == x1 and y0 == y1:
                break
            err2 = err * 2
            if err2 > -dy:
                err -= dy
                x0 += sx
            if err2 < dx:
                err += dx
                y0 += sy

    def getPixels(self) -> _2DArray:
        # If texture has changed reapply texture
        if self.texture.getHasChanged():
            self.texture.resetHasChanged()
            
            self._applyTexture()

        return super().getPixels()

class TexturedRectangle(PixelContainer):
    # Anchors: "center", "topleft", "topright", "bottomleft", "bottomright"
    def __init__(self, width: int, height: int, texture: PixelContainer, anchor = "center", pxScaleFactor: int = 1):
        self.texture = texture
        self.anchor = anchor
        self.width = width
        self.height = height

        super().__init__(width, height, pxScaleFactor)

        self._applyTexture()

    def _applyTexture(self):
        self.clear()

        textureWidth = self.texture.width
        textureHeight = self.texture.height
        texturePixels = self.texture.getPixels()

        # Determine texture offset based on anchor
        if self.anchor == "center":
            offsetX = (self.width - textureWidth) // 2
            offsetY = (self.height - textureHeight) // 2
        elif self.anchor == "topleft":
            offsetX = 0
            offsetY = 0
        elif self.anchor == "topright":
            offsetX = self.width - textureWidth
            offsetY = 0
        elif self.anchor == "bottomleft":
            offsetX = 0
            offsetY = self.height - textureHeight
        elif self.anchor == "bottomright":
            offsetX = self.width - textureWidth
            offsetY = self.height - textureHeight
        else:
            raise ValueError("Invalid anchor value")

        for y in range(self.height):
            for x in range(self.width):
                texX = x - offsetX
                texY = y - offsetY
                if 0 <= texX < textureWidth and 0 <= texY < textureHeight:
                    pixel = texturePixels[texY][texX]
                    if pixel is not None:
                        self.setPixel(x, y, pixel)

    def getPixels(self) -> _2DArray:
        # If texture has changed reapply texture
        if self.texture.getHasChanged():
            self.texture.resetHasChanged()
            
            self._applyTexture()

        return super().getPixels()

class TexturedSquare(TexturedRectangle):
    def __init__(self, size: int, texture: PixelContainer, anchor = "center", pxScaleFactor: int = 1):
        super().__init__(size, size, texture, anchor, pxScaleFactor)

class TexturedDot(TexturedRectangle):
    def __init__(self, texture: PixelContainer, anchor = "center", pxScaleFactor: int = 1):
        super().__init__(1, 1, texture, anchor, pxScaleFactor)

class TexturedEllipsis(PixelContainer):
    # Anchors: "center", "topleft", "topright", "bottomleft", "bottomright"
    def __init__(self, radiusX: int, radiusY: int, texture: PixelContainer, anchor = "center", pxScaleFactor: int = 1):
        self.texture = texture
        self.anchor = anchor
        self.radiusX = radiusX
        self.radiusY = radiusY

        width = radiusX * 2 + 1
        height = radiusY * 2 + 1
        super().__init__(width, height, pxScaleFactor)

        self._applyTexture()
    
    def _applyTexture(self):
        self.clear()

        cx = self.radiusX
        cy = self.radiusY

        width = self.radiusX * 2 + 1
        height = self.radiusY * 2 + 1

        textureWidth = self.texture.width
        textureHeight = self.texture.height
        texturePixels = self.texture.getPixels()

        # Determine texture offset based on anchor
        if self.anchor == "center":
            offsetX = cx - textureWidth // 2
            offsetY = cy - textureHeight // 2
        elif self.anchor == "topleft":
            offsetX = 0
            offsetY = 0
        elif self.anchor == "topright":
            offsetX = width - textureWidth
            offsetY = 0
        elif self.anchor == "bottomleft":
            offsetX = 0
            offsetY = height - textureHeight
        elif self.anchor == "bottomright":
            offsetX = width - textureWidth
            offsetY = height - textureHeight
        else:
            raise ValueError("Invalid anchor value")

        for y in range(height):
            for x in range(width):
                # Check if the point is inside the ellipse using the ellipse equation
                if ((x - cx) ** 2) / (self.radiusX ** 2) + ((y - cy) ** 2) / (self.radiusY ** 2) <= 1:
                    texX = x - offsetX
                    texY = y - offsetY
                    if 0 <= texX < textureWidth and 0 <= texY < textureHeight:
                        pixel = texturePixels[texY][texX]
                        if pixel is not None:
                            self.setPixel(x, y, pixel)

    def getPixels(self) -> _2DArray:
        # If texture has changed reapply texture
        if self.texture.getHasChanged():
            self.texture.resetHasChanged()
            
            self._applyTexture()

        return super().getPixels()

class TexturedCircle(TexturedEllipsis):
    def __init__(self, radius: int, texture: PixelContainer, anchor = "center", pxScaleFactor: int = 1):
        super().__init__(radius, radius, texture, anchor, pxScaleFactor)

class TexturedPolygon(PixelContainer):
    # Anchors: "center", "topleft", "topright", "bottomleft", "bottomright"
    def __init__(self, vertices: list[tuple[int, int]], texture: PixelContainer, anchor = "center", pxScaleFactor: int = 1):
        self.texture = texture
        self.anchor = anchor
        self.vertices = vertices

        minX = min(v[0] for v in vertices)
        maxX = max(v[0] for v in vertices)
        minY = min(v[1] for v in vertices)
        maxY = max(v[1] for v in vertices)

        self.width = maxX - minX + 1
        self.height = maxY - minY + 1
        super().__init__(self.width, self.height, pxScaleFactor)

        # Shift vertices into container space
        self.localVertices = [(x - minX, y - minY) for x, y in vertices]

        self._applyTexture()

    
    # def _applyTexture(self):
    #     self.clear()

    #     width = self.width
    #     height = self.height

    #     textureWidth = self.texture.width
    #     textureHeight = self.texture.height
    #     texturePixels = self.texture.getPixels()

    #     # Determine texture offset based on anchor
    #     if self.anchor == "center":
    #         offsetX = (width - textureWidth) // 2
    #         offsetY = (height - textureHeight) // 2
    #     elif self.anchor == "topleft":
    #         offsetX = 0
    #         offsetY = 0
    #     elif self.anchor == "topright":
    #         offsetX = width - textureWidth
    #         offsetY = 0
    #     elif self.anchor == "bottomleft":
    #         offsetX = 0
    #         offsetY = height - textureHeight
    #     elif self.anchor == "bottomright":
    #         offsetX = width - textureWidth
    #         offsetY = height - textureHeight
    #     else:
    #         raise ValueError("Invalid anchor value")

    #     localVertices = [(x, y) for (x, y) in self.vertices]

    #     for y in range(height):
    #         xs = []

    #         for i in range(len(localVertices)):
    #             y1 = localVertices[i][1]
    #             y2 = localVertices[(i + 1) % len(localVertices)][1]

    #             # FIXED edge rule
    #             if (y1 > y >= y2) or (y2 > y >= y1):
    #                 x1 = localVertices[i][0]
    #                 x2 = localVertices[(i + 1) % len(localVertices)][0]
    #                 t = (y - y1) / (y2 - y1)
    #                 xs.append(x1 + t * (x2 - x1))

    #         xs.sort()

    #         for i in range(0, len(xs), 2):
    #             x_start = math.ceil(xs[i])
    #             x_end   = math.floor(xs[i + 1])
    #             for x in range(x_start, x_end + 1):
    #                 texX = x - offsetX
    #                 texY = y - offsetY
    #                 if 0 <= texX < textureWidth and 0 <= texY < textureHeight:
    #                     pixel = texturePixels[texY][texX]
    #                     if pixel is not None:
    #                         self.setPixel(x, y, pixel)

    def _applyTexture(self):
        self.clear()

        width = self.width
        height = self.height

        texturePixels = self.texture.getPixels()
        textureWidth = self.texture.width
        textureHeight = self.texture.height

        # Compute polygon vertices relative to container
        minX = min(v[0] for v in self.vertices)
        minY = min(v[1] for v in self.vertices)
        localVertices = [(x - minX, y - minY) for x, y in self.vertices]

        # Determine anchor offset
        if self.anchor == "center":
            offsetX = (width - textureWidth) // 2
            offsetY = (height - textureHeight) // 2
        elif self.anchor == "topleft":
            offsetX = 0
            offsetY = 0
        elif self.anchor == "topright":
            offsetX = width - textureWidth
            offsetY = 0
        elif self.anchor == "bottomleft":
            offsetX = 0
            offsetY = height - textureHeight
        elif self.anchor == "bottomright":
            offsetX = width - textureWidth
            offsetY = height - textureHeight
        else:
            raise ValueError("Invalid anchor value")

        for y in range(height):
            xs = []

            # Scanline intersection
            for i in range(len(localVertices)):
                x1, y1 = localVertices[i]
                x2, y2 = localVertices[(i + 1) % len(localVertices)]

                if (y1 > y >= y2) or (y2 > y >= y1):
                    t = (y - y1) / (y2 - y1)
                    xs.append(x1 + t * (x2 - x1))

            xs.sort()

            for i in range(0, len(xs), 2):
                x_start = math.ceil(xs[i])
                x_end = math.floor(xs[i + 1])
                for x in range(x_start, x_end + 1):
                    # Map polygon coordinates to texture coordinates with anchor offset
                    texX = int((x - offsetX) / max(1, width - 1) * (textureWidth - 1))
                    texY = int((y - offsetY) / max(1, height - 1) * (textureHeight - 1))

                    # Clamp texture coordinates to valid range
                    texX = max(0, min(texX, textureWidth - 1))
                    texY = max(0, min(texY, textureHeight - 1))

                    pixel = texturePixels[texY][texX]
                    if pixel is not None:
                        self.setPixel(x, y, pixel)

    # def _applyTexture(self):
    #     self.clear()

    #     width = self.width
    #     height = self.height

    #     texturePixels = self.texture.getPixels()
    #     textureWidth = self.texture.width
    #     textureHeight = self.texture.height

    #     # Compute polygon vertices relative to container (0..width-1, 0..height-1)
    #     minX = min(v[0] for v in self.vertices)
    #     minY = min(v[1] for v in self.vertices)
    #     localVertices = [(x - minX, y - minY) for x, y in self.vertices]

    #     for y in range(height):
    #         xs = []

    #         # Scanline intersection with polygon edges
    #         for i in range(len(localVertices)):
    #             x1, y1 = localVertices[i]
    #             x2, y2 = localVertices[(i + 1) % len(localVertices)]

    #             if (y1 > y >= y2) or (y2 > y >= y1):
    #                 t = (y - y1) / (y2 - y1)
    #                 xs.append(x1 + t * (x2 - x1))

    #         xs.sort()

    #         for i in range(0, len(xs), 2):
    #             x_start = math.ceil(xs[i])
    #             x_end = math.floor(xs[i + 1])
    #             for x in range(x_start, x_end + 1):
    #                 # Map polygon coordinates to texture coordinates (stretch texture)
    #                 texX = int((x / max(1, width - 1)) * (textureWidth - 1))
    #                 texY = int((y / max(1, height - 1)) * (textureHeight - 1))

    #                 pixel = texturePixels[texY][texX]
    #                 if pixel is not None:
    #                     self.setPixel(x, y, pixel)

    def getPixels(self) -> _2DArray:
        # If texture has changed reapply texture
        if self.texture.getHasChanged():
            self.texture.resetHasChanged()
            
            self._applyTexture()

        return super().getPixels()

class TexturedTriangle(TexturedPolygon):
    def __init__(self, vertex1: tuple[int, int], vertex2: tuple[int, int], vertex3: tuple[int, int], texture: PixelContainer, anchor = "center", pxScaleFactor: int = 1):
        super().__init__([vertex1, vertex2, vertex3], texture, anchor, pxScaleFactor)