# 贡献指南 (Contributing Guide)

感谢你关注并愿意为 **JevKit Agent (`jevkit-agent`)** 项目贡献力量！

为了保证代码库的极简、轻量、高可维护性与零依赖特性，请在提交代码前仔细阅读以下准则。

---

## 核心原则

1. **零第三方依赖原则**：
   - 核心源码 `jevkit-agent.py` **只允许使用 Python 标准库**（如 `urllib.request`, `json`, `ctypes`, `re`, `time` 等），严禁引入 `requests`, `tkinter`, `numpy` 等任何第三方包；
   - 保证单文件即可在裸机 Windows 环境下运行。
2. **零密钥入库原则（Zero Secrets）**：
   - 严禁在任何提交的代码、测试用例或示例配置中硬编码真实的 API Key、Token 或凭据；
   - 提交前请使用 `git status` 确认未跟踪敏感配置。
3. **测试全绿原则**：
   - 任何改动后必须运行：
     ```powershell
     cd jevkit-agent
     python dev/jevkit-agent.py --selftest
     python dev/check-constants.py dev/jevkit-agent.py
     ```
     确保所有自检项（125+ 项）与静态常量检查全部 100% 通过（0 失败）。

---

## 提交信息规范 (Conventional Commits)

提交信息请遵循业界通用的语义化前缀：

| 前缀 | 说明 | 示例 |
|---|---|---|
| `feat:` | 新功能、新特性 | `feat: 增加对外部树表动态热导入支持` |
| `fix:` | 修复缺陷或 Bug | `fix: 修复高层 DSL 漏写井号时的标记自愈` |
| `docs:` | 文档更新 | `docs: 更新 README 中的三文件编程流程说明` |
| `refactor:` | 代码重构（不改变外部行为） | `refactor: 提取公共路由节点遍历逻辑` |
| `test:` | 测试用例增删改 | `test: 增加 JevClient 探针真实请求断言` |
| `chore:` | 杂项维护（打包脚本、构建配置、.gitignore） | `chore: 优化 PyInstaller spec 依赖配置` |

---

## 提交流程

1. Fork 本仓库并克隆到本地；
2. 基于 `main` 分支拉取开发分支（`git checkout -b feat/your-feature-name`）；
3. 进行代码编写并添加对应的单测；
4. 运行 `dev/check-constants.py` 和 `--selftest` 验证通过；
5. 提交 commit 并推送到你的 Fork 仓库；
6. 创建 Pull Request，详细描述改动内容与测试结果。
