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
import io
import json
import os
import random
import re
import shutil
import sqlite3
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

import requests
from PIL import Image

from helper.db_helper import DBHelper
from helper.image_helper import ImageHelper
from model.data import *
from tqdm import tqdm

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None


def analysis_and_rename_file(dir_path, path_prefix, handler, num_prefix=None):
    filenames = os.listdir(dir_path)
    length = len(filenames)
    if not filenames and num_prefix:
        print(f'[{num_prefix}]无文件')
    for i, filename in enumerate(filenames):
        if '$RECYCLE' in filename or filename.endswith('.txt'):
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
col = db_helper.get_col(Col.Image)


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


def copy_from_nas():
    is_hor = False
    params = {
        'types': '1,2,3',
        'levels': '1,2,3,4,5,6',
        'limit': 300000,
        'isVertical': 'false' if is_hor else 'true',
        'isRandom': 'false',
        'halfMonth': 12,
        'startTime': '2024-09-17',
        # 'inAuthors': ','.join(['雨波_HaneAme', '星之迟迟', '小仓千代w', '小仓千代', '清水由乃', 'byoru', 'Byoru'])
        # 'inAuthors': ','.join(['雨波_HaneAme', '星之迟迟', '小仓千代w', '小仓千代', '清水由乃', 'byoru', 'Byoru'])
    }
    req = requests.get(url='https://nas.xuanniao.fun:49150//api/imageAlbum/imagePaths', params=params)
    infos = json.loads(req.text)
    base_path = 'D:/' + ('横' if is_hor else '竖')
    reg = re.compile(r'.*_(?P<type>\d)_(?P<level>\d)_\d{4}-\d{2}-\d{2}\.\w+')
    for i, info in enumerate(infos):
        path = info["path"]
        print(f'[{i}/{len(infos)}]{path}')
        try:
            remote_path = f'Z:/image/{path}'
            if not os.path.exists(remote_path):
                print('文件不存在，跳过')
                continue
            filename = info['aliasName'].replace(',', '_')
            match = reg.match(filename)
            if not match:
                print(f'文件名不合法，跳过：{filename}')
                continue
            img_type = match.group('type')
            level = match.group('level')
            dir_path = f'{base_path}/2-{img_type}-{level}'
            # dir_path = r'Y:/壁纸/竖/123'
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            local_path = f'{dir_path}/{filename}'
            if is_hor:
                max_width, max_height = 1920, 1080
            else:
                max_width, max_height = 1440, 2560
            FileHelper.compress_save(remote_path, local_path, max_width=max_width, max_height=max_height)
            # save_size_network_img(info['id'], local_path)
        except Exception as e:
            print(f'下载失败：{e}')


def save_size_network_img(obj_id, filepath):
    # if not db_helper.exist(Col.Image, fl={'_id': ObjectId(obj_id)}):
    #     return
    response = requests.get(f'https://nas.xuanniao.fun:49150/api/imageAlbum/sizedImage/{obj_id}?width=1440&height=2560')
    if response.status_code == 200:
        img = Image.open(io.BytesIO(response.content))
        filepath = filepath.replace('.png', '.jpg')
        img.save(filepath, 'JPEG', quality=90)
        # with open(filepath, 'wb') as f:
        #     f.write(response.content)
    else:
        print(f"无法下载图片，响应状态码: {response.status_code}")


def copy_tushy_img():
    src_dir = r'Y:\和谐\新建文件夹\\Tushy'
    dest_dir = r'Z:\image\和谐\写真\\Tushy[网站]'
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
    tags = db_helper.find_decode(Tag, fl, reverse=True)
    for i, tag in enumerate(tags):
        count = col.count_documents({'tags': tag.id()})
        if count == 0 and tag.type == '':
            db_helper.get_col(Col.Tag).delete_one({'_id': tag.id()})
            print(f'[{i}/{length}]{tag.name} 数量为空，删除')
            continue
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
        print(f'[{i}/{length}]{count}, {tag.id()}, {tag.name}, {tag.tran}, {img.color}, {img.path}')


dest_dir_path = 'Y:/thumb'


def create_thumb(prefix, query):
    relative_path = query['path']
    if relative_path.startswith('D:'):
        print(f'{relative_path} 本地文件，跳过')
        return
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


def update_name(tag_type: TagType, old, new):
    fl = {'tran': old, 'type': tag_type.value}
    exist_tag = db_helper.find_one_decode(Tag, fl)
    if exist_tag:
        db_helper.update_one(Col.Tag, fl, {'tran': new})
    key = ''
    if tag_type == TagType.Role:
        key = 'roles'
        old = old.split('(')[0]
        new = new.split('(')[0]
    elif tag_type == TagType.Work:
        key = 'works'
    elif tag_type == TagType.Author:
        key = 'authors'
    if not key:
        print('没有对应的 key')
        return
    res = col.update_many({key: old}, {'$addToSet': {key: new}})
    add_cnt = res.modified_count
    if old:
        res = col.update_many({key: old}, {'$pull': {key: old}})
        del_cnt = res.modified_count
    else:
        del_cnt = 0
    print(
        f'type: {tag_type}, {old} -> {new}, 更新 Tag: {exist_tag is not None}, 添加新数量: {add_cnt}, 删除旧数量: {del_cnt}')


type2Key = {
    TagType.Role: 'roles',
    TagType.Work: 'works',
    TagType.Author: 'authors',
}

type2cate_id = {
    TagType.Desc: ObjectId('644b699307d86ee33044b3e4'),
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
    key = type2Key.get(old.get_type())
    if key:
        cnt2 = col.update_many({key: old.tran}, {'$addToSet': {key: new.tran}}).modified_count
        col.update_many({key: new.tran}, {'$pull': {key: old.tran}})
    else:
        cnt2 = 0
    print(f'{old_name} -> {new.tran}, {res.modified_count}, {cnt2}, {new.name}, {new_alias}')


def refresh_audio_title_nand_artist(dir_path):
    from mutagen.flac import FLAC
    from mutagen.id3 import ID3, TIT2, TPE1

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
            title, artist = names[0], names[1]
        else:
            title, artist = names[0], ''
        # 移除 title 里由 「【】」包裹的内容
        title = re.sub(r'【.*?】', '', title)
        if extension == '.mp3':
            audio = ID3(filepath)
            audio["TIT2"] = TIT2(3, title)  # 更新歌曲标题
            audio["TPE1"] = TPE1(3, artist)  # 更新艺术家名称
        elif extension == '.flac':
            audio = FLAC(filepath)
            audio['TITLE'] = title
            audio['ARTIST'] = artist
        else:
            print('格式不支持')
            continue
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


def add_author_tag():
    items = col.aggregate([
        {"$match": {"type": {"$in": [2, 3]}}},
        {'$unwind': '$authors'},
        {'$group': {'_id': '$authors'}}
    ])
    for i, item in enumerate(items):
        author = item['_id']
        exist = db_helper.exist(Col.Tag, {'$or': [{'name': author}, {'alias': author}, {'tran': author}]})
        if exist:
            print(f'{i}, {author} 已存在')
            continue
        # cnt = col.count_documents({'authors': author})
        db_helper.insert(Col.Tag, Tag(name=author, tran=author, type=TagType.Author.value,
                                      category_id=type2cate_id[TagType.Author]))
        tag = db_helper.find_one_decode(Tag, {'tran': author})
        update_cnt = col.update_many({'authors': author}, {'$addToSet': {'tags': tag.id()}})
        print(f'{i}, {author} - {update_cnt.modified_count}')
    print('结束')


def tran_danbooru_tag():
    tags = db_helper.find_decode(Tag, {'source': TagSource.Danbooru.value, 'tran': '', 'type': ''})
    for i, tag in enumerate(tags):
        tran = translate(tag.name)
        print(f'[{i}/{len(tags)}]{tag.id()}, {tag.name} -> {tran}')
        db_helper.update_one(Col.Tag, {'_id': tag.id()}, {'tran': tran})


def translate(text):
    appid = '20180330000141696'  # 替换为你的APPID
    secretKey = 'T0cdT4oaaY73TaJ1G6vp'  # 替换为你的密钥

    httpClient = None
    myurl = '/api/trans/vip/translate'

    q = text
    fromLang = 'en'
    toLang = 'zh'
    salt = random.randint(32768, 65536)
    sign = appid + q + str(salt) + secretKey
    sign = hashlib.md5(sign.encode()).hexdigest()
    myurl = myurl + '?appid=' + appid + '&q=' + requests.utils.quote(
        q) + '&from=' + fromLang + '&to=' + toLang + '&salt=' + str(
        salt) + '&sign=' + sign

    try:
        httpClient = requests.get('https://api.fanyi.baidu.com' + myurl)
        response = httpClient.content.decode('utf-8')
        result = json.loads(response)
        if 'trans_result' in result:
            return result['trans_result'][0]['dst']
        else:
            return '翻译失败'
    except Exception as e:
        print(e)
    finally:
        if httpClient:
            httpClient.close()


def add_analysis_works(filepath, _):
    if not ImageHelper.is_image(filepath):
        return
    path_without_ext, ext = os.path.splitext(filepath)
    tag_filepath = f'{path_without_ext}.txt'
    if not os.path.exists(tag_filepath):
        return
    relative_path = FileHelper.get_relative_path(filepath)
    img = db_helper.find_one_decode(MyImage, {'path': relative_path})
    if not img:
        print('没有对应数据')
        return
    with open(tag_filepath) as f:
        tag_names = f.read().split(', ')
    exist_cnt = len(img.tags)
    new_tags = set()
    for tag in img.tags:
        if isinstance(tag, ObjectId):
            new_tags.add(tag)
        elif isinstance(tag, list):
            for item in tag:
                new_tags.add(item)
    add_tags = []
    roles = img.roles
    works = img.works
    for tag_name in tag_names:
        tag = db_helper.find_or_create_tag(tag_name, TagSource.Danbooru)
        new_tags.add(tag.id())
        if tag.id() not in img.tags:
            if tag.tran:
                add_tags.append(tag.tran)
            else:
                add_tags.append(tag.name)
        if tag.type == TagType.Role.value and tag.tran not in roles:
            # remove (xxx) in tag.tran
            roles.append(tag.tran.split('(')[0])
        if tag.type == TagType.Work.value and tag.tran not in works:
            works.append(tag.tran)
    new_tags = list(new_tags)
    roles = list(set(roles))
    works = list(set(works))
    col.update_one({'_id': img.id()}, {'$set': {'tags': new_tags, 'roles': roles, 'works': works}})
    # new_img = db_helper.find_one_decode(MyImage, {'path': relative_path})
    add_cnt = len(new_tags) - exist_cnt
    os.remove(tag_filepath)
    print(f'添加{add_cnt}标签：{add_tags}')


def del_empty_tag():
    fl = {
        # 'source': {'$in': [TagSource.Yande.value, TagSource.Pixiv.value, TagSource.Konachan.value]},
        'type': '',
        'count': 0
    }
    for tag in db_helper.find_decode(Tag, fl):
        print(f'{tag.source}, {tag.name}')
    db_helper.get_col(Col.Tag).delete_many(fl)
    print('结束')


def copy_all_images():
    import datetime
    conn = sqlite3.connect(f'D:\\主机壁纸\\data.sqlite')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS img (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            orientation INTEGER,
            type INTEGER,
            level INTEGER,
            works TEXT,
            roles TEXT,
            series TEXT,
            authors TEXT,
            create_date DATE,
            path TEXT,
            mongo_id TEXT
        );
        ''')
    # now = datetime.now()
    # one_year_ago = now - datetime.timedelta(days=500)
    # create_time = datetime.datetime(2024, 9, 13)
    create_time = datetime.datetime(2024, 11, 20)
    fl = {
        'level': {'$in': [8]},
        '$expr': {'$lte': ['$width', '$height']},
        'create_time': {'$gte': create_time},
    }
    total_cnt = col.count_documents(fl)
    li = col.find(fl)
    # li = col.aggregate([
    #     {'$match': fl},
    #     {'$sample': {'size': 3000}}
    # ])
    # li = db_helper.find(Col.Image, {'level': 7}).sort('create_time', pymongo.ASCENDING).skip(16000)
    insert_sql = '''
    INSERT INTO img (orientation, type, level, works, roles, series, authors, create_date, path, mongo_id) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    values = []
    dest_dir_path = 'D:\\主机壁纸'
    images = list(map(lambda x: MyImage.from_dict(x), li))
    for i, img in enumerate(images):
        # if i <= 16432:
        #     continue
        # remote_url = f'https://nas.xuanniao.fun:49150/image/{img.path}'
        # response = requests.get(remote_url)
        # if response.status_code != 200:
        #     print(f'{remote_url} 不存在')
        #     continue
        # temp_path = 'temp.jpg'
        # with open(temp_path, 'wb') as f:
        #     f.write(response.content)
        remote_path = os.path.join('z:\\image', img.path)
        if not os.path.exists(remote_path):
            continue
        works = ','.join(img.works)
        roles = ','.join(img.roles)
        authors = ','.join(img.authors)
        cnt = 0
        orientation = 1 if img.width > img.height else 2
        cursor.execute('SELECT * FROM img WHERE mongo_id = ?', [str(img.id())])
        local_img = cursor.fetchone()
        if local_img:
            print(f'[{i}/{total_cnt}]{img.path} 已存在')
            continue
        while True:
            alais_name = get_alias_name(img, cnt)
            relative_path = f'{orientation}-{img.type}-{img.level}/{alais_name}'
            dest_path = f'{dest_dir_path}/{relative_path}'
            if not os.path.exists(dest_path):
                break
            cnt += 1
        if cnt:
            print(f'有重复，重命名序号 {cnt}')
        # need_skip = i <= 15211
        need_skip = False
        if need_skip:
            cnt -= 1
            alais_name = get_alias_name(img, cnt)
            relative_path = f'{orientation}-{img.type}-{img.level}/{alais_name}'
            # dest_path = f'{dest_dir_path}/{relative_path}'
            dest_path = os.path.join(dest_dir_path, relative_path)

        print(f'[{i}/{total_cnt}]{img.path} -> {relative_path}')
        if orientation == 1:
            max_width, max_height = 1920, 1080
            # max_width, max_height = 2880, 1800
        else:
            max_width, max_height = 1080, 1920
        dir_path = os.path.dirname(dest_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        try:
            if not need_skip:
                FileHelper.compress_save(remote_path, dest_path, max_width=max_width, max_height=max_height)
        except Exception as e:
            # conn.commit()
            # cursor.close()
            # conn.close()
            print(f'压缩失败：{e}')
            continue
        values.append((orientation, img.type, img.level, works, roles, img.series, authors,
                       img.create_time.strftime('%Y-%m-%d'), relative_path, str(img.id())))
        if len(values) >= 1000:
            cursor.executemany(insert_sql, values)
            conn.commit()
            values.clear()
    cursor.close()
    conn.close()


def get_alias_name(img: MyImage, cnt: int):
    works = ','.join(img.works).replace('_', '##')
    roles = ','.join(img.roles).replace('_', '##')
    authors = ','.join(img.authors).replace('_', '##')
    series = img.series.replace('_', '##')
    filename, ext = os.path.splitext(os.path.basename(img.path))
    if img.type == 1 or img.type == 2:
        if works:
            prefix = f'{works}_{roles}_{series}_{authors}'
        else:
            prefix = filename.replace('_', 'xxx')
    else:
        prefix = f'{works}_{authors}'
    if cnt > 0:
        prefix += f'_n{cnt:02d}n'
    prefix = re.sub(r'[<>:"/\\|?*]', '#x#', prefix)
    date_str = img.create_time.strftime('%Y-%m-%d')
    return f'{prefix}_{img.type}_{img.level}_{date_str}.jpg'


def rename_jellyfin(season_no, dir_path):
    files = os.listdir(dir_path)
    cnt = len(files)
    for i, filename in enumerate(files):
        filepath = os.path.join(dir_path, filename)
        if os.path.isdir(filepath):
            continue
        if re.search(r'S\d\dE\d\d', filename):
            print(f'[{i}/{cnt}]已匹配，{filename}')
            continue
        # 使用正则表达式匹配并移除数字前的部分
        rules = [
            # ‘[Nekomoe kissaten&VCB-Studio] Oregairu Kan [07][Ma10p_1080p][x265_flac]
            (r'^.*?\[(\d+)]', r'[\1])', '['),
            # [VCB-Studio] Sidonia no Kishi 01  (Alternative Angle Ver.) [Hi10p 1080p x264 aac]
            (r'^.*?\b(\d+)\b', r'\1)', ' '),
        ]
        new_filename = None
        for pattern, repl, prefix in rules:
            new_filename = re.sub(pattern, repl, filename)
            if new_filename:
                new_filename = new_filename.strip().strip(prefix)
        if not new_filename or new_filename == filename:
            print(f'[{i}/{cnt}]未匹配，{filename}')
            continue
        new_filename = f'S{season_no:02d}E{new_filename}'
        if new_filename.endswith('.ass'):
            for item in ['.tc', '.TC', '.cht', '.JPTC']:
                new_filename = new_filename.replace(item, '')
            for item in ['.sc', '.SC', '.chs', '.JPSC']:
                new_filename = new_filename.replace(item, '.srd')
        new_filepath = os.path.join(dir_path, new_filename)
        os.rename(filepath, new_filepath)
        print(f'[{i}/{cnt}]{filename} -> {new_filename}')


def try_open_vixen_photo_web(kind, title, filename):
    base_path = f'Y:\\和谐\\新建文件夹\\{kind}'
    for exist_filename in os.listdir(base_path):
        if title in exist_filename:
            print('已经下载了')
            return
    exist = db_helper.find_one_decode(MyImage, {'path': {'$regex': f'{kind}.*{title}'}})
    if exist:
        print(f'已经存在了，{exist.path}')
        return
    dest_path = f'{base_path}\\{filename}'
    os.makedirs(dest_path)
    open_path = dest_path.replace('/', '\\')
    # ex = f"explorer {open_path}"
    # os.system(ex)
    low_str = title.replace(' ', '-').replace('\'', '').lower()
    url = f'https://members.{kind.lower()}.com/pictureset/{low_str}'
    print(url)
    os.system(f'start chrome "{url}"')
    _ = input('输入任意字符后继续：')


def download_vixen_images():
    with open('vixen.json') as f:
        js = json.load(f)
    nodes = js['data']['findVideosOnSites']['edges']
    kind = 'Deeper'
    for i, di in enumerate(nodes):
        node = di['node']
        title = node['title']
        title = re.sub(r'[<>/\\|:"?]', '', title)
        # slug = node['slug']
        # 2024-09-13T17:30:00.000Z
        release_date = node['releaseDate']
        date_str = release_date.split('T')[0]
        # 遍历合并 modelsSlugged 内除最后一个外的 name 为用 ', ' 隔开的字符串
        models = node['modelsSlugged']
        model_names = ', '.join([model['name'] for model in models[:-1]])
        # 生成文件名形如 Stefany Kyler - Petite Stefany Rides His Hard Cock[2024-11-30]
        filename = f'{model_names} - {title}[{date_str}]'
        print(f'[{i}/{len(nodes)}]{filename}')
        try_open_vixen_photo_web(kind, title, filename)
    print('本次搜索结束')
    exit()


def copy_fanboxs(path):
    filepaths = []
    for root, ds, fs in os.walk(path):
        for f in fs:
            if f.endswith('.json'):
                filepaths.append(os.path.join(root, f))
    for i, filepath in enumerate(filepaths):
        with open(filepath, 'r', encoding='utf-8') as f:
            js_obj = json.load(f)
        post_id = js_obj['body']['id']
        date = js_obj['body']['publishedDatetime'].split('T')[0]
        title = js_obj['body']["title"]
        username = js_obj['body']['user']['name']
        print(f'[{i}/{len(filepaths)}] {username}, {post_id}, {date}, {title}')
        if js_obj['body']['isRestricted']:
            print('未购买')
            continue
        dir_path = os.path.dirname(os.path.dirname(filepath)) + '\\images'
        if not os.path.exists(dir_path):
            print('没有图片文件夹')
            continue
        save_dir = f'Z:\\image\\二次元\\作者\\{username}'
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        filenames = os.listdir(dir_path)
        for j, filename in enumerate(filenames):
            source_path = os.path.join(dir_path, filename)
            extension = os.path.splitext(filename)[1]
            save_filename = f'{post_id}_{date}_{title}_{j + 1:02d}{extension}'
            save_path = os.path.join(save_dir, save_filename)
            if os.path.exists(save_path):
                continue
            print(f'[{i}/{len(filepaths)}][{j}/{len(filenames)}] 复制 {save_filename}')
            shutil.copy2(source_path, save_path)


def mv_media():
    src = 'X:\\media'
    src_dirs = []
    i = 0
    for rs, ds, fs in os.walk(src):
        for d in ds:
            if d == 'Subtitles':
                dir_path = os.path.join(rs, d)
                print(f'找到文件夹: {dir_path}')
                move_folder_with_progress(f'{i}-', src, dir_path)
                i += 1
                # src_dirs.append(dir_path)
                break
    # cnt = len(src_dirs)
    # for i, dir_path in enumerate(src_dirs):
    #     move_folder_with_progress(f'[{i}/{cnt}]', src, dir_path)


def move_folder_with_progress(prefix, src_base, src):
    dest = 'W:\\media'
    rel_path = os.path.relpath(src, src_base)
    dest_path = os.path.join(dest, rel_path)
    if os.path.exists(dest_path):
        print(f'{prefix}已存在，{dest_path}')
        return
    parent_dir = os.path.dirname(dest_path)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
    print(f'{prefix}移动 {src} -> {dest_path}')

    # os.system(f'robocopy "{src}" "{dest_path}" /MOVE /MT:16 /E /COPY:DAT')
    # return

    total_size = sum(os.path.getsize(os.path.join(root, f))
                     for root, _, files in os.walk(src)
                     for f in files)

    moved_size = 0

    # 创建目标文件夹
    os.makedirs(dest_path, exist_ok=True)

    # 移动文件夹下的所有内容
    with tqdm(total=total_size, unit='B', unit_scale=True, desc="Moving") as pbar:
        for root, dirs, files in os.walk(src):
            rel_path = os.path.relpath(root, src)
            target_root = os.path.join(dest_path, rel_path)

            os.makedirs(target_root, exist_ok=True)

            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(target_root, file)

                os.chmod(src_file, 0o777)
                shutil.move(src_file, dst_file)

                moved_size += os.path.getsize(dst_file)
                pbar.update(os.path.getsize(dst_file))

    # 删除空的源文件夹
    shutil.rmtree(src)


if __name__ == '__main__':
    # get_pixiv_down_author()
    # analysis_and_rename_file(r'C:\Users\illusion\Downloads\新建文件夹\雨波 2024 12月', 'Z:/', add_analysis_works)
    # copy_fanboxs(r'D:\code\GitHub\FANBOX-downloader\posts\daniella')
    # thumb_all_thumb()
    # update_tag_cover_and_count()
    # mv_media()
    # wnload_vixen_images()
    copy_all_images()
    # copy_from_nas()
    # rename_jellyfin(1, r'X:\media\tp\tv\[千夏字幕组&喵萌奶茶屋&VCB-Studio] 妖精森林的小不点')
    # del_empty_tag()
    # merge_tag('64ecb60b2b20a29f24220436', '65d0595ed66484ca5db1d3ca')
    # update_name(TagType.Role, '姉崎 寧', '姉崎 甘寧')
    # update_type(TagType.Role, '光荣', TagType.Company)
