#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新解密TS文件脚本

功能:
    使用指定的key文件解密目录中的所有ts文件，覆盖原文件
    采用ffmpeg方式进行解密，无需安装额外的加密库

使用方法:
    python 0__redecription.py

注意:
    - 需要安装ffmpeg并添加到系统路径
    - 脚本会自动检测ffmpeg是否可用
"""

import os
import sys
import subprocess
import tempfile
import shutil

# 配置
KEY_FILE = r"F:\M3u8Download\夜色人生\key"
TS_DIR = r"F:\M3u8Download\夜色人生"


def check_ffmpeg():
    """检查ffmpeg是否可用"""
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("检测到 ffmpeg 已安装")
            return True
    except FileNotFoundError:
        pass
    
    print("错误: 未找到 ffmpeg，请确保 ffmpeg 已安装并添加到系统路径")
    return False


def read_key(key_file):
    """读取密钥文件"""
    if not os.path.exists(key_file):
        raise FileNotFoundError(f"密钥文件不存在: {key_file}")
    
    with open(key_file, 'rb') as f:
        key = f.read()
    
    print(f"读取密钥文件: {key_file}")
    print(f"密钥长度: {len(key)} 字节")
    
    return key


def get_ts_files(directory):
    """获取目录中的所有ts文件"""
    if not os.path.exists(directory):
        raise FileNotFoundError(f"目录不存在: {directory}")
    
    ts_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.ts'):
                ts_files.append(os.path.join(root, file))
    
    ts_files.sort()
    print(f"找到 {len(ts_files)} 个TS文件")
    return ts_files


def create_temp_m3u8(ts_file, key_file, temp_dir):
    """
    为单个ts文件创建临时m3u8文件
    这样ffmpeg就可以使用它来解密
    """
    ts_filename = os.path.basename(ts_file)
    key_filename = os.path.basename(key_file)
    
    # 复制key文件到临时目录
    temp_key = os.path.join(temp_dir, key_filename)
    shutil.copy2(key_file, temp_key)
    
    # 复制ts文件到临时目录
    temp_ts = os.path.join(temp_dir, ts_filename)
    shutil.copy2(ts_file, temp_ts)
    
    # 创建m3u8内容
    # 注意：这里我们使用简单的m3u8格式，包含key信息
    m3u8_content = f"""#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-KEY:METHOD=AES-128,URI="{key_filename}",IV=0x00000000000000000000000000000000
#EXTINF:10.0,
{ts_filename}
#EXT-X-ENDLIST
"""
    
    m3u8_path = os.path.join(temp_dir, 'temp.m3u8')
    with open(m3u8_path, 'w', encoding='utf-8') as f:
        f.write(m3u8_content)
    
    return m3u8_path


def decrypt_ts_with_ffmpeg(ts_file, key_file):
    """
    使用ffmpeg解密单个ts文件
    
    方法：
    1. 创建一个临时目录
    2. 复制ts文件和key文件到临时目录
    3. 创建一个临时m3u8文件，指向这些文件
    4. 使用ffmpeg读取m3u8并输出解密后的ts
    5. 用解密后的文件覆盖原文件
    """
    original_size = os.path.getsize(ts_file)
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建临时m3u8文件
        m3u8_path = create_temp_m3u8(ts_file, key_file, temp_dir)
        
        # 输出文件路径（临时目录中）
        temp_output = os.path.join(temp_dir, 'decrypted.ts')
        
        # 构建ffmpeg命令
        # 使用 -c copy 进行流复制（不重新编码）
        cmd = [
            'ffmpeg',
            '-loglevel', 'error',
            '-allowed_extensions', 'ALL',
            '-i', m3u8_path,
            '-c', 'copy',
            '-bsf:v', 'h264_mp4toannexb',
            '-f', 'mpegts',
            temp_output
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=temp_dir
            )
            
            if result.returncode != 0:
                print(f"  ffmpeg错误: {result.stderr}")
                return False
            
            # 检查输出文件是否存在
            if not os.path.exists(temp_output) or os.path.getsize(temp_output) == 0:
                print(f"  错误: 解密失败，输出文件为空或不存在")
                return False
            
            # 读取解密后的内容
            with open(temp_output, 'rb') as f:
                decrypted_data = f.read()
            
            # 检查解密后的数据是否以TS同步字节开头 (0x47)
            if decrypted_data and decrypted_data[0] != 0x47:
                print(f"  警告: 解密后的数据不以TS同步字节开头")
                print(f"  第一个字节: 0x{decrypted_data[0]:02X} (应为 0x47)")
            
            # 覆盖原文件
            with open(ts_file, 'wb') as f:
                f.write(decrypted_data)
            
            new_size = len(decrypted_data)
            print(f"  解密完成: {os.path.basename(ts_file)} ({original_size} -> {new_size} 字节)")
            return True
            
        except Exception as e:
            print(f"  错误: {e}")
            import traceback
            traceback.print_exc()
            return False


def decrypt_ts_with_ffmpeg_direct(ts_file, key_file):
    """
    使用ffmpeg的另一种方式解密：使用外部key文件
    这种方法更简单，不需要创建m3u8文件
    
    注意：这种方法可能不适用于所有情况，因为ffmpeg的ts demuxer
    可能不直接支持外部key解密
    """
    original_size = os.path.getsize(ts_file)
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        # 输出文件路径
        temp_output = os.path.join(temp_dir, 'decrypted.ts')
        
        # 尝试使用ffmpeg的crypto协议
        # 这种方法需要知道IV，并且格式比较复杂
        
        # 替代方案：创建一个简单的m3u8文件（和上面的方法一样）
        # 因为这是最可靠的方法
        
        # 先复制文件到临时目录
        temp_ts = os.path.join(temp_dir, os.path.basename(ts_file))
        temp_key = os.path.join(temp_dir, os.path.basename(key_file))
        shutil.copy2(ts_file, temp_ts)
        shutil.copy2(key_file, temp_key)
        
        # 创建m3u8
        m3u8_content = f"""#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-KEY:METHOD=AES-128,URI="{os.path.basename(key_file)}"
#EXTINF:10.0,
{os.path.basename(ts_file)}
#EXT-X-ENDLIST
"""
        
        m3u8_path = os.path.join(temp_dir, 'temp.m3u8')
        with open(m3u8_path, 'w', encoding='utf-8') as f:
            f.write(m3u8_content)
        
        # 构建ffmpeg命令
        cmd = [
            'ffmpeg',
            '-loglevel', 'error',
            '-allowed_extensions', 'ALL',
            '-i', m3u8_path,
            '-c', 'copy',
            '-f', 'mpegts',
            temp_output
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=temp_dir
            )
            
            if result.returncode != 0:
                print(f"  ffmpeg错误: {result.stderr}")
                return False
            
            if not os.path.exists(temp_output) or os.path.getsize(temp_output) == 0:
                print(f"  错误: 解密失败，输出文件为空或不存在")
                return False
            
            # 读取并覆盖
            with open(temp_output, 'rb') as f:
                decrypted_data = f.read()
            
            with open(ts_file, 'wb') as f:
                f.write(decrypted_data)
            
            new_size = len(decrypted_data)
            print(f"  解密完成: {os.path.basename(ts_file)} ({original_size} -> {new_size} 字节)")
            return True
            
        except Exception as e:
            print(f"  错误: {e}")
            return False


def main():
    """主函数"""
    print("=" * 60)
    print("TS文件重新解密工具 (ffmpeg方式)")
    print("=" * 60)
    
    # 检查ffmpeg
    if not check_ffmpeg():
        sys.exit(1)
    
    # 读取密钥
    try:
        key = read_key(KEY_FILE)
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)
    
    # 检查密钥长度
    if len(key) not in [16, 24, 32]:
        print(f"警告: 密钥长度 {len(key)} 字节不是标准的AES密钥长度 (16/24/32)")
    
    # 获取TS文件列表
    try:
        ts_files = get_ts_files(TS_DIR)
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)
    
    if not ts_files:
        print("错误: 没有找到TS文件")
        sys.exit(1)
    
    print(f"\n开始解密 {len(ts_files)} 个文件...")
    print("-" * 60)
    
    # 解密每个文件
    success_count = 0
    for i, ts_file in enumerate(ts_files, 1):
        print(f"[{i}/{len(ts_files)}] 处理: {ts_file}")
        try:
            # 使用第一种方法（带IV的m3u8）
            if decrypt_ts_with_ffmpeg(ts_file, KEY_FILE):
                success_count += 1
        except Exception as e:
            print(f"  错误: {e}")
            import traceback
            traceback.print_exc()
    
    print("-" * 60)
    print(f"解密完成: 成功 {success_count}/{len(ts_files)} 个文件")
    print("=" * 60)


if __name__ == "__main__":
    main()
