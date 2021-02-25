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

if __name__ == "__main__":

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


