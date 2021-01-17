# this project is for interact with real zebrafish
# it should contain follows function without inferance to each other:
#   1. load img from camera
#   2. save img from camera
#   3. show the image which interact with fish

from multiprocessing import Process, Value, Queue, Manager
from Cam import grabCam
from ctypes import c_bool
from ShImg import showImg
import time

if __name__ == "__main__":
    cam_q = Queue()  # the Queue for camera img
    is_Running = Value(c_bool, True)
    saving = Value(c_bool, False)

    man = Manager()
    form = man.list([None, None])
    camera = Process(args=(cam_q, is_Running, form, ), target=grabCam,
                     kwargs={'mode': "video", "c_num": 1, "secs": 20, "saving": saving})
    windows = Process(target=showImg, args=(cam_q, is_Running, form,),
                      kwargs={'mode': "traj", 'calibrate': False, "full": True, "saving": saving})

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
