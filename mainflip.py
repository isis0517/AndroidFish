from multiprocessing import Process, Value, Queue, Manager
from Cam import grabCam
from ctypes import c_bool
import time
import pygame
import cv2
import queue
import numpy as np

def showImg(cam_q:Queue, is_running: Value, form: list, **kwargs) -> None:
    mode = kwargs.get('mode', "pass")
    display = kwargs.get('display', 1)
    pgFps = kwargs.get('pgFps', 60)
    cM = kwargs.get('cM', np.identity(2))
    bias = kwargs.get('bias', np.zeros(2))
    is_calibrate = kwargs.get('calibrate', True if mode == 'inter' else False)
    full = kwargs.get("full", False)
    saving = kwargs.get("saving", Value(c_bool, False))
    pasue = False

    if form[0] is None:
        for s in range(10):
            time.sleep(0.1)
            if form[0] is not None:
                break
            if s == 9:
                print("showing error : no camera is open")
                exit()
    shape, dtype = form[0:2]
    tran = list(range(len(shape)))
    tran[0] = 1
    tran[1] = 0

    pygame.init()
    bg = cv2.bgsegm.createBackgroundSubtractorMOG(history=300, nmixtures=4, backgroundRatio=0.1)

    pygame.display.set_caption("OpenCV camera stream on Pygame")
    pgClock = pygame.time.Clock()
    init_size = [700, 700]
    flags = 0  # | pygame.DOUBLEBUF   # | pygame.SCALED #pygame.HWSURFACE | pygame.FULLSCREEN pygame.RESIZABLE ||
    # pygame.HWSURFACE | pygame.DOUBLEBUF
    if full:
        flags = flags | pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.SHOWN
        init_size = [0, 0]
    screen = pygame.display.set_mode(init_size, display=display, flags=flags)
    screen.fill([150, 150, 150])
    sc_shape = np.array(pygame.display.get_window_size())


    while is_running.value:

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    is_running.value = False
                if event.key == pygame.K_SPACE:
                    pasue = not pasue
                    if pasue:
                        mode = 'debug'
                    else:
                        mode = kwargs.get('mode', "pass")
                if event.key == pygame.K_s:
                    saving.value = not saving.value
        rects = [screen.fill([150, 150, 150])]

        try:
            buf = cam_q.get(True, 0.01)
        except queue.Empty as e:
            continue
        img = np.ndarray(shape, dtype=dtype, buffer=buf)

        img = np.transpose(img, tran)[::-1, ::-1, ...]

        #img = cv2.cvtColor(img, cv2.COLOR_BayerGB2RGB)

        img = bg.apply(img)

        if img.ndim < 3:
            img = np.broadcast_to(img[:, :, np.newaxis], (img.shape[0], img.shape[1], 3))
        if img.shape[2] == 1:
            img = np.broadcast_to(img, (img.shape[0], img.shape[1], 3))
        frame = pygame.image.frombuffer(img.tobytes(), shape[0:2], 'RGB')
        frame = pygame.transform.scale(frame, tuple(sc_shape))
        rects.append(screen.blit(frame, (0, 0)))

        pgClock.tick(pgFps)
        pygame.display.update(rects)


if __name__ == "__main__":
    cam_q = Queue()  # the Queue for camera img
    is_Running = Value(c_bool, True)
    saving = Value(c_bool, False)

    man = Manager()
    form = man.list([None, None])
    camera = Process(args=(cam_q, is_Running, form, ), target=grabCam,
                     kwargs={'mode': "video", "c_num": 1, "secs": 20, "saving": saving})
    windows = Process(target=showImg, args=(cam_q, is_Running, form,),
                      kwargs={'mode': "traj", 'calibrate': False, "full": False, "saving": saving})

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