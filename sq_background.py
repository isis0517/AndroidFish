from multiprocessing import Process, Value, Queue, Manager, Pool
import pygame
import numpy as np
import time
from pypylon import pylon
from ctypes import c_bool
import cv2
import os
import json

def savebuff(buff, s, shape, dtype=float, savepath=""):
    img = np.ndarray(shape, dtype=dtype, buffer=buff)
    np.save(os.path.join(savepath, f"frame_{s}.npy"), img)


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
    camera.RegisterConfiguration(pylon.AcquireContinuousConfiguration(), pylon.RegistrationMode_ReplaceAll,
                                  pylon.Cleanup_Delete)

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

        camera.Close()
        camera.RegisterConfiguration(pylon.SoftwareTriggerConfiguration(), pylon.RegistrationMode_ReplaceAll,
                                     pylon.Cleanup_Delete)
        camera.Open()
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        return (shape, dtype)

    camera.Open()
    PixelFormat = camera.PixelFormat.GetValue()

    print("resolution : ", f"{camera.Width.GetValue()}X{camera.Height.GetValue()}")
    print("Format : ", PixelFormat)

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
    camera.Close()
    camera.RegisterConfiguration(pylon.SoftwareTriggerConfiguration(), pylon.RegistrationMode_ReplaceAll,
                                 pylon.Cleanup_Delete)
    camera.Open()
    camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    return (shape, dtype)

if __name__ == "__main__":
    os.environ["PYLON_CAMEMU"] = "1"

    with open('pyconfig.json', 'r') as f:
        kwargs = json.load(f)

    # parameter
    vpath = kwargs.get('vpath', "F_F_03.avi")
    display = kwargs.get('display', 1)
    full = kwargs.get("full", False)
    bk_color = [0, 0, 0]  # RGB
    savepath = kwargs.get('savepath', "")

    # pygame init
    pygame.init()
    pygame.font.init()  # you have to call this at the start,
    myfont = pygame.font.SysFont('Comic Sans MS', 25)

    # camera init
    camera = camInit(**kwargs)
    cam_shape, cam_type = camConfig(camera, **kwargs)

    # video
    video = cv2.VideoCapture(vpath)
    retval, img = video.read()
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
    sc_rat = min(sc_shape / shape)

    # loop init
    num = 0
    is_running = True
    is_saving = False
    pause = False

    # loop start
    with Pool() as pool:
        while is_running:
            # all keyboard event is detected here
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    is_running = False
                if event.type == pygame.VIDEORESIZE:
                    vsize = event.size
                    time.sleep(0.5)
                    for ev in pygame.event.get():
                        if ev.type == pygame.VIDEORESIZE:
                            vsize = ev.size
                    old_screen = screen
                    screen = pygame.display.set_mode(vsize, pygame.RESIZABLE)
                    screen.blit(old_screen, (0, 0))
                    sc_shape = np.array(vsize)
                    sc_rat = min(sc_shape / shape)
                    del old_screen
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        # Q -> kill the process
                        is_running = False

                    if event.key == pygame.K_SPACE:
                        # space -> hold all process, the screen should be frozen and no more saving
                        pause = not pause

                    if event.key == pygame.K_s:
                        is_saving = not is_saving

                    if event.key == pygame.K_r:
                        video.set(cv2.CAP_PROP_POS_AVI_RATIO, 0)
                        num = 0
                        _, img = video.read()

            # load img and play out
            if not pause:
                retval, img = video.read()
                if retval is False:
                    print(f"The video is finished, the record end in {num} frames")
                    break
            # update the screen
            rects = [screen.fill(bk_color)]
            frame = pygame.image.frombuffer(img.tobytes(), shape[0:2], 'RGB')
            frame = pygame.transform.scale(frame, tuple((shape * sc_rat).astype(int)))
            rect = frame.get_rect()
            rect.center = tuple(sc_shape // 2)
            rects.append(screen.blit(frame, rect))
            if pause:
                textsurface = myfont.render(f"P", False, (20, 200, 200))
                rects.append(screen.blit(textsurface, (ts_radius, ts_radius)))

            if is_saving:
                rects.append(pygame.draw.circle(screen, (255, 0, 0), (ts_radius, ts_radius), ts_radius * 0.4))
                if pause:
                    rects.append(pygame.draw.circle(screen, (120, 40, 40), (ts_radius, ts_radius), ts_radius * 0.4))
                textsurface = myfont.render(str(num), False, (200, 200, 200))
                rects.append(screen.blit(textsurface, (ts_radius * 0.7, ts_radius * 0.6)))

            pgClock.tick(pgFps)
            pygame.display.update(rects)

            # camera grab and saving
            camera.WaitForFrameTriggerReady(200, pylon.TimeoutHandling_ThrowException)
            camera.ExecuteSoftwareTrigger()
            grabResult = camera.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)
            if grabResult.GrabSucceeded():
                if is_saving and not pause:
                    pool.apply_async(np.save(os.path.join(savepath, f"frame_{num}"), grabResult.GetArray()))
                else:
                    pass
            else:
                raise Exception("camera grab failed")

            grabResult.Release()

            if not pause:
                num += 1
        pygame.quit()
        camera.Close()
        camera.RegisterConfiguration(pylon.AcquireContinuousConfiguration(), pylon.RegistrationMode_ReplaceAll,
                                     pylon.Cleanup_Delete)
        pool.close()
    print(f"{num}")
