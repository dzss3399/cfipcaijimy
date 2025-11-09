#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
只提取 CloudFlareYes IP（JS 渲染），保存为纯 IP 列表（无时间、无注释）
"""

import re
from playwright.sync_api import sync_playwright

URL = "https://stock.hostmonit.com/CloudFlareYes"
OUTPUT_FILE = "yxip.txt"
WAIT_TIME = 5  # 等待 JS 加载

def fetch_page():
    with sync_playwright() as p:
        print("启动浏览器渲染 JS...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(WAIT_TIME * 1000)  # 等待 JS 渲染
        content = page.content()
        browser.close()
        print(f"页面渲染完成，大小: {len(content)} 字符")
        return content

def extract_ips(text):
    # 提取所有 IPv4 和 IPv6
    ipv4 = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', text)
    ipv6 = re.findall(r'\b(?:[0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4}\b', text)

    valid = set()
    # 过滤有效 IPv4
    for ip in ipv4:
        parts = list(map(int, ip.split('.')))
        if len(parts) == 4 and all(0 <= p <= 255 for p in parts):
            if not (ip.startswith('0.') or ip.startswith('127.') or ip == '255.255.255.255'):
                valid.add(ip)
    # 过滤有效 IPv6
    for ip in ipv6:
        if ':' in ip and not ip.startswith(':') and not ip.endswith(':'):
            valid.add(ip)
    return sorted(valid)

def main():
    html = fetch_page()
    ips = extract_ips(html)
    if not ips:
        print("未提取到 IP")
        return

    # 只写 IP，一行一个，无任何额外内容
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for ip in ips:
            f.write(ip + '\n')

    print(f"成功！{len(ips)} 个 IP 已保存到 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
