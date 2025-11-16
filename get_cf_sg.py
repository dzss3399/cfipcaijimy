#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloudflare 官方 IPv4 → 每段 500 IP → 测速（SG/US/HK/JP）→ 各取最快 30 个 → SG.txt / US.txt / HK.txt / JP.txt
"""
import time
import requests
import ipaddress
import subprocess
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 配置 ====================
IPV4_URL = "https://www.cloudflare.com/ips-v4"
TIMEOUT = 6
MAX_WORKERS = 150
IPS_PER_CIDR = 300
TOP_N = 30

# 测速节点（轻量、稳定、全球分布）
TEST_POINTS = {
    'SG': {'host': 'sgp-ping.vultr.com', 'location': '新加坡'},
    'US': {'host': 'nj-us-ping.vultr.com', 'location': '美国 (新泽西)'},
    'HK': {'host': 'hnd-jp-ping.vultr.com', 'location': '香港 (近邻)'},  # 香港无专用，借日本
    'JP': {'host': 'hnd-jp-ping.vultr.com', 'location': '日本 (东京)'},
}
# ==============================================


def keep_alive():
    url = "https://dtt3399-myspace.hf.space"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print(f"成功保活！状态码: {response.status_code} | 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"失败！状态码: {response.status_code}")
    except Exception as e:
        print(f"错误: {e}")




def get_ipv4_cidrs():
    """获取官方 IPv4 CIDR 列表"""
    try:
        r = requests.get(IPV4_URL, timeout=10)
        r.raise_for_status()
        return [line.strip() for line in r.text.strip().split('\n') if line.strip()]
    except Exception as e:
        print(f"获取 CIDR 失败: {e}")
        return []

def expand_cidr_random(cidr, count=IPS_PER_CIDR):
    """从 CIDR 随机取 count 个主机 IP"""
    try:
        net = ipaddress.ip_network(cidr, strict=False)
        if net.num_addresses <= 2:
            return []
        hosts = list(net.hosts())
        if len(hosts) <= count:
            return [str(ip) for ip in hosts]
        return [str(ip) for ip in random.sample(hosts, count)]
    except:
        return []

def test_ip_geo(ip, host):
    """测速指定节点"""
    cmd = [
        'curl', '-s', '-o', '/dev/null', '-w', '%{time_total}',
        '--max-time', str(TIMEOUT),
        '--resolve', f"{host}:80:{ip}",
        f"http://{host}"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT + 2)
        if result.returncode == 0:
            return round(float(result.stdout.strip()) * 1000, 2), ip
        return float('inf'), ip
    except:
        return float('inf'), ip

def main():
    print("正在获取 Cloudflare 官方 IPv4 CIDR...")
    # 运行一次
    keep_alive()
    cidrs = get_ipv4_cidrs()
    if not cidrs:
        print("获取失败")
        return

    print(f"共 {len(cidrs)} 个 CIDR，开始展开 IP（每段 {IPS_PER_CIDR} 个）...")
    all_ips = []
    for i, cidr in enumerate(cidrs, 1):
        ips = expand_cidr_random(cidr, IPS_PER_CIDR)
        all_ips.extend(ips)
        print(f"  [{i:2d}/{len(cidrs)}] {cidr} → {len(ips)} IPs")

    if not all_ips:
        print("未生成任何 IP")
        return

    # 为每个地区测速
    results = {geo: [] for geo in TEST_POINTS}
    for geo, info in TEST_POINTS.items():
        host = info['host']
        location = info['location']
        print(f"\n开始测速 → {location}（{host}）...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(test_ip_geo, ip, host): ip for ip in all_ips}
            for future in as_completed(futures):
                lat, ip = future.result()
                if lat != float('inf'):
                    results[geo].append((lat, ip))
                    print(f"  {ip} → {lat} ms ({location})")
                else:
                    print(f"  {ip} → 超时")

    # 排序并取前 TOP_N
    best = {}
    for geo in TEST_POINTS:
        results[geo].sort()
        best[geo] = results[geo][:TOP_N]

    # 写入文件
    for geo, data in best.items():
        filename = f"{geo}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            for _, ip in data:
                f.write(ip + '\n')
        print(f"\n{TEST_POINTS[geo]['location']} 最快 {len(data)} 个已保存 → {filename}")

    print("\n所有任务完成！文件列表：SG.txt US.txt HK.txt JP.txt")

if __name__ == "__main__":
    main()
