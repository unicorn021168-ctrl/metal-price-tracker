#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
金属价格自动采集脚本
=====================
每天工作日自动抓取以下金属的中间价：
  - 上海有色网(shmet.com): 1#电解铜、1#电解镍、0#锌锭(上海)、1#锡、1#钴(华南)
  - 我的钢铁网(thj.mysteel.com/wu/): 碳化钨

数据保存到 CSV 文件（追加写入），包含日期、金属名称、价格等字段。
可通过命令行手动运行，也可配合定时任务自动执行。

用法:
    python metal_price_tracker.py              # 采集并保存
    python metal_price_tracker.py --display    # 采集、保存并打印表格
    python metal_price_tracker.py --query 2026-07-09  # 查询指定日期数据
"""

import csv
import os
import sys
import json
import argparse
from datetime import datetime, date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ============================================================
# 配置
# ============================================================

# 输出文件路径（CSV，追加写入）
SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_FILE = SCRIPT_DIR / "metal_prices_history.csv"

# shmet.com API 配置
SHMET_API_URL = "https://api.shmet.com/api/rest/spot/spotPrices"
SHMET_API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Content-Type": "application/json",
    "Referer": "https://www.shmet.com/",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://www.shmet.com",
}

# shmet.com 金属类型映射
# key: API请求的type参数, value: 目标金属名称列表
SHMET_TARGETS = {
    "Cu":   ["1#电解铜"],
    "Ni":   ["1#电解镍"],
    "Zn":   ["0#锌锭/上海"],
    "Sn":   ["1#锡"],
    "CoLi": ["1#钴/华南"],
}

# mysteel.com 配置
MYSTEEL_URL = "https://thj.mysteel.com/wu/"
MYSTEEL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://thj.mysteel.com/",
}
MYSTEEL_TARGETS = ["碳化钨"]

# CSV 文件表头
CSV_HEADERS = [
    "采集日期",
    "金属名称",
    "规格/地区",
    "中间价",
    "报价范围",
    "涨跌",
    "报价时间",
    "单位",
    "数据来源",
]

# 请求超时（秒）
REQUEST_TIMEOUT = 30


# ============================================================
# 数据采集：上海有色网
# ============================================================

def fetch_shmet_prices():
    """通过 shmet.com API 获取金属现货中间价"""
    results = []

    for metal_type, target_names in SHMET_TARGETS.items():
        payload = {"code": "Home2", "type": metal_type}
        try:
            resp = requests.post(
                SHMET_API_URL,
                json=payload,
                headers=SHMET_API_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != "000000" or not data.get("data"):
                print(f"  [WARN] shmet.com type={metal_type}: "
                      f"返回异常 code={data.get('code')}, "
                      f"msg={data.get('message')}")
                continue

            # 遍历返回数据，筛选目标金属
            for item in data["data"]:
                name = item.get("name", "")
                # 跳过升贴水数据
                if item.get("premium"):
                    continue

                # 检查是否是目标金属（精确匹配名称）
                if name not in target_names:
                    continue

                # 取最新一条价格记录（pricesList 第一个元素）
                prices_list = item.get("pricesList", [])
                if not prices_list:
                    continue

                latest = prices_list[0]
                middle = latest.get("middle", "")
                high = latest.get("high", "")
                low = latest.get("low", "")
                change = latest.get("change", "")
                price_time = latest.get("date", "")

                # 构建报价范围
                price_range = f"{low}-{high}" if low and high else ""

                # 解析规格/地区
                spec = ""
                if "/" in name:
                    parts = name.split("/", 1)
                    spec = parts[1]

                # 判断单位（铜/镍/锌/锡/钴 均为 元/吨）
                unit = "元/吨"

                results.append({
                    "采集日期": date.today().isoformat(),
                    "金属名称": name.split("/")[0],
                    "规格/地区": spec,
                    "中间价": middle,
                    "报价范围": price_range,
                    "涨跌": change,
                    "报价时间": price_time,
                    "单位": unit,
                    "数据来源": "上海有色网",
                })

                print(f"  [OK] {name}: 中间价 {middle} {unit} "
                      f"(范围 {price_range}, 涨跌 {change})")

        except requests.RequestException as e:
            print(f"  [ERROR] shmet.com type={metal_type}: 请求失败 - {e}")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  [ERROR] shmet.com type={metal_type}: 解析失败 - {e}")

    return results


# ============================================================
# 数据采集：我的钢铁网（碳化钨）
# ============================================================

def fetch_mysteel_prices():
    """从 mysteel.com 页面解析碳化钨价格"""
    results = []

    try:
        resp = requests.get(
            MYSTEEL_URL,
            headers=MYSTEEL_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding

        soup = BeautifulSoup(resp.text, "lxml")

        # 查找"今日价格"表格
        table = soup.find("table", class_="today-tab")
        if not table:
            print("  [WARN] mysteel.com: 未找到今日价格表格")
            return results

        tbody = table.find("tbody")
        if not tbody:
            print("  [WARN] mysteel.com: 表格无 tbody")
            return results

        for row in tbody.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 5:
                continue

            name = cells[0].get_text(strip=True)
            if name not in MYSTEEL_TARGETS:
                continue

            price = cells[1].get_text(strip=True)
            change = cells[2].get_text(strip=True)
            unit = cells[3].get_text(strip=True)
            price_date = cells[4].get_text(strip=True)

            # 涨跌格式化
            change_val = change
            try:
                change_num = float(change)
                if change_num > 0:
                    change_val = f"+{change}"
            except ValueError:
                pass

            results.append({
                "采集日期": date.today().isoformat(),
                "金属名称": name,
                "规格/地区": "",
                "中间价": price,
                "报价范围": "",
                "涨跌": change_val,
                "报价时间": price_date,
                "单位": unit,
                "数据来源": "我的钢铁网",
            })

            print(f"  [OK] {name}: 价格 {price} {unit} "
                  f"(涨跌 {change_val}, 日期 {price_date})")

    except requests.RequestException as e:
        print(f"  [ERROR] mysteel.com: 请求失败 - {e}")
    except Exception as e:
        print(f"  [ERROR] mysteel.com: 解析失败 - {e}")

    return results


# ============================================================
# 数据存储
# ============================================================

def save_to_csv(records, filepath=OUTPUT_FILE):
    """将价格记录追加写入 CSV 文件"""
    if not records:
        print("[INFO] 无数据可保存")
        return False

    file_exists = filepath.exists()
    has_content = file_exists and filepath.stat().st_size > 0

    with open(filepath, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)

        # 仅在文件为空时写入表头
        if not has_content:
            writer.writeheader()

        for record in records:
            writer.writerow(record)

    print(f"\n[INFO] 已保存 {len(records)} 条记录到: {filepath}")
    return True


def query_by_date(query_date, filepath=OUTPUT_FILE):
    """从 CSV 文件中查询指定日期的价格数据"""
    if not filepath.exists():
        print(f"[INFO] 文件不存在: {filepath}")
        return []

    results = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("采集日期") == query_date:
                results.append(row)

    return results


# ============================================================
# 数据展示
# ============================================================

def display_table(records):
    """以表格形式打印价格数据"""
    if not records:
        print("\n无数据可显示")
        return

    print("\n" + "=" * 90)
    print(f"  金属价格日报 - {records[0].get('采集日期', 'N/A')}")
    print("=" * 90)

    # 表头
    header = (
        f"{'金属名称':<14} {'规格/地区':<10} {'中间价':>12} "
        f"{'报价范围':>16} {'涨跌':>8} {'单位':<10} {'来源':<10}"
    )
    print(f"\n  {header}")
    print(f"  {'-' * 84}")

    for r in records:
        name = r.get("金属名称", "")
        spec = r.get("规格/地区", "")
        price = r.get("中间价", "")
        price_range = r.get("报价范围", "")
        change = r.get("涨跌", "")
        unit = r.get("单位", "")
        source = r.get("数据来源", "")

        # 涨跌着色标记
        change_display = change
        if change:
            try:
                change_num = float(change)
                if change_num > 0:
                    change_display = f"↑+{change}"
                elif change_num < 0:
                    change_display = f"↓{change}"
                else:
                    change_display = f"→ {change}"
            except ValueError:
                pass

        row = (
            f"{name:<14} {spec:<10} {price:>12} "
            f"{price_range:>16} {change_display:>8} {unit:<10} {source:<10}"
        )
        print(f"  {row}")

    print(f"  {'-' * 84}")
    print(f"  共 {len(records)} 种金属\n")


# ============================================================
# 主流程
# ============================================================

def run_collection(display=True):
    """执行完整的数据采集、存储和展示流程"""
    print(f"\n{'='*60}")
    print(f"  金属价格采集 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # 1. 采集上海有色网数据
    print("[1/3] 采集上海有色网数据...")
    shmet_data = fetch_shmet_prices()
    print(f"  -> 获取 {len(shmet_data)} 条记录\n")

    # 2. 采集我的钢铁网数据
    print("[2/3] 采集我的钢铁网数据...")
    mysteel_data = fetch_mysteel_prices()
    print(f"  -> 获取 {len(mysteel_data)} 条记录\n")

    # 3. 合并并保存
    all_data = shmet_data + mysteel_data
    print(f"[3/3] 保存数据...")
    save_to_csv(all_data)

    # 4. 展示
    if display:
        display_table(all_data)

    return all_data


def main():
    parser = argparse.ArgumentParser(
        description="金属价格自动采集工具"
    )
    parser.add_argument(
        "--display", "-d",
        action="store_true",
        help="采集后打印价格表格",
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="查询指定日期的数据（格式: YYYY-MM-DD）",
    )
    args = parser.parse_args()

    if args.query:
        # 查询模式
        records = query_by_date(args.query)
        if records:
            display_table(records)
        else:
            print(f"\n未找到 {args.query} 的价格数据")
    else:
        # 采集模式
        run_collection(display=args.display)


if __name__ == "__main__":
    main()
