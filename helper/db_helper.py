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
    SimilarImage = 'similar_image'


@unique
class DBType(Enum):
    Local = 0
    Server = 1


tzinfo = pytz.timezone('Asia/Shanghai')


class DBHelper:
    def __init__(self, error_handler, with_server=False):
        self.error_handler = error_handler

    _cache = {}

    def _get_db(self, db_type):
        if db_type == DBType.Server:
            url = ConfigHelper().get_config_key('database', 'mongoServer')
        else:
            url = ConfigHelper().get_config_key('database', 'mongoLocal')
        if url in self._cache:
            return self._cache[url]
        else:
            db = pymongo.MongoClient(url, tz_aware=True, tzinfo=tzinfo)['acg']
            self._cache[url] = db
            return db

    # def __show_error(self, error):
    #     error_str = str(error)
    #     print(error_str)
    #     if self.error_handler:
    #         self.error_handler(error_str)

    def get_col(self, db_type: DBType, col: Col):
        return self._get_db(db_type)[col.value]

    def get_model_data_list(self, table):
        """
        获取下拉框所需的model数据
        :param table: 数据表名
        :return:
        """
        col = self._get_search_db()[table]
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

    @staticmethod
    def _check_item(item):
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
        server = self._get_db(DBType.Server)
        if server:
            server[col.value].insert_one(item)
        local = self._get_db(DBType.Local)
        if local:
            local[col.value].insert_one(item)

    def update_one(self, col, fl, item):
        item = self._check_item(item)
        set_di = {'$set': item}
        server = self._get_db(DBType.Server)
        if server:
            server[col.value].update_one(fl, set_di)
        local = self._get_db(DBType.Local)
        if local:
            local[col.value].update_one(fl, set_di)

    def update_many(self, col, fl, item):
        item = self._check_item(item)
        set_di = {'$set': item}
        server = self._get_db(DBType.Server)
        if server:
            server[col.value].update_many(fl, set_di)
        local = self._get_db(DBType.Local)
        if local:
            local[col.value].update_many(fl, set_di)

    def update_image(self, image: MyImage):
        """
        更新图片分类信息
        :param image: 图片信息
        :return: ObjectId
        """
        image.file_create_time = tzinfo.localize(image.file_create_time)
        return self.update_one(Col.Image, {'_id': image.id}, image)

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
        query = self.search_one(Col.Image, {'path': filepath})
        if query:
            return MyImage.from_dict(query)

    def get_id_by_path(self, filepath):
        query = self.search_one(Col.Image, {'path': filepath}, {'_id': 1})
        if query:
            return query['_id']

    def delete(self, image_id):
        fl = {'_id': image_id}
        server = self._get_db(DBType.Server)
        if server:
            server[Col.Image.value].delete_one(fl)
        local = self._get_db(DBType.Local)
        if local:
            local[Col.Image.value].delete_one(fl)

    def _get_search_db(self):
        local = self._get_db(DBType.Server)
        if local:
            return local
        else:
            return self._get_db(DBType.Server)

    def search_one(self, col, fl, filed=None):
        if not fl:
            fl = {}
        return self._get_search_db()[col.value].find_one(fl, filed)

    def search_all(self, col, fl=None, filed=None):
        if not fl:
            fl = {}
        return self._get_search_db()[col.value].find(fl, filed)

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
            image_file = ImageFile(image_sql.id, "%s/%s" % (tp_lists[-2], tp_lists[-1]), path)
            image_file_list.append(image_file)
        return image_sql_list, image_file_list

    def get_images(self, page, pagesize):
        queries = self._get_search_db()[Col.Image.value].find().limit(pagesize).skip(page * pagesize)
        return [MyImage.from_dict(x) for x in queries]

    def get_count(self, fl=None):
        """
        获取图片总数
        :return:
        """

        col = self._get_search_db()[Col.Image.value]
        if fl:
            return col.count_documents(fl)
        else:
            return col.estimated_document_count()
