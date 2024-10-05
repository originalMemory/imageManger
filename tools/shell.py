#!/usr/bin/env python3
# coding=utf-8
"""
@project : tutor_flutter
@ide     : VsCode
@file    : shell
@author  : illusion
@desc    : 工具文件
@create  : 2021-07-16 18:06:35
"""

import subprocess
import sys
from enum import Enum, unique


@unique
class Color(Enum):
    White = 0
    Red = 1
    Green = 2
    Yellow = 3
    Blue = 4

    def get_foreground_color(self):
        if self == Color.White:
            return 38
        elif self == Color.Red:
            return 31
        elif self == Color.Green:
            return 32
        elif self == Color.Yellow:
            return 33
        elif self == Color.Blue:
            return 34


def print_msg(msg, color=Color.Green):
    print(f'\033[{color.get_foreground_color()}m{msg}\033[0m')
    sys.stdout.flush()


def sh(*pop_en_args):
    print_msg(f'shell: {pop_en_args}', color=Color.Blue)
    subprocess.check_call(pop_en_args, shell=True)


def sh_out(*pop_en_args):
    print_msg(f'shell_out: {pop_en_args}', color=Color.Blue)
    res = subprocess.check_output(pop_en_args, shell=True)
    res = str(res, encoding='utf-8')
    print_msg(res)
    return res
