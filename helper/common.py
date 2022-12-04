#!/user/bin/env python3
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : common.py
@author  : illusion
@desc    :
@create  : 2022-08-21 23:19:34
"""
import json
import random
import time

import requests


def get_html(url, cookies_filepath=None):
    i = 0
    while i < 3:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.119 Safari/537.36'}
            proxies = {"http": "http://127.0.0.1:7890", "https": 'http://127.0.0.1:7890'}
            cookies = {}
            if cookies_filepath:
                with open(cookies_filepath) as f:
                    obj = json.loads(f.read())
                    for item in obj:
                        cookies[item['name']] = item['value']
            return requests.get(url, headers=headers, proxies=proxies, timeout=12, cookies=cookies).text
        except Exception as e:
            print(f'第 {i} 次获取网页 {url} 失败：{e}')
            time.sleep(random.uniform(0, 2))
            i += 1