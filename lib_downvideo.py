import os
import requests
from bs4 import BeautifulSoup
import urllib
import unicodedata
import datetime
import re
import logging
from urllib.parse import urlparse, urljoin
import lib_findbook as fb

# 1. 读取 URL
#   使用 requests.get 获取 m3u8 文件内容。
#   如果出现网络错误，捕获异常并结束函数。

# 2. 判断域名中是否同时包含 "lz" 和 "cdn"
#   使用 urlparse(m3u8_url).netloc 提取域名部分。
#   检查域名中是否同时包含 "lz" 和 "cdn"。如果没有，输出提示信息并结束函数。

# 3. 读取所有视频片段文件名，并查找插入的行（b）及其行号
#   - 遍历 m3u8 文件的每一行，提取以 .ts 结尾的文件名及其行号。
#   - 检查文件名中的数字部分是否连续。
#   - 如果当前行与上一行不连续，且下一行与当前行也不连续，则当前行为插入行（b）。
#   - 输出插入行（b）的 URL 及其行号。
def remove_m3u8_ad(m3u8_content):
    """
    处理 m3u8 文件的 URL, 提取视频片段文件名 和 插入的广告行。
    1. 读取 URL。
    2. 判断域名中是否同时包含 "lz" 和 "cdn"，如果没有则结束函数。量子云
    3. 如果包含，读取所有视频片段文件名，查找插入的广告及其行号。
    :param m3u8_url: 真正m3u8 文件的 URL
    """
    # 1. 读取 URL, 但是这可能是一个已经下载好的m3u8文件，所以不用再次下载
    # if validators.url(m3u8_url):
    #     try:
    #         res = requests.get(m3u8_url)
    #         res.raise_for_status()
    #         m3u8_content = res.text
    #     except requests.RequestException as e:
    #         print(f"获取 m3u8 文件时出现网络错误: {e}")
    #         return

    # 2. 判断域名中是否同时包含 "lz" 和 "cdn"
    # domain = urlparse(m3u8_url).netloc  # 获取域名部分
    # if "lz" not in domain or "cdn" not in domain:
    #     print(f"域名 {domain} 中不包含 'lz' 和 'cdn'，结束处理。")
    #     return

    # 3. 读取所有视频片段文件名，并查找插入的行（b）及其行号
    lines = m3u8_content.splitlines(keepends=True)  # 按行分割，保留行尾符, 便于写回文件
    ts_filenames = []
    ts_line_numbers = []
    ad_lines_list = [] # 广告行
    # 提取所有 .ts 文件名及其行号
    for i, line in enumerate(lines, start=1):  # 行号从 1 开始计数，方便编辑软件查看
        if line.startswith("#EXTI"):  # 找到以 #EXTINF 开头的行
            # 下一行是视频片段 URL
            if i < len(lines):
                ts_url = lines[i]  # i从1开始计数，实际是第 i+1 行
                ts_filenames.append(ts_url)
                ts_line_numbers.append(i + 1)  # EXTINF 行号 + 1 = URL 行号
    print(len(ts_filenames), len(ts_line_numbers))

    if not ts_filenames:
        print("未找到包含视频片段的行。")
        return

    # 查找广告行
    print("以下为插入的ad行: \n")
    Ad_in = False  # 是否进入广告状态
    for j in range(2, len(ts_filenames)):
        prev_filename = ts_filenames[j - 1]
        curr_filename = ts_filenames[j]

        # 这行代码的主要功能是从字符串 prev_filename 中提取最后一个路径组件（通常是文件名）里的所有数字字符，然后将这些数字字符连接成一个新的字符串, 再转换为整数，判断是否连续
        try:
            prev_num = int(''.join(filter(str.isdigit, prev_filename.split("/")[-1])))
            curr_num = int(''.join(filter(str.isdigit, curr_filename.split("/")[-1])))

        # 改为判断字符数量 地址长度是否相同
        # try:
        #     prev_num = len(prev_filename.split("/")[-1])
        #     curr_num = len(curr_filename.split("/")[-1]) + 1 # 配合后面的代码，不用再改了
        except ValueError:
            print(f"文件名格式不符合要求，无法判断连续性：{prev_filename}, {curr_filename}")
            continue

        # 遇到了不连续的情况，切换是否进入广告状态
        if curr_num != prev_num + 1:
            Ad_in = not Ad_in
            if Ad_in:  # 进入广告状态
                print("ad in after", ts_filenames[j-1].strip())
                print(f"{curr_filename.strip()},行号in:{ts_line_numbers[j]}")
                ad_lines_list.append(ts_line_numbers[j] - 1) # 把#EXTINF行也加进去
                ad_lines_list.append(ts_line_numbers[j])
            else:  # 退出广告状态
                print(f"ad area +1 {ts_filenames[j-1].strip()}")
                _ = input("continue")
        else:
            if Ad_in:
                print(f"{curr_filename.strip()},行号-:{ts_line_numbers[j]}")
                ad_lines_list.append(ts_line_numbers[j] - 1) # 把#EXTINF行也加进去
                ad_lines_list.append(ts_line_numbers[j])
            else:
                pass # 正常行
    print(ad_lines_list)

    # 这里也可以返回一个list，然后在主函数中写入文件
    lines_no_ad = [lines[i-1] for i in range(1, len(lines)+1) if i not in ad_lines_list] # 从1开始计数, 和lines保持一致
    return ''.join(lines_no_ad)  # 返回无广告的 m3u8 文件内容
    
    # 保存无广告的 m3u8 文件
    # with open("noad.m3u8", 'w', encoding='utf-8') as file:
    #     for item in lines_no_ad:
    #         # 将元素写入文件，无需添加换行符, splitlines(keepends=True)
    #         file.write(item)

def get_domain_by_url(url):
    """
    拆分 URL, 获取协议、域名、路径、文件名和后缀。其实urllib.parse import urljoin可以解决大部分问题
    :param url: 完整的 URL
    :return: 元组 (协议+域名, 路径, 文件名, 后缀)
    """
    url_sche = urllib.parse.urlparse(url).scheme  # 协议，如 https
    url_netloc = urllib.parse.urlparse(url).netloc  # 域名，如 www.123.com
    url_path = urllib.parse.urlparse(url).path  # 路径，如 /2134/45/a.html
    uname = os.path.basename(url_path)  # 全文件名，如 a.html
    suffix = os.path.splitext(uname)  # 后缀，如 ('.html',)

    return f"{url_sche}://{url_netloc}", url_path, uname, suffix


def extract_m3u8_from_playpage(url_in):
    """ 内部使用的函数，
    从播放页面 URL 中提取 m3u8 地址。
    :param url_in: 播放页面 URL
    :return: 元组 (m3u8_url, "m3u8") 或 (错误信息, "err")
    """
    try:
        # 发送 HTTP 请求

        response = requests.get(url_in, headers=fb.rnd_header())
        response.encoding = 'utf-8'  # 确保正确的编码
        # print(response.text)
        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # 查找指定的 div 标签 dzyy.cc
        div_tag = soup.find('div', class_='hl-player-wrap embed-responsive embed-responsive-16by9 by-qq362695000 clearfix')
        if not div_tag:
            return ""

        # 查找第一个 script 标签
        script_tag = div_tag.find('script')
        if not script_tag:
            return ""

        # 提取 JavaScript 代码
        jscode = script_tag.string
        if not jscode:
            return ""

        # 使用正则表达式查找 player_aaaa 对象
        match = re.search(r'var player_aaaa=(.*)', jscode)
        if not match:
            return ""

        # 提取 player_aaaa 对象中的 url 值
        js_str = match.group(1)
        url_match = re.search(r'"url":"([^"]+)"', js_str)
        if not url_match:
            return ""
        # 处理 url 并检查是否为 m3u8 格式
        url_m = url_match.group(1).replace("\\", "")
        if url_m.endswith("m3u8"):
            return url_m
        else:
            return url_m  # ayiqi，这里返回的是非m3u8的url，可能是.html, 暂时先把这个html写在u字段里

        ## ccy1.com
        # ifrdiv = soup.find("div", id="tem_vod_box")  # script 的div
        # if ifrdiv:
        #     scriptm3u8 = ifrdiv.find_all("script")[4].string
        #     matchline = re.search(r'var temPlayRenderCode(.*)', scriptm3u8)
        #     varline = matchline.group(1)
        #     srcarea = re.search(r'url=([^\']+)', varline)
        #     m3url = srcarea.group(1)
        #     print(m3url)
        #     return m3url
        # else:
        #     return "aaa"
    except Exception as e:
        print(e)
        return "eee"


def mklocaldir(subpath):
    """
    创建本地目录，如果目录不存在则创建。
    :param subpath: 子目录路径
    """
    # 新建日期文件夹，如果没有指定文件存储位置，就用年月日创建文件夹，否则用指定的文件夹
    if not subpath:  # ""
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
    :param filepath: 文件路径
    :return: 字典，键为 URL, 值为标题
    """
    listDict = dict()
    os.chdir(".")
    with open(filepath, encoding='utf-8') as f_menulist:
        try:
            lines = f_menulist.readlines()  # 读取全部内容，并以列表方式返回
            filesum = len(lines)  # 一共有多少章，即目录文件有多少行
            print("Total: " + str(filesum) + " links in menulist")

            # 读取全部或者一定的行数
            linesToRead = filesum
            linesStart = 0  # 从哪一行开始读取。从第一行开始则写0.
            for i in range(linesStart, linesStart + linesToRead):
                # 获取网址和每章标题
                currentline = lines[i].split("|")
                currenturl = currentline[0]
                currenttitle = currentline[1].strip()  # 去除换行符
                listDict[currenturl] = currenttitle
        finally:
            f_menulist.close()

    return listDict


def clean_unicode(text):
    """
    清理 ambiguous Unicode 字符。
    :param text: 输入的字符串
    :return: 清理后的字符串
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
    # 替换 replace_dict 中定义的字符
    for key, value in replace_dict.items():
        text = text.replace(key, value)
    text = text.replace('\u2028', ' ').replace('\u2029', ' ')  # 替换 Unicode 字符 不寻常的换行符 vscode提示的东西 LS PS
    
    return "".join(
        char for char in unicodedata.normalize("NFKC", text) if not unicodedata.category(char).startswith("C")
    )


def split_file_path(file_full_path):
    """
    拆分文件路径，获取目录、文件名和后缀。
    :param file_full_path: 完整文件路径
    :return: 元组 (目录, 仅文件名, 后缀)
    """
    directory = os.path.abspath(file_full_path)  # 获取文件所在的目录路径
    filename_with_ext = os.path.basename(file_full_path)  # 获取文件名（包含扩展名）
    filename, extension = os.path.splitext(filename_with_ext)  # 分离文件名和扩展名
    return directory, filename, extension



def get_second_layer_m3u8(url):
    """
    获取第二层 m3u8 地址
    :param url: 第一层 m3u8 地址
    :return: 第二层 m3u8 地址或 None
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