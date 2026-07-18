# Displays the photos taken in timelapse_capture.py by cycling through all the photos in the given folder
import time
import os
import cv2
"""
    TODO:
- add timestamps
"""
# ===================
#    Configuration
# ===================                                                            TODO:
IMAGE_DIR = os.path.expanduser("~/Documents/timelapse-camera/timelapse5")    # image folder
loop_time = 7.5     # in seconds (float)


# ===============
#    Functions
# ===============

def sort_dir(dir):
    """
    Returns an numerically sorted list of items in the given directory path
    """
    item_list = os.listdir(dir)
    # remove non-.jpg items from list
    for item in item_list:
        if item[-4:] != ".jpg":
            item_list.remove(item)
    # sort list numerically
    for i in range(len(item_list)):
        for k in range(len(item_list)-1-i):
            if int(item_list[k][5:-4]) > int(item_list[k+1][5:-4]):
                temp = item_list[k]
                item_list[k] = item_list[k+1]
                item_list[k+1] = temp
      
    return item_list


def display_image(file_name, window_name = "Live Timelapse Display"):
    path = IMAGE_DIR + "/" + file_name
    img = cv2.imread(path)
    cv2.putText(img,file_name,(5,20),0,0.5,(255,0,0))
    cv2.imshow(window_name,img)
    key = cv2.waitKey(1)


# ===============
#    Main Loop
# ===============

def main():
    try:
        i = -1

        while True:
            images = sort_dir(IMAGE_DIR)

            # Display image if there is an image to show
            if len(images) > 0:
            
                if i >= len(images):
                    i = 0
                
                print(f"Displaying: {images[i]}")
                display_image(images[i])

                i += 1

                # wait as needed so the loop matches target time (for a static photo folder)
                time.sleep(loop_time/len(images))
            
            else:
                print("No images found.")
                time.sleep(2)

    except KeyboardInterrupt:
        print("KeyboardInterrupt detected. Stopping program...")
        return

if __name__ == "__main__":
    main()