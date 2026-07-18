"""
Timelapse capture script for Raspberry Pi.

Polls an ESP32 camera server for JPEG captures, keeps total storage under
a fixed bit budget (allotted_space), and thins out older photos (removing
every other one) once the budget is full, adjusting the capture interval
based on the new average spacing between remaining photos.

Request:
give me a python script to run in vscode on a raspberry pi with an integer 
variable allotted_space designating free bits that gets the 
time, then sends a capture request, waits until it gets the full jpeg back 
from the esp32, prints the size of the file in bits, and checks if 
total_bits_used + the image size < allotted space.
If so, the code should add it to a timelapse folder as image1.jpeg
(or whatever naming scheme you determine best), then add the name
of the file as well as its size in bits and time taken to photo_array, 
add its size to total_bits_used, and wait until the time is more than 
capture_wait_time (float) seconds past the time the photo was taken before 
sending another capture request. Otherwise, it should check if the number of 
images in photo_array > 1, and if so, find every even numbered photo 
(the photos at indexes 1, 3, 5, etc. with 0 as the first index) and 
delete them from the folder before adding the new photo to the folder 
and setting capture_wait_time to the new average time between when each 
photo was taken. If the number of images in photo_array is 1 or 0, print 
"There isn't enough allotted space to make a timelapse" and stop the program.
"""

import requests
import time
import os

# ============================================================
# Configuration
# ============================================================
ESP32_IP = "192.168.5.152"          # <-- set to your ESP32's IP
CAPTURE_URL = f"http://{ESP32_IP}/capture"
OUTPUT_DIR = "me/knotsobad/Documents/timelapse-camera/timelapse1"    # folder where images are stored

allotted_space = 50_000_000          # total budget, in BITS
capture_wait_time = 5.0              # seconds between captures (float, adjustable)
REQUEST_TIMEOUT = 10                 # seconds to wait for ESP32 response

# ============================================================
# State
# ============================================================
total_bits_used = 0
photo_array = []       # list of dicts: {"name": str, "size_bits": int, "time": float}
photo_counter = 0       # ever-increasing counter used for unique filenames

os.makedirs(OUTPUT_DIR, exist_ok=True)


def take_capture():
    """
    Sends a capture request to the ESP32 and blocks until the full JPEG
    is received. Returns (jpeg_bytes, capture_time) or (None, None) on failure.
    """
    capture_time = time.time()
    try:
        response = requests.get(CAPTURE_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        # .content already blocks until the full body has been received
        return response.content, capture_time
    except requests.exceptions.RequestException as e:
        print(f"Capture request failed: {e}")
        return None, None


def save_photo(jpeg_bytes, capture_time):
    """Writes the JPEG to disk and returns (filename, size_bits)."""
    global photo_counter
    photo_counter += 1
    filename = f"image{photo_counter}.jpg"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(jpeg_bytes)

    size_bits = len(jpeg_bytes) * 8
    return filename, size_bits


def delete_photo(entry):
    """Removes a photo's file from disk given its photo_array entry."""
    filepath = os.path.join(OUTPUT_DIR, entry["name"])
    try:
        os.remove(filepath)
    except FileNotFoundError:
        pass


def thin_out_photos():
    """
    Removes every even-numbered photo (indexes 1, 3, 5, ... i.e. the
    2nd, 4th, 6th... photos taken) from disk and from photo_array.
    Returns the new (thinned) photo_array.
    """
    global total_bits_used

    kept = []
    for i, entry in enumerate(photo_array):
        if i % 2 == 1:
            # even-numbered photo (odd index) -> delete
            delete_photo(entry)
            total_bits_used -= entry["size_bits"]
        else:
            kept.append(entry)

    return kept


def recompute_capture_wait_time(photos):
    """
    Recomputes capture_wait_time as the average time gap between
    consecutive photos in the given list, ordered by capture time.
    """
    if len(photos) < 2:
        return capture_wait_time  # not enough data, leave unchanged

    times = sorted(p["time"] for p in photos)
    gaps = [t2 - t1 for t1, t2 in zip(times, times[1:])]
    return sum(gaps) / len(gaps)


def main():
    global total_bits_used, capture_wait_time, photo_array

    print(f"Starting timelapse capture. Budget: {allotted_space} bits")

    while True:
        jpeg_bytes, capture_time = take_capture()

        if jpeg_bytes is None:
            # Request failed; wait a moment and try again
            time.sleep(1)
            continue

        size_bits = len(jpeg_bytes) * 8
        print(f"Captured image: {size_bits} bits ({size_bits / 8} bytes)")

        if total_bits_used + size_bits < allotted_space:
            # Enough room -- keep the photo
            filename, size_bits = save_photo(jpeg_bytes, capture_time)
            photo_array.append({
                "name": filename,
                "size_bits": size_bits,
                "time": capture_time
            })
            total_bits_used += size_bits
            print(f"Saved {filename} ({size_bits} bits). "
                  f"Total used: {total_bits_used}/{allotted_space} bits")

        else:
            # Not enough room -- try thinning out older photos
            if len(photo_array) > 1:
                photo_array = thin_out_photos()

                # Add the new photo now that space has been freed
                filename, size_bits = save_photo(jpeg_bytes, capture_time)
                photo_array.append({
                    "name": filename,
                    "size_bits": size_bits,
                    "time": capture_time
                })
                total_bits_used += size_bits

                capture_wait_time = recompute_capture_wait_time(photo_array)

                print(f"Thinned photo set. New photo count: {len(photo_array)}. "
                      f"New capture_wait_time: {capture_wait_time:.2f}s. "
                      f"Total used: {total_bits_used}/{allotted_space} bits")
            else:
                print("There isn't enough allotted space to make a timelapse")
                return

        # Wait until capture_wait_time seconds have passed since this photo
        elapsed = time.time() - capture_time
        remaining = capture_wait_time - elapsed
        if remaining > 0:
            time.sleep(remaining)


if __name__ == "__main__":
    main()