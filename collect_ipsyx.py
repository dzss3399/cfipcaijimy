#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绕过 403，从 https://stock.hostmonit.com/CloudFlareYes 提取 IP → yxip.txt
使用系统 curl 模拟真实 Chrome 浏览器
"""

import re
import subprocess
import sys
from datetime import datetime

URL = "https://stock.hostmonit.com/CloudFlareYes"
OUTPUT_FILE = "yxip.txt"

def fetch_with_curl():
    """使用 curl 完整模拟 Chrome 浏览器请求"""
    cmd = [
        'curl', '-s', '--compressed', '--max-time', '20',
        '--tlsv1.2',
        '--http2',
        '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        '-H', 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8',
        '-H', 'Accept-Encoding: gzip, deflate, br',
        '-H', 'Connection: keep-alive',
        '-H', 'Upgrade-Insecure-Requests: 1',
        '-H', 'Sec-Fetch-Dest: document',
        '-H', 'Sec-Fetch-Mode: navigate',
        '-H', 'Sec-Fetch-Site: none',
        '-H', 'Sec-Fetch-User: ?1',
        '-H', 'Priority: u=0, i',
        URL
    ]

    try:
        print("正在使用 curl 访问页面（模拟 Chrome）...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        
        if result.returncode != 0:
            print(f"curl 执行失败: {result.stderr}")
            return None

        if "403" in result.stdout or "Forbidden" in result.stdout:
            print("检测到 403，但 curl 仍可能返回内容...")
        
        if len(result.stdout) < 500:
            print(f"页面内容过短（{len(result.stdout)} 字节），可能被拦截")
            return None

        print(f"页面获取成功！大小: {len(result.stdout)} 字符")
        return result.stdout

    except subprocess.TimeoutExpired:
        print("请求超时")
        return None
    except Exception as e:
        print(f"curl 异常: {e}")
        return None


def extract_ips(text):
    """提取并验证 IPv4 和 IPv6"""
    ipv4_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    ipv6_pattern = r'\b(?:[0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4}\b'

    ipv4_matches = re.findall(ipv4_pattern, text)
    ipv6_matches = re.findall(ipv6_pattern, text)

    valid_ipv4 = set()
    for ip in ipv4_matches:
        try:
            parts = list(map(int, ip.split('.')))
            if len(parts) == 4 and all(0 <= p <= 255 for p in parts):
                if not (ip.startswith('0.') or ip.startswith('127.') or ip == '255.255.255.255'):
                    valid_ipv4.add(ip)
        except:
            continue

    valid_ipv6 = {ip for ip in ipv6_matches if ':' in ip and not ip.startswith(':') and not ip.endswith(':')}

    all_ips = sorted(valid_ipv4.union(valid_ipv6))
    return all_ips


def save_ips(ips):
    """保存到 yxip.txt"""
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"# CloudFlareYes IP List\n")
        f.write(f"# 来源: {URL}\n")
        f.write(f"# 更新时间: {now}\n")
        f.write(f"# 共 {len(ips)} 个有效 IP\n\n")
        for ip in ips:
            f.write(ip + '\n')
    print(f"成功保存 {len(ips)} 个 IP → {OUTPUT_FILE}")


def main():
    html = fetch_with_curl()
    if not html:
        print("无法获取页面内容，脚本退出。")
        print("\n建议检查：")
        print("  1. 网络是否正常")
        print("  2. curl 是否已安装：`curl --version`")
        print("  3. 网站是否临时维护")
        sys.exit(1)

    ips = extract_ips(html)
    if not ips:
        print("未提取到任何有效 IP。")
        return

    save_ips(ips)


if __name__ == "__main__":
    main()
