import requests, re, time
from bs4 import BeautifulSoup as bs

from concurrent.futures import ThreadPoolExecutor

# 使用说明
# https://www.ddyueshu.com/ 下载器
# 使用前改好下面的menu_page变量的内容就OK
# TO_REPLACE变量中存储需要去除的字符串(例如各种插入广告)

# 调整线程数目: 推荐设定成CPU核心数*10 例如i5-10400F 设成60线程
# 一般情况下内存不会溢出 除非内容实在太多
# 经过测试 下载<临高启明>(2600+章) TXT大小25MB左右 不会溢出
# 12线程 用时157.1秒
# 60线程 用时72.8秒
# 84线程 用时85.6秒
# 120线程 用时61.7秒
# 2627线程(当时章节数) 用时69.8秒(可能是网站限制) CPU占用约20%(i5-10400F) 内存约220MB

menu_page = "https://www.ddyueshu.com/9_9614/"

TO_REPLACE = [
    "[笔趣看    ]百度搜索“笔趣看”手机阅读\r         。请记住本书首发域名：ddyueshu.com。顶点小说手机版阅读网址：m.ddyueshu.com",
    "请记住本书首发域名：ddyueshu.com。顶点小说手机版阅读网址：m.ddyueshu.com"
]

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.8,en-US,en;q=0.6,ja-JP,ja;q=0.4',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
    'Referer': menu_page
}

def get_date() -> str:
    _tuple = time.localtime(time.time())
    return "%d.%d.%d" % (_tuple[0], _tuple[1], _tuple[2])

def get_book(menu_page: str):
    _get = requests.get(menu_page, headers = HEADERS)
    _get.encoding = "gbk"

    main_box = bs(_get.text, 'lxml').body.find_all("div", class_ = "box_con")[1].div.dl

    return {
        "book_name": re.findall(r"《(.+)》", main_box.dt.b.string)[0],
        "chapter_urls": [dd.a["href"].split("/")[-1][:-5] for dd in main_box.find_all("dd")[6:]]
    }

def get_chapter(url: str):
    _get = requests.get(url, headers = HEADERS)
    _get.encoding = "gbk"
    soup = bs(_get.content, 'lxml')
    main_content = soup.find("div", id = "content").text.replace("\xa0", " ")
    for it in TO_REPLACE:
        main_content = main_content.replace(it, "")

    return {
        "chapter_name": soup.find("div", class_ = "bookname").h1.string.strip(),
        "main_content": main_content
    }

def write_to_text(book_name: str, content_dict: dict):
    with open(get_date() + " " + book_name + ".txt", "w+", encoding = "utf-8") as txt:
        for _key in sorted(content_dict.keys()):
            _chapter = content_dict[_key]
            txt.write(_chapter["chapter_name"])
            txt.write("\n")
            txt.write(_chapter["main_content"])
            txt.write("\n")


content_dict = {}

#THREAD
def write_content(key: int, url: str):
    _d = get_chapter(url)
    content_dict[key] = _d
    #print("获取到章节内容. 章节名: " + _d["chapter_name"])

book = get_book(menu_page)
chapter_count = len(book["chapter_urls"])
thread_count = min(chapter_count, 60)

print(f"书名: {book['book_name']}")
print(f"章节数: {chapter_count}")
print(f"下载线程数: {thread_count}")

print("开始下载...")
time1 = time.time()
with ThreadPoolExecutor(max_workers = thread_count) as executor:
    for suffix in book["chapter_urls"]:
        executor.submit(write_content, int(suffix), menu_page + suffix + ".html")
print("下载完成. 下载章节数: %d, 用时%.1f秒" % (chapter_count, time.time() - time1))

print("开始写入文件...")
time1 = time.time()
write_to_text(book["book_name"], content_dict)
print("写入完成. 用时: %.1f秒" % (time.time() - time1))
