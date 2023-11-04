#!/usr/bin/env python3
# coding=utf-8
"""
@project : imageManger
@ide     : PyCharm
@file     : note
@author  : wuhb
@desc    :
@create  : 2023/11/4 23:17
"""
import json
import os
import re
from datetime import datetime


def update_siyuan_souban_tag():
    name_2_key = {
        '阶段': 'custom-phase',
        '类型': 'custom-type',
        '比例': 'custom-scale',
        '版本': 'custom-version',
        '预定时间': 'custom-order-date',
        '定金': 'custom-deposit',
        '补款': 'custom-remainder',
        '总价': 'custom-total',
        '支付尾款时间': 'custom-remainder-date',
        '补款时间': 'custom-remainder-date',
        '到货时间': 'custom-arrival-date',
        '购买链接': 'custom-url',
    }
    dir_path = '/Users/wuhb/SiYuan/data/20231103155125-bte6bri/20231104164047-ta1nc9j'
    # 以 RO 八重神子文件里的顺序为准
    template_filepath = '/Users/wuhb/SiYuan/data/20231103155125-bte6bri/20231104164047-ta1nc9j/20231104162431-ttg39xj.sy'
    attr_key = 'custom-doc-attrs'
    with open(template_filepath, 'r', encoding='utf-8') as f:
        attr_value = json.load(f)['Properties'].get(attr_key)
    for filename in os.listdir(dir_path):
        if not filename.endswith('.sy'):
            continue
        filepath = os.path.join(dir_path, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            txt = f.read()
        match = re.search(rf'更新: (.*?)("|\\n)', txt)
        if not match or match.group(0) == '0':
            continue
        update_txt = match.group(0).strip('\\n').strip('"')
        finish_txt = update_txt.replace('1', '0')
        txt = txt.replace(update_txt, finish_txt)

        data = json.loads(txt)
        properties = data['Properties']
        properties[attr_key] = attr_value
        for name, key in name_2_key.items():
            match = re.search(rf'{name}: ?(.*?)("|\\n)', txt)
            if not match:
                continue
            value = match.group(1)
            if not value:
                continue
            key = name_2_key[name]
            if 'date' in key:
                # value from 'September 15, 2023' to '2023-09-15 00:00:00'
                # 使用 datetime 解析日期字符串
                date_obj = datetime.strptime(value, '%B %d, %Y')
                # 将日期对象格式化为目标字符串格式
                value = date_obj.strftime('%Y-%m-%d 00:00:00')

            properties[key] = value
        data['Properties'] = properties
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    update_siyuan_souban_tag()
