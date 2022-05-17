import pygame
import numpy as np
import time
import datetime
from pypylon import pylon
import cv2
import os
import json
import tkinter as tk
from tkinter import ttk
from multiprocessing import Process, Queue, Pipe
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
        self.model = camera.GetDeviceInfo().GetModelName()
        self.cam_shape, self.dtype = self.camConfig(camera)
        self.shape = np.array([self.cam_shape[1], self.cam_shape[0]])
        self.camera = camera
        self.tank_shape = tuple((self.shape * min(tank_size / self.shape)).astype(np.int))
        self.rect = pygame.Rect((0, 0), tuple(self.tank_shape))
        self.rect.center = tuple(sc_shape // 2)
        self.setDelayCount(0)

    def setDelayCount(self, count):
        self.delaycount = count
        self.scenes = [np.zeros(np.append(self.tank_shape, [3]), dtype=np.uint8)] * count

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

        config = {"record": False}
        schedule = []
        console_dict = {"state": "idle"}
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
        stage_light_var.set(1)
        checkbox = ttk.Checkbutton(stage_frame, variable=stage_display_var, text="display")
        checkbox.grid(column=2, row=row_num)
        checkbox = ttk.Checkbutton(stage_frame, variable=stage_light_var, text="light")
        checkbox.grid(column=3, row=row_num)

        def setting():
            for s, cam in enumerate(init_cams):
                config[s] = {"show": stage_show_vars[s].get(), "lag": int(stage_lag_entrys[s].get())
                             , "random": stage_random_vars[s].get(), "rand_path": stage_random_entrys[s].get()}
            config["display"] = stage_display_var.get()
            config["light"] = stage_light_var.get()
            conn_send.send(config)

        def load(load_config):
            for s, cam in enumerate(init_cams):
                stage_show_vars[s].set(load_config[s]['show'])
                stage_lag_entrys[s]['text'] = load_config[s]['lag']
                stage_random_vars[s].set(load_config[s]['random'])
                stage_random_entrys[s]['text'] = load_config[s]['rand_path']
            stage_display_var.set(config["display"])
            stage_light_var.set(config["light"])

        stage_set_but = tk.Button(stage_frame, text="SET", command=setting, heigh=1, width=6, font=('Arial Bold', 12))
        stage_set_but.grid(column=4, row=row_num)
        setting()

        exp_frame = ttk.Frame(borderwidth=2, relief='solid')
        exp_frame.pack(anchor='center')

        exp_title = tk.Label(exp_frame, text="Experiment", font=('Arial', 12), width=10, height=2, anchor='center')
        exp_title.grid(column=0, row=0, columnspan=5)

        exp_break_label = tk.Label(exp_frame, text="Break time (sec)")
        exp_break_label.grid(column=0, row=1)
        exp_break_entry = tk.Entry(exp_frame)
        exp_break_entry.grid(column=1, row=1)

        exp_duration_label = tk.Label(exp_frame, text="Duration (sec)")
        exp_duration_label.grid(column=0, row=2)
        exp_duration_entry = tk.Entry(exp_frame)
        exp_duration_entry.grid(column=1, row=2)

        exp_filename_label = tk.Label(exp_frame, text="Saving name")
        exp_filename_label.grid(column=0, row=3)
        exp_filename_entry = tk.Entry(exp_frame)
        exp_filename_entry.insert(tk.END, "exp")
        exp_filename_entry.grid(column=1, row=3)

        exp_repeat_label = tk.Label(exp_frame, text="Repeats")
        exp_repeat_label.grid(column=0, row=4)
        exp_repeat_entry = tk.Entry(exp_frame)
        exp_repeat_entry.insert(tk.END, '1')
        exp_repeat_entry.grid(column=1, row=4)

        def breaking():
            console_dict['state'] = "breaking"
            config['display'] = False
            config['light'] = False
            load(config)
            setting()

        def lighting():
            config['display'] = True
            config['light'] = True
            load(config)
            setting()

        def recording():
            console_dict['state'] = "recording"
            config["record"] = True
            setting()

        def done():
            exp_repeat_entry.insert(tk.END, str(int(exp_repeat_entry.get())-1))
            config["record"] = False
            setting()

        def execute():
            for child in stage_frame.winfo_children():
                child.configure(state='disable')
            for child in exp_frame.winfo_children():
                child.configure(state='disable')
            repeat = int(exp_repeat_entry.get())
            break_sec = int(exp_break_entry.get())
            duration_sec = int(exp_duration_entry.get())
            foldername = exp_filename_entry.get()
            config['folder'] = foldername
            config['duration'] = duration_sec
            sec = 0
            for s in range(repeat):
                schedule.append(window.after(sec*1000, breaking))
                sec += break_sec
                schedule.append(window.after(sec*1000, lighting))
                sec += 2
                schedule.append(window.after(sec*1000, recording))
                sec += duration_sec+5
                schedule.append(window.after(sec*1000, done))
            schedule.append(window.after(sec*1000, stop))
        exp_execute_but = tk.Button(exp_frame, text="EXECUTE", command=execute)
        exp_execute_but.grid(column=5, row=10)

        exp_current_label = tk.Label(window)
        exp_current_label.pack()

        def stop():
            console_dict['state'] = "idle"
            for work in schedule:
                window.after_cancel(work)
            for child in stage_frame.winfo_children():
                child.configure(state='normal')
            for child in exp_frame.winfo_children():
                child.configure(state='normal')
            config['record'] = False
            setting()
        stop_but = tk.Button(window, text="STOP", heigh=1, width=6, font=('Arial Bold', 14), command=stop)
        stop_but.pack(anchor="n")

        def update():
            if conn_recv.poll():
                pass
            exp_current_label['text'] = console_dict['state']
            window.after(1, update)

        # 第6步，主視窗迴圈顯示
        window.after(1, update)
        window.mainloop()

class RecCamera(Process):
    def __init__(self, camera, fps=30):
        super().__init__()
        self.camera_model = camera.GetDeviceInfo().GetModelName()
        self.path = ""
        self.duration = 10
        self.fps = fps
        self.config = {"fps": fps}

    def setFolder(self, path):
        if os.path.exists(path):
            s = 0
            while os.path.exists(path+f"{s}"):
                s+=1
            path = path+f"{s}"
        self.path = path

    def setDuration(self, duration):
        self.duration = duration

    def setConfig(self, config: dict):
        for key, value in config.items():
            self.config[key] = value

    def run(self):

        T1 = pylon.TlFactory.GetInstance()
        lstDevices = T1.EnumerateDevices()
        num = 0
        for s, cam_info in enumerate(lstDevices):
            camera = pylon.InstantCamera(T1.CreateFirstDevice(cam_info))
            if self.camera_model == camera.GetDeviceInfo().GetModelName():
                num = s
        camera = pylon.InstantCamera(T1.CreateFirstDevice(lstDevices[num]))

        camera.Open()
        camera.AcquisitionFrameRateEnable.SetValue(True)
        camera.AcquisitionFrameRate.SetValue(self.fps)
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        path = self.path
        if os.path.exists(path):
            s = 0
            while os.path.exists(path+f"{s}"):
                s+=1
            path = path+f"{s}"
        os.mkdir(path)

        with open(os.path.join(path, "config"), 'w') as file:
            json.dump(self.config, file)

        for s in range(self.duration*self.fps):
            grabResult = camera.RetrieveResult(10000, pylon.TimeoutHandling_ThrowException)
            if grabResult.GrabSucceeded():
                np.save(os.path.join(path, f"{s}.npy"), grabResult.GetArray())
        camera.Close()


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
    pgFps = 30
    delay = 0
    crack = 0

    # loading arduino
    PORT = Arduino.AUTODETECT
    if not isinstance(PORT, str):
        print("no Arduino is detected")
    else:
        print(f"Arduino is detected at PORT {PORT}")

    board = Arduino("COM4")

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

    # rect config
    tank_sel = False
    m_pos = (0, 0)
    setDisplace = lambda x: None

    # rec config
    if not rec_cams is None:
        recorder = RecCamera(rec_cams)

    # loop start
    while is_running and console.is_alive():
        # the rects will be updated, it is the key point to take fps stable
        rects = []

        # all keyboard event is detected here
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                is_running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for obj in reversed(pyg_cameras):
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
            show_cameras = []
            for s, obj in enumerate(pyg_cameras):
                if config[s]["show"] == 1:
                    show_cameras.append(obj)
                lag = config[s]["lag"]
                obj.setDelayCount(pgFps*lag)
            is_display = config["display"]==1
            if config["light"] == 1:
                board.digital[12].write(1)
            else:
                board.digital[12].write(0)

            if 'record' in config.keys() and rec_cams:
                if config['record']:
                    if not recorder.is_alive():
                        savepath = os.path.join(workpath, config['folder'])
                        recorder.setFolder(savepath)
                        recorder.setDuration(config['duration'])
                        recorder.start()
                elif recorder.is_alive():
                    recorder.terminate()
                    del recorder
                    recorder = RecCamera(rec_cams)
                else:
                    del recorder
                    recorder = RecCamera(rec_cams)

            rects.append(screen.fill(bk_color))
            # update the value


        # update the pos
        if tank_sel:
            rects.append(screen.fill(bk_color))
            c_pos = pygame.mouse.get_pos()
            setDisplace((c_pos[0]-m_pos[0], c_pos[1]-m_pos[1]))
            m_pos = c_pos

        # update the screen
        for obj in show_cameras:
            frame = obj.update()
            rect = obj.rect
            cover = screen.blit(frame, rect)
            rects.append(rect)

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
    console.terminate()
