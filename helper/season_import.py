#!/usr/bin/env python3
# coding=utf-8
"""
@project : imageManger
@ide     : PyCharm
@file     : season_import
@author  : wuhb
@desc    :
@create  : 2023/2/26 19:22
"""
import os
from bs4 import BeautifulSoup
import requests
import re
import time
import sys
import xml.etree.ElementTree as ET

proxy = None
api_key = '7734bdb5ad99c6df5463a7deefd3d391'


def prepare_season_content(season, title, plot=''):
    e_season = ET.Element('season')
    ET.SubElement(e_season, 'seasonnumber').text = str(season)
    ET.SubElement(e_season, 'lockdata').text = 'false'
    ET.SubElement(e_season, 'title').text = title
    ET.SubElement(e_season, 'plot').text = plot
    return BeautifulSoup(ET.tostring(e_season), 'xml').prettify()


def check_overwrite_file(file):
    data = read_file(file)
    if data is None:
        return True
    data = BeautifulSoup(data, 'xml')
    tag_season = data.find('season')
    if tag_season is None:
        return True
    lock = tag_season.find('lockdata')
    return False if lock is not None and lock.text.strip().upper() == 'TRUE' else True


def read_file(file):
    if not os.path.exists(file):
        return None
    with open(file, 'r') as f:
        return f.read()


def get_tmddb_id(tv_nfo):
    print(f'reading file: {os.path.abspath(tv_nfo)}')
    tv_nfo = read_file(tv_nfo)
    if tv_nfo is None:
        return None
    tv_nfo = BeautifulSoup(tv_nfo, 'xml')
    tv_nfo = tv_nfo.find('tvshow')
    if tv_nfo is None:
        return None
    tmdb_id = tv_nfo.find('tmdbid')
    return None if tmdb_id is None else tmdb_id.text


def request_tv_info(tv_id, key):
    print(f'Accessing tmdb to get tv info of {tv_id}')
    response = requests.get(f'https://api.themoviedb.org/3/tv/{tv_id}',
                            timeout=10, params={'api_key': key, 'language': 'zh-CN'},
                            proxies=None if proxy is None else {'https': proxy})
    if response.status_code != 200:
        raise f'''Failed to access tmdb api for get tv {tv_id}.
        status: {response.status_code}
        message: {response.content}'''
    return response.json()


def load_tv_info(file):
    tv_id = get_tmddb_id(file)
    if tv_id is None:
        raise f'Failed to get tmdb id from ${file}'
    print(f'Got tmdb id {tv_id}')
    retry = 5
    tv_info = None
    while retry > 0:
        try:
            retry = retry - 1
            tv_info = request_tv_info(tv_id, api_key)
            retry = 0
        except:
            time.sleep(1)
            print(f'Failed to request tmdb api. rest attempts {retry}')
    if tv_info is None:
        raise 'Failed to get tmdb info'
    new_line="\n\t\t\t"
    print(f'''Got tv info from tmdb
========> tmdb id: {tv_info['id']}
          title: {tv_info['name']}({tv_info['original_name']})
          seasons: {len(tv_info['seasons'])}
{new_line}{new_line.join(list(map( lambda x: str(x['season_number']) + '. '+ x['name'] , tv_info['seasons'] )))}
    ''')
    return tv_info


def get_season_number(folder_name):
    m = re.search('([Ss]eason\\s*[0-9]+)|([第季]+\\s*[0-9]+\\s*季*)|([Ss][0-9]+)|([0-9]+)', folder_name)
    if m is None:
        return None
    s = m.group(0)
    print(f'season: {s}')
    m = re.search('[0-9]+', s)
    return int(m.group(0))


def scan_seasons(directory):
    season_map = None
    for sud_dir in os.listdir(directory):
        if not os.path.isdir(os.path.join(directory, sud_dir)):
            continue
        n = get_season_number(sud_dir)
        if n is not None:
            if season_map is None:
                season_map = {}
            season_map[n] = sud_dir
    return season_map


def write_season_info(file):
    folder = os.path.dirname(os.path.abspath(file))
    print(f'Identified the tv folder: {folder}')
    season_folders = scan_seasons(folder)
    print(f'Scanned out the season folders: {season_folders}')
    if season_folders is None:
        print('Not found any season folder')
        exit(0)
    tv_info = load_tv_info(file)
    for season in tv_info['seasons']:
        season_number = int(season['season_number'])
        season_folder = season_folders.get(season_number)
        if season_folder is None:
            continue
        season_folder = os.path.join(folder, season_folder)
        season_file = os.path.join(season_folder, 'season.nfo')
        if not check_overwrite_file(season_file):
            print(f'the file {season_file} has been locked.')
            continue
        if season['name'] is None:
            season['name'] = '第 {: 2d} 季'.format(season_number)

        season_data = prepare_season_content(season_number, season['name'], season['overview'])
        with open(season_file, 'wb') as f:
            print(f"========> writing file '{season_file}'...")
            f.write(season_data.encode('utf-8'))


if __name__ == '__main__':
    file = '/Volumes/Normal1/media/tv/赛博朋克：边缘行者 (2022)/tvshow.nfo'
    if len(sys.argv) > 3:
        proxy = str(sys.argv[3])
    try:
        write_season_info(file)
    except Exception as e:
        print(f'Failed to write season for file : {file}, {e}')
    finally:
        print('============== END ==============\n')