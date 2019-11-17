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
import pymysql
from PyQt5.QtWidgets import QMessageBox

from model.data import MyImage, BaseData, ImageFile


class DBHelper:
    config = {
        'host': 'localhost',  # 地址
        'user': 'root',  # 用户名
        'passwd': '123',  # 密码
        'db': 'myacg',  # 使用的数据库名
        'charset': 'utf8',  # 编码类型
        'cursorclass': pymysql.cursors.DictCursor  # 按字典输出
    }

    def __init__(self, context):
        self.context = context

    def execute(self, sql_str):
        connect = None
        is_success = True
        try:
            connect = pymysql.connect(**self.config)
            cursor = connect.cursor()
            cursor.execute(sql_str)
            connect.commit()
        except pymysql.Error as error:
            self.__show_error(error)
            is_success = False
        finally:
            if connect:
                connect.close()
        return is_success

    def execute_many(self, sql_str, val):
        connect = None
        is_success = True
        try:
            connect = pymysql.connect(**self.config)
            cursor = connect.cursor()
            cursor.executemany(sql_str, val)
            connect.commit()
        except pymysql.Error as error:
            self.__show_error(error)
            is_success = False
        finally:
            if connect:
                connect.close()
        return is_success

    def query_with_return_all(self, sql_str):
        connect = None
        query = None
        try:
            connect = pymysql.connect(**self.config)
            cursor = connect.cursor()
            cursor.execute(sql_str)
            query = cursor.fetchall()
        except pymysql.Error as error:
            self.__show_error(error)
        finally:
            if connect:
                connect.close()
        return query

    def query_with_return_one(self, sql_str):
        connect = None
        query = None
        try:
            connect = pymysql.connect(**self.config)
            cursor = connect.cursor()
            cursor.execute(sql_str)
            query = cursor.fetchone()
        except pymysql.Error as error:
            self.__show_error(error)
        finally:
            if connect:
                connect.close()
        return query

    def __show_error(self, error):
        error_str = str(error)
        if 'a foreign key constraint fails' in error_str:
            error_str = "有关联数据，不能删除！"
        QMessageBox.information(self.context, "提示", error_str, QMessageBox.Ok)

    def get_model_data_list(self, table, where_str=None):
        """
        获取下拉框所需的model数据
        :param table: 数据表名
        :param where_str: 查询条件
        :return:
        """
        sql_str = f"select `id`,`name` from `{table}`"
        if where_str:
            sql_str += f" where {where_str}"
        sql_str += ";"
        query = self.query_with_return_all(sql_str)
        lists = [BaseData(x['id'], x['name']) for x in query]
        return lists

    def insert_image(
            self,
            desc,
            author,
            type_id,
            level_id,
            tags,
            works,
            role,
            source,
            filename,
            path,
            width,
            height,
            size,
            create_time,
            series,
            uploader
    ):
        """
        保存图片分类信息
        :param desc: 描述
        :param author: 作者
        :param type_id: 类型 id
        :param level_id: 等级 id
        :param tags: 标签列表，用逗号分隔
        :param works: 来源作品
        :param role: 角色
        :param source: 来源站点
        :param filename: 文件名
        :param path: 文件路径
        :param width: 图片宽度
        :param height: 图片高度
        :param size: 文件大小
        :param create_time: 文件创建时间
        :param series: 系列
        :param uploader: 上传者
        :return:
        """
        # 替换单引号以保证插入
        desc = desc.replace("'", "\\'")
        author = author.replace("'", "\\'")
        tags = tags.replace("'", "\\'")
        works = works.replace("'", "\\'")
        role = role.replace("'", "\\'")
        filename = filename.replace("'", "\\'")
        path = path.replace("'", "\\'")
        series = series.replace("'", "\\'")
        uploader = uploader.replace("'", "\\'")
        sql_str = f"""INSERT INTO myacg.image(`desc`, author, type_id, level_id, tags, works, role, source, filename, 
            path, width, height, `size`, file_create_time, series, uploader) values ('{desc}', '{author}', {type_id}, 
            {level_id}, '{tags}', '{works}', '{role}', '{source}', '{filename}', '{path}', {width}, {height}, {size}, 
            '{create_time}', '{series}', '{uploader}');"""
        print(sql_str)
        self.execute(sql_str)

    def update_image(
            self,
            image_id,
            desc,
            author,
            type_id,
            level_id,
            tags,
            works,
            role,
            source,
            filename,
            path,
            width,
            height,
            size,
            create_time,
            series,
            uploader
    ):
        """
        保存图片分类信息
        :param image_id: 图片 id
        :param desc: 描述
        :param author: 作者
        :param type_id: 类型 id
        :param level_id: 等级 id
        :param tags: 标签列表，用逗号分隔
        :param works: 来源作品
        :param role: 角色
        :param source: 来源站点
        :param filename: 文件名
        :param path: 文件路径
        :param width: 图片宽度
        :param height: 图片高度
        :param size: 文件大小
        :param create_time: 文件创建时间
        :param series: 系列
        :param uploader: 上传者
        :return:
        """
        # 替换单引号以保证插入
        desc = desc.replace("'", "\\'")
        author = author.replace("'", "\\'")
        tags = tags.replace("'", "\\'")
        works = works.replace("'", "\\'")
        role = role.replace("'", "\\'")
        filename = filename.replace("'", "\\'")
        path = path.replace("'", "\\'")
        series = series.replace("'", "\\'")
        uploader = uploader.replace("'", "\\'")
        sql_str = f"""update myacg.image set `desc`='{desc}',author='{author}', type_id={type_id}, level_id={level_id}, 
            tags='{tags}', works='{works}', role='{role}', source='{source}', filename='{filename}', path='{path}', 
            width={width}, height={height}, `size`={size}, file_create_time='{create_time}', series='{series}', 
            uploader='{uploader}' where id={image_id}"""
        self.execute(sql_str)

    def search_by_file_path(self, file_path):
        """
        根据路径搜索图片
        :param file_path:
        :return:
        """
        info = None
        file_path = file_path.replace("'", "\\'")
        sql_str = f"select * from myacg.image where path='{file_path}' limit 1"
        query = self.query_with_return_one(sql_str)
        if query:
            info = MyImage.from_mysql_dict(query)
        return info

    def get_id_by_path(self, file_path):
        file_path = file_path.replace("'", "\\'")
        sql_str = f"select id from myacg.image where path='{file_path}' limit 1"
        query = self.query_with_return_one(sql_str)
        if query:
            return query['id']
        else:
            return 0

    def delete(self, image_id):
        sql_str = f"delete from myacg.image where id={image_id}"
        self.execute(sql_str)

    def search_by_where(self, sql_where):
        image_sql_list = []
        image_file_list = []
        sql_str = f"select * from myacg.image where {sql_where}"
        queries = self.query_with_return_all(sql_str)
        for query in queries:
            image_sql = MyImage.from_mysql_dict(query)
            image_sql_list.append(image_sql)

            path = image_sql.path
            tp_lists = path.split('/')
            image_file = ImageFile(image_sql.id, "%s/%s" % (tp_lists[-2], tp_lists[-1]), path)
            image_file_list.append(image_file)
        return image_sql_list, image_file_list
