#!/user/bin/env python
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : main
@author  : wuhoubo
@desc    :
@create  : 202111/13 15:57:59
@update  :
"""
import json
import os
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

import requests
from PIL import Image
from colorthief import ColorThief

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
    params = {
        'filter': {
            'type': {'$in': [1, 2, 3]},
            'level': {'$in': [5, 6, 4]},
            '$expr': {'$lte': ['$width', '$height']},
        },
        'limit': 800,
        'random': True,
        'halfRecent': True,
    }
    req = requests.get(url='http://127.0.0.1:8000/api/randomImageSql', data=json.dumps(params),
                       headers={'Content-Type': 'application/json'})
    infos = json.loads(req.text)
    dir_path = '普通壁纸/横'
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    for i, info in enumerate(infos):
        remote_path = f'/Volumes/NAS/{info["path"]}'
        print(f'[{i}/{len(infos)}]{remote_path}')
        try:
            if not os.path.exists(remote_path):
                print('文件不存在，跳过')
                continue
            filename = info['aliasName'].replace(',', '_')
            local_path = f'{dir_path}/{filename}'
            FileHelper.compress_save(remote_path, local_path)
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


def validate_title(title):
    rstr = r"[\/\\\:\*\?\"\<\>\|]"  # '/ \ : * ? " < > |'
    new_title = re.sub(rstr, "~", title)  # 替换为下划线
    return new_title


def rename_bilibili_download():
    old_path = r'Z:\视频\MAD AMV'
    olds = os.listdir(old_path)
    dir_path = r'F:\B站\默认'
    li = os.listdir(dir_path)
    for i, av in enumerate(li):
        item_path = os.path.join(dir_path, av)
        dvi_path = os.path.join(item_path, f'{av}.dvi')
        if not os.path.exists(dvi_path):
            continue
        with open(dvi_path, encoding='utf-8') as f:
            di = json.load(f)
        title = di['Title']
        uploader = di['Uploader']
        new_name = f'{title}_{uploader}_{av}'
        print(f'[{i}/{len(li)}]{new_name}')
        os.rename(item_path, os.path.join(dir_path, validate_title(new_name)))
        for old in olds:
            if title in old or av in old:
                print(f'有已存在文件，删除 - {old}')
                FileHelper.del_file(os.path.join(old_path, old))


def get_exif():
    src = '/Users/wuhb/develop/self/image-album/public/src/__Lanthanum_Flameworks.jpg'
    with open(src, 'rb') as f:
        infos = []
        tags = exifread.process_file(f)
        model = tags.get('Image Model')
        infos.append(('器材', model))
        focal_length = tags.get('EXIF FocalLength')
        infos.append(('焦距', f'{focal_length}mm'))
        f_number = tags.get('EXIF FNumber', 0)
        if f_number:
            f_number = f'F{f_number}, '
        else:
            f_number = ''
        et = tags.get('EXIF ExposureTime', 0)
        if f_number:
            et = f'{et}s, '
        else:
            et = ''
        iso = tags.get('EXIF ISOSpeedRatings', 0)
        if iso:
            iso = f'ISO{iso}'
        else:
            iso = ''
        infos.append(('参数', f'{f_number}{et}{iso}'))
        infos.append(('软件', str(tags.get('Image Software'))))
        infos.append(('拍摄时间', tags.get('EXIF DateTimeOriginal')))
        for info in infos:
            print(info)

        for tag in tags:
            print(f'{tag}, {tags.get(tag)}')


# RGB格式颜色转换为16进制颜色格式
def RGB_to_Hex(rgb):
    color = '#'
    for i in rgb:
        num = int(i)
        # 将R、G、B分别转化为16进制拼接转换并大写  hex() 函数用于将10进制整数转换成16进制，以字符串形式表示
        color += str(hex(num))[-2:].replace('x', '0').upper()
    return color


executor = ThreadPoolExecutor(max_workers=20)
col = db_helper.get_col(Col.Image)


def update_color(prefix, query):
    path = FileHelper.get_full_path(query['path'])
    if not os.path.exists(path):
        print(f'{prefix}图片不存在, {path}')
        return
    color = ColorThief(path).get_color()
    hex = RGB_to_Hex(color)
    print(f'{prefix}{hex}, {path}')
    col.update_one({'_id': query['_id']}, {'$set': {'color': hex}})


def update_all_image_color():
    page = 0
    pagesize = 500
    fl = {'color': {'$exists': False}, 'level': {'$lte': 8}}
    total_count = col.count_documents(fl)
    while True:
        queries = col.find(fl, {'_id': 1, 'path': 1}).sort('_id', 1).limit(pagesize)
        empty = True
        tp = []
        for i, query in enumerate(queries):
            empty = False
            tp.append((f'[{page * pagesize + i}/{total_count}]', query))
            if len(tp) == 20:
                all_task = [executor.submit(update_color, x[0], x[1]) for x in tp]
                wait(all_task, return_when=ALL_COMPLETED)
                tp = []
        page += 1
        print()
        if empty:
            break


def update_tag_cover_and_count():
    fl = {}
    col_dest = db_helper.get_col(Col.TranDest)
    length = col_dest.count_documents(fl)
    queries = col_dest.find(fl).skip(1214)
    for i, query in enumerate(queries):
        dest = TranDest.from_dict(query)
        fl_img = {
            'tags': dest.id,
            'level': {'$gte': 5, '$lte': 8},
            '$expr': {'$gte': ['$width', '$height']},
        }
        # if dest.type == TagType.Works:
        #     fl_img['works'] = [dest.name]
        # elif dest.type == TagType.Role:
        #     fl_img['roles'] = [dest.name]
        limit = [x for x in col.find(fl_img).sort('create_time', -1).limit(1)]
        if not limit:
            fl_img['level'] = {'$lte': 8}
            limit = [x for x in col.find(fl_img).sort('create_time', -1).limit(1)]
        if not limit:
            del fl_img['$expr']
            limit = [x for x in col.find(fl_img).sort('create_time', -1).limit(1)]
        if not limit:
            continue
        img = MyImage.from_dict(limit[0])
        col_dest.update_one({'_id': dest.id}, {'$set': {'cover': img.path, 'color': img.color}})
        print(f'[{i}/{length}]{dest.name}, {img.color}, {img.path}')


def create_thumb(prefix, query):
    dest_dir_path = 'Y:/thumb'
    relative_path = query['path']
    full_path = FileHelper.get_full_path(relative_path)
    if not os.path.exists(full_path):
        print(f'{prefix}{full_path} 源文件不存在')
        return
    dest_path = f'{dest_dir_path}/{relative_path}'
    if os.path.exists(dest_path):
        print(f'{prefix}{full_path} 缩略图文件已存在')
        col.update_one({'_id': query['_id']}, {'$set': {'exist_thumb': True}})
        return
    dir_path = os.path.dirname(dest_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    size = ImageHelper.save_thumb(full_path, dest_path)
    col.update_one({'_id': query['_id']}, {'$set': {'exist_thumb': True}})
    print(f'{prefix}{size}, {dest_path}')


def thumb_all_thumb():
    page = 0
    pagesize = 2000
    exist_param = 'exist_thumb'
    fl = {'level': {'$lte': 8}}
    total_count = col.count_documents(fl)
    while page * pagesize <= total_count:
        queries = col.find(fl, {'_id': 1, 'path': 1, exist_param: 1}).sort('_id', 1).skip(page * pagesize).limit(
            pagesize)
        tp = []
        for i, query in enumerate(queries):
            prefix = f'[{page * pagesize + i}/{total_count}]'
            if exist_param in query:
                print(f'{prefix}已创建。{query["path"]}')
                continue
            tp.append((prefix, query))
            if len(tp) == 20:
                all_task = [executor.submit(create_thumb, x[0], x[1]) for x in tp]
                wait(all_task, return_when=ALL_COMPLETED)
                tp = []
        page += 1


if __name__ == '__main__':
    # get_pixiv_down_author()
    # analysis_and_rename_file(r'D:\新建文件夹 (2)\下载\弥音音', 'Z:/', check_exist)
    update_all_image_color()
    # update_tag_cover_and_count()
    # TagHelper().get_not_exist_yande_tag()
    # update_author_name('OrangeMaru', 'YD')
    # copy_image()
    # split_third_works()
    # record_similar_image('星之迟迟', r'E:\下载\第四资源站\未下\星之迟迟')
    # TagHelper().analysis_tags()
