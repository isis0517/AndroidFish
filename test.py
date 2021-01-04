import numpy as np
from multiprocessing import Process, Value, Pipe, Pool, Manager
from ctypes import c_bool
from multiprocessing import SimpleQueue as Queue
import cv2
from time import sleep
import time
import sys, os
import pygame

def grabCam(cam_q, l):
    c = np.random.randint(255, size=(4000,2000,3), dtype=np.uint8)
    for s in range(l):
        cam_q.send(c)
    return
    

def getCam(cam_q, l):
    
    for s in range(l):
        frame = cam_q.recv()
        #print(s,frame.shape)

def picam(cam_p, l):
    c = np.random.randint(255, size=(4000,2000,3), dtype=np.uint8)
    print(c.nbytes)
    cb = c.tobytes()
    for s in range(l):
        cam_p.send_bytes(cb)

def getpi(cam_p, l):
    for s in range(l):
        buff = cam_p.recv_bytes()
        frame = np.frombuffer(buff, dtype=np.uint8)
        #print(s,frame.shape)

def test(a):
    a['123'] = 11

if __name__ == "__main__":
    a = dict({"123":12})
    print(a)
    test(a)
    print(a)
    with Manager() as manager:
        t = manager.dict({'shape':(10,1)})
        print(t['shape'])

    exit()
    a, b  = Pipe()
    l = 60
    window = Process(target=grabCam, args=(a,l,))
    console = Process(target=getCam, args=(b,l,))
    start = time.time()
    window.start()
    console.start()

    console.join()  #等待console結束，主程序才會繼續
    window.terminate()  #一旦console join, 摧毀window程序

    print(f"{time.time()-start:.5f}")
    sleep(2)

    a, b  = Pipe()

    window = Process(target=picam, args=(a,l,))
    console = Process(target=getpi, args=(b,l,))
    start = time.time()
    window.start()
    console.start()

    console.join()  #等待console結束，主程序才會繼續
    window.terminate()  #一旦console join, 摧毀window程序

    print(f"{time.time()-start:.5f}")
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


