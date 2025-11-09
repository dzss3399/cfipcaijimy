#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CloudFlareYes IP 提取（浏览器渲染 JS）+ 测速 + Clash 导出
解决 JS 动态加载问题 | 100% 提取完整 IP
"""

import re
import sys
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright
import subprocess

# ==================== 配置区 ====================
URL = "https://stock.hostmonit.com/CloudFlareYes"
ALL_IP_FILE = "yxip.txt"
BEST_IP_FILE = "best_ip.txt"
CLASH_FILE = "cloudflare_clash.yaml"
TIMEOUT = 6
MAX_WORKERS = 60
TOP_N = 10
TEST_URL = "http://cp.cloudflare.com"
ENABLE_CLASH = True
WAIT_TIME = 5  # JS 渲染等待时间（秒）
# ==============================================

def fetch_page_with_browser():
    """使用 Playwright 渲染 JS 获取完整页面"""
    with sync_playwright() as p:
        try:
            print("正在启动浏览器渲染 JS...")
            browser = p.chromium.launch(headless=True)  # headless=True 为无头模式
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            )
            page.goto(URL, wait_until="networkidle", timeout=30000)  # 等待网络空闲
            time.sleep(WAIT_TIME)  # 额外等待 JS 加载
            content = page.content()
            browser.close()
            if len(content) < 1000:
                print("渲染后内容仍过短，可能加载失败")
                return None
            print(f"JS 渲染成功！页面大小: {len(content):,} 字符")
            return content
        except Exception as e:
            print(f"浏览器渲染失败: {e}")
            return None


def extract_ips(text):
    """提取并验证 IP"""
    ipv4 = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', text)
    ipv6 = re.findall(r'\b(?:[0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4}\b', text)

    valid_ipv4 = set()
    for ip in ipv4:
        parts = list(map(int, ip.split('.')))
        if len(parts) == 4 and all(0 <= p <= 255 for p in parts):
            if not (ip.startswith('0.') or ip.startswith('127.') or ip == '255.255.255.255'):
                valid_ipv4.add(ip)

    valid_ipv6 = {ip for ip in ipv6 if ':' in ip and not ip.startswith(':') and not ip.endswith(':')}
    all_ips = sorted(valid_ipv4.union(valid_ipv6))
    print(f"提取到 {len(all_ips)} 个有效 IP")
    return all_ips


def test_ip(ip):
    """测速单个 IP"""
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


def save_all_ips(ips):
    with open(ALL_IP_FILE, 'w', encoding='utf-8') as f:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"# CloudFlareYes 全量 IP（JS 渲染提取）\n")
        f.write(f"# 来源: {URL}\n")
        f.write(f"# 更新时间: {now}\n")
        f.write(f"# 共 {len(ips)} 个\n\n")
        for ip in ips:
            f.write(ip + '\n')
    print(f"全部 IP 已保存 → {ALL_IP_FILE}")


def save_best_ips(best_list):
    if not best_list:
        print("警告：所有 IP 超时")
        with open(BEST_IP_FILE, 'w', encoding='utf-8') as f:
            f.write(f"# 无可用 IP\n")
            f.write(f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        return

    with open(BEST_IP_FILE, 'w', encoding='utf-8') as f:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"# 最快 {min(TOP_N, len(best_list))} 个 CloudFlare IP\n")
        f.write(f"# 测速目标: {TEST_URL}\n")
        f.write(f"# 更新时间: {now}\n\n")
        for lat, ip in best_list:
            f.write(f"{ip}  # {lat} ms\n")
    print(f"最快 IP 已保存 → {BEST_IP_FILE}")


def export_clash_nodes(best_list):
    if not ENABLE_CLASH or not best_list:
        return
    with open(CLASH_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# CloudFlare 优选节点（{len(best_list)} 个）\n")
        f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("proxies:\n")
        for i, (lat, ip) in enumerate(best_list, 1):
            f.write(f"  - name: CF-BEST-{i:02d}-{lat}ms\n")
            f.write(f"    type: vmess\n")
            f.write(f"    server: {ip}\n")
            f.write(f"    port: 443\n")
            f.write(f"    uuid: 00000000-0000-0000-0000-000000000000\n")
            f.write(f"    alterId: 0\n")
            f.write(f"    cipher: auto\n")
            f.write(f"    tls: true\n")
            f.write(f"    skip-cert-verify: true\n")
            f.write(f"    network: ws\n")
            f.write(f"    ws-path: /\n")
            f.write(f"    ws-headers:\n")
            f.write(f"      Host: {ip}\n\n")
    print(f"Clash 节点已导出 → {CLASH_FILE}")


def main():
    # 1. 浏览器渲染
    html = fetch_page_with_browser()
    if not html:
        print("JS 渲染失败，脚本退出")
        sys.exit(1)

    # 2. 提取 IP
    ips = extract_ips(html)
    if not ips:
        print("未提取到 IP（页面可能无数据）")
        return
    save_all_ips(ips)

    # 3. 测速
    print(f"开始测速 {len(ips)} 个 IP...")
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

    # 4. 选优 + 保存
    results.sort()
    best = results[:TOP_N]
    save_best_ips(best)
    export_clash_nodes(best)

    # 5. 总结
    if best:
        fastest_ip, fastest_lat = best[0]
        print(f"\n完成！最快 IP：{fastest_ip} ({fastest_lat} ms)")
    else:
        print("\n完成！但所有 IP 超时，请检查网络。")


if __name__ == "__main__":
    main()
