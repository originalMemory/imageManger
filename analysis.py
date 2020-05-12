#!/user/bin/env python
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : main
@author  : wuhoubo
@desc    : 
@create  : 2020/5/11 8:39:45
@update  :
"""

from googletrans import Translator
from openpyxl import Workbook
from helper.db_helper import DBHelper

def extractYandeTags():
    wb = Workbook()
    sheet = wb.get_active_sheet()
    sheet.append(('数量', '标签'))
    source = 'yande'
    offset = 0
    db_helper = DBHelper(error_handler)
    tags = {}
    while True:
        sql_str = f"select `desc` from image where source='{source}' limit 500 offset {offset};"
        print(sql_str)
        queries = db_helper.query_with_return_all(sql_str)
        if not queries:
            break

        for query in queries:
            tag_str = query['desc']
            if not tag_str:
                continue
            local_tags = str(tag_str).split(' ')
            for tag in local_tags:
                if tag in tags:
                    count = tags[tag]
                else:
                    count = 0
                tags[tag] = count + 1
        offset += 500
    
    tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)
    for (tag, count) in tags:
        sheet.append((count, tag))
    wb.save("yande标签列表.xlsx")

def error_handler(error_str):
    print(f"数据库错误：{error_str}")


if __name__ == '__main__':
    extractYandeTags()
