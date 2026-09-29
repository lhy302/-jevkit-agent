# JevAgent 工程落地稿 V2.0

> 配套规范：《JevAgent 设计稿 V1.0（最终定修稿）》
> 本稿完全替代《JevAgent 工程落地补充稿 V1.0》。
> 冲突处理：设计稿 V1.0 的冻结结论（封闭集合、路由 schema、确认点版本向量、词表工厂生效时机、异构审查要求）以设计稿为准；工程落地、挂载、三文件模型、分隔符、流程、接口以本稿为准。

---

## 0. 本稿解决的问题

原工程落地稿把 JevAgent 当"系统"来写，导致：
- 与通用 Agent 的边界不清，重复描述编排层职责。
- 缺少落盘、命名、分隔符的具体规范，三条流程无法执行。
- 分隔符未考虑目标语言注释符，代码无法编译。
- 工具化定位缺失，接口不可注册到现有 Agent。

本稿重写如下内容：**JevAgent 的角色、三文件模型、分隔符规范、工具接口、三条流程、块拆分、落盘命名、版本绑定、部署与验收**。

---

## 1. JevAgent 的角色定位

**JevAgent 是通用 Agent 的编程专用扩展工具，注册在 tool 字段调用，不替代通用 Agent。**

它解决的核心痛点：通用 Agent 把大量算力浪费在"语法长什么样"，而不是"逻辑是什么"。JevAgent 把语法补全从通用 Agent 的工作量里剥离出去。

### 1.1 职责划分

| 职责 | 归属 |
|---|---|
| 理解用户意图 | 通用 Agent |
| 选择目标语言、选择表 | 通用 Agent |
| 写高层语义 DSL | 通用 Agent |
| 现有代码打分隔符 | 通用 Agent |
| 高层 DSL → 特化 DSL | JevAgent（逐块） |
| 特化 DSL → 最终代码 | JevAgent（逐块） |
| 代码 → 特化 DSL | JevAgent（逐块） |
| 特化 DSL → 高层 DSL | JevAgent（逐块） |
| 修改后重新翻译 | JevAgent（按块，不整体） |
| 语义审 | 通用 Agent |
| 结构审 / 语法验证 | JevAgent / Tier 1 |

### 1.2 JevAgent 内部构成

```
JevAgent（工具系统）
├── BlockSplitter      读分隔符，拆块 / 拼块
├── RouterEngine       按表路由，产路径
├── TemplateEngine     叶子模板填充
├── SymbolTable        动态符号表读写
├── VocabValidator     词表语法验证
├── NormalizeDsl       DSL 描述规范化
├── ContextPacker      块前后文打包，控制上下文窗口
└── JevClient          → Jev 模型 API（仅 Choice / Score / Noul）

Jev（模型）
└── 只做 Choice / Score / Noul，不生成自由文本
```

**关键区分**：BlockSplitter 是 JevAgent 的模块，不是 Jev 模型。Jev 模型只做候选内判断，不做代码拆分。

---

## 2. 三文件模型

每个逻辑模块（一个函数、一个文件、一个可独立验证单元）都有三份表示，**同目录、同基名、扩展名区分**：

```
<module>.high.dsl              高层语义（人类可读，中文 DSL，语言无关）
<module>.spec.<lang>.dsl       特化语义（Jev 生成，绑定目标语言）
<module>.<ext>                 最终代码（可编译 / 可执行）
```

例：`auth` 模块，Python 目标：

```
auth/
  auth.high.dsl
  auth.spec.python.dsl
  auth.py
```

同一模块若要再出 C 版本，只加特化层与代码层，**高层语义复用**：

```
auth/
  auth.high.dsl
  auth.spec.python.dsl
  auth.py
  auth.spec.c.dsl
  auth.c
```

### 2.1 三文件的职责

| 文件 | 谁写 | 谁读 | 作用 |
|---|---|---|---|
| `.high.dsl` | 通用 Agent | 通用 Agent、人类、Jev | 逻辑的唯一真相源（语言无关） |
| `.spec.<lang>.dsl` | JevAgent | JevAgent、通用 Agent | 记录特化选择，是代码的可读中间表示 |
| `.<ext>` | JevAgent | 编译器 / 解释器 | 最终产物 |

**关键约束**：
- 高层语义是唯一真相源。修改逻辑改 `.high.dsl`。
- 特化语义和代码是派生表示，**不手工修改**（除非走"代码 → 特化"反向流程）。
- 三文件通过块 ID 一一对应。

### 2.2 为什么同目录同基名

三份表示是同一逻辑的三个投影。同目录保证：
- diff 时一起走。
- 重构时一起动。
- 版本控制粒度一致。
- 块 ID 对齐简单。

分目录会引入"三处都可能改"的漂移风险。

---

## 3. 分隔符规范

### 3.1 为什么用目标语言的注释符

最终代码要交给编译器 / 解释器解析。分隔符不能是裸标记，必须是**目标语言合法的注释**，否则代码无法执行。

因此：
- **高层 DSL**：语言无关，用 `#` 作为注释符。
- **特化 DSL**：绑定目标语言，用目标语言的行注释符。
- **最终代码**：用目标语言的行注释符。

特化 DSL 与代码的块标记形式完全一致，方便逐块 diff 与 grep。

### 3.2 各语言注释符对照

| 语言 | 行注释 | 备注 |
|---|---|---|
| Python / Shell / Bash / Ruby / Perl / YAML / R / Julia / Elixir / Nim / Tcl / Awk | `#` | |
| C / C++ / Java / JavaScript / TypeScript / Go / Rust / C# / Kotlin / Swift / F# / Scala / Dart | `//` | |
| SQL / Haskell / Lua / Elm | `--` | |
| Lisp / Clojure / Scheme | `;` | |
| HTML / XML / SVG | `<!-- ... -->` | 无行注释，用块注释 |
| CSS | `/* ... */` | 无行注释，用块注释 |
| MATLAB / Octave / Erlang / Prolog | `%` | |
| VB / VBScript | `'` | |
| Fortran | `!` | |
| 汇编（x86 通用） | `;` | 部分汇编器用 `#` |

**策略**：优先行注释；无行注释的语言用块注释。

### 3.3 统一标记格式

```
<comment>@jev-block:<block_id>:begin
... 内容 ...
<comment>@jev-block:<block_id>:end
```

- `<comment>` 替换为目标语言的注释前缀（见 3.2）。
- `<block_id>` 是块标识。
- 标记行单独占一行，前后无其他内容。
- 标记体 `@jev-block:<id>:begin` 在三文件中完全一致，仅注释前缀不同。

### 3.4 块 ID 规范

```
<module>_<seq>                 # 如 auth_001
<module>_<seq>.<sub>           # 嵌套，如 auth_001.1
```

- **块 ID 一经分配终身不变**。修改块内容不改块 ID。
- 块 ID 在同一模块内唯一。
- 三文件使用相同块 ID。
- 支持嵌套，不重叠。

### 3.5 三文件中的形态

**高层 DSL**（Python 目标示例）：

```
# @jev-block:auth_001:begin
定义 验证用户(用户名, 密码):
    如果 用户名 == "":
        返回 假
    返回 检查密码(用户名, 密码)
# @jev-block:auth_001:end

# @jev-block:auth_002:begin
定义 检查密码(用户名, 密码):
    ...
# @jev-block:auth_002:end
```

**特化 DSL**（Python 特化）：

```
# @jev-block:auth_001:begin
定义 验证用户(用户名: str, 密码: str) -> bool:                # node:/python/function/define
    如果 用户名 == "":                                         # node:/python/control/if
        返回 False                                             # node:/python/function/return
    返回 检查密码(用户名, 密码)                                # node:/python/function/call
# @jev-block:auth_001:end
```

**最终代码**（Python）：

```python
# @jev-block:auth_001:begin
def validate_user(username: str, password: str) -> bool:
    if username == "":
        return False
    return check_password(username, password)
# @jev-block:auth_001:end
```

**最终代码**（C）：

```c
// @jev-block:auth_001:begin
bool validate_user(const char* username, const char* password) {
    if (username[0] == '\0') {
        return false;
    }
    return check_password(username, password);
}
// @jev-block:auth_001:end
```

**最终代码**（HTML）：

```html
<!-- @jev-block:page_001:begin -->
<div class="header">...</div>
<!-- @jev-block:page_001:end -->
```

### 3.6 边界规则

- 标记行必须独占一行，前后无其他字符。
- 块内容必须完整覆盖一个逻辑单元。
- 块之间允许存在不归属任何块的自由内容（imports、全局声明、空行）。
- 块不可重叠。
- 嵌套时，`<id>.<sub>` 必须完整位于父块 `<id>` 内。
- 若目标语言注释不能出现在某位置（如字符串内、表达式中间），则该位置不能打分隔符；通用 Agent 在打分隔符时必须保证位置合法。

---

## 4. 中文高层 DSL

高层 DSL 采用中文缩进语法，语言无关，作为 `semantic_v1` 的 sugar。canonical 仍是 S-表达式。

### 4.1 关键词表（封闭集合）

**结构与控制**：

| 中文关键词 | 语义 | semantic 节点 |
|---|---|---|
| `定义` | 函数定义 | `/function/define` |
| `返回` | 返回 | `/function/return` |
| `如果` / `否则如果` / `否则` | 条件分支 | `/control/branch/if` |
| `选择` / `情况` / `默认` | 多分支 | `/control/branch/switch` |
| `当` | while 循环 | `/control/loop/while` |
| `对于 … 中的 …` | 遍历集合 | `/control/loop/for` |
| `对于 … 从 … 到 … [步长 …]` | 索引迭代 | `/control/loop/iterate` |
| `尝试` / `捕获` / `抛出` | 异常 | `/error/try` `/error/catch` `/error/raise` |
| `跳出` / `继续` | break / continue | 控制流跳出 |
| `#` | 注释 | 无 |

**数据与类型**：

| 中文关键词 | 语义 |
|---|---|
| `设` | 显式声明 |
| `真` / `假` / `空` | 字面量 |
| `整数` / `浮点` / `布尔` / `字符串` / `列表` / `映射` | 类型标注 |
| `且` / `或` / `非` | 逻辑运算 |

**IO**：

| 中文关键词 | 语义 |
|---|---|
| `输出` | `/io/output` |
| `输入` | `/io/input` |

### 4.2 语法示例

```
定义 求大于阈值的平均值(数据列表, 阈值):
    总和 = 0
    计数 = 0

    对于 数据列表 中的 每个 元素:
        如果 元素 > 阈值:
            总和 = 总和 + 元素
            计数 = 计数 + 1

    如果 计数 == 0:
        返回 空

    返回 总和 / 计数
```

### 4.3 语法糖展开规则

| Python 语法糖 | 高层 DSL 展开 |
|---|---|
| `[x*2 for x in lst]` | `结果 = []` + `对于 lst 中的 x: 结果.追加(x*2)` |
| `{k:v for k,v in pairs}` | `结果 = {}` + `对于 pairs 中的 每对: 结果[键] = 值` |
| `lambda x: x+1` | `定义 匿名(x): 返回 x + 1` |
| `@decorator` | 显式包装函数定义 |
| `with open(...) as f:` | `尝试: ... 捕获 错误: ... 最终: 关闭(资源)` |
| `a, b = 1, 2` | `a = 1` + `b = 2` |
| `0 < x < 10` | `x > 0 且 x < 10` |
| `f"值={x}"` | `"值=" + 字符串(x)` |
| `lst[1:3]` | `切片(lst, 1, 3)` |
| `a if c else b` | 显式 `如果 c: ... 否则: ...` |
| `*args, **kwargs` | 显式列表 / 映射参数 |
| `yield` / `async` / `await` | 特化层处理 |
| `global` / `nonlocal` | 显式作用域声明 |
| `:=` | 显式赋值 |

### 4.4 与 S-表达式对应

中文 DSL：

```
定义 求平均值(数据列表):
    总和 = 0
    对于 数据列表 中的 每个 元素:
        总和 = 总和 + 元素
    返回 总和 / 长度(数据列表)
```

S-表达式：

```lisp
(define (求平均值 数据列表)
  (body
    (assign 总和 0)
    (for 元素 在 数据列表
      (assign 总和 (add 总和 元素)))
    (return (div 总和 (call 长度 数据列表)))))
```

节点名与 `semantic_v1` 中 `/function/define`、`/control/loop/for`、`/data/assign`、`/data/add`、`/data/div`、`/function/return` 一一对应。

### 4.5 不进入高层 DSL 的概念

以下概念不下沉到高层 DSL，全部由特化层处理：

- 内存管理：malloc / free / 所有权 / GC
- 指针与引用：指针算术 / 借用检查 / 智能指针
- 并发模型：goroutine / async / await / 线程调度
- 语言特有语法糖：推导式 / 宏 / 模板元编程 / 装饰器
- 平台特有：文件描述符 / 信号 / 系统调用细节

---

## 5. 特化语义 DSL

特化 DSL 是高层 DSL 的实例化版本，绑定目标语言。它是代码的可读中间表示，主要给 JevAgent 和通用 Agent 使用，人类不必常读。

### 5.1 结构

- **保留中文关键词**：`定义`、`如果`、`返回`、`对于` 等与高层 DSL 一致。
- **类型具体化**：用目标语言的类型名（`str`、`int`、`const char*` 等）。
- **字面量具体化**：用目标语言字面量（`False`、`false`、`""`）。
- **行尾节点标注**：每行末尾用行注释标注对应的特化节点路径（可选，Jev 生成时写入）。
- **语言特性显式标注**：语言特有的选择（如 Python 的 `len()` 判空 vs C 的 `'\0'` 检查）以注释形式标注原因。

### 5.2 示例

**Python 特化**：

```
# @jev-block:auth_001:begin
# spec: python_v3 | from: auth.high.dsl
定义 验证用户(用户名: str, 密码: str) -> bool:                # node:/python/function/define
    如果 用户名 == "":                                         # node:/python/control/if
        返回 False                                             # node:/python/function/return
    返回 检查密码(用户名, 密码)                                # node:/python/function/call
# @jev-block:auth_001:end
```

**C 特化**：

```
// @jev-block:auth_001:begin
// spec: c_v1 | from: auth.high.dsl
定义 验证用户(用户名: const char*, 密码: const char*) -> bool:    // node:/c/function/define
    // 特化：C 无字符串相等运算符，改用首字符判空
    如果 用户名[0] == '\0':                                        // node:/c/control/if
        返回 false                                                 // node:/c/function/return
    返回 检查密码(用户名, 密码)                                    // node:/c/function/call
// @jev-block:auth_001:end
```

### 5.3 与代码的对应

特化 DSL 的每一行对应代码的一行或一段：
- 结构化行（`定义`、`如果`）对应代码的声明 / 控制语句。
- 表达式行对应代码的表达式。
- 行尾 `node:` 标注给出该行使用的特化节点路径，模板填充时读取该路径。

### 5.4 双向可逆

特化 DSL ↔ 代码必须可往返：
- 正向：JevAgent 读特化 DSL，按 `node:` 标注填充模板，产代码。
- 反向：JevAgent 读代码，按表匹配节点，产特化 DSL。

往返测试纳入 `tests/roundtrip/`。

---

## 6. 工具接口

JevAgent 注册为通用 Agent 的工具集。接口统一返回结构化结果。

### 6.1 接口清单

| 工具名 | 输入 | 输出 |
|---|---|---|
| `jev.split_blocks` | 文件路径、文件类型 | `[{block_id, content, start, end}]` |
| `jev.high_to_spec` | 模块路径、目标语言、表引用 | `spec.<lang>.dsl` 落盘路径 + 报告 |
| `jev.spec_to_code` | 模块路径、目标语言、表引用 | 代码文件落盘路径 + 报告 |
| `jev.code_to_spec` | 模块路径（已含分隔符）、目标语言、表引用 | `spec.<lang>.dsl` + 报告 |
| `jev.spec_to_high` | 模块路径、表引用 | `high.dsl` + 报告 |
| `jev.translate_block` | block_id、方向、上下文 | 单块翻译结果 + 置信度 + 质疑 |

### 6.2 请求 / 响应结构

**`jev.translate_block` 请求**：

```json
{
  "block_id": "auth_001",
  "direction": "high_to_spec",
  "module_path": "src/auth/auth",
  "target_lang": "python",
  "table_ref": "python_v3",
  "block_content": "...",
  "prev_block_tail": "...",
  "next_block_head": "...",
  "shared_symbols": ["用户名", "密码"],
  "manifest_id": "manifest_2026_09_29_001",
  "context_window_budget": 2048
}
```

**响应**：

```json
{
  "block_id": "auth_001",
  "direction": "high_to_spec",
  "output": "...",
  "path": ["/python", "/function", "/define"],
  "confidence": 0.94,
  "ambiguities": [],
  "symbols_used": ["用户名", "密码", "检查密码"],
  "symbols_defined": ["验证用户"],
  "dsl_normalization": {
    "input_nodes": 4,
    "normalized_nodes": 4,
    "unknown_nodes": [],
    "description_deviations": []
  }
}
```

### 6.3 注册方式

视通用 Agent 框架而定：

| 框架 | 注册方式 |
|---|---|
| OpenAI Function Calling | 注册 JSON Schema 工具 |
| MCP | 暴露为 MCP Server：`mcp://jevagent/translate_block` 等 |
| LangChain / AutoGen | 提供 `BaseTool` 适配器 |
| 自研 | 提供 Python / TypeScript SDK |

### 6.4 禁止事项

- 禁止 JevAgent 调常规 LLM API。
- 禁止通用 Agent 直接冒充 Jev 做最终 Choice。
- 禁止 Jev 服务不可用时静默用通用 LLM 顶替。
- 禁止两套密钥混用。

---

## 7. 三条流程

### 7.1 编写流程

```
用户要求
  ↓
通用 Agent 理解意图
  ↓
通用 Agent 选择目标语言 + 高层语义表 + 特化表
  ↓
通用 Agent 写 <module>.high.dsl（含块分隔符），落盘
  ↓
通用 Agent 调用 jev.high_to_spec(module, target_lang, table_ref)
  ↓
JevAgent 按块读取 → 逐块路由到特化层 → 拼装 <module>.spec.<lang>.dsl，落盘
  ↓
通用 Agent 调用 jev.spec_to_code(module, target_lang, table_ref)
  ↓
JevAgent 按块读取 → 逐块叶子填充 → 拼装 <module>.<ext>，落盘
  ↓
通用 Agent 语义审 + Tier 1 确定性检查
  ↓
确认点提交（三文件 + 块索引 + manifest 一起入版本向量）
```

**关键点**：
- 落盘分三步，每步产生一个可独立查看 / 编辑的文件。
- 通用 Agent 只在第一步写内容，后两步是 JevAgent 生成，通用 Agent 只审不写。
- 任何一步失败，回滚到该步之前的确认点。

### 7.2 转换为可编写流程

```
已有代码（无分隔符）
  ↓
通用 Agent 阅读代码 → 选择特化表
  ↓
通用 Agent 在代码中以注释形式插入块分隔符，落盘为 <module>.<ext>
  （此步需要语义判断，Jev 不做）
  ↓
通用 Agent 调用 jev.code_to_spec(module, target_lang, table_ref)
  ↓
JevAgent 按分隔符拆块 → 逐块翻译为特化 DSL → 拼装 <module>.spec.<lang>.dsl，落盘
  ↓
通用 Agent 调用 jev.spec_to_high(module, table_ref)
  ↓
JevAgent 按分隔符拆块 → 逐块翻译为高层 DSL → 拼装 <module>.high.dsl，落盘
  ↓
通用 Agent 语义审（关键：确认高层语义忠实于原代码意图）
  ↓
确认点提交
```

**结果**：一份原本只有代码的模块，变成三文件齐全、可被 JevAgent 按块接手的可编写状态。

**跨语言转换也走这条路**：已有 C 代码 → `code_to_spec` → `spec_to_high` → 得到 `high.dsl` → 换目标语言，`high_to_spec` + `spec_to_code` → 得到 Python 代码。通用 Agent 全程盯梢语义等价性。

### 7.3 修改流程

```
人类或通用 Agent 定位到某个块（按 @jev-block:<id>）
  ↓
修改 <module>.high.dsl 中该块的内容
  ↓
通用 Agent 调用 jev.translate_block(block_id, "high_to_spec", context)
  ↓
JevAgent 只翻译这一个块 → 替换 <module>.spec.<lang>.dsl 中对应块
  ↓
通用 Agent 调用 jev.translate_block(block_id, "spec_to_code", context)
  ↓
JevAgent 只翻译这一个块 → 替换 <module>.<ext> 中对应块
  ↓
通用 Agent 审查该块 + 相邻块接口
  ↓
确认点提交（只更新该块相关的版本向量）
```

**关键点**：
- **不整体重跑**。改一个块只翻译一个块，成本与块数无关，只与改动块数相关。
- 三文件的对应块靠 `block_id` 对齐。
- 若修改影响了块的对外接口（签名、副作用），通用 Agent 负责检查相邻块的契约。

---

## 8. 块拆分与上下文传递

### 8.1 拆分由 JevAgent 的 BlockSplitter 完成

`BlockSplitter` 是 JevAgent 的模块，不是 Jev 模型。它只做机械拆分：
- 扫描分隔符标记。
- 提取块 ID、内容、起止位置。
- 保留块间自由内容。
- 嵌套块按层级组织。

### 8.2 上下文打包

Jev 上下文窗口有限，块不能太大；但块不能完全独立，翻译时需要相邻上下文。`ContextPacker` 负责打包：

```json
{
  "block_id": "auth_001",
  "block_content": "...",
  "prev_block_tail": "...",
  "next_block_head": "...",
  "shared_symbols": ["用户名", "密码"],
  "manifest": "manifest_2026_09_29_001",
  "direction": "high_to_spec",
  "target_table": "python_v3"
}
```

- `prev_block_tail` / `next_block_head`：只取摘要（如函数签名、前 3 行、后 3 行），避免爆窗。
- `shared_symbols`：由通用 Agent 维护的符号表快照，保证跨块命名一致。
- 块大小约束沿用设计稿：≤ Jev 上下文窗口的 50%（建议 8k–16k token 窗口下取 4k–8k）。

### 8.3 拼装

翻译完成后，JevAgent 按原顺序拼回：
- 块内容替换。
- 块间自由内容保留。
- 分隔符标记保留（不被翻译吞掉）。

---

## 9. 表选择与方向控制

**选择用哪张表、往哪个语言特化，由通用 Agent 把关。**

理由：通用 Agent 能更好理解用户意图。JevAgent 只按通用 Agent 指定的表执行。

### 9.1 通用 Agent 的选表输入

- 用户意图描述。
- 目标运行环境（编译 / 解释 / 执行）。
- 现有代码库的语言分布。
- 性能 / 可维护性 / 生态约束。

### 9.2 多表选择

若一个模块需同时产出多语言，通用 Agent 逐个指定：

```
auth.high.dsl
  → (python_v3) → auth.spec.python.dsl → auth.py
  → (c_v1)      → auth.spec.c.dsl      → auth.c
```

高层语义复用，特化层分叉。

### 9.3 表版本绑定

表版本写入 manifest（见第 11 节）。表升级时，需重新翻译受影响的块（走修改流程）。

---

## 10. 落盘、命名、目录结构

### 10.1 命名规范

```
<module>.high.dsl                    高层语义
<module>.spec.<lang>.dsl             特化语义
<module>.<ext>                       代码
```

- `<module>`：模块名，小写下划线，与代码内模块名一致。
- `<lang>`：语言标识，如 `python`、`c`、`shell`、`js`、`go`。
- `<ext>`：语言标准扩展名，如 `.py`、`.c`、`.sh`、`.js`、`.go`。

### 10.2 目录结构

```
project/
├── manifest.json                     # 版本绑定
├── blocks_index.json                 # 块 ID ↔ 三文件映射、依赖、状态
├── src/
│   ├── auth/
│   │   ├── auth.high.dsl
│   │   ├── auth.spec.python.dsl
│   │   ├── auth.py
│   │   ├── auth.spec.c.dsl
│   │   └── auth.c
│   └── utils/
│       ├── utils.high.dsl
│       ├── utils.spec.python.dsl
│       └── utils.py
├── tables/                           # 路由表
│   ├── skeleton_v1.json
│   ├── semantic_v1.json
│   ├── python_v3.json
│   ├── c_v1.json
│   └── shell_v2.json
├── vocab/                            # 词表
│   ├── common.json
│   ├── python.json
│   └── dialog.json
├── dsl/                              # DSL 解析 / 生成
│   ├── parser.py
│   ├── emitter.py
│   └── roundtrip_test.py
└── .jev/
    ├── cache/
    └── audit/
```

### 10.3 blocks_index.json

```json
{
  "module": "auth",
  "blocks": [
    {
      "block_id": "auth_001",
      "files": {
        "high": "src/auth/auth.high.dsl",
        "spec": {"python": "src/auth/auth.spec.python.dsl", "c": "src/auth/auth.spec.c.dsl"},
        "code": {"python": "src/auth/auth.py", "c": "src/auth/auth.c"}
      },
      "symbols_defined": ["验证用户"],
      "symbols_used": ["检查密码"],
      "status": "confirmed"
    },
    {
      "block_id": "auth_002",
      "files": { "...": "..." },
      "status": "confirmed"
    }
  ]
}
```

`status` 取值：`draft` / `translated` / `confirmed` / `rolled_back`。

---

## 11. Manifest 与版本绑定

```json
{
  "manifest_id": "manifest_2026_09_29_001",
  "skeleton": "common_skeleton_v1",
  "semantic": "semantic_v1",
  "tables": {
    "python": "python_v3",
    "c": "c_v1",
    "shell": "shell_v2"
  },
  "vocab": "common_v3",
  "mappings": {
    "python": "python_v3_semantic",
    "c": "c_v1_semantic"
  },
  "symbol_snapshot": "sym_001",
  "code_commit": "git_abc",
  "dsl_commit": "git_def",
  "jev_model": "jev-4b-v1",
  "jevagent_version": "2.0.0"
}
```

### 11.1 缓存键

```
cache_key = hash(
  manifest_id +
  block_id +
  direction +
  block_content_hash +
  target_table +
  symbol_env_snapshot +
  candidate_vocab_version
)
```

版本变化 → 缓存失效。

### 11.2 确认点版本向量

每个确认点绑定：

- 三文件对应块的内容哈希。
- 块 ID。
- manifest_id。
- 符号表快照。
- 动态节点集合（若该块涉及运行期）。
- 审查状态。

回滚时，按版本向量恢复三文件对应块 + 符号表 + 动态节点 + 缓存键。

---

## 12. 错误处理与质疑

| 错误 | 处理 |
|---|---|
| Jev API 超时 | 重试 2 次，指数退避；仍失败 → `jev_unavailable`，阻塞 |
| Jev API 5xx | 同上 |
| Jev API 限流 | 退避 + 队列；不可逆操作阻塞 |
| Jev 返回 schema 错 | 标记 `jev_schema_invalid`，不采信 |
| Jev 模型版本不匹配 | 拒绝，要求切换 manifest |
| `unknown_node` | 阻塞，通用 Agent 澄清或词表工厂补全 |
| `no_mapping` | 查 `raw_fallback`，允许则 raw，否则质疑 |
| `guard_failed` | 抛质疑或回退 raw |
| `vocab_invalid` | 拒绝合并，可部分合并，严重人工介入 |
| 分隔符未闭合 | `malformed_block`，阻塞 |
| 分隔符嵌套非法 | `invalid_nesting`，阻塞 |
| 块 ID 冲突 | `duplicate_block_id`，阻塞 |
| 块 ID 在三文件中不对齐 | `block_mismatch`，阻塞 |
| 常规 LLM 失败 | 通用 Agent 自身降级策略；Jev 不顶替 |

### 12.1 重试原则

- Choice / Score / Noul 幂等，可重试。
- 不可逆操作审查失败 → 回滚最近确认点。
- 边界模糊默认阻塞。

### 12.2 质疑格式

沿用设计稿第 10.2 节结构，新增字段：

```json
{
  "ambiguity_type": "malformed_block",
  "block_id": "auth_001",
  "file": "auth.high.dsl",
  "line": 12,
  "description": "块 auth_001 缺少 end 标记",
  "blocking": true
}
```

---

## 13. 与审查层集成

### 13.1 分层策略

| Tier | 内容 | 触发 |
|---|---|---|
| Tier 0 | JevAgent 置信度 | 高置信 + 可逆 → 直接过 |
| Tier 1 | 确定性检查（沙箱 / lint / 分隔符校验 / 块对齐） | 永远开 |
| Tier 2 | 通用 Agent 语义审 | 中低置信 / 不可逆 / 跨语言 |
| Tier 3 | 人类仲裁 | Tier 2 分歧 |

### 13.2 阻塞规则

- **生成三文件** → 可逆，非阻塞，异步审。
- **执行代码 / 写文件 / 网络请求 / 数据库修改** → 不可逆，阻塞。

### 13.3 审查粒度

- **块级**：一个块审一次。
- **三文件对齐审**：确认三文件中块 ID 一致、内容对应。
- **语义审**：通用 Agent 读高层 DSL + 特化 DSL + 代码，确认语义等价。

### 13.4 回滚

回滚到最近确认点，恢复：

- 三文件对应块。
- 符号表快照。
- 动态节点。
- 块间契约。
- 缓存键。
- 审查状态。

已发布词表 / 路由表版本不回滚，只切换引用。

---

## 14. 部署形态

### 14.1 开发环境

```
本地通用 Agent 进程
  → JevAgent SDK
  → 本地 Jev Runtime
      → Ollama / llama.cpp / vLLM
      → jev-4b
```

### 14.2 生产环境

```
通用 Agent 集群
  → JevAgent Service（HTTP / gRPC / MCP）
      → Jev Runtime 集群
          → 内网 4B Jev 模型
```

### 14.3 双 API 配置

```yaml
orchestrator:
  llm:
    provider: openai_compatible
    base_url: ${AGENT_API_BASE_URL}
    api_key: ${AGENT_API_KEY}
    model: ${AGENT_MODEL}
    timeout_s: 120

jev:
  runtime:
    provider: native_jev
    base_url: ${JEV_API_BASE_URL}
    api_key: ${JEV_API_KEY}
    model: ${JEV_MODEL}
    timeout_s: 10
  agent:
    mode: embedded                  # embedded | sidecar | remote
    manifest_path: ./manifest.json
    tables_dir: ./tables
    vocab_dir: ./vocab
    cache_dir: ./.jev/cache
```

两套密钥必须来自不同 secret scope，不落盘、不进日志、不进 prompt。

---

## 15. 测试与验收

### 15.1 测试层级

| 层级 | 内容 |
|---|---|
| 单元测试 | 分隔符拆分 / 拼装、块 ID 校验、路由、模板、符号表、词表验证 |
| 契约测试 | Jev Runtime API schema、双 API mock |
| 集成测试 | 通用 Agent → JevAgent → Jev Runtime |
| 三文件对齐测试 | 三文件中块 ID 一致、内容对应 |
| 往返测试 | 高层 DSL ↔ S-表达式、特化 DSL ↔ 代码 |
| 黄金样例 | 跨层验证：公约数 DSL → C / Python → 执行结果比对 |
| 回归测试 | 词表 / 表变更后黄金样例不回归 |
| 混沌测试 | Jev 宕机、超时、限流、版本不匹配 |
| 安全测试 | AST、白名单、沙箱、密钥隔离 |

### 15.2 最小验收标准

- 能配置两套 API：常规 LLM API + Jev API。
- 能注册 JevAgent 工具到现有 Agent。
- 能跑通编写流程：写 `high.dsl` → `high_to_spec` → `spec_to_code` → 三文件落盘。
- 能跑通转换流程：给已有代码打分隔符 → `code_to_spec` → `spec_to_high` → 三文件落盘。
- 能跑通修改流程：改一个块 → 只翻译一个块 → 三文件该块同步更新。
- 能处理 `unknown_node`、`no_mapping`、`vocab_invalid`、`malformed_block`。
- 能回滚到最近确认点。
- 黄金样例跨层验证通过。
- Jev 服务不可用时不会静默用通用 LLM 顶替。
- 最终代码能被目标语言编译器 / 解释器正常解析（分隔符不破坏语法）。

---

## 16. 实现路线图

### Phase E1：基础工具与双 API

- LLMClient / JevClient
- 配置 schema、环境变量、密钥隔离
- Jev Runtime 适配（native + openai_compatible）

### Phase E2：三文件与分隔符

- BlockSplitter（多语言注释符）
- 三文件落盘 / 读取
- blocks_index.json
- 块 ID 校验

### Phase E3：高层 DSL 与特化 DSL

- 中文高层 DSL parser / emitter
- S-表达式互转
- 特化 DSL 结构定义
- 往返测试

### Phase E4：JevAgent SDK 与工具注册

- RouterEngine / TemplateEngine / SymbolTable / VocabValidator / NormalizeDsl / ContextPacker
- 工具注册（MCP / Function Calling / SDK）
- `translate_block` 等接口

### Phase E5：三条流程打通

- 编写流程端到端
- 转换为可编写流程端到端
- 修改流程端到端

### Phase E6：审查与确认点

- Tier 1 确定性检查（含分隔符校验）
- Tier 2 异构语义审
- 确认点版本向量
- 回滚

### Phase E7：多语言与跨层验证

- semantic_v1
- C / Shell / Python 特化表
- 黄金样例跨层验证
- raw 节点控制

### Phase E8：词表工厂

- 候选词表生成（通用 Agent）
- 词表语法验证（JevAgent）
- 冲突检查 / 回归测试 / 版本化

---

## 17. 与设计稿 V1.0 的关系

本稿不修改设计稿 V1.0 的任何冻结结论，只在其下补全工程落地。

| 设计稿条目 | 本稿对应 |
|---|---|
| 3.1 总览图 | 第 1 节：JevAgent 降为工具 |
| 6.2 处理流程 | 第 7 节：三条流程重写 |
| 11.4 调用协议 | 第 6 节：工具接口重写 |
| 15.2 缩进语法 | 第 4 节：中文高层 DSL 替换 |
| 18.1 manifest | 第 11 节：扩展为绑定三文件 + 块索引 |
| 8.8 回滚 | 第 13.4 节：回滚粒度细化为"块 + 三文件对应投影" |

**新增冻结项**：

1. 三文件同目录同基名：`<module>.high.dsl` / `<module>.spec.<lang>.dsl` / `<module>.<ext>`。
2. 块 ID 终身不变：`<module>_<seq>`，允许嵌套 `_<seq>.<sub>`。
3. 分隔符统一标记：`@jev-block:<id>:begin` / `:end`，注释前缀随目标语言。
4. 高层 DSL 用 `#`，特化 DSL 与代码用目标语言行注释符。
5. 改块不重跑全量：修改流程按块翻译，成本 O(改动块数)。
6. 通用 Agent 打分隔符：代码 → 特化层的切块由通用 Agent 做，JevAgent 不做切块语义判断。

---

## 18. 一句话总结

> JevAgent 是通用 Agent 的一个 tool。输入是"带块分隔符的高层 / 特化 DSL 或代码 + 目标语言表"，输出是同块 ID 的下一层表示。三文件同目录同基名，块 ID 终身不变，分隔符用目标语言注释符保证代码可编译，改一个块只翻一个块。通用 Agent 管意图、选表、打分隔符、写高层；JevAgent 管逐块翻译、路由、补全、验证。