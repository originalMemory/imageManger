#!/user/bin/env python3
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : display_helper
@author  : illusion
@desc    : 显示器相关帮助类
@create  : 2021/3/21
"""

from win32api import GetSystemMetrics
from win32con import SM_CMONITORS, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN


class DisplayHelper:
    @staticmethod
    def monitor_sizes():
        # 显示器数量检测
        monitor_number = GetSystemMetrics(SM_CMONITORS)
        # 主屏幕尺寸检测
        main_screen = (GetSystemMetrics(0), GetSystemMetrics(1))  # 主屏幕宽高
        # print("主屏幕尺寸：", GetSystemMetrics(0), "*", GetSystemMetrics(1))
        # 屏幕最大尺寸
        all_screen_width = GetSystemMetrics(SM_CXVIRTUALSCREEN)  # 屏幕最大宽度
        all_screen_height = GetSystemMetrics(SM_CYVIRTUALSCREEN)  # 屏幕最大高度
        all_screen = (all_screen_width, all_screen_height)
        # print("屏幕总尺寸:", all_screen_width, "*", all_screen_height)
        # 当前主流的分辨率基数是宽，偶数是高
        resolving_power = [1280, 720, 1920, 1080, 2560, 1440, 3840, 2160, 4096, 2160, 7680, 4320]

        if monitor_number > 1:  # 屏幕数量判断print(monitor_number)就可以知道有多少块屏幕
            secondary_screen_width = all_screen_width - main_screen[0]  # 副屏宽=总屏幕宽-当前屏幕宽
            # print("副屏宽",secondary_screen_width)

            # 主屏横竖屏检测
            if GetSystemMetrics(0) > GetSystemMetrics(1):
                print("主屏(横屏)尺寸：", GetSystemMetrics(0), "*", GetSystemMetrics(1))
            else:
                print("主屏(竖屏)尺寸：", GetSystemMetrics(0), "*", GetSystemMetrics(1))

            # 横屏状态
            for i in range(0, len(resolving_power) - 1, 2):
                # print("i",resolving_power[i])
                if secondary_screen_width == resolving_power[i]:
                    secondary_screen = (resolving_power[i], resolving_power[i + 1])
                    # print("副屏(横屏)尺寸：", resolving_power[i], resolving_power[i + 1])
                    # return "副屏(竖屏)尺寸：",secondary_screen
                    break
            # 竖屏状态
            for i in range(1, len(resolving_power) - 1, 2):
                # print("i",resolving_power[i])
                if secondary_screen_width == resolving_power[i]:
                    secondary_screen = (resolving_power[i], resolving_power[i + 1])
                    # print("副屏(竖屏)尺寸：", resolving_power[i], resolving_power[i - 1])
                    # return "副屏(竖屏)尺寸",secondary_screen
                    break
            return [main_screen, secondary_screen]
        else:
            return [main_screen]
