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
import re
import time
from collections import Counter

import requests
from bs4 import BeautifulSoup
from bson import ObjectId

from helper.db_helper import DBHelper, DBExecuteType, Col
from helper.image_helper import ImageHelper
from model.data import *


class TagHelper:
    db_helper = DBHelper(None)

    def _get_html(self, url, cookies_filepath=None):
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
                print(f'第 {i} 次获取网页失败：{e}')
                time.sleep(random.uniform(0, 2))
                i += 1

    def get_not_exist_yande_tag(self):
        imgs, _ = self.db_helper.search_by_filter("path like '%图片/新妹魔王的契约者%'")
        n = len(imgs)
        i = 0
        while i < n:
            img = imgs[i]
            no = ImageHelper.get_yande_no(img.relative_path)
            if not no:
                print(f'[{i}/{n}]{img.id} - {img.relative_path}')
                i += 1
                continue
            url = f'https://yande.re/post/show/{no}'
            html = self._get_html(url)
            duration = random.uniform(0, 1)
            if not html:
                print(f'请求失败，休眠 {duration}s 重试')
                time.sleep(duration)
                continue
            val = BeautifulSoup(html, 'lxml')
            # ul = val.find('div', id='stats').find('ul')
            # li = ul.li.next_sibling.next_sibling
            # uploader = li.a.next_sibling.next_sibling
            # if not uploader:
            #     uploader = 'Anonymous'
            # else:
            #     uploader = uploader.get_text()
            lis = val.find('ul', id='tag-sidebar').find_all('li')
            # tags = img.tags.split(',')
            tags = []
            for li in lis:
                tag = li.contents[2].get_text().replace(' ', '_')
                query = self.db_helper.search_one(Col.TranDest, {'name': tag}, {'dest_ids': 1})
                if query:
                    tags += query['dest_ids'].split(',')
                else:
                    tags.append(tag)
            print(f'[{i}/{n}]{img.id} - from {img.tags} to {tags} - {img.relative_path}')
            if img.tags == tags:
                i += 1
                continue
            self.db_helper.update_one(Col.Image, {'_id': img.id}, {'tags': tags})
            # print(f'休眠 {duration:.2f}s')
            # time.sleep(duration)
            i += 1

    def get_not_exist_pixiv_tag(self):
        imgs, _ = self.db_helper.search_by_filter("source='pixiv' and length(tags)<20")
        n = len(imgs)
        i = 0
        while i < n:
            img = imgs[i]
            no = ImageHelper.get_pixiv_no(img.relative_path)
            if not no:
                print(f'[{i}/{n}]找不到 no {img.id} - {img.relative_path}')
                i += 1
                continue
            html = self._get_html(f'https://www.pixiv.net/artworks/{no}', 'cookies.txt')
            if not html:
                time.sleep(3)
                continue
            if '该作品已被删除，或作品ID不存在。' in html:
                print(f'[{i}/{n}]作品不存在 {img.id} - {img.relative_path}')
                i += 1
                continue
            val = BeautifulSoup(html, 'lxml')
            meta = val.find('meta', id='meta-preload-data')
            obj = json.loads(meta.attrs['content'])
            obj_tags = obj['illust'][no]['tags']['tags']
            tags = []
            for tag in obj_tags:
                tag_str = tag['tag']
                if 'translation' in tag:
                    tag_str += f"({tag['translation']['en']})"
                tags.append(tag_str)
            tag_str = ';'.join(tags)
            tag_str = tag_str.replace("'", "\\'")
            print(f'[{i}/{n}]{img.id} - {no},{img.desc} - {tag_str}')
            img.tags = tag_str
            self.db_helper.execute(f"update myacg.image set tags='{tag_str}' where id={img.id}", DBExecuteType.Run)
            duration = random.uniform(0, 2)
            print(f'休眠 {duration}s')
            time.sleep(duration)
            i += 1

    def get_tag_source_data(self, fl):
        queries = self.db_helper.search_all(Col.TranSource)
        sources = [TranSource.from_dict(x) for x in queries]
        queries = self.db_helper.search_all(Col.TranDest)
        dest_id_di = {}
        for query in queries:
            dest = TranDest.from_dict(query)
            dest_id_di[dest.id] = dest
        tags = []
        length = self.db_helper.get_count(fl)
        queries = self.db_helper.search_all(Col.Image, fl)
        i = 0
        for query in queries:
            i += 1
            img = MyImage.from_dict(query)
            print(f'[{i}/{length}]{img.id} - {img.tags}')
            for tag in img.tags:
                if isinstance(tag, ObjectId):
                    continue
                tags.append(tag)
        counter = Counter(tags)
        counter = counter.most_common()
        return sources, dest_id_di, counter

    def get_not_tran_yande_tag(self):
        sources, dest_id_di, counter = self.get_tag_source_data({'source': 'yande', 'tags': {'$regex': '[a-z]'}})
        lines = ['数量,原名,翻译名,类型,备注\n']
        n = len(counter)
        for i in range(n):
            tag, count = counter[i]
            if count < 5:
                continue
            trans = []
            types = []
            for source in sources:
                # 一些标签是混合式的，用现有的混合判断下
                patterns = [f'_{source.name}', f'{source.name}_', f'({source.name}', f'{source.name})']
                for pattern in patterns:
                    if pattern in tag:
                        for dest_id in source.dest_ids:
                            dest = dest_id_di[dest_id]
                            if dest.name == 'censored' and 'uncensored' in tag:
                                continue
                            if dest.name:
                                trans.append(dest.name)
                                types.append(dest.type.value)
                        break
            extra = ''
            if not trans:
                no, name = self.get_yande_author_info(tag)
                if no:
                    trans.append(name)
                    types.append('author')
                    extra = no
            line = f"{count},{tag},{';'.join(trans)},{';'.join(types)},{extra}\n"
            print(f'[{i}/{n}]{line.strip()}')
            lines.append(line)
        with open('tags.csv', 'w+', encoding='utf-8') as f:
            f.writelines(lines)

    def get_not_tran_pixiv_tag(self):
        sources, dest_id_di, counter = self.get_tag_source_data({'source': 'pixiv'})
        lines = ['数量,原名,翻译名,类型,备注\n']
        n = len(counter)
        for i in range(n):
            mix_tag, count = counter[i]
            if count < 10:
                continue
            trans = []
            types = []
            if '(' in mix_tag:
                trans.append(mix_tag.split('(')[1][:-1])
                types.append('label')
            if 'R-18' == mix_tag:
                trans.append(mix_tag)
                types.append('label')
            for source in sources:
                if source.name not in mix_tag:
                    continue
                for dest_id in source.dest_ids.split(','):
                    dest = dest_id_di[dest_id]
                    if dest.name:
                        trans.append(dest.name)
                        types.append(dest.type.value)
                break
            line = f"{count},{mix_tag},{';'.join(trans)},{';'.join(types)},\n"
            print(f'[{i}/{n}]{line.strip()}')
            lines.append(line)
        with open('pixiv.csv', 'w+', encoding='utf-8') as f:
            f.writelines(lines)

    def analysis_tags(self):
        queries = self.db_helper.search_all(Col.TranSource)
        source_name_di = {}
        for query in queries:
            source = TranSource.from_dict(query)
            source_name_di[source.name] = source
        source_name_di = {}
        queries = self.db_helper.search_all(Col.TranDest)
        dest_name_di = {}
        dest_id_di = {}
        for query in queries:
            dest = TranDest.from_dict(query)
            dest_name_di[dest.name] = dest
            dest_id_di[dest.id] = dest
        sources, dest_id_di, counter = self.get_tag_source_data()
        queries = self.db_helper.search_all(Col.Image, {'source': 'yande', 'tags': {'$regex': '[a-z]'}})
        for i in range(len(queries)):
            image = MyImage.from_dict(queries[i])
            print(f'[{i}/{len(queries)}]{image.id} - {image.tags}')
            roles = set(image.roles)
            works = image.works
            authors = image.authors
            new_tags = set()
            for tag in image.tags:
                if tag in dest_name_di:
                    new_tags.add(str(dest_name_di[tag].id))
                    continue
                if tag in source_name_di:
                    if tag not in source_name_di:
                        continue
                    for dest_id in source_name_di[tag].dest_ids.split(','):
                        dest = dest_id_di[int(dest_id)]
                        if dest.type == TagType.Role:
                            roles.add(dest.name)
                        elif dest.type == TagType.Works:
                            works.append(dest.name)
                        elif dest.type == TagType.Author:
                            authors.append(dest.name)
                        elif dest.type == TagType.Empty:
                            new_tags.add(tag)
                            break
                        new_tags.add(str(dest_id))
                    continue
                new_tags.add(tag)
            if new_tags == image.tags:
                continue
            self.db_helper.get_col(Col.Image).update_one(
                {'_id': image.id},
                {'tags': new_tags, 'roles': roles, 'works': works, 'authors': authors}
            )

    def record_trans_tags(self):
        with open('tags.csv', encoding='utf-8') as f:
            lines = f.readlines()
        for i in range(len(lines)):
            line = lines[i].strip()
            print(f'[{i}/{len(lines)}]{line}')
            line = line.split(',')
            source = line[1]
            dests = line[2].split(';')
            types = line[3].strip().split(';')
            extra = line[4].strip()
            for j in range(len(dests)):
                if len(types) > 1 and len(types) != len(dests):
                    print('数据不匹配')
                    continue
                dest = dests[j]
                type = ''
                if j < len(types):
                    type = types[j]
                self.insert_or_update_tag(type, source, dest, extra)

    def insert_or_update_tag(self, type, source, dest, extra):
        dest_fl = {'name': dest}
        exist_dest = self.db_helper.search_one(Col.TranDest, dest_fl)
        if not exist_dest:
            self.db_helper.insert(Col.TranDest, TranDest(name=dest, type=TagType(type), extra=extra))
            dest_id = self.db_helper.search_one(Col.TranDest, dest_fl, {'_id': 1})['_id']
        else:
            dest_id = exist_dest['_id']

        exist_source = self.db_helper.search_one(Col.TranSource, {'name': source})
        if exist_source:
            source = TranSource.from_dict(exist_source)
            if dest_id in source.dest_ids:
                print('已存在，跳过')
                return
            dest_ids = source.dest_ids
            dest_ids.append(dest_id)
            self.db_helper.update_one(Col.TranSource, {'_id': source.id}, {'dest_ids': dest_ids})
        else:
            self.db_helper.insert(Col.TranSource, TranSource(name=source, dest_ids=[dest_id]))

    def get_yande_author_info(self, source):
        url = f'https://yande.re/artist.xml?name={source}'
        html = self._get_html(url)
        no, name = self._search_author_info_by_match(html)
        if no:
            return no, name
        # danbooru 的数据比 yande 全，再查一次
        return self._get_danbooru_author(source)

    def _get_danbooru_author(self, name):
        empty = None, None
        url = f"https://danbooru.donmai.us/artists?commit=Search&search[any_name_matches]={name}"
        html = self._get_html(url)
        if not html:
            return empty
        try:
            val = BeautifulSoup(html, 'lxml')
            a_nodes = val.findAll(name="a", attrs={"class": "tag-type-1"})
            if not len(a_nodes):
                return empty
            artist_url = f"https://danbooru.donmai.us/{a_nodes[0].attrs['href']}"
            return self._search_author_info_by_match(self._get_html(artist_url))
        except Exception as e:
            print(f'解析 pixiv 用户信息失败 {e}')
            return empty

    def _search_author_info_by_match(self, html):
        empty = None, None
        if not html:
            return empty
        match = re.search(r"member.php\?id=(?P<no>\d+)", html)
        no = None
        if match:
            no = match.group('no')
        else:
            match = re.search(r"users/(?P<no>\d+)", html)
            if match:
                no = match.group('no')
        if not no:
            return empty
        html = self._get_html(f'https://www.pixiv.net/users/{no}', 'cookies.txt')
        if not html:
            return empty
        try:
            val = BeautifulSoup(html, 'lxml')
            meta = val.find('meta', id='meta-preload-data')
            obj = json.loads(meta.attrs['content'])
            name = obj['user'][no]['name']
        except Exception as e:
            print(f'解析 pixiv 用户信息失败 {e}')
            return empty
        return no, name

    @staticmethod
    def split_tags(tags):
        split_chars = [';', ',', ' ']
        for char in split_chars:
            if char not in tags:
                continue
            return tags.split(char)
        return [tags]


if __name__ == '__main__':
    TagHelper().record_trans_tags()
