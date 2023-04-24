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
from typing import TypeVar, Type

import pymongo
import pytz
from bson import ObjectId
from dacite import from_dict
from pymongo.collection import Collection

from helper.config_helper import ConfigHelper
from helper.file_helper import FileHelper
from model.data import MyImage, BaseData, ImageFile, Tag, Col


def get_time(f):
    def inner(*arg, **kwarg):
        s_time = time.time()
        res = f(*arg, **kwarg)
        e_time = time.time()
        print('耗时：{}秒'.format(e_time - s_time))
        return res

    return inner


T = TypeVar('T')


@unique
class DBExecuteType(Enum):
    Run = 0
    FetchAll = 1
    FetchOne = 2


tzinfo = pytz.timezone('Asia/Shanghai')


def _get_local_dt(dt):
    return tzinfo.localize(dt)


class DBHelper:
    def __init__(self, error_handler, with_server=False):
        self.error_handler = error_handler
        url = ConfigHelper().get_config_key('database', 'mongoServer')
        self._client = pymongo.MongoClient(url, tz_aware=True, tzinfo=tzinfo)
        self._db = self._client['acg']

    def __del__(self):
        self._client.close()

    def get_col(self, col: Col) -> Collection:
        return self._db[col.value]

    def get_model_data_list(self, table):
        """
        获取下拉框所需的model数据
        :param table: 数据表名
        :return:
        """
        col = self._db[table]
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
        di = image.dict()
        return self.insert(Col.Image, di)

    @staticmethod
    def _check_item(item):
        if not isinstance(item, dict):
            item = item.__dict__.copy()
        if '_id' in item:
            del item['_id']
        if 'id' in item:
            del item['id']
        if 'category_id' in item and item['category_id'] is None:
            del item['category_id']
        item['update_time'] = tzinfo.localize(datetime.now())
        return item

    def insert(self, col, item):
        item = self._check_item(item)
        item['create_time'] = tzinfo.localize(datetime.now())
        return self._db[col.value].insert_one(item)

    def update_one(self, col, fl, item):
        item = self._check_item(item)
        set_di = {'$set': item}
        return self._db[col.value].update_one(fl, set_di)

    def update_many(self, col, fl, item):
        item = self._check_item(item)
        set_di = {'$set': item}
        return self._db[col.value].update_many(fl, set_di)

    def update_image(self, image: MyImage):
        """
        更新图片分类信息
        :param image: 图片信息
        :return: ObjectId
        """
        image.file_create_time = tzinfo.localize(image.file_create_time)
        return self.update_one(Col.Image, {'_id': image.id()}, image)

    def update_path(self, img_id, relative_path):
        return self.update_one(Col.Image, {'_id': img_id}, {'path': relative_path})

    def search_by_md5(self, md5):
        """
        根据md5搜索图片
        :param md5:
        :return:
        """
        query = self.search_one(Col.Image, {'md5': md5})
        if query:
            return MyImage.from_dict(query)

    def search_by_file_path(self, filepath):
        """
        根据路径搜索图片
        :param filepath:
        :return:
        """
        relative_path = FileHelper.get_relative_path(filepath)
        query = self.search_one(Col.Image, {'path': relative_path})
        if query:
            return MyImage.from_dict(query)

    def get_id_by_path(self, filepath):
        query = self.search_one(Col.Image, {'path': filepath}, {'_id': 1})
        if query:
            return query['_id']

    def delete(self, image_id):
        fl = {'_id': image_id}
        self._db[Col.Image.value].delete_one(fl)

    def search_one(self, col, fl, filed=None):
        if not fl:
            fl = {}
        return self._db[col.value].find_one(fl, filed)

    def search_all(self, col, fl=None, filed=None):
        if not fl:
            fl = {}
        return self._db[col.value].find(fl, filed)

    def exist(self, col, fl):
        return self.search_one(col, fl, {'_id': 1}) is not None

    def search_by_filter(self, fl):
        image_sql_list = []
        image_file_list = []
        # fl = {'type': 1, '$where': 'this.works.length>0'}
        queries = self.search_all(Col.Image, fl).sort('create_time', pymongo.DESCENDING).limit(2000)
        for query in queries:
            image_sql = MyImage.from_dict(query)
            image_sql_list.append(image_sql)

            path = image_sql.full_path()
            tp_lists = path.split('/')
            image_file = ImageFile(image_sql.id(), "%s/%s" % (tp_lists[-2], tp_lists[-1]), path)
            image_file_list.append(image_file)
        return image_sql_list, image_file_list

    def get_images(self, page, pagesize):
        queries = self._db[Col.Image.value].find().limit(pagesize).skip(page * pagesize)
        return [MyImage.from_dict(x) for x in queries]

    def get_count(self, fl=None):
        """
        获取图片总数
        :return:
        """

        col = self._db[Col.Image.value]
        if fl:
            return col.count_documents(fl)
        else:
            return col.estimated_document_count()

    def find(self, col, fl=None, filed=None):
        if fl is None:
            fl = {}
        return self._db[col.value].find(fl, filed)

    def find_decode(self, data_class: Type[T], fl=None, limit=0) -> [T]:
        col = Col.from_dataclass(data_class)
        if not col:
            raise f'{data_class}没有对应的表'
        find = self.find(col, fl)
        if limit:
            find = find.limit(limit)
        return [from_dict(data_class=data_class, data=x) for x in find]

    def find_one(self, col, fl=None, filed=None):
        if fl is None:
            fl = {}
        return self._db[col.value].find_one(fl, filed)

    def find_one_decode(self, dataclass: Type[T], fl) -> T:
        cursor = self.find_one(Col.from_dataclass(dataclass), fl)
        if cursor:
            if 'category_id' in cursor and cursor['category_id'] is None:
                del cursor['category_id']
            return from_dict(data_class=dataclass, data=cursor)

    def find_or_create_tag(self, name, source, tran='') -> Tag:
        fl = {'$or': [{'name': name}, {'alias': name}]}
        tag = self.find_one_decode(Tag, fl)
        if tag:
            return tag
        self.insert(Col.Tag, Tag(name=name, source=source.value, tran=tran))
        return self.find_one_decode(Tag, fl)

    def delete_one(self, col, item_id):
        fl = {'_id': item_id}
        self._db[col.value].delete_one(fl)

    def update_one_by_id(self, col, obj_id, data):
        if isinstance(obj_id, str):
            obj_id = ObjectId(obj_id)
        data['update_time'] = _get_local_dt(datetime.now())
        self.update_one_by_data(col, {'_id': obj_id}, data)

    def update_one_by_data(self, col, fl, data):
        self.base_update_one(col, fl, {'$set': data})

    def base_update_one(self, col, fl, data):
        self._db[col.value].update_one(fl, data)

