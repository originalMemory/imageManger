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
import json
import os
import shutil

import requests
from PIL import Image
from webdav3.client import Client
from webdav3.exceptions import NoConnection

from helper.config_helper import ConfigHelper
from helper.db_helper import DBHelper, Col
from helper.image_helper import ImageHelper
from helper.tag_helper import TagHelper
from model.data import *

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None


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
                FileHelper.del_file(filepath)
            continue
        index_str = f'{i}/{length}'
        if num_prefix:
            index_str = f'{num_prefix}-{index_str}'
        print(f'[{index_str}] {filepath}')
        handler(filepath, path_prefix)


db_helper = DBHelper(None)
tag_helper = TagHelper()


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
        FileHelper.del_file(file_path)


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
        print(f'更新地址。原地址：{info.full_path()}')
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


def split_third_works():
    source = r'F:\下载\Femjoy 2012'
    dir_paths = []
    for first in os.listdir(source):
        path = os.path.join(source, first)
        if os.path.isfile(path):
            continue
        for second in os.listdir(path):
            second_path = os.path.join(path, second)
            if os.path.isfile(second_path):
                continue
            dir_paths.append(second_path)
    author2paths = {}
    for path in dir_paths:
        info = ImageHelper.analyze_image_info(path, check_size=False)
        if not info.authors:
            continue
        author = info.authors[0]
        if author not in author2paths:
            author2paths[author] = []
        author2paths[author].append(path)
    dest = r'Z:\和谐\写真'
    dest_femjoy = r'Z:\和谐\写真\FemJoy[网站]'
    for author, paths in author2paths.items():
        print(f'{author} - {paths}')
        author_path = os.path.join(dest, author)
        dest_paths = []
        if len(paths) == 1 and not os.path.exists(author_path):
            path = paths[0]
            name = os.path.basename(path)
            dest_path = os.path.join(dest_femjoy, name)
            shutil.move(path, dest_path)
            dest_paths.append(dest_path)
        else:
            for path in paths:
                name = os.path.basename(path)
                dest_path = os.path.join(author_path, name)
                shutil.move(path, dest_path)
                dest_paths.append(dest_path)
        for path in dest_paths:
            analysis_and_rename_file(path, 'Z:/', update_path)


@dataclass
class AuthorCount:
    author: TranDest = field(default=None)
    sources: list = field(default_factory=list)
    count: int = field(default=0)


def get_down_author():
    queries = db_helper.search_all(Col.TranDest, {'type': 'author', '$expr': {'$gt': [{'$strLenCP': '$extra'}, 5]}})
    authors = [TranDest.from_dict(x) for x in queries]
    author_counts = []
    for i, author in enumerate(authors):
        if 'twitter' in author.extra:
            print(f'[{i}/{len(authors)}]{author.name} - 是 twitter 地址，跳过')
            continue
        count = db_helper.get_count({'authors': author.name})
        sources = db_helper.search_all(Col.TranSource, {'dest_ids': author.id}, {'name': 1})
        sources = [x['name'] for x in sources]
        print(f'[{i}/{len(authors)}]{author.name} - 英文名：{sources} 图片数：{count}')
        item = AuthorCount()
        item.author = author
        item.count = count
        item.sources = sources
        author_counts.append(item)
    author_counts = sorted(author_counts, key=lambda x: x.count, reverse=True)
    with open('authors.csv', 'w+', encoding='utf-8') as f:
        f.write('id, 作者, pixivId, 图片数')
        for item in author_counts:
            string = f'{item.author.id}, {item.author.name}, {item.author.extra}, {item.count}, {" ".join(item.sources)}\n'
            f.write(string)
            print(string[:-1])


def get_or_create_dest(name, tag_type, extra):
    fl = {'name': name}
    query = db_helper.search_one(Col.TranDest, fl)
    if query:
        return TranDest.from_dict(query)
    db_helper.insert(Col.TranDest, TranDest(name=name, type=tag_type, extra=extra).di())
    return TranDest.from_dict(db_helper.search_one(Col.TranDest, fl))


def update_author_name(old, new):
    fl = {'name': old}
    db_helper.update_one(Col.TranDest, fl, {'name': new})
    col = db_helper.get_col(Col.Image)
    res = col.update_many({'authors': old}, {'$addToSet': {'authors': new}})
    print(res.modified_count)
    res = col.update_many({'authors': old}, {'$pull': {'authors': old}})
    print(res.modified_count)


def copy_from_nas():
    config_helper = ConfigHelper()
    webdav_sec = 'webdav'
    options = {
        'webdav_hostname': 'http://192.168.31.39:5007/NAS',
        'webdav_login': config_helper.get_config_key(webdav_sec, 'login'),
        'webdav_password': config_helper.get_config_key(webdav_sec, 'password'),
        'webdav_timeout': 3
    }
    try:
        client = Client(options)
        client.check('test')
        print('使用局域网 webdav')
    except NoConnection as e:
        options['webdav_hostname'] = config_helper.get_config_key(webdav_sec, 'hostname')
        options['webdav_timeout'] = 10
        client = Client(options)
        print('使用远程 webdav')

    params = {
        'type': '1',
        'level': '4',
        'orientation': 2,
        'count': 1100
    }
    req = requests.get(url='https://xuanniao.fun/api/randomImagePaths', params=params)
    infos = json.loads(req.text)
    dir_path = 'F:/壁纸/竖/1-4'
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    for i, info in enumerate(infos):
        remote_path = info['path']
        print(f'[{i}/{len(infos)}]{remote_path}')
        try:
            if not client.check(remote_path):
                print('文件不存在，跳过')
                continue
            filename = info['aliasName'].replace(',', '_')
            local_path = FileHelper.get_no_repeat_filepath(dir_path, filename)
            client.download_sync(remote_path, local_path)
        except Exception as e:
            print(f'下载失败：{e}')


def copy_tushy_img():
    src_dir = r'F:\下载\Vixen'
    dest_dir = r'Z:\和谐\写真\Vixen[网站]'
    li = os.listdir(src_dir)
    len_i = len(li)
    for i, filename in enumerate(li):
        work_path = os.path.join(src_dir, filename)
        if not os.path.isdir(work_path):
            continue
        img_path = ''
        for item in os.listdir(work_path):
            path = os.path.join(work_path, item)
            if os.path.isdir(path):
                img_path = path
                break
        if not img_path:
            continue
        print(f'[{i}/{len_i}]{filename}')
        dest_path = os.path.join(dest_dir, filename)
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)
        lj = os.listdir(img_path)
        len_j = len(lj)
        for j, sub_name in enumerate(lj):
            dest_file = os.path.join(dest_path, sub_name)
            print(f'[{i}/{len_i}-{j}/{len_j}]{dest_file}')
            if os.path.exists(dest_file):
                continue
            shutil.copy2(os.path.join(img_path, sub_name), dest_file)


if __name__ == '__main__':
    # get_pixiv_down_author()
    analysis_and_rename_file(r'D:\新建文件夹 (2)\下载\弥音音', 'Z:/', check_exist)
    # TagHelper().get_not_exist_yande_tag()
    # update_author_name('OrangeMaru', 'YD')
    # copy_image()
    # split_third_works()
    # record_similar_image('星之迟迟', r'E:\下载\第四资源站\未下\星之迟迟')
    # TagHelper().analysis_tags()
