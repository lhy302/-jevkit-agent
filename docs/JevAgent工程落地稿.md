# JevAgent 工程落地稿 V3.0

> 配套规范：《JevAgent 设计稿 V2.0》。本稿完全替代《JevAgent 工程落地稿 V2.0》。
> 权威依据：《JevAgent 重构方案：二文件模型与库导入层》（含第 11 节决策记录 D1~D20，**binding**）。
> 冲突处理：设计稿 V2.0 的冻结结论（封闭集合、路由 schema、确认点版本向量、词表工厂生效时机、异构审查要求）以设计稿为准；工程落地、二文件模型、分隔符与块类别、库导入层、校验防火墙、通用关键字核、流程、接口以本稿为准。
> 本稿为破坏性版本变更，对应 `jevagent_version = 3.0.0`。

---

## 0. 本稿解决的问题

V2.0 落地稿以三份表示为轴组织条款，该组织方式已被判定不成立（结论见 2.5 与第 18 节）。本稿对准以下问题：

- **唯一真相源不明确**：二文件模型下唯一真相源是 `<module>.spec.<lang>.dsl`，无歧义。
- **库导入无归属**：导入此前只能作为块外自由内容硬写，无注解、无去重、无位置与完整性保证，直接导致 C 产物缺 `#include` 而无法编译。
- **生成完整性无保证**：骨架层声明了却从未被消费；收尾符号、类型声明、格式符缺口靠人工补丁。
- **未知输入被静默吞掉**：未识别行静默落到 `/{lang}/raw`，使整层退化为逃生舱，BUG-04 / BUG-05 长期潜伏。
- **语言表完整性无校验**：缺节点、映射悬空、关键字表与代码构成双真相源，靠约定必然漂移。
- **跨语言无路径**：一源多目标路径消失，须以"复制 + 定点处理"重建。

本稿重写：**角色定位、二文件模型、分隔符与块类别、spec DSL 语法、spec 与代码的对应、工具接口、两条主流程 + 一条辅助流程、块拆分与保留块、表选择与方向控制、落盘命名与目录、manifest 与版本绑定、错误处理与质疑、审查集成、部署形态、测试与验收、实现路线图**。

---

## 1. JevAgent 的角色定位

**JevAgent 是通用 Agent 的编程专用扩展工具，注册在 tool 字段调用，不替代通用 Agent。**

核心痛点：通用 Agent 把大量算力浪费在"语法长什么样"，而不是"逻辑是什么"。JevAgent 把语法补全、导入解析、生成完整性从通用 Agent 的工作量里剥离出去。

### 1.1 职责划分

| 职责 | 归属 |
|---|---|
| 理解用户意图、选择目标语言与表 | 通用 Agent |
| 在 spec DSL 中书写逻辑与所需库 | 通用 Agent |
| 给既有代码打块分隔符 | 通用 Agent |
| 编译 / 执行验证 | 通用 Agent（工具只保证生成） |
| spec DSL → 最终代码 | JevAgent（逐块） |
| 代码 → spec DSL | JevAgent（逐块） |
| 修改后按块重译（不整体重跑） | JevAgent |
| 库导入的真实语法、位置、去重、完整性 | JevAgent |
| 闭合符号、骨架、格式符等生成完整性 | JevAgent |
| 引用合法性校验（防火墙） | JevAgent |
| 语义审 | 通用 Agent |
| 结构审 / 语法验证 | JevAgent / Tier 1 |

### 1.2 JevAgent 内部构成

```
JevAgent（工具系统）
├── BlockSplitter      读分隔符，拆块 / 拼块；识别块类别与保留块
├── RouterEngine       按表路由，产路径；核心节点优先解析
├── TemplateEngine     叶子模板填充；骨架与收尾符号
├── SymbolTable        符号表读写；以 names 块为权威源
├── Validator          校验防火墙（引用合法性 / 闭包完整性 / 纠偏）
├── VocabValidator     词表与语言表语法验证（含 check_tables）
├── NormalizeDsl       关键字归一（由 syntax_core_v1 驱动）
├── ContextPacker      块前后文打包，控制上下文窗口
└── JevClient          → Jev 模型 API（仅 Choice / Score / Noul）

Jev（模型）
└── 只做 Choice / Score / Noul，不生成自由文本
```

**关键区分**：BlockSplitter 是 JevAgent 的模块，不是 Jev 模型；Jev 模型只做候选内判断，不做代码拆分。

**本层存在的三条理由**（判据：一层只有在承载另一层无法承载的信息时才配存在）：

| 腿 | 机制 | 承载的独有信息 |
|---|---|---|
| 可追溯 | 行尾 `node:` 注解 | 每行语义归属（BUG-04 / BUG-05 正是靠它被发现） |
| 可校验 | 校验防火墙（第 12 节） | 符号来源、库归属、类型、作用域 |
| 可迁移 | 通用关键字核（第 13 节） | 写法差异（词汇 / 语法 / 运算符） |

---

## 2. 二文件模型

每个逻辑模块（一个函数、一个文件、一个可独立验证单元）有两份表示，**同目录、同基名、扩展名区分**：

```
<module>.spec.<lang>.dsl       唯一真相源（SSOT）：中文关键字 + 目标语言语义 + node 注解
<module>.<ext>                 生成产物（含置顶导入区）
```

`auth` 模块，Python 目标：

```
auth/
  auth.spec.python.dsl
  auth.py
```

同一模块再出 C 版本属**跨语言迁移**（见 7.4 与 13.6），新增一组二文件：`auth.spec.c.dsl` + `auth.c`。

### 2.1 二文件的职责

| 文件 | 谁写 | 谁读 | 作用 |
|---|---|---|---|
| `.spec.<lang>.dsl` | 通用 Agent（首作者），JevAgent（闭包回写、纠偏回写） | 通用 Agent、人类、JevAgent | **逻辑的唯一真相源**，语言绑定 |
| `.<ext>` | JevAgent | 编译器 / 解释器 | 最终产物，**不手工修改** |

**关键约束**：

- 修改逻辑**一律改 spec**；代码是派生表示，既有代码入口走 `code_to_spec`（7.2）。
- 二文件通过块 ID 与块类别对应（`declaration-only` 块不出现在代码侧，见 3.6）。
- 工具对 spec 的写入是**受控写入**：仅限导入闭包回写（`origin:auto`）与 `confusions` 纠偏（`auto-corrected`），其余一律不自动改写。
- spec 内部的 `/semantic/*` 路由路径保留为**内部路由中间层**，不是用户可写层，也不是独立文件。

### 2.2 为什么同目录同基名

两份表示是同一逻辑的两个投影，同目录保证：diff 时一起走、重构时一起动、版本控制粒度一致、块 ID 对齐简单（`check_alignment` 只需比较同目录两文件的块 ID 集合与顺序）。分目录会引入"两处都可能改"的漂移风险。

### 2.3 落盘顺序与失败回滚

```
spec 落盘 → check_spec（预检）→ spec_to_code → code 落盘
         → check_alignment（spec ↔ code 块 ID 集合与顺序一致）→ 确认点
```

任何一步失败，回滚到该步之前的确认点（见 13.4）。`spec_to_code` **必须幂等**：连续运行两次产物字节一致。

### 2.4 `blocks_index.json` 与 `manifest.json`

二文件模型下这两个文件仍与模块同目录自动维护：`blocks_index.json`（二文件映射 + 块状态 + 依赖，结构见 10.3，`files.high` 字段已移除）、`manifest.json`（版本绑定，结构见第 11 节）。

### 2.5 存量迁移

现有旧格式模块按"一次性转换后删除旧文件"处理，不保留兼容层：

| 现有工件 | 处理 |
|---|---|
| `<module>.high.dsl` | 用**现版** `high_to_spec` 生成 `<module>.spec.<lang>.dsl` → **删除 `.high.dsl`** |
| `<module>.spec.<lang>.dsl` / `<module>.<ext>` | 保留，作为回归基线 |
| 其他旧格式语料（含实验期残留） | 同上转换，转为 spec 语料。**本仓库无常驻旧格式模块**，该规则面向使用者项目 |

**迁移后的清理项**：

1. 旧格式相关动作（`high_to_spec` / `spec_to_high`）从工具动作枚举、schema、描述中移除。
2. `blocks_index.json` 移除 `files.high` 字段。
3. `manifest.json` 移除旧格式描述，新增 `required_imports_version` 与 `skeleton` 实际生效标记。
4. `lib/normalize.js` 的 `KEYWORD_MAP` 由 `syntax_core_v1.json` 驱动，成为中文关键字 ↔ 目标语言关键字的**单一真相源**。
5. 注入通用 Agent 的系统提示词指导同步改写为二文件模型 + 迁移约定（13.6）。

> 迁移只发生一次；迁移完成后，本稿不再出现旧格式路径。

---

## 3. 分隔符规范

### 3.1 为什么用目标语言的注释符

最终代码要交给编译器 / 解释器解析，分隔符不能是裸标记，必须是**目标语言合法的注释**。spec DSL 与最终代码均用目标语言的行注释符；两者块标记形式**完全一致**，方便逐块 diff 与 grep。

### 3.2 各语言注释符对照

| 语言 | 行注释 | 备注 |
|---|---|---|
| Python / Shell / Bash / Ruby / Perl / YAML / R / Julia / Elixir / Nim / Tcl / Awk | `#` | |
| C / C++ / Java / JavaScript / TypeScript / Go / Rust / C# / Kotlin / Swift / F# / Scala / Dart | `//` | |
| SQL / Haskell / Lua / Elm | `--` | |
| Lisp / Clojure / Scheme / 汇编（x86 通用） | `;` | 汇编部分用 `#` |
| HTML / XML / SVG | `<!-- ... -->` | 无行注释，用块注释 |
| CSS | `/* ... */` | 无行注释，用块注释 |
| MATLAB / Octave / Erlang / Prolog / VB / Fortran | `%` / `'` / `!` | 各自按语言取用 |

**策略**：优先行注释；无行注释的语言用块注释。

### 3.3 统一标记格式

```
<comment>@jev-block:<block_id>:begin
... 内容 ...
<comment>@jev-block:<block_id>:end
```

- `<comment>` 替换为目标语言的注释前缀（见 3.2）；`<block_id>` 是块标识。
- 标记行单独占一行，前后无其他内容。
- 标记体 `@jev-block:<id>:begin` 在 spec 与 code 两文件中完全一致，仅注释前缀随语言。
- 保留块使用固定 ID：`names`、`imports`（见 3.6）。

### 3.4 块 ID 规范

```
<module>_<seq>                 # 如 auth_001
<module>_<seq>.<sub>           # 嵌套，如 auth_001.1
```

- **块 ID 一经分配终身不变**；修改块内容不改块 ID。
- 块 ID 在同一模块内唯一；spec 与 code 使用相同块 ID。
- 支持嵌套，不重叠。

### 3.5 二文件中的形态

**spec DSL**（Python 目标）：

```
# @jev-block:names:begin
库 math
变量 数据: list
变量 计数: int
# @jev-block:names:end

# @jev-block:imports:begin
引入 math                                   # node:/python/module/import origin:declared
# @jev-block:imports:end

# @jev-block:auth_001:begin
定义 验证用户(用户名: str, 密码: str) -> bool:                # node:/python/function/define
    如果 用户名 == "":                                         # node:/python/control/if
        返回 False                                             # node:/python/function/return
    返回 检查密码(用户名, 密码)                                # node:/python/function/call
# @jev-block:auth_001:end
```

**最终代码**（Python）：`names` 块不出现在代码侧（`declaration-only`），`imports` 块置顶（`hoisted`）。

```python
# @jev-block:imports:begin
import math
# @jev-block:imports:end

# @jev-block:auth_001:begin
def validate_user(username: str, password: str) -> bool:
    if username == "":
        return False
    return check_password(username, password)
# @jev-block:auth_001:end
```

**最终代码**（C，块标记随语言换成 `//`）：

```c
// @jev-block:auth_001:begin
bool validate_user(const char* username, const char* password) {
    if (username[0] == '\0') { return false; }
    return check_password(username, password);
}
// @jev-block:auth_001:end
```

**最终代码**（HTML，无行注释语言，改用块注释标记）：`<!-- @jev-block:page_001:begin --> … <!-- @jev-block:page_001:end -->`。

### 3.6 边界规则与块类别

| 类别 | 例子 | 存在于 spec | 存在于 code | 参与对齐 |
|---|---|---|---|---|
| `emitting`（默认） | 所有普通块 | ✅ | ✅ | ✅ |
| `declaration-only` | `names` | ✅ | ❌ | ❌ |
| `hoisted` | `imports` | ✅ | ✅ | ✅（位置强制首位） |

**为什么必须有块类别**：`check_alignment` 按块 ID 顺序严格比较；若不引入类别，第一个带 `names` 的模块必然对齐失败。块类别必须先于 `names` 块落地（P0 内完成）。

**边界规则**：

- 标记行必须独占一行，前后无其他字符；块不可重叠。
- 块内容必须完整覆盖一个逻辑单元；嵌套时 `<id>.<sub>` 必须完整位于父块 `<id>` 内。
- 块之间允许存在不归属任何块的**自由内容**（全局声明、空行、尾注），在翻译与拼装中**无损保留**（含空行数量）。
- 若目标语言注释不能出现在某位置（字符串内、表达式中间），该位置不能打分隔符；通用 Agent 打分隔符时必须保证位置合法。
- 引入 `names` 与 `imports` 后，**自由区不再承担导入职责**：导入必须落在 `imports` 块内或由工具闭包生成，否则 `code_to_spec` 无法收纳、`check_alignment` 无法平衡。

**保留块的拆分与置顶规则**：

- `names` 块置于 spec 文件开头（`declaration-only`，不参与对齐）。
- `imports` 块在 **spec 与 code 两文件中一致地**提到首位（C 语言置于头部注释之后、任何代码之前）。
- `imports` 块缺失但闭包产出了导入 → 工具**自动创建**该块并写入（回写 spec + 写入 code）。
- 存在多个 `imports` 块 → 合并为一个，保持首次出现位置。

---

## 4. spec DSL 的语法

spec DSL 采用中文缩进语法，**绑定目标语言**，是唯一真相源：作者（通用 Agent）在其中直接书写逻辑与所需库。

### 4.1 关键词表（通用关键字核，闭集）

关键词表由 `tables/syntax_core_v1.json` 定义，**语言无关**，各语言 DSL 共享同一套关键字与运算符表达。该表为**闭集**：新增节点需经评审（参照候选词表流程），不得就地扩展。

**结构与控制**：

| 中文关键词（canonical） | 别名（容错输入） | 核心节点 |
|---|---|---|
| `定义` | `函数`、`定义函数` | `/core/define` |
| `返回` | `回` | `/core/return` |
| `如果` / `否则如果` / `否则` | `若` / `否则若` / — | `/core/if` `/core/elif` `/core/else` |
| `当` / `对于 … 中的 …` | `循环当` / `遍历` | `/core/loop/while` `/core/loop/for` |
| `跳出` / `继续` | `break` / `continue` | `/core/loop/break` `/core/loop/continue` |
| `设` | `声明`、`定义变量` | `/core/var/declare` |
| `输出` / `输入` | `打印` / `读取` | `/core/io/output` `/core/io/input` |

**库与导入**（`imports` 块专用，仍属通用核）：

| 中文关键词 | 别名 | 核心节点 |
|---|---|---|
| `引入 <module>` / `引入 <module> 作为 <alias>` | `导入` / `导入 … 作为 …` | `/core/module/import` `/core/module/import_as` |
| `从 <module> 引入 <names>` | `自 … 引入 …` | `/core/module/from_import` |
| `引入系统 <header>` / `引入本地 <header>` | — | `/core/module/import/system` `/core/module/import/local` |

**符号宇宙**（`names` 块专用）：`库 <module> [作为 <alias>]`、`变量 <name>[: <type>]`、`常量 <name> = <value>`、`函数 <name>(<params>) -> <ret>`（可选）。

**运算符核**（`core_operators`）：

| 作者统一写法 | Python | C | Shell |
|---|---|---|---|
| `<=` / `>=` | `<=` / `>=` | `<=` / `>=` | `-le` / `-ge` |
| `并且` / `或者` / `非` | `and` / `or` / `not` | `&&` / `\|\|` / `!` | `&&` / `\|\|` / `!` |

**运算符核只屏蔽写法差异，不屏蔽语义差异**；语义差异由各语言的履约声明显式标注（见 9.4），不作粉饰。

**常量书写**：`True` / `False` / `None` 为 canonical（照抄代码形态）；`真` / `假` / `空` 保留为**容错输入别名**，归一后输出只出 canonical。

### 4.2 语法示例与生成的对应

```
# @jev-block:names:begin
库 stdio.h
变量 累计: int
常量 步长 = 1
# @jev-block:names:end

# @jev-block:imports:begin
引入系统 stdio.h                            # node:/c/module/include_system origin:declared
# @jev-block:imports:end

# @jev-block:csum_001:begin
定义 累加(上限: int) -> int:                // node:/c/function/define
    设 累计: int = 0                        // node:/c/data/declare
    当 累计 <= 上限:                        // node:/c/control/while
        累计 += 步长                        // node:/c/data/assign
    返回 累计                               // node:/c/function/return
# @jev-block:csum_001:end
```

生成结果（`<=` 由运算符核转换；`&` 取地址符由 `names` 类型声明推导；骨架与闭包导入在导入区同一次去重合并）：

```c
// @jev-block:imports:begin
#include <stdio.h>
// @jev-block:imports:end

// @jev-block:csum_001:begin
int 累加(int 上限) {
    int 累计 = 0;
    while (累计 <= 上限) {
        累计 += 1;
    }
    return 累计;
}
// @jev-block:csum_001:end
```

### 4.3 语法糖展开规则

各语言的语法糖**不进入 spec DSL**，由工具按 `core_operators` 与模板展开：

| 目标语言语法糖 | spec DSL 展开 |
|---|---|
| Python `[x*2 for x in lst]` / `lambda` | `结果 = []` + `对于 lst 中的 x: …`；或显式原生透传 |
| Python `a, b = 1, 2` / `0 < x < 10` | 拆为两条赋值 / `x > 0 并且 x < 10` |
| Python `f"值={x}"` / `with open(...) as f:` | `输出("值=" + 字符串(x))` / `尝试 … 捕获 … 最终 …` |
| Python `yield` / `async` / `await` / `@decorator` | 语言表节点、显式包装函数定义，或显式原生透传 |
| C 三元 `a ? b : c` | 显式 `如果 … 否则 …` |
| C 格式符 `%d` / `%s` | 作者只写 `输出(表达式)`，**格式符由工具按类型解析** |
| Shell test `-le` / `-ge`、变量引用 `"$var"` | 作者只写 `<=` / `>=` 与变量名，生成器负责形态 |
| Shell 闭合 `}` / `done` / `fi`、语句结束符 `;`、大括号 | 由生成器补齐，作者不写 |

### 4.4 容错别名归一

- 每个核心节点有 **canonical（唯一输出形式）** 与 **aliases（容错输入集，闭集）**。
- 归一在 `NormalizeDsl` 中完成，由 `syntax_core_v1.json` 驱动，**只用 canonical 定位节点**。
- **未命中别名集 → 硬错误 `unknown_node`**，附最近候选建议（编辑距离**只用于给建议，绝不自动采用**）。
- `confusions` 表负责少量确定的跨语言误写纠偏（档 B：仅 `action: correct` 自动改，且必须在报告中可见）；其余一律报错。
- 归一结果写入响应字段 `dsl_normalization`：`{input_nodes, normalized_nodes, unknown_nodes, auto_corrected, description_deviations}`。

### 4.5 不进入 spec DSL 的概念

以下概念不下沉到 spec DSL，**留在各语言表中处理**，并按 `core_conformance` 三档显式标注（见 9.4）：

| 概念 | 例子 | 处理 |
|---|---|---|
| 内存管理 | `malloc` / `free` / 所有权 / GC | 语言表节点；C 侧走 `stdlib.h` 闭包 |
| 指针与引用 | 指针算术 / 借用检查 / 智能指针 | 语言表节点；不可表达 → 显式标记的原生透传 |
| 并发模型 | goroutine / async / await / 线程调度 | 语言表节点 |
| 语言特有语法糖 | 推导式 / 宏 / 模板元编程 / 装饰器 | 4.3 语法糖展开，或显式原生透传 |
| 平台特有 | 文件描述符 / 信号 / 系统调用细节 | 语言表节点 |
| 库专有 API 形态 | `df.groupby('k').sum()`、numpy 向量化 | **原生透传，必须显式标记**，报告标注"工具不做保证" |
| 跨语言语义归一 | "这段逻辑在 C 里怎么写" | **不做**；语义差异显式标注，不粉饰 |

**逃生舱规则（硬约束）**：原生透传必须写成显式形式（如 `原生 python "…"`、`原生 c "…"`），使"**未标记却无法解析**"能一律报错。

> 原则：**逃生舱一旦隐式，整层就都成了逃生舱。**

---

## 5. spec DSL 及其与代码的对应

spec DSL 是唯一真相源，也是代码的可读中间表示；它给 JevAgent 与通用 Agent 使用，人类不必常读。

### 5.1 结构

- **中文关键字**：第 4 节关键字核 + 各语言导入关键字。
- **目标语言语义**：类型名（`str`、`int`、`const char*`）、字面量（`True`、`false`、`""`）、库名（**照抄代码形态，不做中文化**）。
- **行尾节点注解**：每行末尾用行注释标注对应的目标语言节点路径（可选，生成时写入）。
- **来源标记行**：块首行可写 `# spec: <table_id>`（如 `# spec: python_v3`）确认表版本；**不写来源文件路径**。
- **语言特性显式标注**：语言特有的选择（如 Python 的 `len()` 判空 vs C 的 `'\0'` 检查）以注释标注原因。
- **保留块**：`names`（`declaration-only`，见 12.5）、`imports`（`hoisted`，见 3.6 与第 8 节）。

### 5.2 示例

**Python spec**：

```
# @jev-block:auth_001:begin
# spec: python_v3
定义 验证用户(用户名: str, 密码: str) -> bool:                # node:/python/function/define
    如果 用户名 == "":                                         # node:/python/control/if
        返回 False                                             # node:/python/function/return
    返回 检查密码(用户名, 密码)                                # node:/python/function/call
# @jev-block:auth_001:end
```

**C spec**（同一块，类型与字面量换成 C 形态，块首行改 `// spec: c_v1`）：

```
定义 验证用户(用户名: const char*, 密码: const char*) -> bool:    // node:/c/function/define
    // 特化：C 无字符串相等运算符，改用首字符判空
    如果 用户名[0] == '\0':                                        // node:/c/control/if
        返回 false                                                 // node:/c/function/return
```

### 5.3 与代码的对应

- 结构化行（`定义`、`如果`、`对于`、`当`）对应代码的声明 / 控制语句；表达式行对应代码的表达式。
- 行尾 `node:` 标注给出该行使用的目标语言节点路径，模板填充时读取该路径。
- `names` 块的条目**不产生代码行**，但决定类型、取地址符、格式符与路由挂载。
- `imports` 块的条目产生代码导入区（置顶、去重、与骨架合并）。

**分类标注（跨语言迁移用，由工具静态计算并写入报告）**：

| 分类 | 判定条件 | 迁移动作 |
|---|---|---|
| `verbatim` | 块内全部节点属核心核，且目标语言履约均为 `supported` | **逐字节复制**，零审阅、禁止重新生成 |
| `partial` | 含 `conditional` 节点 | 复制 + 标注需确认的前置条件 |
| `rewrite` | 含库节点 / `unsupported` 节点 | 必须重写；工具产出差异清单 |

### 5.4 双向可逆

- 正向：JevAgent 读 spec，按 `node:` 标注填模板，做闭包与骨架应用，产代码（`spec_to_code`）。
- 反向：JevAgent 读代码（由通用 Agent 先打分隔符），按表匹配节点，产 spec（`code_to_spec`）。

**必须成立的三条**：① `spec_to_code` **幂等**（连续运行两次产物字节一致，含导入区内容与位置）；② `code → spec → code` 往返中块外自由内容无损（含空行数量），块 ID 集合与顺序不变；③ `verbatim` 块跨语言复制后**逐字节一致**。往返测试纳入 `tests/roundtrip/`。

---

## 6. 工具接口

JevAgent 注册为通用 Agent 的工具集，接口统一返回结构化结果。

### 6.1 接口清单

| 工具名 | 状态 | 输入 | 输出 |
|---|---|---|---|
| `jev.split_blocks` | 保留 | 文件路径、文件类型 | `[{block_id, category, content, start, end}]` |
| `jev.spec_to_code` | 保留并增强 | 模块路径、目标语言、表引用 | 代码落盘路径 + 报告（含闭包 / 骨架 / 置顶记录） |
| `jev.code_to_spec` | 保留，**地位上升** | 模块路径（已含分隔符）、目标语言、表引用 | `spec.<lang>.dsl` + 报告（含自由区导入收纳记录） |
| `jev.translate_block` | 保留 | block_id、方向、上下文 | 单块翻译结果 + 置信度 + 质疑 |
| `jev.check_alignment` | 语义改为**二文件** | 模块路径 | `{aligned, issues}`（比较 spec ↔ code 块 ID 集合与顺序） |
| `jev.check_spec` | **新增（P4）** | 模块路径、目标语言、表引用 | 校验报告（error / warning / auto-corrected），**不生成代码** |
| `jev.check_tables` | **新增（P5）** | 表目录或表 ID 列表 | 履约完整性报告 + 「语言 × 核心节点覆盖率矩阵」 |
| `jev.spec_to_spec` | **新增（P3）** | 源模块路径、源语言、目标语言、表引用 | 目标 spec 落盘路径 + **迁移报告** |
| `jev.spec_export` | **新增（P3，可选）** | 模块路径、目标语言 | 剥离 `node:` 注解的只读可读稿（**禁止作为编辑入口**） |
| `rollback` / `list_tables` / `import_table` / `validate_vocab` / `jev_decision` / `get_config` / `set_config` | 不变 | 见各自 schema | 见各自 schema |

**退役**：两个涉及旧格式的动作从 `ACTIONS`、工具 schema `enum`、工具描述中移除（名称仅保留于 2.5 的一次性存量迁移说明）。

**`translate_block` 的 `direction` 枚举收窄为**：`spec_to_code` | `code_to_spec`。

### 6.2 请求 / 响应结构

**`jev.translate_block` 请求**：

```json
{
  "block_id": "auth_001", "direction": "spec_to_code",
  "module_path": "src/auth/auth", "target_lang": "python", "table_ref": "python_v3",
  "block_content": "...", "prev_block_tail": "...", "next_block_head": "...",
  "shared_symbols": ["用户名", "密码"],
  "names_env": {"库": ["math"], "变量": [{"name": "数据", "type": "list"}]},
  "manifest_id": "manifest_2026_09_30_001", "context_window_budget": 2048
}
```

**响应**：

```json
{
  "block_id": "auth_001", "direction": "spec_to_code", "output": "...",
  "path": ["/python", "/function", "/define"], "confidence": 0.94, "ambiguities": [],
  "symbols_used": ["用户名", "密码", "检查密码"], "symbols_defined": ["验证用户"],
  "dsl_normalization": {"input_nodes": 4, "normalized_nodes": 4, "unknown_nodes": [],
                        "auto_corrected": [], "description_deviations": []},
  "validation": {"ok": true, "errors": [], "warnings": [], "auto_corrected": [],
                 "coverage": {"rules_applied": ["ref_symbol", "ref_library", "import_closure"],
                              "unmodeled_libraries": ["numpy"]}}
}
```

**`jev.check_spec` 请求**：`{module_path, target_lang, table_ref, strict}`。响应：

```json
{
  "ok": false, "module_path": "src/auth/auth", "table_ref": "python_v3",
  "errors": [
    {"type": "undeclared_symbol", "block_id": "csum_001", "file": "auth.spec.c.dsl", "line": 12,
     "symbol": "上限", "message": "标识符 上限 未在 names 块声明", "nearest_candidates": ["上界", "上线"]},
    {"type": "missing_import", "block_id": "csum_001", "file": "auth.spec.c.dsl", "line": 15,
     "symbol": "printf", "message": "使用 printf 但缺少 <stdio.h>", "suggested_import": "引入系统 stdio.h"}
  ],
  "warnings": [{"type": "unmodeled_library", "library": "numpy", "message": "库未被建模，引用级校验不覆盖其签名"}],
  "auto_corrected": [{"block_id": "csum_001", "line": 9, "from": "print", "to": "printf", "rule": "confusions/c/correct"}],
  "coverage": {"rules_applied": ["unknown_node", "ref_symbol", "ref_library", "import_closure", "conditional_requires", "confusions"],
               "unmodeled_libraries": ["numpy"]}
}
```

**`jev.check_tables` 响应（覆盖率矩阵为正式交付物）**：`{ok, core_table, matrix:{columns, rows}, issues}`。

```json
{
  "ok": true, "core_table": "syntax_core_v1",
  "matrix": {"columns": ["python", "c", "shell"],
    "rows": [
      {"core_node": "/core/define",    "python": "supported", "c": "supported",   "shell": "conditional"},
      {"core_node": "/core/loop/for",  "python": "supported", "c": "conditional", "shell": "supported"},
      {"core_node": "/core/io/input",  "python": "supported", "c": "conditional", "shell": "supported"},
      {"core_node": "/core/io/output", "python": "supported", "c": "supported",   "shell": "supported"}]},
  "issues": [
    {"language": "c", "core_node": "/core/loop/for", "status": "conditional", "requires": ["集合带有已知长度绑定或哨兵"]},
    {"language": "shell", "core_node": "/core/define", "status": "conditional", "requires": ["函数体以闭合 } 收尾（OBS-08a）"]}]
}
```

**`jev.spec_to_spec` 响应（迁移报告，禁止静默降级）**：`{source, target, spec_path, blocks, unresolved}`，`blocks` 逐块给出分类与动作。

```json
{
  "source": {"module": "src/auth/auth", "lang": "python", "table_ref": "python_v3"},
  "target": {"module": "src/auth/auth", "lang": "c", "table_ref": "c_v1"},
  "spec_path": "src/auth/auth.spec.c.dsl",
  "blocks": [
    {"block_id": "auth_001", "class": "verbatim", "action": "copied", "bytes_copied": 214},
    {"block_id": "auth_002", "class": "partial", "action": "copied+requires", "requires": ["集合带有已知长度绑定或哨兵"]},
    {"block_id": "auth_003", "class": "rewrite", "action": "regenerated",
     "missing_nodes": ["/core/io/output"], "library_substitutions": [{"from": "numpy.mean", "suggested": "手写累加 + 除法"}],
     "lossy_points": ["pandas 链式调用 → 需手写循环"], "placeholder": "/* TODO(jev): 需人工处理，见迁移报告 */"}],
  "unresolved": ["auth_004"]
}
```

### 6.3 注册方式

| 框架 | 注册方式 |
|---|---|
| OpenAI Function Calling | 注册 JSON Schema 工具 |
| MCP | 暴露为 MCP Server：`mcp://jevagent/spec_to_code` 等 |
| LangChain / AutoGen | 提供 `BaseTool` 适配器 |
| 自研 | 提供 Python / TypeScript SDK |

### 6.4 禁止事项

- 禁止 JevAgent 调常规 LLM API；禁止通用 Agent 直接冒充 Jev 做最终 Choice；禁止 Jev 服务不可用时静默用通用 LLM 顶替；禁止两套密钥混用。
- 禁止在 `check_spec` 报 error 的情况下静默产出代码（须拒绝产出，或产出带显式错误标记的草稿）。
- 禁止未标记的原生透传（逃生舱必须显式且可 grep）。
- 禁止 `verbatim` 块被重新生成（必须逐字节复制）。

---

## 7. 两条主流程 + 一条辅助流程

### 7.1 编写流程（spec → code）

```
用户要求 → 通用 Agent 理解意图 → 选择目标语言 + 语言表
  → 通用 Agent 写 <module>.spec.<lang>.dsl（含块分隔符、names 块、imports 块），落盘
  → jev.check_spec(...)          ← 推荐预检；有 error 则修正 spec 后重试，不进入生成
  → jev.spec_to_code(...)        ← JevAgent：闭包推导 → 导入回写 spec(origin:auto) → 骨架应用
                                    → 导入区置顶去重 → 逐块模板填充 → 拼装代码，落盘
  → jev.check_alignment(...)     ← 二文件块 ID 集合与顺序
  → 通用 Agent 编译门槛验证（V1/V2/V3）+ Tier 1 确定性检查
  → 确认点提交（spec + code + 块索引 + manifest 一起入版本向量）
```

**关键点**：落盘分两步，每步产生一个可独立查看的文件（代码不手工改）；通用 Agent 只在第一步写内容，第二步由 JevAgent 生成，通用 Agent 只审不写；**工具负责生成，编译由通用 Agent 执行**（门槛见 13.1）；任何一步失败，回滚到该步之前的确认点。

### 7.2 转换流程（既有代码 → spec）

```
已有代码（无分隔符）
  → 通用 Agent 阅读代码 → 选择语言表
  → 通用 Agent 以注释形式插入块分隔符，落盘为 <module>.<ext>（此步需语义判断，Jev 不做）
  → jev.code_to_spec(...)        ← JevAgent：扫描自由区导入 → 收纳为 imports 块 → 逐块反译
                                    → 拼装 spec，落盘（首次导入时自动生成 names 块）
  → 通用 Agent 语义审（确认 spec 忠实于原代码意图）→ 确认点提交
```

**结果**：一份原本只有代码的模块变成二文件齐全、可被 JevAgent 按块接手的可编写状态。

**导入收纳细节**（逆向分支的前提）：

| 步骤 | 内容 |
|---|---|
| 1 | 扫描第一个 `@jev-block` 之前的自由区（C 还需扫 `#define` / `#include` 段） |
| 2 | 按语言正则匹配：Python `^import\s+(\S+)(?:\s+as\s+(\S+))?$` / `^from\s+(\S+)\s+import\s+(.+)$`；C `^#include\s+[<"]([^>"]+)[>"]$`；Shell `^(?:source\|\.)\s+(\S+)$` |
| 3 | 命中行从自由区摘除，物化为 `@jev-block:imports` 块（保持原顺序） |
| 4 | 反查 `required_imports`：命中 → `origin:auto`；否则 → `origin:declared` |
| 5 | 每行加 `# node:/<lang>/module/...` 注解 |

### 7.3 修改流程（按块，不整体重跑）

```
定位块（按 @jev-block:<id>）→ 修改 spec 中该块内容
  → jev.translate_block(block_id, "spec_to_code", context) → 只翻译并替换代码中对应块
  →（反向场景）改代码后 translate_block(block_id, "code_to_spec", context) → 只替换 spec 中对应块
  → 通用 Agent 审查该块 + 相邻块接口 → 确认点提交（只更新该块相关的版本向量）
```

**关键点**：**不整体重跑**，成本与块数无关、只与改动块数相关；二文件对应块靠 `block_id` 对齐；`names` 块变更或 `translate_block` 之后必须**重新挂载**符号宇宙（见 12.5）；若修改影响块的对外接口（签名、副作用），通用 Agent 负责检查相邻块的契约。

### 7.4 辅助流程：跨语言迁移（复制 + 定点处理）

跨语言不是"一源多目标"，而是**复制 + 定点处理**：

```
源语言模块（spec + code，已有）→ jev.spec_to_spec(module, src_lang, dst_lang, table_ref)
  → JevAgent 逐块分类 verbatim / partial / rewrite，产出迁移报告与目标 spec
  → verbatim 块：逐字节复制，零审阅、禁止重新生成
    partial 块：复制 + 处理报告标注的前置条件
    rewrite 块：仅对这些块调用生成能力
  → jev.spec_to_code(目标 spec) → 目标语言代码 → 编译门槛验证 + 语义审 → 确认点提交
```

**给通用 Agent 的操作约定**（同时写入注入的系统提示词指导）：

```
跨语言迁移时：① 先取迁移报告中的块级分类；② verbatim 块原样复制，不要重新生成；
③ partial 块复制后处理标注的前置条件；④ 仅对 rewrite 块调用生成能力。
```

**理由**：复制零幻觉（逐字节搬运，不经过模型生成），重新生成才是模型出错的地方；最小改动面本身就是最低幻觉面。

---

## 8. 块拆分、库导入层与上下文传递

### 8.1 拆分由 JevAgent 的 BlockSplitter 完成

`BlockSplitter` 是 JevAgent 的模块，不是 Jev 模型，只做机械拆分：扫描分隔符标记；提取块 ID、类别（`emitting` / `declaration-only` / `hoisted`）、内容、起止位置；识别并解析保留块 `names` 与 `imports`；保留块间自由内容（含空行数量）；嵌套块按层级组织；拼装时执行置顶与合并（spec 与 code 一致执行）。

### 8.2 库导入层

**三类导入问题**：

| 类别 | 例子 | 谁负责 | 机制 |
|---|---|---|---|
| **A. 隐含必需导入** | C 用 `printf` → 必须 `#include <stdio.h>` | **工具自动推导（闭包保证）** | 语言表 `required_imports` 白名单 |
| **B. 显式库依赖** | `math`、`numpy`、`stdio.h` | 作者在 `imports` 块声明，工具生成正确语法并置顶 | `引入` 系列关键字 |
| **C. 库引入的可选语法** | numpy 向量化、pandas 链式调用 | 工具 idiom 表 + 显式原生透传 + 决策兜底 | 报告标注"不做保证" |

**"必选项"原则**：A 类必须由工具**闭包保证** —— 只要代码引用了符号，对应导入就必须出现，不允许依赖作者记性。

**闭包算法（在 `spec_to_code` 中执行）**：

```
输入：spec 各块内容、目标语言表 T、作者显式导入集 E（imports 块 + names 块）
1. S := 对所有块执行 SymbolTable.extractSymbols(..., referenced)
       扫描前剔除注释（# / // / --）与字符串字面量，剔除语言关键字与内建类型（keyword_blacklist）
2. D := { T.required_imports[s] | s ∈ S 且命中白名单 }
3. R := 合并(E, D)，按规范化 key 去重：key = (kind, module|header, alias, sorted(names))
4. 若任一 s 的解析结果为 kind:"unsupported" → 抛硬错误（禁止静默丢弃）
5. 排序：显式声明保持声明顺序在前；自动推导按字典序在后
6. 产出导入区内容
7. 回写 spec 的 imports 块（自动项标 origin:auto），保持 SSOT 完整
8. 生成代码：骨架导入 ∪ 导入区，同一次去重合并
```

> 第 7 步是关键：闭包结果**回写到 spec**，使 spec 始终是完整真相源，且二文件对齐检查不会因"code 多出几行导入"而失衡。

**`origin` 标记**：

| 值 | 含义 | 逆向行为 |
|---|---|---|
| `declared`（默认） | 作者声明的依赖 | 正常回译 `引入 …` |
| `auto` | 工具闭包推导 | `code_to_spec` **不产生新的 spec 行**（已在 spec 中，仅更新标记）；不得被当作作者意图 |

**闭包输入升级**：`names` 块的 `库` 条目（如 `库 numpy 作为 np`）使闭包从"白名单猜"升级为"声明即知"；语言表 `required_imports` 退化为**兜底下限**（处理 `printf`、`len` 这类标准库符号）。仅副作用导入（如 `import matplotlib.pyplot`）才需显式 `引入`。

**骨架层必须真正生效**：`spec_to_code` 读取语言表的 `skeleton_ref` 并**实际应用**，在 manifest 中写入 `skeleton_applied: true`（见第 11 节）。

| 语言 | 骨架内容 |
|---|---|
| C | 头部注释 + 基础 `#include` + 可选 `main()` 框架 + 大括号收尾 |
| Python | 可选 shebang / 编码声明 / `if __name__ == "__main__":` 框架 |
| Shell | shebang + `set -euo pipefail` + 闭合符号 |

骨架的固定导入与闭包导入在导入区做**同一次去重合并**。

**生成完整性配套修复**：

| 编号 | 问题 | 修复 |
|---|---|---|
| OBS-07a | C 缺 `#include` → 编译失败 | 闭包 + 骨架 |
| OBS-07b | `printf("%s\n", 整数表达式)` 是 UB | `输出(表达式)` 由工具按 `names` 类型或字面量解析格式符 |
| OBS-08a/b/c/d | shell 缺 `}`/`done`/`fi`；`设` 未翻译；条件未转换；缺 `/shell/function/call` | 补收尾符号、补 `设` 翻译、`core_operators` 转换、补齐节点 |

**格式符规则**：作者侧统一写单一关键字 `输出(表达式)`，不问类型；工具依 `names` 表类型（或字面量推断）解析格式符（整数 → `%d`，字符串 → `%s`）；类型未知时报错要求补类型声明，或退到显式 `输出文本` / `输出整数`（**降级为逃生舱，不再是常态**）。

### 8.3 上下文打包

Jev 上下文窗口有限，块不能太大，但翻译时需要相邻上下文，`ContextPacker` 负责打包（字段与 6.2 的 `translate_block` 请求一致）：`block_content`、`prev_block_tail` / `next_block_head`、`shared_symbols`、`names_env`、`manifest`、`direction`、`target_table`。

- `prev_block_tail` / `next_block_head`：只取摘要（函数签名、前 3 行、后 3 行），避免爆窗。
- `shared_symbols` / `names_env`：符号表快照，保证跨块命名一致；类型信息支撑格式符与取地址符生成。
- 块大小约束沿用设计稿：≤ Jev 上下文窗口的 50%（建议 8k–16k token 窗口下取 4k–8k）。

### 8.4 拼装

按原顺序拼回：块内容替换；块间自由内容保留（含空行）；分隔符标记保留（不被翻译吞掉）；`imports` 块提到首位，`names` 块不出现在代码侧；骨架内容与导入区合并后写入。

---

## 9. 表选择与方向控制

**选择用哪张表、往哪个语言生成，由通用 Agent 把关**（通用 Agent 更能理解用户意图），JevAgent 只按指定的表执行。

### 9.1 选表输入

- 用户意图描述；目标运行环境（编译 / 解释 / 执行）。
- 现有代码库的语言分布；性能 / 可维护性 / 生态约束。
- **目标语言对通用关键字核的履约情况**（`unsupported` 的核心节点意味着该语言不能承接对应写法）。

### 9.2 多语言产出

若一个模块需同时产出多语言，逐个指定，各自维护一组二文件：

```
auth.spec.python.dsl → (python_v3) → auth.py
auth.spec.c.dsl      → (c_v1)      → auth.c
```

跨语言迁移走 `spec_to_spec` + 迁移报告（7.4），**不做静默转换**。

### 9.3 表版本绑定

表版本写入 manifest（第 11 节）。表升级时需重新翻译受影响的块（走修改流程）。

### 9.4 核心表与语言表的选择关系

```
syntax_core_v1.json（语言无关，闭集）
  ├── core_nodes       中文关键字 canonical + aliases
  └── core_operators   运算符表达 → 各语言写法
        ↓ 各语言表声明 core_conformance（履约映射）
  {core_node → {status: supported | conditional(requires) | unsupported(reason), node: /lang/...}}
        ↓
  python_v3.json / c_v1.json / shell_v2.json
```

**路由两跳**：`中文关键字` → `inferSemanticNode` → `semantic_mappings`（`/semantic/module/*` 为内部中间层）→ `/{lang}/*` 节点 → 模板填充。

**三档履约状态与工具行为**：

| 状态 | 含义 | 工具行为 |
|---|---|---|
| `supported` | 无条件可生成 | 直接生成 |
| `conditional` | 有前置条件 | **由防火墙校验前置**；不满足 → 硬错误 `core_unfulfilled` 并指出缺什么 |
| `unsupported` | 目标语言无对应物 | 硬错误 `unsupported_core` + 替代建议，**禁止静默丢弃** |

**一个诚实的例子**：`对于 x 中的 数据:`（遍历集合）在 Python 直接成立，在 C 里**存在真实语义缺口** —— C 遍历数组需要长度或哨兵，仅凭"数据"这个名字推不出 `n`，因此只能标 `conditional`，前置条件为"集合带已知长度绑定"，由 `names` 表（`变量 数据: list` + `常量 长度`）或防火墙检查来满足。

**一致性校验不能只靠约定**（已有三处漂移实测证据：`c_v1` 曾缺 for/while 节点、`shell_v2` 缺 `function/call`、`KEYWORD_MAP` 与语言表构成双真相源）：`check_tables` 对每个语言表逐核心节点校验履约声明，缺声明即报错；`unsupported` 必须附 `reason`；`conditional` 必须附 `requires`；`normalize.js` 的 `KEYWORD_MAP` 由 `syntax_core_v1.json` 驱动。

### 9.5 方向控制

| 方向 | 动作 | 触发 |
|---|---|---|
| `spec_to_code` | spec → 代码 | 编写流程、修改流程 |
| `code_to_spec` | 代码 → spec | 转换流程、修改流程 |
| 跨语言 | `spec_to_spec`（源 spec → 目标 spec）+ 迁移报告 | 辅助流程 |

---

## 10. 落盘、命名、目录结构

### 10.1 命名规范

```
<module>.spec.<lang>.dsl             唯一真相源（语言绑定）
<module>.<ext>                       代码
```

`<module>`：模块名，小写下划线，与代码内模块名一致；`<lang>`：语言标识，如 `python` / `c` / `shell` / `js` / `go`；`<ext>`：语言标准扩展名，如 `.py` / `.c` / `.sh` / `.js` / `.go`。

### 10.2 目录结构

```
project/
├── manifest.json / blocks_index.json      # 版本绑定；块 ID ↔ 二文件映射、块类别、依赖、状态
├── src/auth/   auth.spec.python.dsl · auth.py · auth.spec.c.dsl · auth.c
├── src/utils/  utils.spec.python.dsl · utils.py
├── tables/     syntax_core_v1.json（通用关键字核：core_nodes + core_operators，闭集）
│               skeleton_v1.json（各语言骨架，必须被实际应用）
│               semantic_v1.json（内部路由中间层）
│               python_v3.json · c_v1.json · shell_v2.json
├── vocab/      common.json · python.json · dialog.json
├── dsl/        parser.py · emitter.py · roundtrip_test.py
└── .jev/       cache/ · audit/
```

### 10.3 blocks_index.json

```json
{
  "module": "auth",
  "blocks": [
    {"block_id": "names", "category": "declaration-only", "status": "confirmed",
     "files": {"spec": {"python": "src/auth/auth.spec.python.dsl"}}},
    {"block_id": "imports", "category": "hoisted", "status": "confirmed",
     "files": {"spec": {"python": "src/auth/auth.spec.python.dsl", "c": "src/auth/auth.spec.c.dsl"},
               "code": {"python": "src/auth/auth.py", "c": "src/auth/auth.c"}}},
    {"block_id": "auth_001", "category": "emitting", "status": "confirmed", "migration_class": "verbatim",
     "files": {"spec": {"python": "src/auth/auth.spec.python.dsl", "c": "src/auth/auth.spec.c.dsl"},
               "code": {"python": "src/auth/auth.py", "c": "src/auth/auth.c"}},
     "symbols_defined": ["验证用户"], "symbols_used": ["检查密码"]},
    {"block_id": "auth_002", "category": "emitting", "files": {"...": "..."}, "status": "confirmed"}
  ]
}
```

`status` 取值：`draft` / `translated` / `confirmed` / `rolled_back`。`migration_class` 取值：`verbatim` / `partial` / `rewrite`（跨语言迁移用，可缺省）。

---

## 11. Manifest 与版本绑定

```json
{
  "manifest_id": "manifest_2026_09_30_001", "model": "two_file_v3",
  "syntax_core": "syntax_core_v1", "semantic": "semantic_v1",
  "skeleton": "common_skeleton_v1", "skeleton_applied": true,
  "tables": {"python": "python_v3", "c": "c_v1", "shell": "shell_v2"},
  "required_imports_version": {"python": "python_v3/required_imports@1", "c": "c_v1/required_imports@1", "shell": "shell_v2/required_imports@1"},
  "core_conformance_version": {"python": "python_v3/core_conformance@1", "c": "c_v1/core_conformance@1", "shell": "shell_v2/core_conformance@1"},
  "vocab": "common_v3", "mappings": {"python": "python_v3_semantic", "c": "c_v1_semantic"},
  "symbol_snapshot": "sym_001", "names_snapshot": "names_001",
  "code_commit": "git_abc", "spec_commit": "git_def",
  "jev_model": "jev-4b-v1", "jevagent_version": "3.0.0"
}
```

| 字段 | 含义 |
|---|---|
| `model` | 模型代际标识 `two_file_v3`；旧格式描述已移除 |
| `skeleton_applied` | **骨架实际生效标记**：为 true 才表示 `skeleton_ref` 参与了生成（此前只写进 manifest、从未被消费） |
| `required_imports_version` | 闭包推导依据的导入白名单版本；升级即缓存失效 |
| `core_conformance_version` | 语言表履约声明版本，`check_tables` 的校验对象 |
| `names_snapshot` | `names` 块快照（符号宇宙挂载的输入） |

### 11.1 缓存键

`cache_key = hash(manifest_id + block_id + direction + block_content_hash + target_table + syntax_core_version + required_imports_version + symbol_env_snapshot + names_snapshot + candidate_vocab_version)`；版本变化 → 缓存失效。

### 11.2 确认点版本向量

每个确认点绑定：二文件对应块的内容哈希；块 ID 与块类别；manifest_id（含 `syntax_core` / `skeleton_applied` / `required_imports_version`）；符号表快照与 `names` 快照；动态节点集合（若该块涉及运行期）；审查状态。回滚时按版本向量恢复二文件对应块 + 符号表 + `names` 挂载 + 动态节点 + 缓存键。

---

## 12. 错误处理与质疑

### 12.1 错误清单

| 错误 | 处理 |
|---|---|
| Jev API 超时 / 5xx | 重试 2 次，指数退避；仍失败 → `jev_unavailable`，阻塞 |
| Jev API 限流 | 退避 + 队列；不可逆操作阻塞 |
| Jev 返回 schema 错 / 模型版本不匹配 | 标记 `jev_schema_invalid` 不采信 / 拒绝并要求切换 manifest |
| `unknown_node` | **硬错误**（未识别即错误，附最近候选建议）；不得静默走 raw |
| `undeclared_symbol` | 硬错误；引用的标识符未在 `names` 块声明 |
| `missing_import` | 硬错误；给出应补的导入语句 |
| `core_unfulfilled` | 硬错误；`conditional` 节点前置条件不满足，说明缺什么 |
| `unsupported_core` | 硬错误；目标语言无该核心节点，给替代建议，禁止静默丢弃 |
| `no_mapping` / `guard_failed` | 查 `raw_fallback`；**仅当原生透传被显式标记**才允许，否则质疑 |
| `vocab_invalid` | 拒绝合并，可部分合并，严重人工介入 |
| `table_drift` | `check_tables` 检出语言表缺核心节点或履约声明不完整 → 阻塞 |
| `malformed_block` / `invalid_nesting` | 分隔符未闭合 / 嵌套非法，阻塞 |
| `duplicate_block_id` / `block_mismatch` | 块 ID 冲突 / 二文件块 ID 不对齐，阻塞 |
| 常规 LLM 失败 | 通用 Agent 自身降级策略；Jev 不顶替 |

### 12.2 重试原则

- Choice / Score / Noul 幂等，可重试；不可逆操作审查失败 → 回滚最近确认点；边界模糊默认阻塞。
- `check_spec` 与 `spec_to_code` **共用同一套规则实现**，避免"预检通过、生成被拦"的不一致。

### 12.3 质疑格式

沿用设计稿第 10.2 节结构，新增字段：

```json
{
  "ambiguity_type": "undeclared_symbol",
  "block_id": "csum_001", "file": "auth.spec.c.dsl", "line": 15,
  "description": "标识符 上限 未在 names 块声明",
  "candidates": ["上界", "上线"],
  "nearest_rule": "编辑距离仅用于给建议，不自动采用",
  "blocking": true
}
```

另一例：`{"ambiguity_type": "malformed_block", "block_id": "auth_001", "file": "auth.spec.python.dsl", "line": 12, "description": "块 auth_001 缺少 end 标记", "blocking": true}`。

### 12.4 校验防火墙的能力边界（必须写入 README）

> **它守的是引用合法性，不是逻辑正确性。**

| ✅ 能拦（符号级 / 引用级） | ❌ 拦不住（语义级） |
|---|---|
| 引用未声明的库；使用未声明的变量 | 算法写错、边界条件错、off-by-one |
| 跨语言写法混入（C 里 `print`、Python 里 `printf`）；常量 / 关键字拼写偏差 | `/` 与 `//` 用错但语法合法；API 参数顺序对但含义错 |
| 调用不存在的本地函数；目标语言无对应物的库（numpy 出现在 C） | 库特定 idiom 的深层误用；业务逻辑理解错 |
| 必需导入缺失（`printf` 无 `<stdio.h>`）；`conditional` 前置不满足 | — |

**三条护栏**：① **覆盖率如实标注** —— 报告必须写明本次校验覆盖了哪些规则、哪些库未建模，**符号级通过 ≠ 逻辑正确**；② **不得静默通过** —— 任何自动纠偏、任何原生透传，都必须在报告中可见；③ **不取代编译与用例测试** —— 本层只做**生成前的引用合法性拦截**，`gcc -Wall` / `py_compile` / `bash -n` 与用例测试仍由通用 Agent 执行。

### 12.5 `names` 块：符号宇宙

置于语义文件开头，用**保留块**（`declaration-only`，不产出代码、不参与对齐）：

```
# @jev-block:names:begin
库 math
库 numpy 作为 np
变量 数据: list
变量 结果: int
常量 上限 = 100
函数 累加(上限: int) -> int
# @jev-block:names:end
```

| 条目类型 | 语法 | 用途 |
|---|---|---|
| `库` | `库 <module> [作为 <alias>]` | 外部模块绑定 → **导入闭包输入**；路由挂载 |
| `变量` | `变量 <name>[: <type>]` | 本地变量；C 侧类型因此**确定而非推断** |
| `常量` | `常量 <name> = <value>` | 常量；可参与字面量校验 |
| `函数`（可选） | `函数 <name>(<params>) -> <ret>` | 本地函数签名；支撑参数个数 / 类型校验 |

**它顺带解决的三件事**：① **导入闭包从"白名单猜"升级为"声明即知"** —— `库 numpy 作为 np` 使工具知道 `np.array(...)` 需要 `import numpy as np`，作者不必再写 `引入 numpy 作为 np`；② **C 的类型从"推断"变"声明"**，格式符与取地址符可正确生成；③ **路由挂载** —— `np.array(...)` 判为库调用，注解 `/python/lib/numpy/array` 而非 `/python/raw`。

**挂载机制（必须严格实现）**：

| 要点 | 要求 |
|---|---|
| 作用域 | **按模块挂载**，禁止全局泄漏（否则路由结果依赖加载顺序，丧失可复现性） |
| 确定性 | 挂载必须是"文件内容的纯函数"：同输入同结果，**可单测** |
| 失效 | `names` 块变更、`translate_block` 之后必须**重新挂载** |
| 冲突校验 | 名字与语法关键字 / 保留字冲突 → 报错；同名不同 kind → 报错 |

**作者负担的解法**：`code_to_spec` 已在遍历代码，令其**首次导入时自动生成 `names` 块**，之后由作者增删。既有代码零成本进入该模型，且名字表从第一天起就准确。

### 12.6 四条关键机制

**机制 1：闭集 + 未知即错误（最重要）** —— 未识别 → 硬错误（附最近候选建议）；编辑距离**只用于给建议，绝不自动采用**；默认行为必须从"静默落到 `/{lang}/raw`"反过来。

**机制 2：逃生舱必须显式且可 grep** —— 原生透传必须显式标记（如 `原生 python "..."`），使"**未标记却无法解析**"能一律报错。灵活性 vs 可验证性的真实张力：只要 Agent 能随手写任意原生行，防火墙就形同虚设。

**机制 3：`confusions` 跨语言误写对照表（闭集）** —— 只收录确定的一对一关系：

```json
"confusions": {
  "c": [{"wrong": "print", "right": "/c/io/output", "action": "correct"},
        {"wrong": "len", "right": null, "action": "error", "hint": "C 无 len，请用 sizeof 或显式长度"}],
  "python": [{"wrong": "printf", "right": "/python/io/output", "action": "correct"}]
}
```

**自动纠偏授权 = 档 B（有限自动）**：仅 `confusions` 表中 `action: correct` 的条目自动改，其余一律报错；一切纠偏必须在报告中可见（`auto_corrected` 字段）。未识别即按最近候选自动改（档 C）危险，等于把语法决定权交给相似度。

**机制 4：先校验、后生成；且可独立调用** —— `spec_to_code` 内部：校验 → 有 error 则**拒绝产出**（或产出带显式错误标记，**禁止静默降级**）；独立 action `check_spec` 供 Agent 不生成即预检，也便于进 CI；两者复用**同一套规则实现**。

---

## 13. 与审查层集成

### 13.1 分层策略

| Tier | 内容 | 触发 |
|---|---|---|
| Tier 0 | JevAgent 置信度 | 高置信 + 可逆 → 直接过 |
| Tier 1 | 确定性检查（**编译门槛 V1/V2/V3** / lint / 分隔符校验 / 块对齐 / `check_spec` / `check_tables`） | 永远开 |
| Tier 2 | 通用 Agent 语义审 | 中低置信 / 不可逆 / 跨语言 |
| Tier 3 | 人类仲裁 | Tier 2 分歧 |

**Tier 1 中的编译门槛（每期必须全绿）**。工具负责生成，**编译由通用 Agent 执行**：

```powershell
& $gcc -Wall -Wextra -c out.c -o out.o      # GCC 14.2.0，退出码必须为 0
& $py  -m py_compile out.py                 # Python 3.12+，退出码必须为 0
& $bash -n out.sh                           # bash 5.2.37，退出码必须为 0
```

| # | 门槛 | 重构前实测状态 | 重构后要求 |
|---|---|---|---|
| V1 | C 产物 `gcc -Wall -Wextra -c` | ❌ 失败：`implicit declaration of 'printf'` | ✅ 必须通过，且 `-Wformat` 无警告 |
| V2 | Python 产物 `py_compile` | ✅ 通过 | ✅ 必须保持 |
| V3 | Shell 产物 `bash -n` | ❌ 失败：`syntax error: unexpected end of file` | ✅ 必须通过 |

### 13.2 阻塞规则

**生成二文件** → 可逆，非阻塞，异步审；**执行代码 / 写文件 / 网络请求 / 数据库修改** → 不可逆，阻塞。

### 13.3 审查粒度

- **块级**：一个块审一次。
- **二文件对齐审**：确认 spec 与 code 中 `emitting` / `hoisted` 块的 ID 集合与顺序一致，`declaration-only` 块按类别跳过。
- **语义审**：通用 Agent 读 spec + 代码，确认语义等价。
- **合法性审**：`check_spec` 报告（引用合法性、闭包完整性、纠偏可见性）。
- **表完整性审**：`check_tables` 的覆盖率矩阵。

### 13.4 回滚

回滚到最近确认点，恢复：二文件对应块；符号表快照与 `names` 挂载；动态节点；块间契约；缓存键；审查状态。已发布词表 / 路由表 / 核心表版本不回滚，只切换引用。

---

## 14. 部署形态

### 14.1 开发环境

```
本地通用 Agent 进程 → JevAgent SDK → 本地 Jev Runtime → Ollama / llama.cpp / vLLM → jev-4b
```

### 14.2 生产环境

```
通用 Agent 集群 → JevAgent Service（HTTP / gRPC / MCP）→ Jev Runtime 集群 → 内网 4B Jev 模型
```

### 14.3 双 API 配置

```yaml
orchestrator:
  llm:   { provider: openai_compatible, base_url: ${AGENT_API_BASE_URL}, api_key: ${AGENT_API_KEY},
           model: ${AGENT_MODEL}, timeout_s: 120 }
jev:
  runtime: { provider: native_jev, base_url: ${JEV_API_BASE_URL}, api_key: ${JEV_API_KEY},
             model: ${JEV_MODEL}, timeout_s: 120 }   # 冷启动实测约 97s、热态 37~58.5s，不得低于 120
  agent:   { mode: embedded, manifest_path: ./manifest.json, tables_dir: ./tables,
             vocab_dir: ./vocab, cache_dir: ./.jev/cache }   # mode: embedded | sidecar | remote
```

两套密钥必须来自不同 secret scope，不落盘、不进日志、不进 prompt。

### 14.4 配置隔离约束

- **测试必须隔离配置路径**：支持注入配置路径或识别 `JEV_CONFIG_FILE` 环境变量，测试一律写临时目录；任何调用 `set_config` 的测试都不得改写生产配置（`~/.dsh/jevagent.json`）。
- 密钥收敛到单点存储 `~/.dsh/jevagent.json`；`cordis.patch.yml` 等补丁层不得承载密钥；配置合并顺序为 `{ ...config, ...persisted }`。
- `set_config` 必须拒绝掩码回写（含 `***` 的值一律拒绝）；写盘建议原子化（先写临时文件再 rename）。
- **离线可用**：`jev_enabled: false` 时 0 次网络请求。

---

## 15. 测试与验收

### 15.1 测试层级

| 层级 | 内容 |
|---|---|
| 单元测试 | 分隔符拆分 / 拼装（含空行无损）、块 ID 校验、块类别跳过逻辑、路由、模板、符号表、关键字归一、词表验证 |
| 防火墙测试 | 每条拦截规则一条用例：`unknown_node` / `undeclared_symbol` / `missing_import` / `core_unfulfilled` / `unsupported_core`；纠偏可见性；覆盖率字段存在性 |
| 契约与集成测试 | Jev Runtime API schema、双 API mock、通用 Agent → JevAgent → Jev Runtime |
| 二文件对齐测试 | spec 与 code 中 `emitting` / `hoisted` 块 ID 集合与顺序一致；`declaration-only` 块按类别跳过 |
| 往返测试 | spec ↔ code（含幂等）、`code → spec → code` 导入内容与位置幂等 |
| 导入闭包测试 | 三类导入（隐含必需 / 显式声明 / 原生透传）；置顶、去重、`origin` 标记正确 |
| 覆盖率矩阵测试 | 三语言表对全部核心节点有履约声明；`unsupported` 附理由；人为制造漂移能被 `check_tables` 检出 |
| 黄金样例 | 跨语言验证：同一算法 → C / Python / Shell → 执行结果比对 |
| 编译门槛测试 | V1 `gcc -Wall -Wextra -c`、V2 `py_compile`、V3 `bash -n`，三语言全部通过 |
| 回归测试 | 词表 / 表 / 核心表变更后黄金样例不回归；308 组排序用例不破 |
| 混沌测试 | Jev 宕机、超时、限流、版本不匹配 |
| 安全测试 | AST、白名单、沙箱、密钥隔离、配置路径隔离 |

### 15.2 最小验收标准

1. **能配置两套 API**（常规 LLM + Jev），**能注册工具到现有 Agent**，且工具 schema 中不再出现旧格式动作；`jev_enabled: false` 时 0 次网络请求。
2. **三条流程全部跑通**：编写流程（写 `spec.<lang>.dsl` → `check_spec` → `spec_to_code` → 二文件落盘）；转换流程（给既有代码打分隔符 → `code_to_spec` → spec 落盘，含自由区导入收纳为 `imports` 块、自动生成 `names` 块）；修改流程（改一个块 → 只翻译一个块 → 二文件该块同步更新，其余块字节不变）。
3. **编译三门槛全绿**：C 过 `gcc -Wall -Wextra -c`（`-Wformat` 无警告）、Python 过 `py_compile`、Shell 过 `bash -n`。
4. **导入闭包成立**：`printf` 自动带 `<stdio.h>`；`引入 math` 在 Python 侧位于首个非注释行之前；同一依赖声明两次只生成一条；显式与自动重复合并为一条并标 `origin:declared`；`spec_to_code` 幂等（连续两次字节一致）。
5. **覆盖率矩阵通过**：三语言表对全部核心节点有履约声明；`unsupported` 附理由；`conditional` 前置不满足时硬错误并说明缺什么。
6. **跨语言一致性**：同一算法在 Python 与 C 的 spec 中，核心节点部分逐行相同（`diff` 验证，差异仅出现在库与类型处）；**`verbatim` 块逐字节复制**，未被重新生成。
7. **`check_spec` 与 `spec_to_code` 判定一致**（同一规则实现）。
8. **防火墙生效**：未声明库 / 未声明变量 / 跨语言误写 / 缺失必需导入在生成前被拦下；未标记却无法解析的行报错；纠偏在报告中可见；报告含覆盖率字段（规则清单 + 未建模库清单）。
9. **能处理** `unknown_node`、`no_mapping`、`vocab_invalid`、`malformed_block`、`undeclared_symbol`、`missing_import`、`core_unfulfilled`、`unsupported_core`；**能回滚到最近确认点**；块隔离成立（`translate_block` 仅改动目标块字节范围）。
10. **配置隔离**：全套测试运行前后，生产配置 `~/.dsh/jevagent.json` 哈希不变。
11. **Jev 不可用时不静默用通用 LLM 顶替**；最终代码能被目标语言编译器 / 解释器正常解析（分隔符不破坏语法）。

---

## 16. 实现路线图

期序对齐重构方案的 P0~P5；**编译门槛 V1/V2/V3 每期必须全绿**。

### P0：移除旧格式 + 二文件模型打通 + 骨架落地 + C 闭包导入

- 移除退役动作（`ACTIONS`、schema `enum`、工具描述同步）；重写注入的系统提示词指导。
- `three-file.js` 路径解析去旧格式字段；`checkAlignment` 改二文件；`updateBlocksIndex` / `updateManifest` schema 调整。
- **块类别落地**（`emitting` / `declaration-only` / `hoisted`）—— 必须先于 `names` 块。
- `skeleton_ref` **实际应用**；`skeleton_v1.json` 补齐 C / Python / Shell 骨架；manifest 写 `skeleton_applied`。
- `required_imports` 闭包 + 导入区置顶去重 + 回写 spec（`origin:auto`）；C 侧 `输出(表达式)` 格式符按类型解析（修 OBS-07b）。
- 存量一次性迁移（2.5），迁移后删除旧格式文件。
- **交付物**：工具不再有退役动作；**生成的 C 无需手工补丁即可编译**（V1 通过）。
- **验收**：V1 通过且 `-Wformat` 无警告；Python 产物与既有基线逐行一致；308 组排序用例全通过。

### P1：正向导入分支

- spec 导入语法与三语言 import 节点；`placement: "imports"` 置顶、去重、排序；`origin` 标记；`semantic_v1` 新增 `/semantic/module/import`、`/semantic/module/import/local`。
- `tryApplyNodeTemplate` 泛化（按 `spec_template` / `template` 通用填充），修 BUG-07。
- **验收**：`引入 math` → Python `import math` 且在首个非注释行之前；`引入系统 stdio.h` → C `#include <stdio.h>`；重复声明只出一条；显式与自动重复合并标 `origin:declared`；`spec_to_code` 幂等。

### P2：逆向分支

- 自由区导入收纳为 `imports` 块（识别正则、反查 `required_imports`、加注解）；`code_to_spec` 反解导入并自动生成 `names` 块。
- `symbol-table.js` 加厚（完整标识符扫描 + 注释 / 字符串剔除 + `keyword_blacklist` + `referenced` 字段）。
- **验收**：手写 `import os` / `#include <stdio.h>` 的代码被正确收纳与注解；`origin:auto` 不产生新的作者声明行；往返导入内容与位置幂等。

### P3：生成完整性补全 + 跨语言 + 只读导出

- shell 路径修复（OBS-08a/b/c/d：闭合符号、`设` 翻译、条件转换、补 `/shell/function/call`）。
- `spec_to_spec` + 迁移报告（`verbatim` / `partial` / `rewrite` 分类）；`spec_export`（剥离注解的只读导出，禁止作为编辑入口）。
- **验收**：shell 产物通过 `bash -n`；跨语言转换产出带风险披露的报告；占位块显式 TODO，无静默降级。

### P4：语言绑定容错层与校验防火墙

- `check_spec` action；`spec_to_code` 内接入校验闸门（校验 → 有 error 拒绝产出）；未识别 → 硬错误（含最近候选建议）。
- `confusions` 查表与档 B 自动纠偏；`names` 块解析与**按模块挂载**（纯函数、禁止全局泄漏、变更后重新挂载、冲突校验）。
- `lib/validator.js`（新增）：规则引擎（引用合法性、闭包完整性、类型 / 签名（可选）、纠偏），输出结构化报告。
- 语言表新增 `aliases`（容错别名集）、`keyword_blacklist`、`confusions`。
- **验收**：未声明库 / 变量 → 硬错误且报告含行号、块 ID、最近候选；C 模块写 `print` → 自动纠偏并可见；未标记却无法解析的行报错、不得静默走 raw；必需导入缺失 → 报错并给应补导入；`check_spec` 与 `spec_to_code` 判定一致；报告含覆盖率字段；拦截对照表中标记 ✅ 的 7 项各有用例并通过。

### P5：通用关键字核与跨语言一致性

- `tables/syntax_core_v1.json`（`core_nodes` + `core_operators`，闭集）；三张语言表新增 `core_conformance`；补齐缺失的核心节点（含 `/core/io/input`）。
- `check_tables` action；**覆盖率矩阵为正式交付物**（同时是给开发者的上手说明书）。
- `core_operators` 参与表达式转换（shell `<=` → `-le` 等）；`KEYWORD_MAP` 由核心表驱动；核心节点优先解析，`conditional` 的 `requires` 交由校验层处理。
- **建议与 P0 同步建立、最迟不晚于 P1**（P1 要改三张语言表，先有 `check_tables` 才能防止边改边漂）。
- **验收**：覆盖率矩阵校验通过；C 侧 `对于` 标 `conditional`，未提供长度绑定时硬错误、提供后生成正确循环；shell 侧 `当 i <= 上限` 生成 `while [ "$i" -le "$上限" ]; do` 且 `bash -n` 通过；同一算法在 Python 与 C 的 spec 中核心节点部分逐行相同；`verbatim` 块跨语言复制逐字节一致；`check_tables` 能检出人为制造的漂移。

### 横切项（随 P0 一并处理）

- ISSUE-03：多端点错误聚合后再抛（避免超时被 404 掩盖）；超时上限提升至 120~180s（冷启动实测约 97s）。
- 端到端测试补编译门槛断言（V1/V2/V3）；测试隔离配置路径（`JEV_CONFIG_FILE`）。
- 词表工厂流程保留：候选词表生成（通用 Agent）→ 词表语法验证（JevAgent）→ 冲突检查 / 回归测试 / 版本化。

---

## 17. 与设计稿 V2.0 的关系

本稿不修改设计稿 V2.0 的任何冻结结论，只在其下补全工程落地。

| 设计稿条目 | 本稿对应 |
|---|---|
| 3.1 总览图 | 第 1 节：JevAgent 降为工具 |
| 6.2 处理流程 | 第 7 节：两条主流程 + 一条辅助流程重写 |
| 11.4 调用协议 | 第 6 节：工具接口重写（退役 / 增强 / 新增） |
| 15.2 DSL 语法 | 第 4 节：spec DSL 语法（通用关键字核驱动） |
| 18.1 manifest | 第 11 节：调整为二文件模型绑定 + 骨架生效标记 + 导入白名单版本 |
| 8.8 回滚 | 第 13.4 节：回滚粒度细化为"块 + 二文件对应投影 + names 挂载" |

**新增冻结项**：

1. 二文件同目录同基名：`<module>.spec.<lang>.dsl` / `<module>.<ext>`。
2. 块 ID 终身不变：`<module>_<seq>`，允许嵌套 `_<seq>.<sub>`。
3. 分隔符统一标记：`@jev-block:<id>:begin` / `:end`，注释前缀随目标语言。
4. 保留块固定 ID：`names`（`declaration-only`）、`imports`（`hoisted`）。
5. **块类别**：`emitting` / `declaration-only` / `hoisted`；`declaration-only` 不参与对齐。
6. spec DSL 与代码均用目标语言行注释符。
7. 改块不重跑全量：修改流程按块翻译，成本 O(改动块数)。
8. 通用 Agent 打分隔符：代码 → spec 的切块由通用 Agent 做，JevAgent 不做切块语义判断。
9. 库导入三类归属：隐含必需（工具闭包保证）/ 显式依赖（作者声明，工具置顶去重）/ 库可选语法（显式原生透传）。
10. **未知即错误**：未识别不得静默走 raw；原生透传必须显式标记。
11. 自动纠偏授权档 B：仅 `confusions` 中 `action: correct` 自动改，且报告可见。
12. 通用关键字核为闭集；`core_conformance` 三档履约，`conditional` 必附 `requires`、`unsupported` 必附 `reason`。
13. 跨语言迁移 = 复制 + 定点处理；`verbatim` 块逐字节复制、禁止重新生成。
14. 编译门槛 V1/V2/V3 为每期必须全绿的 CI 级门槛。

---

## 18. 一句话总结

> JevAgent 是通用 Agent 的一个 tool。输入是"带块分隔符的 spec DSL 或已打分隔符的代码 + 目标语言表"，输出是同块 ID 的另一侧表示。spec DSL 是唯一真相源，块 ID 终身不变，分隔符用目标语言注释符保证代码可编译，改一个块只翻一个块。工具管逐块翻译、导入闭包、骨架落地、引用合法性校验与核心节点履约；通用 Agent 管意图、选表、打分隔符、写 spec、编译验证。库导入由工具闭包保证完整性并回写 spec，未知输入一律硬错误，跨语言迁移只复制 `verbatim`、只重写 `rewrite`。

> 经过实践检验发现高层语义方案完全不可行，因为不同语言之间的细节逻辑本就不同，强行抹平反而问题更大。
