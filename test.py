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
        buff = cam_q.recv_bytes()
        #print(s,frame.shape)

def grabcamQ(q, l):
    c = np.random.randint(255, size=(4000,2000,3), dtype=np.uint8)
    cb = c.tobytes()
    for s in range(l):
        q.put_nowait(cb)

def getQ(q, l):
    for s in range(l):
        try:
            buf = q.get()
        except:
            pass
        frame = np.frombuffer(buf, dtype=np.uint8)
        #print(s,frame.shape)

def grabcamQQ(q, l):
    c = np.random.randint(255, size=(4000,2000,3), dtype=np.uint8)
    for s in range(l):
        q.put_nowait(c)

def getQQ(q, l):
    for s in range(l):
        try:
            frame = q.get()
        except:
            pass

def test(a):
    a['123'] = 11

if __name__ == "__main__":
    sleep(2)

    q = Queue()
    l = 200
    window = Process(target=grabcamQQ, args=(q,l,))
    console = Process(target=getQQ, args=(q,l,))
    start = time.time()
    window.start()
    console.start()

    console.join()
    window.join()
    print(f"use queue : {time.time()-start:.5f}")


    q = Queue()

    window = Process(target=grabcamQ, args=(q,l,))
    console = Process(target=getQ, args=(q,l,))
    start = time.time()
    window.start()
    console.start()

    console.join()
    window.join()
    print(f"use queue (buff) : {time.time()-start:.5f}")


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


