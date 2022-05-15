import pygame
import numpy as np
import time
from pypylon import pylon
import cv2
import os
import json
import tkinter as tk
from tkinter import ttk
from multiprocessing import Process, Queue
from pyfirmata2 import Arduino


class InitWindows(tk.Frame):
    def __init__(self, cameras):
        self.root = tk.Tk()
        # self.root.geometry('500x300')
        tk.Frame.__init__(self, self.root)
        combo_values = ["Record", "Display", "No Use"]
        row_num = 0
        self.cameras = cameras
        self.cam_usage = list()
        self.cam_prompts = list()
        for camera in self.cameras:
            self.cam_prompts.append(tk.Label(self, text=camera.GetDeviceInfo().GetModelName(), anchor='w'))
            self.cam_usage.append(ttk.Combobox(self, values=combo_values, width=7))
            self.cam_prompts[-1].grid(column=0, row=row_num, sticky="W")
            self.cam_usage[-1].grid(column=1, row=row_num, sticky="W")
            self.cam_usage[-1].current(2)
            row_num += 1

        self.path_prompt = tk.Label(self, text="Working dictionary : ")
        self.path_prompt.grid(column=0, row=row_num, sticky="W")
        self.path_entry = tk.Entry(self, text=0, width=40)
        self.path_entry.insert(tk.END, os.getcwd())
        self.path_entry.grid(column=1, row=row_num, sticky="W")
        row_num += 1

        self.display_prompt = tk.Label(self, text="pygame display numbers:")
        self.display_prompt.grid(column=0, row=row_num, sticky="W")
        self.display_entry = tk.Entry(self, width=4)
        self.display_entry.insert(tk.END, 1)
        self.display_entry.grid(column=1, row=row_num, sticky="W")
        row_num += 1

        self.check_btn = tk.Button(self, text="Check", command=self.check, width=10, heigh=2)
        self.check_btn.grid(column=0, row=row_num, columnspan=2)
        self.pack(fill="both", expand=True)

        self.root.mainloop()

    def check(self):
        self.rec_cam = None
        self.display_cams = []
        for c_num, usage in enumerate(self.cam_usage):
            if usage.current() == 0:
                self.rec_cam = self.cameras[c_num]
            elif usage.current() == 1:
                self.display_cams.append(self.cameras[c_num])

        self.display_num = int(self.display_entry.get())
        self.workpath = self.path_entry.get()
        self.root.destroy()


class PygCamera:
    def __init__(self, camera: pylon.InstantCamera, sc_shape, tank_size=np.array([1300, 400])):
        self.cam_shape, self.dtype = self.camConfig(camera)
        self.shape = np.array([self.cam_shape[1], self.cam_shape[0]])
        self.camera = camera
        self.tank_shape = tuple((self.shape * min(tank_size / self.shape)).astype(np.int))
        self.rect = pygame.Rect((0, 0), tuple(self.tank_shape))
        self.rect.center = tuple(sc_shape // 2)
        self.setDelayCount(0)

    def setDelayCount(self, count):
        self.delaycount = count
        self.scenes = [np.zeros(np.append(self.shape, [3]), dtype=np.uint8)] * count

    def grabCam(self):
        grabResult = self.camera.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)

        if grabResult.GrabSucceeded():
            buff = grabResult.GetBuffer()
            img = cv2.cvtColor(np.ndarray(self.cam_shape, dtype=np.uint8, buffer=buff), cv2.COLOR_BAYER_BG2BGR)
            img = cv2.resize(img, self.tank_shape, cv2.INTER_NEAREST)
            img = cv2.blur(img, (3, 3))
            self.scenes.append(img)
        else:
            raise Exception("camera grab failed")

    def getFrame(self) -> pygame.Surface:
        img = self.scenes.pop(0)
        return pygame.image.frombuffer(img.tobytes(), self.tank_shape, 'RGB')

    def update(self) -> pygame.Surface:
        self.grabCam()
        return self.getFrame()

    def setDisplace(self, dis):
        center = self.rect.center
        self.rect.center = (center[0]+dis[0], center[1]+dis[1])

    @staticmethod
    def camConfig(camera: pylon.InstantCamera):
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


def show_console(conn, ):
    # 讀入影片,由於參數傳遞的關係，數據必須先預處理成list才能避免傳遞時使用傳址的方式
    # 第1步，例項化object，建立視窗window
    window = tk.Tk()

    # 第2步，給視窗的視覺化起名字
    window.title('console panel')

    # 第3步，設定視窗的大小(長 * 寬)
    window.geometry('500x500')  # 這裡的乘是小x

    # 第4步，在圖形介面上設定標籤
    var = tk.StringVar()  # 將label標籤的內容設定為字元型別，用var來接收hit_me函式的傳出內容用以顯示在標籤上
    Lable1 = tk.Label(window, textvariable=var, bg='green', fg='white', font=('Arial', 12), width=30, height=2)
    # 說明： bg為背景，fg為字型顏色，font為字型，width為長，height為高，這裡的長和高是字元的長和高，比如height=2,就是標籤有2個字元這麼高
    Lable1.pack()

    # 第6步，主視窗迴圈顯示
    window.mainloop()
    # 注意，loop因為是迴圈的意思，window.mainloop就會讓window不斷的重新整理，如果沒有mainloop,就是一個靜態的window,傳入進去的值就不會有迴圈，mainloop就相當於一個很大的while迴圈，有個while，每點選一次就會更新一次，所以我們必須要有迴圈
    # 所有的視窗檔案都必須有類似的mainloop函式，mainloop是視窗檔案的關鍵的關鍵。


def getCams():
    try:
        T1 = pylon.TlFactory.GetInstance()
        lstDevices = T1.EnumerateDevices()
        if len(lstDevices) == 0:
            print("no camera is detected")
        cameras = []
        for cam_info in lstDevices:
            cameras.append(pylon.InstantCamera(T1.CreateFirstDevice(cam_info)))

        print("total camera numbers : ",
              len(lstDevices))
    except:
        print("init fail")
        raise Exception("camera init failed")
    return cameras


if __name__ == "__main__":
    ## this line enable the camera emulater
    os.environ["PYLON_CAMEMU"] = "1"
    if not os.path.exists("mmconfig.json"):
        with open("mmconfig.json", 'w'):
            pass
    with open('mmconfig.json', 'r') as f:
        kwargs = json.load(f)

    # parameter
    bk_color = [200, 200, 200]  # RGB
    pgFps = 30
    delay = 0
    crack = 0

    # loading arduino
    # PORT = Arduino.AUTODETECT
    # if not isinstance(PORT, str):
    #     print("no Arduino is detected")
    # else:
    #     print(f"Arduino is detected at PORT {PORT}")
    #     board = Arduino(PORT)

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

    # console setting
    console = Process(target=show_console)
    console.start()

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
    for cam in use_cams:
        pyg_cameras.append(PygCamera(cam, sc_shape))

    # loop init
    is_running = True
    is_exp = True

    # rect config

    tank_sel = False
    m_pos = (0, 0)
    setDisplace = lambda x: None

    # loop start
    while is_running and console.is_alive():

        # all keyboard event is detected here
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                is_running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for obj in reversed(pyg_cameras):
                    cover = obj.rect
                    print(obj.camera)
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
        if False:   # if console set some values
            pass
            # update the value


        # the rects will be updated, it is the key point to take fps stable
        rects = []

        # update the pos
        if tank_sel:
            rects.append(screen.fill(bk_color))
            c_pos = pygame.mouse.get_pos()
            setDisplace((c_pos[0]-m_pos[0], c_pos[1]-m_pos[1]))
            m_pos = c_pos

        # update the screen
        if is_exp:
            for obj in pyg_cameras:
                frame = obj.update()
                rect = obj.rect
                cover = screen.blit(frame, rect)
                rects.append(rect)
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
    console.terminate()
