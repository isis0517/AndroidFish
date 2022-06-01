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
# 2. only part of screen is lighting
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
    # os.environ["PYLON_CAMEMU"] = "1"
    # parameter
    bk_color = [200, 200, 200]  # RGB

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

    # stage init
    screen = pygame.display.set_mode(init_size, display=display, flags=flags)
    screen.fill([0, 0, 0])
    pygame.display.update()
    sc_shape = np.array(pygame.display.get_window_size())

    # PygCam setting
    pyg_cameras = []
    for cam in use_cams:
        pyg_cameras.append(PygCamera(cam, sc_shape))

    # console setting
    console = Console([cam.model for cam in pyg_cameras])
    console.start()

    # loop init
    is_running = True
    is_display = True
    is_sidesave = True
    able_record = False
    send_cam = -1
    counter = 0

    # rect config
    tank_sel = False
    m_pos = (0, 0)
    setDisplace = lambda x: None

    # rec config
    if rec_cams is not None:
        recorder = RecCamera(rec_cams, pgFps)
        able_record = True

    # side save config
    if is_sidesave:
        side_video = cv2.VideoWriter("sidevideo.mp4", cv2.VideoWriter_fourcc(*"mp4v"), pgFps
                                     , pyg_cameras[0].tank_shape)

    # loop start
    while is_running and console.is_alive():

        # the rects will be updated, it is the key point to take fps stable
        rects = []

        # all keyboard event is detected here
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                is_running = False

            # mouse button down, check whether the tank image is selected.
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for obj in reversed(pyg_cameras):
                    cover = obj.getCover()
                    if cover.collidepoint(pygame.mouse.get_pos()):
                        tank_sel = True
                        # assign the displace function.
                        setDisplace = obj.setDisplace
                        break
                m_pos = pygame.mouse.get_pos()

            # mouse button release, no tank is select
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
            for s, obj in enumerate(pyg_cameras):
                if config[s]["show"] == 1:
                    obj.is_show = True
                else:
                    obj.is_show = False
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
                    recorder.setDuration(config['duration'])
                    recorder.setConfig(config)
                    recorder.setFolder(os.path.join(workpath, config['folder']))
                    recorder.startRecord()
                else:
                    recorder.stopRecord()

            send_cam = config["debug_cam"]

            rects.append(screen.fill([0, 0, 0]))
            # update the value


        # update the pos
        if tank_sel:
            rects.append(screen.fill([0, 0, 0]))
            c_pos = pygame.mouse.get_pos()
            setDisplace((c_pos[0]-m_pos[0], c_pos[1]-m_pos[1]))
            m_pos = c_pos

        # update the screen
        for obj in pyg_cameras:
            obj.grabCam()

        if send_cam >= 0:
            console.send(pyg_cameras[send_cam].scenes[0][:, :, ::-1])

        if is_sidesave:
            side_video.write(pyg_cameras[0].scenes[0][:, :, ::-1])

        for obj in pyg_cameras:
            frame = obj.getFrame()
            pygame.draw.rect(screen, bk_color, obj.rect)
            rects.append(obj.rect)
            rects.append(pygame.draw.rect(screen, bk_color, obj.background))

        if not is_display:
            rects.append(screen.fill([0, 0, 0]))

        pygame.display.update(rects)

        if able_record:
            recorder.update()

        counter += 1
        pgClock.tick()
        if counter == 30:
            print(pgClock.get_fps())
            counter = 0

    pygame.quit()
    if is_sidesave:
        side_video.release()
    for cam in pyg_cameras:
        cam.camera.Close()
    if console.is_alive():
        console.terminate()

