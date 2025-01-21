#!/user/bin/env python
# coding=utf-8

import os
import re
from dataclasses import dataclass, field
from datetime import datetime

from bs4 import BeautifulSoup
from ebooklib import epub


@dataclass
class Novel:
    title: str
    desc: str
    authors: list[str]
    subjects: list[str]
    series: str
    series_index: str
    publisher: str
    about_titles: list[str]


def add_space_after_character(text):
    # 定义匹配模式
    pattern = r"([部卷回集章篇节])(?!\s)"

    # 使用re.sub来替换
    corrected_text = re.sub(pattern, r"\1 ", text)

    return corrected_text


def split_text(filepath, about_titles):
    # section_pattern = r'^\s*第[0-9０１２３４５６７８９一二三四五六七八九十零〇百千两]+[部卷][ 　]*.*'
    section_pattern = r'^\s*第[0-9０１２３４５６７８９一二三四五六七八九十零〇百千两]+[卷][ 　]*.*'
    chapter_pattern = r'^\s*第[0-9０１２３４５６７８９一二三四五六七八九十零〇百千两]+[回集章篇节][ 　]*.*'
    first_chapter_pattern = r'^\s*序[回集章篇节][ 　]*.*'
    sections = []
    section = []
    chapter = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip().lstrip('\ufeff')
            if not line:
                continue
            if line in about_titles:
                print(f'匹配作品相关：{line}')
                if len(chapter):
                    section.append(chapter)
                    chapter = []
            elif re.match(section_pattern, line):
                line = add_space_after_character(line)
                print(f'匹配卷：{line}')
                if len(chapter):
                    section.append(chapter)
                    chapter = []
                if len(section) > 0:
                    sections.append(section)
                    section = []
            elif re.match(first_chapter_pattern, line) or re.match(chapter_pattern, line):
                line = add_space_after_character(line)
                print(f'匹配章节：{line}')
                if len(chapter) > 0:
                    section.append(chapter)
                    chapter = []
            chapter.append(line)
        if len(chapter):
            section.append(chapter)
        if len(section):
            sections.append(section)
    if len(sections) > 1 and about_titles:
        sections[0].insert(0, ['作品相关'])
    return sections


def create_epub(filename, novel: Novel):
    dir_path = 'D:\\epub'
    txt_sections = split_text(os.path.join(dir_path, filename), novel.about_titles)
    book = epub.EpubBook()
    book.set_title(novel.title)
    book.set_language('zh')
    for author in novel.authors:
        book.add_author(author)
    book.namespaces['calibre'] = 'http://calibre.kovidgoyal.net/2009/metadata'

    book.add_metadata('DC', 'description', novel.desc)
    book.add_metadata('DC', 'publisher', novel.publisher)
    book.add_metadata('DC', 'date', datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z'))
    for subject in novel.subjects:
        book.add_metadata('DC', 'subject', subject)

    if novel.series:
        book.add_metadata(None, "meta", "", {"name": "calibre:series", "content": novel.series})
        book.add_metadata(None, "meta", "", {"name": "calibre:series_index", "content": novel.series_index})

    css_id = "main-css"
    with open(os.path.join(dir_path, 'main.css'), 'r', encoding='utf-8') as f:
        style = f.read()
        css = epub.EpubItem(uid=css_id, file_name="css/main.css", media_type="text/css", content=style)
    book.add_item(css)

    # 添加封面
    cover_and_subject = ''
    if os.path.exists(os.path.join(dir_path, 'cover.jpg')):
        with open(os.path.join(dir_path, 'cover.jpg'), 'rb') as f:
            cover_content = f.read()
        book.set_cover('cover.jpg', cover_content)
        cover_and_subject = '\n<div style="text-align:center"><img class="cover" src="cover.jpg"/></div>'
    # 创建封面页面
    home_page = epub.EpubHtml(title='首页', file_name='home.xhtml', lang='zh', uid='home')
    home_page.add_item(css)
    desc_lines = [f'<p>{line}</p>' for line in novel.desc.split('\n') if line.strip()]
    desc_html = '\n'.join(desc_lines)
    home_page.content = f'''
<div>{cover_and_subject}
<h1>{novel.title}</h1>
<h2>{"，".join(novel.authors)}</h2>
<div class="tags">
{''.join(f'<span class="tag">{subject}</span><span> </span>' for subject in novel.subjects)}
</div>
<b>简介</b>
{desc_html}
</div>
    '''
    book.add_item(home_page)

    epub_sections = []
    chapter_i = 1
    for txt_section in txt_sections:
        epub_section = []
        for txt_chapter in txt_section:
            epub_chapter = create_chapter(book, css, chapter_i, txt_chapter)
            epub_section.append(epub_chapter)
            chapter_i += 1
        epub_sections.append(epub_section)
    # 阅读顺序
    home_link = epub.Link(home_page.file_name, home_page.title, home_page.id)
    if len(epub_sections) == 1:
        book.toc = [home_link] + [epub.Link(item.file_name, item.title, item.id) for item in epub_sections[0]]
    else:
        toc = [home_link]
        for epub_section in epub_sections:
            toc_section = (
                epub.Section(epub_section[0].title, href=epub_section[0].file_name),
                [epub.Link(item.file_name, item.title, item.id) for item in epub_section[1:]]
            )
            toc.append(toc_section)
        book.toc = toc
    # book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['home'] + [item for sublist in epub_sections for item in sublist]

    # 添加 guide 元素
    epub.write_epub(os.path.join(dir_path, f'{novel.title} - {",".join(novel.authors)}.epub'), book, {})


def create_chapter(book, css, i, lines):
    ch = epub.EpubHtml(title=lines[0], lang='zh', uid=f'chapter{i}', file_name=f'chapter{i}.xhtml')
    ch.add_item(css)
    ch.content = f'<h3>{lines[0]}</h3>'
    ch.content += ''.join(f'<p>{line}</p>' for line in lines[1:])
    book.add_item(ch)
    return ch


def update_epub(filename, novel: Novel):
    dir_path = 'D:\\epub'
    filepath = os.path.join(dir_path, filename)
    book = epub.read_epub(filepath)
    for author in novel.authors:
        book.add_author(author)
    book.namespaces['calibre'] = 'http://calibre.kovidgoyal.net/2009/metadata'
    if novel.series:
        book.add_metadata(None, "meta", "", {"name": "calibre:series", "content": novel.series})
        book.add_metadata(None, "meta", "", {"name": "calibre:series_index", "content": novel.series_index})
    sub_html = ''
    for subject in novel.subjects:
        book.add_metadata('DC', 'subject', subject)
        sub_html += f'<span class="tag">{subject}</span><span> </span>\n'
    with open(os.path.join(dir_path, 'main.css'), 'r', encoding='utf-8') as f:
        style = f.read()
    main_css_id = 'css'
    # main_css_id = 'main-css'
    css_item = None
    for item in book.items:
        if item.id == main_css_id:
            item.content = style
            css_item = item
            break
    if not css_item:
        css_item = epub.EpubItem(uid=main_css_id, file_name="css/main.css", media_type="text/css", content=style)
        book.add_item(css_item)
    for item in book.items:
        if isinstance(item, epub.EpubHtml):
            item.add_item(css_item)
        if item.id == 'coverpage':
            abstract = '<b>简介</b>'
            new_text = f'<div class="tags">\n{sub_html}</div>\n{abstract}'
            # 使用 BeautifulSoup 来处理 HTML 内容
            soup = BeautifulSoup(item.content, 'html.parser')
            # 查找 <b>简介</b> 并替换整个标签
            tag = soup.find('b', string="简介")  # 找到 <b>标签，内容为"简介"
            if tag:
                # 替换整个 <b>简介</b> 元素为新的 HTML 内容
                new_content = BeautifulSoup(new_text, 'html.parser')
                tag.replace_with(new_content)
                item.content = str(soup)
            # content = str(item.content)
            # new_content = content.replace(abstract, new_text)
            # item.content = new_content
    new_filename = f'{novel.title} - {",".join(novel.authors)}.epub'
    if novel.series_index:
        new_filename = f'{novel.series_index} {new_filename}'
    # 替换非法字符
    new_filename = re.sub(r'[<>/\\|:"?]', '_', new_filename)
    new_filepath = os.path.join(dir_path, new_filename)
    epub.write_epub(new_filepath, book, {})


if __name__ == '__main__':
    novel = Novel(
        title='世界的唯一',
        desc='''
''',
        authors=['coly'],
        subjects=['H', '催眠', '常识改变'],
        series=None,
        series_index='',
        publisher='',
        about_titles=[]
    )
    # create_epub(r'《春秋风华录后宫魔改版》1-225章.txt', novel)
    update_epub('世界的唯一.epub', novel)
