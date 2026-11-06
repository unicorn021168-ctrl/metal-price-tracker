import sys
import unittest
import csv
import json
import tempfile
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from collect import merge_records, validate, main
import collector

def record(price='100'):
    return {'采集日期':'2026-11-06','金属名称':'1#电解铜','规格/地区':'',
            '中间价':price,'报价时间':'11-05 11:30','单位':'元/吨',
            '报价范围':'90-110','涨跌':'1','数据来源':'shmet'}

class CollectionTests(unittest.TestCase):
    def test_rerun_is_idempotent(self):
        a=record()
        self.assertEqual(merge_records([a],[a]),[a])
    def test_partial_failure_preserves_history(self):
        a=record()
        self.assertEqual(merge_records([a],[]),[a])
    def test_changed_price_replaces_same_key(self):
        self.assertEqual(merge_records([record()],[record('105')]),[record('105')])
    def test_reject_invalid_price(self):
        with self.assertRaises(ValueError): validate(record('NaN'))
    def test_reject_wrong_unit(self):
        a=record(); a['单位']='元/千克'
        with self.assertRaises(ValueError): validate(a)
    def test_reject_price_outside_range(self):
        with self.assertRaises(ValueError): validate(record('200'))
    def test_failed_run_does_not_reuse_history_as_fresh(self):
        with tempfile.TemporaryDirectory() as folder:
            history=Path(folder)/'history.csv'; result=Path(folder)/'result.json'
            with history.open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.DictWriter(f,fieldnames=collector.CSV_HEADERS)
                w.writeheader(); w.writerow(record())
            before=history.read_bytes()
            with patch.object(sys,'argv',['collect','--history',str(history),'--result',str(result)]), patch.object(collector,'fetch_shmet_prices',return_value=[]), patch.object(collector,'fetch_mysteel_prices',return_value=[]):
                self.assertEqual(main(),2)
            self.assertEqual(history.read_bytes(),before)
            self.assertEqual(json.loads(result.read_text(encoding='utf-8'))['records'],[])
    def test_history_failure_is_not_reported_as_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            history=Path(folder)/'history.csv'; result=Path(folder)/'result.json'
            history.write_text('wrong,header\n',encoding='utf-8')
            with patch.object(sys,'argv',['collect','--history',str(history),'--result',str(result)]), patch.object(collector,'fetch_shmet_prices',return_value=[record()]), patch.object(collector,'fetch_mysteel_prices',return_value=[]):
                with self.assertRaises(ValueError): main()
            self.assertFalse(json.loads(result.read_text(encoding='utf-8'))['history_saved'])

if __name__=='__main__': unittest.main()
