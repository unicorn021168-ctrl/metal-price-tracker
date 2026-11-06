# Metal Price Tracker · 金属价格追踪

用于 Codex / WorkBuddy 等支持 Skill 的助手：采集六种金属价格，保存本地 CSV，并通过 **kdocs skill + kdocs-cli** 同步金山文档。

## 支持品种

| 品种 | 来源 | 单位 |
| --- | --- | --- |
| 1#电解铜、1#电解镍、0#锌锭/上海、1#锡、1#钴/华南 | shmet.com | 元/吨 |
| 碳化钨 | 我的钢铁网 | 元/千克 |

支持失败来源重试、同日去重、保留已有成功价格和写入后回读验证。采集日期与来源报价日期分别记录。

## 准备

1. 下载或克隆本仓库，将整个文件夹以 `metal-price-tracker` 命名，放入助手的技能目录。
2. 安装并登录官方 `kdocs` skill / `kdocs-cli`。
3. 在所用 Python 环境中安装依赖：`python -m pip install -r requirements.txt`。
4. 准备可编辑的金山文档表格，包含：**汇总、电解铜、电解镍、锌锭、锡、钴、碳化钨**。汇总列为日期、六种价格、备注；分表列为日期、价格、备注。详见 [同步规则](references/kdocs-workflow.md)。

## 使用

向助手发送（替换尖括号中的内容）：

```text
使用 $metal-price-tracker 采集今天的金属价格。
目标金山文档：<完整分享链接或 file_id>。
历史 CSV 保存到：<本地 CSV 绝对路径>。
```

**不绑定默认云文档**，每次可指定不同目标；目标不明确时会先询问。云表同步由助手通过 kdocs 执行。

只运行本地采集，可在仓库目录执行：

```bash
python scripts/collect.py --history runtime/metal_prices_history.csv --result runtime/latest.json --retry-failed
```

该命令仅采集并保存本地数据，不直接写入金山文档。不要直接运行 `scripts/collector.py`，其原始入口不包含防重复处理。

## 定时运行与维护

- [定时任务描述模板](references/workbuddy-task.md)：填写目标文档和 CSV 路径后使用，不会自动创建或修改调度。
- [完整技能说明](SKILL.md) · [版本记录](CHANGELOG.md)
- 测试：`python -m unittest discover -s tests`
- 凭据由 kdocs 管理；不要将 Token、运行结果或历史 CSV 提交到仓库。

行情取决于来源页面与接口的可用性，可能返回上一报价日的数据；失败和报价日期会如实报告。
