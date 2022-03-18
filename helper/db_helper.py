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
import datetime
import threading
import time
from enum import unique, Enum

import pymysql

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


class DBHelper:
    local_conn = None
    server_conn = None

    def __init__(self, error_handler):
        self.error_handler = error_handler
        self.lock = threading.Lock()
        # 本地数据库
        local_config = {
            'host': 'localhost',  # 地址
            'user': 'root',  # 用户名
            'passwd': '123',  # 密码
            'db': 'myacg',  # 使用的数据库名
            'charset': 'utf8',  # 编码类型
            'cursorclass': pymysql.cursors.DictCursor  # 按字典输出
        }
        self.local_conn = self._connect(local_config)

        # 线上数据库
        config_helper = ConfigHelper()
        section = 'database'
        server_config = {
            'host': config_helper.get_config_key(section, 'host'),  # 地址
            'user': config_helper.get_config_key(section, 'user'),  # 用户名
            'passwd': config_helper.get_config_key(section, 'password'),  # 密码
            'db': 'myacg',  # 使用的数据库名
            'charset': 'utf8mb4',  # 编码类型
            'cursorclass': pymysql.cursors.DictCursor  # 按字典输出
        }
        self.server_conn = self._connect(server_config)

    def _connect(self, config):
        try:
            conn = pymysql.connect(**config)
            conn.ping()
            return conn
        except pymysql.Error as error:
            print(f'{config} 数据库连接失败：{error}')

    def execute(self, sql_str, execute_type):
        if not self.local_conn and not self.server_conn:
            self.error_handler('没有数据库连接')
        res = None
        if execute_type == DBExecuteType.Run:
            # 写入时远程和本地都要写入，数据以远程为准
            res = self._execute_with_conn(sql_str, self.server_conn, execute_type)
            if not res:
                return res
            self._execute_with_conn(sql_str, self.local_conn, execute_type)
        elif execute_type in [DBExecuteType.FetchOne, DBExecuteType.FetchAll]:
            # 查询时如果本地有就不去查远程了，提高查询速度
            if self.local_conn:
                res = self._execute_with_conn(sql_str, self.local_conn, execute_type)
            else:
                res = self._execute_with_conn(sql_str, self.server_conn, execute_type)
        return res

    def _execute_with_conn(self, sql_str, conn, execute_type):
        if execute_type == DBExecuteType.Run:
            if conn == self.local_conn:
                type_str = '本地'
            else:
                type_str = '远程'
            print(f'连接类型：{type_str}，执行语句：\n{sql_str}')
        if not conn:
            print('连接不存在，停止执行')
            return False
        try:
            # 校验是否能连接成功
            self.lock.acquire()
            conn.ping(reconnect=True)
            cursor = conn.cursor()
            cursor.execute(sql_str)
            res = None
            if execute_type == DBExecuteType.Run:
                res = True
            elif execute_type == DBExecuteType.FetchAll:
                res = cursor.fetchall()
            elif execute_type == DBExecuteType.FetchOne:
                res = cursor.fetchone()
            conn.commit()
            self.lock.release()
            return res
        except pymysql.Error as error:
            self.lock.release()
            self.__show_error(error)
            if execute_type == DBExecuteType.Run:
                return False

    def __show_error(self, error):
        error_str = str(error)
        print(error_str)
        exit(1)
        if 'a foreign key constraint fails' in error_str:
            error_str = "有关联数据，不能删除！"
        if self.error_handler:
            self.error_handler(error_str)

    def get_model_data_list(self, table, where_str=None):
        """
        获取下拉框所需的model数据
        :param table: 数据表名
        :param where_str: 查询条件
        :return:
        """
        sql_str = f"select `name`,`value` from `{table}`"
        if where_str:
            sql_str += f" where {where_str}"
        sql_str += ";"
        query = self.execute(sql_str, execute_type=DBExecuteType.FetchAll)
        if query:
            lists = [BaseData(x['value'], x['name']) for x in query]
            return lists

    def insert_image(self, image: MyImage):
        """
        保存图片分类信息，不包括 id，创建时间和更新时间
        :param image: 图片信息
        :return:
        """
        # 替换单引号以保证插入
        desc = image.desc.replace("'", "\\'")
        author = image.author.replace("'", "\\'")
        tags = image.tags.replace("'", "\\'")
        works = image.works.replace("'", "\\'")
        role = image.role.replace("'", "\\'")
        path = image.relative_path.replace("'", "\\'")
        series = image.series.replace("'", "\\'")
        uploader = image.uploader.replace("'", "\\'")
        sql_str = f"""INSERT INTO myacg.image(`desc`, author, type, level, tags, works, role, source, 
path, width, height, `size`, file_create_time, series, uploader, md5, sequence) values ('{desc}', '{author}',
{image.type}, {image.level}, '{tags}', '{works}', '{role}', '{image.source}', '{path}',
{image.width}, {image.height}, {image.size}, '{image.file_create_time}', '{series}', '{uploader}', '{image.md5}',
{image.sequence});"""
        return self.execute(sql_str, execute_type=DBExecuteType.Run)

    def insert_full_image(self, image: MyImage, conn):
        """
        保存全部的图片分类信息
        :param image: 图片信息
        :param conn: 要写入的数据库
        :return:
        """
        # 替换单引号以保证插入
        desc = image.desc.replace("'", "\\'")
        author = image.author.replace("'", "\\'")
        tags = image.tags.replace("'", "\\'")
        works = image.works.replace("'", "\\'")
        role = image.role.replace("'", "\\'")
        path = image.relative_path.replace("'", "\\'")
        series = image.series.replace("'", "\\'")
        uploader = image.uploader.replace("'", "\\'")
        sql_str = f"""INSERT INTO myacg.image(id, `desc`, author, type, level, tags, works, role, source, 
path, width, height, `size`, file_create_time, series, uploader, md5, sequence, create_time, update_time) values 
({image.id}, '{desc}', '{author}', {image.type}, {image.level}, '{tags}', '{works}', '{role}', '{image.source}',
 '{path}', {image.width}, {image.height}, {image.size}, '{image.file_create_time}', '{series}', '{uploader}',
  '{image.md5}', {image.sequence}, '{image.create_time}', '{image.update_time}');"""
        return self.execute(sql_str, execute_type=DBExecuteType.Run)

    def update_image(self, image: MyImage, conn=None):
        """
        更新图片分类信息
        :param image: 图片信息
        :param conn: 图片信息
        :return:
        """
        # 替换单引号以保证插入
        desc = image.desc.replace("'", "\\'")
        author = image.author.replace("'", "\\'")
        tags = image.tags.replace("'", "\\'")
        works = image.works.replace("'", "\\'")
        role = image.role.replace("'", "\\'")
        path = image.relative_path.replace("'", "\\'")
        series = image.series.replace("'", "\\'")
        if image.uploader:
            uploader = image.uploader.replace("'", "\\'")
        else:
            uploader = ''
        sql_str = f"""update myacg.image set `desc`='{desc}',author='{author}', type={image.type},
            level={image.level}, tags='{tags}', works='{works}', role='{role}', source='{image.source}',
            path='{path}', md5='{image.md5}', width={image.width}, height={image.height},
            `size`={image.size}, file_create_time='{image.file_create_time}', series='{series}', uploader='{uploader}',
            sequence={image.sequence} where id={image.id}"""
        if conn:
            return self._execute_with_conn(sql_str, conn, DBExecuteType.Run)
        else:
            return self.execute(sql_str, execute_type=DBExecuteType.Run)

    def update_path(self, img_id, relative_path):
        path = relative_path.replace("'", "\\'")
        return self.execute(f"update myacg.image set path='{path}' where id={img_id}", execute_type=DBExecuteType.Run)

    def search_by_md5(self, md5):
        """
        根据md5搜索图片
        :param md5:
        :return:
        """
        sql_str = f"select * from myacg.image where md5='{md5}' limit 1"
        query = self.execute(sql_str, execute_type=DBExecuteType.FetchOne)
        if query:
            return MyImage.from_mysql_dict(query)

    def search_by_file_path(self, file_path, conn=None):
        """
        根据路径搜索图片
        :param file_path:
        :param conn:
        :return:
        """
        file_path = file_path.replace("'", "\\'")
        sql_str = f"select * from myacg.image where path='{file_path}' limit 1"
        if conn:
            query = self._execute_with_conn(sql_str, conn, DBExecuteType.FetchOne)
        else:
            query = self.execute(sql_str, execute_type=DBExecuteType.FetchOne)
        if query:
            return MyImage.from_mysql_dict(query)

    def get_id_by_path(self, file_path):
        file_path = file_path.replace("'", "\\'")
        sql_str = f"select id from myacg.image where path='{file_path}' limit 1"
        query = self.execute(sql_str, execute_type=DBExecuteType.FetchOne)
        if query:
            return query['id']
        else:
            return 0

    def delete(self, image_id):
        sql_str = f"delete from myacg.image where id={image_id}"
        self.execute(sql_str, execute_type=DBExecuteType.Run)

    def search_by_where(self, sql_where):
        image_sql_list = []
        image_file_list = []
        sql_str = f"select * from myacg.image where {sql_where}"
        queries = self.execute(sql_str, execute_type=DBExecuteType.FetchAll)
        if not isinstance(queries, list):
            return image_sql_list, image_file_list
        for query in queries:
            image_sql = MyImage.from_mysql_dict(query)
            image_sql_list.append(image_sql)

            path = image_sql.path
            tp_lists = path.split('/')
            image_file = ImageFile(image_sql.id, "%s/%s" % (tp_lists[-2], tp_lists[-1]), path)
            image_file_list.append(image_file)
        return image_sql_list, image_file_list

    def get_images(self, page, pagesize):
        sql_str = f"select * from myacg.image limit {pagesize} offset {page * pagesize};"
        queries = self.execute(sql_str, DBExecuteType.FetchAll)
        image_sql_list = []
        for query in queries:
            image_sql = MyImage.from_mysql_dict(query)
            image_sql_list.append(image_sql)
        return image_sql_list

    def get_table_count(self, count_sql):
        """
        获取总数
        :param count_sql: 统计sql语句
        :return:
        """
        count = 0
        query = self.execute(count_sql, DBExecuteType.FetchOne)
        if query:
            for key, value in query.items():
                count = value
                break
        return count

    def get_image_count(self, sql_where):
        """
        获取图片总数
        :return:
        """
        return self.get_table_count(f"select count(*) from myacg.image where {sql_where};")

    def get_one_image_with_where(self, sql_where, offset):
        sql = f"select * from myacg.image where {sql_where} limit 1 offset {offset};"
        query = self.execute(sql, DBExecuteType.FetchOne)
        if query:
            return MyImage.from_mysql_dict(query)

    def sync_data(self, source_conn, dest_conn):
        date = datetime.datetime.now()
        sql = f"select * from myacg.image where update_time>'{date}'"
        queries = self._execute_with_conn(sql, source_conn, DBExecuteType.FetchAll)
        for i, query in enumerate(queries):
            image = MyImage.from_mysql_dict(query)
            print(f'[{i}/{len(queries)}] {image.id}')
            local_image = self.search_by_file_path(image.relative_path, dest_conn)
            if local_image:
                self.update_image(image, dest_conn)
            else:
                self.insert_full_image(image, dest_conn)

