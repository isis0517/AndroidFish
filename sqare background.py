from multiprocessing import Process, Value, Queue, Manager, Pool
import pygame
import numpy as np
import time
from pypylon import pylon
from ctypes import c_bool
import cv2
import os
import json

## TODO: slove the resize
## TODO: write the readme to explain how to use

def showImg(cam_q: Queue, is_running: Value, is_saving:Value, **kwargs) -> None:
    # parameter
    vpath = kwargs.get('vpath', "F_F_03.avi")
    display = kwargs.get('display', 1)
    full = kwargs.get("full", False)
    pause = False
    bk_color = [0, 0, 0] #RGB

    # init
    pygame.init()
    pygame.font.init()  # you have to call this at the start,
    myfont = pygame.font.SysFont('Comic Sans MS', 25)

    #video
    video = cv2.VideoCapture(vpath)
    _, img = video.read()
    video.set(cv2.CAP_PROP_POS_AVI_RATIO, 0)
    shape, dtype = img.shape, img.dtype
    shape = np.array([shape[1], shape[0]])
    ts_radius = min(shape) * 0.05
    pgFps = video.get(cv2.CAP_PROP_FPS)

    # pygame config
    pygame.display.set_caption("OpenCV camera stream on Pygame")
    pgClock = pygame.time.Clock()
    init_size = shape
    flags = pygame.RESIZABLE  # | pygame.DOUBLEBUF | pygame.SCALED  pygame.NOFRAME | #  #pygame.HWSURFACE | pygame.FULLSCREEN pygame.RESIZABLE ||
    #     # pygame.HWSURFACE | pygame.DOUBLEBUF
    if full:
        flags = flags | pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.SHOWN
        init_size = [0, 0]
    screen = pygame.display.set_mode(init_size, display=display, flags=flags)
    screen.fill(bk_color)
    sc_shape = np.array(pygame.display.get_window_size())
    sc_rat = min(sc_shape/shape)

    # loop init
    num = 0
    save_state = False

    while is_running.value:
        # all keyboard event is detected here

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                is_running.value = False
                is_saving.value = False
            if event.type == pygame.VIDEORESIZE:
                vsize = event.size
                time.sleep(0.5)
                for ev in pygame.event.get():
                    if ev.type == pygame.VIDEORESIZE:
                        vsize= ev.size
                old_screen = screen
                screen = pygame.display.set_mode(vsize, pygame.RESIZABLE)
                screen.blit(old_screen, (0, 0))
                sc_shape = np.array(vsize)
                sc_rat = min(sc_shape/shape)
                del old_screen
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    # Q -> kill the process
                    is_running.value = False
                if event.key == pygame.K_SPACE:
                    # space -> hold all process, the screen should be frozen and no more saving
                    pause = not pause
                    if pause:
                        save_state = is_saving.value
                        is_saving.value = False
                    else:
                        is_saving.value = save_state
                        save_state = False
                if event.key == pygame.K_s:
                    if pause:
                        save_state = not save_state
                        video.set(cv2.CAP_PROP_POS_AVI_RATIO, 0)
                        _, img = video.read()
                    else:
                        is_saving.value = not is_saving.value
                        video.set(cv2.CAP_PROP_POS_AVI_RATIO, 0)
                if event.key == pygame.K_r:
                    video.set(cv2.CAP_PROP_POS_AVI_RATIO, 0)
                    _, img = video.read()
        try:
            len = cam_q.qsize()
            for s in range(len+1):
                n = cam_q.get(timeout=0.001)
                num = n
        except:
            pass
        rects = []
        if pause:
            pass
        elif num>0:
            rects = [screen.fill(bk_color)]
            retval, img = video.read()
            if retval is False:
                time.sleep(0.1)
                is_running.value = False
                is_saving.value = False
                print(f"The video is finished, the record end in {num} frames")
                break
        frame = pygame.image.frombuffer(img.tobytes(), shape[0:2], 'RGB')
        frame = pygame.transform.scale(frame, tuple((shape*sc_rat).astype(int)))
        rect = frame.get_rect()
        rect.center = tuple(sc_shape//2)
        rects.append(screen.blit(frame, rect))
        if is_saving.value:
            rects.append(pygame.draw.circle(screen, (255, 0, 0), (ts_radius, ts_radius), ts_radius * 0.4))
            textsurface = myfont.render(str(num), False, (200, 200, 200))
            rects.append(screen.blit(textsurface, (ts_radius*0.7, ts_radius*0.6)))
        if save_state:
            rects.append(pygame.draw.circle(screen, (120, 40, 40), (ts_radius, ts_radius), ts_radius * 0.4))
        if pause:
            textsurface = myfont.render("pause", False, (0, 200, 200))
            rects.append(screen.blit(textsurface, (ts_radius * 1.1, ts_radius * 1.1)))

        pgClock.tick(pgFps)
        pygame.display.update(rects)

def savebuff(buff, s, shape, dtype=float, savepath=""):
    img = np.ndarray(shape, dtype=dtype, buffer=buff)
    np.save(os.path.join(savepath, f"frame_{s}.npy"), img)

def grabCam(cam_q: Queue, is_running, saving, savepath="", **kwargs):
    if not os.path.isdir(os.path.join(savepath, "frames")):
        os.mkdir(os.path.join(savepath, "frames"))
    savepath = os.path.join(savepath, "frames")
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
    # conecting to the first available camera
    camera = camInit(**kwargs)
    camera.Open()
    shape, dtype = camConfig(camera, **kwargs)
    s = 0
    with Pool(2) as pool:

        while camera.IsGrabbing() and is_running.value:
            grabResult = camera.RetrieveResult(6000, pylon.TimeoutHandling_ThrowException)
            cam_q.put(s)
            if grabResult.GrabSucceeded():
                buff = grabResult.GetBuffer()
                if saving.value:
                    pool.apply_async(savebuff, args=(buff, s, shape,), kwds={"dtype": dtype, "savepath": savepath})
                    s += 1
                else:
                    s = 0

            grabResult.Release()
        pool.close()
        pool.join()
        # Releasing the resource and reset
        is_running.value = False
        camera.StopGrabbing()
        #camera.BinningVertical.SetValue(1)
        #camera.BinningHorizontal.SetValue(1)
        camera.Close()
        cam_q.close()

    print("camera stop in", s)
    return

def camInit(c_num=0, **kwargs):
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
        raise Exception("camera init failed")
    return camera

def camConfig(camera, **kwargs):
    print(kwargs)
    FrameRate = kwargs.setdefault('FrameRate', 30)

    if camera.GetDeviceInfo().GetModelName() == "Emulation":
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
            raise Exception()

        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        return (shape, dtype)

    camera.Open()
    camera.AcquisitionFrameRateEnable.SetValue(True)
    camera.AcquisitionFrameRate.SetValue(FrameRate)
    #camera.BinningVertical.SetValue(1)
    #camera.BinningHorizontal.SetValue(1)

    PixelFormat = camera.PixelFormat.GetValue()

    print("resolution : ", f"{camera.Width.GetValue()}X{camera.Height.GetValue()}")
    print("Format : ", PixelFormat)
    #
    # camera.BinningVerticalMode.SetValue("Average")
    # camera.BinningHorizontalMode.SetValue("Average")

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
        raise Exception('grab failed')

    camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    return (shape, dtype)


if __name__ == "__main__":
    os.environ["PYLON_CAMEMU"] = "2"

    with open('pyconfig.json', 'r') as f:
        para = json.load(f)

    cam_q = Queue()  # the Queue for camera img
    is_Running = Value(c_bool, True)
    is_Saving = Value(c_bool, False)

    camera = Process(args=(cam_q, is_Running, is_Saving, ), target=grabCam,
                     kwargs=para)
    windows = Process(target=showImg, args=(cam_q, is_Running, is_Saving,),
                      kwargs=para)

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