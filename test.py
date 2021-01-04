import numpy as np
from multiprocessing import Process, Value, Pipe, Pool, Manager
from ctypes import c_bool
from multiprocessing import Queue
import cv2
from time import sleep
import time
import sys, os
#import pygame

def grabCam(cam_q, l):
    start = time.time()
    c = np.random.randint(255, size=(4000,2000,3), dtype=np.uint8)
    cb = c.tobytes()
    for s in range(l):
        cam_q.send_bytes(cb)

    print(f"use pipe : {time.time()-start:.5f}")
    

def getCam(cam_q, l):
    
    for s in range(l):
        sleep(0.1)
        buff = cam_q.recv_bytes()
        #print(s,frame.shape)

def grabcamQ(q, l):
    start = time.time()
    c = np.random.randint(255, size=(4000,2000,3), dtype=np.uint8)
    cb = c.tobytes()
    for s in range(l):
        q.put_nowait(cb)
    print(f"use queue : {time.time()-start:.5f}")

def getQ(q, l):
    for s in range(l):
        sleep(0.1)
        buff = q.get()
        frame = np.frombuffer(buff, dtype=np.uint8)
        #print(s,frame.shape)

def test(a):
    a['123'] = 11

if __name__ == "__main__":
    sleep(2)
    a, b = Pipe()
    l = 100
    window = Process(target=grabCam, args=(a,l,))
    console = Process(target=getCam, args=(b,l,))
    start = time.time()
    window.start()
    console.start()

    window.join()

    sleep(2)

    q = Queue()

    window = Process(target=grabcamQ, args=(q,l,))
    console = Process(target=getQ, args=(q,l,))
    start = time.time()
    window.start()
    console.start()

    """console.join()  #等待console結束，主程序才會繼續
    window.terminate()  #一旦console join, 摧毀window程序"""

    window.join()


    sleep(2)

    
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


