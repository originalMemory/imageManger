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
from dataclasses import dataclass, field
from datetime import datetime

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QAction
from screeninfo import Monitor

from helper.file_helper import FileHelper


@dataclass
class MyImage:
    """
    Mysql 中 image 表的数据类型映射
    """
    id: int = field(default=0)
    desc: str = field(default="")
    author: str = field(default="")
    """
    类型 id
    """
    type_id: int = field(default=0)
    """
    等级 id
    """
    level_id: int = field(default=0)
    """
    标签
    """
    tags: str = field(default="")
    """
    作品
    """
    works: str = field(default="")
    """
    角色
    """
    role: str = field(default="")
    """
    来源站点
    """
    source: str = field(default="")
    width: int = field(default=0)
    height: int = field(default=0)
    size: float = field(default=0.0)
    filename: str = field(default="")
    dir_path: str = field(default="")
    """
    作品序号，用于快速对比合集资源
    """
    sequence: int = field(default=0)
    path: str = field(default="")
    relative_path: str = field(default="")
    md5: str = field(default="")
    """
    文件创建时间
    """
    file_create_time: datetime = field(default=datetime.now())
    """
    信息创建时间
    """
    create_time: datetime = field(default=datetime.now())
    """
    信息更新时间
    """
    update_time: datetime = field(default=datetime.now())
    """
    系列
    """
    series: str = field(default="")
    """
    上传者
    """
    uploader: str = field(default="")

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
            dir_path=query['dir_path'],
            sequence=query['sequence'],
            relative_path=query['path'],
            md5=query['md5'],
            file_create_time=query['file_create_time'],
            create_time=query['create_time'],
            update_time=query['update_time'],
            series=query['series'],
            uploader=query['uploader']
        )
        image.path = FileHelper.get_full_path(image.relative_path)
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


@dataclass
class MonitorSetting:
    monitor: Monitor
    image_desc_action: QAction
    image_level_actions: list
    image: MyImage = None
