#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import sys

# 目标 URL
URL = "https://stock.hostmonit.com/CloudFlareYes"
OUTPUT_FILE = "yxip.txt"

# 请求头（模拟浏览器，防止被拒）
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
}

def extract_ips(text):
    """提取 IPv4 和 IPv6 地址"""
    ipv4_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    ipv6_pattern = r'\b(?:[0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4}\b'

    ipv4_list = re.findall(ipv4_pattern, text)
    ipv6_list = re.findall(ipv6_pattern, text)

    # 过滤无效 IPv4（如 0.0.0.0, 255.255.255.255）
    valid_ipv4 = []
    for ip in ipv4_list:
        octets = ip.split('.')
        if all(0 <= int(o) <= 255 for o in octets):
            if not (ip.startswith('0.') or ip == '255.255.255.255'):
                valid_ipv4.append(ip)

    # 过滤空或不完整 IPv6
    valid_ipv6 = [ip for ip in ipv6_list if ip.count(':') >= 1 and not ip.startswith(':') and not ip.endswith(':')]

    return valid_ipv4, valid_ipv6

def main():
    try:
        print(f"正在获取 {URL} ...")
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()
        print("页面获取成功！")

        ipv4_ips, ipv6_ips = extract_ips(response.text)

        # 去重并排序
        all_ips = sorted(set(ipv4_ips + ipv6_ips))

        # 写入文件
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for ip in all_ips:
                f.write(ip + '\n')

        print(f"共提取 {len(all_ips)} 个 IP 地址，已保存到 {OUTPUT_FILE}")
        print(f"   IPv4: {len(ipv4_ips)} 个")
        print(f"   IPv6: {len(ipv6_ips)} 个")

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"处理出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
