"""
Timelapse capturing script for Raspberry Pi.

Uses HTTP requests to collect JPEG photos from a web server hosted via ESP32-cam on the RPi's hotspot.
Collects and curates images for a timelapse ready to be displayed using timelapse_display.py.
Provides and requires user input to set up desired timelapse settings, including allocated disk space, ESP32 ip,
output directory, wait time between pictures

The available timelapse modes are:
    halt - stops when storage limit is reached
    loop - removes the earliest images to clear disk space for incoming images
    
"""

# ===================
#       Imports
# ===================
import requests
import time
import os
import shutil

"""
    TODO:
 - Account for response delay in request delay (can be done after each capture, maybe while waiting for response?)
"""

# ===================
#    Configuration
# ===================
ESP32_IP = "10.42.0.247"
CAPTURE_URL = f"http://{ESP32_IP}/capture"                                         # TODO
OUTPUT_DIR = os.path.expanduser("~/Documents/timelapse-camera/")    # folder where images are stored

allocated_space = 5_000_000     # total bytes the program is allowed to use
capture_wait_time = 0.5         # seconds between captures (float, adjustable)
REQUEST_TIMEOUT = 30            # seconds to wait for ESP32 response
OVERFLOW_HANDLING = "thin"      # when out of space, either stops (halt), clears half (thin), or removes first (loop)

# ===================
#        State
# ===================
total_bytes_used = 0
photo_counter = 1       # incremental file name counter
photo_array = []       # list of dicts: {"name": str, "size_bytes": int, "time": float, "capture_delay": float}

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ===================
#      Functions
# ===================

# TODO FIXME!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
def valid_details(text):
    return True


def save_details():
    global ESP32_IP, CAPTURE_URL, OUTPUT_DIR, allocated_space, capture_wait_time, REQUEST_TIMEOUT, OVERFLOW_HANDLING, total_bytes_used, photo_array, photo_counter
    
    with open(os.path.join(OUTPUT_DIR,"details.txt"),"w") as w:
        w.write(f"ESP32_IP = {ESP32_IP}\n")
        w.write(f"OUTPUT_DIR = {OUTPUT_DIR}\n\n")

        w.write(f"allocated_space = {allocated_space}\n")
        w.write(f"capture_wait_time = {capture_wait_time}\n")
        w.write(f"REQUEST_TIMEOUT = {REQUEST_TIMEOUT}\n")
        w.write(f"OVERFLOW_HANDLING (timelapse mode) = {OVERFLOW_HANDLING}\n\n")

        w.write(f"photo_counter = {photo_counter}\n\n")

        w.write("Photo array:\n")

        written_photo_array = []
        for photo_dict in photo_array:
            
            # written_photo_array is a list so I can use .join() on it
            written_photo_array.append(','.join([photo_dict.get("name"),
                                        str(photo_dict.get("size_bytes")),
                                        str(photo_dict.get("time")),
                                        str(photo_dict.get("capture_delay"))]))

        w.write(";".join(written_photo_array))


def setup_timelapse(foldername):
    """Gathers all the info needed to start a timelapse (or continue an existing timelapse)

    Args: 
        foldername (String): string after "timelapse" in folder name (timelapse_)
    """

    global ESP32_IP, CAPTURE_URL, OUTPUT_DIR, allocated_space, capture_wait_time, REQUEST_TIMEOUT, OVERFLOW_HANDLING, total_bytes_used, photo_array, photo_counter
    
    # loops until setup is complete through loading existing timelapse or creating a new one
    while True:
        if foldername == "":
            # goes back to folder selection if the user lists an existing folder
            print("\nWhat do you want to save your timelapse as?")
            foldername = "timelapse" + input("timelapse")

            # try to create a new folder using foldername
            # if name alr taken, check if the folder has a details.txt file
            try: 
                os.makedirs(os.path.join(OUTPUT_DIR,foldername), exist_ok=False)
            except OSError:
                # TODO: check if valid 
                if len(os.listdir(os.path.join(OUTPUT_DIR,foldername))) == 0:
                    pass
                else:
                    print(f"items in specified folder: {os.listdir(os.path.join(OUTPUT_DIR,foldername))}")
                    print("Folder name taken, try again")
                    foldername = ""

            # get the user's settings preferences
            user_uncertain = True
            while user_uncertain:
                while True:
                    print(f"Bytes: {shutil.disk_usage("/")}")
                    u = input("allocated_space (bytes, 100_000 default): ")
                    if u == "":
                        break
                    else: 
                        try:
                            allocated_space = int(u)
                            break
                        except ValueError:
                            "Your answer must be an int or empty"
                while True:
                    u = input("capture_wait_time (seconds, 2 default): ")
                    if u == "":
                        break
                    else: 
                        try:
                            allocated_space = float(u)
                            break
                        except ValueError:
                            "Your answer must be a float or empty"
                while True:
                    u = input("REQUEST_TIMEOUT (seconds, 20 default): ")
                    if u == "":
                        break
                    else: 
                        try:
                            allocated_space = float(u)
                            break
                        except ValueError:
                            "Your answer must be a float or empty"
                            REQUEST_TIMEOUT = float(input(""))
                    break
                new_esp32_ip = input("ESP32_IP (enter nothing for default ip): ")
                if new_esp32_ip != "":
                    ESP32_IP = new_esp32_ip
                    CAPTURE_URL = f"http://{ESP32_IP}/capture"
                while True:
                    print("What should the program do when it runs out of space?")
                    OVERFLOW_HANDLING = input("Options: end the program ('halt'), clear half ('thin', DEFAULT), or remove the first photo ('loop'): ").lower()
                    if OVERFLOW_HANDLING in ("halt","thin","loop"):
                        break
                    elif OVERFLOW_HANDLING == "":
                        OVERFLOW_HANDLING = "thin"
                        break
                    else:
                        print("I don't recognize that option. Your answer isn't case sensitive here, but it should exactly match one of the choices.")

                # confirm settings
                print(f"Allocated space: {allocated_space} bytes")
                print(f"Initial time between capture requests: {capture_wait_time} sec")
                print(f"Request timeout time: {REQUEST_TIMEOUT} sec")
                print(f"ESP32 IP: {ESP32_IP}")
                print(f"Timelapse mode: {OVERFLOW_HANDLING}")
                
                while True:
                    user_certainty = input("Do those settings look right? (y/n)").lower()
                    if user_certainty == "y":
                        user_uncertain = False
                        return
                    elif user_certainty == "n":
                        user_uncertain = True   # doesn't change the variable
                        break
        else:
            
            with open(os.path.join(OUTPUT_DIR,foldername,"details.txt")) as r:
                details = r.read().split("\n")

            ESP32_IP = details[0].split(" = ")[1]
            CAPTURE_URL = f"http://{ESP32_IP}/capture"
            OUTPUT_DIR = os.path.expanduser(details[1].split(" = ")[1])
            
            allocated_space = int(details[3].split(" = ")[1])
            capture_wait_time = float(details[4].split(" = ")[1])
            REQUEST_TIMEOUT = float(details[5].split(" = ")[1])
            OVERFLOW_HANDLING = details[6].split(" = ")[1]

            photo_counter = int(details[8].split(" = ")[1])

            # separate different photos
            photo_list = details[11].split(";")
            for photo in photo_list:
                if photo == "":
                    continue

                # separate photo details
                photo = photo.split(",")
                photo_dict = {
                "name": photo[0],
                "size_bytes": int(photo[1]),
                "time": float(photo[2]),
                "capture_delay": float(photo[3])
                }
                photo_array.append(photo_dict)
                total_bytes_used += photo_dict.get("size_bytes")
            
            # leave setup
            return
            


def select_timelapse():
    """
    Prompts user to either choose an existing timelapse or create a new timelapse, then redirects to setup_timelapse to create timelapse
    """
    # check each item in directory to find all timelapses with valid details.txt files
    dir_list = os.listdir(OUTPUT_DIR)
    valid_list = []
    for item in dir_list:
        try:
            with open(os.path.join(OUTPUT_DIR,item,"details.txt")) as reader:
                if valid_details(reader.read()):
                    valid_list.append(item)
                continue

        except (FileNotFoundError, NotADirectoryError):
            continue

    # print timelapse options
    if len(valid_list) < 1:
        print("Creating new timelapse")
        setup_timelapse("")
    else:
        print("Valid loadable timelapses (with a valid details.txt file):")
        for item in valid_list: print(item) 
        print("Type one of the options above to load a timelapse or type nothing to create a new timelapse, then hit ENTER. ")
        setup_timelapse(input(""))


def take_capture():
    """Sends /capture http request to ESP32 halts program until the full JPEG is received
    
    Return:
        (jpeg_bytes, capture_time, delay_time) on success
        (None, None, None) on failure
    """
    request_time = time.time()
    print("Sending capture request...")
    try:
        response = requests.get(CAPTURE_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        capture_time = time.time()
        print(f"Response took {capture_time - request_time:.4f} seconds.")
 
        # .content already blocks until the full body has been received
        return response.content, capture_time, capture_time - request_time
    
    except requests.exceptions.RequestException as e:
        print(f"Capture request failed: {e}")
        print(f"Error flagged after {time.time() - request_time:.4f} seconds.")
 
        return None, None, None


def save_photo(jpeg_bytes, capture_time):
    """
    Writes the JPEG to disk and returns (filename, size_bytes)
    """
    global photo_counter
    filename = f"image{photo_counter}.jpg"
    filepath = os.path.join(OUTPUT_DIR, filename)
    photo_counter += 1
 
    # Save image to image#.jpg
    with open(filepath, "wb") as f:
        f.write(jpeg_bytes)
 
    size_bytes = len(jpeg_bytes)
    return filename, size_bytes


def delete_photo(photo):
    """Removes a photo's file from disk given its photo_array entry.

    Args:
        photo (dict with key "name" -> filename)

    """
    filepath = os.path.join(OUTPUT_DIR, photo["name"])
    try:
        os.remove(filepath)
    except FileNotFoundError:
        pass


def thin_out_photos():
    """Removes every other photo (odd # indexes) from the disk and from photo_array.

    Return:
        list of dicts: every even # index from photo_array.
    """
    global total_bytes_used

    kept_photos = []

    # keep every other photo
    for i, photo in zip(range(len(photo_array)),photo_array):
        if i % 2 == 1:
            delete_photo(photo)
            total_bytes_used -= photo["size_bytes"]
        else:
            kept_photos.append(photo)

    return kept_photos


def recompute_capture_wait_time(photos):
    """Recomputes capture_wait_time as the average time gap between
    consecutive photos in the given list, ordered by capture time.

    Args:
        photos (list of dicts including key "time"): details for every saved image
    
    Return:
        int: average time between photos
    """

    if len(photos) < 2:
        return capture_wait_time  # not enough data, leave unchanged
 
    times = sorted(p["time"] for p in photos)
 
    # goes through pairs of times in "times"
    # aka gaps = [t2 - t1 for t1, t2 in zip(times,times[1:])]
    gaps = []
    for t1, t2 in zip(times,times[1:]):
        gaps.append(t2 - t1)
    
    return sum(gaps) / len(gaps)


# =======================
#        Main Loop
# =======================

def main():
    global total_bytes_used, capture_wait_time, photo_array
    
    # user prompts on launch
    select_timelapse()

    print(f"Starting timelapse capture. Budget: {allocated_space} bytes")

    # burn 1 "capture" to avoid lingering http requests
    print("Burning 1st request...")
    take_capture()

    while True:
        # request picture
        jpeg_bytes, capture_time, capture_delay = take_capture()

        if jpeg_bytes is None:
            # Request failed; wait a moment and try again
            time.sleep(1)
            continue

        size_bytes = len(jpeg_bytes)
        print(f"Captured image: {size_bytes} bytes")

        # checks if there is enough room to add the photo
        if total_bytes_used + size_bytes <= allocated_space:
          
            # save photo to folder with all obtained attributes
            filename, size_bytes = save_photo(jpeg_bytes, capture_time)
            photo_array.append({
                "name": filename,
                "size_bytes": size_bytes,
                "time": capture_time, 
                "capture_delay": capture_delay
            })

            total_bytes_used += size_bytes
            print(f"Saved {filename} ({size_bytes} bytes). "
                  f"Total used: {total_bytes_used}/{allocated_space} bytes")

        # insufficient space for next photo
        else:
            
            # save and stop program
            if OVERFLOW_HANDLING == "halt":
                print("Allocated space reached. Timelapse mode: halt")
                print("Saving details...")
                save_details()
                print("Saved. Stopping program...")
                break
            

            # clear necessary images from the start, add next image, then continue program
            elif OVERFLOW_HANDLING == "loop":
                # loop until there is space for the next capture, up to 3 times
                images_removed = 0 
                while total_bytes_used + size_bytes > allocated_space and images_removed < 3:
                    print("Allocated space insufficient. Timelapse mode: loop")
                    
                    print("Deleting earliest image...")
                    delete_photo(photo_array[0])
                    total_bytes_used -= photo_array[0]["size_bytes"]
                    photo_array.pop(0)
                    print("Image deleted.")
                    images_removed += 1

                    jpeg_bytes = None
                    while jpeg_bytes is None:
                        print("Taking new photo")
                        jpeg_bytes, capture_time, capture_delay = take_capture()
                        size_bytes = len(jpeg_bytes)
                        print(f"Captured new image: {size_bytes} bytes")

                if images_removed < 3:
                    filename, size_bytes = save_photo(jpeg_bytes, capture_time)
                    photo_array.append({
                        "name": filename,
                        "size_bytes": size_bytes,
                        "time": capture_time,
                        "capture_delay": capture_delay
                    })
                    total_bytes_used += size_bytes

                    save_details()
                else:
                    print("Something went wrong, unable to add a new image (without deleting an unreasonable number of existing photos)")


            # default option to thin every other existing image
            # clear half of the images, add the next image that matches the new time spacing, then continue program
            elif OVERFLOW_HANDLING == "thin":
                # loop until there is space for the next image
                while total_bytes_used + size_bytes > allocated_space:
                    print("Allocated space insufficient. Timelapse mode: thin")
                    print("Thanos snapping photos...")
                    if len(photo_array) > 1:
                        photo_array = thin_out_photos()
                    else:
                        print("There isn't enough allocated space to make a timelapse based on the most recent photo received! Gadzooks!")
                        return

                # Check if new photo matches new capture wait time
                if capture_time > photo_array[-1].get("time") + (0.9 * recompute_capture_wait_time(photo_array)):
                    capture_wait_time = recompute_capture_wait_time(photo_array)
                    
                    filename, size_bytes = save_photo(jpeg_bytes, capture_time)
                    photo_array.append({
                        "name": filename,
                        "size_bytes": size_bytes,
                        "time": capture_time,
                        "capture_delay": capture_delay
                    })
                    total_bytes_used += size_bytes

                # Wait until old capture wait time has elapsed again, then take new photo and update wait time
                else:
                    elapsed = time.time() - capture_time
                    remaining = capture_wait_time - elapsed
                    if remaining > 0:
                        time.sleep(remaining)

                    # NOW update new capture wait time
                    capture_wait_time = recompute_capture_wait_time(photo_array)

            
                print(f"Halved existing frames. New photo count: {len(photo_array)}. "
                    f"New capture wait time: {capture_wait_time:.2f}s. "
                    f"Total space used: {total_bytes_used}/{allocated_space} bytes")
                
                save_details()


        # Wait until capture_wait_time seconds have passed since this photo
        elapsed = time.time() - capture_time
        remaining = capture_wait_time - elapsed
        if remaining > 0:
            time.sleep(remaining)


# ======================
#        Run Code
# ======================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("KeyboardInterrupt detected. Stopping program...")
        print("Saving current settings to details.txt, you have 3 seconds to cancel the saving process")
        time.sleep(3)
        save_details()
        print("Settings saved")