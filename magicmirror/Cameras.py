from pypylon import pylon
import numpy as np
import cv2
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
from multiprocessing import Pool
import json
import datetime
from collections import deque

class PygCamera:
    def __init__(self, camera: pylon.InstantCamera, tank_size=np.array([1300, 400])):
        self.model = camera.GetDeviceInfo().GetModelName()
        self.cam_shape, self.dtype = self.camConfig(camera)
        self.shape = np.array([self.cam_shape[1], self.cam_shape[0]])
        self.camera = camera
        self.tank_shape = tuple((self.shape * min(tank_size / self.shape)).astype(int))
        self.delaycount = 0
        self.scenes = deque()
        self.threshold = 40
        self.COM = False
        self.pos = (0, 0)
        self.is_show = True

    def setDelayCount(self, count):
        if self.delaycount == count:
            return
        self.delaycount = count
        lst = [np.zeros(np.append(self.tank_shape, [3]), dtype=np.uint8)]*count
        self.scenes.clear()
        self.scenes.extend(lst)

    def grabCam(self):
        grabResult = self.camera.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)

        if grabResult.GrabSucceeded():
            buff = grabResult.GetBuffer()
            img = cv2.cvtColor(np.ndarray(self.cam_shape, dtype=np.uint8, buffer=buff), cv2.COLOR_BAYER_BG2BGR)
            img = cv2.resize(img, self.tank_shape, cv2.INTER_LINEAR)
            fg = (np.max(img, axis=2) > self.threshold).astype(np.uint8)
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
                self.pos = (cX, cY)
            self.scenes.append(img)
        else:
            print(f"{self.model} camera grab failed at time {datetime.datetime.now()}")
            img = np.ones((self.tank_shape[1], self.tank_shape[0], 3), dtype=np.uint8)
            self.scenes.append(img)

    def update(self) -> np.ndarray:
        self.grabCam()
        return self.scenes.popleft()

    def read(self) -> (bool, np.ndarray):
        self.grabCam()
        return True, self.scenes.popleft()

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
        camera.AcquisitionFrameRateEnable.SetValue(True)
        camera.AcquisitionFrameRate.SetValue(60)
        camera.StartGrabbing(pylon.GrabStrategy_LatestImages)
        camera.OutputQueueSize = 2

        return (shape, dtype)

    def close(self):
        self.camera.Close()


class RecCamera():
    def __init__(self, camera, fps):
        super().__init__()
        self.path = ""
        self.config = {"fps": fps}
        self.fps = fps
        self.duration = 10
        self.frame_num = 0
        self.maxcount = self.duration*self.fps
        self.is_record = False
        self.poses = []

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
        self.camera.StartGrabbing(pylon.GrabStrategy_LatestImages)
        self.camera.OutputQueueSize = 2
        self.shape = shape
        self.dtype = dtype
        self.pool = Pool()


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

    def update(self, poses=None):
        grabResult = self.camera.RetrieveResult(10000, pylon.TimeoutHandling_ThrowException)
        if self.is_record and self.maxcount > self.frame_num:
            if grabResult.GrabSucceeded():
                # self.pool.apply_async(savenpy, args=(os.path.join(self.path, f"{self.frame_num}.npy")
                #                                 , grabResult.GetBuffer())
                #                                 , kwds={"shape": self.shape, "dtype": self.dtype})
                np.save(os.path.join(self.path, f"{self.frame_num}.npy"),
                        np.ndarray(self.shape, dtype=self.dtype, buffer=grabResult.GetBuffer()))
                self.frame_num += 1

            else:
                print(f"{self.model} camera grab failed at time {datetime.datetime.now()}, which mission is recording")

        elif self.is_record:
            self.is_record = False

    def startRecord(self):

        path = self.path
        if os.path.isdir(path):
            s = 0
            while os.path.isdir(path+f"({s})"):
                s+=1
            path = path+f"{s}"
        os.mkdir(path)
        self.path = path

        with open(os.path.join(path, "config"), 'w') as file:
            file.write(f"{datetime.datetime.now().strftime('%Y/%d/%m %H:%M:%S')}"+"\n")
            json.dump(self.config, file)

        self.frame_num = 0
        self.maxcount = self.duration*self.fps
        self.is_record = True
        self.poses = []

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