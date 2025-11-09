#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloudflare 官方 IP → 测速 → 选最快 10 个 → yxip.txt（纯 IP）
无时间、无注释、无浏览器、无反爬
"""

import requests
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置
IPV4_URL = "https://www.cloudflare.com/ips-v4"
IPV6_URL = "https://www.cloudflare.com/ips-v6"
OUTPUT_FILE = "yxip.txt"
TIMEOUT = 5          # 测速超时（秒）
MAX_WORKERS = 50     # 并发数
TOP_N = 10           # 选最快 N 个

def get_cf_ips():
    """获取 Cloudflare 官方 IP 范围（CIDR）"""
    def fetch(url):
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.text.strip().split('\n')
        except:
            return []
    
    ipv4 = fetch(IPV4_URL)
    ipv6 = fetch(IPV6_URL)
    return [line.strip() for line in ipv4 + ipv6 if line.strip()]

def expand_cidr(cidr):
    """将 CIDR 转为单个 IP（取第一个 IP）"""
    import ipaddress
    try:
        net = ipaddress.ip_network(cidr, strict=False)
        return str(net.network_address)
    except:
        return None

def get_all_ips():
    """获取所有起始 IP"""
    cidrs = get_cf_ips()
    ips = []
    for cidr in cidrs:
        ip = expand_cidr(cidr)
        if ip:
            ips.append(ip)
    return ips

def test_ip(ip):
    """测速：返回 (延迟ms, IP)"""
    cmd = ['curl', '-s', '-o', '/dev/null', '-w', '%{time_total}', '--max-time', str(TIMEOUT)]
    url = f"http://[{ip}]" if ':' in ip else f"http://{ip}"
    cmd += [url]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT + 2)
        if result.returncode == 0:
            latency = round(float(result.stdout.strip()) * 1000, 2)
            return latency, ip
        return float('inf'), ip
    except:
        return float('inf'), ip

def main():
    print("正在获取 Cloudflare 官方 IP...")
    ips = get_all_ips()
    if not ips:
        print("获取失败")
        return
    print(f"共 {len(ips)} 个 IP，开始测速...")

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(test_ip, ip): ip for ip in ips}
        for future in as_completed(futures):
            lat, ip = future.result()
            if lat != float('inf'):
                results.append((lat, ip))
                print(f"  {ip} → {lat} ms")
            else:
                print(f"  {ip} → 超时")

    results.sort()
    best = [ip for _, ip in results[:TOP_N]]

    # 只写 IP，一行一个
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for ip in best:
            f.write(ip + '\n')

    print(f"\n完成！最快 {len(best)} 个 IP 已保存 → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
