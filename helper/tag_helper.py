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

from helper.db_helper import DBHelper, DBExecuteType
from helper.image_helper import ImageHelper
from model.data import *


class TagHelper:
    db_helper = DBHelper(None)

    def _get_html(self, url, cookies_filepath=None):
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
            print(f'获取网页失败：{e}')

    def get_not_exist_yande_tag(self):
        imgs, _ = self.db_helper.search_by_where("source='yande' and uploader=''")
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
            if not html:
                time.sleep(2)
                continue
            val = BeautifulSoup(html, 'lxml')
            ul = val.find('div', id='stats').find('ul')
            li = ul.li.next_sibling.next_sibling
            uploader = li.a.next_sibling.next_sibling
            if not uploader:
                uploader = 'Anonymous'
            else:
                uploader = uploader.get_text()
            print(f'[{i}/{n}]{img.id} - {uploader} - {img.relative_path}')
            self.db_helper.execute(f"update myacg.image set uploader='{uploader}' where id={img.id}", DBExecuteType.Run)
            duration = random.uniform(0, 2)
            print(f'休眠 {duration}s')
            time.sleep(duration)
            i += 1

    def get_not_exist_pixiv_tag(self):
        imgs, _ = self.db_helper.search_by_where("source='pixiv' and tags=''")
        n = len(imgs)
        i = 0
        while i < n:
            img = imgs[i]
            no = ImageHelper.get_pixiv_no(img.relative_path)
            if not no:
                print(f'[{i}/{n}]找不到 no {img.id} - {img.relative_path}')
                i += 1
                continue
            html = self._get_html(f'https://www.pixiv.net/artworks/{no}', '../cookies.txt')
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

    def get_not_tran_yande_tag(self):
        queries = self.db_helper.execute("select * from myacg.tran_source", DBExecuteType.FetchAll)
        sources = [TranSource.from_dict(x) for x in queries]
        queries = self.db_helper.execute("select * from myacg.tran_dest", DBExecuteType.FetchAll)
        dest_id_di = {}
        for query in queries:
            dest = TranDest.from_dict(query)
            dest_id_di[str(dest.id)] = dest
        tags = []
        queries = self.db_helper.execute("select * from myacg.image where source='yande' and tags regexp '[a-z]'",
                                         DBExecuteType.FetchAll)
        for i in range(len(queries)):
            img = MyImage.from_mysql_dict(queries[i])
            print(f'[{i}/{len(queries)}]{img.id} - {img.tags}')
            for tag in img.tags.split(','):
                if tag.isdigit():
                    continue
                tags.append(tag)
        counter = Counter(tags)
        counter = counter.most_common()
        lines = ['数量,原名,翻译名,类型,备注\n']
        n = len(counter)
        for i in range(n):
            tag, count = counter[i]
            if count < 5:
                continue
            trans = []
            types = []
            for source in sources:
                patterns = [f'_{source.name}', f'{source.name}_', f'({source.name}', f'{source.name})']
                for pattern in patterns:
                    if pattern in tag:
                        for dest_id in source.dest_ids.split(','):
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
        with open('yande.csv', 'w+') as f:
            f.writelines(lines)

    def analysis_tags(self):
        queries = self.db_helper.execute("select * from myacg.tran_source", DBExecuteType.FetchAll)
        source_name_di = {}
        for query in queries:
            source = TranSource.from_dict(query)
            source_name_di[source.name] = source
        queries = self.db_helper.execute("select * from myacg.tran_dest", DBExecuteType.FetchAll)
        dest_name_di = {}
        dest_id_di = {}
        for query in queries:
            dest = TranDest.from_dict(query)
            dest_name_di[dest.name] = dest
            dest_id_di[dest.id] = dest
        queries = self.db_helper.execute("select * from myacg.image where source='yande' and tags regexp '[a-z]'",
                                         DBExecuteType.FetchAll)
        for i in range(len(queries)):
            image = MyImage.from_mysql_dict(queries[i])
            print(f'[{i}/{len(queries)}]{image.id} - {image.tags}')
            split_chars = [',', ';', ' ']
            for char in split_chars:
                if char in image.tags:
                    tags = image.tags.split(char)
                    break
            roles = set()
            if image.role:
                roles.add(image.role)
            works = image.works
            author = image.author
            new_tags = set()
            for tag in tags:
                if tag in dest_name_di:
                    new_tags.add(str(dest_name_di[tag].id))
                    continue
                if tag in source_name_di:
                    for dest_id in source_name_di[tag].dest_ids.split(','):
                        dest = dest_id_di[int(dest_id)]
                        if dest.type == TagType.Role:
                            roles.add(dest.name)
                        elif dest.type == TagType.Works:
                            works = dest.name
                        elif dest.type == TagType.Author:
                            author = dest.name
                        new_tags.add(str(dest_id))
                    continue
                new_tags.add(tag)
            tag_str = ','.join(new_tags).replace("\'", "\\'")
            role = ','.join(roles).replace("\'", "\\'")
            works = works.replace("\'", "\\'")
            author = author.replace("\'", "\\'")
            self.db_helper.execute(
                f"update myacg.image set tags='{tag_str}',role='{role}',works='{works}',author='{author}' where id={image.id}",
                DBExecuteType.Run)

    def record_trans_tags(self):
        with open('yande.csv') as f:
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
                if j < len(types):
                    type = types[j]
                else:
                    type = 'label'
                self.insert_or_update_tag(type, source, dest, extra)

    def insert_or_update_tag(self, type, source, dest, extra):
        source = source.replace("'", "\\'")
        dest = dest.replace("'", "\\'")
        if extra:
            extra = f"'{extra}'"
        else:
            extra = 'null'

        exist_dest = self.db_helper.execute(f"select id from myacg.tran_dest where name='{dest}'",
                                            DBExecuteType.FetchOne)
        if not exist_dest:
            self.db_helper.execute(f"insert into myacg.tran_dest(name, type, extra) VALUES ('{dest}','{type}',{extra})",
                                   DBExecuteType.Run)
            dest_id = self.db_helper.execute(f"select id from myacg.tran_dest where name='{dest}'",
                                             DBExecuteType.FetchOne)['id']
        else:
            dest_id = exist_dest['id']
        dest_id = str(dest_id)

        exist_source = self.db_helper.execute(f"select * from myacg.tran_source where name='{source}'",
                                              DBExecuteType.FetchOne)
        if exist_source:
            source = TranSource.from_dict(exist_source)
            if dest_id in source.dest_ids:
                print('已存在，跳过')
                return
            dest_ids = f'{source.dest_ids},{dest_id}'
            self.db_helper.execute(f"update myacg.tran_source set dest_ids='{dest_ids}' where id={source.id}",
                                   DBExecuteType.Run)
        else:
            self.db_helper.execute(f"insert into myacg.tran_source(name, dest_ids) VALUES ('{source}','{dest_id}')",
                                   DBExecuteType.Run)

    def update_author(self):
        queries = self.db_helper.execute(
            f"select d.id,s.name as source,d.name as dest,d.extra as dest from myacg.tran_source s inner join myacg.tran_dest d on d.id in(s.dest_ids) where d.extra is null and d.type='author';",
            DBExecuteType.FetchAll)
        for i in range(len(queries)):
            query = queries[i]
            source = query['source']
            id = query['id']
            print(f"[{i}/{len(queries)}]{id}, {query['dest']} - {source}")
            no, name = self.get_yande_author_info(source)
            if not no:
                continue
            self.db_helper.execute(f"update myacg.tran_dest set extra='{no}' where id={id}", DBExecuteType.Run)

    def get_yande_author_info(self, source):
        empty = None, None
        url = f'https://yande.re/artist.xml?name={source}'
        html = self._get_html(url)
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
        html = self._get_html(f'https://www.pixiv.net/users/{no}', '../cookies.txt')
        if not html:
            return empty
        val = BeautifulSoup(html, 'lxml')
        meta = val.find('meta', id='meta-preload-data')
        obj = json.loads(meta.attrs['content'])
        name = obj['user'][no]['name']
        return no, name
