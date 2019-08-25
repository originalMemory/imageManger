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


def check_kind(table, name, id=0):
    """
    检查种类是否存在
    :param table: 表名
    :param name: 种类名
    :param id: 编号。默认为0，此时检查所有名称。不为0时检查除该种类外的所有名称
    :return:
    """
    if id == 0:
        sql_str = f"select * from `{table}` where `name`='{name}';"
    else:
        sql_str = f"select * from `{table}` where `name`='{name}' and `id`!={id};"
    query.exec_(sql_str)
    if query.next():
        return True
    else:
        return False


def add_kind(table, name, id):
    """
    添加种类
    :param table: 表名
    :param name: 种类名
    :param id: 编号
    :return:
    """
    sql_str = f"INSERT INTO `{table}`(`name`, `user_id`) values ('{name}', {id})"
    # print(sql_str)
    query.exec_(sql_str)

def classify(id, filename, path):
    if id == 0:
        pass


def delete_kind(table, ids):
    """
    删除种类
    :param table: 表名
    :param ids: 编号列表
    :return:
    """
    ids_str = ",".join(ids)
    if not query.exec_(f"delete from `{table}` where `id` in ({ids_str})"):
        err_text = query.lastError().text()
        if 'a foreign key constraint fails' in err_text:
            return 2
    return 1


def update_kind(table, id, name):
    """
    更新种类名称
    :param table: 表名
    :param id: 编号
    :param name: 名称
    :return:
    """
    sql_str = f"update `{table}` set `name`='{name}' where `id`={id};"
    query.exec_(sql_str)


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