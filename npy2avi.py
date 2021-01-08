import os
import cv2
import time
import numpy as np

def npy2avi(path, savepath=""):
    flist = os.listdir(path)
    tiflist = []
    for filename in flist:
        if os.path.isdir(filename):
            continue
        if filename.split(".")[-1] == "npy" and filename.find("frame") >= 0:
            tiflist.append(filename)

    print('There is a total of ', len(tiflist), 'images')
    frame_num = len(tiflist)
    # for srt in os.listdir(path):
    # flist.append(srt.split('_'))

    # 排序路徑
    tiflist.sort(key=lambda x: int(x.split("_")[-1].split(".")[0]))

    # 變成絕對路徑
    flist = []
    for filename in tiflist:
        flist.append(os.path.join(path, filename))
    img = np.load(filename)
    size = (img.shape[1], img.shape[0])
    video = cv2.VideoWriter(os.path.join(savepath, "video.avi"), cv2.VideoWriter_fourcc(*'MPEG'),
                            30, size, isColor=False)

    start = time.time()
    num = 0

    for filename in flist:
        num += 1
        if (num % 100 == 0):
            print(num)
        img = np.load(filename)
        video.write(img)

    print(time.time() - start)
    video.release()

    print("end")