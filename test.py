import numpy as np
from multiprocessing import Process, Value, Pipe, Pool, Manager
from ctypes import c_bool
from multiprocessing import Queue
import cv2
from time import sleep
import time
import sys, os

from pypylon import genicam
from pypylon import pylon
#import pygame

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

    os.environ["PYLON_CAMEMU"] = "3"

    # Number of images to be grabbed.
    countOfImagesToGrab = 10

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


