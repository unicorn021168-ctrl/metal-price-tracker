# 本机运行路径配置

- 不设置默认金山文档。目标链接或 file_id 由调用方指定，规则见 SKILL.md「指定文档位置」。
- Python：使用本机已安装 requirements.txt 依赖的 Python，可在调用时指定解释器绝对路径。
- 历史 CSV：调用时指定本地绝对路径；同一台账持续使用同一文件。
- 本次结果 JSON：使用单独的运行输出路径，不与历史 CSV 共用文件。
- 时区：Asia/Shanghai。使用 skill 包内 collect.py 作为采集入口。
- 源码与版本：`https://github.com/unicorn021168-ctrl/metal-price-tracker`。

已有任务明确配置的本机路径可以继续复用，当前调用指定的新路径优先。不要猜测其他用户的路径。本机文件路径不代表任何云文档的写入授权。
