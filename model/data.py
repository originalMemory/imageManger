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
from enum import unique, Enum

from PyQt6.QtGui import QPixmap, QAction
from bson import ObjectId
from screeninfo import Monitor

from helper.file_helper import FileHelper


@unique
class TagType(Enum):
    Empty = ''
    Label = 'label'
    Role = 'role'
    Works = 'works'
    Company = 'company'
    Author = 'author'
    Unknown = 'unknown'


@dataclass
class TranSource:
    id: ObjectId = field(default=None)
    name: str = field(default="")
    dest_ids: str = field(default="")
    create_time: datetime = field(default=datetime.now())
    update_time: datetime = field(default=datetime.now())

    @staticmethod
    def from_dict(query):
        item = TranSource(
            id=query['_id'],
            name=query['name'],
            dest_ids=query['dest_ids'],
            create_time=query['create_time'],
            update_time=query['update_time'],
        )
        return item


@dataclass
class TranDest:
    id: ObjectId = field(default=None)
    name: str = field(default="")
    type: TagType = field(default=TagType.Label)
    extra: str = field(default=None)
    create_time: datetime = field(default=datetime.now())
    update_time: datetime = field(default=datetime.now())

    @staticmethod
    def from_dict(query):
        item = TranDest(
            id=query['_id'],
            name=query['name'],
            type=TagType(query['type']),
            extra=query['name'],
            create_time=query['create_time'],
            update_time=query['update_time'],
        )
        return item

    def get_pixiv_url(self):
        if self.type == TagType.Author and self.extra:
            return f'https://www.pixiv.net/users/{self.extra}'


@dataclass
class MyImage:
    """
    Mysql 中 image 表的数据类型映射
    """
    id: ObjectId = field(default=None)
    desc: str = field(default="")
    author: str = field(default="")
    """
    类型
    """
    type: int = field(default=0)
    """
    等级
    """
    level: int = field(default=0)
    """
    标签
    """
    tags: list = field(default_factory=list)
    """
    作品
    """
    works: list = field(default_factory=list)
    """
    角色
    """
    roles: list = field(default_factory=list)
    """
    来源站点
    """
    source: str = field(default="")
    width: int = field(default=0)
    height: int = field(default=0)
    size: float = field(default=0.0)
    """
    作品序号，用于快速对比合集资源
    """
    sequence: int = field(default=0)
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
    """
    本地字段，本地地址
    """
    path: str = field(default="")

    @staticmethod
    def from_dict(query):
        image = MyImage(
            id=query['_id'],
            desc=query['desc'],
            author=query['author'],
            type=query['type'],
            level=query['level'],
            tags=query['tags'],
            works=query['works'],
            roles=query['roles'],
            source=query['source'],
            width=query['width'],
            height=query['height'],
            size=query['size'],
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

    def di(self, with_id=False):
        di = self.__dict__.copy()
        del di['id']
        if not with_id:
            di['_id'] = self.id
        return di


@dataclass
class BaseData:
    id: ObjectId = None
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
