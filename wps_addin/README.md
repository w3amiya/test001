# WPS 插件初稿

这是 Tableau 导数工具的 WPS 插件前端初稿。当前目标是先打通插件界面和本地助手，不直接把 Tableau 自动化逻辑写进插件。

## 结构

```text
wps_addin/
  manifest.xml
  taskpane.html
  assets/
    taskpane.css
    taskpane.js
```

## 本地助手

先在本机启动助手接口：

```bash
cd /path/to/tableau_wps_helper
set PYTHONPATH=%cd%\src
python -m tableau_wps_helper.cli serve --host 127.0.0.1 --port 8765
```

Mac 测试时：

```bash
cd /Users/amiya/project/Codex/tableau_wps_helper
PYTHONPATH=/Users/amiya/project/Codex/tableau_wps_helper/src \
python3 -m tableau_wps_helper.cli serve --host 127.0.0.1 --port 8765
```

## 前端页面

开发期可以用任意静态服务器打开 `taskpane.html`，例如：

```bash
cd /path/to/tableau_wps_helper/wps_addin
python -m http.server 3000
```

然后访问：

```text
http://127.0.0.1:3000/taskpane.html
```

## WPS 加载

`manifest.xml` 是插件清单初稿，当前按任务窗格插件形态组织。Windows 上需要根据实际 WPS 版本支持的加载方式调整清单字段和本地地址。

第一版建议先验证：

- 插件任务窗格能打开
- 能连接 `http://127.0.0.1:8765/health`
- 能读取 `.twb` Worksheet
- 能执行导入计划

## 当前边界

- 当前插件前端不直接控制 Tableau Desktop。
- 当前插件前端不直接读取当前 WPS 工作簿路径。
- 真实的 Tableau 导出仍需要 Windows + Tableau Desktop 2025.2 环境继续调试。
