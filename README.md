# Tableau WPS Helper

本项目是 Tableau 工作簿数据导出到 WPS/Excel 的本地助手骨架。

当前阶段实现稳定的本地能力：

- 读取 `.twb` 文件中的 Worksheet 列表
- 维护最近使用文件、导出目录、Tableau 路径、Sheet 映射等配置
- 将 CSV / Excel 文件写入指定 `.xlsx` 工作簿的指定 Sheet
- 通过 JSON 导入计划一次写入多个 Sheet
- 清空旧数据但尽量保留原 Sheet 格式
- 写入本地日志
- 预留 Tableau Desktop 自动化导出接口

后续在 Windows + WPS + Tableau Desktop 2025.2 环境下接入自动化模块。

## 目录

```text
tableau_wps_helper/
  config/
    default_config.json
  src/tableau_wps_helper/
    cli.py
    config.py
    excel_writer.py
    job_runner.py
    logger.py
    tableau_automation.py
    twb_parser.py
  tests/
```

## 快速使用

如果在开发环境中不方便写入用户文档目录，可以临时指定配置和日志目录：

```bash
export TABLEAU_WPS_HELPER_CONFIG=/tmp/tableau_wps_helper_config.json
export TABLEAU_WPS_HELPER_LOG_DIR=/tmp/tableau_wps_helper_logs
```

列出 `.twb` 文件中的 Worksheet：

```bash
python3 -m tableau_wps_helper.cli list-worksheets /path/to/workbook.twb
```

将 CSV 写入 Excel 工作簿：

```bash
python3 -m tableau_wps_helper.cli import-file \
  --source /path/to/export.csv \
  --workbook /path/to/target.xlsx \
  --sheet Sheet1 \
  --start-cell A1 \
  --header-rows 1
```

按导入计划一次写入多个 Sheet：

```bash
python3 -m tableau_wps_helper.cli import-plan \
  --plan /path/to/import_plan.json
```

导入计划示例：

```json
{
  "targetWorkbook": "target.xlsx",
  "startCell": "A1",
  "headerRows": 1,
  "items": [
    {
      "source": "二段成本汇总.xlsx",
      "sheet": "二段成本汇总"
    },
    {
      "source": "提单号清洗.csv",
      "sheet": "提单号清洗",
      "startCell": "A1"
    }
  ]
}
```

记录 Worksheet 到 Sheet 的映射：

```bash
python3 -m tableau_wps_helper.cli set-mapping \
  --twb /path/to/workbook.twb \
  --worksheet 二段成本汇总 \
  --sheet Sheet1
```

设置 Tableau Desktop 路径：

```bash
python3 -m tableau_wps_helper.cli set-tableau-path "C:\\Program Files\\Tableau\\Tableau 2025.2\\bin\\tableau.exe"
```

查看 Tableau 自动化导出模块状态：

```bash
python3 -m tableau_wps_helper.cli automation-status
```

在 Windows 上尝试自动化导出 Worksheet：

```bash
python -m tableau_wps_helper.cli export-tableau ^
  --twb "D:\reports\成本模型.twb" ^
  --worksheet "二段成本汇总" ^
  --export-dir "D:\TableauExports" ^
  --use-cache-on-refresh-failure
```

当前第一版自动化依赖 `pywinauto`：

```bash
pip install pywinauto openpyxl
```

注意：Tableau Desktop 的菜单、语言、弹窗和 Worksheet 标签在不同电脑上可能不完全一致，`tableau_automation.py` 里的菜单路径和控件查找可能需要在 Windows 机器上调试。

## 说明

当前 `tableau_automation.py` 已提供第一版 Windows 自动化导出尝试，后续需要在 Windows + Tableau Desktop 2025.2 环境下根据实际菜单、弹窗和语言继续调试。
