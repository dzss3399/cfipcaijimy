#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 https://stock.hostmonit.com/CloudFlareYes 页面提取 IP 并保存到 yxip.txt
"""

import re
import requests
from datetime import datetime

# ==================== 配置 ====================
URL = "https://stock.hostmonit.com/CloudFlareYes"
OUTPUT_FILE = "yxip.txt"
TIMEOUT = 15
# ==============================================

def get_page_content():
    """使用真实浏览器头获取页面内容"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/130.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
    }

    try:
        print(f"正在访问: {URL}")
        response = requests.get(URL, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        print(f"页面获取成功！大小: {len(response.text)} 字符")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None


def extract_ips(text):
    """提取并过滤有效的 IPv4 和 IPv6"""
    # IPv4 正则
    ipv4_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    # IPv6 正则（简化版，匹配常见格式）
    ipv6_pattern = r'\b(?:[0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4}\b'

    ipv4_list = re.findall(ipv4_pattern, text)
    ipv6_list = re.findall(ipv6_pattern, text)

    valid_ipv4 = set()
    for ip in ipv4_list:
        octets = ip.split('.')
        if len(octets) != 4:
            continue
        if all(0 <= int(o) <= 255 for o in octets):
            if not (ip.startswith('0.') or ip == '255.255.255.255' or ip.startswith('127.')):
                valid_ipv4.add(ip)

    valid_ipv6 = {ip for ip in ipv6_list if ':' in ip and not ip.startswith(':') and not ip.endswith(':')}

    all_ips = sorted(valid_ipv4.union(valid_ipv6))
    return all_ips


def save_to_file(ips):
    """保存 IP 到 yxip.txt，带注释头"""
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"# CloudFlareYes IP List\n")
        f.write(f"# 来源: {URL}\n")
        f.write(f"# 更新时间: {now}\n")
        f.write(f"# 共 {len(ips)} 个 IP\n\n")
        for ip in ips:
            f.write(ip + '\n')
    print(f"成功保存 {len(ips)} 个 IP 到 {OUTPUT_FILE}")


def main():
    html = get_page_content()
    if not html:
        print("无法获取页面内容，脚本退出。")
        return

    ips = extract_ips(html)
    if not ips:
        print("未提取到任何有效 IP。")
        return

    save_to_file(ips)


if __name__ == "__main__":
    main()
