"""Collect once; write a fresh result separately from idempotent CSV history."""
import argparse
import csv
import io
import json
import math
import os
from contextlib import redirect_stdout
from datetime import datetime, timezone, timedelta
from pathlib import Path
import collector

NAMES = ['1#电解铜', '1#电解镍', '0#锌锭', '1#锡', '1#钴', '碳化钨']

def validate(r):
    name = r['金属名称']
    if name not in NAMES:
        raise ValueError('非目标金属')
    p = float(r['中间价'])
    if not math.isfinite(p) or p <= 0:
        raise ValueError('中间价无效')
    if r['单位'] != ('元/千克' if name == '碳化钨' else '元/吨'):
        raise ValueError('单位异常')
    if not r.get('报价时间'):
        raise ValueError('报价时间缺失')
    expected_region = {'0#锌锭':'上海', '1#钴':'华南'}.get(name, '')
    if r.get('规格/地区', '') != expected_region:
        raise ValueError('规格/地区异常')
    if r.get('报价范围'):
        low, high = map(float, r['报价范围'].split('-'))
        if not low <= p <= high:
            raise ValueError('中间价不在报价范围内')

def key(r):
    return tuple(r.get(k, '') for k in ('采集日期','金属名称','规格/地区'))

def merge_records(history, fresh):
    # Keep old historical rows verbatim; only upsert keys successfully fetched now.
    replacements = {key(r): r for r in fresh}
    out, seen = [], set()
    for r in history:
        k = key(r)
        if k not in replacements:
            out.append(r)
        elif k not in seen:
            out.append(replacements[k]); seen.add(k)
    out.extend(r for k,r in replacements.items() if k not in seen)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--history', type=Path, required=True)
    ap.add_argument('--result', type=Path, required=True)
    ap.add_argument('--retry-failed', action='store_true', help='Retry missing source once')
    args = ap.parse_args()
    if args.history.resolve() == args.result.resolve():
        ap.error('history and result must differ')
    lock = args.history.with_suffix(args.history.suffix + '.lock')
    args.history.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit('已有采集锁；确认没有运行中的采集后人工处理锁文件')
    os.close(fd)
    try:
        today = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
        output, valid, issues = io.StringIO(), {}, []
        sources = [(collector.fetch_shmet_prices, NAMES[:5]),
                   (collector.fetch_mysteel_prices, NAMES[5:])]
        with redirect_stdout(output):
            for fetch, expected in sources:
                for attempt in range(2 if args.retry_failed else 1):
                    for r in fetch():
                        try:
                            validate(r)
                            r['采集日期'] = today
                            r['数据来源'] = 'shmet' if r['金属名称'] != '碳化钨' else '我的钢铁网'
                            valid[r['金属名称']] = r
                        except (ValueError, KeyError, TypeError) as e:
                            issues.append(f"{r.get('金属名称','未知')}: {e}")
                    if all(n in valid for n in expected): break
        fresh = [valid[n] for n in NAMES if n in valid]
        missing = [n for n in NAMES if n not in valid]
        result = {'collection_date':today, 'history_saved':False, 'records':fresh, 'missing':missing,
                  'warnings':issues, 'log':output.getvalue()}
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        if fresh:
            history = []
            if args.history.exists():
                with args.history.open(encoding='utf-8-sig', newline='') as f:
                    reader = csv.DictReader(f)
                    if reader.fieldnames != collector.CSV_HEADERS:
                        raise ValueError('CSV表头变化，停止写入')
                    history = list(reader)
            rows = merge_records(history, fresh)
            temp = args.history.with_suffix('.csv.tmp')
            with temp.open('w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=collector.CSV_HEADERS)
                writer.writeheader(); writer.writerows(rows)
            os.replace(temp, args.history)
            result['history_saved'] = True
            args.result.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(output.getvalue())
        print(f'成功 {len(fresh)}/6；缺失：{missing}；本次结果：{args.result}')
        return 2 if missing else 0
    finally:
        lock.unlink()

if __name__ == '__main__':
    raise SystemExit(main())
