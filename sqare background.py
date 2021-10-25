from multiprocessing import Process, Value, Queue, Manager, Pool
import pygame
import numpy as np
import time
from pypylon import pylon
from ctypes import c_bool
import cv2
import os

def showImg(cam_q: Queue, is_running: Value, form: list, **kwargs) -> None:
    # parameter
    vpath = kwargs.get('vpath', "F_F_03.avi")
    display = kwargs.get('display', 1)
    full = kwargs.get("full", False)
    saving = kwargs.get("saving", Value(c_bool, False))
    pause = False

    # init
    pygame.init()
    pygame.font.init()  # you have to call this at the start,
    myfont = pygame.font.SysFont('Comic Sans MS', 25)

    # pygame config
    pygame.display.set_caption("OpenCV camera stream on Pygame")
    pgClock = pygame.time.Clock()
    init_size = [1200, 1200]
    flags = pygame.NOFRAME   # | pygame.DOUBLEBUF   # | pygame.SCALED #pygame.HWSURFACE | pygame.FULLSCREEN pygame.RESIZABLE ||
    #     # pygame.HWSURFACE | pygame.DOUBLEBUF
    if full:
        flags = flags | pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.SHOWN
        init_size = [0, 0]
    screen = pygame.display.set_mode(init_size, display=display, flags=flags)
    screen.fill([200, 180, 200])
    sc_shape = np.array(pygame.display.get_window_size())

    #video
    video = cv2.VideoCapture(vpath)
    _, img = video.read()
    shape, dtype = img.shape, img.dtype
    shape = (shape[1], shape[0])
    ts_radius = min(shape) * 0.05
    pgFps = video.get(cv2.CAP_PROP_FPS)
    video.set(cv2.CAP_PROP_POS_AVI_RATIO, 0)
    num = 0

    while is_running.value:
        # all keyboard event is detected here

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    # Q -> kill the process
                    is_running.value = False
                if event.key == pygame.K_SPACE:
                    # space -> hold all process, the screen should be frozen and no more saving
                    pause = not pause
                    if pause:
                        temp = saving.value
                        saving.value = False
                    else:
                        saving.value = temp
                if event.key == pygame.K_s:
                    saving.value = not saving.value
                    video.set(cv2.CAP_PROP_POS_AVI_RATIO, 0)
                if event.key == pygame.K_r:
                    video.set(cv2.CAP_PROP_POS_AVI_RATIO, 0)
        try:
            num = cam_q.get(timeout=0.001)
        except:
            pass
        rects = []
        if not pause:
            rects = [screen.fill([200, 180, 200])]
            retval, img = video.read()
            frame = pygame.image.frombuffer(img.tobytes(), shape[0:2], 'RGB')
            frame = pygame.transform.scale(frame, tuple(sc_shape))
            rects.append(screen.blit(frame, (0, 0)))
        if saving.value:
            rects.append(pygame.draw.circle(screen, (255, 0, 0), (ts_radius, ts_radius), ts_radius * 0.4))
            textsurface = myfont.render(str(num), False, (200, 200, 200))
            rects.append(screen.blit(textsurface, (ts_radius*0.7, ts_radius*0.6)))

        pgClock.tick(pgFps)
        pygame.display.update(rects)




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

#        camera.BinningVerticalMode.SetValue("Average")
#        camera.BinningHorizontalMode.SetValue("Average")

        # if camera.Width.GetValue() / 1000 > 1 or camera.Height.GetValue() / 1000 > 1:
        #     rat = max(camera.Height.GetValue() / 1000, camera.Width.GetValue() / 1000)
        #     print("binning rate = ", rat)
        #     camera.BinningVertical.SetValue(int(rat))
        #     camera.BinningHorizontal.SetValue(int(rat))

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

        counter = FrameRate * secs

        print(f"starting recording {secs} secs with {FrameRate}fps at path:", savepath)

        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        start = time.time()
        s = 0
        with Pool(2) as pool:

            while camera.IsGrabbing() and is_running.value:
                grabResult = camera.RetrieveResult(6000, pylon.TimeoutHandling_ThrowException)
                cam_q.put(s)
                counter = counter - 1
                if grabResult.GrabSucceeded():
                    buff = grabResult.GetBuffer()
                    if saving.value:
                        pool.apply_async(savebuff, args=(buff, s, shape,), kwds={"dtype": dtype, "savepath": savepath})
                        s += 1
                    else:
                        s = 0

                grabResult.Release()

                if counter == 0:
                    print(f"stop recording {s} frames in time :", time.time() - start)
                    is_running.value = False
                    break
            # Releasing the resource and reset
            camera.StopGrabbing()
            camera.BinningVertical.SetValue(1)
            camera.BinningHorizontal.SetValue(1)
            camera.Close()
            cam_q.close()

        print("stop")
        return


if __name__ == "__main__":
    #os.environ["PYLON_CAMEMU"] = "2"
    cam_q = Queue()  # the Queue for camera img
    is_Running = Value(c_bool, True)
    saving = Value(c_bool, False)

    man = Manager()
    form = man.list([None, None])
    camera = Process(args=(cam_q, is_Running, form, ), target=grabCam,
                     kwargs={'mode': "camera", "c_num": 0, "secs": 600, "saving": saving})
    windows = Process(target=showImg, args=(cam_q, is_Running, form,),
                      kwargs={'mode': "pass", 'calibrate': False, "full": False, "saving": saving, "display":  1})

    windows.start()
    camera.start()
    while True:
        time.sleep(1)

        if not (camera.is_alive() and windows.is_alive()):
            windows.terminate()
            camera.terminate()
            camera.join()
            windows.join()
            break