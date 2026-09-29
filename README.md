# JevKit Agent (jevkit-agent) & JevAgent 编程系统

<div align="center">

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Platform: Windows 10 | 11](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg)
![Python: 3.8 ~ 3.14+](https://img.shields.io/badge/Python-3.8%20~%203.14%2B-3776AB.svg)
![Tests: 127 Passed](https://img.shields.io/badge/Tests-127%20Passed-brightgreen.svg)
![Architecture: Dual--API](https://img.shields.io/badge/Architecture-Dual--API%20Isolated-orange.svg)

**单文件 · 零依赖 · 纯 Win32 原生图形界面 · 具备全自主操作系统能力 · 双 API 隔离架构 · 驱动 JevAgent 三文件模型编程系统**

[快速上手](#-快速上手) • [核心特性](#-核心特性) • [三文件模型](#-jevagent-三文件模型编程) • [外部树表导入](#-外部树表自由导入与热加载) • [配置说明](#-配置说明) • [规范文档](#-设计规范与理论基准)

</div>

---

## 📖 项目概述

**JevKit Agent (`jevkit-agent`)** 是一个专为 Windows 10 / 11 深度优化的超轻量级自主 Agent。整套系统仅使用 **Python 标准库** 实现，无任何第三方包依赖，打包为独立的纯原生无控制台 Win32 可执行程序（`jevkit-agent.exe`），无需安装 Python 即可开箱即用。

本项目原生集成了符合《JevAgent 设计稿 V1.0》与《JevAgent 工程落地稿 V2.0》规范的 **JevAgent 编程系统**：通过双 API 物理隔离架构，联合通用大模型（负责逻辑编排与高层语义编写）与 Jev 判定模型（负责闭集精确路由与消除幻觉），构建语言无关的高层 DSL 到特化代码的受约束落地链路。

---

## 🌟 核心特性

### 1. 全自主操作系统 Agent 工具集
所有工具面向 AI 完全自主调用，用户只需用自然语言下达目标：
* **`pwsh`**：持久化 PowerShell 2.0~7.x 会话，支持状态跨轮次保持、静默安装环境、运行脚本与智能排障；
* **`str_replace_editor`**：高性能文件查看（带行号与防刷屏折叠）、创建、精准行替换与插入；
* **`mouse_control`**：自主控制 Windows 鼠标（坐标移动、左/右/中键点击、双击、长按释放、滚轮滑动与位置查询）；
* **`read_image`**：自主读取本地图片（PNG/JPG/WEBP/GIF/BMP），自动编码注入多模态上下文进行视觉分析；
* **`take_screenshot`**：自主截取 Windows 桌面屏幕送入模型进行 GUI 视觉闭环判断；
* **`jevagent`**：JevAgent 三文件规范编程与 Jev 决策专用工具。

### 2. 双 API 独立配置架构（存放在同一配置文件中）
整个 Agent 具备两套完全物理隔离的 API 配置，从底层协议保证安全：
* **通用 AI API**：驱动主智能体进行自然语言交互、多轮对话、长程思考与工具调用（支持 OpenAI 兼容 `/chat/completions` 与 Vision 格式）；
* **Jev 决策 API**：专用于 JevAgent 树形路由的确定性判断（直连 Jev / JevK5 服务，仅做 Choice / Score / Noul 判断）；
* **隔离与容错**：两套密钥物理隔离绝不混用；Jev API 支持 2 次指数退避重试与不可用熔断，**严禁使用通用 LLM 冒充 Jev 决策**；通用 AI 具备对 `RemoteDisconnected`、`ConnectionReset` 的底层断流自动重试。

### 3. JevAgent 三文件模型编程系统
彻底将语法特化细节与逻辑业务解耦，实现跨语言规范化落地：
* **三文件模型**：同目录、同基名、扩展名区分：
  * `<module>.high.dsl`：中文高层语义 DSL，语言无关，是业务逻辑的**唯一真相源**；
  * `<module>.spec.<lang>.dsl`：目标语言特化 DSL，标注特化节点路径与字面量；
  * `<module>.<ext>`：目标语言最终代码（可直接由解释器执行或编译器编译）。
* **多语言注释分隔符（BlockSplitter）**：以目标语言合法注释（`#`, `//`, `--`, `<!-- -->` 等）标记 `@jev-block:<id>:begin/end`，不污染代码语法，支持高层 DSL 标记容错自愈；
* **O(改动块数) 修改流程**：支持单块就地局部翻译替换，未修改块字节级 100% 保持不动；
* **真实动态符号表与版本回滚**：自动提取 `symbols_defined` 与 `symbols_used` 写入 `blocks_index.json`，支持 `rollback` 原子回退至上一确认点快照。

### 4. 外部树表自由导入与热加载
* 内置公共骨架表（`skeleton_v1`）、语义公约数层（`semantic_v1`）、Python 特化表（`python_v3`）、C 特化表（`c_v1`）及 Shell 特化表（`shell_v2`）；
* **开箱支持自定义扩展**：用户放入新的树表或通过工具调用 `import_table` 即可完成外部树表的热加载。

---

## 🚀 快速上手

### 方式 A：下载免安装发布版（从 GitHub Releases 下载）
1. 在本仓库右侧 **[Releases](../../releases)** 页面直接下载由 GitHub Actions 自动化编译打包的最新成品压缩包 `jevkit-agent-windows-x64.zip`；
2. 解压后直接双击 **`启动.bat`** 或 **`jevkit-agent.exe`**；
3. 首次运行会自动弹出设置窗口（或随时按 **F2**）：
   * 填入通用 AI 的 `base_url` 与 `api_key`，回车保存后自动弹出模型选择；
   * 在菜单「设置」→「Jev 接口与密钥」中配置 Jev 决策服务的地址与凭据；
4. 在最下方的输入框输入任务指令，回车发送！

### 方式 B：源码直接运行（面向开发者）
要求 Python 3.8+（仅需 Python 标准库，零第三方外部依赖）：
```powershell
cd jevkit-agent
python dev/jevkit-agent.py --gui
```

---

## 🌳 外部树表自由导入与热加载

JevAgent 采用树形路由体系，用户可以极简地扩充任意编程语言或业务领域的特化树表：

### 1. 目录直接放入（热加载）
将自定义的树表 JSON 文件（如 `rust_v1.json`、`go_v1.json`）直接放入 `tables/` 目录中。下次调用路由翻译时引擎自动扫描并热生效，无需重启程序。

### 2. 通过 Agent 工具动态导入
可在对话中直接向 `jevagent` 发送指令导入：
```json
{
  "action": "import_table",
  "file_path": "D:/custom_tables/rust_v1.json"
}
```
系统会自动执行 Schema 校验、保存到 `tables/` 目录并热注册生效。

### 3. 查看已加载树表
调用 `jevagent(action="list_tables")` 可随时查看当前系统加载的所有内置与外部树表清单及节点数量。

---

## ⚙️ 配置说明

配置文件为 `jevkit-agent.config.json`（模板见 `jevkit-agent/dev/jevkit-agent.config.example.json`）：

```json
{
  "base_url": "https://api.deepseek.com",
  "api_key": "sk-your-llm-key",
  "model": "deepseek-chat",
  "tables_dir": "./tables",
  "jev_base_url": "http://127.0.0.1:8199",
  "jev_api_key": "your-jev-key",
  "jev_model": "jevk5-4b-v0.3-Q4_K_M",
  "jev_timeout_s": 30
}
```

* 环境变量支持：
  * 通用 API：`JEVKIT_BASE_URL` / `OPENAI_BASE_URL`，`JEVKIT_API_KEY` / `OPENAI_API_KEY`，`JEVKIT_MODEL` / `OPENAI_MODEL`
  * Jev API：`JEV_API_BASE_URL` / `JEVK5_URL`，`JEV_API_KEY` / `JEVK5_API_KEY`，`JEV_MODEL`
  * 树表目录：`JEVKIT_TABLES_DIR` / `JEV_TABLES_DIR`

---

## 📁 项目目录结构

```
jevkit-agent/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml               # GitHub Actions 自动化持续集成流水线 (125项自检)
│   │   └── release.yml          # GitHub Actions 自动化编译打包与 Release 附件发布
│   └── ISSUE_TEMPLATE/          # 社区 Issue 规范模板
├── docs/                        # 核心设计与工程落地规范文档
│   ├── JevAgent 设计稿.md         # JevAgent 系统设计 V1.0 联合定修稿
│   └── JevAgent工程落地稿.md      # JevAgent 工程落地与工具化落地稿 V2.0
├── jevkit-agent/                # 完整源码工程开发套件
│   ├── dev/
│   │   ├── jevkit-agent.py      # 核心单文件源码（标准库零外部依赖）
│   │   ├── build-exe.bat        # 本地 PyInstaller 单文件打包脚本
│   │   ├── check-constants.py   # Win32 原生常量静态检查器
│   │   ├── gui-e2e.py           # GUI 进程外消息队列端到端自动化测试
│   │   └── 开发文档.md          # 内部架构与协议实现深度文档
│   └── tables/                  # 官方默认内置路由树表
├── .gitignore                   # 安全红线与构建产物忽略规则
├── CONTRIBUTING.md               # 代码贡献与代码规范
├── LICENSE                      # MIT 开源许可证
└── README.md                    # 本文档
```

---

## 🧪 自动化测试与质量保障

项目内置完整的离线与集成自动化测试套件：
```powershell
cd jevkit-agent
python dev/jevkit-agent.py --selftest
```
执行全部 **125 项** 自动化回归测试（0 失败）：
* 双 API 隔离与密钥安全测试；
* Jev 决策模型端点规格化与真实探针测试；
* BlockSplitter 多语言注释拆块、闭合校验与裸标记自愈测试；
* C 语言特化函数大括号自动闭合补全测试；
* `blocks_index.json` 多语言多特化增量合并测试；
* 常用语法节点扩充（`设`/`跳出`/`继续`）转换测试；
* 外部树表动态导入（`import_table`）与树表枚举（`list_tables`）测试；
* 确认点版本向量哈希记录与原子回退（`rollback`）测试。

---

## 📄 设计规范与理论基准

* [JevAgent 设计稿 V1.0（联合定修稿）](docs/JevAgent%20设计稿.md)
* [JevAgent 工程落地稿 V2.0](docs/JevAgent工程落地稿.md)

---

## 🤝 参与贡献

欢迎提交 Issue 与 Pull Request！详情请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📜 开源协议

本项目采用 [MIT License](LICENSE) 开源许可证。
