#!/user/bin/env python
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : main
@author  : wuhoubo
@desc    :
@create  : 2021/11/13 15:57:59
@update  :
"""
import os
import re

from PIL import Image

from helper.db_helper import DBHelper, DBExecuteType
from helper.image_helper import ImageHelper
from helper.tag_helper import TagHelper
from model.data import *

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None


def analysis_and_rename_file(dir_path, prefix, handler):
    for root, dirs, files in os.walk(dir_path):
        length = len(files)
        for i in range(length):
            file = files[i]
            file_path = os.path.join(root, file)
            print(f'[{i}/{length}] {file_path}')
            handler(file_path, prefix)


db_helper = DBHelper(None)


def update_image(file_path, prefix):
    info = ImageHelper.analyze_image_info(file_path)
    source = info.source
    if source == 'pixiv':
        sub_str = f'_{info.tags}'
    elif source in ['yande', 'konachan']:
        if '00000' in info.relative_path:
            sub_str = f'{info.tags}_00000'
        elif '_00' in info.relative_path:
            sub_str = f'{info.tags}_00'
        else:
            sub_str = f'{info.tags}'
    else:
        sub_str = ''
    new_path = file_path.replace(sub_str, '')
    if file_path == new_path:
        print('未匹配或已经优化过文件名，直接跳过')
        return
    try:
        if not os.path.exists(new_path):
            os.rename(file_path, new_path)
    except Exception as e:
        print(f"重命名失败：{e}")
        return
    md5 = FileHelper.get_md5(new_path)
    old = db_helper.search_by_md5(md5)
    if not old:
        print('没有历史数据，跳过')
        return
    new_path = new_path.replace('\\', '/')
    image = MyImage(id=old.id, desc=info.desc, author=info.author, type=old.type, level=old.type,
                    tags=info.tags, works=old.works, role=old.role, source=info.source, width=old.width,
                    height=old.height, size=old.size, relative_path=new_path.replace(prefix, ''), md5=md5,
                    file_create_time=FileHelper.get_create_time_str(new_path), series=old.series,
                    uploader=info.uploader, sequence=old.sequence)
    db_helper.update_image(image)


def recheck_size(start_page):
    page_size = 500
    error_f = open('error.log', 'a+', encoding='utf-8')
    not_exist_f = open('notExist.log', 'a+', encoding='utf-8')
    count = db_helper.get_table_count("select count(*) from myacg.image;")
    while True:
        offset = (start_page - 1) * page_size
        sql = f"select * from myacg.image limit {page_size} offset {offset};"
        queries = db_helper.execute(sql, DBExecuteType.FetchAll)
        if not queries:
            print('没有数据，结束检查')
            break
        infos = [MyImage.from_mysql_dict(x) for x in queries]
        n = len(infos)
        for i in range(n):
            info = infos[i]
            print(f'[{offset + i}/{count}] {info.id}, {info.relative_path}')
            if not os.path.exists(info.path):
                not_exist_f.write(f'{info.id},{info.path}\n')
                print('图片不存在')
                db_helper.delete(info.id)
                continue
            try:
                width, height = Image.open(info.path).size
            except Exception as e:
                error_f.write(f'{info.id},{info.relative_path},{info.width},{info.height},{e}\n')
                print('尺寸读取失败')
                continue
            if not width or not height:
                error_f.write(f'{info.id},{info.relative_path},{info.width},{info.height}\n')
                print('尺寸读取失败')
                continue
            if width == info.width and height == info.height:
                continue
            print(f'宽度：{info.width} -> {width}，高度：{info.height} -> {height}')
            info.width = width
            info.height = height
            db_helper.update_image(info)
        start_page += 1
    error_f.close()
    not_exist_f.close()


def check_no_record_image(file_path, prefix):
    if not ImageHelper.is_image(file_path):
        return
    relative_path = file_path.replace('\\', '/').replace(prefix, '')
    info = db_helper.search_by_file_path(relative_path)
    if not info:
        md5 = FileHelper.get_md5(file_path)
        info = db_helper.search_by_md5(md5)
        if info:
            db_helper.update_path(info.id, relative_path)
    if not info:
        with open('notRecord.log', 'a+', encoding='utf-8') as f:
            f.write(f'{file_path}\n')
        print('文件不存在')


def rename_png2jpg(dir_path):
    for root, dirs, files in os.walk(dir_path):
        length = len(files)
        for i in range(length):
            file = files[i]
            file_path = os.path.join(root, file)
            print(f'[{i}/{length}] {file_path}')
            extension = FileHelper.get_file_extension(file_path)
            if extension != '.png':
                continue
            new_path = file_path.replace('.png', '.jpg')
            os.rename(file_path, new_path)


def get_file_paths(dir_path):
    paths = []
    img_extension = ['jpg', 'jpeg', 'bmp', 'png']
    # img_extension = ['png']
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.lower().split('.')[-1] in img_extension:
                paths.append([root, os.path.join(root, file)])
    return paths


def compress(source_dir, target_dir):
    paths = get_file_paths(source_dir)
    n = len(paths)
    total_percent = 0
    for i in range(n):
        path = os.path.join(paths[i][1])
        img = Image.open(path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        filename = path.split('/')[-1].split('.')[0]
        target_sub_dir = os.path.join(target_dir, paths[i][0].replace(source_dir, ''))
        new_path = os.path.join(target_sub_dir, filename + '.jpg')
        # if os.path.exists(new_path):
        #     continue
        no = 1
        while os.path.exists(new_path):
            new_path = os.path.join(target_sub_dir, f'{filename}_{no:0>2d}.jpg')
            print(f'有重复，重命名为：{new_path}')
            no += 1
        if not os.path.exists(target_sub_dir):
            print(f'创建文件夹{target_sub_dir}')
            os.makedirs(target_sub_dir)
        img.save(new_path, quality=90)
        old_size = FileHelper.get_file_size_in_mb(path)
        new_size = FileHelper.get_file_size_in_mb(new_path)
        sub = old_size - new_size
        percent = round(new_size * 100 / old_size, 2)
        total_percent += percent
        print(f'[{i}/{n}]压缩比例 {percent:.2f}%, 减小大小 {round(sub / old_size, 2):.2f} MB, {path.replace(source_dir, "")}')
    print(f'总压缩比：{round(total_percent / n, 2):.2f}%')


def check_exist(file_path, prefix):
    if not ImageHelper.is_image(file_path):
        return
    md5 = FileHelper.get_md5(file_path)
    info = db_helper.search_by_md5(md5)
    if info:
        print('已存在，删除该文件')
        os.remove(file_path)


def refresh_db():
    with open(r'F:\more.sql', encoding='utf-8') as f:
        lines = f.readlines()
    n = len(lines)
    for i, line in enumerate(lines):
        # if i < 542:
        #     continue
        if not line.startswith('INSERT'):
            continue
        print(f'[{i}/{n}]{line.strip()}')
        match = re.search(r"VALUES \((?P<values>.+?)\);$", line)
        if not match:
            print('搜索出错')
            continue
        values_source = [x.strip() for x in match.group('values').split(',')]
        values = []
        j = 0
        while j < len(values_source):
            value = values_source[j]
            if value.startswith("'") and not value.endswith("'"):
                tp = []
                while not values_source[j].endswith("'"):
                    tp.append(values_source[j])
                    j += 1
                tp.append(values_source[j])
                values.append(','.join(tp))
            else:
                values.append(value)
            j += 1

        d = 3
        for j in range(len(values)):
            values[j] = values[j].strip()
            if values[j].startswith("'"):
                values[j] = values[j][1:]
            if values[j].endswith("'"):
                values[j] = values[j][:-1]
        # INSERT INTO `image` VALUES ('249375', '', 'Shirokitsune', '', '2', '9', '', '原神', null, '0', '', '芭芭拉', '', '4000', '6000', '3.43', null, null, '和谐/收藏/Shirokitsune/芭芭拉/010.jpg', 'f2c435e981102cad2aa35924eb73b9c7', '2021-11-21 21:40:46', '2022-02-05 18:11:40', '2022-02-05 18:11:40');
        image = MyImage(
            desc=values[1],
            author=values[2],
            uploader=values[3],
            type=values[4],
            level=values[5],
            tags=values[6],
            works=values[7],
            sequence=values[8],
            series=values[9],
            role=values[10],
            source=values[11],
            width=values[12],
            height=values[13],
            size=values[14],
            relative_path=values[15],
            md5=values[16],
            file_create_time=values[17],
            create_time=values[18],
            update_time=values[19]
        )
        db_helper.insert_full_image(image)

def temp():
    queries = db_helper.execute("select * from myacg.image where source='yande' and tags!=''",
                                DBExecuteType.FetchAll)
    for i in range(len(queries)):
        img = MyImage.from_mysql_dict(queries[i])
        print(f'[{i}/{len(queries)}]{img.id} - {img.tags}')
        split_chars = [';', ',', ' ']
        tags = []
        for char in split_chars:
            if char not in img.tags:
                continue
            tags = img.tags.split(char)
        changed = False
        for j in range(len(tags)):
            tag = tags[j]
            if tag.isdigit():
                continue
            sql = f"select id from myacg.tran_dest where name='{tag}'"
            print(sql)
            query = db_helper.execute(sql, DBExecuteType.FetchOne)
            if query:
                changed = True
                tags[j] = str(query['id'])
        if not changed:
            continue
        db_helper.execute(f"update myacg.image set tags='{','.join(tags)}' where id={img.id}", DBExecuteType.Run)


if __name__ == '__main__':
    # analysis_and_rename_file(r'E:\下载\第四资源站\秋和柯基', 'Z:/', check_exist)
    # TagHelper().analysis_tags()
    # temp()
    print(ImageHelper.get_source_tags('[yande_492889_Mr_GT]asian_clothes cleavage clouble tianxia_00'))
