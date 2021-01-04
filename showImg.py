import time
from skimage.measure import label
from skimage.measure import regionprops
import pygame
import cv2
import numpy as np


def showImg(cam_q, is_Running, mode="pass", cM=np.identity(2), b=np.zeros((2))):
    # parameter
    pgFps = 90
    shape, dtype = cam_q.recv()
    tran = list(range(len(shape)))
    tran[0] = 1
    tran[1]=0

    # init
    pygame.init()
    bg = cv2.bgsegm.createBackgroundSubtractorMOG(history=300, nmixtures=10, backgroundRatio=0.05)
    # bg = cv2.bgsegm.createBackgroundSubtractorCNT()
    # bg = cv2.bgsegm.createBackgroundSubtractorGMG()
    # bg = cv2.bgsegm.createBackgroundSubtractorGSOC()

    # config
    pygame.display.set_caption("OpenCV camera stream on Pygame")
    pgClock = pygame.time.Clock()
    flags = pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE  # | pygame.SCALED #pygame.HWSURFACE | pygame.FULLSCREEN
    screen = pygame.display.set_mode([1000, 1000], display=0, flags=flags)
    scshape = pygame.display.get_window_size()

    while is_Running.value:

        if not cam_q.poll():
            # guarantee that when there is no img in pipe, pygame  still check is_Running
            pass
        else:
            screen.fill([0, 0, 0])
            buf = cam_q.recv_bytes()
            img = np.ndarray(shape, dtype=dtype, buffer=buf)
            img = np.transpose(img,tran)
            

            if mode == "pass":

                if img.ndim < 3:
                    img = np.broadcast_to(img[:, :, np.newaxis], (img.shape[0], img.shape[1], 3))
                if img.shape[2] == 1:
                    img = np.broadcast_to(img, (img.shape[0], img.shape[1], 3))
                frame = pygame.surfarray.make_surface(img)

            elif mode == "debug":
                img = bg.apply(img)

                if img.ndim < 3:
                    img = np.broadcast_to(img[:, :, np.newaxis], (img.shape[0], img.shape[1], 3))
                if img.shape[2] == 1:
                    img = np.broadcast_to(img, (img.shape[0], img.shape[1], 3))
                frame = pygame.surfarray.make_surface(img)

            elif mode == "inter":
                frame = bg.apply(img)
                labels = label(frame, connectivity=2, background=0)
                group = regionprops(labels, cache=True)
                area = 0
                pos = (0, 0)
                for com in group:
                    if com.area > area:
                        area = com.area
                        pos = com.centroid
                pos = (int(pos[0]), int(pos[1]))
                frame = pygame.Surface(shape[0:2])
                pygame.draw.circle(frame, (255, 255, 255), pos, 10)

            frame = pygame.transform.scale(frame, scshape)
            screen.blit(frame, (0, 0))
        pgClock.tick(pgFps)
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                is_Running.value = False

    cam_q.close()
    pygame.quit()
