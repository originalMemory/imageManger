#!/user/bin/env python
# coding=utf-8
import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
import zipfile
from dataclasses import dataclass

from hentai import Hentai, Format, Utils, Tag

from tools.shell import sh
import xml.etree.ElementTree as ET
from xml.dom import minidom


@dataclass
class ComicInfo:
    id: int
    raw: str
    name: str
    intro: str
    links: str


def search_tran(cursor, table, tags):
    if isinstance(tags, Tag):
        tags = [tags]
    for tag in tags:
        cursor.execute(f"SELECT * FROM {table} WHERE raw = ?", (tag.name,))
        res = cursor.fetchone()
        if res:
            info = ComicInfo(*res)
            return re.sub(r'!\[.*?]\(.*?\)', '', info.name)


def search(query):
    if isinstance(query, str):
        li = Utils.search_by_query(query)
    else:
        hen = Hentai(query)
        if not Hentai.exists(hen.id):
            print(f'没有找到: {query}')
            return
        li = [hen]
    doujin = None
    if not li:
        print('没有找到')
        return
    for item in li:
        exist_chinese = False
        for lan in item.language:
            if lan.name == 'chinese':
                doujin = item
                exist_chinese = True
                break
        if exist_chinese:
            break
        doujin = item
    conn = sqlite3.connect(r'Z:\图书\calibre\EhTagTranslation.db')
    cursor = conn.cursor()
    artist = search_tran(cursor, 'artist', doujin.artist)
    group = search_tran(cursor, 'groups', doujin.group)
    language = search_tran(cursor, 'language', doujin.language)
    tran_info_list = []
    parody = search_tran(cursor, 'parody', doujin.parody)
    if parody:
        tran_info_list.append(f"原作:{parody}")
    category = search_tran(cursor, 'category', doujin.category)
    if category:
        tran_info_list.append(f"分类:{category}")
    for tag in doujin.tag:
        name = search_tran(cursor, 'female', [tag])
        if name:
            tran_info_list.append(name)
            continue
        name = search_tran(cursor, 'male', [tag])
        if name:
            tran_info_list.append(name)
    en_title = doujin.title(Format.English)
    # japan_title = doujin.title(Format.Japanese)
    # 移除所有 [] 的内容
    # title = re.sub(r'\[.*?]', '', japan_title)
    # 从 en_title 提取最后一个 [] 内的内容
    translater = '翻译者:' + en_title.split('[')[-1].strip(']')
    # print(f'\n标题：{title}')
    print(f'书号：nhentai:{doujin.id}\n作者：{artist}\n出版商：{group}\n语言：{language}')
    print(f'标签：{",".join([translater] + tran_info_list)}\n')
    print(f'标签：{",".join(tran_info_list)}')
    cursor.close()
    conn.close()
    print('\n查找结束')


def update_default_extras():
    conn = sqlite3.connect(r'Z:\图书\calibre\漫画\metadata.db')
    cursor = conn.cursor()
    cursor.execute("select id from books")
    book_ids = list(map(lambda x: x[0], cursor.fetchall()))
    tables = ['custom_column_1', 'custom_column_2', 'custom_column_3', 'custom_column_4', 'custom_column_6']
    for i, book_id in enumerate(book_ids):
        if i < 1458:
            continue
        print(f'[{i}/{len(book_ids)}] {book_id}')
        for table in tables:
            exist = cursor.execute(f"select * from {table} where book = {book_id}").fetchone()
            if exist:
                continue
            sql = f"insert into {table} (book, value) values ({book_id}, false)"
            cursor.execute(sql)
            conn.commit()


def update_extra_cols():
    conn = sqlite3.connect(r'Z:\图书\calibre\漫画\metadata.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    i = 0
    for rs, ds, fs in os.walk(r'Z:\图书\calibre\漫画'):
        for f in fs:
            if f.endswith('.opf'):
                print(f'[{i}]{os.path.basename(rs)}')
                update_one_extra_col(conn, cursor, os.path.join(rs, f))
                i += 1
    conn.commit()
    cursor.close()
    conn.close()


def update_one_extra_col(conn, cursor, filepath):
    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()
    key_cut = 'is_cut'
    key_sort = 'is_sort'
    key_read = 'is_read'
    key_tankoubon = 'tankoubon'
    key_revise = 'revise'
    key_tran_title = 'tran_title'
    keys = [key_cut, key_sort, key_read, key_tankoubon, key_revise, key_tran_title]
    book_id = int(os.path.basename(os.path.dirname(filepath)).split('(')[-1].strip(')'))
    for line in lines:
        if '<meta name="calibre:user_metadata:' not in line:
            continue
        key = None
        for item in keys:
            prefix = f'<meta name="calibre:user_metadata:#{item}'
            if prefix in line:
                key = item
                break
        if not key:
            continue
        # &quot;#value#&quot;: false,
        match = re.search(f'&quot;#value#&quot;: ([^,]+),', line)
        if not match:
            continue
        value = match.group(1)
        value = value.replace('&quot;', '"')
        if key == key_tran_title:
            if value == 'null':
                continue
        elif value != 'true':
            continue
        table = None
        if key == key_sort:
            table = 'custom_column_1'
        elif key == key_tankoubon:
            table = 'custom_column_2'
        elif key == key_revise:
            table = 'custom_column_3'
        elif key == key_read:
            table = 'custom_column_4'
        elif key == key_tran_title:
            table = 'custom_column_5'
        elif key == key_cut:
            table = 'custom_column_6'
        if table:
            sql = f"insert into {table} (book, value) values ({book_id}, {value})"
            print(sql)
            cursor.execute(sql)
            conn.commit()


def update_new_book_meta(book_path, key, src, dest):
    meta_path = os.path.join('/Users/wuhb/Downloads/test', book_path, 'metadata.opf')
    with open(meta_path) as f:
        lines = f.readlines()
    for i in range(len(lines)):
        line = lines[i]
        if key in line:
            lines[i] = line.replace(src, dest)
            break
    with open(meta_path, 'w') as f:
        f.writelines(lines)


def get_rules(cursor, table):
    cursor.execute(f"select * from {table}")
    rules = []
    query = cursor.fetchall()
    for i, item in enumerate(query):
        tran = item[2]
        tran_with_prefix = f'女性:{tran}'
        rules.append({
            "match_type": "has",
            "replace": tran,
            "query": tran_with_prefix,
            "action": "replace"
        })
        print(f'[{i}/{len(query)}] {table} {item[1]} -> {item[2]}')
    return rules


def update_tag_map_rule():
    conn = sqlite3.connect(r'Z:\图书\calibre\EhTagTranslation.db')
    cursor = conn.cursor()
    tran_rules = get_rules(cursor, 'female')
    tran_rules += get_rules(cursor, 'male')
    tran_rules += get_rules(cursor, 'mixed')
    rule_path = r'D:\Program Files\Calibre Portable\Calibre Settings\tag-map-rules.json'
    with open(rule_path, encoding='utf-8') as f:
        rule_di = json.load(f)
    rule_name = '去除e-hentai男女标签前缀'
    rule_di[rule_name] = tran_rules
    with open(rule_path, 'w', encoding='utf-8') as f:
        json.dump(rule_di, f, ensure_ascii=False, indent=2)
    print('更新完成')
    cursor.close()
    conn.close()


if __name__ == '__main__':
    search(474078)
