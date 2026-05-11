# 一键存职位 - Job Saver Extension

Chrome 浏览器插件，一键从当前页面提取职位信息并保存到求职 Agent 系统。

## 安装方法

### 开发者模式安装

1. 打开 Chrome，访问 `chrome://extensions/`
2. 开启右上角 **"开发者模式"**
3. 点击 **"加载已解压的扩展程序"**
4. 选择本目录 (`extensions/save-job-extension/`)
5. 完成！

### 使用方法

1. 确保求职 Agent 在运行：`python3 job_agent_web.py`（端口 9999）
2. 浏览任意职位页面（LinkedIn / Indeed / Greenhouse / 公司官网等）
3. 点击工具栏的 📥 图标
4. 预览提取的职位信息
5. 点击 **"保存到求职Agent"**

### 自定义 Agent 地址

如果 Agent 运行在其它机器或端口，点击弹出框右上角 ⚙️ 设置按钮修改地址。

## 支持的站点

- **LinkedIn** — 自动提取标题、公司、地点、描述
- **Indeed** — 同上
- **Greenhouse / Lever / Workday** — 标准 ATS 页面
- **公司官网** — 通过 JSON-LD、OG 元标签、DOM 文本分析
- **任何页面** — 通用 fallback 提取

## 隐私说明

插件仅在点击时分析当前页面，所有数据仅发送到你自己的求职 Agent 服务。

## 文件结构

```
save-job-extension/
├── manifest.json          # 扩展配置
├── content/
│   └── extractor.js       # 页面信息提取脚本（多策略）
├── popup/
│   ├── popup.html         # 弹出窗口
│   ├── popup.css          # 样式
│   └── popup.js           # 弹出窗口逻辑
└── icons/                 # 图标（16/48/128 PNG）
```
