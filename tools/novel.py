#!/user/bin/env python
# coding=utf-8

import os
import re
from dataclasses import dataclass, field
from turtle import up
from ebooklib import epub
from datetime import datetime
from bs4 import BeautifulSoup

@dataclass
class Novel:
    title: str = field(default='')
    content: list = field(default_factory=list)

    def empty(self):
        return not len(self.content)


def add_space_after_character(text):
    # 定义匹配模式
    pattern = r"([部卷回集章篇节])(?!\s)"

    # 使用re.sub来替换
    corrected_text = re.sub(pattern, r"\1 ", text)

    return corrected_text


def split_text(filepath):
    section_pattern = r'^\s*第[0-9０１２３４５６７８９一二三四五六七八九十零〇百千两]+[部卷][ 　]*.*'
    chapter_pattern = r'^\s*第[0-9０１２３４５６７８９一二三四五六七八九十零〇百千两]+[回集章篇节][ 　]*.*'
    first_chapter_pattern = r'^\s*序[回集章篇节][ 　]*.*'
    sections = []
    section = []
    chapter = []
    with open(filepath, 'r', encoding='gbk') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if re.match(section_pattern, line):
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
    return sections


def create_epub(filename, with_cover, title, authors, desc, subjects, series, series_index):
    dir_path = 'D:\\epub'
    txt_sections = split_text(os.path.join(dir_path, filename))
    book = epub.EpubBook()
    book.set_title(title)
    book.set_language('zh')
    for author in authors:
        book.add_author(author)
    book.namespaces['calibre'] = 'http://calibre.kovidgoyal.net/2009/metadata'

    book.add_metadata('DC', 'description', desc)
    book.add_metadata('DC', 'publisher', '幻灭')
    book.add_metadata('DC', 'date', datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z'))
    for subject in subjects:
        book.add_metadata('DC', 'subject', subject)

    book.add_metadata(None, "meta", "", {"name": "calibre:series", "content": series})
    book.add_metadata(None, "meta", "", {"name": "calibre:series_index", "content": series_index})

    css_id = "main-css"
    with open(os.path.join(dir_path, 'main.css'), 'r', encoding='utf-8') as f:
        style = f.read()
        css = epub.EpubItem(uid=css_id, file_name="css/main.css", media_type="text/css", content=style)
    book.add_item(css)

    # 添加封面
    css_line = ''
    if with_cover:
        with open(os.path.join(dir_path, 'cover.jpg'), 'rb') as f:
            cover_content = f.read()
        book.set_cover('cover.jpg', cover_content)
        css_line = '\n<div style="text-align:center"><img class="cover" src="cover.jpg"/></div>'
    # 创建封面页面
    home_page = epub.EpubHtml(title='首页', file_name='home.xhtml', lang='zh', uid='home')
    home_page.add_item(css)
    desc_lines = [f'<p>{line}</p>' for line in desc.split('\n') if line.strip()]
    desc_html = '\n'.join(desc_lines)
    home_page.content = f'''
<div>{css_line}
<h1>{title}</h1>
<h2>{"，".join(authors)}</h2>
<div class="tags">
{''.join(f'<span class="tag">{subject}</span><span> </span>' for subject in subjects)}
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
    if len(epub_sections) == 1:
        book.toc = [epub.Link(item.file_name, item.title, item.id) for item in epub_sections[0]]
    else:
        toc = []
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
    epub.write_epub(os.path.join(dir_path, f'{title} - {author}.epub'), book, {})


def create_chapter(book, css, i, lines):
    ch = epub.EpubHtml(title=lines[0], lang='zh', uid=f'chapter{i}', file_name=f'chapter{i}.xhtml')
    ch.add_item(css)
    ch.content = f'<h3>{lines[0]}</h3>'
    ch.content += ''.join(f'<p>{line}</p>' for line in lines[1:])
    book.add_item(ch)
    return ch


def update_epub(filename, author, subjects, series, series_index):
    dir_path = 'D:\\epub'
    filepath = os.path.join(dir_path, filename)
    book = epub.read_epub(filepath)
    book.add_author(author)
    book.namespaces['calibre'] = 'http://calibre.kovidgoyal.net/2009/metadata'
    book.add_metadata(None, "meta", "", {"name": "calibre:series", "content": series})
    book.add_metadata(None, "meta", "", {"name": "calibre:series_index", "content": series_index})
    sub_html = ''
    for subject in subjects:
        book.add_metadata('DC', 'subject', subject)
        sub_html += f'<span class="tag">{subject}</span><span> </span>\n'
    with open(os.path.join(dir_path, 'main.css'), 'r', encoding='utf-8') as f:
        style = f.read()
    main_css_id = 'main-css'
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

    epub.write_epub(filepath, book, {})


if __name__ == '__main__':
    desc = '''
千红一哭，万艳同悲。
白骨如山忘姓氏，无非公子与红妆。
后世青年魂穿红楼世界中宁国远亲之上，为了免于被贾府牵连之命运，只好步步为营，然而茫然四顾，发现家国天下，乱世将临，为不使神州陆沉，遍地膻腥，只好提三尺剑，扫不臣，荡贼寇，平鞑虏，挽天倾！
这一切，从截胡秦可卿开始……
'''
    title = '红楼之挽天倾 重置5.0+5.3'
    authors = ['林悦南兮', 'North']
    subjects = ['历史', '架空历史', '穿越', '后宫', 'H']
    series = '红楼之挽天倾'
    series_index = '7'
    create_epub(r'1-1 红楼之挽天倾1-1688 前800章重置过 5.3整合.txt', True, title, authors, desc, subjects, series, series_index)
    # update_epub('红楼之挽天倾 (North)加料5.2版.epub', author, subjects, series, series_index)

