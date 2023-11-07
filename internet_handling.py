from ping3 import ping
import time
import os
import requests
import json
import io
with open("telegram_key.txt") as f:
    token = f.readline()
base_url = "https://api.telegram.org/bot{}/sendPhoto?parse".format(token)


def check_internet():
    return ping("api.telegram.org", timeout=1)

def main():
    cwd = os.getcwd()
    cache_dir = os.path.join(cwd, "cache")
    while True:            
        list_cache = os.listdir(cache_dir)
        if check_internet() and len(list_cache) >= 1:
            for item in list_cache:
                if item.endswith(".jpeg"):
                    continue
                file_path = os.path.join(cache_dir, item)
                try:
                    with open(file_path, "r+") as f:
                        print("opened {}".format(item))
                        data = json.load(f)
                        image = io.BytesIO()
                        with open(data["img_path"], "rb") as img_f:
                            image.write(img_f.read())
                        image.seek(0)
                        files = {}
                        files["photo"] = image
                        parameter = {}
                        parameter["chat_id"] =  "-1001974152494"
                        parameter["parse_mode"] = "Markdown"
                        parameter["caption"] = "{}\nLocation: CAM-{}\n---------------------\n_this is a cached picture_".format(data["cache_time"], data["cam_id"])
                        resp = requests.post(base_url, params=parameter, files=files, timeout=3)
                    if resp.status_code == 200:
                        print("sent {}".format(item))
                        os.remove(data["img_path"])
                        os.remove(file_path)
                except:
                    print("except trigger")
                    continue
            print("after foreach")     
            time.sleep(10.0)
        else:
            print("no internet or no more data")
            time.sleep(5.0)

if __name__ == "__main__":
    main()