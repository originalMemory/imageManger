#!/user/bin/env python3
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : extension.py
@author  : illusion
@desc    :
@create  : 2022-03-12 13:22:14
"""
import time


def timeit(func):
    """
    :param func: 需要传入的函数
    :return:
    """

    def _warp(*args, **kwargs):
        """
        :param args: func需要的位置参数
        :param kwargs: func需要的关键字参数
        :return: 函数的执行结果
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        elastic_time = time.time() - start_time
        print(f"方法 '{func.__name__}'  执行耗时 {elastic_time:.4f}s")
        return result

    return _warp

