import requests

url = 'http://192.168.5.218' # Might need to change occasionally

try:
    print("Sending request...")
    # returns a TimeoutError if no bytes are returned by 0.1 sec
    r = requests.get(url+"/capture", timeout=0.1)
    print("Response recieved.")

    print("Parsing response")
    with open("capture.jpg","wb") as writer:
        writer.write(r.content)

except requests.exceptions.ConnectTimeout:
    print("Request timed out.")
