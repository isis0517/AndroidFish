import os.path

import numpy as np
import datetime
from pypylon import pylon
import cv2
import json
from TKwindows import *
from Cameras import *
from pyfirmata2 import Arduino
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

# to do
# 1. camera config saving
# 2. record by outer schedule(files, including different config)
# 3. image enhance
# 4. adding random to the path


class Logger:
    def __init__(self, rootpath):
        self.rootpath = rootpath
        self.file = open(os.path.join(rootpath, "mm_log"), 'w')
        self.headers = []

    def log(self, mes):
        time_stamp = datetime.datetime.now().strftime("%Y/%d/%m %H:%M:%S ")
        self.file.write(time_stamp+mes)

    def __del__(self):
        self.file.close()


if __name__ == "__main__":

    ## this line enable the camera emulater
    os.environ["PYLON_CAMEMU"] = "1"

    # parameter
    bk_color = [200, 200, 200]  # RGB
    crack = 0

    # pygame init
    pygame.init()
    pygame.font.init()  # you have to call this at the start,
    myfont = pygame.font.SysFont('Comic Sans MS', 25)

    # camera init
    cameras = getCams()
    init_window = InitWindows(cameras)
    use_cams = init_window.display_cams
    rec_cams = init_window.rec_cam
    display = init_window.display_num
    workpath = init_window.workpath
    pgFps = init_window.pgFps
    PORT = init_window.port

    # loading arduino
    if PORT == "None":
        PORT = None
    board = Arduino(PORT)

    # pygame config
    pygame.display.set_caption("OpenCV camera stream on Pygame")
    pgClock = pygame.time.Clock()
    flags = 0  # pygame.RESIZABLE  # | pygame.DOUBLEBUF | pygame.SCALED  pygame.NOFRAME | #  #pygame.HWSURFACE | pygame.FULLSCREEN pygame.RESIZABLE ||
    #     # pygame.HWSURFACE | pygame.DOUBLEBUF
    flags = flags | pygame.SHOWN | pygame.DOUBLEBUF | pygame.HWSURFACE | pygame.NOFRAME  # | pygame.FULLSCREEN
    init_size = [0, 0]
    screen = pygame.display.set_mode(init_size, display=display, flags=flags)
    screen.fill(bk_color)
    pygame.display.update()
    sc_shape = np.array(pygame.display.get_window_size())

    # PygCam setting
    pyg_cameras = []
    show_cameras = []
    for cam in use_cams:
        pyg_cameras.append(PygCamera(cam, sc_shape))
        show_cameras.append((pyg_cameras[-1]))

    # console setting
    console = Console([cam.model for cam in pyg_cameras])
    console.start()

    # loop init
    is_running = True
    is_display = True
    able_record = False
    send_cam = -1

    # rect config
    tank_sel = False
    m_pos = (0, 0)
    setDisplace = lambda x: None

    # rec config
    if rec_cams is not None:
        recorder = RecCamera(rec_cams, pgFps)
        able_record = True

    # loop start
    while is_running and console.is_alive():
        # the rects will be updated, it is the key point to take fps stable
        rects = []

        # all keyboard event is detected here
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                is_running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for obj in reversed(show_cameras):
                    cover = obj.rect
                    if cover.collidepoint(pygame.mouse.get_pos()):
                        tank_sel = True
                        setDisplace = obj.setDisplace
                        break
                m_pos = pygame.mouse.get_pos()

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                tank_sel = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    # Q -> kill the process
                    is_running = False

        # console trigger
        if console.poll():   # if console set some values
            config = console.getConfig()
            is_running = config['is_running']
            show_cameras = []
            for s, obj in enumerate(pyg_cameras):
                if config[s]["show"] == 1:
                    show_cameras.append(obj)
                if config[s]["com"] == 1:
                    obj.COM = True
                else:
                    obj.COM = False
                lag = config[s]["lag"]
                obj.threshold = config[s]["threshold"]
                obj.setDelayCount(pgFps*lag)
            is_display = config["display"] == 1
            if config["light"] == 1:
                board.digital[12].write(1)
            else:
                board.digital[12].write(0)

            if 'record' in config.keys() and able_record:
                if config['record']:
                    is_record = True
                    recorder.setDuration(config['duration'])
                    recorder.setConfig(config)
                    recorder.setFolder(os.path.join(workpath, config['folder']))
                    recorder.startRecord()
                else:
                    recorder.stopRecord()

            send_cam = config["debug_cam"]

            rects.append(screen.fill(bk_color))
            # update the value


        # update the pos
        if tank_sel:
            rects.append(screen.fill(bk_color))
            c_pos = pygame.mouse.get_pos()
            setDisplace((c_pos[0]-m_pos[0], c_pos[1]-m_pos[1]))
            m_pos = c_pos

        # update the screen
        if able_record:
            recorder.update()
        for obj in show_cameras:
            obj.grabCam()

        if send_cam >= 0:
            console.send(pyg_cameras[send_cam].scenes[0])

        for obj in show_cameras:
            frame = obj.getFrame()
            cover = screen.blit(frame, obj.rect)
            rects.append(obj.rect)

        if not is_display:
            rects.append(screen.fill([0, 0, 0]))

        pygame.display.update(rects)

        pgClock.tick(pgFps)
        crack += 1

        if pgClock.get_time() > 1200 / (pgFps):
            crack += 1
            pass
        else:
            crack = 0

        if crack > 5:
            print("lagging!, interval =", pgClock.get_time(), "ms")

    pygame.quit()
    for cam in pyg_cameras:
        cam.camera.Close()
    if console.is_alive():
        console.terminate()

