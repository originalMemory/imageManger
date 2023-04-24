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
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import unique, Enum
from typing import Type, TypeVar

from PyQt6.QtGui import QPixmap, QAction
from bson import ObjectId
from dacite import from_dict
from screeninfo import Monitor

from helper.file_helper import FileHelper

DB = TypeVar('DB', bound='BaseDB')


@dataclass
class BaseDB:
    _id: ObjectId = field(default=None)
    create_time: datetime = field(default=datetime.now())
    update_time: datetime = field(default=datetime.now())

    def id(self):
        return self._id

    def dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls: Type[DB], query) -> DB:
        return from_dict(data_class=cls, data=query)


@unique
class TagType(Enum):
    Empty = ''
    Role = 'role'
    Work = 'work'
    Desc = 'desc'
    Company = 'company'
    Author = 'author'
    Unknown = 'unknown'


@unique
class Col(Enum):
    Image = 'image'
    Level = 'level'
    Tag = 'tag'
    TagCategory = 'tag_category'

    @staticmethod
    def from_dataclass(data_class: Type[DB]):
        if data_class == MyImage:
            return Col.Image
        if data_class == Tag:
            return Col.Tag
        if data_class == TagCategory:
            return Col.TagCategory


@dataclass
class MyImage(BaseDB):
    desc: str = field(default="")
    authors: list = field(default_factory=list)
    type: int = field(default=0)
    level: int = field(default=0)
    tags: list = field(default_factory=list)
    works: list = field(default_factory=list)
    roles: list = field(default_factory=list)
    source: str = field(default="")
    width: int = field(default=0)
    height: int = field(default=0)
    size: float = field(default=0.0)
    sequence: int = field(default=0)
    md5: str = field(default="")
    file_create_time: datetime = field(default=datetime.now())
    series: str = field(default="")
    uploader: str = field(default="")
    path: str = field(default="")
    color: str = field(default='')

    def full_path(self):
        return FileHelper.get_full_path(self.path)

    def author_str(self):
        return ','.join(self.authors)


@unique
class TagSource(Enum):
    Danbooru = 'danbooru'
    Yande = 'yande'
    Pixiv = 'pixiv'
    Unknown = 'unknown'


@dataclass
class Tag(BaseDB):
    name: str = field(default='')
    tran: str = field(default='')
    description: str = field(default='')
    restricted: bool = field(default=False)
    alias: list = field(default_factory=list)
    source: str = field(default='')
    wiki_url: str = field(default='')
    category_id: ObjectId = field(default=None)
    children: list = field(default_factory=list)
    type: str = field(default='')

    def get_type(self):
        if type:
            return TagType(self.type)
        else:
            return TagType.Unknown


@dataclass
class TagCategory(BaseDB):
    name: str = field(default='')
    description: str = field(default='')
    children: list = field(default_factory=list)


@dataclass
class BaseData:
    id: int = 0
    name: str = ""


@dataclass
class ImageFile:
    id: ObjectId = None
    name: str = ""
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
    create_time: datetime = field(default=datetime.now())
    update_time: datetime = field(default=datetime.now())

    def id(self):
        return self._id
