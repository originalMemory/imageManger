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

import hashlib

from PyQt5 import QtSql
from PyQt5.QtSql import QSqlQuery

from model.data import MyImage

query = QSqlQuery()  # 全局变量，用于与mysql交互


def init():
    # 连接数据库
    db = QtSql.QSqlDatabase.addDatabase('QMYSQL')
    db.setHostName('localhost')
    db.setUserName('root')
    db.setPassword('123')
    db.open()
    global query
    query = QSqlQuery()

    # 检查数据库，不存在则创建
    database_name = "myacg"
    if not exist_database(database_name):
        query.exec_(f"CREATE DATABASE {database_name};")
        print("创建数据库成功！")
    query.exec_(f"use {database_name};")

    # # 检查表，不存在则创建
    # table_names = get_all_table_name()
    # table_name = "image"
    # if table_name not in table_names:
    #     query.exec_(f"CREATE TABLE if not exists `{table_name}`("
    #                 "  `id` int(11) NOT NULL," \
    #                 "  `desc` varchar(255) DEFAULT NULL COMMENT '描述'," \
    #                 "  `author` varchar(255) DEFAULT NULL COMMENT '作者'," \
    #                 "  `tags` varchar(1000) DEFAULT NULL COMMENT '标签'," \
    #                 "  `works` varchar(255) DEFAULT NULL COMMENT '来源作品'," \
    #                 "  `publish_time` datetime DEFAULT NULL COMMENT '发布时间'," \
    #                 "  `level` smallint(1) DEFAULT '0' COMMENT '等级。-1为模糊，0为阴，1为奶，2为内衣，3为全身，4为头像'," \
    #                 "  `source` varchar(255) DEFAULT NULL COMMENT '来源站点'," \
    #                 "  `path` varchar(255) DEFAULT NULL COMMENT '文件路径'," \
    #                 "  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'," \
    #                 "  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'," \
    #                 "  PRIMARY KEY (`id`)" \
    #                 ") ENGINE=InnoDB DEFAULT CHARSET=utf8;")
    #     print("创建用户表功！")


def exist_database(name):
    """
    判断是否存在该数据库
    :param name: 数据库名称
    :return:
    """
    query.exec_("show databases;")
    while query.next():
        if name == query.value(0):
            return True
    return False


def get_all_table_name():
    """
    获取所有表名
    :return:
    """
    query.exec_("show tables;")
    lists = []
    while query.next():
        lists.append(query.value(0))
    return lists


def get_model_data_list(table, where_str=None):
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
    query.exec_(sql_str)
    lists = []
    while query.next():
        li = {
            "id": query.value(0),
            "name": query.value(1)
        }
        lists.append(li)
    query.finish()
    return lists


def insert_image(
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
        create_time
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
    :return:
    """
    sql_str = f"INSERT INTO myacg.image(`desc`, author, type_id, level_id, tags, works, role, source, filename, path," \
        f" width, height, `size`, file_create_time) values ('{desc}', '{author}', {type_id}, {level_id}, '{tags}'," \
        f" '{works}', '{role}', '{source}', '{filename}', '{path}', {width}, {height}, {size}, '{create_time}');"
    query.exec_(sql_str)


def search(file_path):
    """
    根据路径搜索图片
    :param file_path:
    :return:
    """
    info = None
    sql_str = f"select * from myacg.image where path='{file_path}' limit 1"
    query.exec_(sql_str)
    if query.next():
        info = MyImage(
            id=query.value('id'),
            desc=query.value('desc'),
            author=query.value('author'),
            type_id=query.value('type_id'),
            level_id=query.value('level_id'),
            tags=query.value('tags'),
            works=query.value('works'),
            role=query.value('role'),
            source=query.value('source'),
            width=query.value('width'),
            height=query.value('height'),
            size=query.value('size'),
            filename=query.value('filename'),
            path=query.value('path'),
            file_create_time=query.value('file_create_time'),
            create_time=query.value('create_time'),
            update_time=query.value('update_time')
        )
        query.finish()
    return info


def exist_by_path(file_path):
    exist = False
    sql_str = f"select id from myacg.image where path='{file_path}' limit 1"
    query.exec_(sql_str)
    if query.next():
        exist = True
        query.finish()
    return exist
