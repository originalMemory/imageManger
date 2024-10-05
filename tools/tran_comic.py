#!/user/bin/env python
# coding=utf-8
import os
import re
import shutil
import sqlite3
import subprocess
from dataclasses import dataclass

import chardet
# from hentai import Hentai, Format, Utils, Tag

from tools.shell import sh
import xml.etree.ElementTree as ET


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
    conn = sqlite3.connect('Z:\图书\calibre\EhTagTranslation.db')
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
            tran_info_list.append(f"女性:{name}")
            continue
        name = search_tran(cursor, 'male', [tag])
        if name:
            tran_info_list.append(f"男性:{name}")
    en_title = doujin.title(Format.English)
    japan_title = doujin.title(Format.Japanese)
    # 移除所有 [] 的内容
    title = re.sub(r'\[.*?]', '', japan_title)
    # 从 en_title 提取最后一个 [] 内的内容
    translater = '翻译者:' + en_title.split('[')[-1].strip(']')
    print(f'\n标题：{title}')
    print(f'书号：nhentai:{doujin.id}\n作者：{artist}\n出版商：{group}\n语言：{language}')
    print(f'标签：{",".join([translater] + tran_info_list)}\n')
    print(f'标签：{",".join(tran_info_list)}')
    cursor.close()
    conn.close()
    print('\n查找结束')


def copy_obf():
    filepaths = []
    for rs, ds, fs in os.walk('/Users/wuhb/Downloads/manga'):
        for f in fs:
            if f.endswith('.cbz'):
                filepaths.append(os.path.join(rs, f))
    for i, filepath in enumerate(filepaths):
        print(f'[{i}/{len(filepaths)}]{filepath}')
        filename = os.path.splitext(os.path.basename(filepath))[0]
        dir_path = os.path.dirname(filepath)
        new_obf = os.path.join(dir_path, f'{filename}.opf')
        if os.path.exists(new_obf):
            continue
        old_obf = os.path.join(dir_path, 'metadata.opf')
        if not os.path.exists(old_obf):
            continue
        shutil.copy2(old_obf, new_obf)


def update_extra_col():
    filepaths = []
    for rs, ds, fs in os.walk('/Users/wuhb/Downloads/manga'):
        for f in fs:
            if f.endswith('.opf'):
                filepaths.append(os.path.join(rs, f))
    conn = sqlite3.connect('/Users/wuhb/Downloads/test/metadata.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    for i, filepath in enumerate(filepaths):
        print(f'[{i}/{len(filepaths)}]{filepath}')
        with open(filepath, encoding='utf-8') as f:
            lines = f.readlines()
        key_cut = 'is_cut'
        key_sort = 'is_sort'
        key_read = 'is_read'
        key_tankoubon = 'tankoubon'
        key_revise = 'revise'
        key_tran_title = 'tran_title'
        keys = [key_cut, key_sort, key_read, key_tankoubon, key_revise, key_tran_title]
        book_id = -1
        book_path = ''
        for line in lines:
            # extract title from "<dc:title>カルデアバニー部</dc:title>"
            title_match = re.search('<dc:title>([^<]+)</dc:title>', line)
            if title_match:
                title = title_match.group(1)
                cursor.execute(f"SELECT * FROM books WHERE title = '{title}'")
                di = dict(cursor.fetchone())
                book_id = di.get('id', -1)
                book_path = di.get('path', '')
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
            if key == key_tran_title:
                sql = f"insert into custom_column_5 (value) values ('{value}')"
                print(sql)
                cursor.execute(sql)
                tran_id = cursor.lastrowid
                sql = f"insert into books_custom_column_5_link (book, value) values ({book_id}, {tran_id})"
                print(sql)
                cursor.execute(sql)
                conn.commit()
                update_new_book_meta(book_path, key, '&quot;#value#&quot;: null,', f'&quot;#value#&quot;: &quot;{value}&quot;,')
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
            elif key == key_cut:
                table = 'custom_column_6'
            if table:
                sql = f"update {table} set value=true where book={book_id}"
                print(sql)
                cursor.execute(sql)
                conn.commit()
                update_new_book_meta(book_path, key, '&quot;#value#&quot;: false,', f'&quot;#value#&quot;: true,')
    conn.commit()
    cursor.close()
    conn.close()


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


if __name__ == '__main__':
    update_extra_col()
