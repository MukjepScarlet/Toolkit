# 使用方法：
# 找到cookie_text变量，在Chrome或Edge等浏览器中进入贴吧首页并登录，按F12调出开发者界面，进入网络/Network选项，刷新网页，找到最上方的贴吧首页GET请求，复制请求的COOKIE文本，放入即可。
# 自动运行方法：使用Windows的计划任务功能，打开控制面板搜索进入，新建任务，选择触发器(TRIGGER)，每天在你使用电脑中途运行一次即可。(例如每天下午六点整，随机延迟5分钟)
# "程序或脚本"填入你的Python路径，参数设置成脚本路径，工作目录可以不填。(此脚本暂未追加日志功能)
# NETA自：https://github.com/sakura-flutter/tampermonkey-scripts
# 功能：直接运行APP端签到，开调试模式查看tasks可以观察运行结果，无可视化

import requests, time, re
import hashlib, random
from concurrent.futures import ThreadPoolExecutor

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

cookies_text = ''

session = requests.session()
session.headers = HEADERS

for cookie in cookies_text.split('; '):
    s = cookie.split('=', 1)
    if s[0] == 'BDUSS':
        BDUSS = s[1]
    session.cookies.set(s[0], s[1])

def get_tbs() -> str:
    session.headers = HEADERS
    return re.findall(r'PageData.tbs = "(.*?)";', session.get('https://tieba.baidu.com/').text)[0]

tbs = get_tbs()

def get_tieba_list(is_sign: bool = False) -> list[dict]:
    session.headers = HEADERS
    result = session.get('https://tieba.baidu.com/mo/q/newmoindex').json()
    if result['error'] != 'success':
        raise Exception("ERROR: %s" % result['error'])
    return [{'kw': b['forum_name'], 'fid': b['forum_id']} for b in result['data']['like_forum'] if b['is_sign'] == is_sign and b['forum_id']]

def do_sign(params: dict) -> dict: #fid: str, kw: str
    time.sleep(random.random() * 3 + 0.5)
    params.update({
        'BDUSS': BDUSS,
        'tbs': tbs
    })
    session.headers = APP_HEADERS
    result = session.post('http://c.tieba.baidu.com/c/c/forum/sign', data = to_url_params_string(sign_request_params(params)).encode('utf-8')).json()['user_info']
    return {
        'name': params['kw'],
        'bonus': result['sign_bonus_point']
    }

def do_sign_multiple(params: dict) -> dict: #forum_ids: list[str]
    time.sleep(random.random() * 0.5 + 0.8)
    params.update({
        'BDUSS': BDUSS,
        'tbs': tbs
    })
    session.headers = APP_HEADERS
    result = session.post('http://c.tieba.baidu.com/c/c/forum/msign', data = to_url_params_string(sign_request_params(params))).json()
    if result['error']['errno'] != '0':
        raise Exception("Sign failed")
    return result['info']

do_sign_multiple({
    'forum_ids': [it['fid'] for it in get_tieba_list()][:199]
})

with ThreadPoolExecutor(max_workers = 3) as executor:
    tasks = [executor.submit(do_sign, it) for it in get_tieba_list()]

pass
