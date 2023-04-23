#!/usr/bin/env python3
# coding=utf-8
"""
@project : imageManger
@ide     : PyCharm
@file    : tag_helper.py
@author  : wuhb
@desc    :
@create  : 2022/3/18 11:43 AM
"""
import json
import random
import time

import requests
from bs4 import BeautifulSoup

from helper.db_helper import DBHelper
from model.data import *

_clash = 'http://127.0.0.1:7890'
_proxies = {"http": _clash, "https": _clash}


def _get_html(url):
    i = 0
    while i < 3:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.119 Safari/537.36'}
            return requests.get(url, headers=headers, proxies=_proxies, timeout=12).text
        except Exception as e:
            print(f'第 {i} 次获取网页 {url} 失败：{e}')
            time.sleep(random.uniform(0, 2))
            i += 1


tag_split = '##'


class TagHelper:
    def __init__(self, db_helper: DBHelper):
        self.db_helper = db_helper

    def get_konachan_yande_tag(self, img: MyImage):
        if img.source not in ['konachan', 'yande']:
            return
        url = None
        if img.source == 'kanachan':
            url = f'https://konachan.com/post/show/{img.sequence}'
        elif img.source == 'yande':
            url = f'https://yande.re/post/show/{img.sequence}'
        if not url:
            print(f'{img.source} 不支持, {img.path}')
            return
        html = _get_html(url)
        col = self.db_helper.get_col(Col.Image)

        if not html:
            _get_html('请求失败')
            return
        val = BeautifulSoup(html, 'lxml')
        title = val.find('title')
        if title.get_text() == 'Not Found (404)':
            print(f'没有图片信息')
            col.update_one({'_id': img.id()}, {'$unset': {'refresh': None}})
            return
        lis = val.find(id='tag-sidebar').find_all('li')
        new_tags = list(map(lambda li: li.contents[2].get_text(), lis))
        self._update_tags(img, new_tags)

    def _update_tags(self, img: MyImage, new_tags):
        tag_names = []
        tag_ids = []
        for tag_id in img.tags:
            tag = self.db_helper.find_one_decode(Tag, {'_id': tag_id})
            if tag:
                tag_ids.append(tag_id)
        for new_tag in new_tags:
            tag = self.db_helper.find_or_create_tag(new_tag)
            if tag.tran:
                tag_names.append(tag.tran)
            else:
                tag_names.append(tag.name)
            tag_ids.append(tag.id())
        duration = random.uniform(0, 2)
        tag_ids = list(set(tag_ids))
        col = self.db_helper.get_col(Col.Image)
        col.update_one({'_id': img.id()}, {'$set': {'tags': tag_ids}, '$unset': {'refresh': None}})
        print(f'休眠 {duration:.2f}s, 查找到标签：{tag_names}')
        time.sleep(duration)

    def get_danbooru_author(self, img: MyImage):
        empty = None, None
        params = {
            'api_key': 'L8QToTt8JorY3PExiQjcHnz3',
            'login': 'originalMemory',
            # 'only': 'id,name,urls'
        }
        url = f'https://danbooru.donmai.us/posts/{img.sequence}.json'
        try:
            req = requests.get(url=url, params=params)
            if not req:
                return empty
            js = json.loads(req.text)
            if not len(js):
                return empty
            tags = js['tag_string_general'].split(' ')
            tags += js['tag_string_character'].split(' ')
            tags += js['tag_string_copyright'].split(' ')
            tags += js['tag_string_artist'].split(' ')
            tags += js['tag_string_meta'].split(' ')
            new_tags = list(map(lambda x: x.replace('_', ' '), tags))
            self._update_tags(img, new_tags)
        except Exception as e:
            print(f'解析 donmai 作者信息失败：{e}')
            return empty

    # def get_not_exist_pixiv_tag(self):
    #     imgs, _ = db_helper.search_by_where("source='pixiv' and tags=''")
    #     n = len(imgs)
    #     i = 0
    #     while i < n:
    #         img = imgs[i]
    #         no = ImageHelper.get_pixiv_no(img.relative_path)
    #         if not no:
    #             print(f'[{i}/{n}]找不到 no {img.id} - {img.relative_path}')
    #             i += 1
    #             continue
    #         cookies = {}
    #         with open('cookies.txt') as f:
    #             obj = json.loads(f.read())
    #             for item in obj:
    #                 cookies[item['name']] = item['value']
    #         try:
    #             html = get_html(f'https://www.pixiv.net/artworks/{no}', cookies)
    #         except Exception as e:
    #             print(f'失败：{e}')
    #             time.sleep(3)
    #             continue
    #         if '该作品已被删除，或作品ID不存在。' in html:
    #             print(f'[{i}/{n}]作品不存在 {img.id} - {img.relative_path}')
    #             i += 1
    #             continue
    #         val = BeautifulSoup(html, 'lxml')
    #         meta = val.find('meta', id='meta-preload-data')
    #         obj = json.loads(meta.attrs['content'])
    #         print(json.dumps(obj))
    #         break
    #         obj_tags = obj['illust'][no]['tags']['tags']
    #         tags = []
    #         for tag in obj_tags:
    #             tag_str = tag['tag']
    #             if 'translation' in tag:
    #                 tag_str += f"({tag['translation']['en']})"
    #             tags.append(tag_str)
    #         tag_str = ';'.join(tags)
    #         tag_str = tag_str.replace("'", "\\'")
    #         print(f'[{i}/{n}]{img.id} - {no},{img.desc} - {tag_str}')
    #         img.tags = tag_str
    #         db_helper.execute(f"update image set tags='{tag_str}' where id={img.id}", DBExecuteType.Run)
    #         duration = random.uniform(0, 2)
    #         print(f'休眠 {duration}s')
    #         time.sleep(duration)
    #         i += 1
