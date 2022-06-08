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
import re

# to do
# 1. pygcamera switch source
# 2. pygcamera saving img
# 3. image enhance
# 4. adding random to the path

# abstract the pygame showing layer so that it can change the playing source. And also, let all recorded camera share
# same interface.

class VideoLoader:
    def __init__(self, tank_shape):
        self.tank_shape = tank_shape
        self.path = ""
        self.is_dir = True
        self.itr = iter([])

    def setPath(self, path):
        try:
            self.path = ""
            self.video.release()
        except Exception as e:
            pass

        try :
            if os.path.exists(path):
                if os.path.isdir(path):
                    flist = list(filter(lambda x: "npy" in x, os.listdir(path)))
                    if len(flist) < 10:
                        return False
                    flist.sort(key=lambda x: (int(re.findall('[0-9]+', x)[0])))
                    self.itr = flist.__iter__()
                    self.is_dir = True
                    self.path = path
                    return True

                elif os.path.isfile(path):
                    self.video = cv2.VideoCapture(path)
                    self.path = path
                    self.is_dir = False
                    return True
            return False
        except Exception as e:
            print(e)
            return False

    def read(self):
        if self.is_dir:
            try:
                name = next(self.itr)
                img = np.load(os.path.join(self.path, name))
                return True, cv2.resize(img, self.tank_shape)
            except:
                pass

        else:
            ret, img = self.video.read()
            if ret:
                return True, cv2.resize(img, self.tank_shape)
            else:
                self.video.release()
        return False, np.ones((self.tank_shape[1], self.tank_shape[0], 3), dtype=np.uint8)

class TankStage(pygame.Rect):
    def __init__(self, camera: PygCamera, sc_shape, **kwargs):
        self.pycamera = camera
        self.config = {"model": camera.model}
        super().__init__((0, 0), tuple(self.pycamera.tank_shape))
        self.center = (sc_shape[0] - self.pycamera.tank_shape[0] // 2, sc_shape[1] -self.pycamera.tank_shape[1] // 2)
        self.tank_shape = self.pycamera.tank_shape
        self.background = self.copy()
        self.background.height = 1000
        self.background.bottomleft = self.topleft

        self.video = VideoLoader(self.tank_shape)
        self.is_video = False

        self.is_show = True

        self.is_save = False
        self.path = f"{self.pycamera.model}"

        self.img = np.zeros((self.tank_shape[1], self.tank_shape[0], 3))

    def getCover(self):
        return self.union(self.background)

    def setDisplace(self, dis):
        self.move_ip(dis)
        self.background.bottomleft = self.topleft

    def setSource(self, path):
        self.is_video = False
        if self.video.setPath(path):
            print(f"load video: {path}, ")
            self.is_video = True
            return True
        else:
            print(f"{path} not exist")
            return False

    def setConfig(self, config:dict):
        if config["show"] == 1:
            self.pycamera.is_show = True
        else:
            self.pycamera.is_show = False
        if config["com"] == 1:
            self.pycamera.COM = True
        else:
            self.pycamera.COM = False

        lag = config["lag"]
        self.pycamera.threshold = config["threshold"]
        self.pycamera.setDelayCount(pgFps*lag)

        if 'center' in config:
            try:
                center = config['center']
                center = tuple(map(int, center[center.index("(") + 1:center.index(")")].split(",")))
                if center[0] < 0 or center[1] < 0:
                    raise Exception()
                if len(center) > 2:
                    raise Exception()
                self.center = center
            except:
                pass
            config['center'] = self.center

        if 'vpath' in config:
            if self.setSource(config['vpath']):
                pass
            else:
                config["vpath"] = ""
        self.config.update(config)

    def update(self):
        if self.is_video:
            ret, self.img = self.video.read()
            if not ret:
                print("is end of the video")
                self.is_video = False
            return pygame.image.frombuffer(self.img.tobytes(), self.tank_shape, 'RGB')
        self.img = self.pycamera.update()

        return pygame.image.frombuffer(self.img.tobytes(), self.tank_shape, 'RGB')



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
    pyg_stages = []
    for cam in use_cams:
        pyg_stages.append(TankStage(PygCamera(cam), sc_shape))

    # console setting
    console = Console([obj.pycamera.model for obj in pyg_stages])
    console.start()
    console.send({"center": [obj.center for obj in pyg_stages]})

    # loop init
    is_running = True
    is_display = True
    able_record = False
    is_sidesave = False
    send_cam = -1
    counter = 0

    # rect config
    tank_sel = False
    m_pos = (0, 0)
    setDisplace = lambda x: None

    # rec config
    pglock = pgFps
    if rec_cams is not None:
        recorder = RecCamera(rec_cams, pgFps)
        able_record = True
        pglock = 0

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
                for obj in reversed(pyg_stages):
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
                console.send({"center": [obj.center for obj in pyg_stages]})

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    # Q -> kill the process
                    is_running = False

        # console trigger
        if console.poll():   # if console set some values
            config = console.getConfig()
            is_running = config['is_running']
            for s, obj in enumerate(pyg_stages):
                config[str(s)]["model"] = obj.pycamera.model
                obj.setConfig(config[str(s)])
            console.send({"center": [obj.center for obj in pyg_stages]})
            console.send({"vpath": [obj.video.path for obj in pyg_stages]})

            is_display = config["display"] == 1
            if config["light"] == 1:
                board.digital[12].write(1)
            else:
                board.digital[12].write(0)

            if 'is_record' in config.keys() and able_record:
                if config['is_record']:
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

        for obj in pyg_stages:
            frame = obj.update()
            screen.blit(frame, obj)
            rects.append(obj)
            rects.append(pygame.draw.rect(screen, bk_color, obj.background))

        if send_cam >= 0:
            console.send({"img": pyg_stages[send_cam].img})

        if not is_display:
            rects.append(screen.fill([0, 0, 0]))

        pygame.display.update(rects)

        if able_record:
            recorder.update()

        counter += 1
        pgClock.tick(pglock)
        if counter == pgFps:
            console.send({"fps": pgClock.get_fps()})
            counter = 0

    pygame.quit()
    for obj in pyg_stages:
        obj.pycamera.camera.Close()
    if console.is_alive():
        console.terminate()

