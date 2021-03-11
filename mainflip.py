from multiprocessing import Pool, Process, Value, Queue, Manager
import os
import queue
import numpy as np
import time
from pypylon import pylon
from ctypes import c_bool
import cv2

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

def savebuff(buff, s, shape, dtype=np.float, savepath=""):
    img = np.ndarray(shape, dtype=dtype, buffer=buff)
    np.save(os.path.join(savepath, f"frame_{s}.npy"), img)


def grabCam(cam_q: Queue, is_running, form, mode="camera", FrameRate=30, secs=10, c_num=0, savepath="",
            saving=Value(c_bool, False)):
    """
        args:
            cam_q : the Pipe comunnecate with cam2img
        kwargs:
            mode : the mode of thish function
                allow value:
                {"camera" -> default
                 "video"}

            FrameRate : the fps of camera
            secs : recording time
            c_num : the number of camera
    """

    if not os.path.isdir(os.path.join(savepath, "frames")):
        os.mkdir(os.path.join(savepath, "frames"))
        savepath = os.path.join(savepath, "frames")
    print(f"The camera is action in {mode} mode")


    #init para
    shape, dtype = (0, 0), 'uint8'
    sf_bin = False

    # video mode
    if mode == "video":

        video = cv2.VideoCapture("F_F_03.avi")

        shape = (int(video.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                 int(video.get(cv2.CAP_PROP_FRAME_WIDTH)), 3)
        dtype = 'uint8'
        form[0] = shape
        form[1] = dtype

        s = 0
        if not video.isOpened():
            print("fail")
        print("video")
        start = time.time()
        while video.isOpened():
            ret, frame = video.read()
            s += 1
            cam_q.put_nowait(frame.tobytes())
            time.sleep(0.03)
            if time.time() - start > secs:
                is_running.value = False

                break
        print("stop")
        return

    # camera mode
    if mode == "camera":

        # connect to the first available camera
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
        except Exception as e:
            print("init fail")
            print(e)
            exit()

        camera.Open()

        try:
            camera.BinningVertical.SetValue(1)
            camera.BinningHorizontal.SetValue(1)
        except Exception as e:
            sf_bin = True

        camera.AcquisitionFrameRateEnable.SetValue(True)
        camera.AcquisitionFrameRate.SetValue(FrameRate)

        # grabone frame to get shape and pixelfromat
        resolution = (0,0)
        grabResult = camera.GrabOne(10000)
        if grabResult.GrabSucceeded():
            pt = grabResult.GetPixelType()
            if pylon.IsPacked(pt):
                _, new_pt = grabResult._Unpack10or12BitPacked()
                resolution, dtype, pixelformat = grabResult.GetImageFormat(new_pt)
            else:
                resolution, dtype, pixelformat = grabResult.GetImageFormat(pt)
                _ = grabResult.GetImageBuffer()

        else:
            print("grab Failed")
            exit()

        print("resolution : ", f"{resolution}")
        print("Format : ", camera.PixelFormat.GetValue())

        # check for binning rate
        if camera.Width.GetValue() / 1000 > 1 or camera.Height.GetValue() / 1000 > 1:
            print("Binning mode")
            rat = int(max(camera.Height.GetValue() / 1000, camera.Width.GetValue() / 1000))

            if sf_bin:
                shape = (resolution[0]//rat, resolution[1]//rat)
                print(f"software binning (cv2.resize). The new shape = {shape}")

            if not sf_bin:
                camera.BinningVerticalMode.SetValue("Average")
                camera.BinningHorizontalMode.SetValue("Average")
                camera.BinningVertical.SetValue(rat)
                camera.BinningHorizontal.SetValue(rat)
                shape = (camera.Width.GetValue(), camera.Height.GetValue())
                print(f"hardware binning rate = {rat} and new shape = {shape}")



        form[0] = (shape[1], shape[0])
        form[1] = dtype
        counter = FrameRate * secs

        s = 0
        print(f"starting recording {secs} secs with {FrameRate}fps at path:", savepath)

        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        start = time.time()
        with Pool(2) as pool:

            while camera.IsGrabbing():
                grabResult = camera.RetrieveResult(6000, pylon.TimeoutHandling_ThrowException)

                counter = counter - 1
                if grabResult.GrabSucceeded():
                    buff = grabResult.GetBuffer()
                    if sf_bin:
                        img = np.ndarray(resolution, dtype=dtype, buffer=buff)
                        img = cv2.resize(img, (shape[1], shape[0]))
                        buff = img.tobytes()
                    cam_q.put_nowait(buff)
                    s += 1

                grabResult.Release()

                if counter == 0:
                    print(f"stop recording {s} frames in time :", time.time() - start)
                    is_running.value = False
                    break

            # Releasing the resource
            camera.StopGrabbing()

            # if using hardware binning, turn back.
            if not sf_bin:
                camera.BinningVertical.SetValue(1)
                camera.BinningHorizontal.SetValue(1)

            camera.Close()
            cam_q.close()

        print("END")
        return

def showImg(cam_q:Queue, is_running: Value, form: list, **kwargs) -> None:
    mode = kwargs.get('mode', "pass")
    display = kwargs.get('display', 1)
    pgFps = kwargs.get('pgFps', 60)
    cM = kwargs.get('cM', np.identity(2))
    bias = kwargs.get('bias', np.zeros(2))
    is_calibrate = kwargs.get('calibrate', True if mode == 'inter' else False)
    full = kwargs.get("full", False)
    saving = kwargs.get("saving", Value(c_bool, False))
    pasue = False

    if form[0] is None:
        for s in range(10):
            time.sleep(0.1)
            if form[0] is not None:
                break
            if s == 9:
                print("showing error : no camera is open")
                exit()
    shape, dtype = form[0:2]
    tran = list(range(len(shape)))
    tran[0] = 1
    tran[1] = 0

    pygame.init()
    bg = cv2.bgsegm.createBackgroundSubtractorMOG(history=300, nmixtures=4, backgroundRatio=0.1)

    pygame.display.set_caption("OpenCV camera stream on Pygame")
    pgClock = pygame.time.Clock()
    init_size = [600, 600]
    flags = 0  # | pygame.DOUBLEBUF   # | pygame.SCALED #pygame.HWSURFACE | pygame.FULLSCREEN pygame.RESIZABLE ||
    # pygame.HWSURFACE | pygame.DOUBLEBUF
    if full:
        flags = flags | pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.SHOWN
        init_size = [0, 0]
    screen = pygame.display.set_mode(init_size, display=display, flags=flags)
    screen.fill([150, 150, 150])
    sc_shape = np.array(pygame.display.get_window_size())

    while is_running.value:

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    is_running.value = False
                if event.key == pygame.K_SPACE:
                    pasue = not pasue
                    if pasue:
                        mode = 'debug'
                    else:
                        mode = kwargs.get('mode', "pass")
                if event.key == pygame.K_s:
                    saving.value = not saving.value
        rects = [screen.fill([150, 150, 150])]

        try:
            buf = cam_q.get(True, 0.01)
        except queue.Empty as e:
            continue
        img = np.ndarray(dtype=dtype, shape=shape, buffer=buf)
        if not mode == 'debug':
            img = bg.apply(img)
        kernel = np.array([[0,1,0],
                           [1,1,1],
                           [0,1,0]]).astype(np.uint8)*10
        img = cv2.erode(img, kernel, iterations=1)
        img = cv2.dilate(img, kernel, iterations=1)
        back = np.full(shape, 120, dtype='uint8')
        back[:, :, 1] += img//2
        back = np.rot90(back)
        frame = pygame.surfarray.make_surface(back)
        #frame = pygame.transform.scale(frame, tuple(sc_shape))
        rects.append(screen.blit(frame, (0, 0)))

        pgClock.tick(pgFps)
        pygame.display.update(rects)


if __name__ == "__main__":
    cam_q = Queue()  # the Queue for camera img
    is_Running = Value(c_bool, True)
    saving = Value(c_bool, False)

    man = Manager()
    form = man.list([None, None])
    camera = Process(args=(cam_q, is_Running, form, ), target=grabCam,
                     kwargs={'mode': "camera", "c_num": 0, "secs": 100, "saving": saving})
    windows = Process(target=showImg, args=(cam_q, is_Running, form,),
                      kwargs={'mode': "traj", 'calibrate': False, "full": False, "saving": saving})

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