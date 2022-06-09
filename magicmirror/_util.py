import os.path
import re
from Cameras import *
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
from TKwindows import CamStageConfig

class TankConfig(TypedDict, total=False):
    show: int
    center: str
    vpath: str
    spath: str


class VideoLoader:
    def __init__(self, tank_shape):
        self.tank_shape = tank_shape
        self.path = ""
        self.is_dir = True
        self.itr = iter([])

    def setPath(self, path: str) -> bool:
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

    def read(self) -> (bool, np.ndarray):
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
    def __init__(self, camera: PygCamera, sc_shape: Union[tuple, np.ndarray]):
        self.pycamera = camera
        self.config = CamStageConfig(model=self.pycamera.model)
        super().__init__((0, 0), tuple(self.pycamera.tank_shape))
        self.center = (sc_shape[0] - self.pycamera.tank_shape[0] // 2, sc_shape[1] -self.pycamera.tank_shape[1] // 2)
        self.tank_shape = self.pycamera.tank_shape
        self.background = self.copy()
        self.background.height = 1000
        self.background.bottomleft = self.topleft

        self.video = VideoLoader(self.tank_shape)
        self.is_video = False

        self.is_show = True

        self.img = np.zeros((self.tank_shape[1], self.tank_shape[0], 3))
        self.fps = self.pycamera.fps

    def getCover(self) -> pygame.Rect:
        return self.union(self.background)

    def setDisplace(self, dis: tuple) -> None:
        self.move_ip(dis)
        self.background.bottomleft = self.topleft
        self.config['center'] = self.center.__str__()

    def setSource(self, path: str) -> bool:
        if len(path) == 0:
            return False
        self.is_video = False
        if self.video.setPath(path):
            print(f"load video: {path}, ")
            self.is_video = True
            self.config['vpath'] = path
            return True
        else:
            print(f"{path} not exist")
            return False

    def setConfig(self, config: Union[CamConfig, TankConfig]) -> dict:
        if config["show"] == 1:
            self.is_show = True
        else:
            self.is_show = False
        if config["com"] == 1:
            self.pycamera.COM = True
        else:
            self.pycamera.COM = False

        lag = config["lag"]
        self.pycamera.threshold = config["threshold"]
        self.pycamera.setDelayCount(self.fps*lag)

        if 'center' in config:
            try:
                center = config['center']
                center_sparse = center[center.index("(") + 1:center.index(")")].split(",")
                center = (int(center_sparse[0]), int(center_sparse[1]))
                if center[0] < 0 or center[1] < 0:
                    raise Exception()
                if len(center) > 2:
                    raise Exception()
                self.center = center
                self.background.bottomleft = self.topleft
            except Exception as e:
                pass
            config['center'] = self.center.__str__()

        if 'vpath' in config:
            if self.setSource(config['vpath']):
                pass
            else:
                config["vpath"] = ""
        self.config = config

        return self.config

    def updateFrame(self) -> pygame.surface:
        img = self.pycamera.update()

        if not self.is_show:
            return pygame.image.frombuffer(bytearray(self.tank_shape[0]*self.tank_shape[1]*3), self.tank_shape, 'RGB')

        if self.is_video:
            ret, self.img = self.video.read()
            if not ret:
                print("is end of the video")
                self.is_video = False
                self.config['vpath'] = ""
            return pygame.image.frombuffer(self.img.tobytes(), self.tank_shape, 'RGB')

        self.img = img
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

