# 可选本机运行路径

- 不设置默认金山文档。目标链接或 file_id 由调用方指定，规则见 SKILL.md「指定文档位置」。
- Python：`C:\Users\unico\.workbuddy\binaries\python\envs\default\Scripts\python.exe`
- 历史 CSV：`C:\Users\unico\WorkBuddy\2026-07-09-08-59-47\metal_prices_history.csv`
- 原始脚本：同目录 `metal_price_tracker.py`。仓库 scripts/collector.py 是其移植版本；不修改原文件。
- 时区：Asia/Shanghai。使用 skill 包内 collect.py 作为采集入口。
- GitHub：`unicorn021168-ctrl/metal-price-tracker`，私有仓库。

这些是原用户已有的非凭据本机路径，供原环境复用；调用时指定的新路径优先。迁移到其他账户时替换。上述路径不代表任何云文档的写入授权。
