from pypylon import pylon
import numpy as np
import cv2
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
from multiprocessing import Pool
import json
from functools import partial

class PygCamera:
    def __init__(self, camera: pylon.InstantCamera, sc_shape, tank_size=np.array([1300, 400])):
        self.model = camera.GetDeviceInfo().GetModelName()
        self.cam_shape, self.dtype = self.camConfig(camera)
        self.shape = np.array([self.cam_shape[1], self.cam_shape[0]])
        self.camera = camera
        self.tank_shape = tuple((self.shape * min(tank_size / self.shape)).astype(int))
        self.rect = pygame.Rect((0, 0), tuple(self.tank_shape))
        self.rect.center = tuple(sc_shape // 2)
        self.delaycount = 0
        self.scenes = []
        self.threshold = 40
        self.COM = False

    def setDelayCount(self, count):
        if self.delaycount == count:
            return
        self.delaycount = count
        self.scenes = [np.zeros(np.append(self.tank_shape, [3]), dtype=np.uint8)] * count

    def grabCam(self):
        grabResult = self.camera.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)

        if grabResult.GrabSucceeded():
            buff = grabResult.GetBuffer()
            img = cv2.cvtColor(np.ndarray(self.cam_shape, dtype=np.uint8, buffer=buff), cv2.COLOR_BAYER_BG2BGR)
            img = cv2.resize(img, self.tank_shape, cv2.INTER_NEAREST)
            img = cv2.blur(img, (3, 3))
            fg = (np.linalg.norm(img, axis=2) > self.threshold).astype(np.uint8)
            img = cv2.bitwise_and(img, img, mask=fg)
            if self.COM:
                M = cv2.moments(fg)
                if M["m00"] == 0:
                    cX = 0
                    cY = 0
                else:
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])
                cv2.circle(img, (cX, cY), 5, (255, 255, 255), -1)
            self.scenes.append(img)
        else:
            raise Exception("camera grab failed")

    def getFrame(self) -> pygame.Surface:
        img = self.scenes.pop(0)
        return pygame.image.frombuffer(img.tobytes(), self.tank_shape, 'RGB')

    def update(self) -> pygame.Surface:
        self.grabCam()
        return self.getFrame()

    def setDisplace(self, dis):
        center = self.rect.center
        self.rect.center = (center[0]+dis[0], center[1]+dis[1])

    def camConfig(self, camera: pylon.InstantCamera):
        if camera.GetDeviceInfo().GetModelName() == "Emulation":
            camera.Open()
            grabResult = camera.GrabOne(6000)
            if grabResult.GrabSucceeded():
                pt = grabResult.GetPixelType()
                if pylon.IsPacked(pt):
                    _, new_pt = grabResult._Unpack10or12BitPacked()
                    shape, dtype, pixelformat = grabResult.GetImageFormat(new_pt)
                else:
                    shape, dtype, pixelformat = grabResult.GetImageFormat(pt)
                    _ = grabResult.GetImageBuffer()
            else:
                raise Exception()

            camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            return (shape, dtype)

        camera.Open()

        grabResult = camera.GrabOne(1000)
        if grabResult.GrabSucceeded():
            pt = grabResult.GetPixelType()
            if pylon.IsPacked(pt):
                _, new_pt = grabResult._Unpack10or12BitPacked()
                shape, dtype, pixelformat = grabResult.GetImageFormat(new_pt)
            else:
                shape, dtype, pixelformat = grabResult.GetImageFormat(pt)
                _ = grabResult.GetImageBuffer()

        else:
            print("grab Failed")
            raise Exception('grab failed')
        camera.Open()
        camera.AcquisitionFrameRateEnable.SetValue(False)
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        return (shape, dtype)

    def close(self):
        self.camera.Close()


class RecCamera():
    def __init__(self, camera, fps):
        super().__init__()
        self.path = ""
        self.duration = 10
        self.fps = fps
        self.config = {"fps": fps}
        self.frame_num = 0
        self.is_record = False
        self.maxcount = self.duration*self.fps
        self.pool = Pool()
        self.camera = camera
        self.camera.Open()
        grabResult = self.camera.GrabOne(1000)
        if grabResult.GrabSucceeded():
            pt = grabResult.GetPixelType()
            if pylon.IsPacked(pt):
                _, new_pt = grabResult._Unpack10or12BitPacked()
                shape, dtype, pixelformat = grabResult.GetImageFormat(new_pt)
            else:
                shape, dtype, pixelformat = grabResult.GetImageFormat(pt)
                _ = grabResult.GetImageBuffer()
        else:
            print("grab Failed")
            raise Exception('grab failed')
        self.camera.AcquisitionFrameRateEnable.SetValue(True)
        self.camera.AcquisitionFrameRate.SetValue(self.fps)
        self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        self.savenpy = partial(savenpy, **{"shape": shape, "dtype": dtype})


    def setFolder(self, path):
        if os.path.exists(path):
            s = 0
            while os.path.exists(path+f"{s}"):
                s+=1
            path = path+f"{s}"
        self.path = path
        self.frame_num = 0

    def setDuration(self, duration):
        self.duration = duration

    def setConfig(self, config: dict):
        for key, value in config.items():
            self.config[key] = value

    def update(self):
        grabResult = self.camera.RetrieveResult(10000, pylon.TimeoutHandling_ThrowException)
        if self.is_record and self.maxcount > self.frame_num:
            if grabResult.GrabSucceeded():
                self.pool.apply_async(savenpy, args=(os.path.join(self.path, f"{self.frame_num}.npy"), grabResult))
                self.frame_num += 1
        elif self.is_record:
            self.is_record = False

    def startRecord(self):

        path = self.path
        if os.path.isdir(path):
            s = 0
            while os.path.isdir(path+f"{s}"):
                s+=1
            path = path+f"{s}"
        os.mkdir(path)
        self.path = path

        with open(os.path.join(path, "config"), 'w') as file:
            json.dump(self.config, file)

        self.frame_num = 0
        self.maxcount = self.duration*self.fps
        self.is_record = True

    def stopRecord(self):
        if self.is_record:
            print("be stopped, ", self.frame_num)
        self.is_record = False
        self.frame_num = 0
        self.maxcount = 0

    def __del__(self):
        self.camera.Close()
        self.pool.close()

def getCams():
    try:
        T1 = pylon.TlFactory.GetInstance()
        lstDevices = T1.EnumerateDevices()
        if len(lstDevices) == 0:
            print("no camera is detected")
        cameras = []
        for cam_info in lstDevices:
            cameras.append(pylon.InstantCamera(T1.CreateFirstDevice(cam_info)))

        print("total camera numbers : ",
              len(lstDevices))
    except:
        print("init fail")
        raise Exception("camera init failed")
    return cameras

def savenpy(filename, buf, shape=[], dtype=''):

    np.save(filename, np.ndarray(shape, dtype=dtype, buffer=buf))
