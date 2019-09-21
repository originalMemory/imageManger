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


@dataclass
class MyImage:
    """
    Mysql 中 image 表的数据类型映射
    """
    id: int
    desc: str
    author: str
    type_id: int
    level_id: int
    tags: str
    works: str
    role: str
    source: str
    width: int
    height: int
    size: float
    filename: str
    path: str
    file_create_time: datetime
    create_time: datetime
    update_time: datetime

