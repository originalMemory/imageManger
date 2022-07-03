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
import math
import os
import random
import re
import shutil
import time
from collections import Counter

import requests
from bs4 import BeautifulSoup

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
            no = ImageHelper.get_yande_no(img.path)
            if not no:
                print(f'[{i}/{n}]{img.id} - {img.path}')
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
            print(f'[{i}/{n}]{img.id} - from {img.tags} to {tags} - {img.path}')
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
            no = ImageHelper.get_pixiv_no(img.path)
            if not no:
                print(f'[{i}/{n}]找不到 no {img.id} - {img.path}')
                i += 1
                continue
            html = self._get_html(f'https://www.pixiv.net/artworks/{no}', 'cookies.txt')
            if not html:
                time.sleep(3)
                continue
            if '该作品已被删除，或作品ID不存在。' in html:
                print(f'[{i}/{n}]作品不存在 {img.id} - {img.path}')
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

    def get_tag_source_data(self, fl, on_progress=None):
        queries = self.db_helper.search_all(Col.TranSource)
        sources = [TranSource.from_dict(x) for x in queries]
        queries = self.db_helper.search_all(Col.TranDest)
        dest_id_di = {}
        for query in queries:
            dest = TranDest.from_dict(query)
            dest_id_di[dest.id] = dest
        tags = []
        length = self.db_helper.get_count(fl)
        queries = self.db_helper.search_all(Col.Image, fl, {'tags': 1, '_id': 1})
        i = 0
        for query in queries:
            i += 1
            cur_tags = query['tags']
            source_tags = [x for x in cur_tags if not isinstance(x, ObjectId)]
            print(f'[{i}/{length}]{query["_id"]} - {source_tags}')
            on_progress.emit('获取标签', round((i / length) * 49))
            tags += source_tags
        counter = Counter(tags)
        counter = counter.most_common()
        on_progress.emit('统计数量', 50)
        return sources, dest_id_di, counter

    def get_not_tran_tags(self, fl, min_count, on_progress=None):
        sources, dest_id_di, counter = self.get_tag_source_data(fl, on_progress)
        lines = []
        data = []
        for tag, count in counter:
            data.append([tag, count])
            if count < min_count:
                break
        n = len(data)
        for i in range(n):
            tag, count = data[i]
            trans = []
            types = []
            for source in sources:
                # 一些标签是混合式的，用现有的混合判断下
                patterns = [f'_{source.name}', f'{source.name}_', f'({source.name}', f'{source.name})']
                for pattern in patterns:
                    if pattern in tag:
                        for dest_id in source.dest_ids:
                            dest = dest_id_di[dest_id]
                            if dest.type == TagType.Unknown:
                                continue
                            if dest.name == 'censored' and 'uncensored' in tag:
                                continue
                            if dest.name:
                                trans.append(dest.name)
                                types.append(dest.type.value)
                        break
            line = [count, tag, ';'.join(trans), ';'.join(types), '']
            print(f'[{i}/{n}]{line}')
            on_progress.emit('解析标签', 50 + round((i + 1) / n * 50))
            lines.append(line)
        return lines

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

    def analysis_tags(self, fl=None):
        if not fl:
            fl = {'source': 'yande', 'tags': {'$regex': '[a-z]'}}
        count = self.db_helper.get_count(fl)
        queries = self.db_helper.search_all(Col.Image, fl)
        i = 0
        for query in queries:
            image = MyImage.from_dict(query)
            i += 1
            roles = set(image.roles)
            works = set(image.works)
            authors = set(image.authors)
            new_tags = set()
            source_tags = []
            for tag in image.tags:
                if isinstance(tag, ObjectId):
                    new_tags.add(tag)
                    continue
                source = self.db_helper.search_one(Col.TranSource, {'name': tag})
                if not source:
                    source_tags.append(tag)
                    new_tags.add(tag)
                    continue
                source = TranSource.from_dict(source)
                for dest_id in source.dest_ids:
                    dest = self.db_helper.search_one(Col.TranDest, {'_id': dest_id})
                    if not dest:
                        continue
                    dest = TranDest.from_dict(dest)
                    new_tags.add(dest.id)
                    if dest.type == TagType.Role:
                        roles.add(dest.name)
                    elif dest.type == TagType.Works:
                        works.add(dest.name)
                    elif dest.type == TagType.Author:
                        authors.add(dest.name)
            print(f'[{i}/{count}]{image.id} - {image.path}, 剩余tags：{source_tags}')
            new_tags = list(new_tags)
            if new_tags == image.tags:
                continue
            self.db_helper.update_one(
                Col.Image,
                {'_id': image.id},
                {'$set': {'tags': new_tags, 'roles': list(roles), 'works': list(works), 'authors': list(authors)}}
            )
            image.tags = new_tags
            image.works = list(works)
            self.split_by_works(image)

    def split_by_works(self, info: MyImage):
        if not info.works or not os.path.exists(info.path):
            return
        base = 'Z:/图片/'
        max_work = ''
        for work in info.works:
            tp = re.sub(r'[<>/\\|:"?]', '_', work)
            if tp in info.path:
                return
            if len(max_work) < len(work):
                max_work = work
        work_dir = re.sub(r'[<>/\\|:"?]', '_', max_work)
        dir_path = os.path.join(base, work_dir)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        filepath = info.full_path()
        filename = os.path.basename(filepath)
        new_filepath = os.path.join(dir_path, filename).replace('\\', '/')
        shutil.move(filepath, new_filepath)
        self.db_helper.update_path(info.id, new_filepath.replace('Z:/', ''))
        print(f'归档到作品 {max_work} 内，文件名 {filename}')

    def record_trans_tags_files(self):
        with open('tags.csv', encoding='utf-8') as f:
            lines = f.readlines()
        for i in range(len(lines)):
            if i == 0:
                continue
            line = lines[i].strip()
            if not line:
                continue
            print(f'[{i}/{len(lines)}]{line}')
            line = line.split(',')
            source = line[1]
            dests = line[2].split(';')
            types = line[3].strip().split(';')
            extra = line[4].strip()
            self.record_tran_tag(source, dests, types, extra)

    def record_tran_tag(self, source, dests, types, extra):
        for j in range(len(dests)):
            if len(types) < len(dests):
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
        if not type:
            type = TagType.Unknown.value
        if not exist_dest:
            self.db_helper.insert(Col.TranDest, TranDest(name=dest, type=TagType(value=type), extra=extra).di())
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

    def get_tran_tags(self, tags):
        source_tags = []
        dest_ids = []
        for tag in tags:
            if isinstance(tag, ObjectId):
                dest_ids.append(tag)
                continue
            query = self.db_helper.search_one(Col.TranSource, {'name': tag})
            if not query:
                source_tags.append(tag)
                continue
            source = TranSource.from_dict(query)
            dest_ids += source.dest_ids
        query = self.db_helper.search_all(Col.TranDest, {'_id': {'$in': dest_ids}})
        tran_tags = list(map(lambda x: TranDest.from_dict(x), query))
        return tran_tags, source_tags


if __name__ == '__main__':
    TagHelper().record_trans_tags()
