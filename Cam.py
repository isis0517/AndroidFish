import numpy as np
import time
from pypylon import pylon
from multiprocessing import Pool, Value, Queue
from ctypes import c_bool
import cv2
import os


def savebuff(buff, s, shape, dtype=np.float, savepath=""):
    img = np.ndarray(shape, dtype=dtype, buffer=buff)
    np.save(os.path.join(savepath, f"frame_{s}.npy"), img)


def grabCam(cam_q: Queue, is_running, form, mode="camera", FrameRate=30, secs=10, c_num=0, savepath="",
            saving=Value(c_bool, False)):
    if not os.path.isdir(os.path.join(savepath, "frames")):
        os.mkdir(os.path.join(savepath, "frames"))
        savepath = os.path.join(savepath, "frames")
    print(f"The camera is action in {mode} mode")
    """
    args:
        cam_q : the Pipe comunnecate with cam2img
    kwargs:
        mode : the mode of thish function
            allow value:
            {"camera" -> default
             "video"}

        FrameRate : the fps of camera
        secs : recording time
        c_num : the number of camera
    """

    shape, dtype = (0, 0), 'uint8'
    if mode == "video":

        video = cv2.VideoCapture("F_F_03.avi")

        shape = (int(video.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                 int(video.get(cv2.CAP_PROP_FRAME_WIDTH)), 3)
        dtype = 'uint8'
        form[0] = shape
        form[1] = dtype

        s = 0
        if not video.isOpened():
            print("fail")
        print("video")
        start = time.time()
        while video.isOpened():
            ret, frame = video.read()
            s += 1
            cam_q.put_nowait(frame.tobytes())
            if time.time() - start > secs:
                is_running.value = False

                break
        print("stop")
        return

    if mode == "camera":

        # conecting to the first available camera
        try:
            T1 = pylon.TlFactory.GetInstance()
            lstDevices = T1.EnumerateDevices()
            if len(lstDevices) == 0:
                print("no camera is detected")
            if len(lstDevices) <= c_num:
                print(f"ther is no number {c_num} camera")
            camera = pylon.InstantCamera(T1.CreateFirstDevice(lstDevices[c_num]))

            print("using camera : ",
                  camera.GetDeviceInfo().GetModelName())
        except:
            print("init fail")
            exit()

        camera.Open()
        camera.AcquisitionFrameRateEnable.SetValue(True)
        camera.AcquisitionFrameRate.SetValue(FrameRate)
        camera.BinningVertical.SetValue(1)
        camera.BinningHorizontal.SetValue(1)

        PixelFormat = camera.PixelFormat.GetValue()

        print("resolution : ", f"{camera.Width.GetValue()}X{camera.Height.GetValue()}")
        print("Format : ", PixelFormat)

        camera.BinningVerticalMode.SetValue("Average")
        camera.BinningHorizontalMode.SetValue("Average")

        if camera.Width.GetValue() / 1000 > 1 or camera.Height.GetValue() / 1000 > 1:
            rat = max(camera.Height.GetValue() / 1000, camera.Width.GetValue() / 1000)
            print("binning rate = ", rat)
            camera.BinningVertical.SetValue(int(rat))
            camera.BinningHorizontal.SetValue(int(rat))

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
            exit()

        form[0] = shape
        form[1] = dtype
        counter = FrameRate * secs

        s = 0
        print(f"starting recording {secs} secs with {FrameRate}fps at path:", savepath)

        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        start = time.time()
        with Pool(2) as pool:

            while camera.IsGrabbing():
                grabResult = camera.RetrieveResult(6000, pylon.TimeoutHandling_ThrowException)

                counter = counter - 1
                if grabResult.GrabSucceeded():
                    buff = grabResult.GetBuffer()
                    cam_q.put_nowait(buff)
                    if saving.value:
                        pool.apply_async(savebuff, args=(buff, s, shape,), kwds={"dtype": dtype, "savepath": savepath})
                    s += 1

                grabResult.Release()

                if counter == 0:
                    print(f"stop recording {s} frames in time :", time.time() - start)
                    is_running.value = False
                    break
            # Releasing the resource
            camera.StopGrabbing()
            camera.BinningVertical.SetValue(1)
            camera.BinningHorizontal.SetValue(1)
            camera.Close()
            cam_q.close()

        print("stop")
        return
