from multiprocessing import Process, Value, Queue, Manager, Pool
import pygame
import numpy as np
import time
from pypylon import pylon
import cv2
import os
import json


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
    camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    return (shape, dtype)

if __name__ == "__main__":
    ## this line enable the camera emulater
    # os.environ["PYLON_CAMEMU"] = "1"

    with open('pyconfig.json', 'r') as f:
        kwargs = json.load(f)

    # parameter
    display = kwargs.get('display', 1)
    full = kwargs.get("full", False)
    bk_color = [0, 0, 0]  # RGB
    pgFps = kwargs.get("fps", 30)

    # pygame init
    pygame.init()
    pygame.font.init()  # you have to call this at the start,
    myfont = pygame.font.SysFont('Comic Sans MS', 25)

    # camera init
    camera = camInit(**kwargs)
    cam_shape, cam_type = camConfig(camera, **kwargs)
    shape = np.array((cam_shape[1], cam_shape[0]))


    # converter
    converter = pylon.ImageFormatConverter()
    converter.OutputPixelFormat = pylon.PixelType_RGB8packed
    converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

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
    img = np.zeros(shape)

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

            grabResult = camera.RetrieveResult(6000, pylon.TimeoutHandling_ThrowException)

            if grabResult.GrabSucceeded():
                image = converter.Convert(grabResult)
                img = image.GetArray()
                # filp the img
            else:
                raise Exception("camera grab failed")
            # update the screen
            rects = [screen.fill(bk_color)]
            img = np.flip(img, axis=0)
            frame = pygame.image.frombuffer(img.tobytes(), shape[0:2], 'RGB')
            frame = pygame.transform.scale(frame, tuple((shape * sc_rat).astype(int)))
            rect = frame.get_rect()
            rect.center = tuple(sc_shape // 2)
            rects.append(screen.blit(frame, rect))


            pgClock.tick(pgFps)
            pygame.display.update(rects)

        pygame.quit()
        camera.Close()
        camera.RegisterConfiguration(pylon.AcquireContinuousConfiguration(), pylon.RegistrationMode_ReplaceAll,
                                     pylon.Cleanup_Delete)
        pool.close()
    print(f"{num}")
