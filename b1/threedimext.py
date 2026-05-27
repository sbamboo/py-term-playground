# Description: A module that provides a handling of 3Dimensional objects as pixel containers. By adding rasterization and projection capabilities inside the getPixels methods.
# Requires: opencv-python

import math

from termobjs import CompositeContainer, PixelContainer, RGBAPixel, _2DArray, Polygon, PolygonWireframe, TexturedPolygon

class Vector3:
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

    def toTuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def __add__(self, other):
        return (self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return (self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float):
        return (self.x * scalar, self.y * scalar, self.z * scalar)

    def dot(self, other) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other):
        return (
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

    def length(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self):
        len = self.length()
        if len == 0:
            return (0, 0, 0)
        return (self.x / len, self.y / len, self.z / len)

class Context3D():
    def __init__(self, displayWidth: int, displayHeight: int, fovDegrees: float = 90.0):
        self.displayWidth = displayWidth
        self.displayHeight = displayHeight
        self.fovDegrees = fovDegrees

    def projectVertices(self, vertices: list[Vector3]) -> list[tuple[int, int]]:
        
        projected = []

        # Focal length based on field of view (FOV)
        f = 1.0 / math.tan(math.radians(self.fovDegrees) / 2)

        for v in vertices:
            # Prevent division by zero
            if v.z == 0:
                continue

            # Perspective projection (simple camera looking down -Z)
            u = (v.x * f) / -v.z   # normalized x
            w = (v.y * f) / -v.z   # normalized y

            # Convert normalized (-1..1) → pixel coordinates
            X = int((u + 1) * 0.5 * self.displayWidth)
            Y = int((1 - w) * 0.5 * self.displayHeight)

            projected.append((X, Y))

        return projected

    def unProjectVertices(self, projectedVertices: list[tuple[int, int]], z: float) -> list[Vector3]:
        unprojected = []

        f = 1.0 / math.tan(math.radians(self.fovDegrees) / 2)

        for (X, Y) in projectedVertices:
            u = (2 * X) / self.displayWidth - 1
            w = 1 - (2 * Y) / self.displayHeight

            x = (u * z) / f
            y = (w * z) / f
            z = z

            unprojected.append(Vector3(x, y, z))

        return unprojected

# Base 3D Object with projection capabilities, a PixelContainer that contains 3D data
# Turns a 3D Face into a 2D polygon by projecting its vertices
# Only works as planar mapping for now (breaks when more then 3 vertices are used and not on same z plane)
class Polygon3D(PixelContainer):
    def __init__(self, ctx: Context3D, vertices: list[Vector3], color: RGBAPixel, pxScaleFactor: int = 1):
        self.ctx = ctx

        self.color = color
        self.pxScaleFactor = pxScaleFactor

        self.setVertices(vertices)

        self.set2DPolygon()

        super().__init__(self.width, self.height, pxScaleFactor)

    def postProjection(self):
        pass

    def setVertices(self, vertices: list[Vector3]):
        projectedVertices = self.ctx.projectVertices(vertices)
        if projectedVertices is None or len(projectedVertices) != len(vertices):
            raise ValueError("Projection resulted in invalid number of vertices, was any vertex at z=0?")
        self.projectedVertices = projectedVertices
        self.vertices = vertices
        self.postProjection()

        # Calculate bounding box to determine width and height
        self.minX = min(x for x, y in self.projectedVertices)
        self.maxX = max(x for x, y in self.projectedVertices)
        self.minY = min(y for x, y in self.projectedVertices)
        self.maxY = max(y for x, y in self.projectedVertices)

        self.width = int(math.ceil(self.maxX - self.minX)) + 1
        self.height = int(math.ceil(self.maxY - self.minY)) + 1

    def set2DPolygon(self):
        self.twoDimPolygon = Polygon(self.projectedVertices, self.color, self.pxScaleFactor)

    def getPixels(self) -> _2DArray:
        # Update 2D pixels from 2D polygon
        self.setPixelsNonDimUpdate(self.twoDimPolygon.getPixels())

        return super().getPixels()

# Textured Polygon3D that uses a PixelContainer as texture
# Only works as planar mapping for now (breaks when more then 3 vertices are used and not on same z plane)
class TexturedPolygon3D(Polygon3D):
    def __init__(self, ctx: Context3D, vertices: list[Vector3], texture: PixelContainer, anchor = "center", pxScaleFactor: int = 1):
        self.texture = texture
        self.anchor = anchor
        super().__init__(ctx, vertices, RGBAPixel(0, 0, 0, 0), pxScaleFactor)

    def set2DPolygon(self):
        self.twoDimPolygon = TexturedPolygon(self.projectedVertices, self.texture, self.anchor, self.pxScaleFactor)

    def getPixels(self) -> _2DArray:
        # If texture has changed reapply texture
        if self.texture.getHasChanged():
            self.texture.resetHasChanged()
            
            # Update textured polygon
            self.set2DPolygon()

        return super().getPixels()

# Wireframe Polygon3D that draws only the outline of the polygon using PolygonWireframe
# Only works as planar mapping for now (breaks when more then 3 vertices are used and not on same z plane)
class WireframePolygon3D(Polygon3D):
    def __init__(self, ctx: Context3D, vertices: list[Vector3], thickness: int, color: RGBAPixel, pxScaleFactor: int = 1):
        self.thickness = thickness
        super().__init__(ctx, vertices, color, pxScaleFactor)

    def set2DPolygon(self):
        self.twoDimPolygon = PolygonWireframe(self.projectedVertices, self.thickness, self.color, self.pxScaleFactor)


# 3D objects can be rotated, translated, and scaled
class Object3D(PixelContainer):
    # Works by the same interface as PixelContainer but handles 3D transformations and projection correctly to allow for non planar objects
    # Since its a PixelContainer it should have pxScaleFactor and width/height properties for later rasterizied rendering
    # and getPixels method to return the rasterized pixels of the object

    # Euler angle rotation functions
    def rotate_x(v: Vector3, angle_rad: float) -> Vector3:
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        y = v.y * cos_a - v.z * sin_a
        z = v.y * sin_a + v.z * cos_a
        return Vector3(v.x, y, z)

    def rotate_y(v: Vector3, angle_rad: float) -> Vector3:
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        x = v.x * cos_a + v.z * sin_a
        z = -v.x * sin_a + v.z * cos_a
        return Vector3(x, v.y, z)

    def rotate_z(v: Vector3, angle_rad: float) -> Vector3:
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        x = v.x * cos_a - v.y * sin_a
        y = v.x * sin_a + v.y * cos_a
        return Vector3(x, y, v.z)

    def apply_rotation(v: Vector3, rotation: Vector3) -> Vector3:
        v = rotate_x(v, math.radians(rotation.x))
        v = rotate_y(v, math.radians(rotation.y))
        v = rotate_z(v, math.radians(rotation.z))
        return v

    # PixelContainer interface
    def __init__(self, ctx: Context3D, vertices: list[Vector3], pos: Vector3 = Vector3(0,0,0), rotation: Vector3 = Vector3(0,0,0), scale: Vector3 = Vector3(1,1,1), pxScaleFactor: int = 1):
        self.ctx = ctx
        self.local_vertices = vertices  # original local vertices
        self.position = pos
        self.rotation = rotation
        self.scale = scale
        self.projectedVertices = []

        super().__init__(0, 0, pxScaleFactor)

        # Transform vertices initially
        self.update_vertices()

    def transform_vertex(self, v: Vector3) -> Vector3:
        # Apply scale
        v_scaled = Vector3(v.x * self.scale.x, v.y * self.scale.y, v.z * self.scale.z)
        # Apply rotation
        v_rotated = apply_rotation(v_scaled, self.rotation)
        # Apply translation
        v_transformed = Vector3(
            v_rotated.x + self.position.x,
            v_rotated.y + self.position.y,
            v_rotated.z + self.position.z
        )
        return v_transformed

    def update_vertices(self):
        # Transform all vertices to world space
        self.transformed_vertices = [self.transform_vertex(v) for v in self.local_vertices]
        # Project to 2D
        self.projectedVertices = self.ctx.projectVertices(self.transformed_vertices)
        if not self.projectedVertices or len(self.projectedVertices) != len(self.transformed_vertices):
            raise ValueError("Projection failed: maybe a vertex is at z=0.")
        # Update bounding box
        self.minX = min(x for x, y in self.projectedVertices)
        self.maxX = max(x for x, y in self.projectedVertices)
        self.minY = min(y for x, y in self.projectedVertices)
        self.maxY = max(y for x, y in self.projectedVertices)
        self.width = int(math.ceil(self.maxX - self.minX)) + 1
        self.height = int(math.ceil(self.maxY - self.minY)) + 1

    def getPixels(self) -> _2DArray:
        # Since Polygon3D,TexturedPolygon3D,WireframePolygon3D cant handle more then 3 vertices correctly we need to project and rasterize correctly here
        return super().getPixels()

    def rotate(self, rotation: Vector3):
        self.rotation = rotation
        self.update_vertices()

    def translate(self, pos: Vector3):
        self.position = pos
        self.update_vertices()

    def rescale(self, scale: Vector3):
        self.scale = scale
        self.update_vertices()

    
