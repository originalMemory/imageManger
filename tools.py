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

from PIL import Image

from helper.db_helper import DBHelper, DBExecuteType, tzinfo, Col
from helper.image_helper import ImageHelper
from helper.tag_helper import TagHelper
from model.data import *
from win32comext.shell import shell, shellcon

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None


def del_file(path):
    shell.SHFileOperation((0, shellcon.FO_DELETE, path, None,
                           shellcon.FOF_SILENT | shellcon.FOF_ALLOWUNDO | shellcon.FOF_NOCONFIRMATION, None,
                           None))  # 删除文件到回收站


def analysis_and_rename_file(dir_path, path_prefix, handler, num_prefix=None):
    filenames = os.listdir(dir_path)
    length = len(filenames)
    if not filenames and num_prefix:
        print(f'[{num_prefix}]无文件')
    for i, filename in enumerate(filenames):
        if '$RECYCLE' in filename:
            continue
        filepath = os.path.join(dir_path, filename)
        if os.path.isdir(filepath):
            prefix = f'{i}/{length}'
            if num_prefix:
                prefix = f'{num_prefix}-{prefix}'
            analysis_and_rename_file(filepath, path_prefix, handler, prefix)
            if not os.listdir(filepath):
                del_file(filepath)
            continue
        index_str = f'{i}/{length}'
        if num_prefix:
            index_str = f'{num_prefix}-{index_str}'
        print(f'[{index_str}] {filepath}')
        handler(filepath, path_prefix)


db_helper = DBHelper(None)
tag_helper = TagHelper()


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
        infos = [MyImage.from_dict(x) for x in queries]
        n = len(infos)
        for i in range(n):
            info = infos[i]
            print(f'[{offset + i}/{count}] {info.id}, {info.path}')
            if not os.path.exists(info.full_path()):
                not_exist_f.write(f'{info.id},{info.full_path()}\n')
                print('图片不存在')
                # db_helper.delete(info.id)
                continue
            try:
                width, height = Image.open(info.full_path()).size
            except Exception as e:
                error_f.write(f'{info.id},{info.full_path()},{info.width},{info.height},{e}\n')
                print('尺寸读取失败')
                continue
            if not width or not height:
                error_f.write(f'{info.id},{info.full_path()},{info.width},{info.height}\n')
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


def check_exist(file_path, prefix):
    if not ImageHelper.is_image(file_path):
        return
    md5 = FileHelper.get_md5(file_path)
    if db_helper.search_by_md5(md5) or db_helper.exist(Col.SimilarImage, {'md5s': md5}):
        print('已存在，删除该文件')
        del_file(file_path)


def update_path(filepath, prefix):
    if '$RECYCLE' in filepath:
        return
    if not ImageHelper.is_image(filepath):
        return
    relative_path = filepath.replace('\\', '/').replace(prefix, '')
    info = db_helper.search_by_file_path(relative_path)
    if info:
        return
    md5 = FileHelper.get_md5(filepath)
    info = db_helper.search_by_md5(md5)
    if info:
        db_helper.update_path(info.id, relative_path)


def split_by_works(filepath, prefix):
    if not ImageHelper.is_image(filepath):
        return
    relative_path = filepath.replace('\\', '/').replace(prefix, '')
    info = db_helper.search_by_file_path(relative_path)
    if not info:
        print('无信息，跳过')
        return
    tag_helper.split_by_works(info)


def check_no_split_works(filepath, prefix):
    if not ImageHelper.is_image(filepath):
        return
    relative_path = filepath.replace('\\', '/').replace(prefix, '')
    info = db_helper.search_by_file_path(relative_path)
    if not info:
        with open('notRecord.log', 'a+', encoding='utf-8') as f:
            f.write(f'{filepath}\n')
        print('无信息，跳过')
        return
    if not info.works:
        dir_name = filepath.split('\\')[-2].replace('_', '/')
        query = db_helper.execute(f"select id from myacg.tran_dest where name='{dir_name}'", DBExecuteType.FetchOne)
        if query:
            print("拆分但丢失作品信息")
            with open('notWorks.log', 'a+', encoding='utf-8') as f:
                f.write(f'{info.id}, {filepath}\n')
        return
    if info.works in filepath:
        return
    with open('notSplitWorks.log', 'a+', encoding='utf-8') as f:
        print("未按作品拆分")
        f.write(f'{info.id}, {info.works}, {filepath}\n')


def copy_image():
    dt = tzinfo.localize(datetime(2022, 1, 2))
    # dt = tzinfo.localize(datetime(2022, 1, 15))
    base = 'F:/壁纸/竖/'
    fl = {
        # 'type': 2,
        'level': {'$in': [1, 2, 3]},
        'create_time': {'$gte': dt},
        '$expr': {'$lt': ['$width', '$height']}
    }

    count = db_helper.get_count(fl)
    # query = db_helper.search_all(Col.Image, fl).skip(29246)
    query = db_helper.search_all(Col.Image, fl)
    i = 0
    for item in query:
        img = MyImage.from_dict(item)
        target_dir = f'{base}{img.type}-{img.level}'
        # if img.width > img.height:
        #     target_dir += '-1'
        # else:
        #     target_dir += '-2'
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        new_filename = os.path.basename(img.path).split('.')[0]
        if img.type == 2:
            new_filename = f"{';'.join(img.works)}_{';'.join(img.roles)}_{img.series}_{';'.join(img.authors)}"
        if img.type == 3:
            new_filename = f"{';'.join(img.works)}_{img.series}_{';'.join(img.authors)}"
        new_filename = new_filename.replace('/', '-')
        print(f'[{i}/{count}]{img.full_path()} to {target_dir}/{new_filename}')
        try:
            FileHelper.copyfile_without_override(img.full_path(), target_dir, new_filename, False)
        except Exception as e:
            print(e)
        i += 1


def record_similar_image(author, dir_path):
    filenames = os.listdir(dir_path)
    length = len(filenames)
    for i, filename in enumerate(filenames):
        filepath = os.path.join(dir_path, filename)
        if not os.path.isdir(filepath):
            continue
        paths = []
        for root, ds, fs in os.walk(filepath):
            for f in fs:
                if '$RECYCLE' in f or not ImageHelper.is_image(f):
                    continue
                paths.append(os.path.join(root, f))
        sub_length = len(paths)
        for j in range(sub_length):
            path = paths[j]
            info = f'[{i}/{length}-{j}/{sub_length}]{path}'
            md5 = FileHelper.get_md5(path)
            if db_helper.search_by_md5(md5) or db_helper.exist(Col.SimilarImage, {'md5s': md5}):
                print(info)
                continue
            di = db_helper.search_one(Col.SimilarImage, {'name': filename})
            if di:
                sim = SimilarImage(**di)
                sim.md5s.append(md5)
                db_helper.update_one(Col.SimilarImage, {'_id': sim.id()}, sim)
            else:
                sim = SimilarImage(author=author, name=filename, md5s=[md5])
                db_helper.insert(Col.SimilarImage, sim)
            print(f'{info}，保存相似md5 {md5}')


if __name__ == '__main__':
    analysis_and_rename_file(r'F:\图片\pixiv', 'Z:/', split_by_works)
    # record_similar_image('雨波_HaneAme', r'E:\下载\[HaneAme Collection]')
    # TagHelper().analysis_tags()
