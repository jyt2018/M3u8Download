#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lib_downvideo - 视频下载相关工具库

功能:
    1. 从播放页面提取 m3u8 地址
    2. 处理 m3u8 文件中的广告片段
    3. 提供 URL 解析和处理工具函数
    4. 提供 base64 密钥解密功能

依赖:
    - requests: HTTP 请求库
    - beautifulsoup4: HTML 解析库

Author: unixsam, 2026-05-02
"""

import os
import requests
from bs4 import BeautifulSoup
import urllib
import unicodedata
import datetime
import re
import logging
import base64
from urllib.parse import urlparse, urljoin
import random


USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36 115Browser/6.0.3',
    'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50',
    'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50',
    'Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)',
    'Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1',
    "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:80.0) Gecko/20100101 Firefox/80.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.2 Safari/605.1.15"
]


def rnd_header():
    """
    生成随机 User-Agent 的 HTTP 请求头。

    从 USER_AGENT_LIST 中随机选择一个 User-Agent，
    构造并返回包含该 User-Agent 的请求头字典。

    :return: 包含随机 User-Agent 的请求头字典
    :rtype: dict
    """
    user_agent = random.choice(USER_AGENT_LIST)
    headers = {
        'User-Agent': user_agent
    }
    return headers


def remove_m3u8_ad(m3u8_content):
    """
    从 m3u8 文件内容中移除广告片段。

    通过检测 ts 文件名中的数字是否连续来识别广告片段。
    当发现文件名中的数字不连续时，判定为进入或退出广告区域。

    :param m3u8_content: m3u8 文件的原始内容
    :type m3u8_content: str
    :return: 移除广告片段后的 m3u8 文件内容
    :rtype: str

    示例:
        >>> original = "#EXTM3U\n#EXTINF:10,\nvideo001.ts\n#EXTINF:5,\nad001.ts\n#EXTINF:10,\nvideo002.ts\n"
        >>> result = remove_m3u8_ad(original)
        >>> print(result)
        #EXTM3U
        #EXTINF:10,
        video001.ts
        #EXTINF:10,
        video002.ts
    """
    lines = m3u8_content.splitlines(keepends=True)
    ts_filenames = []
    ts_line_numbers = []
    ad_lines_list = []

    for i, line in enumerate(lines, start=1):
        if line.startswith("#EXTI"):
            if i < len(lines):
                ts_url = lines[i]
                ts_filenames.append(ts_url)
                ts_line_numbers.append(i + 1)

    print(len(ts_filenames), len(ts_line_numbers))

    if not ts_filenames:
        print("未找到包含视频片段的行。")
        return m3u8_content

    print("以下为插入的ad行: \n")
    Ad_in = False
    for j in range(2, len(ts_filenames)):
        prev_filename = ts_filenames[j - 1]
        curr_filename = ts_filenames[j]

        try:
            prev_num = int(''.join(filter(str.isdigit, prev_filename.split("/")[-1])))
            curr_num = int(''.join(filter(str.isdigit, curr_filename.split("/")[-1])))
        except ValueError:
            print(f"文件名格式不符合要求，无法判断连续性：{prev_filename}, {curr_filename}")
            continue

        if curr_num != prev_num + 1:
            Ad_in = not Ad_in
            if Ad_in:
                print("ad in after", ts_filenames[j-1].strip())
                print(f"{curr_filename.strip()},行号in:{ts_line_numbers[j]}")
                ad_lines_list.append(ts_line_numbers[j] - 1)
                ad_lines_list.append(ts_line_numbers[j])
            else:
                print(f"ad area +1 {ts_filenames[j-1].strip()}")
                _ = input("continue")
        else:
            if Ad_in:
                print(f"{curr_filename.strip()},行号-:{ts_line_numbers[j]}")
                ad_lines_list.append(ts_line_numbers[j] - 1)
                ad_lines_list.append(ts_line_numbers[j])
            else:
                pass
    print(ad_lines_list)

    lines_no_ad = [lines[i-1] for i in range(1, len(lines)+1) if i not in ad_lines_list]
    return ''.join(lines_no_ad)


def get_domain_by_url(url):
    """
    解析 URL，获取协议、域名、路径、文件名和后缀。

    :param url: 完整的 URL 地址
    :type url: str
    :return: 包含以下元素的元组:
        - 协议+域名 (str): 如 "https://www.example.com"
        - 路径 (str): URL 中的路径部分
        - 文件名 (str): 路径中的最后一个组件
        - 后缀 (tuple): 文件名和后缀的元组
    :rtype: tuple

    示例:
        >>> get_domain_by_url("https://www.example.com/path/to/video.html")
        ('https://www.example.com', '/path/to/video.html', 'video.html', ('video', '.html'))
    """
    url_sche = urllib.parse.urlparse(url).scheme
    url_netloc = urllib.parse.urlparse(url).netloc
    url_path = urllib.parse.urlparse(url).path
    uname = os.path.basename(url_path)
    suffix = os.path.splitext(uname)

    return f"{url_sche}://{url_netloc}", url_path, uname, suffix


def extract_m3u8_from_playpage(url_in):
    """
    从视频播放页面 URL 中提取 m3u8 地址。

    通过解析 HTML 页面中的 JavaScript 代码，查找 player_aaaa 对象，
    并从中提取视频播放地址。

    :param url_in: 视频播放页面的 URL
    :type url_in: str
    :return: 提取到的 m3u8 地址（或其他视频地址），如果提取失败则返回空字符串
    :rtype: str

    注意:
        目前支持的网站结构:
        - 查找 class 为 'hl-player-wrap embed-responsive embed-responsive-16by9 by-qq362695000 clearfix' 的 div
        - 在该 div 内查找第一个 script 标签
        - 从 script 中提取 var player_aaaa 对象
        - 从 player_aaaa 中提取 url 字段
    """
    try:
        response = requests.get(url_in, headers=rnd_header())
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        div_tag = soup.find('div', class_='hl-player-wrap embed-responsive embed-responsive-16by9 by-qq362695000 clearfix')
        if not div_tag:
            return ""

        script_tag = div_tag.find('script')
        if not script_tag:
            return ""

        jscode = script_tag.string
        if not jscode:
            return ""

        match = re.search(r'var player_aaaa=(.*)', jscode)
        if not match:
            return ""

        js_str = match.group(1)
        url_match = re.search(r'"url":"([^"]+)"', js_str)
        if not url_match:
            return ""
        url_m = url_match.group(1).replace("\\", "")
        if url_m.endswith("m3u8"):
            return url_m
        else:
            return url_m

    except Exception as e:
        print(e)
        return "eee"


def mklocaldir(subpath):
    """
    创建本地存储目录。

    如果提供了子路径，则在当前工作目录下创建该子路径；
    如果未提供子路径（空字符串），则以当前日期（格式: %y%m%d）创建目录。

    :param subpath: 子目录路径，可以为空字符串
    :type subpath: str

    注意:
        - 目录已存在时不会报错
        - 只会创建一级目录（不会递归创建多级目录）
    """
    if not subpath:
        savefile_path = os.path.join(subpath, datetime.datetime.now().strftime('%y%m%d'))
    else:
        savefile_path = os.path.join(subpath, savefile_path)

    download_path = os.path.join(os.getcwd(), subpath)
    print(download_path)
    if not os.path.exists(download_path):
        os.mkdir(download_path)

    print("savefile_path = " + savefile_path)
    if not os.path.exists(savefile_path):
        os.mkdir(savefile_path)


def file2dict(filepath):
    """
    将结构化的文本文件转换为字典。

    文件格式要求:
        每行格式: URL|标题
        例如: https://example.com/video1|第一集 开始

    :param filepath: 结构化文本文件的路径
    :type filepath: str
    :return: 字典，键为 URL，值为标题
    :rtype: dict

    示例:
        文件内容:
            https://example.com/ep1|第一集
            https://example.com/ep2|第二集
        返回:
            {'https://example.com/ep1': '第一集', 'https://example.com/ep2': '第二集'}
    """
    listDict = dict()
    os.chdir(".")
    with open(filepath, encoding='utf-8') as f_menulist:
        try:
            lines = f_menulist.readlines()
            filesum = len(lines)
            print("Total: " + str(filesum) + " links in menulist")

            linesToRead = filesum
            linesStart = 0
            for i in range(linesStart, linesStart + linesToRead):
                currentline = lines[i].split("|")
                currenturl = currentline[0]
                currenttitle = currentline[1].strip()
                listDict[currenturl] = currenttitle
        finally:
            f_menulist.close()

    return listDict


def clean_unicode(text):
    """
    清理字符串中的异常 Unicode 字符和 HTML 实体。

    处理的内容包括:
    1. 替换常见的 HTML 实体（如 &nbsp;, &amp; 等）
    2. 移除 Unicode 行分隔符 (U+2028) 和段落分隔符 (U+2029)
    3. 使用 NFKC 规范化 Unicode 字符
    4. 移除所有控制字符

    :param text: 需要清理的原始字符串
    :type text: str
    :return: 清理后的字符串
    :rtype: str

    示例:
        >>> clean_unicode("Hello&nbsp;World&amp;Test")
        'Hello World&Test'
    """
    replace_dict = {
        "&nbsp;": " ",
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": "\"",
        "&apos;": "'",
        "&#39;": "'",
        "&#34;": "\"",
        "&#60;": "<",
        "&#62;": ">",
    }
    if not isinstance(text, str):
        return text
    for key, value in replace_dict.items():
        text = text.replace(key, value)
    text = text.replace('\u2028', ' ').replace('\u2029', ' ')

    return "".join(
        char for char in unicodedata.normalize("NFKC", text) if not unicodedata.category(char).startswith("C")
    )


def split_file_path(file_full_path):
    """
    拆分文件路径，获取目录、文件名和后缀。

    :param file_full_path: 完整的文件路径（绝对路径或相对路径）
    :type file_full_path: str
    :return: 包含以下元素的元组:
        - 目录 (str): 文件所在的目录路径（绝对路径）
        - 文件名 (str): 不含后缀的文件名
        - 后缀 (str): 文件后缀（包含点号，如 '.mp4'）
    :rtype: tuple

    示例:
        >>> split_file_path("/home/user/video.mp4")
        ('/home/user', 'video', '.mp4')
    """
    directory = os.path.abspath(file_full_path)
    filename_with_ext = os.path.basename(file_full_path)
    filename, extension = os.path.splitext(filename_with_ext)
    return directory, filename, extension


def get_second_layer_m3u8(url):
    """
    从第一层 m3u8 文件中获取第二层 m3u8 地址。

    有些 m3u8 文件是多级结构：第一层包含不同清晰度的选项，
    每个选项指向另一个 m3u8 文件（第二层），第二层才包含实际的 ts 片段。

    :param url: 第一层 m3u8 文件的 URL
    :type url: str
    :return: 第二层 m3u8 地址（文件中找到的第一个 .m3u8 结尾的行），
             如果获取失败或未找到则返回 None
    :rtype: str or None
    """
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            lines = response.text.splitlines()
            for line in lines:
                if line.endswith(".m3u8"):
                    return line
        return None
    except Exception as e:
        logging.error(f"获取第二层 m3u8 地址时发生错误：{e}")
        return None


def decode_base64_key(base64_key_str):
    """
    将 base64 编码的字符串解码为二进制密钥数据。

    用于解密加密的 m3u8 视频。当视频使用 AES 加密时，
    可以通过此函数将 base64 编码的密钥解码为二进制格式。

    :param base64_key_str: base64 编码的密钥字符串
    :type base64_key_str: str
    :return: 解码后的二进制密钥数据，如果输入为 None 则返回 None
    :rtype: bytes or None

    示例:
        >>> key = decode_base64_key("5N12sDHDVcx1Hqnagn4NJg==")
        >>> print(type(key))
        <class 'bytes'>

    注意:
        解码后的密钥可以直接写入 key 文件供 ffmpeg 使用
    """
    if base64_key_str:
        return base64.b64decode(base64_key_str.encode())
    return None
