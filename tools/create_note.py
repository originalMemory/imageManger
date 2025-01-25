#!/user/bin/env python
# coding=utf-8
import json
import os
from datetime import datetime
import requests


def main():
    # 把当前日期转化为型如 'yyyy-mm-dd ddd' 格式的字符串，ddd 表示周几，要中文
    now = datetime.now()
    # 定义星期的中文映射
    weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    # 格式化日期为指定格式
    formatted_date = now.strftime('%Y-%m-%d') + ' ' + weekdays[now.weekday()]

    base_path = r'Z:\笔记'
    with open(os.path.join(base_path, '模板', '日记模板.md'), encoding='utf-8') as f:
        lines = []
        skip = True
        for line in f.readlines():
            if line.startswith('---'):
                skip = False
            if not skip:
                lines.append(line)
    print(lines[0])
    # req = requests.request('https://nas.xuanniao.fun:49150/api/imageAlbum/moonImage')
    # moon = json.loads(req.text)
    moon = { 'sourceUrl' : 'test', 'lskyUrl': 'test2' }



if __name__ == '__main__':
    main()
