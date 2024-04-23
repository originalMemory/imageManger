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
import hashlib
import json
import os
import re
import shutil
import urllib.parse
from datetime import datetime

from helper.file_helper import FileHelper


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


def copy_notion_2_obsidian():
    src_path = '/Users/illusion/Downloads/手办购买'
    bae_dest_path = '/Users/illusion/obsidian'
    dest_path = f'{bae_dest_path}/手办'
    keys = [
        'figurePhase',
        'figureType',
        'figureScale',
        'figureVersion',
        'figureSource',
        'figureCreator',
        'figureProxy',
        'figureOrderDate',
        'figureDeposit',
        'figureRemain',
        'figureTotal',
        'figureRemainDate',
        'figureGetDate'
    ]
    name_2_key = {
        '阶段': 'figurePhase',
        '类型': 'figureType',
        '比例': 'figureScale',
        '版本': 'figureVersion',
        '原作': 'figureSource',
        '工作室': 'figureCreator',
        '代理': 'figureProxy',
        '预定时间': 'figureOrderDate',
        '定金': 'figureDeposit',
        '补款': 'figureRemain',
        '总价': 'figureTotal',
        '补款时间': 'figureRemainDate',
        '到货时间': 'figureGetDate',
    }
    for filename in os.listdir(src_path):
        if not filename.endswith('.md'):
            continue
        with open(os.path.join(src_path, filename), 'r', encoding='utf-8') as f:
            lines = f.readlines()
        role = lines[0].strip('#').strip()
        creator = ''
        key_2_value = {}
        content_i = 0
        src_img_dir = os.path.splitext(filename)[0]
        url_encode_filename = urllib.parse.quote(src_img_dir)
        for i in range(2, 20):
            line = lines[i]
            if len(line) <= 2:
                content_i = i + 1
                break
            name, value = line.split(': ')
            value = value.strip()
            key = name_2_key.get(name)
            if not key:
                continue
            if key == 'figureCreator':
                creator = value
            key_2_value[key] = value
        new_lines = ['---\n']
        for key in keys:
            value = key_2_value.get(key, '')
            new_lines.append(f'{key}: {value}\n')
        first_img_path = ''
        contents = []
        for i in range(content_i, len(lines)):
            src_line = lines[i]
            line = lines[i].replace('## ', '# ')
            if not len(line):
                continue
            if url_encode_filename not in line:
                contents.append(line)
                continue
            # extract txt between ()
            match = re.search(r'\((.*?)\)', line)
            img_relative_path = None
            if match:
                img_relative_path = match.group(1)
            else:
                # extract txt between []
                match = re.search(r'\[(.*?)]', line)
                if match:
                    img_relative_path = match.group(1)
            if not img_relative_path:
                print(f'查找图片出错: {line}')
                contents.append(line)
                continue
            img_relative_path = urllib.parse.unquote(img_relative_path)
            img_path = f'{src_path}/{img_relative_path}'
            new_img_dir = f'img/2024-04'
            new_img_name = save_img(img_path, f'{bae_dest_path}/{new_img_dir}')
            new_img_path = f'{new_img_dir}/{new_img_name}'
            if not first_img_path:
                first_img_path = f'"![[{new_img_path}]]"'
            new_line = f'![{new_img_name}]({new_img_path})'
            contents.append(new_line)
        new_lines.append(f'cover: {first_img_path}\n')
        now_str = datetime.now().strftime('%Y-%m-%dT%H:%M')
        new_lines.append(f'created: {now_str}\n')
        new_lines.append(f'updated: {now_str}\n')
        new_lines.append('---\n')
        new_lines.extend(contents)
        with open(f'{dest_path}/{creator}-{role}.md', 'w+') as f:
            f.writelines(new_lines)
        print(f'{creator}-{role}.md')


def save_img(src_path, dest_dir):
    dest_name = os.path.basename(src_path)
    dest_path = os.path.join(dest_dir, dest_name)
    src_name = os.path.basename(src_path)
    decode_name = urllib.parse.unquote(src_name)
    if os.path.exists(dest_path) or src_name != decode_name:
        md5 = FileHelper.get_md5(src_path)
        ext = os.path.splitext(src_path)[1]
        dest_name = f'{md5}{ext}'
        dest_path = os.path.join(dest_dir, dest_name)
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    shutil.copy2(src_path, dest_path)
    return dest_name


if __name__ == '__main__':
    copy_notion_2_obsidian()
    # update_siyuan_souban_tag()
