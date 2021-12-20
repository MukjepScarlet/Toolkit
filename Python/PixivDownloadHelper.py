import json
import re
import time
import requests
import os
import imageio
from zipfile import ZipFile
from selenium import webdriver
from retrying import retry
from bs4 import BeautifulSoup as bs

from concurrent.futures import ThreadPoolExecutor

class PixivGetter():
    def __init__(self, username, password):
        self.browser = webdriver.PhantomJS()
        self.login(username, password)

    def login(self, username, password):
        login_url = "https://accounts.pixiv.net/login"

        self.browser.get(login_url)
        element = self.browser.find_element_by_xpath("// input [@ autocomplete ='username']")
        element.send_keys(username)
        element = self.browser.find_element_by_xpath("// input [@ autocomplete ='current-password']")
        element.send_keys(password)
        element.send_keys('\ue007')#Enter
        element = element.find_element_by_xpath("// button [@ type ='submit']").click
        while self.browser.current_url == login_url:
            time.sleep(0.1)

    def get(self, url):
        self.browser.get(url)
        return self.browser

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.8,en-US,en;q=0.6,ja-JP,ja;q=0.4',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
    'Referer': 'https://www.pixiv.net'#
}

running_tasks = False

GETTER = None

def create_path(path: str):
    os.path.exists(path) or os.mkdir(path)

def get_info(id: "int | str") -> dict[str]:
    """
    ``id``: ID of artwork\n
    """
    url = f"https://www.pixiv.net/artworks/{id}"
    soup = bs(requests.get(url, headers = HEADERS, timeout = 10).text, "lxml")
    main_dict = json.loads(soup.find("meta", attrs = { "id": "meta-preload-data", "name": "preload-data" })["content"])["illust"][str(id)]
    
    page_count = main_dict["pageCount"]

    source = [main_dict["urls"]["original"].replace("p0", "p%d" % page) for page in range(page_count)]

    return {
        "id": main_dict["id"],#int 作品ID
        "title": main_dict["title"],#str 作品标题
        "description": main_dict["description"],#str 作品描述
        "date": main_dict["uploadDate"],#str 作品上传日期
        "source": source,#list[str] 作品图片链接
        "page": page_count,#int 作品页数
        "type": main_dict["illustType"],
        "tags": [it["tag"] for it in main_dict["tags"]["tags"]],#list[str] 标签
        "bookmark": main_dict["bookmarkCount"],#int 收藏数
        "like": main_dict["likeCount"],#int 点赞数
        "view": main_dict["viewCount"],#int 观看次数
        "author": {#作者信息
            "id": main_dict["userId"],
            "name": main_dict["userName"]
        }
    }

@retry()
def download(url: str, path: str):
    try:
        with open(path, 'wb') as pic:
            pic.write(requests.get(url, headers = HEADERS, timeout = 15).content)
    except TimeoutError:
        print(f"Download Timeout! URL: {url}")

MAIN_PATH = "D:/PixivDownload"

#create_path(MAIN_PATH)

def download_illust(id: "int | str"):
    """
    ``id`` ID of illust\n
    GIF/PNG/JPG OK (Download GIF need to log in)
    """

    running_tasks = True

    info = get_info(id)

    print(f"ID: {id}; Title: {info['title']}")
    create_path(author_path := os.path.join(MAIN_PATH, info['author']['id'] + " - " + info['author']['name']))
    create_path(illust_path := os.path.join(author_path, info['id'] + " - " + info['title']))

    start_time = time.time()

    if info["type"] == 0:
        with ThreadPoolExecutor(max_workers = info["page"] if info["page"] < 8 else 8) as executor:
            for i, url in enumerate(info["source"]):
                print(f"Started Downloading page {i}...")
                executor.submit(download, url, os.path.join(illust_path, re.findall(r".+_(p[0-9]\..+)", url)[0]))
        
    elif info["type"] == 2:
        print("INFO: this is a GIF.")

        if not GETTER:
            print("Please log in first.")
            return
        
        file_info = json.loads(GETTER.get(f"https://www.pixiv.net/ajax/illust/{id}/ugoira_meta").find_element_by_tag_name("body").text)["body"]

        zip_url: str = file_info['originalSrc']

        print("Started downloading GIF source file...")
        download(zip_url, zip_path := os.path.join(illust_path, "cache.zip"))
        
        print("Started extracting...")
        temp_file_list = []
        with ZipFile(zip_path) as zip:
            for file in zip.namelist():
                temp_file_list.append(os.path.join(illust_path, file))
                zip.extract(file, illust_path)

        delay = [it["delay"] for it in file_info["frames"]]
        delay = sum(delay) / len(delay)

        print("Start building up GIF file...")
        imageio.mimsave(os.path.join(illust_path, "ugoira.gif"), map(imageio.imread, temp_file_list), "GIF", duration = delay / 1000)

        for file in temp_file_list:
            os.remove(file)
        os.remove(zip_path)

    else:
        raise ValueError("IllegalArgument: Can't check the type of illust.")

    finish_time = time.time()
    print("Download finished. Time: %.1fs\n" % (finish_time - start_time))

    running_tasks = False

    with open(illust_path + "/info.json", mode = "w+", encoding = "utf-8") as f:
        info["download_time"] = time.asctime()
        json.dump(info, f, indent = 4, ensure_ascii = False)

#login
PIXIV_ID = None
PASSWORD = None

GETTER = PixivGetter(PIXIV_ID, PASSWORD)

def get_illust_ids(id: "int | str") -> list[str]:
    """
    ``id`` ID of author/uploader\n
    need login.
    """
    global GETTER
    if not GETTER: GETTER = PixivGetter(PIXIV_ID, PASSWORD)
    return [*json.loads(GETTER.get(f"https://www.pixiv.net/ajax/user/{id}/profile/all").find_element_by_tag_name("body").text)["body"]["illusts"]]

#to write downloads
#plz set main path first.
#e.g.
#download_illust(72637936)


if GETTER: GETTER.browser.close()
