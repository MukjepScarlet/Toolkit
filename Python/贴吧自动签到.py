# 使用方法：
# 在脚本目录下新建文件config.json，内容为一个字符串数组，里面放上需要使用的COOKIES，可以放多个，COOKIE文本中有双引号，请用转义符号
# 在Chrome或Edge等浏览器中进入贴吧首页并登录，按F12调出开发者界面，进入网络/Network选项，刷新网页，找到最上方的贴吧首页GET请求，复制请求的COOKIE文本，放入即可。
# 自动运行方法：使用Windows的计划任务功能，打开控制面板搜索进入，新建任务，选择触发器(TRIGGER)，每天在你使用电脑中途运行一次即可。(例如每天下午六点整，随机延迟5分钟)
# "程序或脚本"填入你的Python路径，参数设置成脚本文件的路径，工作目录填写脚本所在的目录
# NETA自：https://github.com/sakura-flutter/tampermonkey-scripts
# 功能：直接运行APP端签到，仿照MC的LOG写出LOGGER系统，可以观看运行结果

import requests, time, re, os, shutil, json
import hashlib, random
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

FAKE_VERSION = '11.8.8.0'

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.8,en-US,en;q=0.6,ja-JP,ja;q=0.4',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
}

APP_HEADERS = {
    'User-agent': f'bdtb for Android {FAKE_VERSION}',
    'Accept': '',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept-Encoding': 'gzip',
    'Cookie': 'ka=open',
}

def create_path(path: str):
    os.path.exists(path) or os.mkdir(path)

class Logger:
    def __init__(self, prefix: str):
        self.prefix = prefix
        self.sys_dir = os.path.dirname(os.path.realpath(__file__))
        self.log_path = os.path.join(self.sys_dir, "log")
        self.current_file = os.path.join(self.sys_dir, "latest.log")
        create_path(self.log_path)
        if os.path.isfile(self.current_file):
            new_name = '%s %s.log' % (self.prefix, time.strftime('%Y-%m-%d %H.%M.%S', time.localtime(os.path.getmtime(self.current_file))))
            new_path = os.path.join(self.sys_dir, new_name)
            os.rename(self.current_file, new_path)
            shutil.move(new_path, os.path.join(self.log_path, new_name))
    
    def log(self, message: str, mode: str = "INFO"):
        with open(self.current_file, 'a+', encoding='utf-8') as file:
            full_message = '[%s] [%s/%s]: %s\n' % (time.strftime('%H:%M:%S', time.localtime()), self.prefix, mode, message)
            file.write(full_message)
            print(full_message, end = '')
    
    def info(self, message: str):
        self.log(message, "INFO")

    def error(self, message: str):
        self.log(message, "ERROR")

    def warn(self, message: str):
        self.log(message, "WARN")
        
LOGGER = Logger("TiebaSign")

def random_string(length: int, table: 'str | list[str]' = '1234567890QWERTYUIOPASDFGHJKLZXCVBNMqwertyuiopasdfghjklzxcvbnm') -> str:
    return ''.join(random.choice(table) for _ in range(length))

def make_fake_params(obj: dict) -> dict:
    return {
        '_client_type': 4,
        '_client_version': FAKE_VERSION,
        '_phone_imei': '0' * 15,
        'model': 'HUAWEI P40',
        'net_type': 1,
        'stErrorNums': 1,
        'stMethod': 1,
        'stMode': 1,
        'stSize': 320,
        'stTime': 117,
        'stTimesNum': 1,
        'timestamp': int(time.time() * 1000),
        **obj
    }

def sign(payload: dict) -> str:
    s = ''.join(f'{key}={payload[key]}' for key in sorted(payload.keys())) + 'tiebaclient!!!'
    return hashlib.md5(s.encode('utf-8')).hexdigest()

def sign_request_params(params: dict, is_fake: bool = True) -> dict:
    if is_fake:
        params = make_fake_params(params)
    
    return {
        **params,
        'sign': sign(params)
    }

def to_url_params_string(params: dict) -> str:
    return '&'.join(f'{k}={v}' for k, v in params.items())

# 读取用户COOKIE信息

with open('config.json', 'r', encoding = 'utf-8') as config_file:
    cookies_texts = json.load(config_file)

# 签到运行部分

session = requests.session()
session.headers = HEADERS

def get_tbs() -> str:
    session.headers = HEADERS
    return re.findall(r'PageData.tbs = "(.*?)";', session.get('https://tieba.baidu.com/').text)[0]

def get_tieba_list(is_sign: bool = False) -> list[dict]:
    session.headers = HEADERS
    result = session.get('https://tieba.baidu.com/mo/q/newmoindex').json()
    if result['error'] != 'success':
        LOGGER.error("贴吧列表获取失败! 错误: %s" % str(result['error']))
        return []
    return [{'kw': b['forum_name'], 'fid': b['forum_id']} for b in result['data']['like_forum'] if b['is_sign'] == is_sign and b['forum_id']]

def do_sign(params: dict) -> bool: #fid: str, kw: str
    time.sleep(random.random() * 1.2 + 0.8)
    params.update({
        'BDUSS': BDUSS,
        'tbs': tbs
    })
    session.headers = APP_HEADERS
    result = session.post('http://c.tieba.baidu.com/c/c/forum/sign', data = to_url_params_string(sign_request_params(params)).encode('utf-8')).json()

    if result['error_code'] == '340006':
        LOGGER.warn('%s吧签到失败, 可能是这个吧出问题了' % (params['kw']))
        return False
    elif result['error_code'] == '340011':
        time.sleep(random.random() * 0.5 + 1)
        return do_sign({
            'kw': params['kw'],
            'fid': params['fid']
        })
    elif result['error_code'] == '110001':
        LOGGER.warn('%s吧签到失败, 未知错误' % (params['kw']))
        return False
    else:
        LOGGER.info("%s吧: 连续签到%s天, +%s" % (params['kw'], result['user_info']['cont_sign_num'], result['user_info']['sign_bonus_point']))
        return True

def do_sign_multiple(params: dict) -> bool: #forum_ids: list[str]
    params.update({
        'BDUSS': BDUSS,
        'tbs': tbs
    })
    session.headers = APP_HEADERS
    result = session.post('http://c.tieba.baidu.com/c/c/forum/msign', data = to_url_params_string(sign_request_params(params))).json()
    if result['error']['errno'] != '0':
        LOGGER.error("批量签到失败, 错误信息: \n    " + ';\n    '.join([f'{k}={v}' for k, v in result['error'].items()]))
        return False
    else:
        for r in result['info']:
            LOGGER.info("%s吧: 连续签到%s天, +%s" % (r['forum_name'], r['sign_day_count'], r['cur_score']))
        LOGGER.info("批量接口调用成功, 共签到成功%d个吧" % len(result['info']))
        return True

i = 1
for cookies_text in cookies_texts:
    time.sleep(random.random())

    LOGGER.info('导入第%d个COOKIE, 共%d个' % (i, len(cookies_texts)))

    BDUSS = None

    session.cookies.clear()

    for cookie in cookies_text.split('; '):
        s = cookie.split('=', 1)
        if s[0] == 'BDUSS':
            BDUSS = s[1]
        session.cookies.set(s[0], s[1])

    if BDUSS == None or type(BDUSS) == type('') and len(BDUSS) == 0:
        LOGGER.error('BDUSS未找到, 请检查当前COOKIE文本是否有误!')
        i += 1
        continue

    try:
        tbs = get_tbs()
    except requests.TooManyRedirects:
        LOGGER.error('重定向次数过多, TBS获取失败! 请检查COOKIE是否正确!')
        i += 1
        continue
    else:
        LOGGER.info('TBS获取成功: ' + tbs)

    tieba_list = get_tieba_list()

    if len(tieba_list) == 0:
        LOGGER.info('该账号没有今天未签到的吧')
        i += 1
        continue

    LOGGER.info("贴吧列表获取完成, 共有%d个贴吧待签到, 列表:" % len(tieba_list))
    LOGGER.info(", ".join(it['kw'] for it in tieba_list))

    if time.localtime().tm_hour == 0:
        LOGGER.warn("当前时间不支持批量签到, 将直接调用单个签到, 建议设置为1点以后运行")
    else:
        do_sign_multiple({
            'forum_ids': [it['fid'] for it in tieba_list][:199]
        })
        
        tieba_list = get_tieba_list()

        LOGGER.info("贴吧列表获取完成, 共有%d个贴吧待签到, 列表:" % len(tieba_list))
        LOGGER.info(", ".join(it['kw'] for it in tieba_list))

    with ThreadPoolExecutor(max_workers = min(3, len(tieba_list))) as executor:
        random.shuffle(tieba_list)
        tasks = [executor.submit(do_sign, it) for it in tieba_list]
    wait(tasks, timeout = 5.0 * len(tieba_list), return_when = ALL_COMPLETED)

    results = [t.result() for t in tasks]

    LOGGER.info('签到结束, 单个签到共有%d个贴吧成功' % sum(results))

    i += 1
