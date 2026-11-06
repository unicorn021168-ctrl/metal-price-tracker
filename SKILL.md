---
name: metal-price-tracker
description: Use when 用户要求每日采集铜、镍、锌、锡、钴、碳化钨价格，核对金山文档金属价格台账，或运行 WorkBuddy 金属价格定时任务。
---

# 金属价格追踪

通过公开来源采集六种金属，保存 CSV，使用已安装的 `kdocs` skill 维护七张工作表并回读核对。版本见 `VERSION`。不执行交易。

## 运行

先读取本机 `kdocs/SKILL.md`，按其版本、认证、错误处理约束操作。只使用 `kdocs-cli`；不依赖旧 `mcp__kdocs__*`。凭据留在系统密钥链，不提交 Token、历史 CSV、云表内容或运行日志。

本用户目标和现有路径见 [references/local-profile.md](references/local-profile.md)。其他用户必须配置自己的 file_id、Python 与 CSV 路径。不要因本技能而新建定时任务或修改现有调度。

1. 用具备 requirements.txt 依赖的 Python 运行：

   `python scripts/collect.py --history <历史CSV绝对路径> --result <本次结果JSON绝对路径> --retry-failed`

   从技能目录运行或使用脚本绝对路径。默认只采集一次；指定 retry-failed 时缺失来源最多补采一次。退出码 2 表示部分或全部缺失，仍需检查本次 JSON。异常退出且未生成新结果时不得使用上次 JSON。不要直接运行 `collector.py` 的 CLI（原始版本会重复追加）。

2. 检查本次 `records/missing/warnings/log/history_saved`。仅退出码0或2且 history_saved=true 才进入云端同步；其他退出或保存失败先报告并处理，不能宣称 CSV 已保存。不要从历史 CSV 推断本次成功。原脚本返回 0 不代表全部成功。保留初次错误及重试结果。六种全部失败时停止云端写入并报告；部分失败按下述规则写空值及原因。

3. 按 [references/kdocs-workflow.md](references/kdocs-workflow.md) 读取七表完整有效区域、检查重复日期、生成单元格写入计划、串行写入与回读。存在冲突或历史重复时先报告；不要擅自删除。无冲突的当天行可以独立完成。

4. 回复 Markdown 表格：金属名称、规格/地区、中间价、报价范围、涨跌、单位、数据来源。注明采集日期与每种报价日期、错误和恢复情况、CSV 路径、七表验证结果；云文档链接只用 API 已返回的真实链接。

## 数据约束

- 铜/镍/锌/锡/钴单位为元/吨，碳化钨为元/千克；不要混用或隐式换算。
- shmet 是 shmet.com 来源，不把它标成 SMM。保存来源原文和报价时间。不能把采集日当作报价日。
- 来源返回旧报价时如实标注；同一报价日可用于多个采集日。报价日期异常、未来日期、异常陈旧时报告核查，不伪造新日期。
- 本次成功价格只用于指定品种及地区；新失败不能覆盖当天已有成功价格。
- 一次只运行一个任务；本地锁只防同一 CSV 的采集并发，不覆盖整段云端操作。若发现其他任务正写同一表，停止并等待其完成后重新读表。

## 迭代升级

Git 仓库为版本来源，使用语义化 VERSION 和 CHANGELOG.md 记录行为变化。更新来源解析或同步规则后运行 `python -m unittest discover -s tests`、技能格式校验、只读云表核对；有写入变化时验证小范围真实结果及重跑不新增行。发布 Git 提交和版本标签后再更新安装目录，保留用户配置与 CSV。无任务授权不自动推送升级或改调度。
