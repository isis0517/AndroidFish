import json
import time
import tkinter as tk
import tkinter.ttk as ttk
from multiprocessing import Pipe, Process
import os
import cv2
from pyfirmata2 import Arduino
from tkinter.filedialog import asksaveasfile
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

        self.pgFps_prompt = tk.Label(self, text="pygame frame rate:")
        self.pgFps_prompt.grid(column=0, row=row_num, sticky="W")
        self.pgFps_entry = tk.Entry(self, width=5)
        self.pgFps_entry.insert(tk.END, 30)
        self.pgFps_entry.grid(column=1, row=row_num, sticky="W")
        row_num += 1

        self.arport_prompt = tk.Label(self, text="Arduino port")
        self.arport_prompt.grid(column=0, row=row_num, sticky="W")
        self.arport_entry = tk.Entry(self, width=5)
        self.arport_entry.insert(tk.END, str(Arduino.AUTODETECT))
        self.arport_entry.grid(column=1, row=row_num, sticky="W")
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
        self.pgFps = int(self.pgFps_entry.get())
        self.port = self.arport_entry.get()
        self.root.destroy()


class ConfigWindow(tk.Frame):
    def __init__(self, conn_recv, conn_send, init_cams):
        self.root = tk.Tk()
        self.init_cams = init_cams
        self.conn_recv = conn_recv
        self.conn_send = conn_send
        self.sec = 0
        self.start = int(time.time())
        super().__init__(self.root)

        self.config = {"record": False, "debug_cam": -1, "is_running": True}
        self.schedule = []
        self.console_dict = {"state": "idle"}
        self.root.title('console panel')

        self.stage_frame = ttk.Frame(borderwidth=2, relief='solid')
        self.stage_frame.pack(anchor='center')

        self.stage_title = tk.Label(self.stage_frame, text="Stage config", font=('Arial', 12), width=10, height=2, anchor='center')
        self.stage_title.grid(column=0, row=0, columnspan=5)

        self.stage_column = ["cam model", "show", "lag", "center of mass", "threshold"]
        self.stage_col_labels = []
        for col_num, text in enumerate(self.stage_column):
            self.stage_col_labels.append(tk.Label(self.stage_frame, text=text, width=12, anchor='center'))
            self.stage_col_labels[-1].grid(column=col_num, row=1)

        row_num = 2
        self.stage_cam_labels = []
        self.stage_show_vars = []
        self.stage_lag_entrys = []
        self.stage_com_vars = []
        self.stage_threshold_entrys = []
        for s, cam in enumerate(self.init_cams):
            self.stage_cam_labels.append(tk.Label(self.stage_frame, text=cam, anchor='w'))
            self.stage_cam_labels[-1].grid(column=0, row=row_num)

            self.stage_show_vars.append(tk.IntVar(self.root))
            checkbox = ttk.Checkbutton(self.stage_frame, variable=self.stage_show_vars[-1])
            checkbox.grid(column=1, row=row_num)
            self.stage_show_vars[-1].set(1)

            self.stage_lag_entrys.append(tk.Entry(self.stage_frame, width=3))
            self.stage_lag_entrys[-1].grid(column=2, row=row_num)
            self.stage_lag_entrys[-1].insert(tk.END, "0")

            self.stage_com_vars.append(tk.IntVar(self.root))
            checkbox = ttk.Checkbutton(self.stage_frame, variable=self.stage_com_vars[-1])
            checkbox.grid(column=3, row=row_num)

            self.stage_threshold_entrys.append(tk.Entry(self.stage_frame, width=4))
            self.stage_threshold_entrys[-1].grid(column=4, row=row_num)
            self.stage_threshold_entrys[-1].insert(tk.END, "30")

            row_num += 1

        self.stage_display_var = tk.IntVar(self.root)
        self.stage_display_var.set(1)
        self.stage_light_var = tk.IntVar(self.root)
        self.stage_light_var.set(1)
        checkbox = ttk.Checkbutton(self.stage_frame, variable=self.stage_display_var, text="display")
        checkbox.grid(column=2, row=row_num)
        checkbox = ttk.Checkbutton(self.stage_frame, variable=self.stage_light_var, text="light")
        checkbox.grid(column=3, row=row_num)

        self.stage_set_but = tk.Button(self.stage_frame, text="SET", command=self.setting, heigh=1, width=6, font=('Arial Bold', 12))
        self.stage_set_but.grid(column=4, row=row_num)

        self.exp_frame = ttk.Frame(borderwidth=2, relief='solid')
        self.exp_frame.pack(anchor='center')

        self.exp_title = tk.Label(self.exp_frame, text="Experiment", font=('Arial', 12), width=10, height=2, anchor='center')
        self.exp_title.grid(column=0, row=0, columnspan=5)

        self.exp_break_label = tk.Label(self.exp_frame, text="Break time (sec)")
        self.exp_break_label.grid(column=0, row=1)
        self.exp_break_entry = tk.Entry(self.exp_frame)
        self.exp_break_entry.insert(tk.END, "300")
        self.exp_break_entry.grid(column=1, row=1)

        self.exp_duration_label = tk.Label(self.exp_frame, text="Duration (sec)")
        self.exp_duration_label.grid(column=0, row=2)
        self.exp_duration_entry = tk.Entry(self.exp_frame)
        self.exp_duration_entry.insert(tk.END, "600")
        self.exp_duration_entry.grid(column=1, row=2)

        self.exp_filename_label = tk.Label(self.exp_frame, text="Saving name")
        self.exp_filename_label.grid(column=0, row=3)
        self.exp_filename_entry = tk.Entry(self.exp_frame)
        self.exp_filename_entry.insert(tk.END, "exp")
        self.exp_filename_entry.grid(column=1, row=3)

        self.exp_repeat_label = tk.Label(self.exp_frame, text="Repeats")
        self.exp_repeat_label.grid(column=0, row=4)
        self.exp_repeat_entry = tk.Entry(self.exp_frame)
        self.exp_repeat_entry.insert(tk.END, '1')
        self.exp_repeat_entry.grid(column=1, row=4)

        self.exp_execute_but = tk.Button(self.exp_frame, text="EXECUTE", command=self.execute)
        self.exp_execute_but.grid(column=5, row=10)

        self.stop_but = tk.Button(self.root, text="STOP record", heigh=1, font=('Arial Bold', 12), command=self.stop)
        self.stop_but.pack(side=tk.RIGHT, fill=tk.BOTH)

        self.dump_but = tk.Button(self.root, text="Dump config", heigh=1, font=('Arial Bold', 12), command=self.dump)
        self.dump_but.pack(side=tk.LEFT, fill=tk.BOTH)

        self.exp_current_label = tk.Label(self.root)
        self.exp_current_label.pack(anchor='center')

        self.debug_frame = ttk.Frame(self.root, borderwidth=2, relief='solid', width=100)
        self.debug_frame.pack(anchor='center')

        self.debug_label = tk.Label(self.debug_frame, text="debug camera:")
        self.debug_label.grid(column=0, row=0)

        self.debug_camera_combo = ttk.Combobox(self.debug_frame, values=["None"] + self.init_cams, width=7)
        self.debug_camera_combo.current(0)
        self.debug_camera_combo.grid(column=1, row=0)

        self.schedule_frame = ttk.Frame(self.root, borderwidth=2, relief='solid')
        self.schedule_frame.pack(side=tk.Button)

        self.schedule_title = tk.Label(self.schedule_frame, text="Schedule", font=('Arial', 12))
        self.schedule_title.grid(column=0, row=0, columnspan=5)

        self.debug_camera_combo.bind("<<ComboboxSelected>>", self.combo_set)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        # 第6步，主視窗迴圈顯示
        self.exp_setting()
        self.stage_setting()
        self.send_config()
        self.root.after(1, self.update)
        self.root.mainloop()

    def send_config(self):
        self.conn_send.send(self.config)

    def setting(self):
        self.stage_setting()
        self.send_config()

    def stage_setting(self):
        for s, cam in enumerate(self.init_cams):
            self.config[s] = {"show": self.stage_show_vars[s].get(), "lag": int(self.stage_lag_entrys[s].get())
                , "com": self.stage_com_vars[s].get(), "threshold": int(self.stage_threshold_entrys[s].get())}
        self.config["display"] = self.stage_display_var.get()
        self.config["light"] = self.stage_light_var.get()

    def show_stage(self, load_config):
        for s, cam in enumerate(self.init_cams):
            self.stage_show_vars[s].set(load_config[s]['show'])
            self.stage_lag_entrys[s]['text'] = load_config[s]['lag']
            self.stage_com_vars[s].set(load_config[s]['com'])
            self.stage_threshold_entrys[s]['text'] = load_config[s]['threshold']
        self.stage_display_var.set(self.config["display"])
        self.stage_light_var.set(self.config["light"])

    def breaking(self):
        self.console_dict['state'] = "breaking"
        self.config['display'] = False
        self.config['light'] = False
        self.show_stage(self.config)
        self.send_config()

    def lighting(self):
        self.config['display'] = True
        self.config['light'] = True
        self.show_stage(self.config)
        self.send_config()

    def recording(self):
        self.console_dict['state'] = "recording"
        self.config["record"] = True
        self.send_config()

    def done(self):
        self.exp_repeat_entry.insert(tk.END, str(int(self.exp_repeat_entry.get()) - 1))
        self.config["record"] = False
        self.send_config()

    def exp_setting(self):
        repeat = int(self.exp_repeat_entry.get())
        break_sec = int(self.exp_break_entry.get())
        duration_sec = int(self.exp_duration_entry.get())
        foldername = self.exp_filename_entry.get()
        self.config['repeat'] = repeat
        self.config['folder'] = foldername
        self.config['duration'] = duration_sec
        self.config['break_sec'] = break_sec

    def show_exp(self, load_config):
        self.exp_repeat_entry.insert(tk.END, load_config['repeat'])
        self.exp_break_entry.insert(tk.END, load_config['break_sec'])
        self.exp_duration_entry.insert(tk.END, load_config['duration'])
        self.exp_filename_entry.insert(tk.END, load_config['folder'])

    def schedule_setting(self, sec=0):
        repeat = self.config['repeat']
        duration_sec = self.config['duration']
        break_sec = self.config['break_sec']
        for s in range(repeat):
            self.schedule.append(self.root.after(sec * 1000, self.breaking))
            sec += break_sec
            self.schedule.append(self.root.after(sec * 1000, self.lighting))
            sec += 2
            self.schedule.append(self.root.after(sec * 1000, self.recording))
            sec += duration_sec + 5
            self.schedule.append(self.root.after(sec * 1000, self.done))
        self.schedule.append(self.root.after(sec * 1000, self.stop))
        return sec

    def execute(self):
        for child in self.stage_frame.winfo_children():
            child.configure(state='disable')
        for child in self.exp_frame.winfo_children():
            child.configure(state='disable')
        self.stage_setting()
        self.exp_setting()
        self.sec = self.schedule_setting()
        self.start = int(time.time())

    def stop(self):
        self.console_dict['state'] = "idle"
        for work in self.schedule:
            self.root.after_cancel(work)
        for child in self.stage_frame.winfo_children():
            child.configure(state='normal')
        for child in self.exp_frame.winfo_children():
            child.configure(state='normal')
        self.config['record'] = False
        self.stage_setting()
        self.sec = 0

    def dump(self):
        temp = self.config.copy()
        duration_sec = int(self.exp_duration_entry.get())
        foldername = self.exp_filename_entry.get()
        temp['folder'] = foldername
        temp['duration'] = duration_sec
        for s, cam in enumerate(self.init_cams):
            temp[s] = {"show": self.stage_show_vars[s].get(), "lag": int(self.stage_lag_entrys[s].get())
                , "com": self.stage_com_vars[s].get(), "threshold": int(self.stage_threshold_entrys[s].get())}
        temp["display"] = self.stage_display_var.get()
        temp["light"] = self.stage_light_var.get()
        out_file = asksaveasfile(mode='w', defaultextension="txt")
        if out_file is None:
            return
        json.dump(temp, out_file)
        out_file.close()

    def combo_set(self, event):
        c_num = self.debug_camera_combo.current() - 1
        if c_num >= 0 and not self.stage_show_vars[c_num].get() == 1:
            c_num = -1
        self.config["debug_cam"] = c_num
        self.stage_setting()

    def update(self):
        if self.conn_recv.poll():
            img = self.conn_recv.recv()
            cv2.imshow(self.init_cams[self.config['debug_cam']], img)
            cv2.waitKey(1)
        delta = 0
        if self.sec:
            delta = int(time.time()) - self.start
        self.exp_current_label['text'] = self.console_dict['state'] + f", {self.sec - delta}sec left"
        self.root.after(1, self.update)


    def close(self):
        self.config["debug_cam"] = -1
        self.config["is_running"] = False
        self.send_config()
        time.sleep(1)
        _ = self.conn_recv.recv()
        self.root.destroy()


class Console(Process):
    def __init__(self, cams):
        super().__init__()
        self.conn1 = Pipe(False)
        self.conn2 = Pipe(False)
        self.cams = cams

    def run(self):
        self.window = ConfigWindow(self.conn1[0], self.conn2[1], self.cams)
        #self.show_console(self.conn1[0], self.conn2[1], self.cams)

    def poll(self):
        return self.conn2[0].poll()

    def getConfig(self):
        return self.conn2[0].recv()

    def send(self, mes):
        if self.conn1[1].closed:
            raise Exception()
        self.conn1[1].send(mes)
