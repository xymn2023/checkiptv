import aiohttp
import asyncio
import re
import datetime
import time
import sys
from urllib.parse import urlparse, urljoin

# ================= 1. 全量抓取地址 (不省略) =================
# 这些是网段的种子，脚本会自动扫描每个地址对应的整个 C 段 (.1 - .254)
urls = [
   "http://1.87.218.1:7878",
   "http://1.195.130.1:9901",
   "http://1.195.131.1:9901",
   "http://1.197.250.1:9901",
   "http://39.152.171.1:9901",
   "http://47.109.181.1:88",
   "http://47.116.70.1:9901",
   "http://49.232.48.1:9901",
   "http://58.19.133.1:9901",
   "http://58.57.40.1:9901",
   "http://59.38.45.1:8090",
   "http://60.255.47.1:8801",
   "http://61.136.172.1:9901",
   "http://61.156.228.1:8154",
   "http://101.66.194.1:9901",
   "http://101.66.195.1:9901",
   "http://101.66.198.1:9901",
   "http://101.66.199.1:9901",
   "http://101.74.28.1:9901",
   "http://103.39.222.1:9999",
   "http://106.42.34.1:888",
   "http://106.42.35.1:888",
   "http://106.118.70.1:9901",
   "http://110.253.83.1:888",
   "http://111.8.242.1:8085",
   "http://111.9.163.1:9901",
   "http://112.14.1:9901",
   "http://112.16.14.1:9901",
   "http://112.26.18.1:9901",
   "http://112.27.145.1:9901",
   "http://112.91.103.1:9919",
   "http://112.99.193.1:9901",
   "http://112.234.23.1:9901",
   "http://112.132.160.1:9901",
   "http://113.57.93.1:9900",
   "http://113.195.162.1:9901",
   "http://113.201.61.1:9901",
   "http://115.48.160.1:9901",
   "http://115.59.9.1:9901",
   "http://116.128.242.1:9901",
   "http://117.174.99.1:9901",
   "http://119.125.131.1:9901",
   "http://121.19.134.1:808",
   "http://121.29.191.1:8000",
   "http://121.43.180.1:9901",
   "http://121.56.39.1:808",
   "http://122.227.100.1:9901",
   "http://123.13.247.1:7000",
   "http://123.54.220.1:9901",
   "http://123.129.70.1:9901",
   "http://123.130.84.1:8154",
   "http://123.139.57.1:9901",
   "http://123.182.60.1:9002",
   "http://124.152.247.1:2001",
   "http://125.42.148.1:9901",
   "http://125.42.228.1:9999",
   "http://125.43.244.1:9901",
   "http://125.125.236.1:9901",
   "http://159.75.75.1:8888",
   "http://171.9.68.1:8099",
   "http://180.213.174.1:9901",
   "http://182.114.48.1:9901",
   "http://182.114.49.1:9901",
   "http://182.114.214.1:9901",
   "http://182.120.229.1:9901",
   "http://183.10.180.1:9901",
   "http://183.131.246.1:9901",
   "http://183.166.62.1:81",
   "http://183.255.41.1:9901",
   "http://211.142.224.1:2023",
   "http://218.13.170.1:9901",
   "http://218.77.81.1:9901",
   "http://218.87.237.1:9901",
   "http://220.248.173.1:9901",
   "http://221.2.148.1:8154",
   "http://221.13.235.1:9901",
   "http://222.172.183.1:808",
   "http://222.243.221.1:9901",
   "http://223.241.247.1:9901"
]

# ================= 2. 频道排序权重与元数据 =================
LOGO_BASE = "https://gitee.com/mytv-android/myTVlogo/raw/main/img/"

# 严格定义排序顺序
SORT_WEIGHT = {
    "CCTV1": 1, "CCTV2": 2, "CCTV3": 3, "CCTV4": 4, "CCTV5": 5, "CCTV5+": 6,
    "CCTV6": 7, "CCTV7": 8, "CCTV8": 9, "CCTV9": 10, "CCTV10": 11,
    "CCTV11": 12, "CCTV12": 13, "CCTV13": 14, "CCTV14": 15, "CCTV15": 16,
    "CCTV16": 17, "CCTV17": 18, "CCTV4K": 19, "CCTV8K": 20,
    "北京卫视": 100, "东方卫视": 101, "湖南卫视": 102, "浙江卫视": 103, "江苏卫视": 104,
    "广东卫视": 105, "安徽卫视": 106, "山东卫视": 107, "湖北卫视": 108, "天津卫视": 109,
    "河北卫视": 110, "山西卫视": 111, "辽宁卫视": 112, "吉林卫视": 113, "黑龙江卫视": 114
}

# ================= 3. 辅助功能函数 =================

def clean_name(name):
    name = name.upper().replace(" ", "")
    # 提取 CCTV 数字
    match = re.search(r'(CCTV\d+[\+]?)', name)
    if match: return match.group(1)
    # 处理卫视
    if "卫视" in name:
        return name.split("-")[0].replace("HD", "").replace("高清", "")
    return name

def get_meta(name):
    cname = clean_name(name)
    if "CCTV" in cname:
        return cname, "央视频道", f"{LOGO_BASE}{cname}.png"
    elif "卫视" in cname:
        return cname, "卫视频道", f"{LOGO_BASE}{cname}.png"
    return cname, "其他频道", ""

def show_bar(curr, total, found, stage):
    length = 25
    progress = int(length * curr // total) if total > 0 else 0
    bar = "█" * progress + "░" * (length - progress)
    sys.stdout.write(f"\r{stage} |{bar}| {curr}/{total} 有效:{found}")
    sys.stdout.flush()

# ================= 4. 核心逻辑 =================

async def check_stream(session, url):
    """检测视频流是否真的能播放"""
    try:
        # 源项目通常带 playlive=1
        target = url + ("&" if "?" in url else "?") + "playlive=1"
        start = time.time()
        async with session.get(target, timeout=3) as r:
            if r.status == 200:
                # 读取一小段流，确认不是空壳
                chunk = await r.content.read(10240) 
                if chunk:
                    return True, int((time.time() - start) * 1000)
    except: pass
    return False, 9999

async def get_json_list(session, base_url):
    """从酒店 IPTV 系统接口获取 JSON 列表"""
    api = f"{base_url}/iptv/live/1000.json?key=txiptv"
    try:
        async with session.get(api, timeout=2) as r:
            if r.status == 200:
                data = await r.json()
                return [(i['name'], urljoin(base_url, i['url'])) for i in data.get('data', [])]
    except: pass
    return []

async def main():
    print(f"🚀 启动地毯式扫描 - {datetime.datetime.now().strftime('%H:%M:%S')}")
    
    # 第一步：生成所有网段 IP (IP 自动扩展)
    print("📡 阶段 1: 生成网段扫描任务...")
    scan_ips = []
    for u in urls:
        p = urlparse(u)
        segments = p.hostname.split('.')
        base = ".".join(segments[:3])
        port = f":{p.port}" if p.port else ""
        for i in range(1, 255):
            scan_ips.append(f"{p.scheme}://{base}.{i}{port}")

    # 第二步：并发抓取频道列表
    found_raw = []
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=300)) as sess:
        print(f"🔍 正在从 {len(scan_ips)} 个潜在接口抓取频道...")
        for i in range(0, len(scan_ips), 100):
            batch = scan_ips[i:i+100]
            results = await asyncio.gather(*(get_json_list(sess, ip) for ip in batch))
            for r in results: found_raw.extend(r)
            show_bar(min(i+100, len(scan_ips)), len(scan_ips), len(found_raw), "接口扫描")

        unique_channels = list(set(found_raw))
        print(f"\n✅ 发现 {len(unique_channels)} 个待测频道，开始稳定性检测...")

        # 第三步：深度检测
        final_list = []
        for i in range(0, len(unique_channels), 50):
            batch = unique_channels[i:i+50]
            tasks = [check_stream(sess, item[1]) for item in batch]
            checks = await asyncio.gather(*tasks)
            
            for idx, (ok, rt) in enumerate(checks):
                if ok:
                    name_raw, url = batch[idx]
                    cname, group, logo = get_meta(name_raw)
                    final_list.append({
                        "name": cname, "url": url, "rt": rt,
                        "group": group, "logo": logo,
                        "weight": SORT_WEIGHT.get(cname, 999)
                    })
            show_bar(min(i+50, len(unique_channels)), len(unique_channels), len(final_list), "稳定性检测")

        # 第四步：按照源项目顺序严格排序
        # 排序：权重优先(CCTV在前)，同频道则按延迟 RT 排序
        final_list.sort(key=lambda x: (x['weight'], x['rt']))

        # 第五步：保存 M3U
        with open("itvlist.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for item in final_list:
                f.write(f'#EXTINF:-1 tvg-name="{item["name"]}" tvg-logo="{item["logo"]}" '
                        f'group-title="{item["group"]}" response-time="{item["rt"]}ms",'
                        f'{item["name"]}\n{item["url"]}\n')

    print(f"\n\n✨ 完成！已按源项目顺序保存 {len(final_list)} 条源至 itvlist.m3u")

if __name__ == "__main__":
    asyncio.run(main())