# Description: A module that provides a VideoContainer class for handling video files as pixel containers.
# Requires: opencv-python

import cv2
import time
import os
import tempfile

from termobjs import PixelContainer, RGBAPixel, _2DArray, AnimatedPixelContainer

class VideoContainer(PixelContainer):
    # For video while we could use AnimatedPixelContainer storing all frames is not efficient
    # So rather we keep tract of the time and then make sure getPixels returns the correct frame based on time
    def __init__(self, videoPath: str, width = None, height = None, pxScaleFactor: int = 1):
        self.cap = cv2.VideoCapture(videoPath)
        if not self.cap.isOpened():
            raise ValueError("Could not open video file: " + videoPath)

        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frameCount = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = self.frameCount / self.fps

        if width is not None and height is not None:
            self.width = width
            self.height = height
        elif width is not None:
            aspectRatio = self.height / self.width
            self.height = int(width * aspectRatio)
            self.width = width
        elif height is not None:
            aspectRatio = self.width / self.height
            self.width = int(height * aspectRatio)
            self.height = height

        super().__init__(self.width, self.height, pxScaleFactor)

        self.startTime = time.time()
        self.currentFrameIndex = 0

    def getPixels(self) -> _2DArray:
        elapsedTime = time.time() - self.startTime
        frameIndex = int((elapsedTime % self.duration) * self.fps)

        if frameIndex != self.currentFrameIndex:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frameIndex)
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
                if (frame.shape[1], frame.shape[0]) != (self.width, self.height):
                    frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_NEAREST)
                for y in range(self.height):
                    for x in range(self.width):
                        r, g, b, a = frame[y, x]
                        self.setPixel(x, y, RGBAPixel(r, g, b, a))
                self.currentFrameIndex = frameIndex

        if (self.pxScaleFactor != 1):
            # Nearest neighbor scaling
            return self._getScaledPixels()

        return self.pixels

class PreScaledVideoContainer(VideoContainer):
    def __init__(self, videoPath: str, width = None, height = None, pxScaleFactor: int = 1, scaledVideoPath: str = None, printProgress: bool = False, printer=lambda x: print(x, end='')):
        if scaledVideoPath is None:
            # use os temp directory for scaled video
            epochStr = str(int(time.time()))
            scaledVideoPath = tempfile.gettempdir() + "/termobjs_videoext_scaled_video" + epochStr + ".mp4"
        self.scaledVideoPath = scaledVideoPath
        self.printProgress = printProgress
        self.printer = printer

        self.videoPath = videoPath

        videoPathToUse = self.videoPath

        # Scale video first
        if (pxScaleFactor != 1):
            self._scaleVideoFile(videoPath, self.scaledVideoPath, 1.0 / pxScaleFactor)
            videoPathToUse = self.scaledVideoPath

        super().__init__(videoPathToUse, width, height, pxScaleFactor)

    def _scaleVideoFile(self, inputPath: str, outputPath: str, scaleFactor: float):
        cap = cv2.VideoCapture(inputPath)
        if not cap.isOpened():
            raise ValueError("Could not open video file: " + inputPath)

        # Video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) * scaleFactor)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) * scaleFactor)

        # Output writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(outputPath, fourcc, fps, (width, height))

        # Process frames
        current_frame = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # Resize frame
            frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_NEAREST)
            out.write(frame)

            # Progress reporting
            current_frame += 1
            if self.printProgress:
                progress = (current_frame / frame_count) * 100
                self.printer(f"\rScaling video: {progress:.2f}%")

        cap.release()
        out.release()
        if self.printProgress:
            self.printer("\nVideo scaling complete!")
