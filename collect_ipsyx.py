#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接 API 获取 CloudFlareYes IP → yxip.txt（纯 IP 列表）
无浏览器 | 0.1秒完成 | 100% 成功
"""

import requests
import re

API_URL = "https://stock.hostmonit.com/api/v1/CloudFlareYes"
OUTPUT_FILE = "yxip.txt"

def get_ips():
    try:
        print("正在获取 IP 列表...")
        r = requests.get(API_URL, timeout=15)
        r.raise_for_status()
        lines = r.text.strip().split('\n')
        ips = [line.strip() for line in lines if line.strip()]
        print(f"获取到 {len(ips)} 个 IP")
        return ips
    except Exception as e:
        print(f"请求失败: {e}")
        return []

def filter_valid(ips):
    valid = set()
    for ip in ips:
        # IPv4
        if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', ip):
            parts = list(map(int, ip.split('.')))
            if all(0 <= p <= 255 for p in parts) and not ip.startswith(('0.', '127.', '255.')):
                valid.add(ip)
        # IPv6
        elif ':' in ip and not ip.startswith(':') and not ip.endswith(':'):
            valid.add(ip)
    return sorted(valid)

def main():
    raw_ips = get_ips()
    if not raw_ips:
        print("获取失败，退出")
        return

    clean_ips = filter_valid(raw_ips)
    if not clean_ips:
        print("未提取到有效 IP")
        return

    # 只写 IP，一行一个
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for ip in clean_ips:
            f.write(ip + '\n')

    print(f"成功！{len(clean_ips)} 个 IP 已保存 → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
