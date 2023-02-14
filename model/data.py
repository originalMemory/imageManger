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

import pytz
from PyQt6.QtGui import QPixmap, QAction
from bson import ObjectId
from screeninfo import Monitor

from helper.file_helper import FileHelper

tzinfo = pytz.timezone('Asia/Shanghai')

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
    dest_ids: list = field(default_factory=list)
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
            extra=query['extra'],
            create_time=query['create_time'],
            update_time=query['update_time'],
        )
        return item

    def di(self):
        d = self.__dict__.copy()
        d['type'] = self.type.value
        return d

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
    authors: list = field(default_factory=list)
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
    地址
    """
    path: str = field(default="")
    color: str = field(default='')

    @staticmethod
    def from_dict(query):
        image = MyImage(
            id=query['_id'],
            desc=query['desc'],
            authors=query['authors'],
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
            path=query['path'],
            md5=query['md5'],
            file_create_time=query['file_create_time'],
            create_time=query['create_time'],
            update_time=query['update_time'],
            series=query['series'],
            uploader=query['uploader']
        )
        if 'color' in query:
            image.color = query['color']
        return image

    def di(self, with_id=False):
        di = self.__dict__.copy()
        del di['id']
        if not with_id:
            di['_id'] = self.id
        return di

    def full_path(self):
        return FileHelper.get_full_path(self.path)

    def author_str(self):
        return ','.join(self.authors)


@dataclass
class BaseData:
    id: ObjectId = None
    name: str = ""


@dataclass
class ImageFile(BaseData):
    full_path: str = ""


@dataclass
class PreloadImage:
    index: int
    pixmap: QPixmap
    width: int
    height: int
    size: int
    create_time: datetime


@dataclass
class MonitorSetting:
    monitor: Monitor
    image_desc_action: QAction
    image_level_actions: list
    image: MyImage = None


@dataclass
class SimilarImage:
    _id: ObjectId = field(default=None)
    author: str = field(default='')
    name: str = field(default='')
    md5s: list = field(default_factory=list)
    create_time: datetime = field(default=tzinfo.localize(datetime.now()))
    update_time: datetime = field(default=tzinfo.localize(datetime.now()))

    def id(self):
        return self._id

