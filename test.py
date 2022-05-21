import numpy as np
from multiprocessing import Process, Value, Pipe, Pool, Manager
from ctypes import c_bool
from multiprocessing import Queue
import cv2
from time import sleep
import time
import sys, os
import tkinter as tk
import tkinter.ttk as ttk
from pypylon import pylon
from threading import Timer, Event
# from tqdm import tqdm
#
# from pypylon import genicam
# from pypylon import pylon
#import pygame
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
def test_2can():
    # Grab_MultipleCameras.cpp
    # ============================================================================
    # This sample illustrates how to grab and process images from multiple cameras
    # using the CInstantCameraArray class. The CInstantCameraArray class represents
    # an array of instant camera objects. It provides almost the same interface
    # as the instant camera for grabbing.
    # The main purpose of the CInstantCameraArray is to simplify waiting for images and
    # camera events of multiple cameras in one thread. This is done by providing a single
    # RetrieveResult method for all cameras in the array.
    # Alternatively, the grabbing can be started using the internal grab loop threads
    # of all cameras in the CInstantCameraArray. The grabbed images can then be processed by one or more
    # image event handlers. Please note that this is not shown in this example.
    # ============================================================================

    os.environ["PYLON_CAMEMU"] = "2"

    # Number of images to be grabbed.
    countOfImagesToGrab = 10*4

    # Limits the amount of cameras used for grabbing.
    # It is important to manage the available bandwidth when grabbing with multiple cameras.
    # This applies, for instance, if two GigE cameras are connected to the same network adapter via a switch.
    # To manage the bandwidth, the GevSCPD interpacket delay parameter and the GevSCFTD transmission delay
    # parameter can be set for each GigE camera device.
    # The "Controlling Packet Transmission Timing with the Interpacket and Frame Transmission Delays on Basler GigE Vision Cameras"
    # Application Notes (AW000649xx000)
    # provide more information about this topic.
    # The bandwidth used by a FireWire camera device can be limited by adjusting the packet size.
    maxCamerasToUse = 2

    # The exit code of the sample application.
    exitCode = 0

    try:

        # Get the transport layer factory.
        tlFactory = pylon.TlFactory.GetInstance()

        # Get all attached devices and exit application if no device is found.
        devices = tlFactory.EnumerateDevices()
        if len(devices) == 0:
            raise pylon.RuntimeException("No camera present.")

        # Create an array of instant cameras for the found devices and avoid exceeding a maximum number of devices.
        cameras = pylon.InstantCameraArray(min(len(devices), maxCamerasToUse))

        l = cameras.GetSize()

        # Create and attach all Pylon Devices.
        for i, cam in enumerate(cameras):
            cam.Attach(tlFactory.CreateDevice(devices[i]))

            # Print the model name of the camera.
            print("Using device ", cam.GetDeviceInfo().GetModelName())

        # Starts grabbing for all cameras starting with index 0. The grabbing
        # is started for one camera after the other. That's why the images of all
        # cameras are not taken at the same time.
        # However, a hardware trigger setup can be used to cause all cameras to grab images synchronously.
        # According to their default configuration, the cameras are
        # set up for free-running continuous acquisition.
        cameras.StartGrabbing()

        # Grab c_countOfImagesToGrab from the cameras.
        for i in range(countOfImagesToGrab):
            if not cameras.IsGrabbing():
                break

            grabResult = cameras.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

            # When the cameras in the array are created the camera context value
            # is set to the index of the camera in the array.
            # The camera context is a user settable value.
            # This value is attached to each grab result and can be used
            # to determine the camera that produced the grab result.
            cameraContextValue = grabResult.GetCameraContext()

            # Print the index and the model name of the camera.
            print("Camera ", cameraContextValue, ": ", cameras[cameraContextValue].GetDeviceInfo().GetModelName())

            # Now, the image data can be processed.
            print("GrabSucceeded: ", grabResult.GrabSucceeded())
            print("SizeX: ", grabResult.GetWidth())
            print("SizeY: ", grabResult.GetHeight())
            img = grabResult.GetArray()
            print("Gray value of first pixel: ", img[0, 0])

    except genicam.GenericException as e:
        # Error handling
        print("An exception occurred.", e.GetDescription())
        exitCode = 1

    # Comment the following two lines to disable waiting on exit.
    sys.exit(exitCode)

def Test2():

    dirname = "/media/hydrolab/L1/0708/male"
    frame_num = 60000
    try:
        os.mkdir(dirname)
    except FileExistsError as e:
        print("already exists")

    os.environ["PYLON_CAMEMU"] = "2"
    try:
        T1 = pylon.TlFactory.GetInstance()
        lstDevices = T1.EnumerateDevices()
        if len(lstDevices) == 0:
            print("no camera is detected")
        if len(lstDevices) <= 0:
            print(f"ther is no camera")

        camera1 = pylon.InstantCamera(T1.CreateFirstDevice(lstDevices[0]))
        camera2 = pylon.InstantCamera(T1.CreateFirstDevice(lstDevices[1]))

        print("using camera1 : ",
              camera1.GetDeviceInfo().GetModelName())
        print("using camera2 : ",
              camera2.GetDeviceInfo().GetModelName())
    except:
        print("init fail")
        exit()


    camera1.RegisterConfiguration(pylon.AcquireContinuousConfiguration(), pylon.RegistrationMode_ReplaceAll,
                                  pylon.Cleanup_Delete)
    camera2.RegisterConfiguration(pylon.AcquireContinuousConfiguration(), pylon.RegistrationMode_ReplaceAll,
                                  pylon.Cleanup_Delete)
    camera1.Open()
    camera2.Open()

    re1 = camera1.GrabOne(1000)
    re2 = camera2.GrabOne(1000)
    if re1.GrabSucceeded():
        size1 = re1.GetArray().shape
    else:
        print("C1 grab Failed")
        exit()

    if re2.GrabSucceeded():
        size2 = re2.GetArray().shape

    else:
        print("C2 grab Failed")
        exit()

    camera1.Close()
    camera2.Close()

    camera1.RegisterConfiguration(pylon.SoftwareTriggerConfiguration(), pylon.RegistrationMode_ReplaceAll,
                                 pylon.Cleanup_Delete)
    camera2.RegisterConfiguration(pylon.SoftwareTriggerConfiguration(), pylon.RegistrationMode_ReplaceAll,
                                 pylon.Cleanup_Delete)

    camera1.Open()
    camera2.Open()

    camera1.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
    camera2.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    start = time.time()

    for s in tqdm(range(frame_num)):
        camera1.WaitForFrameTriggerReady(200, pylon.TimeoutHandling_ThrowException)
        camera2.WaitForFrameTriggerReady(200, pylon.TimeoutHandling_ThrowException)
        camera1.ExecuteSoftwareTrigger()
        camera2.ExecuteSoftwareTrigger()

        re1 = camera1.RetrieveResult(100, pylon.TimeoutHandling_Return)
        re2 = camera2.RetrieveResult(100, pylon.TimeoutHandling_Return)
        np.save(os.path.join(dirname, f"c1_{s}"), re1.GetArray())
        np.save(os.path.join(dirname, f"c2_{s}"), re2.GetArray())

    camera1.Close()
    camera2.Close()

    camera1.RegisterConfiguration(pylon.AcquireContinuousConfiguration(), pylon.RegistrationMode_ReplaceAll,
                                 pylon.Cleanup_Delete)
    camera2.RegisterConfiguration(pylon.AcquireContinuousConfiguration(), pylon.RegistrationMode_ReplaceAll,
                                 pylon.Cleanup_Delete)

    camera1.Open()
    camera2.Open()
    camera1.Close()
    camera2.Close()

def HI():
    print("HAHA")

def grabCam(cam_q, l):
    start = time.time()
    c = np.random.randint(255, size=(2000,2000,1), dtype=np.uint8)
    cb = c.tobytes()
    for s in range(l):
        cam_q.send_bytes(cb)
    print(time.time()-start, " spend")

def getCam(cam_q, l):
    
    for s in range(l):
        buff = cam_q.recv_bytes()
        frame = np.frombuffer(buff, dtype=np.uint8)
        #print(s,frame.shape)

def grabcamQ(q, l):
    start = time.time()
    c = np.random.randint(255, size=(2000,2000,1), dtype=np.uint8)
    cb = c.tobytes()
    for s in range(l):
        q.put(cb)
    print(time.time()-start, " spend")

def getQ(q, l):
    for s in range(l):
        buf = q.get()
        frame = np.frombuffer(buf, dtype=np.uint8)
        #print(s,frame.shape)

def grabcamQQ(q, l):

    start = time.time()
    c = np.random.randint(255, size=(2000,2000,1), dtype=np.uint8)
    for s in range(l):
        q.put(c)
    print(time.time()-start, " spend")
    return

def getQQ(q, l):
    for s in range(l):
        frame = q.get()
    print("sum=")
def test(a):
    a['123'] = 11

def hello():
    print("hello, world")


def show_console(conn, setting):
    # 讀入影片,由於參數傳遞的關係，數據必須先預處理成list才能避免傳遞時使用傳址的方式
    # 第1步，例項化object，建立視窗window

    def sleepbaby():
        time.sleep(10)
        print("i am sleep baby")
    p = Process(target=sleepbaby)
    window = tk.Tk()

    # 第2步，給視窗的視覺化起名字
    window.title('console panel')

    # 第3步，設定視窗的大小(長 * 寬)
    window.geometry('500x500')  # 這裡的乘是小x

    # 第4步，在圖形介面上設定標籤
    var = tk.StringVar()  # 將label標籤的內容設定為字元型別，用var來接收hit_me函式的傳出內容用以顯示在標籤上
    Lable1 = tk.Label(window, text="text", bg='green', fg='white', font=('Arial', 12), width=30, height=2)
    # 說明： bg為背景，fg為字型顏色，font為字型，width為長，height為高，這裡的長和高是字元的長和高，比如height=2,就是標籤有2個字元這麼高
    Lable1.pack()
    Lable2 = tk.Label(window, text="text", bg='blue', fg='white', font=('Arial', 12), width=30, height=2)
    # 說明： bg為背景，fg為字型顏色，font為字型，width為長，height為高，這裡的長和高是字元的長和高，比如height=2,就是標籤有2個字元這麼高
    Lable2.pack()
    def update():
        now = time.time()
        Lable1['text'] = f"{now:.2f}"
        if conn.poll():
            print("setting!")
            info_dict = conn.recv()
            Lable2['text'] = info_dict['label2']
        window.after(1, update)
    Button1 = tk.Button(window, text="test something", command=lambda: setting.send(10))
    Button1.pack()

    # 第6步，主視窗迴圈顯示
    window.after(1, update)
    window.mainloop()
    # 注意，loop因為是迴圈的意思，window.mainloop就會讓window不斷的重新整理，如果沒有mainloop,就是一個靜態的window,傳入進去的值就不會有迴圈，mainloop就相當於一個很大的while迴圈，有個while，每點選一次就會更新一次，所以我們必須要有迴圈
    # 所有的視窗檔案都必須有類似的mainloop函式，mainloop是視窗檔案的關鍵的關鍵。

class Console(Process):
    def __init__(self, cams):
        super().__init__()
        self.conn1 = Pipe(False)
        self.conn2 = Pipe(False)
        self.cams = cams

    def run(self):
        self.show_console(self.conn1[0], self.conn2[1], self.cams)

    def poll(self):
        return self.conn2[0].poll()

    def getConfig(self):
        return self.conn2[0].recv()

    def setState(self, state: dict):
        self.conn1[1].send(state)

    def show_console(self, conn_recv, conn_send, init_cams):

        print("in")
        getCams()
        window = tk.Tk()
        window.title('console panel')
        window.geometry('500x500')  # 這裡的乘是小x

        stage_frame = ttk.Frame(borderwidth=2, relief='solid')
        stage_frame.pack(anchor='center')

        stage_title = tk.Label(stage_frame, text="Stage config", font=('Arial', 12), width=10, height=2, anchor='center')
        stage_title.grid(column=0, row=0, columnspan=5)

        stage_column = ["cam model", "show", "lag", "random", "randfile"]
        stage_col_labels = []
        for col_num, text in enumerate(stage_column):
            stage_col_labels.append(tk.Label(stage_frame, text=text, width=10, anchor='center'))
            stage_col_labels[-1].grid(column=col_num, row=1)

        row_num = 2
        stage_cam_labels = []
        stage_show_vars = []
        stage_lag_entrys = []
        stage_random_vars = []
        stage_random_entrys = []
        for s, cam in enumerate(init_cams):
            stage_cam_labels.append(tk.Label(stage_frame, text=cam, anchor='w'))
            stage_cam_labels[-1].grid(column=0, row=row_num)

            stage_show_vars.append(tk.IntVar(window))
            checkbox = ttk.Checkbutton(stage_frame, variable=stage_show_vars[-1])
            checkbox.grid(column=1, row=row_num)
            stage_show_vars[-1].set(1)

            stage_lag_entrys.append(tk.Entry(stage_frame, width=3))
            stage_lag_entrys[-1].grid(column=2, row=row_num)
            stage_lag_entrys[-1].insert(tk.END, "0")

            stage_random_vars.append(tk.IntVar(window))
            checkbox = ttk.Checkbutton(stage_frame, variable=stage_random_vars[-1])
            checkbox.grid(column=3, row=row_num)

            stage_random_entrys.append(tk.Entry(stage_frame, width=20))
            stage_random_entrys[-1].grid(column=4, row=row_num)
            stage_random_entrys[-1].insert(tk.END, "")

            row_num += 1

        stage_display_var = tk.IntVar(window)
        stage_display_var.set(1)
        stage_light_var = tk.IntVar(window)
        checkbox = ttk.Checkbutton(stage_frame, variable=stage_display_var, text="display")
        checkbox.grid(column=2, row=row_num)
        checkbox = ttk.Checkbutton(stage_frame, variable=stage_light_var, text="light")
        checkbox.grid(column=3, row=row_num)

        config = {}
        def setting():
            for s, cam in enumerate(init_cams):
                config[s] = {"show": stage_show_vars[s].get(), "lag": int(stage_lag_entrys[s].get())
                             , "random": stage_random_vars[s].get(), "rand_path": stage_random_entrys[s].get()}
            config["display"] = stage_display_var.get()
            config["light"] = stage_light_var.get()
            conn_send.send(config)
        stage_set_but = tk.Button(stage_frame, text="SET", command=setting, heigh=1, width=6, font=('Arial Bold', 12))
        stage_set_but.grid(column=4, row=row_num)
        setting()

        exp_frame = ttk.Frame(borderwidth=2, relief='solid')
        exp_frame.pack(anchor='center')

        exp_title = tk.Label(exp_frame, text="Experiment", font=('Arial', 12), width=10, height=2, anchor='center')
        exp_title.grid(column=0, row=0, columnspan=5)

        exp_break_label = tk.Label(exp_frame, text="Break time")
        exp_break_label.grid(column=0, row=1)
        exp_break_entry = tk.Entry(exp_frame)
        exp_break_entry.grid(column=1, row=1)

        def execute():
            for child in stage_frame.winfo_children():
                child.configure(state='disable')

        exp_execute_but = tk.Button(exp_frame, text="EXECUTE", command=execute)
        exp_execute_but.grid(column=4, row=row_num)

        def update():
            if conn_recv.poll():
                pass
            window.after(1, update)

        # 第6步，主視窗迴圈顯示
        window.after(1, update)
        window.mainloop()

        # 注意，loop因為是迴圈的意思，window.mainloop就會讓window不斷的重新整理，如果沒有mainloop,就是一個靜態的window,傳入進去的值就不會有迴圈，mainloop就相當於一個很大的while迴圈，有個while，每點選一次就會更新一次，所以我們必須要有迴圈
        # 所有的視窗檔案都必須有類似的mainloop函式，mainloop是視窗檔案的關鍵的關鍵。


if __name__ == "__main__":
    os.environ["PYLON_CAMEMU"] = "3"
    maxCamerasToUse = 2
    countOfImagesToGrab = 200
    try:
        # Get the transport layer factory.
        tlFactory = pylon.TlFactory.GetInstance()

        # Get all attached devices and exit application if no device is found.
        devices = tlFactory.EnumerateDevices()
        if len(devices) == 0:
            raise pylon.RuntimeException("No camera present.")

        # Create an array of instant cameras for the found devices and avoid exceeding a maximum number of devices.
        cameras = pylon.InstantCameraArray(min(len(devices), maxCamerasToUse))

        l = cameras.GetSize()
        timelst = []

        # Create and attach all Pylon Devices.
        for i, cam in enumerate(cameras):

            # Print the model name of the camera.
            cam.Attach(tlFactory.CreateDevice(devices[i]))
            print("Using device ", cam.GetDeviceInfo().GetModelName())

            if "E" not in cam.GetDeviceInfo().GetModelName():
                cam.Open()
                cam.AcquisitionFrameRate.SetValue(10)
                cam.AcquisitionFrameRateEnable.SetValue(True)
                cam.Close()

            timelst.append([])


        # Starts grabbing for all cameras starting with index 0. The grabbing
        # is started for one camera after the other. That's why the images of all
        # cameras are not taken at the same time.
        # However, a hardware trigger setup can be used to cause all cameras to grab images synchronously.
        # According to their default configuration, the cameras are
        # set up for free-running continuous acquisition.
        cameras.StartGrabbing()
        n0 = time.time()
        start = time.time()

        # Grab c_countOfImagesToGrab from the cameras.
        for i in range(countOfImagesToGrab):
            if not cameras.IsGrabbing():
                break

            grabResult = cameras.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

            # When the cameras in the array are created the camera context value
            # is set to the index of the camera in the array.
            # The camera context is a user settable value.
            # This value is attached to each grab result and can be used
            # to determine the camera that produced the grab result.
            cameraContextValue = grabResult.GetCameraContext()
            now = time.time()

            # Print the index and the model name of the camera.
            # print(f"Camera", cameraContextValue, f"{now-start:.3f}",
            #       ": ", cameras[cameraContextValue].GetDeviceInfo().GetModelName())
            start = now
            timelst[cameraContextValue].append(now)

            # Now, the image data can be processed.
            # print("GrabSucceeded: ", grabResult.GrabSucceeded())
            # print("SizeX: ", grabResult.GetWidth())
            # print("SizeY: ", grabResult.GetHeight())
            #img = grabResult.GetArray()
            # print("Gray value of first pixel: ", img[0, 0])
    except:
        pass
    #console = Console([1,2,3])
    #console.start()
    for t in timelst[0]:
        print(f"{t-n0:.3f} ", end=" ||")
    time.sleep(1)

    exit()
    conn_rev, conn_sed = Pipe(False)
    sett_get, sett_put = Pipe(False)
    console = Process(target=show_console, args=(conn_rev, sett_put))
    console.start()
    time.sleep(1)
    conn_sed.send({"label2": "i am ready"})
    time.sleep(1)
    conn_sed.send({"label2": "i am ready, NOW"})
    time.sleep(1)
    conn_sed.send({"label2": "i am ready, PLZ"})
    time.sleep(1)
    conn_sed.send({"label2": "i am going to died!"})
    time.sleep(1)
    conn_sed.send({"label2": "GO"})

    while console.is_alive():
        if sett_get.poll():
            print(sett_get.recv())
    exit()
    Test2()

    img = np.zeros((100,200), dtype='uint8')
    print(cv2.resize(img, (20,10)).shape)

    a = np.arange(12).reshape(3,2,2)
    print(np.rot90(a))

    exit()
    sleep(2)

    q = Queue()
    l = 3000
    window = Process(target=grabcamQQ, args=(q,l,))
    console = Process(target=getQQ, args=(q,l//3,))
    console2 = Process(target=getQQ, args=(q,l//3,))
    console3 = Process(target=getQQ, args=(q,l//3,))
    start = time.time()
    window.start()
    console.start()
    console2.start()
    console3.start()

    #console.join()
    window.join()
    print(f"use queue : {time.time()-start:.5f}")


    sleep(2)

    q = Queue()
    l = 3000
    window = Process(target=grabcamQQ, args=(q,l,))
    console = Process(target=getQQ, args=(q,l,))
    start = time.time()
    window.start()
    console.start()

    #console.join()
    window.join()
    print(f"use queue : {time.time()-start:.5f}")
    sys.exit()


    q = Queue()

    window = Process(target=grabcamQ, args=(q,l,))
    console = Process(target=getQ, args=(q,l//2,))
    console2 = Process(target=getQ, args=(q,l//2,))
    start = time.time()
    window.start()
    console.start()
    console2.start()

    #console.join()
    window.join()
    print(f"use queue (buff) : {time.time()-start:.5f}")

"""    a, b = Pipe(False)

    window = Process(target=grabCam, args=(b, l,))
    console = Process(target=getCam, args=(a, l,))
    start = time.time()
    window.start()
    console.start()

    #console.join()
    window.join()
    print(f"use queue (buff) : {time.time() - start:.5f}")

    sleep(2)
"""

    
"""    exit()
    start = time.time()
    print(start)
    for s in range(1):
        q.put(c)
        print(s)

    print(q.get())
    print(f"{time.time()-start:.5f}")


    a, b = Pipe()
    start = time.time()

    for s in range(1):
        a.send(c)
        b.recv()
    print(f"{time.time()-start:.5f}")

    time.sleep(5)"""


