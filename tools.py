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
import logging
import os
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

import requests
from PIL import Image

# from mutagen.flac import FLAC
# from mutagen.mp3 import MP3

from helper.db_helper import DBHelper
from helper.image_helper import ImageHelper
from model.data import *
from tools.tag_helper import TagHelper

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


def check_no_record_image(file_path, prefix):
    if not ImageHelper.is_image(file_path):
        return
    relative_path = file_path.replace('\\', '/').replace(prefix, '')
    info = db_helper.search_by_file_path(relative_path)
    if not info:
        md5 = FileHelper.get_md5(file_path)
        info = db_helper.search_by_md5(md5)
        if info:
            db_helper.update_path(info.id(), relative_path)
    if not info:
        with open('notRecord.log', 'a+', encoding='utf-8') as f:
            f.write(f'{file_path}\n')
        print('文件不存在')


def check_exist(file_path, _):
    if not ImageHelper.is_image(file_path):
        return
    md5 = FileHelper.get_md5(file_path)
    if db_helper.search_by_md5(md5):
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
        db_helper.update_path(info.id(), relative_path)


def split_by_works(filepath, _):
    if not ImageHelper.is_image(filepath):
        return
    info = db_helper.search_by_file_path(filepath)
    if not info:
        print('无信息，跳过')
        return
    if not info.works or not os.path.exists(info.full_path()):
        return
    base = 'Z:/image/二次元'
    max_work = ''
    for work in info.works:
        tp = re.sub(r'[<>/\\|:"?]', '_', work)
        if tp in info.path:
            return
        if len(max_work) < len(work):
            max_work = work
    work_dir = re.sub(r'[<>/\\|:"?]', '_', max_work)
    dir_path = os.path.join(base, work_dir)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    filepath = info.full_path()
    filename = os.path.basename(filepath)
    new_filepath = os.path.join(dir_path, filename)
    shutil.move(filepath, new_filepath)
    db_helper.update_path(info.id(), FileHelper.get_relative_path(new_filepath))
    print(f'归档到作品 {max_work} 内，文件名 {filename}')


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


def setup_logging():
    logging.basicConfig(format='%(asctime)s, %(level)s: %(message)s', level=logging.INFO)


def copy_from_nas():
    params = {
        'types': '1,2,3',
        'levels': '5,6,7,8',
        'limit': 2000,
        'isVertical': 'true',
        'isRandom': 'true',
        'halfMonth': 3,
    }
    req = requests.get(url='https://nas.xuanniao.fun:49150/api/imageAlbum/imagePaths', params=params)
    infos = json.loads(req.text)
    dir_path = '/Users/illusion/Downloads/竖'
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    for i, info in enumerate(infos):
        remote_path = f'/Volumes/Core/image/{info["path"]}'
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


col = db_helper.get_col(Col.Image)


def update_color(prefix, query):
    path = FileHelper.get_full_path(query['path'])
    dest_path = path.replace('Z:/image', 'Y:/thumb')
    if os.path.exists(dest_path):
        path = dest_path
    if not os.path.exists(path):
        print(f'{prefix}图片不存在, {path}')
        return
    hex_color = ImageHelper.get_hex_color(path)
    print(f'{prefix}{hex_color}, {path}')
    col.update_one({'_id': query['_id']}, {'$set': {'color': hex_color}})


def update_all_image_color():
    executor = ThreadPoolExecutor(max_workers=20)
    page = 0
    pagesize = 5000
    fl = {'color': '', 'level': {'$lte': 8}}
    total_count = col.count_documents(fl)
    while True:
        queries = col.find(fl, {'_id': 1, 'path': 1, 'color': 1}).sort('_id', 1).limit(pagesize)
        empty = True
        tp = []
        for i, query in enumerate(queries):
            empty = False
            color = query['color']
            if color:
                continue
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
    fl = {'children': {'$size': 0}}
    col_tag = db_helper.get_col(Col.Tag)
    length = col_tag.count_documents(fl)
    tags = db_helper.find_decode(Tag, fl)
    for i, tag in enumerate(tags):
        count = col.count_documents({'tags': tag.id()})
        # col_tag.update_one({'_id': tag.id()}, {'$set': {'count': count}})
        # print(f'[{i}/{length}]{tag.name}, {tag.tran}, {count}')
        fl_img = {
            'tags': tag.id(),
            'level': {'$gte': 5, '$lte': 8},
            '$expr': {'$gte': ['$width', '$height']},
            "color": {'$exists': True, '$ne': ''}
            # "color": {'$and': [{'$exists': True}, {'$ne': ''}]}
        }
        limit = [x for x in col.find(fl_img).sort('create_time', -1).limit(1)]
        if not limit:
            fl_img['level'] = {'$lte': 8}
            limit = [x for x in col.find(fl_img).sort('create_time', -1).limit(1)]
        if not limit:
            del fl_img['$expr']
            limit = [x for x in col.find(fl_img).sort('create_time', -1).limit(1)]
        if not limit:
            col_tag.update_one({'_id': tag.id()}, {'$set': {'count': count}})
            print(f'[{i}/{length}]{tag.tran}, {count}')
            continue
        img = MyImage.from_dict(limit[0])
        col_tag.update_one({'_id': tag.id()}, {'$set': {'cover': img.path, 'color': img.color, 'count': count}})
        print(f'[{i}/{length}]{tag.name}, {tag.tran}, {count}, {img.color}, {img.path}')


dest_dir_path = 'Y:/thumb'


def create_thumb(prefix, query):
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
    parent_dir = os.path.dirname(dest_path)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
        print(f'{prefix}创建目录, {parent_dir}')
    try:
        size = ImageHelper.save_thumb(full_path, dest_path)
        dir_path = os.path.dirname(dest_path)
        color = query.get('color')
        if not color:
            color = ImageHelper.get_hex_color(dest_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        col.update_one({'_id': query['_id']}, {'$set': {'exist_thumb': True, 'color': color}})
        print(f'{prefix}{size}, {color}, {dest_path}')
    except Exception as e:
        print(f'{prefix}转换出错：{e}')


def thumb_all_thumb():
    executor = ThreadPoolExecutor(max_workers=20)
    page = 0
    pagesize = 2000
    exist_param = 'exist_thumb'
    fl = {'level': {'$lte': 8}}
    total_count = col.count_documents(fl)
    while page * pagesize <= total_count:
        queries = col.find(fl, {'_id': 1, 'path': 1, exist_param: 1}).sort('update_time', -1).skip(
            page * pagesize).limit(
            pagesize)
        tp = []
        print(f'获取{page}结束')
        for i, query in enumerate(queries):
            prefix = f'[{page * pagesize + i}/{total_count}]'
            path = query["path"]
            dest_path = f'{dest_dir_path}/{path}'
            if os.path.exists(dest_path):
                print(f'{prefix}已创建。{dest_path}')
                continue
            tp.append((prefix, query))
            if len(tp) == 20:
                all_task = [executor.submit(create_thumb, x[0], x[1]) for x in tp]
                wait(all_task, return_when=ALL_COMPLETED)
                tp = []
        page += 1


def pf(i, count, msg):
    print(f'[{i}/{count}]{msg}')


def update_name(tag_type: TagType, old, new):
    fl = {'tran': old, 'type': tag_type.value}
    exist_tag = db_helper.find_one_decode(Tag, fl)
    if exist_tag:
        db_helper.update_one(Col.Tag, fl, {'tran': new})
    key = ''
    if tag_type == TagType.Role:
        key = 'roles'
    elif tag_type == TagType.Work:
        key = 'works'
    elif tag_type == TagType.Author:
        key = 'authors'
    if not key:
        print('没有对应的 key')
        return
    res = col.update_many({key: old}, {'$addToSet': {key: new}})
    add_cnt = res.modified_count
    res = col.update_many({key: old}, {'$pull': {key: old}})
    del_cnt = res.modified_count
    print(
        f'type: {tag_type}, {old} -> {new}, 更新 Tag: {exist_tag is not None}, 添加新数量: {add_cnt}, 删除旧数量: {del_cnt}')


type2Key = {
    TagType.Role: 'roles',
    TagType.Work: 'works',
    TagType.Author: 'authors',
}

type2cate_id = {
    TagType.Desc: ObjectId('643d3445c5aed9845530fdf8'),
    TagType.Role: ObjectId('643d3445c5aed9845530fdf8'),
    TagType.Work: ObjectId('643d3fb986a0fb8a264d15f7'),
    TagType.Author: ObjectId('643d424e20d1428144cb441a'),
    TagType.Company: ObjectId('643d4252139fe1cdeeccc76b'),
    TagType.Unknown: ObjectId('643e90c4117ccd117ce689b6'),
}


def update_type(old_type, old_name, new_type, new_name=None):
    if not new_name:
        new_name = old_name
    tag = db_helper.find_one_decode(Tag, {'type': old_type.value, 'tran': old_name})
    if not tag:
        print(f'没有对应的 Tag, {old_name}')
        return
    db_helper.update_one(Col.Tag, {'_id': tag.id()},
                         {'type': new_type.value, 'tran': new_name, 'category_id': type2cate_id[new_type]})
    new_key = type2Key.get(new_type)
    fl = {'tags': tag.id()}
    if new_key:
        col.update_many(fl, {'$addToSet': {new_key: new_name}})
    old_key = type2Key.get(old_type)
    if old_key:
        cnt = col.update_many(fl, {'$pull': {old_key: old_name}}).modified_count
    else:
        cnt = 0
    print(f'{old_name}, {old_type} -> {new_type}, {new_name}, 数量: {cnt}')


def search_tags():
    imgs = db_helper.find_decode(MyImage, {'refresh': {'$exists': True}, 'source': 'pixiv'})
    tag_helper = TagHelper(db_helper)
    for i, img in enumerate(imgs):
        print(f'[{i}/{len(imgs)}]{img.path}')
        tag_helper.get_pixiv_tags(img)


def merge_tag(old_id, new_id):
    if old_id == new_id:
        print('old_id == new_id')
        return
    old = db_helper.find_one_decode(Tag, {'_id': ObjectId(old_id)})
    if not old:
        print('没有对应old')
        return
    old_name = old.name
    new = db_helper.find_one_decode(Tag, {'_id': ObjectId(new_id)})
    col_tag = db_helper.get_col(Col.Tag)
    col_tag.update_one({'_id': new.id()}, {'$addToSet': {'alias': old_name}})
    for old_alias in old.alias:
        col_tag.update_one({'_id': new.id()}, {'$addToSet': {'alias': old_alias}})
    new_alias = db_helper.find_one_decode(Tag, {'_id': ObjectId(new_id)}).alias
    col.update_many({'tags': old.id()}, {'$addToSet': {'tags': new.id()}})
    res = col.update_many({'tags': old.id()}, {'$pull': {'tags': old.id()}})
    col_tag.delete_one({'_id': old.id()})
    key = type2Key[old.get_type()]
    cnt2 = col.update_many({key: old.tran}, {'$addToSet': {key: new.tran}}).modified_count
    col.update_many({key: new.tran}, {'$pull': {key: old.tran}})
    print(f'{old_name} -> {new.tran}, {res.modified_count}, {cnt2}, {new.name}, {new_alias}')


def refresh_audio_title_nand_artist(dir_path):
    filepaths = []
    audio_ends = ['.mp3', '.flac']
    for root, ds, fs in os.walk(dir_path):
        for f in fs:
            for ends in audio_ends:
                if f.endswith(ends):
                    filepaths.append(os.path.join(root, f))
    for i, filepath in enumerate(filepaths):
        print(f'[{i}/{len(filepaths)}]{filepath}')
        name, extension = os.path.splitext(os.path.basename(filepath))
        names = name.split(' - ')
        if len(names) >= 2:
            title, artist = names[1], names[0]
        else:
            title, artist = names[0], ''
        if extension == '.mp3':
            audio = MP3(filepath)
        elif extension == '.flac':
            audio = FLAC(filepath)
        else:
            print('格式不支持')
            continue
        audio['TITLE'] = title
        audio['ARTIST'] = artist
        audio.pprint()
        audio.save()


def group_lifan():
    base = r'D:\BaiduNetdiskDownload\~合集\MS2102'
    video_paths = []
    cover_paths = []
    ass_paths = []
    for root, ds, fs in os.walk(base):
        for filename in fs:
            filepath = os.path.join(root, filename)
            if filename.endswith('.jpg'):
                cover_paths.append(filepath)
            if filename.endswith('.mkv'):
                video_paths.append(filepath)
            if filename.endswith('.ass'):
                ass_paths.append(filepath)
    for i, cover_path in enumerate(cover_paths):
        print(f'[{i}/{len(cover_paths)}]{cover_path}')
        cover_name = os.path.splitext(os.path.basename(cover_path))[0].replace('.ass', '')
        video_path, ass_path = None, None
        for path in video_paths:
            if cover_name in path:
                video_path = path
                break
        for path in ass_paths:
            if cover_name in path:
                ass_path = path
                break
        if not video_path or not ass_path:
            print('没有对应的视频或字幕')
            continue
        remove_values = [
            '[Maho.sub]', '[Maho＆sakurato.sub]',
            ' ＃1', ' ＃2', ' ＃3', ' ＃4', ' ＃5', ' ＃6',
            ' 第1巻', ' 第2巻', ' 第3巻', ' 上巻', ' 下巻'
        ]
        key = os.path.splitext(os.path.basename(ass_path))[0]
        for value in remove_values:
            key = key.replace(value, '')
        key = key.strip()
        dir_path = os.path.join(base, key)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        shutil.move(cover_path, os.path.join(dir_path, os.path.basename(cover_path)))
        shutil.move(video_path, os.path.join(dir_path, os.path.basename(video_path)))
        shutil.move(ass_path, os.path.join(dir_path, os.path.basename(ass_path)))


def remove_set(key, value):
    res = col.update_many({key: value}, {'$pull': {key: value}})
    print(res.modified_count)


if __name__ == '__main__':
    # get_pixiv_down_author()
    # analysis_and_rename_file(r'Z:\image\二次元\临时', 'Z:/', split_by_works)
    # thumb_all_thumb()
    # merge_tag('64422b2440aa1fca44e492e1', '65143aa217de431bdb6a6a50')
    update_name(TagType.Role, 'shenhe', '申鹤')
    # update_type(TagType.Work, 'punishing gray raven', TagType.Author)
    # update_tag_cover_and_count()
    # copy_from_nas()
    # split_third_works()
    # record_similar_image('星之迟迟', r'E:下载第四资源站未下星之迟迟')
