from pypylon import pylon
import numpy as np
import cv2
import os
import json
import datetime
from collections import deque


class Recorder:
    def __init__(self, fps=30, workpath=""):
        self.is_record = False
        self.frame_num = 0
        self.duration = 0
        self.fps = fps
        self.maxcount = 0
        self.model = "Not init"
        self.workpath = workpath
        self.path = ""
        self.dirname = ""
        self.img = np.zeros((10, 10))
        pass

    def setFolder(self, dirname: str) -> bool:
        if len(dirname) == 0:
            return False
        path = os.path.join(self.workpath, dirname)
        if os.path.exists(path):
            s = 0
            while os.path.exists(path + f"({s})"):
                s += 1
            path = path + f"{s}"
        self.dirname = dirname
        self.path = path
        self.frame_num = 0
        return True

    def setDuration(self, duration):
        self.duration = duration
        self.frame_num = 0
        self.maxcount = self.duration * self.fps

    def dumpConfig(self, config):
        if len(self.path) == 0:
            print(f"{self.model} , no path is used to dump config")
            return

        with open(os.path.join(self.path, "config"), 'w') as file:
            file.write(f"{datetime.datetime.now().strftime('%Y/%d/%m %H:%M:%S')}" + "\n")
            json.dump(config, file)

    def startRecord(self, dirname="", duration=0):
        if len(dirname) == 0:
            print(f"{self.model}is not be saved")
            return
        self.setFolder(dirname)
        self.setDuration(duration)
        os.mkdir(self.path)
        self.is_record = True

    def stopRecord(self):
        if self.is_record:
            print(f"{self.model}be stopped, ", self.frame_num)
        self.is_record = False
        self.frame_num = 0
        self.path = ""
        self.dirname = ""
        self.maxcount = 0

    def saveFrame(self, img: np.ndarray):
        if not self.is_record:
            return False
        if self.frame_num >= self.maxcount:
            self.is_record = False
            self.stopRecord()
            return False
        np.save(os.path.join(self.path, f"frame_{self.frame_num}"), img)
        self.frame_num += 1
        return True

    def saveImg(self):
        if not self.is_record:
            return False
        if self.frame_num >= self.maxcount:
            self.is_record = False
            self.stopRecord()
            return False
        np.save(os.path.join(self.path, f"frame_{self.frame_num}"), self.img)
        self.frame_num += 1
        return True

    def saveBuff(self, buff):
        if not self.is_record:
            return False
        if self.frame_num >= self.maxcount:
            self.is_record = False
            self.stopRecord()
            return False
        np.save(os.path.join(self.path, f"frame_{self.frame_num}"), np.ndarray(buffer=buff, shape=self.shape, dtype=self.dtype))
        self.frame_num += 1
        return True


class PygCamera:
    def __init__(self, camera: pylon.InstantCamera, tank_size=np.array([1300, 400]), fps=30):
        self.model = camera.GetDeviceInfo().GetModelName()
        self.fps = fps
        self.cam_shape, self.dtype = self.camInit(camera)
        self.shape = np.array([self.cam_shape[1], self.cam_shape[0]])
        self.camera = camera
        self.tank_shape = tuple((self.shape * min(tank_size / self.shape)).astype(int))
        self.delaycount = 0
        self.scenes = deque()
        self.threshold = 40
        self.COM = False
        self.pos = (0, 0)

    def setDelayCount(self, count: int) -> None:
        if self.delaycount == count:
            return
        self.delaycount = count
        lst = [np.zeros(np.append(self.tank_shape, [3]), dtype=np.uint8)] * count
        self.scenes.clear()
        self.scenes.extend(lst)

    def grabCam(self) -> None:
        try:
            grabResult = self.camera.RetrieveResult(20, pylon.TimeoutHandling_ThrowException)
        except Exception as e:
            return
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
        try:
            img = self.scenes.popleft()
        except:
            return False,  np.ones((self.tank_shape[1], self.tank_shape[0], 3), dtype=np.uint8)

        return True, img

    def camInit(self, camera: pylon.InstantCamera) -> (np.ndarray, np.dtype):
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
        camera.AcquisitionFrameRate.SetValue(self.fps*2)
        camera.StartGrabbing(pylon.GrabStrategy_LatestImages)
        camera.OutputQueueSize = 2

        return shape, dtype

    def close(self):
        self.camera.Close()


class RecCamera(Recorder):
    def __init__(self, camera, fps, workpath=""):
        super().__init__(fps=fps, workpath=workpath)
        self.model = camera.GetDeviceInfo().GetModelName()
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

    def updateFrame(self, poses=None):
        grabResult = self.camera.RetrieveResult(10000, pylon.TimeoutHandling_ThrowException)
        if grabResult.GrabSucceeded():
            self.saveBuff(grabResult.GetBuffer())

        else:
            print(f"{self.model} camera grab failed at time {datetime.datetime.now()}, which mission is recording")

    def __del__(self):
        self.camera.Close()



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
