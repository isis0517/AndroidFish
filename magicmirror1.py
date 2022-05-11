import pygame
import numpy as np
import time
from pypylon import pylon
import cv2
import os
import json
import tkinter as tk
from multiprocessing import Process, Queue
from pyfirmata2 import Arduino


def show_console():
    # 讀入影片,由於參數傳遞的關係，數據必須先預處理成list才能避免傳遞時使用傳址的方式
    # 第1步，例項化object，建立視窗window
    window = tk.Tk()

    # 第2步，給視窗的視覺化起名字
    window.title('console panel')

    # 第3步，設定視窗的大小(長 * 寬)
    window.geometry('500x500')  # 這裡的乘是小x

    # 第4步，在圖形介面上設定標籤
    var = tk.StringVar()    # 將label標籤的內容設定為字元型別，用var來接收hit_me函式的傳出內容用以顯示在標籤上
    Lable1 = tk.Label(window, textvariable=var, bg='green', fg='white', font=('Arial', 12), width=30, height=2)
    # 說明： bg為背景，fg為字型顏色，font為字型，width為長，height為高，這裡的長和高是字元的長和高，比如height=2,就是標籤有2個字元這麼高
    Lable1.pack()

    # 第6步，主視窗迴圈顯示
    window.mainloop()
    # 注意，loop因為是迴圈的意思，window.mainloop就會讓window不斷的重新整理，如果沒有mainloop,就是一個靜態的window,傳入進去的值就不會有迴圈，mainloop就相當於一個很大的while迴圈，有個while，每點選一次就會更新一次，所以我們必須要有迴圈
    # 所有的視窗檔案都必須有類似的mainloop函式，mainloop是視窗檔案的關鍵的關鍵。

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
    os.environ["PYLON_CAMEMU"] = "1"
    if not os.path.exists("mmconfig.json"):
        with open("mmconfig.json", 'w'):
            pass
    with open('mmconfig.json', 'r') as f:
        kwargs = json.load(f)

    # parameter
    display = 1
    full = True
    bk_color = [200, 200, 200]  # RGB
    pgFps = 30
    delay = 0
    crack = 0

    # loading arduino
    PORT = Arduino.AUTODETECT
    if not isinstance(PORT, str):
        print("no Arduino is detected")
    else:
        print(f"Arduino is detected at PORT {PORT}")
        board = Arduino(PORT)

    # pygame init
    pygame.init()
    pygame.font.init()  # you have to call this at the start,
    myfont = pygame.font.SysFont('Comic Sans MS', 25)

    # camera init
    camera = camInit(**kwargs)
    cam_shape, cam_type = camConfig(camera, **kwargs)
    shape = np.array((cam_shape[1], cam_shape[0]))

    # console setting
    console = Process(target=show_console)
    console.start()

    # pygame config
    pygame.display.set_caption("OpenCV camera stream on Pygame")
    pgClock = pygame.time.Clock()
    init_size = [1300, 400]
    flags = 0 #pygame.RESIZABLE  # | pygame.DOUBLEBUF | pygame.SCALED  pygame.NOFRAME | #  #pygame.HWSURFACE | pygame.FULLSCREEN pygame.RESIZABLE ||
    #     # pygame.HWSURFACE | pygame.DOUBLEBUF
    if full:
        flags = flags | pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.SHOWN | pygame.NOFRAME # | pygame.FULLSCREEN
        init_size = [0, 0]
    screen = pygame.display.set_mode(init_size, display=display, flags=flags)
    screen.fill(bk_color)
    sc_shape = np.array(pygame.display.get_window_size())


    # loop init
    start = time.time()
    is_running = True
    fps_check = False
    img = np.zeros(shape)
    scenes = [np.ones(np.append(shape, [3]), dtype=np.uint8)]*delay

    # rect config
    tank_size = np.array([1300, 400])
    sc_rat = min(tank_size / shape)
    tank1_cen = tuple(sc_shape//2)
    tank1_sel = False
    cover = pygame.rect.Rect((0,0), tuple(tank_size))
    cover.center = tank1_cen

    dis = (0,0)

    # loop start
    while is_running and console.is_alive():
        # all keyboard event is detected here
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                is_running = False

            if event.type == pygame.MOUSEMOTION:
                dis = pygame.mouse.get_rel()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if cover.collidepoint(pygame.mouse.get_pos()):
                    tank1_sel = True

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                tank1_sel = False

            if event.type == pygame.VIDEOEXPOSE:
                fps_check=False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    # Q -> kill the process
                    is_running = False

        # grab image
        grabResult = camera.RetrieveResult(6000, pylon.TimeoutHandling_ThrowException)

        if grabResult.GrabSucceeded():
            buff = grabResult.GetBuffer()
            img = cv2.cvtColor(np.ndarray(cam_shape, dtype=np.uint8, buffer=buff), cv2.COLOR_BAYER_BG2BGR)
            img = cv2.blur(img, (3, 3))
            scenes.append(img)
        else:
            raise Exception("camera grab failed")

        # update the pos
        if tank1_sel:
            tank1_cen = (tank1_cen[0]+dis[0], tank1_cen[1]+dis[1])
            dis = [0, 0]

        # update the screen
        rects = [screen.fill(bk_color)]
        last_img = scenes.pop(0)
        frame = pygame.image.frombuffer(last_img.tobytes(), shape[0:2], 'RGB')
        frame = pygame.transform.scale(frame, tuple((shape * sc_rat).astype(int)))
        rect = frame.get_rect()
        rect.center = tank1_cen
        cover = screen.blit(frame, rect)
        rects.append(cover)

        pygame.display.update(rects)

        pgClock.tick(pgFps)
        crack += 1

        if fps_check and pgClock.get_time() > 1200/(pgFps):
            print("lagging!, stop the video", pgClock.get_time())
            crack += 1
        else:
            crack=0

        if crack > 5:
            break

        fps_check = True

    pygame.quit()
    camera.Close()
    console.terminate()
