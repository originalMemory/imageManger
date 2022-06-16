#!/user/bin/env python
# coding=utf-8
"""
@project : DeviceManager
@ide     : PyCharm
@file    : db_helper
@author  : wuhoubo
@desc    : 数据库交互
@create  : 2019/5/27 21:03:31
@update  :
"""
import time
from datetime import datetime
from enum import unique, Enum

import pymongo
import pytz
from dateutil.parser import parser

from helper.config_helper import ConfigHelper
from model.data import MyImage, BaseData, ImageFile


def get_time(f):
    def inner(*arg, **kwarg):
        s_time = time.time()
        res = f(*arg, **kwarg)
        e_time = time.time()
        print('耗时：{}秒'.format(e_time - s_time))
        return res

    return inner


@unique
class DBExecuteType(Enum):
    Run = 0
    FetchAll = 1
    FetchOne = 2


@unique
class Col(Enum):
    Image = 'image'
    Level = 'level'
    Type = 'type'
    TranSource = 'tran_source'
    TranDest = 'tran_dest'


tzinfo = pytz.timezone('Asia/Shanghai')


class DBHelper:
    db = pymongo.MongoClient(ConfigHelper().get_config_key('database', 'mongo'), tz_aware=True, tzinfo=tzinfo)['acg']
    img_col = db['image']

    def __init__(self, error_handler, with_server=False):
        self.error_handler = error_handler

    # def __show_error(self, error):
    #     error_str = str(error)
    #     print(error_str)
    #     if self.error_handler:
    #         self.error_handler(error_str)

    def get_col(self, col: Col):
        return self.db[col.value]

    def get_model_data_list(self, table):
        """
        获取下拉框所需的model数据
        :param table: 数据表名
        :return:
        """
        col = self.db[table]
        query = col.find()
        if query:
            lists = [BaseData(x['value'], x['name']) for x in query]
            return lists

    def insert_image(self, image: MyImage):
        """
        保存图片分类信息，不包括 id，创建时间和更新时间
        :param image: 图片信息
        :return:
        """
        image.file_create_time = tzinfo.localize(image.file_create_time)
        di = image.di(True)
        return self.insert(Col.Image, di)

    def _check_item(self, item):
        if not isinstance(item, dict):
            item = item.__dict__.copy()
        if '_id' in item:
            del item['_id']
        if 'id' in item:
            del item['id']
        item['update_time'] = tzinfo.localize(datetime.now())
        return item

    def insert(self, col, item):
        item = self._check_item(item)
        item['create_time'] = tzinfo.localize(datetime.now())
        self.get_col(col).insert_one(item)

    def update_one(self, col, fl, item):
        item = self._check_item(item)
        self.get_col(col).update_one(fl, {'$set': item})

    def update_image(self, image: MyImage):
        """
        更新图片分类信息
        :param image: 图片信息
        :param conn: 图片信息
        :return: ObjectId
        """
        image.file_create_time = tzinfo.localize(image.file_create_time)
        image.update_time = tzinfo.localize(datetime.now())
        di = image.di()
        del di['create_time']
        fl = {'_id': image.id}
        return self.img_col.update_one(fl, {'$set': di})

    def update_path(self, img_id, relative_path):
        return self.img_col.update_one({'_id': img_id}, {'$set': {'path': relative_path}})

    def search_by_md5(self, md5):
        """
        根据md5搜索图片
        :param md5:
        :return:
        """
        query = self.img_col.find_one({'md5': md5})
        if query:
            return MyImage.from_dict(query)

    def search_by_file_path(self, filepath):
        """
        根据路径搜索图片
        :param filepath:
        :return:
        """
        query = self.img_col.find_one({'path': filepath})
        if query:
            return MyImage.from_dict(query)

    def get_id_by_path(self, filepath):
        query = self.img_col.find_one({'path': filepath}, {'_id': 1})
        if query:
            return query['_id']

    def delete(self, image_id):
        return self.img_col.delete_one({'_id': image_id})

    def search_one(self, col, fl, filed=None):
        if filed is None:
            filed = {}
        return self.db[col.value].find_one(fl, filed)

    def search_all(self, col, fl=None, filed=None):
        if fl is None:
            fl = {}
        if filed is None:
            filed = {}
        return self.db[col.value].find(fl, filed)

    def exist(self, col, fl):
        return self.search_one(col, fl, {'_id': 1}) is not None

    def search_by_filter(self, fl):
        image_sql_list = []
        image_file_list = []
        queries = self.img_col.find(fl)
        for query in queries:
            image_sql = MyImage.from_dict(query)
            image_sql_list.append(image_sql)

            path = image_sql.path
            tp_lists = path.split('/')
            image_file = ImageFile(image_sql.id, "%s/%s" % (tp_lists[-2], tp_lists[-1]), path)
            image_file_list.append(image_file)
        return image_sql_list, image_file_list

    def get_images(self, page, pagesize):
        queries = self.img_col.find().limit(pagesize).skip(page * pagesize)
        return [MyImage.from_dict(x) for x in queries]

    def get_count(self, fl=None):
        """
        获取图片总数
        :return:
        """
        if fl:
            return self.img_col.count_documents(fl)
        else:
            return self.img_col.estimated_document_count()

    def get_one_image_with_where(self, fl, offset):
        query = self.img_col.find_one(fl)
        if query:
            return MyImage.from_dict(query)

    def sync_server_data(self):
        config = ConfigHelper()
        dt = config.get_config_key('history', 'last_sync_time', None)
        if dt:
            dt = parser.parse(dt)
        else:
            dt = datetime.now(tzinfo)
        fl = {'update_time': {'$get': dt}}
        count = self.img_col.count_documents(fl)
        queries = self.img_col.find(fl)
        i = 0
        sever_img_col = pymongo.MongoClient(config.get_config_key('database', 'mongo'))['acg']['image']
        for query in queries:
            image = MyImage.from_dict(query)
            print(f'[{i}/{count}] {image.id}')
            local_image = self.search_by_md5(image.md5)
            if local_image:
                sever_img_col.update_one({'_id': image.id}, image.di())
            else:
                sever_img_col.insert_one(image.di(True))
