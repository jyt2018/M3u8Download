"""
功能:
1. 解析m3u8文件
2. 根据给定的时间范围过滤m3u8文件,并下载一个精简后的m3u8文件, 然后需要使用m3u8downloader下载视频片段
3. 创建新的m3u8文件, 依次写入m3u_head, clip_list, "#EXT-X-ENDLIST"
4. 更改后的m3u8文件保存为本地文件, 文件名用t1, t2标识
5. 运行时输入m3u8文件的URL或本地路径, 以及开始和结束时间
6. 过滤后的m3u8文件保存在当前目录下
7. key URI的处理改为绝对路径
8. 代码中的get_domain_by_url函数是lib_downvideo.py中的函数
author: jyt2018@github
"""
import M3u8Download
import lib_downvideo as dv
import re
import requests

def parse_time(time_str):
    """
    解析时间字符串, 格式为hh:mm:ss
    :param time_str: 时间字符串
    :return: 以秒为单位的时间
    """
    h, m, s = map(int, time_str.split(':'))
    return h * 3600 + m * 60 + s

def filter_m3u8(m3u8_url, t1, t2):
    """
    根据给定的时间范围过滤m3u8文件
    :param m3u8_url: m3u8文件的URL或本地路径
    :param t1: 开始时间, 格式为hh:mm:ss
    :param t2: 结束时间, 格式为hh:mm:ss
    :return: 过滤后的m3u8文件路径
    """
    t1_sec = parse_time(t1)  # 将开始时间转换为秒
    t2_sec = parse_time(t2)  # 将结束时间转换为秒
    m3u_head = []  # 存储m3u8文件头部信息
    clip_list = []  # 存储符合时间范围的片段信息
    start_found = False  # 标记是否找到开始时间
    end_found = False  # 标记是否找到结束时间

    # 读取m3u8文件内容
    if m3u8_url.startswith('http'):
        response = requests.get(m3u8_url)
        lines = response.text.splitlines()
    else:
        with open(m3u8_url, 'r') as file:
            lines = file.readlines()

    current_time = 0  # 当前时间初始化为0
    for j, line in enumerate(lines):
        if line.startswith('#EXTINF'):
            match = re.search(r'#EXTINF:(\d+\.?\d*),', line)
            if match:
                duration = float(match.group(1))  # 获取片段持续时间
                end_time = current_time + duration  # 计算片段结束时间
                if not start_found and t1_sec <= end_time:
                    start_found = True  # 找到开始时间
                    if m3u_head:
                        m3u_head.append(line)
                elif start_found and not end_found and t2_sec >= current_time and t2_sec < end_time:
                    end_found = True  # 找到结束时间
                if start_found and not end_found:
                    clip_list.append(line)  # 添加片段信息
                if end_found:
                    break
                current_time = end_time  # 更新当前时间
        elif line.startswith('#EXT-X-KEY'):
            key_uri_match = re.search(r'URI="([^"]+)"', line)
            if key_uri_match:
                key_uri = key_uri_match.group(1)
                if not key_uri.startswith('http'):
                    if key_uri.startswith('/'):
                        key_uri = dv.get_domain_by_url(m3u8_url)[0] + key_uri
                    else:
                        key_uri = m3u8_url.rsplit(dv.get_domain_by_url(m3u8_url)[2])[0] + "/" + key_uri
                line = line.replace(key_uri_match.group(1), key_uri)
            m3u_head.append(line)  # 添加密钥信息
        elif line.startswith('#EXT-X-DISCONTINUITY'):
            # 跳过#EXT-X-DISCONTINUITY行
            continue
        else:
            if not start_found:
                if j == 0:
                    m3u_head.append(line)  # 添加头部信息
                else:
                    if not lines[j-1].startswith("#EXTINF"):
                        m3u_head.append(line)  # 添加头部信息
            else:
                if line.startswith('http'):
                    clip_list.append(line)  # 添加片段URL
                elif line.startswith('/'):
                    clip_list.append(dv.get_domain_by_url(m3u8_url)[0] + line[1:])  # 添加片段URL
                else:
                    clip_list.append(m3u8_url.rsplit(dv.get_domain_by_url(m3u8_url)[2])[0] + "/" + line)  # 添加片段URL

    output_file = f"filtered_{t1.replace(':', '')}_{t2.replace(':', '')}.m3u8"
    with open(output_file, 'w') as file:
        for line in m3u_head:
            file.write(line + '\n')  # 写入头部信息
        for line in clip_list:
            file.write(line + '\n')  # 写入片段信息
        file.write("#EXT-X-ENDLIST\n")  # 写入结束标志

    return output_file

if __name__ == "__main__":
    m3u8_url = input("input url, or local file location:")
    t1 = input("input start time, format hh:mm:ss")  # 开始时间
    t2 = input("input end time, format hh:mm:ss")  # 结束时间
    output_file = filter_m3u8(m3u8_url, t1, t2)
    print(f"Filtered m3u8 file saved as: {output_file}")
    download = input("do you want to download the video clips? (y/n) ")
    if download.lower() == 'y':
        # 获取output_file的本地文件路径
        output_file_local = dv.split_file_path(output_file)[0]
        print(f"output_file_local: {output_file_local}")
        # 输出文件的名称
        output_file_name = dv.split_file_path(output_file)[1].split('.')[0]
        print(f"output_file_name: {output_file_name}")
        # 调用M3u8Download下载视频片段
        M3u8Download.M3u8Download(output_file_local, output_file_name)
