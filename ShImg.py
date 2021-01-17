from skimage.measure import label
from skimage.measure import regionprops
import pygame
import cv2
import numpy as np
import time
from multiprocessing import Value, Queue
from ctypes import c_bool
import queue


# def showImg(cam_q, is_Running, mode="pass", display=0, pgFps=90, imgformat=None,  cM=np.identity(2), bias=np.zeros(
# (2))):
def showImg(cam_q:Queue, is_running: Value, form: list, **kwargs) -> None:
    # parameter
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

    # init
    pygame.init()
    bg = cv2.bgsegm.createBackgroundSubtractorMOG(history=300, nmixtures=4, backgroundRatio=0.1)
    # bg = cv2.bgsegm.createBackgroundSubtractorCNT()
    # bg = cv2.bgsegm.createBackgroundSubtractorGMG()
    # bg = cv2.bgsegm.createBackgroundSubtractorGSOC()

    # pygame config
    pygame.display.set_caption("OpenCV camera stream on Pygame")
    pgClock = pygame.time.Clock()
    init_size = [2000, 2000]
    flags = 0  # | pygame.DOUBLEBUF   # | pygame.SCALED #pygame.HWSURFACE | pygame.FULLSCREEN pygame.RESIZABLE ||
    # pygame.HWSURFACE | pygame.DOUBLEBUF
    if full:
        flags = flags | pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.SHOWN
        init_size = [0, 0]
    screen = pygame.display.set_mode(init_size, display=display, flags=flags)
    screen.fill([150, 150, 150])
    sc_shape = np.array(pygame.display.get_window_size())

    # calibration setting
    test_time = 1
    Height, Width = sc_shape[0:2]
    points_num = 0
    ts_radius = min(Height, Width) * 0.05
    label_points = np.array(
        [(ts_radius, ts_radius), (Height - ts_radius, ts_radius), (ts_radius, Width - ts_radius),
         (Height - ts_radius, Width - ts_radius)])
    X = np.array([label_points[0] - label_points[3],
                  label_points[1] - label_points[2]]).T
    mapping_points = []
    calibrate_start = time.time()
    poses = []
    bg_stable = False
    background = np.zeros(shape)
    b_num = 1

    # try to load the Cm and bias
    if not is_calibrate:
        try:
            cM = np.load(f"cM_{sc_shape}.npy")
            bias = np.load(f"bias_{sc_shape}.npy")
        except:
            cM = np.identity(2)
            bias = np.zeros(2)

    # other init:
    im_pos = (shape[0] / 2, shape[1] / 2)
    rf_config = [0, 0]
    rf_state = dict({"center": np.array(sc_shape) // 2, 'damp': 0.5, 'pos': np.array(sc_shape) // 2})

    # traj init
    if mode == 'traj':
        traj_q = queue.Queue()
        traj = np.load("0111_trj.npy")
        for pos in traj:
            traj_q.put(pos)

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
        img = np.ndarray(shape, dtype=dtype, buffer=buf)
        # img = np.transpose(img, tran)

        if is_calibrate:
            bg.apply(img)
            if not bg_stable:  # waiting for background
                background += img
                b_num += 1
                if time.time() - calibrate_start > 5:
                    background = (background / b_num).astype(np.uint8)
                    bg_stable = True
                    calibrate_start = time.time()
            else:
                if time.time() - calibrate_start > test_time:  # record the poses
                    points_num += 1
                    mapping_points.append(np.average(poses, axis=0))
                    poses = []
                    calibrate_start = time.time()

                elif time.time() - calibrate_start > 0.2 * test_time:
                    img = cv2.absdiff(background, img)
                    img = np.where(img > np.std(img) * 3, 255, 0).astype('uint8')
                    poses.append(label_pos(img))

                if points_num == len(label_points):
                    is_calibrate = False
                    C = np.array([mapping_points[0] - mapping_points[3],
                                  mapping_points[1] - mapping_points[2]]).T
                    cM = np.dot(X, np.linalg.inv(C))
                    bias = np.array(label_points[0]) - np.dot(cM, mapping_points[0])

                    np.save(f"cM_{sc_shape}.npy", cM)
                    np.save(f"bias_{sc_shape}.npy", bias)
                else:
                    label_point = label_points[points_num]
                    rects.append(pygame.draw.circle(screen, (0, 0, 0), label_point, ts_radius))

        elif mode == "pass" or mode == 'debug':
            img = np.transpose(img, tran)[::-1, ::-1, ...]
            if mode == "debug":
                img = bg.apply(img)

            if img.ndim < 3:
                img = np.broadcast_to(img[:, :, np.newaxis], (img.shape[0], img.shape[1], 3))
            if img.shape[2] == 1:
                img = np.broadcast_to(img, (img.shape[0], img.shape[1], 3))
            frame = pygame.image.frombuffer(img.tobytes(), shape[0:2], 'RGB')
            frame = pygame.transform.scale(frame, tuple(sc_shape))
            rects.append(screen.blit(frame, (0, 0)))

        elif mode == "inter":
            img = bg.apply(img)
            im_pos = np.array(label_pos(img, pos=im_pos))
            fr_pos = np.dot(cM, im_pos) + bias
            inter_fr_pos = fr_pos
            inter_fr_pos = robot_fish(fr_pos, rf_state, rf_config)
            inter_fr_pos = np.ceil(inter_fr_pos)
            rects.append(pygame.draw.circle(screen, (30, 100, 10), inter_fr_pos, 30))

        elif mode == "traj":
            pos = traj_q.get()
            pos = (pos[0]*sc_shape[0], pos[1]*sc_shape[1])
            rects.append(pygame.draw.circle(screen, (30, 100, 10), pos, 30))

        if saving.value:
            rects.append(pygame.draw.circle(screen, (255, 0, 0), (ts_radius, ts_radius), ts_radius * 0.3))
        pgClock.tick(pgFps)
        pygame.display.update(rects)

    pygame.quit()


def label_pos(img, **kwargs):
    labels = label(img, connectivity=2, background=0)
    group = regionprops(labels, cache=True)
    area = kwargs.get('area', img.shape[0] * img.shape[1] * 0.00001)
    pos = kwargs.get('pos', (0, 0))
    for com in group:
        if com.area > area:
            area = com.area
            pos = com.centroid
    return pos


def robot_fish(mate_pos, state: dict, config: list):
    v = state.get('speed', np.array([0, 0]))
    pos = state.get('pos', np.array([0, 0]))
    cen = state.get('center', np.array([100, 100]))
    damp = state.get('damp', 0.2)

    a = config[0] * (mate_pos - pos) + config[1] * (cen - pos) + np.random.normal(0, 200, size=2) - v * damp
    v = v + a * 0.033
    pos = pos + v * 0.033

    state['pos'] = pos
    state['speed'] = v

    return pos
