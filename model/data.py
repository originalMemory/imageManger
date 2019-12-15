#!/user/bin/env python
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : data
@author  : wuhoubo
@desc    : 所有数据类
@create  : 2019/9/21 15:05:36
@update  :
"""
import datetime
from dataclasses import dataclass

from PyQt5.QtGui import QPixmap


@dataclass
class MyImage:
    """
    Mysql 中 image 表的数据类型映射
    """
    id: int
    desc: str
    author: str
    """
    类型 id
    """
    type_id: int
    """
    等级 id
    """
    level_id: int
    """
    标签
    """
    tags: str
    """
    作品
    """
    works: str
    """
    角色
    """
    role: str
    """
    来源站点
    """
    source: str
    width: int
    height: int
    size: float
    filename: str
    path: str
    """
    文件创建时间
    """
    file_create_time: datetime
    """
    信息创建时间
    """
    create_time: datetime
    """
    信息更新时间
    """
    update_time: datetime
    """
    系列
    """
    series: str
    """
    上传者
    """
    uploader: str

    @staticmethod
    def from_mysql_dict(query):
        image = MyImage(
            id=query['id'],
            desc=query['desc'],
            author=query['author'],
            type_id=query['type_id'],
            level_id=query['level_id'],
            tags=query['tags'],
            works=query['works'],
            role=query['role'],
            source=query['source'],
            width=query['width'],
            height=query['height'],
            size=query['size'],
            filename=query['filename'],
            path=query['path'],
            file_create_time=query['file_create_time'],
            create_time=query['create_time'],
            update_time=query['update_time'],
            series=query['series'],
            uploader=query['uploader']
        )
        return image


@dataclass
class BaseData:
    id: int = 0
    name: str = ""


@dataclass
class ImageFile(BaseData):
    full_path: str = ""


@dataclass
class PreloadImage:
    full_path: str
    pixmap: QPixmap
