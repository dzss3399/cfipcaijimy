#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import subprocess
from datetime import datetime

URL = "https://stock.hostmonit.com/CloudFlareYes"
OUTPUT_FILE = "yxip.txt"

# 使用 curl 绕过 JS 检测（更稳定）
def fetch_page_with_curl():
    cmd = [
        'curl', '-s', '--compressed',
        '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        '-H', 'Accept-Language: en-US,en;q=0.5',
        '-H', 'Accept-Encoding: gzip, deflate',
        '-H', 'Connection: keep-alive',
        '-H', 'Upgrade-Insecure-Requests: 1',
        URL
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if result.returncode == 0 and "403" not in result.stdout and len(result.stdout) > 100:
            return result.stdout
        else:
            print("curl 失败或返回内容过短")
            return None
    except Exception as e:
        print(f"curl 执行失败: {e}")
        return None

def extract_ips(text):
    # 提取 IPv4
    ipv4_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    ipv4_list = re.findall(ipv4_pattern, text)

    # 提取 IPv6
    ipv6_pattern = r'\b(?:[0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4}\b'
    ipv6_list = re.findall(ipv6_pattern, text)

    # 过滤有效 IPv4
    valid_ipv4 = []
    for ip in ipv4_list:
        parts = list(map(int, ip.split('.')))
        if all(0 <= p <= 255 for p in parts) and not ip.startswith('0.'):
            if ip != '255.255.255.255':
                valid_ipv4.append(ip)

    # 过滤有效 IPv6
    valid_ipv6 = [ip for ip in ipv6_list if ':' in ip and not ip.startswith(':') and not ip.endswith(':')]

    return valid_ipv4, valid_ipv6

def main():
    print(f"正在获取 {URL} ...")
    html = fetch_page_with_curl()

    if not html:
        print("无法获取页面内容，请检查网络或目标网站是否启用更强反爬")
        sys.exit(1)

    print(f"页面获取成功！长度: {len(html)} 字符")

    ipv4_ips, ipv6_ips = extract_ips(html)
    all_ips = sorted(set(ipv4_ips + ipv6_ips))

    # 写入文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# CloudFlareYes IP List\n")
        f.write(f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 共 {len(all_ips)} 个 IP\n\n")
        for ip in all_ips:
            f.write(ip + '\n')

    print(f"成功！共提取 {len(all_ips)} 个 IP，已保存到 {OUTPUT_FILE}")
    print(f"   IPv4: {len(ipv4_ips)} 个")
    print(f"   IPv6: {len(ipv6_ips)} 个")

if __name__ == "__main__":
    main()
