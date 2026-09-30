# JevAgent 设计稿 V2.0（最终定修稿）

> 版本：V2.0  
> 定位：以 Jev 判断模型为核心、树形路由为骨架、通用 Agent 为编排层，**二文件模型 + 库导入层 + 校验防火墙 + 通用关键字核**四位一体的**语义解析编写器**系统。  
> 合并来源：《JevAgent 设计稿 v0.2》《JevAgent 设计稿补充：跨语言分层语义与底层特化 v0.1》《JevAgent 设计稿：逻辑歧义消除补充稿 v1.0》；架构级修订依据《JevAgent 重构方案：二文件模型与库导入层》（下称《重构方案》），其第 11 节 D1~D20 决策对本稿 binding。  
> 效力：本稿为三份原稿经《重构方案》修订后的联合定修稿。凡与二文件模型、库导入层、校验防火墙、通用关键字核相冲突的旧条款一律失效，以本稿为准；跨语言相关内容以《重构方案》第 12、13 节为准；其余内容按主设计稿 v0.2 与《逻辑歧义消除补充稿 v1.0》执行。本稿发布后，作为 Agent 实验实践、产品落地、实现评审的唯一基准稿。  
> 落地约束：实现时不得自行更改本稿冻结的封闭集合、路由 schema、块类别定义、确认点版本向量、词表工厂生效时机、异构审查要求、核心表闭集、删除即错误的容错口径。需要变更时，必须走版本化流程：生成候选 → Jev 验证 → 通用 Agent 语义审 → 回归测试 → 编译门槛 → 人类审批 → 版本递增。

---

## 0. 最终统一口径（最高优先级）

以下为最高优先级解释，后续条款均围绕其展开：

> **路由表 schema 冻结；`/dynamic` 是独立运行期层；动态节点结构封闭、实例动态；词表工厂仅任务前生效；二文件模型（spec 唯一真相源 + 生成产物）取代旧多文件模型；库导入由工具闭包保证、显式依赖由 Agent 声明；块类别三分；未知即错误、禁止静默走 raw；逃生舱必须显式标记且可 grep；核心表 `syntax_core_v1` 为闭集且只统一词汇、语法、运算符；履约三档 `supported` / `conditional` / `unsupported`；特化映射静态优先；回滚按确认点版本向量；可逆按执行动作判定；词表语法 Jev 审、词条语义通用 Agent 审；异构要求不同类型模型；规则沉淀分散在各表；特化层是一等公民；raw 是安全阀。**

补充口径：

- 通用 Agent 负责逻辑分解、spec DSL 编写、全局状态、符号宇宙声明（`names` 块）、接口契约、风格统一、质疑处理、词表工厂、编译与用例验证。
- JevAgent 负责 spec 解析、核心节点识别与履约校验、库导入闭包与置顶去重、生成前的引用合法性校验（校验防火墙）、特化映射选择、符号选择、模板填充、词表语法验证、结构化质疑。
- 审查层负责 Tier 1 确定性检查（含编译门槛）、Tier 2 异构通用 Agent 交叉审查、Tier 3 人类仲裁。
- 人类只处理分歧，不处理流程；工作量 O(分歧数)，非 O(任务量)。

---

## 1. 系统定位

JevAgent 不是通用 Agent，也不是代码生成器。它是一个**受约束的逻辑落地执行器**：

- **输入**：一份已写好的 spec DSL（`<module>.spec.<lang>.dsl`）+ 一张目标语言路由表 + 当前符号环境 + 词表。
- **输出**：确定性代码 / 命令。
- **不负责**：理解长逻辑、管理全局状态、编排任务顺序、代替编译器与用例测试。

它的核心价值在于：**在封闭集合内做精确判断，把幻觉从代码层消除**。

在二文件模型下，JevAgent 的职责进一步收缩为：

- 在 spec 层：识别核心节点与语言绑定节点，做库导入闭包，做生成前的引用合法性校验（未知即错误）。
- 在特化层：从语言特化子树中选择叶子、填充模板、做语法补全选择。
- 在词表工厂：验证候选词表的语法正确性，不做词条语义创造。

**边界**：它守的是**引用合法性**，不是**逻辑正确性**。算法错误仍需用例测试，编译与执行验证仍由通用 Agent 负责。

---

## 2. 核心概念

| 概念 | 说明 |
|------|------|
| **Jev** | 只做 Choice / Score / Noul 三类判断的模型，不生成自由文本。 |
| **路由表** | 树形结构，描述从抽象逻辑到目标语言语法的映射路径。 |
| **二文件模型** | `<module>.spec.<lang>.dsl`（唯一真相源）+ `<module>.<ext>`（生成产物），同目录维护 `blocks_index.json` 与 `manifest.json`。 |
| **spec DSL** | 语言绑定的中文关键字 DSL，承载目标语言语义与 `node:` 注解，是唯一可写入口。 |
| **库导入层** | 隐含必需导入由工具闭包保证；显式依赖由 Agent 在 spec 中声明；保留块 `imports` 由工具置顶。 |
| **块类别** | `emitting`（默认，产出代码、参与对齐）/ `declaration-only`（如 `names`，不产出代码、不参与对齐）/ `hoisted`（如 `imports`，位置强制首位）。 |
| **保留块** | 具备固定 ID 与固定语义的块：`names`、`imports`。前者不产出代码，后者由工具置顶。 |
| **名字表（`names`）** | 置于语义文件开头的保留块，声明库/变量/常量/函数，构成符号宇宙；按模块挂载到路由树，禁止全局泄漏。 |
| **校验防火墙** | 生成前的引用合法性拦截层：未知即错误、逃生舱显式标记、`confusions` 有限纠偏；不守逻辑正确性。 |
| **通用关键字核** | 各语言 DSL 共享的循环/分支/定义/输入输出关键字与运算符表达，定义在语言无关的 `syntax_core_v1`。 |
| **核心履约（core_conformance）** | 每张语言表对核心节点的履约声明，三档：`supported` / `conditional`（附 `requires`）/ `unsupported`（附 `reason`）。 |
| **词表** | 封闭集合，任务前可扩展，任务期间不可新增。 |
| **模板表** | 封闭集合，定义叶子节点的代码形态与槽位。 |
| **对话表** | 封闭集合，把结构化缺口翻译成人话。 |
| **语言特化层** | 各目标语言表的特化子树，处理指针、内存、并发、语法糖、库调用等语言特有细节。 |
| **块** | 通用 Agent 切分出的独立逻辑单元，是 Jev 的处理粒度。 |
| **确认点** | 通过审查的块，是回滚锚点。 |
| **确认点版本向量** | 绑定代码、spec、符号表快照、动态节点、契约、表版本、缓存键等状态。 |
| **词表工厂** | 通用 Agent 为特定任务生成候选词表，Jev 验证语法正确性。 |
| **动态符号表** | 运行期维护的变量、函数、模块、类、别名等符号集合，权威源为 `names` 块。 |
| **`/dynamic` 层** | 独立运行期层，不是目标语言表的静态节点，也不是表扩展。 |
| **manifest** | 统一版本绑定文件，包含 skeleton、table、vocab、mapping、required_imports、symbol_snapshot、code_commit、spec_commit。 |
| **raw 节点** | 不可提取部分的显式保留，作为特化层安全阀；必须显式标记且可 grep。 |
| **迁移分类** | 跨语言迁移时的块级静态分类：`verbatim` / `partial` / `rewrite`。 |

---

## 3. 整体架构

### 3.1 编排与执行总览

```
用户意图
    ↓
┌─────────────────────────────────────┐
│  通用 Agent（编排层）                │
│  - 逻辑分解 → 块序列 + 接口契约      │
│  - 全局状态管理（变量/作用域/类型）  │
│  - 符号宇宙声明（names 块）          │
│  - 词表工厂（按任务生成候选词表）    │
│  - 编写 spec DSL（含显式库依赖）     │
│  - 逐块调用 JevAgent                 │
│  - 质疑处理 / 重切 / 升级            │
│  - 块间接口校验 + 风格统一           │
│  - 编译门槛与用例验证                │
└─────────────────────────────────────┘
    ↓ spec DSL + 符号环境 + 表选择 + 词表
┌─────────────────────────────────────┐
│  JevAgent（执行层）                  │
│  - spec 解析：names 块 → 符号挂载    │
│  - 核心节点识别与履约校验（三档）    │
│  - 引用合法性校验（校验防火墙）      │
│  - 库导入闭包 + 置顶去重 + 回写 spec │
│  - 特化层：树形路由、映射选择        │
│  - 叶子模板填充                      │
│  - 动态符号选择                      │
│  - 词表语法验证                      │
│  - 不确定时抛出结构化质疑            │
└─────────────────────────────────────┘
    ↓ 块输出 + 校验报告 + 质疑 + 词表验证结果
┌─────────────────────────────────────┐
│  审查层                              │
│  - Tier 1：确定性检查（编译门槛/lint）│
│  - Tier 2：异构通用 Agent 交叉审查   │
│  - Tier 3：人类仲裁（仅分歧点）      │
└─────────────────────────────────────┘
    ↓
目标语言代码 / 命令
```

### 3.2 二文件模型架构

```
<module>.spec.<lang>.dsl   （唯一真相源：中文关键字 + 目标语言语义 + node 注解）
    ↓ JevAgent：解析 → 校验防火墙 → 核心节点识别 → 语言表映射 → 叶子填充 → 骨架与导入组装
<module>.<ext>             （生成产物：含置顶导入区与骨架）
    ↑ code_to_spec         （既有代码入口：自由区收纳 → 逐块反解 → 回写 spec）
```

**关键变化**：语言绑定，**不做跨语言归一**；库与逻辑同处一层，写什么逻辑、用哪个库由通用 Agent 在 spec 中直接书写，导入的真实语法、位置、去重、完整性由工具保证。

### 3.3 责任归属表

| 环节 | 生成者 | 验证者 | 容错策略 |
|------|--------|--------|----------|
| spec DSL 编写 | 通用 Agent | JevAgent（校验防火墙） | **不容忍未知**：未识别即硬错误（附最近候选）；命中别名集则归一且必须在报告中可见；`confusions` 仅档 B 自动纠偏 |
| spec → 目标代码 | JevAgent | 通用 Agent + Tier 1 | 结构确定，不容忍语法错误；产物必须过编译门槛；有 error 时拒绝产出，禁止静默降级 |

---

## 4. 核心接口与封闭性

### 4.1 Jev 的 Choice / Score / Noul 定义

**结论**：三者是候选内判断接口，不是生成接口。

**接口规则**：

| 接口 | 输入 | 输出 | 约束 |
|------|------|------|------|
| Choice | 有限候选集 + 上下文 | 候选 ID | 只返回候选 ID，不生成新文本 |
| Score | 候选集 + 上下文 | ranking + 置信度 | 用于排序，不直接决定最终选择 |
| Noul | 门控问题 + 上下文 | `continue / stop / unknown` | 用于是否结束、是否完整等门控 |

**候选来源**：路由引擎、符号表、词表、别名集。Jev 不构造候选。

**底层建议**：规则引擎 + 小模型 + 约束解码；LLM 仅用于候选分类。

**校准目标**：

- Choice top1 ≥ 98%
- Score top1 ≥ 95%
- Noul ≥ 99%

**示例**：变量位置优先从 `/dynamic/variables` 选 `a`，而不是让 Jev 编造 `a`。

### 4.2 封闭集合与动态路由表边界

**结论**：路由表 schema 任务期间冻结；`/dynamic` 是独立运行期层；动态节点结构封闭，实例动态。

**规则**：

- 路由表结构不可变。
- `/dynamic` 不是目标语言表的静态节点，也不是表扩展，而是独立运行期层。
- 路由引擎在运行期把 `/dynamic` 层合并进候选视图。
- 动态节点必须来自符号表，带 `symbol_name / symbol_type / scope / provenance`。
- Jev 只能选已注册动态节点，不能发明。

**示例**：`a = 10` 后，`/dynamic/variables/a` 挂载；Jev 写变量时 Choice 到该节点，输出 `a`。

### 4.3 词表工厂与任务期间封闭性

**结论**：不违反，因为词表工厂仅任务前生效；任务中不新增、不热补丁。

**规则**：

- 任务前：可预判、可用户请求、可工厂生成候选，Jev 验证，人审批后合并。
- 任务中：`vocabulary_gap` 只抛质疑或记录，不生成当前任务可用词表。
- 可用预定义兜底词表，但兜底词表也必须任务前已存在。
- 任务结束后的缺口记录，作为下一任务前词表工厂输入。
- 不直接修改当前任务使用的词表版本。

**示例**：遇到 `hash_sha256` 缺词，当前任务抛 `vocabulary_gap`；记录后下一任务前生成 `shell_crypto_v1`。

### 4.4 双向校验的对称性

整个系统形成**双向校验闭环**：

| 方向 | 生成者 | 验证者 | 验证内容 |
|------|--------|--------|----------|
| 代码生成 | JevAgent | 通用 Agent | 语义正确性 |
| 词表生成 | 通用 Agent | JevAgent | 语法正确性 |
| 特化映射生成 | JevAgent | 通用 Agent | 语义等价性 |

- **Jev 生成代码 → 通用 Agent 审**：通用 Agent 语义强，能发现逻辑错误。
- **通用 Agent 生成词表 → Jev 审**：Jev 结构强，能发现语法错误。
- **Jev 做特化映射 → 通用 Agent 审**：通用 Agent 审语义等价性、歧义分支行动方向。

两者失败模式正交，互相补位。这是异构交叉的第二种形态——不是同一产物的双方审查，而是**各自擅长的产物交给对方验证**。

---

## 5. 通用关键字核与特化映射

### 5.1 核心原则

#### 5.1.1 通用关键字核原则

**各语言 DSL 共享同一套循环、分支、定义、输入输出关键字与运算符表达；只统一词汇、语法、运算符。**

统一的范围：

- **词汇**：`定义` / `返回` / `如果` / `否则如果` / `否则` / `对于` / `当` / `跳出` / `继续` / `设` / `输出` / `输入`。
- **运算符**：比较、逻辑与算术运算符的表达（如 `<=`、`并且`、`或者`、`非`）。
- **语句结构写法**：`对于 x 中的 集合:`、`如果 条件:` 等前缀式关键字写法。

不统一的范围（必须显式标注，禁止粉饰）：

| 类别 | 例子 | 处理 |
|------|------|------|
| 语义差异 | C 遍历数组需要长度或哨兵，Python 直接遍历 | 标 `conditional` 并附 `requires` |
| 库差异 | `math.sqrt` 与 `sqrt` + `<math.h>` | 落在各语言表节点中，不归一 |
| 类型系统差异 | C 需显式类型，Python 无声明概念 | 由 `names` 块声明承载 |
| 内存 / 并发 / 未定义行为 | `malloc`、借用检查、goroutine | 不进入核心核；仅在各语言特化子树 |

**判断标准**：如果一处差异属于"同一件事的不同写法"，由工具屏蔽，不暴露给作者；如果属于"目标语言里这件事本就不成立"，必须标注并交由防火墙校验前置条件。**禁止为凑齐通用性而粉饰缺口。**

#### 5.1.2 底层特化原则

**语言特有实现细节只在针对性优化的树形图中处理，由 Jev 在该层做语法补全选择。**

特化层不是"兜底"，而是**一等公民**。C 的指针解引用、Rust 的借用、Python 的 GIL 相关操作，都应在各自语言表中有完整的路由子树，而不是塞进核心核用条件分支区分。

#### 5.1.3 core 的护栏

**必须写死的护栏**（防止 core 被往上推，重演旧路线失败）：

> **core 只统一"词汇、语法、运算符"。语义差异与库差异明确留在各语言，标注为 `conditional` / `unsupported`，并由防火墙校验前置条件。**

**一个诚实的例子**：`对于 x 中的 数据:` 在 Python 直接成立，在 C 里存在真实语义缺口——C 遍历数组需要长度或哨兵，仅凭"数据"这个名字推不出 `n`。因此它只能标 `conditional`，前置条件为"集合带已知长度绑定"，由 `names` 表（`变量 数据: list` + `常量 长度`）或防火墙检查来满足。

**不掩盖这类缺口，正是本层的分水岭**：把缺口标出来、并在生成前拦下，而不是粉饰成"语言无关"。

#### 5.1.4 分层粒度受 Jev 能力约束

Jev 不擅长多步推理，每一步准确率会下降。因此从"核心节点"到"特化层叶子"的语义跳跃不应超过 2-3 层。核心节点集不能过度膨胀，否则 Jev 在路由时置信度会显著衰减。

块大小 ≤ Jev 上下文窗口的 50% 的约束在同一层内同样适用：一个块对应的特化子树，应控制在一屏可读的规模。

### 5.2 核心表 `syntax_core_v1`

**结论**：核心表语言无关，独立为 `syntax_core_v1`，与各语言表共享同一路由引擎。

**规则**：

- 节点定义在 `tables/syntax_core_v1.json`，含 `core_nodes` 与 `core_operators` 两段。
- **核心表为闭集**：新增核心节点需显式评审（参照候选词表流程），禁止就地扩表。
- 每条核心节点声明 `canonical` 与可选 `aliases`。
- 目标语言表通过 `core_conformance` 关联核心节点与其特化叶子。
- 同一引擎，不同表。

**示例**：`对于 x 中的 数据:` 命中 `/core/loop/for`；进入 Python 表后查 `core_conformance` 到 `/python/control/loop/for`。

#### 5.2.1 `/semantic/*` 的角色

**结论**：`/semantic/*` 保留为**内部路由中间层**，不再是用户可写层。

| 对比项 | 旧的用户可写层 | 现在的内部中间层 |
|--------|----------------|------------------|
| 是否有对应文件 | 有（可读写） | **无**（不落盘为可编辑入口） |
| 谁能改 | 通用 Agent | 表维护者，随表版本化 |
| 作用 | 承载"语言无关逻辑" | 承接 `inferSemanticNode` 两跳路由的中间一跳 |
| 失败后果 | 层间往返失真 | 仅路由失败 → 硬错误 |

`inferSemanticNode` → `semantic_mappings` → `/{lang}/*` 这条两跳路由仍是从**中文关键字**定位目标节点的有效机制，只是不再对应任何用户可写文件。P0 起 `/semantic/module/import`、`/semantic/module/import/local` 亦按此定位纳入。

### 5.3 核心节点最小完备集

**结论**：第一批必须覆盖定义、返回、分支、循环、变量、输入输出与运算符核。

**集合**：

| 核心节点 | canonical | 说明 |
|----------|-----------|------|
| `/core/define` | `定义` | 函数定义 |
| `/core/return` | `返回` | 返回值 |
| `/core/if` | `如果` | 条件分支 |
| `/core/elif` | `否则如果` | 多路分支 |
| `/core/else` | `否则` | 兜底分支 |
| `/core/loop/for` | `对于` | 遍历 |
| `/core/loop/while` | `当` | 条件循环 |
| `/core/loop/break` | `跳出` | 跳出循环 |
| `/core/loop/continue` | `继续` | 跳过本轮 |
| `/core/var/declare` | `设` | 变量声明 / 赋值 |
| `/core/io/output` | `输出` | 输出 |
| `/core/io/input` | `输入` | 输入 |

**运算符核**（`core_operators`）：

| 作者统一写 | Python | C | Shell |
|-----------|--------|---|-------|
| `<=` | `<=` | `<=` | `-le` |
| `>=` | `>=` | `>=` | `-ge` |
| `并且` | `and` | `&&` | `&&` |
| `或者` | `or` | `\|\|` | `\|\|` |
| `非` | `not` | `!` | `!` |

**判断标准**：

- 三种语言都有"同一件事的不同写法" → 进核心核，由工具屏蔽。
- 至少一种语言需要额外前置条件 → 进核心核，履约标 `conditional` 并附 `requires`。
- 某种语言语义上不成立 → 进核心核，履约标 `unsupported` 并附 `reason`；**不得从核心表删除**，也不得虚假标 `supported`。

**示例**：`当 i <= 上限:` 在 shell 侧由运算符核转成 `while [ "$i" -le "$上限" ]; do`。

### 5.4 与主骨架的对应

主设计稿骨架：

```
/control
  /loop
    /for
    /while
    /iterate
  /branch
    /if
    /switch
/data
  /declare
  /assign
  /read
  /write
/function
  /define
  /call
  /return
/io
  /input
  /output
/error
  /try
  /catch
  /raise
```

所有语言表共享该骨架，核心节点与骨架一一对应，但**不包含**语言特有子分支（如 `/c/pointer`、`/rust/borrow`）。这些特化子树挂在各语言表的 `/dynamic` 或独立特化分支下，**不能修改骨架层级**。

### 5.5 容错别名归一

**结论**：节点声明 `canonical` + `aliases`，命中别名即归一；未命中一律硬错误。

**规则**：

- 别名集为**闭集**，随表版本化。
- 候选来自别名集与 `confusions` 表，不来自相似度计算。
- 命中别名 → 归一为 canonical，记录到 `alias_normalization`，**必须在报告中可见**。
- 未命中 → 硬错误 `unknown_node`，附**最近候选建议**（编辑距离只用于给建议，**绝不自动采用**）。
- 禁止静默落到 `/{lang}/raw`。
- `confusions` 表仅收录确定的一对一误写，且仅 `action: correct` 的条目自动纠偏，其余只报错。
- 同一别名模式高频出现或未命中率 >5% → 触发别名集评审（而非扩大自动纠偏）。

**示例**：`函数 主函数():` 命中 `/core/define` 的别名 `函数`，归一为 `定义` 并记录；`打印("x")` 未命中任何别名 → 硬错误，附建议"是否想写 `输出("x")`？"。

### 5.6 特化层映射

**结论**：静态声明优先，Jev 推断仅 fallback 且必须 Tier2 审。

**规则**：

- 映射表由语言表维护者维护，版本化。
- 查不到映射时，Jev 推断候选来自：同骨架其他语言映射、历史映射、相似节点。
- **推断结果一律由 Tier2 审**，不得直接落地为常态路径。
- 允许 `raw_fallback` 时回退 raw，且必须显式标记并计入报告。
- 不允许则 `no_mapping` 质疑。

**示例**：C 表有 `(deref ptr) → /c/pointer/deref`；Rust 表查不到时，Jev 推断候选 `*ptr` 或 `ptr.as_ref()`，Tier2 审。

### 5.7 特化节点结构

```json
{
  "node_id": "/c/pointer/deref",
  "parent": "/c/pointer",
  "type": "leaf",
  "template": "*{ptr}",
  "spec_template": "解引用({ptr})",
  "slots": ["ptr"],
  "guards": ["not_null(ptr)", "aligned(ptr, 4)"],
  "maps_from": ["/semantic/data/deref"],
  "placement": "inline",
  "aliases": ["取值", "取指针内容"],
  "raw_fallback": true,
  "notes": "指针算术场景需走 /c/pointer/arith 分支"
}
```

关键字段：

| 字段 | 含义 |
|------|------|
| `template` | 目标语言代码形态 |
| `spec_template` | 作者侧书写形态，逆向与容错归一使用 |
| `maps_from` | 可从哪些中间层节点映射而来，供 Jev 路由时匹配 |
| `guards` | 语言特定的前置条件，不满足时 Jev 应抛出质疑或回退 `raw` |
| `placement` | 产物落位：`inline`（默认）/ `imports`（由组装器置顶） |
| `aliases` | 容错别名集（闭集），命中即归一 |
| `raw_fallback` | 是否允许回退到原始代码块，允许即须显式标记 |

**`guards` 与 `conditional.requires` 的关系**：

- `conditional.requires` 属**核心履约声明**，由核心节点维度描述"缺什么就不能生成"，由校验防火墙在生成前检查，不满足即硬错误。
- `guards` 属**特化节点自身约束**，由语言表维护者在叶子维度描述，命中时 Jev 抛 `guard_failed` 质疑或回退 `raw`。
- 两者不可互相替代：前者是表级声明、必须机器可判；后者是节点级约束、可含语言特定断言。

### 5.8 特化层路由

Jev 在特化层的路由流程：

```
spec 行
  ↓ 核心节点识别（canonical + aliases 归一）
核心节点 (/core/loop/for)
  ↓ 语言表已确定（C）；查 core_conformance 三档
  ↓ conditional → 交防火墙查 requires，不满足即硬错误并说明缺什么
在 /c/control 分支下 Choice：候选 /c/control/for、/c/control/while
  ↓ Jev 依上下文（集合是否有长度绑定、是否哨兵终止）选择
到达叶子，填充模板（含 core_operators 转换）
  ↓ guards 不满足 → 抛 missing_condition 或 unknown_symbol
```

### 5.9 多语言共享的核心关键字

同一核心关键字可被多张语言表履约：

| 核心节点 | Python 履约 | C 履约 | Shell 履约 |
|---------|------------|--------|-----------|
| `/core/loop/for` | `/python/control/loop/for` | `/c/control/for`（conditional：需长度或哨兵） | `/shell/control/for` |
| `/core/loop/while` | `/python/control/loop/while` | `/c/control/while` | `/shell/control/while` |
| `/core/io/output` | `/python/io/output` | `/c/io/output`（格式符由工具按类型解析） | `/shell/io/output` |
| `/core/var/declare` | `/python/data/declare` | `/c/data/declare`（需类型声明） | `/shell/data/assign` |
| 解引用类意图 | 无对应物 → `unsupported` + reason | `/c/pointer/deref` | 无对应物 → `unsupported` + reason |

### 5.10 映射声明

每张语言表在元数据中声明其支持的核心履约与特化映射：

```json
{
  "table_id": "c_v1",
  "target_language": "c",
  "skeleton_ref": "common_skeleton_v1",
  "core_conformance": {
    "/core/define":    "/c/function/define",
    "/core/io/output": { "status": "supported", "node": "/c/io/output" },
    "/core/loop/for":  { "status": "conditional", "node": "/c/control/for",
                         "requires": ["集合带有已知长度绑定或哨兵"] },
    "/core/io/input":  { "status": "conditional", "node": "/c/io/input",
                         "requires": ["参数为已声明类型的变量（用于生成取地址符 &）"] }
  },
  "semantic_mappings": {
    "/semantic/module/import":       "/c/module/include_system",
    "/semantic/module/import/local": "/c/module/include_local"
  },
  "required_imports": {
    "printf": "<stdio.h>", "scanf": "<stdio.h>", "malloc": "<stdlib.h>",
    "strlen": "<string.h>", "sqrt": "<math.h>"
  },
  "confusions": [
    { "wrong": "print", "right": "/c/io/output", "action": "correct" },
    { "wrong": "len", "right": null, "action": "error", "hint": "C 无 len，请用 sizeof 或显式长度" }
  ]
}
```

Jev 在从核心节点进入特化层时，直接读取 `core_conformance`，减少 Choice 层数。

### 5.11 跨语言一致性校验

**结论**：以覆盖率矩阵校验为主，**不能只靠约定**。

**规则**：

- 新增 action `check_tables`：逐语言校验 `core_conformance` 完整性，产出「语言 × 核心节点覆盖率矩阵」。
- 缺声明即报错；`unsupported` 必须附 `reason`；`conditional` 必须附 `requires`。
- 覆盖率矩阵为**正式交付物**，同时是给开发者的上手说明书。
- 运算符核纳入编译门槛验证覆盖（V1 / V3）。
- 同逻辑跨语言时，**核心节点部分应逐行相同**（可用 `diff` 验证，差异仅出现在库与类型处）。

**漂移必须受校验——本项目已有三处实测证据**：

| 漂移实例 | 后果 |
|---|---|
| `c_v1.json` 曾缺 `/c/control/for`、`/c/control/while` | C 的 `对于` / `当` 无法生成 |
| `shell_v2.json` 缺 `/shell/function/call` | shell 函数调用走错分类 |
| `normalize.js` 的 `KEYWORD_MAP` 与各语言表构成两套真相源 | 映射不一致，且 `KEYWORD_MAP` 沦为死代码 |

**示例**：覆盖率矩阵。

| 核心节点 | Python | C | Shell |
|---|---|---|---|
| `/core/define` | ✅ | ✅ | ⚠️ conditional |
| `/core/loop/for` | ✅ | ⚠️ conditional | ✅ |
| `/core/io/input` | ✅ | ⚠️ conditional | ✅ |
| `/core/io/output` | ✅ | ✅ | ✅ |

### 5.12 映射失败处理

按履约三档处理：

| 档 | 含义 | 工具行为 |
|----|------|----------|
| `supported` | 无条件可生成 | 直接生成 |
| `conditional` | 有前置条件 | **校验前置**；不满足 → 硬错误并说明缺什么（如"集合缺少已知长度绑定，请在 `names` 块补 `常量 长度`"） |
| `unsupported` | 目标语言无对应物 | 硬错误 + 替代建议，**禁止静默丢弃** |

补充规则：

1. 核心节点在语言表中**无履约声明** → 报错（等同 `unsupported`，但不允许无声明蒙混）。
2. `raw_fallback: true` 的节点可回退 `raw`，但必须显式标记并计入报告。
3. 通用 Agent 尝试从其他语言表推断或请求 spec 澄清。
4. 无法补全则升级人类仲裁。

### 5.13 不可提取部分与 raw 节点

当语言表无法表达某个底层操作时，保留原始代码块：

```
raw:
  source_lang: C
  code: |
    char *p = (char *)&x;
    p[0] ^= 0xFF;
  reason: pointer_arithmetic
  declared_by: /c/pointer/arith
```

**raw 节点是特化层的安全阀**，须遵守：

- **逃生舱必须显式标记且可 grep**。原则：**逃生舱一旦隐式，整层就都成了逃生舱。**
- 未标记却无法解析的行 → 一律报错，不得静默走 raw。
- raw **必须计入报告**（块 ID、行号、原因、占比）。
- raw 占比 >10% 触发词表工厂 / 特化映射补全。
- raw 占比 >30% 阻塞新任务。
- 跨语言迁移时 raw 保留原始代码，并计入 `rewrite` 块。
- raw 不参与一致性校验，整体正确性靠人工与沙箱。

---

## 6. JevAgent 设计

### 6.1 职责边界

**做**：

- 在给定块内走树形路由。
- 从有限分支中选择下一个节点。
- 解析 `names` 块并做模块级符号挂载。
- 识别核心节点并校验核心履约（三档）。
- 做生成前的引用合法性校验（校验防火墙）。
- 做库导入闭包、置顶去重，并把结果回写 spec。
- 在特化层做映射选择、语法补全选择。
- 从动态符号表中选择已定义变量/函数/模块。
- 填充叶子模板槽位。
- 验证候选词表的语法正确性。
- 逻辑不清时抛出结构化质疑。

**不做**：

- 跨块逻辑推理。
- 全局状态维护。
- 自由文本生成。
- 长上下文理解。
- 主动发明词表项（只做验证，不做创造）。
- 代替编译器与用例测试（不代跑编译器，不宣称"校验通过 = 代码正确"）。

### 6.2 处理流程

```
输入：spec 块内容 + names 符号环境 + 目标语言表 ID + 词表
  ↓
1. 表选择（单表直接用，多表走 Jev Choice）；2. 词表验证（若本轮有候选词表）
  ↓
3. spec 解析：names 块 → 模块级符号挂载（纯函数）；定位保留块（names / imports）
  ↓
4. 核心节点识别与履约校验：canonical + aliases 归一 → core_conformance 三档 → conditional 查 requires
  ↓
5. 引用合法性校验（防火墙）：未声明库/变量、跨语言误写、必需导入缺失；有 error → 拒绝产出
  ↓
6. 库导入闭包：显式声明 ∪ 表推导 → 去重排序 → 回写 spec 的 imports 块（自动项标 origin:auto）
  ↓
7. 特化层路由：优先 core_conformance / semantic_mappings，查不到走 Jev Choice（推断交 Tier2）
  ↓
8. 符号选择：动态符号表 → 名字表 → 质疑；兜底词表仅作最后手段
  ↓
9. 叶子：模板填充 + core_operators 转换 + 骨架应用 + 导入区置顶
  ↓
10. 输出块代码 + 路由路径 + 置信度 + 校验报告 + 词表验证结果
  ↓
11. 低置信 / 逻辑缺口 → 抛结构化质疑
```

### 6.3 输出格式

```json
{
  "block_id": "blk_003",
  "path": ["/python", "/control", "/loop", "/for"],
  "confidence": 0.94,
  "code": "for i in range(长度):",
  "slots": {"var": {"source": "names", "value": "i"}, "iterable": {"source": "names", "value": "range(长度)"}},
  "ambiguities": [],
  "symbols_used": ["长度"],
  "symbols_defined": [],
  "imports": {"declared": ["import math"], "auto": [], "placement": "top"},
  "core_conformance": {"/core/loop/for": {"status": "supported", "node": "/python/control/loop/for"}},
  "spec_validation": {
    "errors": [], "warnings": [],
    "auto_corrected": [{"line": 12, "from": "print(...)", "to": "输出(...)", "rule": "confusions/print"}],
    "coverage": {"rules_applied": ["引用合法性", "导入闭包", "confusions"],
                 "libraries_modeled": ["math", "stdio.h"], "libraries_unmodeled": []}
  },
  "alias_normalization": {"input_nodes": 5, "normalized_nodes": 5, "unknown_nodes": [],
                          "alias_hits": [{"input": "函数 主函数()", "canonical": "/core/define", "alias": "函数"}]},
  "raw_ratio": 0.0,
  "vocab_validation": {"candidate_vocab_id": "shell_crypto_v1", "valid": true, "issues": []}
}
```

---

## 7. 树形路由表设计

### 7.1 表的元结构

```json
{
  "schema_version": "2.0",
  "table_id": "python_v3",
  "target_language": "python",
  "skeleton_ref": "common_skeleton_v1",
  "core_conformance": {
    "/core/define":   "/python/function/define",
    "/core/loop/for": "/python/control/loop/for"
  },
  "required_imports": { "math": "import math", "numpy": "import numpy" },
  "confusions": [{ "wrong": "printf", "right": "/python/io/output", "action": "correct" }],
  "keyword_blacklist": ["if", "else", "for", "while", "def", "return", "import"],
  "root": { "type": "branch", "choices": ["control", "data", "function", "io", "error", "module"] },
  "nodes": {
    "/control/loop/for": {
      "type": "leaf", "template": "for {var} in {iterable}:", "spec_template": "对于 {var} 中的 {iterable}:",
      "slots": ["var", "iterable"], "aliases": ["循环", "遍历"], "placement": "inline", "dynamic": true
    },
    "/module/import": {
      "type": "leaf", "template": "import {module}", "spec_template": "引入 {module}",
      "slots": ["module"], "maps_from": ["/semantic/module/import"], "placement": "imports"
    }
  }
}
```

新增字段说明：

| 字段 | 含义 |
|------|------|
| `core_conformance` | 核心节点 → 特化节点（或三档声明对象）的履约映射 |
| `required_imports` | 符号 → 必需导入的映射，供闭包推导（**只从表白名单推导**，不做启发式猜测） |
| `placement` | 节点级落位：`inline`（默认）/ `imports`（由组装器置顶） |
| `aliases` | 节点级容错别名集（闭集），命中即归一 |
| `confusions` | 跨语言误写对照表（闭集），仅 `action: correct` 自动纠偏 |
| `keyword_blacklist` | 符号扫描时需剔除的语言关键字与内建类型 |

### 7.2 节点类型

| 类型 | 作用 | Jev 调用 |
|------|------|----------|
| `branch` | 分支节点，有多个子节点 | Choice |
| `leaf` | 叶子节点，带模板 | 无（直接填充） |
| `score_node` | 多候选排序 | Score |
| `gate` | 门控（是否继续/结束） | Noul |
| `dynamic` | 动态符号挂载点 | Choice（从符号表） |
| `symlink` | 跨表链接 | 无 |

### 7.3 骨架规范与块类别

所有语言表共享同一套抽象骨架：

```
/control
  /loop
    /for
    /while
    /iterate
  /branch
    /if
    /switch
/data
  /declare
  /assign
  /read
  /write
/function
  /define
  /call
  /return
/io
  /input
  /output
/error
  /try
  /catch
  /raise
/module
  /import
  /include_system
  /include_local
```

语言特有语法只能出现在叶子或可选子分支，**不能修改骨架层级**。

**块类别**（块切分与对齐机制的前提）：

| 类别 | 例子 | 存在于 spec | 存在于 code | 参与对齐 |
|------|------|-------------|-------------|----------|
| `emitting`（默认） | 所有普通块 | ✅ | ✅ | ✅ |
| `declaration-only` | `names` | ✅ | ❌ | ❌ |
| `hoisted` | `imports` | ✅ | ✅ | ✅（位置强制首位） |

**规则**：

- `check_alignment` 必须按块类别**跳过 `declaration-only` 块**，否则第一个带 `names` 的模块就会对齐失败。
- 块类别须先于校验防火墙落地。
- `hoisted` 块在 spec 与 code 两文件中**一致地**提到首位；C 语言置于头部注释之后、任何代码之前。

### 7.4 多表选择

**结论**：关键词 + 嵌入粗筛，Jev 精判。

**规则**：

- 表数量 <10：Jev 直接 Choice。
- ≥10：关键词/嵌入粗筛 → Jev 精判。
- 低置信才并行试 top-2。
- 并行成本由编排层承担。
- 缓存失效按版本向量。
- 选择结果缓存：同会话相似任务复用。

---

## 8. 名字表（`names` 块）与符号宇宙

### 8.1 问题

Jev 在需要写变量名、函数名、模块名时，如果没有符号宇宙，只能：

- 使用兜底词表编造名字 → 与实际代码不一致。
- 抛质疑 → 增加人工负担。

此外，C 路径原先靠字面量**猜**类型，符号来源也无法区分"本地函数"与"库函数"，导致库调用被误判、必需导入缺失。

### 8.2 方案

在语义文件**开头**用保留块 `names` 声明符号宇宙，工具解析后**按模块挂载**到路由树：

```
# @jev-block:names:begin
库 math
库 numpy 作为 np
变量 数据: list
变量 结果: int
常量 上限 = 100
函数 冒泡排序(数据: list) -> list
# @jev-block:names:end
```

**结论**：`names` 是保留块而非自由内容，保证往返可解析、可校验、可重新挂载。

### 8.3 名字表结构

| 条目类型 | 语法 | 用途 |
|----------|------|------|
| `库` | `库 <module> [作为 <alias>]` | 外部模块绑定 → **导入闭包输入**；路由挂载（`np.array(...)` → `/python/lib/numpy/array`） |
| `变量` | `变量 <name>[: <type>]` | 本地变量；C 侧类型因此**确定而非推断** |
| `常量` | `常量 <name> = <value>` | 常量；可参与字面量校验 |
| `函数` | `函数 <name>(<params>) -> <ret>` | 本地函数签名；支撑参数个数/类型校验 |

解析产出的内部结构：

```json
{
  "scope_id": "module_top",
  "module_id": "bubble_sort",
  "names": {
    "libraries": [{"name": "math", "alias": null, "declared_at": "names"},
                  {"name": "numpy", "alias": "np", "declared_at": "names"}],
    "variables": [{"name": "数据", "type": "list", "defined_at": "names"},
                  {"name": "结果", "type": "int", "defined_at": "names"}],
    "constants": [{"name": "上限", "value": 100, "defined_at": "names"}],
    "functions": [{"name": "冒泡排序", "params": [{"name": "数据", "type": "list"}], "returns": "list"}]
  }
}
```

### 8.4 挂载机制

**结论**：按模块挂载，纯函数挂载，失效即重挂。

**规则**：

| 要点 | 要求 |
|------|------|
| 作用域 | **按模块挂载**，禁止全局泄漏（否则路由结果依赖加载顺序，丧失可复现性） |
| 确定性 | 挂载必须是"文件内容的纯函数"：同输入同结果，**可单测** |
| 失效 | `names` 块变更、`translate_block` 之后必须**重新挂载** |
| 冲突校验 | 名字与语法关键字/保留字冲突 → 报错；同名不同 kind → 报错 |

```
1. 解析 names 块 → 结构化条目
  ↓
2. 校验：关键字冲突 / 同名不同 kind / 类型字面量合法
  ↓
3. 生成动态节点（symbol_name / symbol_type / scope / provenance，provenance ∈ names | code_to_spec | runtime）
   挂载到**本模块**的路由视图，不进入其他模块
  ↓
4. 模块卸载或 names 变更 → 整批卸载并重挂
  ↓
5. Jev 路由到符号位置时，从本模块视图 Choice
```

**作者负担的解法**：`code_to_spec` 已在遍历代码，令其**首次导入时自动生成 `names` 块**（落成识别到的外部模块、变量、常量），之后由作者增删。既有代码零成本进入该模型，且名字表从第一天起就准确。

### 8.5 作用域管理

- 符号按作用域分层，与代码作用域对应。
- Jev 路由时，只看到**当前可见作用域**的符号。
- 作用域退出时，对应动态节点自动卸载。
- 跨作用域引用时，通用 Agent 负责补全限定名。
- 模块级挂载与作用域分层叠加：先按模块隔离，再按作用域过滤。

### 8.6 优先级

Jev 在需要符号时，按以下优先级 Choice：

```
1. 当前作用域动态符号（最高）
2. 父作用域动态符号
3. 模块级 names 符号
4. 预定义词表
5. 抛质疑（"未找到匹配的变量，是否新建？"）
```

### 8.7 动态节点示例

Python 中 `names` 声明了 `变量 结果: int` 后，`/dynamic/variables` 下出现：

```json
{
  "/dynamic/variables/结果": {
    "type": "dynamic",
    "symbol_name": "结果", "symbol_type": "int", "scope": "module_top",
    "provenance": "names", "template": "结果"
  }
}
```

接下来 Jev 想写该变量时，直接选中 `/dynamic/variables/结果`，输出 `结果`，**不再走兜底词表**。

### 8.8 回滚与一致性

**结论**：按确认点保存版本向量，块内变更暂存，确认点提交。

**规则**：

- 版本向量包含：代码 commit、spec commit、名字表快照、动态节点集合、块间契约、词表/路由表/骨架版本、缓存键。
- 回滚到最近确认点，卸载该点之后动态节点。
- 恢复名字表快照。
- 跨块引用以确认点版本为准。
- 不可逆副作用已执行则记录补偿或人工处理。

**示例**：`blk_003` 审查失败，回滚到 `blk_002` 确认点，`blk_003` 新增变量与动态节点全部卸载。

### 8.9 符号来源与闭包的关系

符号来源决定**是否需要导入**，是库导入闭包的判据：

| 符号来源 | 典型形态 | 是否需要导入 | 谁负责 |
|----------|----------|--------------|--------|
| 外部库 | `math`、`numpy`、`stdio.h`、`./lib/common.sh` | ✅ 需要，按语言原生语法生成并置顶 | 工具（闭包/置顶） |
| 标准库符号 | `printf`、`len`、`sqrt` | ✅ 需要，由 `required_imports` 白名单推导 | 工具（闭包） |
| 本地变量 / 常量 | `数据`、`上限` | ❌ 不需要 | 工具（仅做合法性校验） |
| 本地函数 | `冒泡排序(...)` | ❌ 不需要；但要校验签名 | 工具（签名校验） |
| 语言内建 | 关键字、内建类型 | ❌ 不需要，扫描时剔除 | 工具（`keyword_blacklist`） |

**结论**：

- `库 <module>` 声明使导入闭包从"白名单猜"升级为"声明即知"：`库 numpy 作为 np` → 工具知道 `np.array(...)` 需要 `import numpy as np`，作者不必再写 `引入 numpy 作为 np`。
- `required_imports` 表退化为**兜底下限**（处理 `printf`、`len` 这类标准库符号）。
- 仅**副作用导入**（如 `import matplotlib.pyplot`）才需显式 `引入`。
- 名字表与代码漂移由校验兜底：代码里出现但表里没有的外部名 → 警告。

### 8.10 粒度

**结论**：变量级、函数签名、类型级；不挂表达式级。

**规则**：

- 变量、函数、类、库、别名都表示。
- 遮蔽、闭包、导入别名由作用域管理。
- 函数签名含参数与返回类型。
- 表达式级不挂载，避免爆炸。

---

## 9. 词表 / 模板表 / 对话表

### 9.1 词表

- **封闭集合**，任务前可扩展，任务期间不可新增。
- 结构：

```json
{
  "word_id": "encrypt",
  "canonical": "加密",
  "synonyms": ["encrypt", "cipher", "加密"],
  "category": "operation",
  "related_nodes": ["/shell/crypto/encrypt"]
}
```

- **覆盖率指标**：每次任务后统计词表外意图数。

### 9.2 模板表

- 定义叶子节点的代码形态与槽位。
- 槽位填充来源：`names` 符号宇宙 / 动态符号表 / 块内上下文 / 质疑补全。
- 模板填充须支持按 `spec_template` / `template` **通用**填充，不得只硬编码单一形态。
- **封闭集合**，任务前可扩展。

### 9.3 对话表

- 把结构化缺口翻译成人话。
- 承担：追问、报错、确认、软拒绝。
- **封闭集合**，任务前可扩展。

### 9.4 词表工厂

**问题**：任务前扩展词表通常靠人工。当任务领域陌生（如从未处理过的 crypto 操作），人工写词表慢且易错。

**方案**：通用 Agent 作为**词表编写者**，Jev 作为**词表语法验证者**。两者分工明确，互相校验。

#### 9.4.1 触发条件

- 运行时缺口检测触发 `vocabulary_gap`。
- 任务开始前通用 Agent 预判需要新词表。
- 用户显式请求扩展某领域词表。
- 上一任务缺口记录。
- raw 占比 >10% 触发词表工厂/特化映射。

#### 9.4.2 流水线

```
1. 需求：识别词表缺口（领域、意图、涉及节点）
   ↓
2. 生成：通用 Agent 生成候选词表（JSON）
   - 词条结构、命名规则、同义词、类别
   - 关联的路由节点
   - 与现有词表的继承/覆盖关系
   - 语言绑定标签
   ↓
3. 验证：Jev 检查候选词表语法正确性
   - 词条结构是否符合 schema
   - 命名是否一致（大小写、分隔符、前缀）
   - 同义词是否与现有词表冲突
   - 关联节点是否在路由表中存在
   - 类别是否在允许集合内
   - core_conformance 是否完整、履约状态是否合法
   ↓
4. 冲突检查：与现有词表比对
   - 重名 / 同义词碰撞
   - 类别冲突
   - 节点重复挂载
   ↓
5. 回归测试：跑黄金样例
   - 现有样例不回归
   - 新词条能被正确路由
   ↓
6. 版本发布：合并到词表
   - 记录 diff、来源、验证结果
   - 版本号递增
```

#### 9.4.3 Jev 的验证职责

Jev 只做**判断**，不生成词条。它的验证项：

| 验证项 | Jev 调用类型 |
|--------|-------------|
| 词条结构是否符合 schema | Noul |
| 命名是否一致 | Score |
| 同义词是否与现有冲突 | Noul |
| 关联节点是否存在 | Noul |
| 类别是否在允许集合 | Choice |
| 词条语义是否与节点匹配 | Score |
| core_conformance 是否完整 | Noul |
| 履约状态是否合法（`conditional` 附 `requires`、`unsupported` 附 `reason`） | Noul |

验证结果结构化输出：

```json
{
  "candidate_vocab_id": "shell_crypto_v1",
  "valid": false,
  "issues": [
    {
      "type": "synonym_collision",
      "word_id": "encrypt",
      "conflict_with": "common_v2/encrypt",
      "severity": "high"
    },
    {
      "type": "unknown_node",
      "word_id": "hash_sha256",
      "related_node": "/shell/crypto/hash-sha256",
      "reason": "节点不存在于 shell_v2"
    }
  ],
  "suggestions": [
    "将 encrypt 重命名为 encrypt_file 避免冲突",
    "先在 shell_v2 中新增 /shell/crypto/hash-sha256 节点"
  ]
}
```

#### 9.4.4 词表版本化

- 每次扩展生成新版本号。
- 保留完整变更历史。
- 支持回滚到任意版本。
- 词表版本与路由表版本绑定（`vocab_ref`）。

#### 9.4.5 继承与覆盖

- 词表支持继承：`base_vocab` + `overrides`。
- 通用词表作为基础，领域词表增量扩展。
- 冲突时显式声明覆盖，不静默替换。

#### 9.4.6 语言绑定标签扩展

词表工厂增加**语言绑定标签**：

```json
{
  "word_id": "deref",
  "canonical": "解引用",
  "synonyms": ["deref", "解引用", "取指针内容"],
  "category": "operation",
  "language": "c",
  "related_nodes": ["/c/pointer/deref"],
  "maps_from": ["/semantic/data/deref"]
}
```

Jev 验证候选词表时，增加验证项：`language` 是否合法、`maps_from` 是否指向存在的中间层节点。

#### 9.4.7 审批

**结论**：审版本摘要、diff、Jev 验证报告、回归结果。

**规则**：

- 低风险自动合并，高风险人工。
- 审批粒度：版本。
- 验证失败：拒绝合并；可部分合并；严重人工介入。
- 不审批自动合并仅限低风险、小 diff、回归通过。

#### 9.4.8 词表语法与词条语义的仲裁分工

- 词条结构、命名、同义词冲突、节点存在性 → Jev。
- 词条语义是否与节点匹配 → 通用 Agent。
- Jev Score 可做语义匹配特征，但最终语义仲裁倾向通用 Agent。
- 优先级：安全 > 结构语法 > 语义 > 风格性能。

**示例**：`encrypt` 同义词碰撞 → Jev；`encrypt` 是否真对应加密操作 → 通用 Agent。

---

## 10. 质疑机制

### 10.1 触发条件

| 条件 | 质疑类型 |
|------|----------|
| 必填槽位缺失 | `missing_slot` |
| 循环终止条件不清 | `missing_condition` |
| 逻辑分支不完整 | `incomplete_branch` |
| 符号表无匹配 | `unknown_symbol` |
| 词表覆盖不足 | `vocabulary_gap` |
| 全局扫描后无节点可表达 | `no_mapping` |
| 候选词表验证失败 | `vocab_invalid` |
| 未识别写法且未命中别名集 | `unknown_node` |
| `conditional` 前置条件不满足 | `requires_unmet` |
| guards 不满足 | `guard_failed` |

### 10.2 质疑格式

```json
{
  "ambiguity_type": "missing_condition",
  "context_path": "/control/loop/while",
  "block_id": "blk_004",
  "description": "循环终止条件未指定",
  "candidates": [
    "遍历完所有元素",
    "满足某条件时退出",
    "外部信号控制"
  ],
  "impact": "影响循环次数和终止行为",
  "blocking": true,
  "suggested_default": null
}
```

### 10.3 处理流程

```
Jev 抛质疑
  ↓
通用 Agent 尝试补全：
  - 从全局状态推断 → 补全
  - 从接口契约推断 → 补全
  - 从历史块推断 → 补全
  - 补 names 声明（类型 / 长度绑定 / 库绑定） → 补全
  - 从词表工厂生成新词条 → 补全
  ↓ 无法补全
升级人类仲裁（结构化呈现，一键决策）
  ↓
决策回写 → 规则沉淀 → 未来同类不重复问
```

### 10.4 自动补全质疑边界

**结论**：通用 Agent 可补全，但必须生成候选 + 证据 + 置信，交 Jev 验证。

**规则**：

- 低置信、不可逆、跨块副作用 → 升级。
- 补全错误由 Tier1/Tier2 发现。
- 不可逆操作必须阻塞。
- 补全失败回滚最近确认点。
- 自动补全与人类仲裁切换条件：低置信 / 不可逆 / 跨块 / 安全敏感。
- **自动纠偏不得越权**：仅 `confusions` 表中 `action: correct` 的条目可自动改，其余一律报错。

**示例**：循环终止条件缺失，通用 Agent 从契约推断 `i < n`，Jev 验证后使用；若不可逆则阻塞。

### 10.5 质疑去重与批量

- 同一缺口一次会话只提一次。
- 任务期间只记录，任务结束统一汇总。
- 按频率和影响面排序。

---

## 11. 与通用 Agent 的集成

### 11.1 分工

| 层 | 职责 |
|----|------|
| 通用 Agent | 逻辑分解、块序列编排、全局状态、符号宇宙（`names` 块）、接口契约、风格统一、质疑处理、**词表工厂**、**编写 spec DSL 与显式库依赖**、**编译与用例验证** |
| JevAgent | spec 解析与符号挂载、核心节点识别与履约校验、引用合法性校验、库导入闭包与置顶、特化层路由、符号选择、模板填充、块内质疑、**词表语法验证** |

### 11.2 块切分标准

- 一个块 = 一个可独立验证的逻辑单元。
- 块大小 ≤ Jev 上下文窗口的 50%。
- Jev 上下文窗口建议 8k–16k token。
- 块对应一个可测试行为。
- 块间接口显式声明。
- 一个块对应的特化子树应可独立验证（核心履约 + 引用合法性）。
- 块切分半自动：通用 Agent 初切，人类可调。
- **保留块**：`names`（符号宇宙，不产出代码，不参与对齐）与 `imports`（导入区，由工具置顶）。保留块不参与普通块的切分粒度约束，但必须有固定 ID 与固定位置语义。

### 11.3 块间接口契约

```json
{
  "block_id": "blk_003",
  "core_nodes": ["/core/loop/for", "/core/var/declare", "/core/io/output"],
  "requires": {
    "variables": ["数据", "上限"],
    "functions": ["冒泡排序"],
    "libraries": ["math"]
  },
  "provides": {
    "variables": ["结果"],
    "functions": []
  },
  "side_effects": ["write_file:output.txt"],
  "preconditions": ["上限 > 0"],
  "postconditions": ["结果 != None"]
}
```

- 通用 Agent 生成 `requires / provides / side_effects / preconditions / postconditions`。
- Jev 验证符号与路径：`requires` 中的变量与库必须在 `names` 块或上游 `provides` 中声明，否则报错。
- Tier1 验证 pre/post。
- 不一致回滚最近确认点。
- `core_nodes` 与 spec 通过版本向量绑定。

### 11.4 调用协议

通用 Agent 传给 JevAgent 的不再是"块描述（自然语言）"，而是**已经写好的 spec DSL 片段 + 名字表 + 目标语言表 ID**。

```
通用 Agent → JevAgent：
{
  "block_id": "blk_003",
  "spec_text": "对于 i 中的 range(长度 - 1):\n    如果 数据[i] > 数据[i + 1]:\n        设 临时 = 数据[i]",
  "names_block": "# @jev-block:names:begin\n变量 数据: list\n常量 长度 = 0\n# @jev-block:names:end",
  "target_table": "python_v3",
  "symbol_env": { ... }, "style_constraints": { ... },
  "context_window_budget": 2048, "candidate_vocab": null
}
```

```
JevAgent → 通用 Agent：
{
  "block_id": "blk_003",
  "code": "...", "path": [...], "confidence": 0.94, "ambiguities": [...],
  "symbols_used": [...], "symbols_defined": [...],
  "imports": {"declared": [], "auto": ["import math"], "placement": "top"},
  "spec_validation": {"errors": [], "warnings": [], "auto_corrected": [],
                      "coverage": {"rules_applied": [...], "libraries_modeled": [...], "libraries_unmodeled": [...]}},
  "alias_normalization": {"input_nodes": 5, "normalized_nodes": 5, "unknown_nodes": [], "alias_hits": [...]},
  "raw_ratio": 0.0,
  "vocab_validation": null
}
```

---

## 12. 异构交叉检查

### 12.1 原理

- JevAgent：窄而深，结构精确，错法可枚举。
- 通用 Agent：宽而浅，语义强，错法不可枚举。
- 两者失败模式正交 → 分歧信号价值高。

**结论**：必须不同类型/不同能力模型；Jev 判断特化，通用 Agent 语义理解。

**规则**：

- Jev：判断特化模型，不输出规范外词，无幻觉率，但缺长规划。
- 通用 Agent：语义理解模型，长规划强，但天然有幻觉。
- 两者失败模式天然互补。
- Tier2 审查者不能是生成者同一实例。
- 若只有同源模型，退化为同构自审，不能宣称失败模式正交。
- 同构自审必须加确定性检查、规则库、人工抽样。

### 12.2 双向校验

| 方向 | 生成者 | 验证者 | 验证内容 |
|------|--------|--------|----------|
| 代码生成 | JevAgent | 通用 Agent | 语义正确性 |
| 词表生成 | 通用 Agent | JevAgent | 语法正确性 |
| 特化映射生成 | JevAgent | 通用 Agent | 语义等价性 |

### 12.3 检查粒度

- **段级**（不是词级）：一个完整逻辑块审一次。
- **分阶段**：
  - 语义审：原始输入 + spec DSL。
  - 映射审：spec DSL + 生成代码。
  - 路径审：路由路径 + 表结构。
  - 一致性审：核心履约覆盖率、`conditional` 前置是否满足、`raw` 是否被显式标记且计入报告。

### 12.4 分歧归因

| 类型 | 特征 | 处理 |
|------|------|------|
| 逻辑歧义 | 输入模糊 | 澄清 spec |
| 表缺陷 | Jev 受表限制选错 | 修正表 |
| 审查幻觉 | 通用 Agent 过度推理 | 降噪 |
| 词表语法错 | Jev 验证发现 | 修正词表 |
| 特化映射错位 | 核心节点与特化叶子映射不等价 | 修正 `core_conformance` 或下沉节点 |
| 节点名偏差 | 写法命中别名集且语义正确 | 归一为 canonical 并记录；未命中即硬错误，不阻塞式静默通过 |
| 履约声明失实 | 虚标 `supported` 但生成失败 | 改标 `conditional` / `unsupported`，补 `requires` / `reason` |
| 不可归因 | 双方都有道理 | 升级人类 |

### 12.5 仲裁规则

- 结构类分歧 → 倾向 JevAgent。
- 语义类分歧 → 倾向通用 Agent。
- 代码类分歧 → 看沙箱和测试。
- 词表类分歧 → 看 Jev 验证结果。
- 词表语法/结构类 → Jev。
- 词条语义匹配类 → 通用 Agent。
- 不可归因 → 人类仲裁。
- 优先级：安全 > 结构语法 > 语义 > 风格性能。

---

## 13. 审查分层与确认点

### 13.1 分层策略

| Tier | 内容 | 成本 | 触发 |
|------|------|------|------|
| Tier 0 | Jev 置信度 | 零 | 高置信 + 可逆 → 直接过 |
| Tier 1 | 确定性检查（含**编译门槛**） | 零 LLM | 永远开 |
| Tier 2 | 通用 Agent 审查 | 中 | 中低置信 / 不可逆 / 目标语言切换 |
| Tier 3 | 人类仲裁 | 高 | Tier 2 分歧 |

### 13.2 编译门槛（Tier 1 硬性项）

**结论**：生成产物必须过真实工具链，编译门槛是 Tier 1 的一部分，**每期必须全绿**。

**规则**：

- 工具负责生成，**编译由通用 Agent 执行**；以下三项为 CI 级门槛，退出码必须为 0：

```powershell
& $gcc -Wall -Wextra -c out.c -o out.o      # C 产物
& $py  -m py_compile out.py                 # Python 产物
& $bash -n out.sh                           # Shell 产物
```

- C 产物须过 `gcc -Wall -c`（建议加 `-Wextra`）。
- Python 产物须过 `py_compile`。
- Shell 产物须过 `bash -n`。
- 编译门槛与核心履约联动：`conditional` 声明若生成出非法代码，视为履约声明失实，须改声明并有对应用例。
- 编译门槛不替代用例测试；编译通过 ≠ 逻辑正确。

**示例**：曾实测到的失败态——C 产物因缺 `#include` 报 `implicit declaration of 'printf'`；shell 产物因缺闭合符号报 `syntax error: unexpected end of file`（退出码 2）。两者均属编译门槛该拦下的失败。

### 13.3 阻塞规则

- **可逆操作**（生成代码、写 spec）→ 非阻塞，异步审查。
- **不可逆操作**（执行 shell、写文件、网络请求、数据库修改）→ 阻塞，审查通过才落地。

### 13.4 可逆 / 不可逆判定

**结论**：按执行动作判定，不按生成物。

**规则**：

- 生成代码/spec/命令文本：可逆，非阻塞。
- 实际写文件：不可逆/半不可逆，阻塞。
- 实际执行 shell：不可逆，阻塞。
- 网络请求代码：可逆。
- 实际网络请求：不可逆，阻塞。
- 数据库修改：不可逆，阻塞。
- 边界模糊默认阻塞。
- 由编排层策略引擎判定。

**示例**：生成 `tar -czf` 命令可逆；实际执行 `tar` 阻塞审查。

### 13.5 确认点队列

```
Jev 生成块 → 入队
  ↓
Tier 1 检查通过（含编译门槛） → 标记确认点
  ↓
Tier 2 异步审查
  ↓
审查通过 → 确认点升级
审查分歧 → 回滚到最近确认点
```

### 13.6 确认点回滚范围

**结论**：回滚确认点版本向量覆盖的全部状态。

**规则**：

- 回滚：代码、spec、名字表快照、动态节点、块间契约、缓存键、审查状态。
- 不回滚：已发布词表/路由表版本，只切换引用。
- 不可逆副作用已执行，记录补偿。
- 所有状态通过确认点版本向量绑定。
- 多状态一致性以确认点为准。

**示例**：回滚到 `blk_002`，`blk_003` 生成的代码、spec、符号、动态节点、契约一起回退。

### 13.7 抽样策略

**结论**：每 100 块或每日校准。

**规则**：

- 高置信抽样，中低全审。
- 校准不准时提高抽样率。
- 错误率反馈周期 1 天/100 块。
- 避免滞后：在线校准 + 滑动窗口。
- 高置信段：按比例抽样。
- 中置信段：全审。
- 低置信段：全审 + 加严。
- 不可逆段：全审 + 阻塞。
- 抽样比例根据历史错误率动态调整。

---

## 14. 沙箱与安全

### 14.1 白名单机制

- 允许的命令、参数模式、路径前缀、网络目标。
- 变量替换先冻结或限制在受控集合。
- AST 级解析，不只看字符串。
- 安全团队定义，AST + 白名单 + 沙箱三层。

### 14.2 危险领域检测

- 不是黑名单（`rm -rf`、`curl | sh`）。
- 是能力白名单（能做什么，不能做什么）。
- 命令替换、`eval`、编码、环境变量、`bash -c`、`find -exec`、`xargs` 全部纳入检查。

### 14.3 执行前检查链

```
Jev 输出 → AST 解析 → 白名单检查 → 沙箱试运行 → 正式执行
```

- AST 解析每种目标语言实现。
- 变量替换不确定时拒绝执行或沙箱试运行。
- Shell 组合空间大，白名单 + AST + 沙箱三层覆盖。
- 危险能力白名单，不是黑名单。

**示例**：`rm -rf` 不在能力白名单，直接拒绝。

---

## 16. 跨语言转换：复制 + 定点处理

> 说明：本节编号沿用原稿。原第 15 节整节已删除，编号不再连续。

### 16.1 原则

**结论**：跨语言迁移的正确形态是**复制 + 定点处理**，不是"重新翻译一遍"。

| 操作 | 幻觉风险 |
|------|----------|
| **复制**已有块内容 | **零**（逐字节搬运，不经过模型生成） |
| **重新生成**同一逻辑 | **高**（模型每写一行都有编造符号/写错 API 的机会） |

通用关键字核的收益不止于降低人类上手门槛——它让**逻辑相同的部分可以大段复制**，AI 只需处理逻辑不同的地方。改动面被压到最小，而**最小改动面本身就是最低幻觉面**。

### 16.2 流程

```
源语言 spec + 源语言代码
  ↓ 源语言表识别侧（code_to_spec 反解，保真优先）
源语言 spec DSL（唯一真相源）
  ↓ 块级迁移分类（可静态计算）
verbatim / partial / rewrite
  ↓ verbatim → 逐字节复制（不经模型）
  ↓ partial  → 复制 + 处理标注的前置条件
  ↓ rewrite  → 仅对这些块调用生成能力
目标语言 spec
  ↓ spec_to_code + 校验防火墙 + 编译门槛
目标语言代码
```

### 16.3 块级迁移分类

**规则**：分类必须**可静态计算**，由核心履约状态与节点来源决定。

| 分类 | 判定条件 | 迁移动作 |
|------|----------|----------|
| `verbatim` | 块内全部节点属核心核，且目标语言履约均为 `supported` | **逐字节复制**，零审阅，**禁止重新生成** |
| `partial` | 含 `conditional` 节点 | 复制 + 标注需确认的前置条件 |
| `rewrite` | 含库节点 / `unsupported` 节点 / raw 块 | 必须重写；工具产出差异清单 |

**护栏**：

- `verbatim` 判定要求**全部节点 `supported`**；任一 `conditional`、库节点或 raw 即降级为 `partial` / `rewrite`。
- `verbatim` 块跨语言复制后必须逐字节一致（有对应用例）。
- 对 `verbatim` 块重新生成即为违规，须在评审中拦下。

### 16.4 迁移报告即差异报告

因库与逻辑强耦合，`spec_to_spec` **必须产出迁移报告**，禁止静默转换：

```
迁移报告内容：
  - 逐块迁移分类（verbatim / partial / rewrite）与判定依据
  - 逐块列出目标语言无对应物的节点
  - 需替换的库调用（及建议替代）
  - 语义有损点（如 pandas 链式调用 → 需手写循环）
  - 需满足的 conditional 前置条件（缺什么、怎么补）
  - 无法自动处理的块 → 保留占位 + 显式 TODO 标记（禁止静默降级）
  - raw 块清单与占比
```

AI 的注意力与 token 全部集中在 `rewrite` 块上；`verbatim` 块不需要 AI 关注，`partial` 只需确认前置。

### 16.5 禁止事项

- **禁止对 `verbatim` 块重新生成**。
- **禁止静默降级**：无法转换的内容必须显式标记为 TODO 占位并计入报告。
- 禁止以"差不多等价"为由改写库调用；库差异必须显式列出。
- 转换结果必须重新过校验防火墙与编译门槛，不得继承源语言的校验结论。

### 16.6 给 AI 的操作约定

```
跨语言迁移时：
  1. 先取迁移分类
  2. verbatim 块 → 原样复制，不要重新生成
  3. partial 块 → 复制后处理标注的前置条件
  4. rewrite 块 → 仅对这些块调用生成能力
```

### 16.7 跨表一致性

- 骨架规范版本化，所有表引用。
- 加表时跑骨架一致性检查（`check_tables`）。
- 核心表为闭集，新增核心节点需评审。
- 覆盖率矩阵随表版本更新，作为正式交付物。
- 语言表漂移必须由 `check_tables` 检出，不能只靠约定。

---

## 17. 人类仲裁

### 17.1 原则

- 人类只处理分歧，不处理流程。
- 工作量 O(分歧数)，非 O(任务量)。
- 分歧率随系统成熟持续下降。

### 17.2 分歧排序

| 影响 \ 歧义 | 高 | 低 |
|-------------|-----|-----|
| 高 | 优先 + 详细展示 | 快速确认 |
| 低 | 批量处理 / 默认 | 自动解决 |

### 17.3 呈现方式

- 只展示分歧点，不展示完整路径。
- 并排对比：Jev 选什么 / 通用 Agent 选什么 / 各自理由。
- 最小上下文。
- 一键决策：A / B / 都不对 / 需要更多信息。
- 结论：并排 A/B，一键决策，规则回写各表。
- 高影响/低歧义默认 + 快速确认。

### 17.4 决策回写

- 同类分歧自动消解。
- 表优化信号。
- spec 澄清信号。
- 词表优化信号。
- 规则沉淀。
- 规则回写各表，人工审批。

### 17.5 规则沉淀

**结论**：沉淀到各表，分散动态进化，不建集中规则库。

**规则**：

- 分歧归因到表缺陷：路由表、词表、模板表、对话表、映射表、审查表。
- 每次分歧是消除表构建缺陷的机会。
- 修补对应表，版本化。
- 回归测试防止过拟合。
- 高频/高影响分歧才沉淀；保留例外。
- 后续同类歧义应减少。

**示例**：同类循环歧义出现三次，补 `/control/loop/while` 的 guards/notes，而不是写通用规则。

---

## 18. 版本绑定、缓存、成本与统计

### 18.1 版本绑定与缓存失效

**结论**：统一 manifest 绑定所有版本。

**规则**：

- manifest 包含：skeleton、table、vocab、mapping、required_imports、symbol_snapshot、code_commit、spec_commit。
- 二文件模型下 `spec_commit` 仅覆盖 spec 单一文件，不再包含多文件层间项。
- 缓存键包含 manifest。
- 跨会话缓存按版本向量失效。
- 相似任务判定基于 manifest + 意图指纹。

**示例**：词表升到 `common_v3`，旧缓存自动失效。

### 18.2 成本模型

**结论**：分阶段成立，总成本需低于直接人工。

**规则**：

- 可逆操作异步审查，延迟秒级。
- 不可逆操作阻塞，延迟人工。
- 初期人类仲裁工作量高，后期下降。
- 若总成本高于人工，降级 Tier2/Tier3。
- 可接受延迟按操作类型分级。

### 18.3 通用 Agent 幻觉率统计

**结论**：按三类指标统计，超过阈值降级。

**规则**：

- `unknown_node`（未识别且未命中别名集）<2%。
- 别名归一命中率 <5%。
- 语义歧义（映射候选多解）<10%。
- 超过则：更小候选集、更多 Jev 验证、人工抽样、别名集/`confusions` 评审。
- 统计频率：每任务/每日。
- 覆盖率必须如实统计：符号级通过 ≠ 逻辑正确。

---

## 19. 目录结构建议

```
jevagent/
├── core/
│   ├── router.py          # 树形路由引擎（核心节点优先解析）
│   ├── jev_client.py      # Jev API 封装
│   ├── symbol_table.py    # 符号表（以 names 块为权威源）
│   ├── template.py        # 模板填充（含 core_operators 转换）
│   ├── validator.py       # 校验防火墙（引用合法性规则引擎）
│   ├── splitter.py        # 块切分 + 块类别识别 + 置顶组装
│   ├── importer.py        # 库导入闭包 / 去重 / 回写 spec
│   └── three-file.py      # 二文件路径解析、对齐检查、备份回滚
├── tables/
│   ├── syntax_core_v1.json  # 通用关键字核（语言无关，闭集）
│   ├── skeleton_v1.json     # 骨架规范（各语言骨架）
│   ├── python_v3.json       # Python 表（core_conformance / required_imports / confusions / aliases）
│   ├── shell_v2.json        # Shell 表
│   ├── c_v1.json            # C 表
│   ├── semantic_v1.json     # 内部路由中间层节点（非用户可写）
│   └── ...
├── vocab/
│   ├── common.json        # 通用词表
│   ├── shell.json         # Shell 词表
│   ├── dialog.json        # 对话表
│   ├── factory.py         # 词表工厂
│   └── validator.py       # Jev 词表验证
├── dsl/
│   ├── parser.py          # spec DSL 解析
│   ├── emitter.py         # spec DSL 生成
│   ├── names.py           # names 块解析与模块级挂载
│   ├── migration.py       # 迁移分类与迁移报告
│   └── roundtrip_test.py  # 往返测试
├── review/
│   ├── tier1_checker.py   # 确定性检查 + 编译门槛
│   ├── tier2_reviewer.py  # 通用 Agent 审查
│   ├── divergence.py      # 分歧归因
│   └── arbitration.py     # 人类仲裁接口
├── sandbox/
│   ├── ast_parser.py      # AST 解析
│   ├── whitelist.py       # 白名单
│   └── runner.py          # 沙箱执行
├── orchestrator/
│   ├── block_splitter.py  # 块切分
│   ├── contract.py        # 接口契约
│   └── composer.py        # 块组合
└── tests/
    ├── golden/            # 黄金样例
    ├── roundtrip/         # 往返测试
    ├── compile_gate/      # 编译门槛（gcc -Wall -c / py_compile / bash -n）
    ├── core_matrix/       # 语言 × 核心节点覆盖率矩阵
    └── migration/         # verbatim 逐字节复制与迁移报告用例
```

---

## 20. 实现路线图

**结论**：按 P0~P5 分期推进；P5 建议与 P0 同步建立，最迟不晚于 P1。

> 理由：P1 要改三张语言表，**先有 `check_tables` 才能防止边改边漂**。

### P0：移除语义抽象层 + 二文件模型打通 + 骨架落地 + C 闭包导入

- [ ] 工具动作收窄：旧的可写抽象层文件及其两个互转动作退役（动作枚举、工具 schema、`translate_block` 方向同步收窄）
- [ ] 二文件模型打通：`<module>.spec.<lang>.dsl` + `<module>.<ext>`，`check_alignment` 语义改为二文件
- [ ] 骨架落地：读取语言表 `skeleton_ref` 并**实际应用**（C：头部注释 + 基础 `#include` + 可选 `main()` 框架）
- [ ] C 闭包导入：`symbol-table` 加厚（完整标识符扫描 + 字符串/注释剔除 + 关键字黑名单 + `referenced` 字段）
- [ ] C 的 `io/output` 按类型解析格式符（作者侧统一 `输出(表达式)`）
- [ ] 块类别识别（`emitting` / `declaration-only` / `hoisted`）——**须先于 P4 落地**
- [ ] 重写注入的系统提示词指导（当前仍教多文件模型）

**验收**：C 产物无需手工补丁即可通过 `gcc -Wall -c`，且 `输出整数(...)` 生成 `printf("%d\n", ...)`、`-Wformat` 无警告；工具 schema 中不再出现互转动作；既有 Python 产物与基线逐行一致；排序用例全通过。

### P1：正向导入分支

- [ ] spec 导入语法：`引入 math` / `引入 numpy 作为 np` / `从 math 引入 sqrt, pi` / `引入系统 stdio.h` / `引入本地 util.h` / `引入 ./lib/common.sh`
- [ ] 三语言 import 节点（`placement: "imports"`）
- [ ] 保留块 `imports`：置顶（spec 与 code 一致执行）、缺失自动创建并回写、多块合并
- [ ] 闭包算法：显式 ∪ 推导、按规范化 key 去重、排序、**回写 spec**（自动项标 `origin:auto`）
- [ ] `spec_to_code` 幂等

**验收**：`引入 math` → Python `import math` 位于首个非注释行之前；`引入系统 stdio.h` → C `#include <stdio.h>` 位于首次使用之前；同一依赖声明两次只生成一条；显式与自动重复合并为一条且标 `origin:declared`；连续两次生成产物字节一致。

### P2：逆向分支

- [ ] 自由区导入收纳：扫描首个块之前的自由区（C 含 `#define` / `#include` 段）
- [ ] 各语言导入识别正则与反解，物化为 `@jev-block:imports` 块（保持原顺序）
- [ ] 反查 `required_imports`：命中 → `origin:auto`；否则 → `origin:declared`
- [ ] `code_to_spec` 首次导入时**自动生成 `names` 块**
- [ ] 逐行补 `# node:/<lang>/module/...` 注解

**验收**：手写 `import os` / `#include <stdio.h>` → spec 有正确注解与 origin；`origin:auto` 不产生新的作者声明行；往返（code → spec → code）导入内容与位置幂等。

### P3：生成完整性补全 + `spec_to_spec` + 迁移报告

- [ ] shell 路径补全：闭合符号（`}` / `done` / `fi`）、`设` 关键字翻译、条件转换、补 `/shell/function/call` 节点
- [ ] `spec_to_spec`：跨语言转换（替代"一源多目标"）
- [ ] 迁移报告：逐块分类 + 差异清单 + 语义有损点 + TODO 占位
- [ ] `spec_export`（可选）：剥离 `node:` 注解的只读导出，**禁止作为编辑入口**

**验收**：shell 产物通过 `bash -n`；跨语言转换产出带风险披露的报告而非静默转换。

### P4：语言绑定容错层 + 校验防火墙

- [ ] `names` 块解析、模块级挂载、纯函数化、失效重挂、冲突校验
- [ ] `lib/validator.js`（新增）：引用合法性、闭包完整性、类型/签名（可选）、`confusions` 纠偏；输出结构化报告
- [ ] router 兜底反转：未识别 → 硬错误（附最近候选建议），编辑距离只给建议
- [ ] 逃生舱显式化：原生透传必须显式标记，未标记却无法解析 → 报错
- [ ] `confusions` 表（闭集）+ 档 B 自动纠偏（仅 `action: correct`，且必须在报告中可见）
- [ ] 新增 action `check_spec`：不生成代码，仅做引用合法性校验，供 Agent 预检与 CI 调用
- [ ] `spec_to_code` 内部接入同一套校验规则（校验 → 有 error 拒绝产出）

**验收**：未声明库/变量 → 硬错误，报告含行号、块 ID、最近候选建议；跨语言误写自动纠偏且报告明确列出；未标记却无法解析的行报错而非静默走 raw；必需导入缺失 → 报错并给出应补的导入；`check_spec` 与 `spec_to_code` 判定一致；报告含覆盖率字段；缺陷拦截对照表中标记为可拦的 7 项各有用例并通过。

### P5：通用关键字核与跨语言一致性

- [ ] 新增 `tables/syntax_core_v1.json`：`core_nodes` + `core_operators`（闭集）
- [ ] 各语言表新增 `core_conformance` 段；补齐缺失核心节点
- [ ] 新增 action `check_tables`（或并入 `validate_vocab`）：逐语言校验履约完整性
- [ ] 交付物：**语言 × 核心节点覆盖率矩阵**
- [ ] `KEYWORD_MAP` 由 `syntax_core_v1.json` 驱动，消除双真相源
- [ ] `core_operators` 参与表达式转换（shell `<=` → `-le` 等）
- [ ] 迁移分类与 AI 操作约定写入注入的系统提示词指导

**验收**：覆盖率矩阵校验通过（三语言表对全部核心节点均有履约声明，`unsupported` 均附理由）；C 侧 `对于` 标 `conditional`，未提供长度绑定时硬错误并说明缺什么，提供后生成正确循环；shell 侧 `当 i <= 上限:` 生成 `while [ "$i" -le "$上限" ]; do` 且 `bash -n` 通过；同一算法在 Python 与 C 的 spec 中核心节点部分逐行相同；`verbatim` 块跨语言复制后逐字节一致；`check_tables` 能检出人为制造的漂移。

### 后续（持续）

- [ ] 路径缓存 / 热路径宏
- [ ] 抽样策略动态调整
- [ ] 规则沉淀自动化
- [ ] 分歧日志分析
- [ ] 词表工厂自动化
- [ ] idiom 表（numpy / pandas 向量化与链式调用）
- [ ] 形式化关键子集验证

---

## 21. 关键风险与对策

| 风险 | 对策 |
|------|------|
| **core 被往上推成语义抽象层（重演旧路线失败）** | §5.1.3 护栏写死：core 只统一词汇/语法/运算符；语义差异必须显式标 `conditional` / `unsupported` |
| **为凑齐覆盖率而虚假声明 `supported`** | `conditional` 必附 `requires`、`unsupported` 必附 `reason`；前置不满足时硬错误，无法蒙混；编译门槛兜底 |
| **`verbatim` 误判（该重写的被判成可复制）** | `verbatim` 要求全部节点 `supported`；任一 `conditional` / 库节点 / raw 即降级为 `partial` / `rewrite` |
| **校验通过被误读为正确** | 三条护栏（覆盖率如实标注、不得静默通过、不取代编译与用例测试）+ 边界写入 README |
| **逃生舱隐式化（整层都成逃生舱）** | 原生透传必须显式标记且可 grep；未标记却无法解析 → 报错；raw 必须计入报告 |
| **自动纠偏退化为"猜"** | 别名集为闭集 + 未命中硬错误；`confusions` 仅 `action: correct` 自动改并计入报告；编辑距离只给建议 |
| **路由被污染** | 模块级作用域 + 纯函数挂载 + 可复现性单测 |
| **名字表与代码漂移** | `code_to_spec` 自动生成 + 校验（代码里出现但表里没有的外部名 → 警告） |
| **又造一个格式变体层** | 不新增文件，演化 spec DSL（判据：是否承载另一层无法承载的信息） |
| **置顶导致对齐检查失衡** | spec 与 code 一致执行置顶；闭包结果回写 spec；`declaration-only` 块不参与对齐 |
| **语言表漂移** | `check_tables` 覆盖率矩阵校验；核心表为闭集，新增需评审 |
| **运算符映射不完备导致生成非法代码** | 运算符核纳入编译门槛（C `gcc -Wall -c` / Shell `bash -n`）覆盖 |
| 路由表爆炸 | 声明式 DSL + BNF 自动生成骨架 |
| 长尾歧义 | 低置信 top-k + 回退 |
| 错误传播 | 每层可回滚 + 确认点 |
| 通用 Agent 幻觉 | Jev 树约束 + 异构交叉 + 生成前防火墙 |
| 审查成本高 | 分层 + 抽样 + 异步 |
| 人类分歧疲劳 | 去重 + 规则沉淀 + 排序 |
| 表骨架漂移 | 骨架规范版本化 + 一致性检查 |
| DSL 往返不稳 | 黄金样例 + 保留块机制 + 不可提取节点保留 |
| 动态符号表污染 | 作用域隔离 + 模块级挂载 + 退出卸载 |
| 词表工厂失控 | Jev 验证 + 回归测试 + 版本化 |
| 词表冲突 | 显式覆盖 + 碰撞检测 |
| 特化层表爆炸 | 按语言独立维护；核心核减少重复 |
| Jev 路由置信度衰减 | 映射优先查表；块大小约束；低置信回退 |
| 一致性校验成本高 | 覆盖率矩阵自动化；Tier 1 确定性检查优先 |
| **`raw` 节点滥用** | 逃生舱必须显式标记且可 grep；统计 `raw` 占比；>10% 触发词表工厂/特化映射，>30% 阻塞 |
| 多语言映射冲突 | 显式声明覆盖；Jev 验证映射合法性 |
| 通用 Agent 幻觉过多 | 防火墙拦截 + 别名集/`confusions` 评审 + 词表工厂补全 |
| 别名归一累积 | 归一必须可见；命中率超阈值触发别名集评审而非扩大自动纠偏 |
| 误报过多导致 Agent 绕行 | 原生透传必须显式标记并计入报告，使"绕行"可见而非隐形 |

---

## 22. 核心设计原则

1. **封闭集合**：词表、模板表、对话表任务期间不可变，保证可验证性。
2. **二文件模型**：`spec` 是唯一真相源，`code` 是生成产物；对齐检查的语义据此收敛。
3. **库导入由工具保证**：隐含必需导入走闭包，显式依赖由 Agent 声明，`imports` 块置顶且回写 spec。
4. **块类别显式**：`emitting` / `declaration-only` / `hoisted`；`names` 不产出代码、不参与对齐。
5. **符号宇宙显式声明**：`names` 块是符号的权威源，按模块挂载、纯函数、不泄漏。
6. **未知即错误**：未识别写法一律硬错误（附最近候选建议），禁止静默落到 raw。
7. **逃生舱必须显式且可 grep**：隐式逃生舱等于没有防火墙。
8. **容错有限且可见**：别名集为闭集；`confusions` 仅档 B 自动纠偏，且必须在报告中列出。
9. **动态符号**：代码中新增的定义实时挂载到路由表，避免兜底编造。
10. **双向校验**：Jev 生成代码 → 通用 Agent 审语义；通用 Agent 生成词表 → Jev 审语法；Jev 做特化映射 → 通用 Agent 审语义等价。
11. **结构约束幻觉**：Jev 只做选择，不做生成，错误空间可枚举。
12. **异构交叉**：窄而深 + 宽而浅，失败模式正交，分歧信号价值高。异构要求不同类型模型；同源则退化为同构自审。
13. **人类仲裁最小化**：只处理分歧点，工作量随系统成熟下降。
14. **可逆非阻塞，不可逆阻塞**：审查策略按可逆性分，不按风险分；可逆按执行动作判定。
15. **块内自治，块间契约**：Jev 只管块内，通用 Agent 管块间。
16. **骨架共享，叶子分化**：跨语言共性靠共享骨架与核心核，落地靠各表叶子。
17. **分歧驱动改进**：分歧日志是表优化、spec 澄清、词表优化的信号源。
18. **词表可工厂化**：通用 Agent 写，Jev 验，人审批；仅任务前生效。
19. **core 只统一词汇、语法、运算符**：语义差异与库差异显式标注，禁止粉饰。
20. **三条腿立身**：**可追溯**（`node:` 注解）、**可校验**（校验防火墙）、**可迁移**（通用关键字核）。
21. **职责对齐能力**：通用 Agent 写 spec（语义强），Jev 校验与路由（结构强），失败模式正交。
22. **幻觉分流**：未知阻塞、别名命中归一且可见、语义歧义走 Score 或质疑。
23. **特化层是一等公民**：语言特有语法不是兜底，而是完整可测试的独立子树。
24. **映射优先于推断**：能查表就不走 Jev Choice；推断结果必须 Tier2 审。
25. **raw 节点是安全阀**：不可提取部分显式标记，计入报告，不参与一致性校验。
26. **复制优先于重生**：迁移时 `verbatim` 块逐字节复制，禁止重新生成。
27. **编译门槛不可绕过**：C 过 `gcc -Wall -c`，Python 过 `py_compile`，Shell 过 `bash -n`。
28. **Jev 只做判断**：做节点识别、履约校验、引用合法性校验与语法补全选择，不生成新逻辑。
29. **规则沉淀分散在各表**：不建集中规则库，修补对应表并版本化。
30. **版本向量统一绑定**：代码、spec、名字表、动态节点、契约、表版本、缓存键通过确认点版本向量绑定。
31. **路由表 schema 冻结**：任务期间不可变；`/dynamic` 独立运行期层；结构封闭、实例动态。
32. **不取代编译与用例测试**：防火墙只做生成前的引用合法性拦截。

---

## 23. 已冻结结论与后续优化项

### 23.1 已冻结结论

- DSL 形态：**二文件模型**（`<module>.spec.<lang>.dsl` + `<module>.<ext>`）；语言绑定，不做跨语言归一；库名/变量名/常量照抄代码形态。
- 常量口径：canonical 为 `True/False/None`，`真/假/空` 保留为**输入别名**，输出只出 canonical。
- 块类别：`emitting` / `declaration-only` / `hoisted`；块类别须先于容错层落地。
- 保留块：`names`（符号宇宙，不产出代码、不参与对齐）、`imports`（置顶、缺失自动创建、去重、回写 spec）。
- 库导入：隐含必需导入由工具闭包保证；显式依赖由 Agent 声明；`origin:auto` 逆向不产生作者声明；闭包只从表白名单推导。
- 容错口径：**未知即错误**；逃生舱必须显式标记且可 grep；自动纠偏仅限 `confusions` 表 `action: correct`（档 B）且必须可见。
- 核心核：`syntax_core_v1` 为**闭集**；履约三档 `supported` / `conditional`（附 `requires`）/ `unsupported`（附 `reason`）；覆盖率矩阵为正式交付物。
- 防火墙边界：守**引用合法性**，不守**逻辑正确性**；三条护栏（覆盖率如实标注、不得静默通过、不取代编译与用例测试）。
- 跨语言迁移：**复制 + 定点处理**；块级分类 `verbatim` / `partial` / `rewrite`；迁移报告即差异报告；禁止静默降级。
- 编译门槛：C 过 `gcc -Wall -c`、Python 过 `py_compile`、Shell 过 `bash -n`，每期全绿。
- 动态符号表粒度：变量级、函数签名、类型级；不挂表达式级。
- 块切分自动化程度：半自动，通用 Agent 初切，人类可调。
- 多表选择粗筛机制：关键词 + 嵌入粗筛，Jev 精判。
- 跨语言差异标注：notes/guards 由语言表维护者写，Jev schema 验证，通用 Agent 语义审。
- 人类仲裁界面：并排 A/B，一键决策，只展示分歧点。
- 词表工厂触发：任务前预判、用户请求、上一任务缺口记录；仅任务前生效，半自动生成 + Jev 验证 + 人审批。
- 词表验证失败回退：拒绝合并；可部分合并；严重人工介入；当前任务不热补丁，使用已有兜底词表或抛质疑。
- 特化映射：静态声明优先，Jev 推断仅 fallback 且须 Tier2 审。
- 异构交叉：必须不同类型/不同能力模型；同源退化为同构自审。
- 仲裁优先级：安全 > 结构语法 > 语义 > 风格性能。
- 自动补全边界：通用 Agent 可补全，但必须候选 + 证据 + 置信，交 Jev 验证；低置信、不可逆、跨块、安全敏感升级。
- 规则沉淀：分散到各表，不建集中规则库。
- 沙箱白名单：安全团队定义，AST + 白名单 + 沙箱三层。
- 成本模型：可逆异步，不可逆阻塞；总成本需低于直接人工。
- 版本绑定：统一 manifest 绑定 skeleton、table、vocab、mapping、required_imports、symbol_snapshot、code_commit、spec_commit。
- 抽样策略：每 100 块或每日校准，在线校准 + 滑动窗口。
- raw 节点控制：>10% 触发词表工厂/特化映射，>30% 阻塞新任务；必须显式标记且计入报告。
- 统计阈值：`unknown_node` <2%，别名归一命中率 <5%，语义歧义 <10%。

### 23.2 后续优化项（不阻塞落地）

- 形式化等价性验证覆盖关键子集的程度。
- 特化层 `guards` 的验证责任归属在具体语言表中的细化。
- `conditional.requires` 的可判定性边界（哪些前置必须机器可判）。
- 别名集与 `confusions` 表的维护责任划分（人工闭集 vs Agent 就地补充）。
- 通用 Agent 审查 prompt 模板的具体设计。
- 分歧归因的自动化程度提升。
- 词表工厂自动合并的低风险阈值调优。
- 多语言共享核心节点时的版本同步机制优化。
- `raw` 节点跨语言转换策略的进一步细化。
- idiom 表首批范围（numpy / pandas）的取舍。

### 23.3 遗留待定

| # | 问题 |
|---|---|
| Q1 | `spec_export`（剥离注解的只读导出）是否要做？ |
| Q2 | P3 的 idiom 表首批范围：仅 numpy，还是 numpy + pandas？ |
| Q3 | C 的 `main()` 由骨架自动生成，还是要求 Agent 显式写块？ |
| Q4 | 复杂原生导入（多行 `from x import (...)`）走 raw 透传是否可接受，或需专门支持？ |
| Q5 | `names` 表粒度：只声明**外部库 + 常量**，还是连**局部变量与函数签名**也纳入？ |
| Q6 | 节点**别名集**由谁维护：人工闭集（可控、可测），还是允许 Agent 写模块时就地补充（灵活，但削弱"输出唯一"）？ |
| Q7 | `confusions` 表初始收录范围？（建议首批只收 `print/printf` 一类确定的一对一误写） |

---

## 24. 最终口径声明

> **路由表 schema 冻结；`/dynamic` 是独立运行期层；动态节点结构封闭、实例动态；词表工厂仅任务前生效；二文件模型为唯一真相源；库导入由工具闭包保证、显式依赖由 Agent 声明；块类别三分且须先于容错层落地；未知即错误、禁止静默走 raw；逃生舱必须显式标记且可 grep；核心表 `syntax_core_v1` 为闭集且只统一词汇、语法、运算符；履约三档 `supported` / `conditional` / `unsupported`，`conditional` 前置不满足即硬错误；特化映射静态优先；回滚按确认点版本向量；可逆按执行动作判定；词表语法 Jev 审、词条语义通用 Agent 审；异构要求不同类型模型；规则沉淀分散在各表；跨语言迁移采用复制 + 定点处理，`verbatim` 块禁止重新生成；编译门槛每期全绿；特化层是一等公民；raw 是安全阀。**

本稿自发布起作为《JevAgent 设计稿 v0.2》《JevAgent 设计稿补充：跨语言分层语义与底层特化 v0.1》《JevAgent 设计稿：逻辑歧义消除补充稿 v1.0》经《JevAgent 重构方案：二文件模型与库导入层》修订后的联合定修稿。后续实现、评审、实验、产品化均以本 V2.0 为准。

> 经过实践检验发现高层语义方案完全不可行，因为不同语言之间的细节逻辑本就不同，强行抹平反而问题更大。



