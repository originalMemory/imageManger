#!/user/bin/env python
# coding=utf-8
import re
import sqlite3
from dataclasses import dataclass

from hentai import Hentai, Format, Utils, Tag


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


if __name__ == '__main__':
    search(504952)
