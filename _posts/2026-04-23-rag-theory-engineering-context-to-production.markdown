---
title: "RAG理论与工程落地：从 Context Engineering 到生产部署"
date: 2026-04-23 19:00:00 +0800
description: 基于 Context Engineering 框架，系统展开 Plain/Hybrid RAG、Agentic/Reflective RAG、GraphRAG 与 LightRAG，并覆盖复杂文档 ingestion、评估闭环与生产部署。
tags: [RAG, LLM, Context Engineering, GraphRAG, Agentic RAG]
categories: [Tech]
---

# 第 1 章 从 Prompt Engineering 到 Context Engineering

## 1. 本章要解决的问题

今天讨论 RAG，如果还把问题定义成“给大模型外挂一个向量库”，很快就会陷入两个误区。

第一个误区是把效果问题都归因于模型能力不够。实际工程里，大量失败并不是模型不会答，而是系统把错误的上下文、过量的上下文、过期的上下文，或者根本不该一起出现的上下文塞进了同一次推理。

第二个误区是把优化空间都放在 prompt 文案上。Prompt 当然重要，但在多轮、长时程、带工具、带外部知识的系统里，决定结果的已经不是单条提示词，而是整个上下文系统的装配方式。

因此，本章真正要解决的问题是：如何把“写好提示词”的思路，升级成“设计好上下文系统”的思路，并为后续三条主路线建立统一坐标系。

判断一个团队是否已经进入 Context Engineering 阶段，不看它有没有用“智能体”这个词，而看它是否开始系统性回答下面四个问题：

1. 哪些信息应该在推理前固定注入，哪些应该运行时按需获取。
2. 哪些信息应该长期保存在外部系统里，而不是始终占据上下文窗口。
3. 工具、记忆、检索、对话历史之间的职责边界是什么。
4. 当上下文预算有限时，系统如何优先保留高信号 token，而不是无差别堆料。

## 2. 为什么这个问题在今天重要

Anthropic 在 2025 年 9 月 29 日发布的《Effective context engineering for AI agents》把 context engineering 明确表述为 prompt engineering 的自然延伸。这个表述重要，不是因为换了一个更新的名词，而是因为它准确描述了当下系统边界的变化：系统指令、工具定义、外部数据、消息历史、记忆文件，已经共同决定模型行为。

这件事在今天尤其重要，有三个原因。

第一，长上下文不是免费午餐。上下文窗口变大，意味着可以放更多信息，但不意味着应该放更多信息。Anthropic 在同一篇文章里强调，context 是关键但有限的资源。窗口越长，模型越容易出现注意力稀释、焦点漂移和相关信息淹没的问题。能塞进去，不等于该塞进去。

第二，企业知识已经不再是一个单纯的“文档检索问题”。真实系统里同时存在制度文档、FAQ、代码仓、工单、报表、网页、图片、权限边界和历史对话。把这些全部视为“待向量化文本”，本身就是错误抽象。很多系统失败，不是因为 embedding 不够好，而是因为知识形态和上下文装配策略不匹配。

第三，托管检索能力和 agentic runtime 能力都在快速成熟。OpenAI 当前的 Retrieval / File Search 已经把“解析、切块、索引、搜索”做成托管能力；Anthropic 则把 runtime context retrieval、compaction、note-taking、hybrid autonomy 作为 agent 架构的一部分来讨论。这意味着工程重点正在从“怎么手写每个组件”，转向“如何决定何时使用哪类上下文机制”。

这也是本书的出发点：不是教你如何把一套旧式 RAG 配方套到所有问题上，而是先回答一个更高层的问题，什么样的任务，需要什么样的上下文系统。

## 3. 核心概念与理论

### 3.1 Context Engineering 的定义

本书采用如下定义：

> Context Engineering 是围绕一次或一系列模型推理，持续设计、裁剪、装配、维护上下文状态的工程实践。

这个定义有四个关键词。

第一是“持续”。Prompt engineering 更像一次性编写说明书；context engineering 则是每次推理都要重新决定什么该带入、什么该舍弃、什么应延后加载。

第二是“状态”。上下文不是一段提示词，而是一次推理时模型可见的全部状态。

第三是“装配”。上下文并非天然存在，而是系统按策略拼装出来的。

第四是“维护”。上下文会老化、膨胀、冲突、重复，因此必须被压缩、更新和清洗。

### 3.2 上下文系统的四层结构

为了避免概念漂移，本书统一把上下文系统拆成四层。

| 层级 | 组成 | 作用 | 典型问题 |
|------|------|------|----------|
| 静态约束层 | system instructions、角色边界、输出格式、合规要求 | 规定模型该如何行动 | 规则过多导致脆弱；规则过少导致失控 |
| 动态任务层 | 用户问题、会话状态、当前子任务 | 描述本轮真正要做什么 | 多轮中目标漂移，历史污染当前问题 |
| 外部知识层 | 检索结果、结构化数据、文档片段、网页、数据库查询结果 | 提供回答所需事实 | 召回错误、上下文过多、来源冲突 |
| 运行时动作层 | 工具、权限、文件句柄、搜索入口、记忆读写能力 | 让模型能够主动获取或更新上下文 | 工具过多、能力重叠、调用成本失控 |

这四层不是并列堆叠，而是有依赖顺序：

1. 静态约束决定系统不该做什么。
2. 动态任务决定系统此刻要做什么。
3. 外部知识决定系统凭什么这样回答。
4. 运行时动作决定系统还能去哪里继续找。

### 3.3 RAG 在 Context Engineering 中的位置

RAG 不是 Context Engineering 的对立面，而是其中最核心的一种“外部知识层”实现方式。  
它解决的是：当相关知识太多，不能全部放进上下文时，如何在推理前或推理时选择最可能有用的那一小部分信息。

但只要把 RAG 放进更大的上下文系统里，就会立刻看到它的边界：

- RAG 不能替代 system instructions。
- RAG 不能定义工具契约。
- RAG 不能自动管理多轮历史。
- RAG 不能天然解决复杂控制流。
- RAG 不能天然重构知识组织方式。

因此，本书后面的三条路线，实际上对应三种不同的上下文组织重心：

| 路线 | 重心 | 适合问题 |
|------|------|----------|
| Plain / Hybrid RAG | 优化外部知识层的召回与排序 | 单跳问答、文档问答、FAQ、制度检索 |
| Agentic / Reflective RAG | 优化运行时动作层与控制流 | 模糊问题、多步检索、需要重试与校验的问题 |
| GraphRAG | 重构外部知识层的组织方式 | 全局分析、跨文档关系发现、主题聚合、影响分析 |

### 3.4 四种常见上下文机制

为避免后续章节混用概念，这里先固定四种常见机制。

#### 长上下文

当知识总量不大、任务局部性强、一次性带入全部信息更简单时，直接用长上下文是合理选择。Anthropic 在《Introducing Contextual Retrieval》中明确提到，如果知识库小于约 200,000 tokens，直接把整个知识库放进 prompt 往往是更简单的方案。

#### 检索

当知识总量大于上下文窗口，或者虽然放得下但成本过高、噪音过多时，需要检索机制按需选择上下文。

#### 工具

当答案不在静态语料里，而在数据库、搜索接口、文件系统、浏览器、代码仓或工作流系统中时，需要工具让模型主动获取信息。

#### 记忆

当任务跨越多轮或长时程运行，上下文需要压缩和持久化时，需要外部记忆，而不是把全部历史永远保留在消息窗口里。

### 3.5 本书的判断原则

从这一章开始，后续所有设计选择都统一用三个判断标准：

1. 相关信息是否应该在推理前就被放进上下文。
2. 如果不该预先放入，系统是否有能力在运行时以低成本拿到它。
3. 这份信息在回答里究竟是证据、约束、工具入口，还是过程记忆。

## 4. 系统设计与工程实现

### 4.1 一个最小上下文系统蓝图

下面给出本书统一使用的上下文系统蓝图。

```text
用户问题
  ↓
任务解析层
  - 问题类型判断
  - 风险级别判断
  - 是否需要检索 / 工具 / 多轮控制
  ↓
上下文装配层
  - 静态约束
  - 当前问题
  - 检索结果或工具结果
  - 必要的会话记忆
  ↓
模型推理层
  - 回答
  - 工具调用
  - 继续检索
  ↓
验证与压缩层
  - groundedness / citation 检查
  - 历史压缩
  - 记忆回写
```

这个蓝图有两个原则。

第一，不把所有东西都提前放入。  
第二，不把一次检索结果误认为最终上下文。

### 4.2 Context Engineering 的五条工程规则

#### 规则 1：把 token 当预算，不当缓存

上下文窗口不是对象存储。能放的东西越多，越要明确为什么放。任何进入上下文的内容都应该回答一个问题：它对当前决策有什么增量价值。

#### 规则 2：静态规则尽量少，但契约必须硬

好的 system prompt 不是把每个边角条件都写成 if-else 文案，而是提供清晰边界、输出合同和行为优先级。规则过细会脆，规则过粗会飘。

#### 规则 3：把检索视为装配，不只是搜索

检索的目标不是“找到像是相关的文本”，而是“组装出回答所需的最小证据集”。这意味着 chunk、metadata、排序、去重、引用格式都属于同一工程问题。

#### 规则 4：工具必须是低歧义的

Anthropic 在 context engineering 文章里特别强调，工具集合膨胀和能力重叠是常见失败源。对人来说都说不清何时该用哪个工具，模型也不会更擅长。

#### 规则 5：历史要压缩，记忆要外置

会话历史越长，污染越严重。后续写 Agentic RAG 时会进一步展开，但从第一章开始就要有一个基本共识：长任务不能只靠 message history 硬撑。

## 5. 关键技术选型

### 5.1 长上下文、检索、工具、记忆怎么选

| 需求特征 | 优先方案 | 原因 |
|----------|----------|------|
| 知识量小且稳定 | 长上下文 | 简单、延迟低、调试成本低 |
| 知识量大但结构平稳 | Plain / Hybrid RAG | 先解决相关证据召回 |
| 问题模糊，需要多次试探 | Agentic / Reflective RAG | 需要控制流而非一次召回 |
| 目标是全局主题和关系理解 | GraphRAG | 需要重构知识组织方式 |
| 任务跨多轮、长时程 | 记忆 + 压缩 | 不能依赖无限消息历史 |

### 5.2 本书的默认选型顺序

本书采用保守选型顺序：

1. 先问能不能直接长上下文解决。
2. 不行，再做最小 Plain RAG。
3. Plain RAG 不够，再升级 Hybrid。
4. 仍然不够，再引入 agentic 控制流。
5. 如果问题本质是跨实体、跨社区、跨制度的全局分析，再考虑 GraphRAG。

这个顺序的原因很简单：复杂度应该由问题结构逼出来，而不是由工具栈爱好驱动。

### 5.3 不适用边界

本章不适合承担以下问题：

- 不适合回答“应该立刻选哪一家向量数据库”这类产品采购问题。
- 不适合直接决定某个 reranker、embedding 模型或索引参数。
- 不适合把所有长文档问答都升级成多智能体系统。

如果知识总量本来就很小，或者系统只是一次性分析一个有限文档包，本章最重要的结论反而可能是：先别上 RAG，先把长上下文和缓存用好。

## 6. 实战案例

### 6.1 案例 A：企业知识库问答的上下文系统蓝图

本书后续章节统一沿用同一案例：

一家中型企业希望做内部知识问答系统，语料包括：

- 《数据分级与使用规范》
- 《客户信息导出审批流程》
- 《外部模型使用安全指引》
- 《客服工单常见问题》
- 若干制度更新通知

用户问题是：

> 业务团队能否把实名认证图片导出到本地做 OCR 标注？如果默认不允许，例外审批路径是什么？

如果只把这个问题当成 prompt engineering 任务，常见做法是直接写一个很长的 system prompt，让模型“尽量严格引用制度回答”。  
这往往不够，因为系统还缺三样东西：

1. 它不知道该从哪份制度里找证据。
2. 它不知道制度更新通知是否覆盖了旧流程。
3. 它不知道“能否”与“例外审批路径”其实是两个子问题。

因此，这个案例天然要求一个最小上下文系统，而不是一段更华丽的提示词。

### 6.2 这个案例在三条路线里的位置

| 路线 | 在本案例中的角色 |
|------|------------------|
| Plain / Hybrid RAG | 找到制度条款、审批流程、例外条件 |
| Agentic / Reflective RAG | 把问题拆成“默认规则”和“例外路径”，并做交叉验证 |
| GraphRAG | 不是第一选择，因为本案例主要是局部制度问答，不是全局关系分析 |

### 6.3 第一章的可执行产出

这一章不写具体代码，但要求产出一张任务分流图。  
对本案例，可以先做如下判定：

1. 语料量超过单次稳定长上下文的舒适区，不能默认整包注入。
2. 目标是找制度证据与流程答案，优先走 RAG 路线。
3. 问题包含“默认规则 + 例外路径”，后续很可能需要在 Plain RAG 基线之上加入 query decomposition。
4. 当前不是 GraphRAG 场景，因为问题并不要求做跨制度社区级主题汇总。

这就为第 2 章建立了一个明确目标：先做出能回答这个问题的最小可用 RAG。

## 7. 评估方法

第一章不做系统调参，而是建立整本书统一的评估视角。

### 7.1 评估对象

本章评估的不是模型答案好不好，而是“系统设计是否把问题放在了正确路线里”。

### 7.2 最小评估清单

| 维度 | 问题 | 通过标准 |
|------|------|----------|
| 问题分型 | 当前问题是长上下文、RAG、Agentic 还是 GraphRAG 问题 | 至少能明确排除两条不合适路线 |
| 上下文边界 | 哪些信息必须进上下文，哪些只保留引用入口 | 不把全部知识库无差别塞进窗口 |
| 证据需求 | 回答是否需要可引用证据 | 需要时必须进入检索路线 |
| 控制流需求 | 是否需要拆解、重试、校验 | 当前案例先记为后续增强点，不在本章展开 |

### 7.3 本章输出指标

虽然不做数值实验，但本章要固定后续指标体系：

- 检索层：Recall@k、MRR、nDCG
- 上下文层：context relevance、context precision、context recall
- 生成层：faithfulness、answer relevance、citation correctness
- 系统层：latency、token cost、failure rate、fallback rate

从这一步开始，后续章节的每次系统增强都必须对应一组指标变化，而不是只展示几个成功案例。

## 8. 常见失败模式

### 8.1 把 prompt 当成全部系统

这是最常见的早期误区。团队会持续往 system prompt 里堆规则，直到 prompt 长得像半套业务系统，但真正的问题其实在检索、权限、历史污染或工具歧义。

### 8.2 把“更多上下文”误当成“更强能力”

很多系统看起来像是知识不够，实则是无关信息过多。更多上下文会带来更多证据，也会带来更多噪音和更多冲突。

### 8.3 先选复杂路线，再找问题匹配

一些团队一开始就上多代理、上图谱、上工作流编排，结果只是把本来可以一周做完的 FAQ 系统，变成了一个很难调试的复杂平台。

### 8.4 忽略“证据”和“动作”是两类不同上下文

检索结果是证据，工具是动作入口。两者混在一起，会导致模型既不清楚该相信什么，也不清楚该调用什么。

### 8.5 用会话历史替代记忆系统

历史对话只是临时缓存，不是长期记忆。把所有历史都保留在窗口里，最后往往既贵又乱，还很难定位污染来源。

## 9. 与下一章的衔接

到这里，全书的总框架已经固定：RAG 不是孤立技巧，而是 Context Engineering 中最重要的一类上下文装配机制。接下来的问题不再是“RAG 是什么”，而是“如何先搭出一个一天内可以跑通、能回答企业知识问答问题的最小系统”。


# 第 2 章 经典 RAG——最小可用系统

## 1. 本章要解决的问题

如果第 1 章解决的是“为什么需要上下文系统”，那么第 2 章要解决的是“先把最小系统跑起来”。

很多团队做 RAG 失败，并不是因为它们没有听说过 hybrid、rerank、agent 或图谱，而是因为它们在没有 baseline 的情况下直接优化复杂特性，最后既不知道系统到底哪里有效，也不知道哪里在浪费成本。

因此，本章只做一件事：给出一个一天内可跑通的最小可用 RAG 系统。  
它必须满足四个条件：

1. 有清晰的数据流。
2. 有可复用的最小案例。
3. 有第一版坏例样本库。
4. 有后续增强所依赖的基线指标。

## 2. 为什么这个问题在今天重要

这个问题今天比两年前更重要，原因恰恰是基础能力已经更容易拿到了。

OpenAI 当前的 Retrieval 文档把 vector store 直接定义为语义搜索的索引容器，上传文件后会自动完成 chunking、embedding 和 indexing；File Search 则已经是 Responses API 下的托管工具，支持 semantic + keyword search。  
这意味着现在做一个最小系统，障碍已经不在“能不能写出一个向量检索 demo”，而在“你能不能克制住过早优化的冲动，先拿到一个可信的 baseline”。

另一个现实原因是，企业团队对 RAG 的第一轮失望，通常不是来自真正的技术天花板，而是来自一开始的系统边界就没有定好：

- 语料没清理；
- 文档没有版本边界；
- 问题集没建立；
- 指标没定义；
- 检索结果没办法回看；
- 回答没有引用。

这些都不是高深问题，却决定一个 MVP 是否值得继续投资。

## 3. 核心概念与理论

### 3.1 最小 RAG 的五步数据流

本书将最小可用 RAG 固定为下面五步：

1. 导入语料
2. 切块
3. 向量化
4. 检索
5. 基于检索结果生成答案

用更工程化的话说，就是：

```text
documents -> chunks -> embeddings -> top-k context -> answer
```

这条链路足够简单，但已经能暴露绝大部分真实问题：文档脏不脏、chunk 切得对不对、top-k 取多少、回答是否 grounded、坏例集中在哪些问题类型。

### 3.2 本章的“最小”是什么意思

最小不是功能最少，而是变量最少。  
为了让后续评估成立，本章明确不引入以下增强项：

- 不做 hybrid search
- 不做 rerank
- 不做 query rewrite
- 不做 decomposition
- 不做 reflective checks
- 不做复杂 PDF 解析

只有先把这些变量全部拿掉，后续每一章的系统改动才有可比性。

### 3.3 托管检索与自建最小栈

本章允许两种 MVP 起步方式。

#### 方式 A：托管检索

适合需要尽快验证业务价值、团队对底层检索栈没有强控制需求的场景。  
优点是快、默认能力全、运维低。缺点是可解释性和可控性相对有限。

#### 方式 B：自建最小栈

适合需要明确控制 chunking、metadata、索引策略和查询链路的场景。  
优点是透明、可调、利于研究。缺点是搭建和维护成本更高。

本书后续默认使用“托管能力也能表达的概念 + 自建系统更容易展示的工程细节”来讲解。  
也就是说，理论上保持平台中立，工程上保持可执行。

### 3.4 一个最小 RAG 回答的正确结构

最小系统的回答至少应包含三类信息：

1. 结论
2. 证据
3. 不确定性说明

如果系统只能给结论，不能给证据，它更像一个聊天机器人，不像一个知识系统。  
如果系统给证据但不说明冲突和不确定性，它在真实企业场景里也很难被信任。

## 4. 系统设计与工程实现

### 4.1 语料准备

本书案例 A 的 MVP 先只导入四类文档：

- 数据分级制度
- 客户信息导出审批 SOP
- 外部模型使用规范
- 历史制度更新通知

目标是保证一个问题至少可能命中三类信息：

- 原则性禁令
- 例外条件
- 最新版本覆盖关系

### 4.2 最小系统架构

```text
文档目录
  ↓  ingest
向量存储 / 托管 vector store
  ↓  search(query, top_k)
召回 chunks
  ↓
回答器
  - 只基于召回片段作答
  - 明确引用来源
  - 缺证据则拒答或降级
```

### 4.3 最小可执行目录

```text
case_a/
  docs/
    data_policy.md
    export_sop.md
    model_usage_policy.md
    update_notice_2026q1.md
  eval/
    queries.jsonl
    bad_cases.jsonl
```

### 4.4 伪代码实现

下面的伪代码刻意保持最小，不引入任何后续章节的增强项。

```python
docs = load_documents("case_a/docs")
chunks = simple_chunk(docs, chunk_size=800, overlap=200)
index = build_vector_index(chunks)

def answer(query: str):
    hits = index.search(query, top_k=5)
    prompt = render_grounded_prompt(query=query, hits=hits)
    return llm_generate(prompt)
```

如果使用 OpenAI 当前的托管能力，最小流程甚至可以进一步压缩为：

1. 创建 vector store。
2. 上传文件并等待索引完成。
3. 用 Retrieval 或 File Search 取回相关 chunks。
4. 让模型基于搜索结果生成 grounded answer。

本章不追求写出最多代码，而是追求把可观测的数据流建立起来。

### 4.5 Grounded 回答模板

最小系统建议固定一个回答模板，降低生成漂移：

```text
结论：
- 默认是否允许

依据：
- 文档 A 第 X 节
- 文档 B 第 Y 节

例外路径：
- 若存在例外，说明审批角色与前置条件

不确定点：
- 如果文档存在冲突或版本不明确，明确指出
```

这个模板的价值不在于文风整齐，而在于它强迫系统把“证据”和“结论”绑定在一起。

## 5. 关键技术选型

### 5.1 MVP 阶段的默认选型

| 组件 | 本章默认选型 | 原因 |
|------|--------------|------|
| 文档格式 | Markdown / 纯文本优先 | 先绕开复杂 PDF 解析噪音 |
| Chunking | 简单固定窗口 | 保持变量最少，后续再优化 |
| 检索 | 向量检索或托管语义检索 | 先建立可用 baseline |
| Top-k | 5 作为起点 | 兼顾覆盖与上下文成本 |
| 生成模板 | 固定 grounded 模板 | 降低模型自由发挥 |
| 引用 | 强制输出来源 | 为后续 faithfulness 评估提供基础 |

### 5.2 托管能力与自建能力的边界

| 场景 | 更适合托管检索 | 更适合自建最小栈 |
|------|----------------|------------------|
| 需要快速验证 | 是 | 否 |
| 需要精细控制 chunking | 否 | 是 |
| 需要自定义 metadata 过滤策略 | 视平台而定 | 是 |
| 团队缺少检索基础设施经验 | 是 | 否 |
| 后续会持续做研究型调优 | 否 | 是 |

### 5.3 不适用边界

这个最小系统不适合以下问题：

- 大量精确标识符检索，如错误码、合同编号、设备编号密集问答
- 需要多跳推理的问题
- 强依赖表格、图像、扫描 PDF 的文档问答
- 需要严格处理版本覆盖和权限隔离的生产场景

换句话说，本章的 MVP 是“可跑通的基线”，不是“可上线的系统”。

## 6. 实战案例

### 6.1 用案例 A 搭第一个能工作的系统

我们继续使用第一章的案例问题：

> 业务团队能否把实名认证图片导出到本地做 OCR 标注？如果默认不允许，例外审批路径是什么？

#### 第一步：准备文档

至少准备四份文档：

1. `data_policy.md`：定义实名认证图片属于高敏感数据，不得擅自导出。
2. `export_sop.md`：定义例外审批流程和责任人。
3. `model_usage_policy.md`：定义外部模型和训练数据的限制。
4. `update_notice_2026q1.md`：说明新的审批要求是否覆盖旧流程。

#### 第二步：准备第一版评估问题

最少准备 20 条问题，覆盖三类：

- 直接问禁令
- 问例外路径
- 问版本更新后的规则差异

#### 第三步：跑一次最小搜索与回答

一个合理的最小召回结果，应该至少包含：

- 一条关于“实名认证图片不可导出”的制度条款
- 一条关于“何种情况下允许申请例外”的流程条款
- 一条关于“最新版本是否覆盖旧流程”的更新通知

如果 top-5 连这三类证据都凑不齐，问题通常不在模型，而在语料、chunk 或索引。

### 6.2 第一版坏例样本库

从第一天开始就应该积累坏例，而不是等系统变复杂之后再回头补。

建议固定五个坏例桶：

| 坏例类型 | 示例 |
|----------|------|
| 召回不到禁令条款 | 回答只谈审批流程，不谈默认禁止 |
| 召回不到版本更新 | 引用了过期流程 |
| 回答无引用 | 结论看起来对，但无法追溯来源 |
| 错把相邻条款拼成答案 | 把导出审批和模型使用规则混成同一条结论 |
| 证据不足仍强答 | 没找到例外路径，却编造审批角色 |

这五类坏例足以支撑后面三章的连续优化。

## 7. 评估方法

### 7.1 本章的实验目标

本章只回答一个问题：  
“最小系统是否已经达到值得继续优化的水平？”

### 7.2 建议指标

| 层级 | 指标 | 本章用途 |
|------|------|----------|
| 检索层 | Recall@5、MRR | 判断 top-k 是否能拿到正确证据 |
| 上下文层 | context precision | 判断召回片段里噪音是否过多 |
| 生成层 | faithfulness、citation correctness | 判断回答是否被证据支撑 |
| 系统层 | latency、token cost | 为后续增强建立成本基线 |

### 7.3 一个足够实用的基线验收标准

对一个 20 到 50 条问题的小评估集，本章建议的基线要求是：

- Recall@5 至少达到可用水平，不能大量漏掉关键制度条款
- citation correctness 必须高于“可接受”的人工门槛
- latency 必须足够低，保证可以快速迭代
- failure rate 必须可观测，而不是失败了也看不出来

这里故意不在第一章就给统一数值阈值，因为不同语料规模差异很大。  
本章更重要的是把“如何度量最小系统”固化下来。

## 8. 常见失败模式

### 8.1 语料干净度不足

制度文档混入旧版本、附件残片、重复条款，最小系统会立刻把这些问题放大。

### 8.2 没有版本边界

如果更新通知和旧制度同时被召回，但系统不区分生效时间，就会出现“每条证据都像真的，但结论彼此冲突”的典型坏例。

### 8.3 把回答正确误认为检索正确

有时模型会靠常识答对，但检索结果其实是错的。  
这类“侥幸正确”在生产上比明显错误更危险，因为它会掩盖系统结构问题。

### 8.4 没有坏例集

没有坏例集，后续任何优化都很容易变成主观体感。  
今天看起来更聪明，明天可能只是更会胡说。

### 8.5 过早引入复杂增强

如果最小系统还没把语料、top-k、引用模板、基线指标理顺，就开始加 query rewrite、rerank、agent loop，调试成本会急剧上升。

## 9. 与下一章的衔接

最小 RAG 系统一旦跑起来，第一批失败模式也会很快暴露出来：同样的问题，有时明明文档里有答案，却还是召回不到；有时召回到了，却片段缺上下文，无法稳定回答。接下来真正要优化的，不是“换个更强模型”，而是先回到索引前处理，重新定义知识单元本身。


# 第 3 章 Chunking 与索引工程

## 1. 本章要解决的问题

第 2 章的最小系统会很快遇到一个反直觉事实：  
很多问答失败，发生在模型推理之前。

制度条款明明存在，检索却拿不到；或者拿到了一个看似相关的 chunk，但这个 chunk 自身缺失主语、时间范围、适用对象，导致模型无法判断它究竟是不是当前问题的证据。

这说明 chunking 不是“预处理里的一个小参数”，而是知识单元设计。  
本章要解决的问题就是：如何把“文本切块”升级成“面向检索的知识单元设计”，并把索引工程变成可实验、可比较、可调优的系统环节。

## 2. 为什么这个问题在今天重要

Anthropic 在 2024 年 9 月 19 日发布的《Introducing Contextual Retrieval》对这个问题给出了非常明确的工程信号：传统 RAG 的一个根本问题，是分块后经常破坏上下文。  
同一篇文章里，Anthropic 进一步指出，Contextual Retrieval 通过在每个 chunk 前补充 chunk-specific context，可以显著降低检索失败率；仅 Contextual Embeddings + Contextual BM25 就把 top-20 chunk retrieval failure rate 从 5.7% 降到 2.9%，再配合 rerank 可降到 1.9%。

这组结果的价值不只是“某个技巧更强”，而是它把一个常被低估的问题明确化了：

- chunk 边界会决定证据是否还能被正确检索；
- chunk 本身是否带上下文，会决定语义检索是否还能看懂它；
- 索引前处理并不是后端清洗细节，而是直接决定召回上限。

在中文场景里，这个问题会更严重，因为大量企业文档具有以下特点：

- 标题层级深
- 枚举条款多
- 同义表述多
- 英文缩写和中文术语混用
- 表格、脚注、版本声明交织

如果仍然把 chunking 理解成“800 tokens 一刀切”，系统很难稳定。

## 3. 核心概念与理论

### 3.1 什么是知识单元

本章统一把一个“可检索 chunk”定义为：

> 在不依赖完整原文的前提下，能够被检索器识别、被排序器比较、被生成模型消费的一段最小证据单元。

这个定义要求一个 chunk 至少满足三件事：

1. 自身能表达主要语义对象
2. 自身能表达适用范围或局部上下文
3. 自身不会因为边界切断而失去关键约束

### 3.2 四类常见切块策略

#### 固定窗口切分

按固定 token 数量切分，配合固定 overlap。  
优点是简单、稳定、吞吐高。缺点是完全不理解文档结构。

#### 递归切分

优先按标题、段落、列表、句子等结构切；装不下再继续向更细粒度递归。  
优点是更贴合自然结构。缺点是实现复杂度更高。

#### 结构感知切分

针对文档类型单独设计边界，例如：

- 制度文档按章节、条款、适用范围切
- FAQ 按问答对切
- API 文档按 endpoint 切
- 会议纪要按议题切

这比通用递归更贴近业务语义。

#### 上下文化切分

不是改变边界，而是给每个 chunk 补上能让检索器理解它的局部说明。  
Anthropic 给出的标准做法是：利用整个文档，为当前 chunk 生成 50 到 100 tokens 的简短上下文，再把它 prepend 到 chunk 前面，同时参与 embedding 与 BM25 索引。

### 3.3 索引工程的五个变量

本章后续实验统一比较以下五个变量：

1. chunk size
2. chunk overlap
3. chunk boundary
4. metadata completeness
5. contextualization

只有把这五个变量拆开，后续实验才有可解释性。

### 3.4 中文文档的特殊点

中文企业文档的切块不能简单照搬英文经验，原因包括：

- 标题和正文之间常没有明显分隔符
- 条款编号本身带语义，例如“3.2.1 例外审批条件”
- 同一个实体可能以中文全称、英文缩写、内部简称多次出现
- 关键限制常出现在句尾修饰，如“未经法务与安全双签，不得……”

因此，中文场景里的好 chunk 往往需要把标题、条款号、适用范围、限制条件一起保留下来。

## 4. 系统设计与工程实现

### 4.1 本章的索引流水线

第 3 章开始，索引前处理不再是 `simple_chunk()` 一个函数，而是一条清晰流水线：

```text
原始文档
  ↓
文档规范化
  - 去噪
  - 版本标记
  - 标题解析
  ↓
结构抽取
  - 章节
  - 条款
  - 列表
  - 表格占位
  ↓
切块
  - 固定 / 递归 / 结构感知
  ↓
chunk metadata
  - doc_id
  - version
  - section_path
  - effective_date
  ↓
contextualize
  - 生成 chunk-specific context
  ↓
索引
```

### 4.2 一个制度文档的坏切法与好切法

假设原文如下：

```text
3.2 实名认证图片导出
3.2.1 默认规则
实名认证图片属于高敏感个人信息，未经批准不得导出至本地环境。
3.2.2 例外场景
若为监管要求或法务备案事项，可发起例外审批。
3.2.3 审批要求
须经数据安全负责人、法务负责人双签，并在七日内销毁副本。
```

如果直接按固定窗口截断，很可能出现这样的 chunk：

```text
若为监管要求或法务备案事项，可发起例外审批。须经数据安全负责人、法务负责人双签，并在七日内销毁副本。
```

这个 chunk 看起来信息很多，但它已经丢掉了三个关键限定：

- 讨论对象是实名认证图片
- 前提是高敏感个人信息
- 这里是例外场景，不是默认规则

更好的结构感知 chunk 至少应该保留：

```text
文档：数据分级与使用规范
章节：3.2 实名认证图片导出 > 3.2.2 例外场景
内容：若为监管要求或法务备案事项，可发起例外审批。
相邻约束：审批要求为数据安全负责人、法务负责人双签，并在七日内销毁副本。
```

再进一步，可加 contextualized chunk：

```text
本 chunk 来自《数据分级与使用规范》中“实名认证图片导出”的例外场景条款，讨论对象为高敏感个人信息的导出审批条件，而非默认可执行规则。
若为监管要求或法务备案事项，可发起例外审批。
```

这类 chunk 对 embedding 和 BM25 都更友好。

### 4.3 推荐的 chunk schema

```json
{
  "chunk_id": "data_policy_3_2_2",
  "doc_id": "data_policy",
  "title": "实名认证图片导出",
  "section_path": ["3.2", "3.2.2"],
  "effective_date": "2026-01-15",
  "content": "...",
  "context_prefix": "...",
  "keywords": ["实名认证图片", "高敏感个人信息", "例外审批"]
}
```

注意这里的重点不是字段越多越好，而是字段必须真正服务于检索和版本判断。

### 4.4 四组索引对比实验

本章固定做四组实验：

| 组别 | 切块方式 | 额外上下文 | 目标 |
|------|----------|------------|------|
| A | 固定窗口 | 无 | 作为第 2 章基线 |
| B | 递归切分 | 无 | 看结构边界是否提升召回 |
| C | 结构感知切分 | 无 | 看业务语义边界是否继续提升 |
| D | 结构感知切分 | 有 contextualized chunk | 看上下文化是否进一步提升 |

第 4 章前不引入 rerank，避免变量污染。

## 5. 关键技术选型

### 5.1 按文档类型选切块策略

| 文档类型 | 首选策略 | 原因 |
|----------|----------|------|
| 制度 / 合规文档 | 结构感知切分 | 条款边界比 token 长度更重要 |
| FAQ | 问答对切分 | 单条问答天然就是知识单元 |
| API / 技术文档 | 标题 + endpoint 切分 | 路径、参数、错误码要保持同域 |
| 长报告 / 白皮书 | 递归切分 + contextualize | 章节跨度大，单段常缺主语 |
| 聊天记录 / 纪要 | 议题或发言轮次切分 | 时间顺序和说话人重要 |

### 5.2 Chunk size 与 overlap 的选择

本章不给万能参数，只给判断逻辑：

- 约束性文档优先保边界，再调大小
- 描述性文档可适当放大 chunk size
- overlap 用于防止边界切断，不是越大越好
- 如果 overlap 已经在“补救错误边界”，通常说明切块策略本身错了

### 5.3 Contextualized chunk 的使用原则

Anthropic 的做法有两个重要启发：

1. contextual text 应该短，目标是定位，不是重写文档
2. contextual text 应同时服务 embedding 与 BM25，而不是只服务其中一种

因此，本书建议 contextualizer prompt 的目标始终是：

- 说明 chunk 讨论对象
- 说明 chunk 在原文中的位置或角色
- 说明这段内容是规则、例外、定义还是流程

### 5.4 不适用边界

本章的方法并不总是值得做重：

- 如果知识库整体很小，直接长上下文可能更简单
- 如果文档极短且结构单一，复杂切块收益有限
- 如果问题高度依赖精确字符串，单靠 chunking 不足以解决，需要 hybrid 或 keyword 支持
- 如果语料持续高频更新，复杂 contextualization 成本需要单独评估

## 6. 实战案例

### 6.1 用同一案例重做索引

继续使用案例 A，但这次只改索引前处理，不改问答模板、不改 top-k、不改模型。

目标问题保持不变：

> 业务团队能否把实名认证图片导出到本地做 OCR 标注？如果默认不允许，例外审批路径是什么？

### 6.2 四种切块结果对比

#### 方案 A：固定窗口

优点是简单。  
缺点是“默认规则”和“例外条件”可能被拆散。

#### 方案 B：递归切分

按标题、段落、句子逐级切，能明显减少“半句条款”问题，但仍不一定理解“例外场景”这种业务角色。

#### 方案 C：结构感知

明确把“默认规则”“例外场景”“审批要求”保成三个语义单元，适合制度文档。

#### 方案 D：结构感知 + contextualized chunk

在方案 C 基础上，再为每个 chunk 补充局部定位说明，增强召回时的语义信号。

### 6.3 一个可直接执行的 contextualizer prompt

```text
你将看到完整文档与其中一个片段。
请用 50 到 100 tokens 的简洁文字说明：
1. 该片段讨论的对象是什么；
2. 它在全文中属于定义、规则、例外还是流程；
3. 它最重要的适用边界是什么。
只输出这段说明，不输出其他内容。
```

### 6.4 示例实验结果

下面给出一个面向案例 A 的示例结果，用于说明比较方法，不宣称其对所有语料通用。

| 方案 | Recall@5 | nDCG@5 | context precision | 备注 |
|------|----------|--------|-------------------|------|
| A 固定窗口 | 0.62 | 0.58 | 0.54 | 例外审批经常缺主语 |
| B 递归切分 | 0.70 | 0.66 | 0.63 | 结构边界更自然 |
| C 结构感知 | 0.79 | 0.75 | 0.72 | 默认规则与例外条款分离清晰 |
| D 结构感知 + contextualized chunk | 0.85 | 0.81 | 0.78 | 对“审批路径”类问题更稳定 |

这个结果的核心不是数字本身，而是它展示了一条很稳定的工程规律：  
当知识单元设计更贴近文档语义，召回质量通常会先于模型能力显著改善。

## 7. 评估方法

### 7.1 本章的实验原则

只改索引，不改回答链路。  
否则你无法确认改进来自 chunking 还是来自生成策略。

### 7.2 推荐指标

| 层级 | 指标 | 观察重点 |
|------|------|----------|
| 检索层 | Recall@5、MRR、nDCG@5 | 是否更容易把正确条款排到前面 |
| 上下文层 | context precision、context recall | 召回片段是否更完整、更少噪音 |
| 生成层 | faithfulness | 即使回答链路未变，生成是否因证据更完整而提升 |
| 系统层 | ingestion latency、index size | 复杂切块是否引入过高预处理代价 |

### 7.3 评估集设计

本章建议至少覆盖四类问题：

- 直接问规则
- 问例外条件
- 问审批角色
- 问版本更新后的适用范围

如果某种切块方式只提升“直接问规则”，却对“版本更新”和“例外路径”没有帮助，说明它只解决了表层语义，不足以支撑真实制度问答。

## 8. 常见失败模式

### 8.1 为了整齐而切坏语义

很多实现喜欢把每个 chunk 控制在相同长度，但制度文档真正重要的是条款完整性，而不是视觉整齐。

### 8.2 Overlap 当成万能补丁

overlap 只能补边界，不能替代正确边界。  
如果必须靠很大 overlap 才能召回正确内容，通常说明 chunk 设计本身有问题。

### 8.3 Metadata 过少或过噪

没有 `effective_date`、`section_path`、`doc_id`，后续很难做版本判断。  
但 metadata 太多、质量太差，也会污染索引和排序。

### 8.4 Contextualizer 写成摘要器

context prefix 的目标是定位 chunk，不是重写全文。  
如果 contextual text 太长、太泛、太像摘要，反而会稀释原始证据。

### 8.5 只看召回，不看预处理代价

复杂 contextualization 可能显著提升质量，但也会带来额外预处理成本。  
如果语料变化很快，本章的最佳方案未必能直接搬到生产。

## 9. 与下一章的衔接

到这里，知识单元已经更像知识单元了：召回更完整，片段更可用，制度边界也更清楚。但只把正确内容“召回进来”还不够，工业系统接下来还要解决另一个问题：当语义相似和精确匹配同时重要时，如何把召回做全，再把排序做准。这就是下一章要进入的 Hybrid Search、RRF 与 Rerank。

# 第 4 章 Hybrid Search、RRF 与 Rerank

## 1. 本章要解决的问题

第 3 章已经把知识单元设计清楚了，但一个更工业化的问题马上会出现：  
即使 chunk 设计已经合理，单一路径检索仍然经常在两类问题上失手。

第一类问题是“语义相似但关键词不重合”。  
用户问“本地落盘”“例外审批”“外包标注”，文档里可能写的是“导出至终端环境”“特殊审批流程”“供应商处理”，纯 BM25 不一定抓得到。

第二类问题是“关键词极其关键，但语义模型容易稀释”。  
制度编号、错误码、审批角色名、产品名、内部术语、版本号、时间点，往往必须精确命中。纯向量检索很容易“意思差不多”，但不够准。

所以，本章要解决的问题不是“如何换一个更好的检索器”，而是建立现代工业 RAG 的标准检索配方：

1. 先用多路 first-stage retrieval 把召回做全。
2. 再用 fusion 把多路结果合并成可比较的候选集。
3. 最后用 second-stage rerank 把上下文排准，只把最该进 prompt 的片段送给模型。

换句话说，本章的主题不是某个孤立算法，而是一条工业检索流水线。

## 2. 为什么这个问题在今天重要

这个问题今天已经不是“高级优化”，而是默认工程要求。

OpenAI 当前 File Search 文档明确说明，file search 是 Responses API 下的托管工具，并通过 semantic + keyword search 检索知识库。这个表述很关键，因为它意味着主流托管检索能力本身已经不再把“语义检索”视为唯一答案，而是默认把语义与关键词组合起来。

Anthropic 在 2024 年 9 月 19 日发布的《Introducing Contextual Retrieval》进一步把这件事说得更具体：  
embeddings + BM25 比 embeddings 单独使用更好；在其实验中，Contextual Embeddings + Contextual BM25 把 top-20 retrieval failure rate 从 5.7% 降到 2.9%，再加 rerank 后降到 1.9%。这说明工业系统里真正有效的不是“再换一个 embedding 模型”，而是让不同检索机制和排序机制分工合作。

Microsoft Learn 当前关于 Azure AI Search 的 RRF 文档则给出了另一个重要信号：fusion 不是简单拼接，而是正式的 ranking 问题。Hybrid search 里多路结果并行返回后，需要一种稳定、可解释、对原始分值尺度不敏感的合并方式。RRF 正是这种工业上足够稳妥的融合算法。

因此，本章的重要性在于，它把“检索增强”从一个单点组件，升级成了一个分层系统：

- 第一层解决 coverage
- 第二层解决 ranking consistency
- 第三层解决 context usefulness

不建立这条标准配方，后续所有 agentic 增强都很容易建立在脆弱的检索地基上。

## 3. 核心概念与理论

### 3.1 Two-Stage Retrieval 的基本框架

本章把现代工业检索固定成下面的框架：

```text
query
  ↓
first-stage retrieval
  - vector retrieval
  - BM25 / keyword retrieval
  - optional filters
  ↓
fusion
  - dedupe
  - merge rankings
  ↓
second-stage rerank
  - score candidate chunks against query
  ↓
top-k context
  ↓
answer generation
```

这个框架的核心思想很简单：

- first-stage retrieval 负责尽量别漏。
- fusion 负责让不同召回路径的结果可以放在一起比较。
- rerank 负责把“可能相关”压缩成“最值得进 prompt”。

### 3.2 为什么 Vector 和 BM25 是互补的

向量检索擅长语义相近。  
BM25 擅长精确词项、短语、标识符和局部关键词。

二者互补，不只是因为一个语义、一个词法，而是因为它们犯错的方式不同。

| 机制 | 长处 | 短板 |
|------|------|------|
| Vector retrieval | 可找出关键词不完全一致但语义相关的内容 | 对编号、术语、版本号等精确匹配不稳定 |
| BM25 / keyword retrieval | 对术语、实体名、错误码、审批角色、时间词更敏感 | 容易漏掉换写法、近义表达和上下文化改写 |

所以 industrial RAG 的第一原则不是“二选一”，而是“让二者都说话”。

### 3.3 RRF 是什么

RRF，Reciprocal Rank Fusion，本质上是一种排名融合算法。  
Microsoft 当前文档对它的定义很清楚：来自多路检索器的 ranked lists 先各自排序，再为每个结果按 `1 / (rank + k)` 计算 reciprocal-rank score，之后把各路分数求和，用合成分数得到最终排序。

这个设计有三个工程优点。

第一，它不依赖不同检索器原始分值可比。  
向量相似度、BM25 分值、过滤打分常常尺度不同，直接拼分数很危险；RRF 只关心名次。

第二，它更重视“多路都排得靠前”的结果。  
一个文档如果同时在向量检索和 BM25 检索里都排前列，通常比只在某一路偶然出现更可信。

第三，它很适合作为 first-stage 之后的中间层，而不是最终判断层。  
RRF 的目标不是得到“最终最优相关性”，而是得到一个更稳、更全的候选集，供 rerank 使用。

### 3.4 Rerank 的职责

Rerank 不是第二个检索器，而是更贵、更精细的排序器。

Anthropic 在 contextual retrieval 文章里给出的运行方式非常典型：

1. 先做初始召回，拿到一大批候选 chunks。
2. 把 query 和候选 chunks 一起交给 reranker。
3. 让 reranker 给每个 chunk 打 relevance score。
4. 只保留 top-k 进入生成阶段。

Rerank 的价值有三点：

1. 它能把 first-stage 的“宽召回”压缩成“高密度上下文”。
2. 它能显著减少 prompt 噪音。
3. 它能把 latency 和 token cost 控制在更合理范围内。

但它的代价也很明确：增加一轮 runtime 计算，并放大候选规模选择错误时的成本。

### 3.5 本章的三组对比

本章后续实验统一比较三组系统：

1. vector only
2. hybrid retrieval
3. hybrid retrieval + rerank

这样设计的原因是，把变量控制在“召回路径”和“排序路径”两个层面，能让后续收益更可解释。

## 4. 系统设计与工程实现

### 4.1 标准检索流水线

对于案例 A，本章建议的标准检索流水线如下：

```text
用户问题
  ↓
query normalization
  - 统一术语
  - 清理噪音字符
  ↓
vector retrieval
  - 取 top_n_vec
  ↓
BM25 retrieval
  - 取 top_n_bm25
  ↓
RRF fusion
  - 按文档/chunk 去重
  - 合成 fused ranking
  ↓
reranker
  - 对 fused top_m 打分
  - 输出 reranked top_k
  ↓
grounded answer generation
```

这里最重要的不是参数，而是职责分工：

- vector 负责拉近语义相似表达
- BM25 负责兜住精确术语
- RRF 负责稳定融合
- rerank 负责把“像相关”变成“真正值得进上下文”

### 4.2 一个可执行的伪代码版本

```python
def retrieve(query: str):
    vec_hits = vector_index.search(query, top_k=20)
    bm25_hits = bm25_index.search(query, top_k=20)

    fused_hits = rrf_merge([vec_hits, bm25_hits], k=60)
    candidate_hits = fused_hits[:30]

    final_hits = reranker.rank(query=query, candidates=candidate_hits)[:8]
    return final_hits
```

如果要强调 first-stage 与 second-stage 的边界，可以进一步分开：

```python
def first_stage(query: str):
    return rrf_merge([
        vector_index.search(query, top_k=20),
        bm25_index.search(query, top_k=20),
    ])

def second_stage(query: str, candidates):
    return reranker.rank(query, candidates)[:8]
```

### 4.3 参数不是越大越好

本章建议关注三个规模参数：

| 参数 | 作用 | 常见错误 |
|------|------|----------|
| `top_n_vec` / `top_n_bm25` | 决定 first-stage 召回覆盖 | 取太小导致漏召回；取太大导致 rerank 成本膨胀 |
| `top_m` | 决定进入 rerank 的候选数 | 过小会损失 hybrid 收益；过大收益递减 |
| `top_k` | 决定最终进入 prompt 的上下文数 | 过小证据不全；过大噪音回流 |

工程上应优先遵循这个顺序：

1. 先确定最小可用 recall。
2. 再确定 rerank 前候选规模。
3. 最后收紧进入 prompt 的 top-k。

### 4.4 版本与 metadata 在 hybrid 阶段开始真正重要

到了 hybrid 阶段，metadata 已经不只是辅助字段，而是检索策略的一部分。  
对案例 A，至少需要这几类字段：

- `doc_id`
- `section_path`
- `effective_date`
- `document_type`
- `version`
- `sensitivity_domain`

原因是 hybrid 把召回做全之后，更容易同时拿回：

- 新旧版本
- 规则条款与流程条款
- 主制度与更新通知

如果没有 metadata，RRF 和 rerank 之后仍然可能把“看起来相关但版本过期”的条款排到前面。

### 4.5 从“召回做全”到“排序做准”的判断方式

一个 hybrid 系统已经足够成熟，通常会表现出三种特征：

1. 对关键词精确问题的 recall 明显高于 vector only。
2. 对语义换写问题的 recall 不低于 vector only。
3. rerank 后进入 prompt 的上下文更短、更聚焦，但 citation correctness 不下降。

如果做不到这三点，说明系统只是“变复杂了”，还不是真正变强。

## 5. 关键技术选型

### 5.1 什么时候必须上 Hybrid

当你的语料和问题同时满足以下任一条件时，Hybrid 通常应成为默认路线：

- 问题里频繁出现专有术语、编号、角色名、时间点
- 文档里同义改写多，纯关键词覆盖不足
- 同一问题既要命中规则条款，也要命中流程条款
- 用户问法口语化，但文档写法制度化

### 5.2 什么时候应该加 RRF

只要存在两路以上并行召回，而且原始分值不可靠或不可比，RRF 就是一个很稳妥的默认选项。

RRF 特别适合：

- BM25 + vector
- 多向量字段并行检索
- 多 collection 并行召回之后的统一排序前处理

RRF 不一定是唯一答案，但它非常适合作为工业默认基线，因为它简单、稳定、解释成本低。

### 5.3 什么时候值得加 Rerank

以下场景通常值得引入 rerank：

- first-stage 为了保证 recall，必须放大候选数
- 进入 prompt 的上下文预算紧张
- citation correctness 和 faithfulness 对业务很关键
- 你已经能召回到对的内容，但排位还不够稳

以下场景不一定值得一上来就加：

- 语料很小
- top-k 已经很短且质量稳定
- latency 预算极度严格
- 当前最大问题仍然是语料清洗和版本边界

### 5.4 Hosted vs self-built 的现实边界

| 目标 | 更适合托管能力 | 更适合自建 |
|------|----------------|------------|
| 快速上线 hybrid baseline | 是 | 否 |
| 深入控制 BM25 字段、fusion、rerank 候选规模 | 否 | 是 |
| 团队资源有限 | 是 | 否 |
| 后续要做系统级检索研究 | 否 | 是 |

### 5.5 不适用边界

本章的方法仍然有明确边界：

- 它不能替代多跳查询控制流
- 它不能天然修复问题表述含糊
- 它不能替代权限判断和多租户隔离
- 它不能解决“需要全局主题概括”的问题

如果一个问题本质上需要先拆问题、再多轮试探、再校验 groundedness，那么再强的 hybrid retrieval 也只是更强的静态入口，而不是完整解法。

## 6. 实战案例

### 6.1 继续增强案例 A

我们继续使用案例 A 的核心问题：

> 业务团队能否把实名认证图片导出到本地做 OCR 标注？如果默认不允许，例外审批路径是什么？

到第 4 章，语料和 chunk 已经经过第 3 章优化，但仍会遇到两个典型问题：

1. “OCR 标注”在文档中可能写成“图像识别训练前处理”。
2. “例外审批路径”可能分散在“特殊审批”“法务备案”“导出审批要求”三类条款中。

这时，vector only 常能抓到语义相近的条款，但容易漏掉审批角色、版本通知和明确禁令。  
BM25 能抓住“实名认证图片”“导出”“审批”这些词，但又可能召回一些只共享关键词、并非核心证据的片段。

因此，本章把实验设计成三组。

### 6.2 实验组设计

| 组别 | 检索方案 | 目标 |
|------|----------|------|
| A | vector only | 作为第 3 章之后的强基线 |
| B | vector + BM25 + RRF | 验证 hybrid 是否扩大覆盖 |
| C | vector + BM25 + RRF + rerank | 验证排序是否更准、上下文是否更密 |

### 6.3 一个具体问题如何被改进

假设用户追问：

> 如果这批实名认证图片需要交给外部供应商做 OCR 预标注，审批通过后是否还能临时保留本地副本？

这个问题里至少有四个关键信号：

1. 实名认证图片
2. 外部供应商
3. OCR 预标注
4. 临时保留本地副本

一个典型的检索演化过程会是：

- vector only 找到“模型使用安全规范”和“图像处理说明”，但未必把“七日内销毁副本”条款提到前排
- hybrid 后，BM25 兜住“副本”“审批”“供应商”等明确词项，RRF 让跨路都靠前的条款进入候选
- rerank 后，真正需要的三类证据会被压到前面：
  - 默认禁令
  - 例外审批条件
  - 审批后的销毁要求

### 6.4 示例结果

下面的结果只用于说明比较方式，不宣称对所有语料通用。

| 方案 | Recall@5 | MRR | nDCG@5 | context precision | latency |
|------|----------|-----|--------|-------------------|---------|
| vector only | 0.76 | 0.69 | 0.71 | 0.61 | 低 |
| hybrid + RRF | 0.87 | 0.77 | 0.80 | 0.66 | 中 |
| hybrid + RRF + rerank | 0.88 | 0.85 | 0.87 | 0.79 | 中高 |

这张表背后的关键信号不是“hybrid 把所有指标都大幅拉高”，而是：

- hybrid 主要先改善 recall
- rerank 主要再改善 rank quality 与 context precision

这正符合本章的职责分工。

## 7. 评估方法

### 7.1 本章实验原则

本章只比较 retrieval stack，不改变回答模板和模型。  
否则 rerank 带来的收益会被生成差异掩盖。

### 7.2 指标设置

| 层级 | 指标 | 本章关注点 |
|------|------|------------|
| 检索层 | Recall@5、MRR、nDCG@5 | hybrid 是否更全、rerank 是否更准 |
| 上下文层 | context precision、context recall | 进入 prompt 的证据是否更集中、更完整 |
| 生成层 | faithfulness、citation correctness | 更好的排序是否转化为更可信的回答 |
| 系统层 | retrieval latency、rerank latency、token cost | hybrid 与 rerank 的 runtime 代价 |

### 7.3 推荐的坏例分桶

| 坏例桶 | 表现 |
|--------|------|
| exact-match miss | 明确术语在文档里有，但 vector only 漏掉 |
| semantic miss | 用户换写法后，BM25 漏掉 |
| version conflict | 新旧版本都召回，但排位错误 |
| noisy top-k | 召回很多看似相关但对回答无用的片段 |
| rerank overcompression | rerank 过度压缩，丢掉必要辅助证据 |

这些坏例桶会在下一章直接变成“实验驱动优化”的输入。

## 8. 常见失败模式

### 8.1 把 Hybrid 当成简单并集

如果只是把 vector 和 BM25 结果拼起来，不做稳定 fusion，系统往往会陷入分值不可比和重复结果淹没的问题。

### 8.2 first-stage 太小

如果 first-stage 候选规模太小，rerank 几乎无事可做，因为真正需要的条款根本没进候选集。

### 8.3 rerank 候选规模失控

如果把几百个候选都送去 rerank，收益很快递减，成本和时延却会继续上升。

### 8.4 忽略 metadata

hybrid 把召回做全之后，更需要 metadata 来区分版本、文档类型和条款角色。  
否则系统只是把更多噪音更稳定地送进来。

### 8.5 指标看错层

一些团队看到 Recall 提升就以为系统变强，但最终进入 prompt 的上下文可能更乱。  
另一些团队只看回答质量，却忽略 latency 和 rerank 成本已经超预算。  
这两种都不是工程化优化。

## 9. 与下一章的衔接

到这里，检索配方已经像一个工业配方了：vector 负责语义覆盖，BM25 负责精确兜底，RRF 负责稳定融合，rerank 负责把上下文排准。但系统也因此进入了一个新阶段：改动开始变多，指标开始变多，收益和代价都不再能靠感觉判断。下一章必须先把评估闭环固定下来，否则后面的 agentic 升级只会让系统更复杂，却不一定更好。


# 第 5 章 Agentic / Reflective RAG

## 1. 本章要解决的问题

到了这一章，系统已经具备：

- 更合理的 chunk
- 更完整的 hybrid retrieval
- 更稳定的 rerank
- 更清晰的评估闭环

但复杂问题仍然会失败。  
失败的原因往往不再是“找不到片段”，而是：

1. 用户问题本身太含混，需要先改写成可检索问题。
2. 一个问题其实包含多个子问题，需要拆开检索。
3. 初始召回不够好，需要二次重试。
4. 系统拿到了上下文，但需要检查上下文是否真的相关。
5. 系统已经生成答案，但还需要检查答案是否 grounded。

这说明问题结构已经变了。  
系统缺的不是更强的静态检索，而是运行时控制流。

因此，本章要解决的问题是：如何把静态 RAG 管线升级成一个具备 query rewrite、query decomposition、context relevance check、groundedness check、停止条件与成本边界的控制流系统。

## 2. 为什么这个问题在今天重要

Anthropic 在 2025 年 9 月 29 日的 context engineering 文章里，已经把 pre-inference retrieval 和 just-in-time runtime retrieval 放进了同一个上下文管理问题中来讨论。它强调，随着 agents 越来越多地在工具循环中工作，系统开始依赖 lightweight identifiers、runtime exploration、compaction 和 note-taking，而不是把所有相关信息预先装进 prompt。

这给 Chapter 5 一个很清晰的方向：  
当问题开始跨步骤、跨子任务、跨局部上下文时，RAG 就不能只是一轮 retrieve-then-read。

NVIDIA 当前的 RAG Blueprint 文档则把这一点进一步工程化：

- Query Rewriting：通过额外 LLM 调用，把多轮上下文里的用户问题去上下文化，改写成更适合检索的 standalone query。
- Query Decomposition：把复杂、多面向问题拆成 focused subqueries，独立检索，再综合答案。
- Self-Reflection：分成 context relevance check 和 response groundedness check 两类校验，并允许设置 loop 上限和阈值。

这些能力重要，不是因为它们让系统“更像智能体”，而是因为它们把复杂问题的处理从一次性猜测，变成了一个可观察、可停止、可评估的 runtime pipeline。

## 3. 核心概念与理论

### 3.1 Query Rewrite、Decomposition、Reflection 的职责区分

这三个词经常被混在一起，但它们解决的是不同层次的问题。

| 机制 | 解决的问题 | 输出 |
|------|------------|------|
| Query Rewrite | 当前问题表达不利于检索 | 更适合检索的单一查询 |
| Query Decomposition | 当前问题本质上包含多个子问题 | 多个子查询及其后续跟进 |
| Reflection | 当前上下文或当前答案质量不够 | 重试、改写、重生成或停止决策 |

### 3.2 Query Rewrite

NVIDIA 当前 query rewriting 文档把它描述得很直接：  
对 multi-turn queries，系统会先做额外 LLM 调用，把当前问题 decontextualize 成更适合 retrieval pipeline 的 standalone query。

它适合解决的问题是：

- 追问式问题
- 指代模糊问题
- 会话依赖型问题

例如：

> 那如果外包供应商参与呢？

这个问题对人类读者是清楚的，对检索器却不清楚。  
rewrite 之后可能变成：

> 在实名认证图片导出场景下，如果需要交由外部供应商做 OCR 预标注，制度是否允许，例外审批路径是什么？

### 3.3 Query Decomposition

NVIDIA 当前 query decomposition 文档把它定义为：  
把 complex, multi-faceted queries 拆成 focused subqueries，独立处理，必要时生成 follow-up questions，最后综合为最终答案。

它适合的问题不是“说法不好”，而是“问题本身就不是一个单跳问题”。

例如：

> 如果这批实名认证图片要导出到本地做 OCR 标注，再交由外部供应商做清洗，默认规则是什么？例外审批需要谁签？审批后副本能保留多久？

这个问题至少包含三个子问题：

1. 默认规则
2. 例外审批条件与角色
3. 审批后的保留与销毁要求

单次检索往往会把这三个维度混成一团。

### 3.4 Reflection

NVIDIA 当前 self-reflection 文档把 reflection 明确拆成两类：

#### Context Relevance Check

系统先判断当前 retrieved context 是否足够相关。  
若不够相关，可以触发 query rewrite 或再次检索。

#### Response Groundedness Check

系统在生成答案后，再判断答案是否真正被上下文支撑。  
若 groundedness 不足，可以要求重新生成，或直接停止并回退。

这两个检查非常重要，因为它们把“重试”从拍脑袋变成了有条件的控制流。

### 3.5 停止条件与成本边界

Agentic 系统最危险的不是不会动，而是一直动。  
因此，本章必须把 stop condition 作为一等公民。

停止条件至少应包含：

1. 最大 rewrite / reflection / recursion 次数
2. 最小可接受 relevance / groundedness 阈值
3. 超时上限
4. 单次 query 的 token / cost 预算
5. 失败后的 fallback 策略

如果没有这些边界，agentic RAG 很容易从“更稳”变成“更慢、更贵、更不可控”。

## 4. 系统设计与工程实现

### 4.1 一个最小的 Agentic / Reflective RAG 管线

```text
user query
  ↓
complexity gate
  - simple? -> go to hybrid retrieval directly
  - complex? -> enter agentic path
  ↓
query rewrite (optional)
  ↓
query decomposition (optional)
  ↓
retrieve for each subquery
  ↓
context relevance check
  - fail -> rewrite / re-retrieve
  - pass -> continue
  ↓
synthesis
  ↓
response groundedness check
  - fail -> regenerate / fallback
  - pass -> return
```

### 4.2 一个简单控制流伪代码

```python
def answer(query):
    if is_simple(query):
        return answer_with_hybrid_rag(query)

    rewritten = maybe_rewrite(query)
    subqueries = maybe_decompose(rewritten)

    contexts = []
    for sq in subqueries:
        ctx = hybrid_retrieve(sq)
        ctx = improve_until_relevant(sq, ctx, max_loops=2)
        contexts.append(ctx)

    draft = synthesize(query, contexts)
    final = improve_until_grounded(query, contexts, draft, max_loops=2)
    return final
```

### 4.3 Complexity Gate

不是每个问题都值得进入 agentic path。  
一个足够实用的 complexity gate 可以基于以下信号：

- 是否包含多个并列子句
- 是否同时询问规则、例外、流程、时效
- 是否是多轮追问
- 是否需要跨多个文档角色
- 是否历史上属于 complex_query_failure 桶

如果没有 gate，系统就会对简单问题过度操作。

### 4.4 Reflection Loop 的设计

NVIDIA 的 reflection 文档里给出了非常清晰的工程启发：

- relevance 与 groundedness 应分开评估
- 每次循环都应有阈值
- 每次循环都应有最大次数

因此，本章建议的 reflection loop 设计如下：

| 阶段 | 检查对象 | 失败动作 |
|------|----------|----------|
| relevance loop | retrieved context | rewrite query / narrow retrieval / rerun |
| groundedness loop | generated answer | regenerate with stricter evidence binding / fallback |

### 4.5 Query-to-Answer 的可观测性

NVIDIA query-to-answer pipeline 文档的价值在于，它把 optional query rewriter、retriever、context reranker、generation 等阶段放进了一条可观测流水线。  
这很适合本书的 experiment-first 叙事，因为你终于可以按阶段记录：

- rewrite latency
- decomposition depth
- subquery count
- rerank candidate count
- reflection loop count
- groundedness pass/fail

有了这些字段，agentic RAG 才能被调，而不是只能被演示。

## 5. 关键技术选型

### 5.1 什么时候先上 Rewrite

当问题主要难在“当前表述不适合检索”时，应优先上 rewrite，而不是 decomposition。

典型场景：

- 多轮追问
- 指代不明
- 口语化追问
- 会话依赖强

### 5.2 什么时候先上 Decomposition

当问题主要难在“一个 query 包含多个子目标”时，应优先上 decomposition。

典型场景：

- 同时问默认规则和例外路径
- 同时问审批角色和后置约束
- 需要多跳组合事实

### 5.3 什么时候必须做 Reflection

以下情况通常值得引入 reflection：

- failure cost 高
- 需要明确引用证据
- 错答风险比延迟更敏感
- 系统已经有足够好的 first-stage retrieval，但 complex queries 仍失败

### 5.4 停止条件应该如何定

建议最先固定这四个参数：

| 参数 | 建议作用 |
|------|----------|
| `MAX_RECURSION_DEPTH` | 限制 decomposition 深度 |
| `MAX_REFLECTION_LOOP` | 限制 relevance / groundedness 反复重试 |
| relevance threshold | 决定是否值得继续找上下文 |
| groundedness threshold | 决定答案是否可以放行 |

默认值不是关键，关键是这些值必须被记录、被评估、被纳入成本预算。

### 5.5 不适用边界

本章的方法不适合：

- 简单 factual queries
- 低延迟强约束场景
- 大量实时查询且 retrieval 已足够稳定的场景
- 只需要单跳 FAQ 的系统

NVIDIA 文档本身也明确给出了类似边界：simple factual questions、single-concept queries、time-sensitive queries 往往不值得做 decomposition。

## 6. 实战案例

### 6.1 用案例 A 进入 Agentic 路线

我们继续使用案例 A，但问题升级为：

> 如果实名认证图片需要导出到本地做 OCR 预标注，再交给外部供应商清洗，默认规则是什么？如果存在例外审批，需要谁批准？批准后本地副本能保留多久？

这已经不是一个适合单次 hybrid retrieval 直接回答的问题。

### 6.2 运行时拆解

一个合理的 decomposition 结果可能是：

1. 实名认证图片导出到本地的默认规则是什么？
2. 外部供应商参与处理时是否有额外限制？
3. 例外审批的条件和审批角色是什么？
4. 审批通过后副本保留和销毁要求是什么？

### 6.3 运行时流程

一个可执行的 agentic 流程可以是：

1. 先 rewrite，把问题转成检索友好的 standalone query
2. 再 decomposition
3. 对每个 subquery 跑 hybrid retrieval
4. 对检索结果做 relevance check
5. 综合生成初版答案
6. 做 groundedness check
7. 若 groundedness 不足，则重生成或 fallback

### 6.4 示例收益

下面的结果只说明比较方式。

| 版本 | complex_query_success | faithfulness | fallback rate | latency | cost/query |
|------|-----------------------|--------------|---------------|---------|-----------|
| hybrid_rrf_rerank_v3 | 0.29 | 0.76 | 0.34 | 中 | 中 |
| agentic_rewrite_v4 | 0.38 | 0.79 | 0.29 | 中高 | 中高 |
| agentic_decompose_reflect_v5 | 0.57 | 0.87 | 0.18 | 高 | 高 |

这张表最重要的不是“agentic 更强”，而是：

- 它确实能解决静态检索管线解决不了的问题
- 但它显著增加 latency 和 cost

所以本章不是鼓励一律升级，而是建立一条受控升级路径。

## 7. 评估方法

### 7.1 本章实验目标

本章要验证的不是“agentic 看起来更聪明”，而是：

1. complex queries 是否更容易成功
2. groundedness 是否真的提高
3. failure rate 和 fallback rate 是否下降
4. 这些收益是否值得 runtime 代价

### 7.2 推荐指标

| 层级 | 指标 | 本章重点 |
|------|------|----------|
| 检索层 | subquery recall、context relevance | 每个子问题是否拿到对的上下文 |
| 上下文层 | aggregated context precision | 多子问题拼接后是否仍然清晰 |
| 生成层 | faithfulness、answer relevance、citation correctness | 综合答案是否被证据支撑 |
| 系统层 | latency、cost/query、failure rate、fallback rate、loop count | 控制流收益是否值得代价 |

### 7.3 评估集设计

本章评估集不应再以简单问题为主，而应重点覆盖：

- 组合式问题
- 多轮追问
- 条件依赖问题
- 需要同时回答规则 + 流程 + 约束的问题

如果评估集仍然 mostly 是简单 FAQ，本章很容易得出误导性的“agentic 没必要”结论。

## 8. 常见失败模式

### 8.1 对所有问题都启用 Agentic Path

这会让简单问题平白增加延迟和成本。

### 8.2 Query Explosion

decomposition 没有边界时，subquery 数量会迅速膨胀，导致 retrieval、rerank、generation 都变重。

### 8.3 Reflection 变成死循环

如果 relevance / groundedness 阈值不合理，或者没有明确 loop limit，系统可能不断改写、重检、重生成。

### 8.4 子问题看似正确，综合答案仍然错误

decomposition 解决的是子问题召回，不自动保证 synthesis 正确。  
因此综合答案仍然必须做 groundedness check。

### 8.5 只看成功率，不看成本边界

如果 success rate 提升 10 个点，但 latency 翻三倍、cost 翻五倍，系统未必真适合生产。

## 9. 与下一章的衔接

到这里，系统已经不只是“会检索”，而是开始“会在运行时组织检索”。但还有一类问题并不会因为多检几次、多拆几个子问题就真正解决：当任务要求的是跨实体、跨制度、跨主题的全局理解时，问题的瓶颈不再是控制流，而是知识组织方式本身。下一章需要进入的，正是从局部检索转向全局理解的 GraphRAG。

# 第 6 章 GraphRAG——从局部检索到全局理解

## 1. 本章要解决的问题

第 5 章把系统从静态检索升级到了运行时控制流：会改写问题、拆解问题、检查上下文、检查答案。  
但有一类问题，即使多检几次、多拆几步，也仍然解决不好。

这类问题不是在问“某条制度怎么规定”，而是在问：

- 哪些制度共同影响一个业务流程
- 哪些部门、系统、角色之间存在隐含依赖
- 某个政策变化会影响哪些下游流程
- 一组文档整体呈现出什么主题、冲突和风险

这些问题的核心不是“检索不到局部证据”，而是“知识组织方式不适合全局理解”。

Plain / Hybrid RAG 的基本单位是 chunk。  
Agentic / Reflective RAG 的增强点是运行时控制流。  
GraphRAG 的根本变化是：把文档从一堆可检索片段，重构成实体、关系、声明、社区和社区报告组成的图式知识结构。

因此，本章要解决的问题是：什么时候必须把知识从局部片段检索，升级为图式组织与全局理解。

## 2. 为什么这个问题在今天重要

Microsoft 当前 GraphRAG 文档已经把 GraphRAG 作为一套独立方法线来组织，而不是普通 RAG 的附属技巧。  
它的 Query Engine 明确包含 Local Search、Global Search、DRIFT Search、Basic Search 和 Question Generation，其中前三个构成 GraphRAG 的核心查询模式。

这件事重要，因为它说明 GraphRAG 的目标并不是“把向量库换成图数据库”。  
GraphRAG 真正解决的是：当问题需要理解整个语料集的组织结构时，单纯靠 top-k chunk 无法稳定提供足够视野。

Microsoft 当前 indexing dataflow 也进一步说明了这一点。GraphRAG 的知识模型包含：

- Document
- TextUnit
- Entity
- Relationship
- Covariate
- Community
- Community Report

默认索引流程从文档切成 TextUnits 开始，再抽取 entities、relationships 和 optional claims，然后做 community detection，最后生成 community reports，并对 text units、graph outputs、community reports 做 embedding。

这条流程的意义是：  
GraphRAG 不是在 query time 临时拼凑上下文，而是在 index time 就把“局部事实”和“全局结构”预先建模出来。

当企业知识库从几十份 FAQ 变成上千份制度、SOP、会议纪要、工单和风险通报时，这种预建模的价值会快速上升。

## 3. 核心概念与理论

### 3.1 GraphRAG 的问题定义

本书把 GraphRAG 定义为：

> 通过从非结构化文本中抽取实体、关系、声明和社区结构，并在查询时结合图结构与原文证据来生成答案的 RAG 方法。

这个定义强调三件事。

第一，GraphRAG 仍然是 RAG。  
它仍然需要外部知识、检索和 grounded generation。

第二，GraphRAG 的知识单位不再只是 chunk。  
chunk 是 provenance 和原文证据，但 entity、relationship、claim、community report 才是图式推理的关键结构。

第三，GraphRAG 的收益来自预先组织结构。  
它不是在回答时“让模型多想想关系”，而是在索引时把关系和社区显式构建出来。

### 3.2 索引流程

GraphRAG 的典型索引流程可以写成：

```text
Documents
  ↓
TextUnits
  ↓
Entities / Relationships / Claims
  ↓
Graph merge and summarization
  ↓
Communities
  ↓
Community Reports
  ↓
Embeddings over text units, graph outputs, reports
```

Microsoft 文档里的默认 dataflow 还明确指出：

- TextUnit 是用于图抽取的文本块，也用于把概念追溯回原文。
- Entity 是从 TextUnit 中抽取的人、地点、事件或自定义实体。
- Relationship 是实体之间的关系。
- Covariate 可表示带时间边界的 claim。
- Community 是实体图经过层级社区检测后的聚类结构。
- Community Report 是对社区内容的总结，适合人读，也适合下游搜索。

### 3.3 三种查询模式

#### Local Search

Local Search 把 AI 抽取出的知识图谱数据和原始文本 chunks 结合起来回答问题。  
它适合关于特定实体的问题，例如：

> 某个审批角色在实名认证图片导出流程中承担什么职责？

Local Search 的核心是局部实体和相关原文证据。

#### Global Search

Global Search 在所有 AI 生成的 community reports 上做 map-reduce 式搜索。  
它适合需要理解整个数据集的问题，例如：

> 公司现有制度中，个人信息出境、外部供应商处理、模型训练数据使用之间最主要的风险主题是什么？

Global Search 的核心是全局社区摘要，而不是单个 chunk。

#### DRIFT Search

DRIFT Search 在 local search 中引入 community information，扩大查询起点，并用 community insights 将问题细化成后续问题。  
它适合介于 Local 与 Global 之间的问题：

> 实名认证图片导出规则变化，会怎样影响供应商处理、模型训练、客服质检这几类流程？

它不是纯局部，也不是全局泛化，而是从局部问题出发，借助社区信息扩展事实覆盖。

### 3.4 GraphRAG 与 Hybrid RAG 的边界

Hybrid RAG 的问题单位是 query-to-chunk。  
GraphRAG 的问题单位是 query-to-structure。

| 问题类型 | Hybrid RAG | GraphRAG |
|----------|------------|----------|
| 单条制度问答 | 很适合 | 通常过重 |
| 精确条款引用 | 很适合 | 需要回退到原文 |
| 多制度影响分析 | 容易漏全局关系 | 适合 |
| 主题归纳 | 依赖召回片段质量 | 更适合 |
| 跨实体关系探索 | 需要多轮 agentic 补救 | 更适合 |
| 高频更新小知识库 | 成本较低 | 可能过重 |

这张表的核心结论是：  
GraphRAG 不是 Hybrid RAG 的替代品，而是解决另一类问题结构。

### 3.5 不要把 GraphRAG 等同于知识图谱项目

传统知识图谱项目常常追求稳定 ontology、严格 schema、人工治理和长期主数据管理。  
GraphRAG 的工程目标更窄：为 RAG 构造更好的检索与综合上下文。

因此，在本书里，GraphRAG 不追求把企业所有知识都建成完美图谱。  
它只在需要全局理解、跨实体关系、社区摘要和影响分析时出现。

## 4. 系统设计与工程实现

### 4.1 GraphRAG 系统架构

```text
文档集合
  ↓
TextUnit composer
  ↓
Entity / Relationship / Claim extractor
  ↓
Graph builder
  - merge duplicate entities
  - summarize entity descriptions
  - summarize relationship descriptions
  ↓
Community detection
  ↓
Community report generation
  ↓
Query engine
  - Local Search
  - Global Search
  - DRIFT Search
```

### 4.2 索引阶段的关键工件

| 工件 | 作用 | 常见风险 |
|------|------|----------|
| TextUnit | 原文证据与图抽取输入 | chunk 太大导致抽取低保真 |
| Entity | 图节点 | 同名实体合并错误 |
| Relationship | 图边 | 关系描述过泛或方向错误 |
| Claim / Covariate | 带状态或时间的信息 | claim 抽取需要调 prompt |
| Community | 图结构聚类 | 社区层级过粗或过细 |
| Community Report | 全局查询的主要语料 | 摘要失真会放大全局错误 |

### 4.3 Query Router

GraphRAG 系统不应该对所有问题都默认 Global Search。  
需要一个 query router：

```text
if query asks about a specific entity:
    use Local Search
elif query asks about whole corpus themes:
    use Global Search
elif query starts local but needs broader relationship coverage:
    use DRIFT Search
else:
    fallback to Hybrid RAG or Basic Search
```

### 4.4 GraphRAG 的 provenance 设计

GraphRAG 的一个常见风险是：社区报告读起来很有洞察，但离原文越来越远。  
因此系统必须保留 provenance：

- Community Report 应能追溯到 community
- Community 应能追溯到 entities / relationships
- Entities / relationships 应能追溯到 TextUnits
- TextUnits 应能追溯到 Documents

没有这条链路，GraphRAG 很容易变成“看起来结构化，实际上不可审计”的系统。

### 4.5 与前面系统的组合方式

GraphRAG 不需要替换前面的 Hybrid RAG。  
更合理的架构是：

```text
Question
  ↓
Question type classifier
  ├─ factual / clause-level -> Hybrid RAG
  ├─ complex multi-hop -> Agentic RAG
  └─ global / relational -> GraphRAG
```

这保持了 KISS：让每条路线处理自己擅长的问题。

## 5. 关键技术选型

### 5.1 什么时候上 GraphRAG

以下情况通常值得考虑 GraphRAG：

- 问题需要跨文档、跨实体、跨制度综合
- 业务目标是影响分析、主题总结、风险发现
- 单纯 top-k chunk 经常缺少全局视野
- 用户关心“哪些因素相互影响”，而不只是“某条规则是什么”

### 5.2 什么时候不要上 GraphRAG

以下情况不应优先上 GraphRAG：

- 知识库很小
- 主要问题是 FAQ 和精确条款问答
- 文档高频更新，预算又很紧
- 无法承受索引阶段 LLM 抽取成本
- 没有能力评估社区报告质量

### 5.3 Local / Global / DRIFT 怎么选

| 查询模式 | 适合问题 | 主要上下文 |
|----------|----------|------------|
| Local Search | 特定实体、具体关系、局部证据 | entities + relationships + text chunks |
| Global Search | 整体主题、全局总结、跨社区分析 | community reports |
| DRIFT Search | 局部问题需要社区扩展 | local facts + community insights + follow-up questions |

### 5.4 不适用边界

GraphRAG 不适合承担以下目标：

- 作为所有 RAG 查询的默认入口
- 替代精确关键词和条款检索
- 替代权限系统
- 在无评估闭环的情况下自动生成管理结论
- 在文档质量很差时直接生成高可信社区报告

GraphRAG 的能力很强，但它的错误也更“像洞察”。这正是它必须被评估和审计的原因。

## 6. 实战案例

### 6.1 案例 B：跨制度影响分析

案例 B 的问题是：

> 如果公司收紧“实名认证图片不得导出本地”的规则，会影响哪些制度、流程、角色和系统？

这个问题用 Hybrid RAG 很容易出错。  
Hybrid RAG 可能召回：

- 实名认证图片导出条款
- 外部供应商处理条款
- 模型训练数据限制条款
- 客服质检流程条款

但它很难稳定回答“这些制度之间如何相互影响”。

### 6.2 GraphRAG 索引

从文档中抽取实体：

- 实名认证图片
- 本地环境
- OCR 标注
- 外部供应商
- 数据安全负责人
- 法务负责人
- 模型训练数据
- 客服质检流程

抽取关系：

- 实名认证图片 属于 高敏感个人信息
- 导出本地 需要 例外审批
- 外部供应商处理 需要 供应商准入
- 审批通过后副本 需要 七日内销毁
- 模型训练 使用 受限数据需额外备案

形成社区：

- 高敏感数据导出社区
- 外部供应商处理社区
- 模型训练合规社区
- 客服质检流程社区

生成社区报告后，Global Search 可以回答：

- 哪些社区受影响
- 哪些实体是桥接点
- 哪些流程可能需要同步更新

### 6.3 三种查询模式的使用

| 用户问题 | 查询模式 |
|----------|----------|
| 数据安全负责人在导出审批中负责什么 | Local Search |
| 这批制度整体上反映了哪些数据治理风险 | Global Search |
| 实名认证图片导出规则变化会波及哪些流程 | DRIFT Search |

### 6.4 示例结果

| 方案 | global coverage | relation correctness | citation correctness | latency | index cost |
|------|-----------------|----------------------|----------------------|---------|------------|
| Hybrid RAG | 中 | 低中 | 高 | 中 | 低 |
| Agentic RAG | 中高 | 中 | 中高 | 高 | 中 |
| GraphRAG | 高 | 高 | 中高 | 高 | 高 |

这个结果展示的是边界：GraphRAG 在全局覆盖和关系正确性上更有优势，但索引成本、查询复杂度和评估难度也更高。

## 7. 评估方法

### 7.1 本章实验目标

本章验证的不是 GraphRAG 是否“更高级”，而是它是否在全局问题上比 Hybrid / Agentic 更合适。

### 7.2 推荐指标

| 层级 | 指标 | 本章重点 |
|------|------|----------|
| 检索层 | entity recall、relationship recall、community coverage | 图结构是否覆盖关键实体和关系 |
| 上下文层 | community report relevance、context diversity | 是否覆盖多个相关社区 |
| 生成层 | faithfulness、citation correctness、relation correctness | 结论是否能回到原文证据 |
| 系统层 | indexing cost、query latency、update latency | 图式方法的代价是否可接受 |

### 7.3 评估集设计

GraphRAG 评估集必须包含三类问题：

- local entity questions
- global theme questions
- local-to-global impact questions

如果只用普通 FAQ 来评估 GraphRAG，会严重低估它的优势，也可能掩盖它的成本问题。

## 8. 常见失败模式

### 8.1 把所有查询都路由到 GraphRAG

这是最直接的过度设计。  
单条制度问答用 Hybrid RAG 往往更快、更准、更可控。

### 8.2 Entity 合并错误

同名实体、简称、部门名、系统名很容易被误合并。  
一旦图节点错，后续关系和社区都会被污染。

### 8.3 Community Report 过度概括

社区报告如果太泛，会让 Global Search 生成漂亮但不可执行的高层话术。

### 8.4 缺少 provenance

如果全局结论无法追溯到 TextUnit 和 Document，GraphRAG 在企业场景里很难被采信。

### 8.5 忽略索引更新成本

GraphRAG 的强项来自 index-time 建模。  
如果语料每天大规模变化，更新成本可能成为真正瓶颈。

## 9. 与下一章的衔接

GraphRAG 解决了从局部检索到全局理解的问题，但代价也很清楚：索引重、抽取贵、更新复杂、评估难。接下来要回答的问题不是“GraphRAG 是否强”，而是“当 GraphRAG 太重时，能否保留图式 RAG 的核心收益，同时把索引与更新成本降下来”。


# 第 7 章 LightRAG 与图式 RAG 的轻量化演进

## 1. 本章要解决的问题

第 6 章已经说明，GraphRAG 能解决 Hybrid RAG 和 Agentic RAG 难以稳定处理的全局理解问题。  
但它也带来一个现实问题：重。

重体现在四个方面：

1. 索引阶段需要抽取大量实体和关系。
2. 社区检测和社区报告生成需要额外成本。
3. 图结构更新不如普通向量索引直接。
4. 评估和排障比 chunk-based RAG 更复杂。

因此，本章要解决的问题是：当标准 GraphRAG 太重时，如何设计更轻量的图式 RAG。

LightRAG 的价值就在这里。  
它不是要否定 GraphRAG，而是提出一种更轻量的图增强检索路径：保留实体关系图、低/高层检索和增量更新能力，同时降低完整图式建模的成本。

## 2. 为什么这个问题在今天重要

LightRAG 的论文和项目页把问题说得很直接：传统 RAG 依赖 flat data representations，缺乏足够的 contextual awareness，容易在复杂依赖问题上给出碎片化答案。  
LightRAG 引入 graph structures 到 text indexing 和 retrieval 过程中，并采用 dual-level retrieval，同时结合 graph structures 与 vector representations，以提升效率和上下文相关性。

它还特别强调 incremental update algorithm。  
这点对企业场景很关键，因为真实知识库很少是一次性静态语料：

- 制度会更新
- SOP 会改版
- 工单会新增
- 风险通报会追加
- 组织和角色会调整

如果每次增量更新都要重建完整 GraphRAG 索引，工程成本很容易超过收益。  
所以本章的重要性在于，它把第 6 章的“图式全局理解”拉回到一个更现实的问题：如何在动态语料里保留足够的图结构，而不把系统拖成重型知识图谱项目。

## 3. 核心概念与理论

### 3.1 什么是轻量图式 RAG

本书把轻量图式 RAG 定义为：

> 在不完整构建重型社区报告体系的前提下，利用实体、关系、局部图邻域、低/高层检索和增量更新机制，增强 RAG 对跨片段依赖的理解能力。

这个定义强调“够用”，而不是“完整”。

### 3.2 LightRAG 的三个关键思想

#### Graph-based Text Indexing

LightRAG 从文本中抽取实体和关系，并通过去重减少图操作开销。  
项目页中还提到，它会用 LLM profiling 为实体节点和关系边生成 key-value 形式的表示：key 用于高效检索，value 用于生成时提供信息。

#### Dual-level Retrieval

LightRAG 把查询分成更具体和更抽象的两类，并采用 low-level retrieval 与 high-level retrieval：

- Low-level retrieval 聚焦具体实体、属性、关系
- High-level retrieval 聚焦更抽象的主题、概念、整体关系

这让系统同时具备局部深度和全局广度。

#### Incremental Update

LightRAG 强调增量更新：新文档按同样图式索引步骤处理，再与已有节点和边合并，而不是每次全量重建。  
这对持续更新语料非常关键。

### 3.3 LightRAG 与 GraphRAG 的差异

| 维度 | 标准 GraphRAG | LightRAG / 轻量图式 RAG |
|------|---------------|-------------------------|
| 目标 | 全局结构理解与社区报告 | 更低成本地增强实体关系检索 |
| 索引 | 更完整的实体、关系、社区、报告 | 更强调图索引、key-value、低/高层检索 |
| 更新 | 全量/批量更新成本较高 | 强调增量更新 |
| 查询 | Local / Global / DRIFT | Low-level / High-level / Hybrid retrieval |
| 适用 | 大规模综合分析 | 动态知识库、成本敏感场景 |

### 3.4 轻量化不是简化成 Hybrid RAG

轻量图式 RAG 不能退化成“加一点 metadata 的 hybrid search”。  
它至少要保留三类图式能力：

1. 实体和关系显式建模
2. 可沿关系扩展上下文
3. 能在具体实体和高层主题之间切换检索视角

如果没有这三点，它只是普通 RAG 的 metadata 增强，不是图式 RAG。

## 4. 系统设计与工程实现

### 4.1 轻量图式索引流程

```text
Documents
  ↓
Chunks / TextUnits
  ↓
Entity and relationship extraction
  ↓
Deduplication
  ↓
Entity KV index
Relationship KV index
Vector index
  ↓
Incremental merge
```

与第 6 章相比，这里可以暂时不生成完整 community reports，或只为高价值主题生成轻量报告。

### 4.2 低/高层检索管线

```text
query
  ↓
query type detection
  ├─ low-level
  │   └─ retrieve entities + local relationships + source chunks
  ├─ high-level
  │   └─ retrieve themes + relation groups + abstract keys
  └─ hybrid
      └─ combine low-level and high-level contexts
  ↓
rerank / context packing
  ↓
answer generation
```

### 4.3 增量更新设计

增量更新至少要处理四类情况：

| 更新类型 | 处理方式 |
|----------|----------|
| 新实体 | 新增节点 |
| 已有实体新描述 | 合并描述并更新时间 |
| 新关系 | 新增边 |
| 已有关系变化 | 记录版本或状态，不直接覆盖旧事实 |

特别是制度场景，不能简单把旧边删除。  
很多关系是 time-bound 的：过去有效、现在失效、未来生效。  
轻量系统也必须保存版本和生效时间。

### 4.4 与前面系统的组合

轻量图式 RAG 可以作为 GraphRAG 与 Hybrid RAG 之间的中间层：

```text
simple factual -> Hybrid RAG
complex controlled -> Agentic RAG
global and stable -> GraphRAG
global-ish and dynamic -> LightRAG / lightweight graph RAG
```

这个分流很重要。  
否则 LightRAG 很容易被误用成“所有问题都加点图结构”。

## 5. 关键技术选型

### 5.1 何时选择 LightRAG / 轻量图式 RAG

适合场景：

- 需要实体关系，但不需要完整社区报告
- 语料持续更新
- 成本不能支撑频繁重建 GraphRAG
- 查询既有具体实体，也有高层主题
- 希望保留图式能力，但部署团队较小

### 5.2 何时仍应选择标准 GraphRAG

如果目标是：

- 全库主题洞察
- 高层社区报告
- 大规模影响分析
- 分析型而非问答型使用

标准 GraphRAG 仍然更合适。

### 5.3 何时退回 Hybrid RAG

如果问题主要是：

- 单条制度引用
- FAQ
- 精确编号和字段检索
- 小知识库问答

轻量图式 RAG 仍然可能过度设计。

### 5.4 不适用边界

轻量图式 RAG 不适合：

- 要求完整、可治理企业知识图谱的场景
- 需要严格本体和主数据管理的场景
- 高风险自动决策且缺少人工审计的场景
- 图抽取质量无法验证的语料

它的正确定位是“工程折中”，不是“图谱治理终局”。

## 6. 实战案例

### 6.1 继续案例 B：跨制度影响分析

在第 6 章中，我们用标准 GraphRAG 分析：

> 实名认证图片导出规则变化，会影响哪些制度、流程、角色和系统？

现在加入一个新约束：

> 这些制度每周都有更新，且团队无法承受频繁全量重建 GraphRAG 索引。

这时 LightRAG / 轻量图式 RAG 更有意义。

### 6.2 轻量图式建模

保留关键实体：

- 实名认证图片
- 外部供应商
- OCR 标注
- 本地副本
- 模型训练数据
- 数据安全负责人
- 法务负责人

保留关键关系：

- 属于
- 需要审批
- 需销毁
- 受供应商准入限制
- 受模型训练备案限制

但暂时不为所有社区生成完整 report，只为高价值主题维护轻量 profile：

- 高敏感数据导出
- 供应商处理
- 模型数据使用

### 6.3 增量更新流程

当新增一条制度更新：

> 自 2026-05-01 起，所有外部供应商参与的图片处理任务必须完成供应商数据处理备案。

系统只需要：

1. 抽取实体“外部供应商”“图片处理任务”“供应商数据处理备案”
2. 抽取关系“外部供应商参与图片处理任务 -> 需要供应商数据处理备案”
3. 与既有供应商处理关系合并
4. 更新相关 key-value profile
5. 重新索引受影响的局部结构

不需要全量重建整个图。

### 6.4 示例对比

| 方案 | relation coverage | update latency | indexing cost | answer comprehensiveness | 适用性 |
|------|-------------------|----------------|---------------|--------------------------|--------|
| Hybrid RAG | 低中 | 低 | 低 | 中 | 简单查询 |
| GraphRAG | 高 | 高 | 高 | 高 | 稳定大语料分析 |
| LightRAG | 中高 | 中低 | 中 | 中高 | 动态语料 |

这个结果的重点是：  
LightRAG 不是绝对最强，而是在“图式能力”和“工程成本”之间取得更好的平衡。

## 7. 评估方法

### 7.1 本章实验目标

本章要验证的是：

1. 是否保留了足够的实体关系覆盖
2. 是否明显降低了索引和更新成本
3. 是否在动态语料中保持回答质量

### 7.2 推荐指标

| 层级 | 指标 | 本章重点 |
|------|------|----------|
| 检索层 | entity recall、relationship recall、low/high retrieval hit rate | 低/高层检索是否都有效 |
| 上下文层 | context diversity、relation completeness | 是否覆盖必要实体关系 |
| 生成层 | comprehensiveness、faithfulness、citation correctness | 答案是否完整且可追溯 |
| 系统层 | incremental update latency、indexing cost、API call count | 轻量化是否真的降低代价 |

### 7.3 评估集设计

评估集必须包含更新前后对比：

- 更新前问题
- 新增文档后问题
- 关系变化问题
- 高层主题问题
- 具体实体问题

否则无法验证 incremental update 的真实价值。

## 8. 常见失败模式

### 8.1 轻量化过头

如果只保留实体，不保留关系，系统就退化成 entity tagging，不再是图式 RAG。

### 8.2 增量合并污染历史

新关系不能直接覆盖旧关系。  
制度和流程通常有时间边界，必须保留版本。

### 8.3 低层和高层检索失衡

只做 low-level，会缺少全局视野。  
只做 high-level，会丢具体证据。

### 8.4 缺少图抽取评估

轻量图式 RAG 的最大风险不是检索错，而是图构错。  
错误节点和边会持续污染后续查询。

### 8.5 把 LightRAG 当成标准 GraphRAG 的廉价替代

LightRAG 是折中方案，不是无损压缩。  
如果业务需要完整全局社区分析，仍然应回到标准 GraphRAG。

## 9. 与下一章的衔接

到这里，三条 RAG 路线已经基本展开：Plain / Hybrid 解决局部证据检索，Agentic / Reflective 解决运行时控制流，GraphRAG / LightRAG 解决知识组织方式。但无论选择哪条路线，真实企业输入都不会是干净 Markdown。下一章要处理的共同瓶颈，是 PDF、表格、图片、扫描件和复杂版式带来的 ingestion 质量问题。


# 第 8 章 多模态与复杂文档 RAG

## 1. 本章要解决的问题

前面章节默认语料已经被整理成较干净的文本。  
真实企业环境通常不是这样。

真实知识来源往往包括：

- 扫描 PDF
- 图文混排报告
- 合同附件
- 表格制度
- 图片截图
- 多页审批单
- PPT 导出的 PDF
- 带脚注、页眉、页码和水印的文档

这类输入如果解析不好，后面的 chunking、hybrid retrieval、rerank、agentic control、GraphRAG 都会被污染。

因此，本章要解决的问题是：如何把复杂文档 ingestion 视为 RAG 系统的一等工程环节，而不是把它当成“读文件”。

## 2. 为什么这个问题在今天重要

NVIDIA 当前 RAG Blueprint 文档已经把复杂文档能力作为系统能力来组织：包括 enhanced PDF extraction、OCR configuration、multimodal embedding support、image captioning、multimodal query support 等。  
它的 Nemotron Parse extraction 文档明确指出，复杂 PDF、扫描文档、复杂布局场景可以启用 Nemotron Parse；表格抽取也可以配置为 Nemotron Parse，且该服务需要 GPU 资源。

这说明复杂文档 RAG 已经不是边缘问题。  
企业知识的主体经常在 PDF 和表格里，而不是在干净纯文本里。

更关键的是，文档解析错误通常不会在 ingestion 阶段立刻暴露。  
它会在后面变成：

- 检索不到
- 召回错页
- 表格列错位
- 引用页码错误
- 数值和单位错配
- 图片说明缺失
- 多页上下文断裂

这些问题表面看是 RAG 质量问题，本质却是 ingestion 质量问题。

## 3. 核心概念与理论

### 3.1 复杂文档 RAG 的关键假设

本章的核心假设是：

> 文档解析质量决定检索质量上限。

如果文本抽取阶段已经把表格列错位，后面再好的 reranker 也只能排序错误内容。  
如果 OCR 阶段漏掉页脚里的生效时间，后面的版本判断就会失败。

### 3.2 文档解析的五层结构

复杂文档 ingestion 应至少保留五层信息：

| 层级 | 示例 | 作用 |
|------|------|------|
| 文本层 | 段落、标题、脚注 | 基础检索 |
| 版式层 | 页码、区域、阅读顺序 | 还原上下文 |
| 结构层 | 表格、列表、章节 | 正确切块 |
| 视觉层 | 图片、图表、扫描文字 | 多模态证据 |
| 元数据层 | 文件名、版本、生效日期、权限 | 过滤与治理 |

普通文本抽取往往只保留第一层。  
复杂文档 RAG 至少要保留前三层，高风险场景还要处理视觉层。

### 3.3 表格不是普通文本

表格常见错误包括：

- 表头丢失
- 单元格错列
- 合并单元格展开错误
- 多页表格断裂
- 单位与数值分离

如果把表格直接拍平成一段文本，检索可能还能命中关键词，但生成时很容易读错关系。

表格应优先被转成结构化 representation：

```json
{
  "page": 12,
  "table_id": "t_12_1",
  "caption": "数据导出审批权限矩阵",
  "columns": ["数据等级", "审批角色", "保留期限"],
  "rows": [
    ["高敏感个人信息", "数据安全负责人 + 法务负责人", "7日内销毁"]
  ]
}
```

### 3.4 页面级摘要的价值

复杂 PDF 中，单页往往是最自然的上下文单元。  
页面级摘要可以帮助系统：

- 快速定位页内主题
- 为 chunk 补充版式上下文
- 给引用提供更稳定的页码锚点
- 在多模态检索中连接图片、表格和文本

页面级摘要不是最终答案，而是检索和上下文装配的辅助索引。

## 4. 系统设计与工程实现

### 4.1 复杂文档 ingestion 流水线

```text
原始文件
  ↓
文件类型识别
  - text PDF
  - scanned PDF
  - DOCX
  - spreadsheet
  - image
  ↓
解析策略选择
  - text extraction
  - OCR
  - layout parser
  - table parser
  - image captioner
  ↓
结构化中间表示
  - pages
  - blocks
  - tables
  - figures
  - metadata
  ↓
page summary / block summary
  ↓
chunking and indexing
  ↓
retrieval and generation
```

### 4.2 文档中间表示

建议所有复杂文档先转成中间表示，而不是直接进 chunker。

```json
{
  "doc_id": "export_policy_pdf",
  "pages": [
    {
      "page_no": 3,
      "summary": "本页说明高敏感个人信息导出审批原则。",
      "blocks": [
        {
          "type": "paragraph",
          "bbox": [72, 120, 520, 180],
          "text": "实名认证图片属于高敏感个人信息..."
        }
      ],
      "tables": [],
      "figures": []
    }
  ]
}
```

### 4.3 Chunking 与复杂结构

复杂文档不应只按 token 切块。  
应按内容类型采用不同策略：

| 内容类型 | 切块策略 |
|----------|----------|
| 普通段落 | 结构感知切分 |
| 表格 | 表级或行组级 chunk |
| 图片 | caption + OCR + 附近文本 |
| 图文混排页 | 页面摘要 + 局部 block |
| 多页表格 | 跨页 table stitching |

### 4.4 引用设计

复杂文档 RAG 的引用至少应包含：

- doc_id
- page_no
- block_id / table_id
- cell range 或 bbox
- extraction_method

这样当答案出错时，才能判断是检索错、解析错、还是生成错。

### 4.5 多模态检索设计

多模态检索不一定意味着所有内容都进同一个 embedding 空间。  
更稳妥的做法是多路索引：

- text index
- table index
- image caption index
- page summary index
- metadata filter

再通过 fusion / rerank 合并候选。

## 5. 关键技术选型

### 5.1 解析工具选择原则

| 场景 | 策略 |
|------|------|
| 数字原生 PDF | text extraction + layout preservation |
| 扫描 PDF | OCR / VLM parser |
| 表格密集文档 | table parser + structure validation |
| 图文混排报告 | page-level layout parser + captions |
| 高风险合规文档 | 保留 page / bbox provenance |

### 5.2 什么时候需要多模态能力

需要多模态能力的信号：

- 答案依赖图片、图表或扫描内容
- 表格列关系比正文更重要
- 版式和位置决定语义
- 文档中大量信息不是可复制文本

如果文档本身是干净 Markdown 或 DOCX，先不要过早引入多模态复杂度。

### 5.3 不适用边界

本章方法不适合被无差别套用：

- 纯文本知识库不需要复杂 PDF 解析
- 小批量临时分析可以用人工预处理
- 表格极少时不必建设完整 table pipeline
- 多模态 embedding 如果缺少评估，会增加不可解释风险

复杂 ingestion 的成本应由文档复杂度和错误代价共同决定。

## 6. 实战案例

### 6.1 案例 C：复杂 PDF 与表格问答

案例 C 的文档是一份 80 页 PDF：

- 前 20 页是数据治理制度
- 中间 30 页是审批流程图和责任矩阵
- 后 20 页是表格化的例外场景
- 最后 10 页是扫描版历史附件

问题是：

> 高敏感个人信息导出到供应商环境时，审批角色、保留期限和销毁证明要求分别是什么？

这个问题依赖：

- 正文规则
- 表格权限矩阵
- 附件说明
- 页级版本信息

### 6.2 三种 ingestion 方案

| 方案 | 做法 | 风险 |
|------|------|------|
| A | 直接抽纯文本 | 表格错位，页码丢失 |
| B | 文本 + 表格结构化 | 能回答矩阵问题，但图片流程仍缺失 |
| C | 页面级解析 + 表格 + 图片 caption + 元数据 | 成本更高，但证据链完整 |

### 6.3 示例输出结构

一个合格答案应类似：

```text
结论：
- 高敏感个人信息导出到供应商环境默认不允许，需走例外审批。

审批角色：
- 数据安全负责人
- 法务负责人
- 供应商管理负责人

保留期限：
- 原则上 7 日内销毁本地副本。

销毁证明：
- 需提交供应商处理记录和销毁证明。

引用：
- export_policy.pdf p.18 table t_18_2
- export_policy.pdf p.34 block b_34_5
```

如果引用只能定位到整份 PDF，而不能定位到页和表，这个系统还不够可审计。

## 7. 评估方法

### 7.1 本章实验目标

本章验证的是 ingestion 改动是否改善了后续检索与生成，而不是单独比较 OCR 字符准确率。

### 7.2 推荐指标

| 层级 | 指标 | 本章重点 |
|------|------|----------|
| 检索层 | page recall、table recall、figure recall | 是否能命中正确页、表、图 |
| 上下文层 | structure preservation、context precision | 表格和版式是否保持语义 |
| 生成层 | citation correctness、numeric correctness、faithfulness | 答案是否引用正确位置并保留数值 |
| 系统层 | ingestion latency、parse failure rate、GPU cost | 复杂解析是否值得 |

### 7.3 坏例分桶

| 坏例桶 | 表现 |
|--------|------|
| table shift | 表格列错位导致答案错 |
| page miss | 检索命中错误页 |
| OCR drop | 扫描件关键文字漏识别 |
| image blind spot | 图里有关键流程但系统看不到 |
| citation too coarse | 引用只能到文档，不能到页/表/块 |

## 8. 常见失败模式

### 8.1 把 PDF 当纯文本

这是复杂文档 RAG 的第一大坑。  
PDF 是版式容器，不是天然语义文本。

### 8.2 表格拍平后失去关系

表格中的“行列关系”往往比单元格文本更重要。  
拍平之后，模型可能知道所有词，但不知道谁对应谁。

### 8.3 忽略页码和位置

企业问答里，引用必须可审计。  
没有 page / bbox / table_id，citation correctness 很难真正评估。

### 8.4 多模态能力缺少路由

不是所有 query 都需要图像模型。  
如果不做路由，系统会变慢、变贵，也更难排障。

### 8.5 解析质量不进评估

如果只评估最终答案，不评估解析中间产物，很多错误会被误判成检索或生成问题。

## 9. 与下一章的衔接

复杂文档解决的是“知识如何进入系统”的问题。但真正上线后，系统还要持续摄取新文档、处理权限边界、记录调用链路、支持回放排障，并在托管能力和自建检索栈之间做长期取舍。下一章不再引入新算法路线，而是把前面所有能力收束到生产部署和长期维护。


# 第 9 章 评估驱动优化

## 1. 本章要解决的问题

如果说前四章已经把系统从“能回答”推到了“回答得更像样”，那么第 9 章要解决的是一个更底层的问题：

> 系统究竟为什么变好，为什么变差，下一步该改哪里？

没有评估闭环，RAG 优化几乎一定会退化成三种低效模式：

1. 靠体感调参
2. 靠 demo 挑例子
3. 靠单次成功回答自我说服

这三种模式都无法支撑后面的高级路线，因为一旦进入 agentic/reflective 控制流，系统变量会更多、成本会更高、失败形态也会更复杂。

因此，本章要做的不是“再发明一套指标”，而是把全书统一改造成 experiment-first 的工程写法：

1. 每一章只改一个关键系统变量。
2. 每一次改动都要有可复用评估集。
3. 每一层指标都要能解释收益和代价。
4. 每一次失败都要进入坏例分桶，而不是停留在聊天记录里。

## 2. 为什么这个问题在今天重要

Ragas 当前 experimentation 文档对 experiment 的定义非常适合作为本书统一方法论：  
一次 experiment，就是对系统做一个有意改动，用可测量指标验证这个改动是否真的产生预期影响。

这一定义重要，因为它直接反对了 RAG 工程里最常见的模糊优化方式。

当前 Ragas 文档把 good experiment 的四条原则写得很实用：

1. measurable metrics
2. systematic result storage
3. isolate changes
4. iterative cycle: make change -> run evaluations -> observe results -> hypothesize next change

这四条原则几乎可以直接翻译成本书的章节组织规则。  
它们也解释了为什么本章必须在第 5 章之前出现：如果不先把“如何证明优化有效”固定下来，后面 query decomposition、reflection、multi-step control flow 的引入，就很容易从工程演进变成系统膨胀。

今天这个问题尤其重要，还有两个现实原因。

第一，托管检索、rerank、agentic 组件越来越容易拿到。  
系统复杂度上升的门槛变低了，但真正理解系统改动带来什么收益，门槛并没有降低。

第二，RAG 问题已经不只是一个准确率问题。  
它同时涉及：

- 检索是否召回到对的证据
- 上下文是否被正确组装
- 生成是否 grounded
- runtime 是否超出时延和成本预算

所以评估必须分层，而不能只看最终回答像不像对。

## 3. 核心概念与理论

### 3.1 什么是一次“好实验”

按照本书的写法，一次好实验必须同时满足四个条件：

1. 改动单一
2. 指标可测
3. 结果可回放
4. 失败可归因

也就是说，实验不是“换一个配置再跑一遍”，而是一次可解释的系统改动。

### 3.2 四层指标体系

本书统一采用四层指标。

#### 检索层

- Recall@k
- MRR
- nDCG

它回答的是：系统有没有把证据召回来。

#### 上下文层

- context relevance
- context precision
- context recall

它回答的是：召回回来的东西，是否真的构成了回答所需的上下文。

#### 生成层

- faithfulness
- answer relevance
- citation correctness

它回答的是：模型生成是否真正被上下文支撑。

#### 系统层

- latency
- token cost
- failure rate
- fallback rate

它回答的是：这个系统是否值得长期运行。

### 3.3 坏例比平均分更重要

平均分当然重要，但真正驱动工程改进的往往不是平均分，而是稳定复现的失败模式。

因此，本书把坏例分桶视为和指标同等重要的工件。  
每一个坏例桶都应该满足：

1. 可重复出现
2. 可指向具体系统层面
3. 能指导下一章改动

### 3.4 Chapter-as-experiment 的写法

为了让整本书真正成为实验驱动工程，本书统一采用“章节即实验”的写法。

| 章节 | 核心改动 |
|------|----------|
| 第 2 章 | 从无到有建立最小 RAG |
| 第 3 章 | 重做 chunking 与索引 |
| 第 4 章 | 增加 hybrid + fusion + rerank |
| 第 5 章 | 引入 query rewrite / decomposition / reflection |
| 第 6 章 | 重构知识组织方式为 GraphRAG |

这种写法的好处是，读者不会把全书读成“技巧列表”，而会读成一条系统演进链。

## 4. 系统设计与工程实现

### 4.1 统一实验流水线

本章固定一条实验流水线，后续所有章节都沿用。

```text
定义系统版本
  ↓
定义改动假设
  ↓
准备评估集
  ↓
运行系统
  - 记录 query
  - 记录 retrieved chunks
  - 记录 final context
  - 记录 answer
  - 记录 latency / token / errors
  ↓
计算指标
  ↓
坏例分桶
  ↓
决定下一次改动
```

### 4.2 实验记录的最小字段

一个最小但够用的实验记录，至少应该保存：

```json
{
  "experiment_name": "hybrid_rrf_rerank_v1",
  "system_version": "v4",
  "query": "...",
  "expected_answer": "...",
  "retrieved_chunks": [...],
  "final_context": [...],
  "response": "...",
  "metrics": {
    "recall_at_5": 0.8,
    "faithfulness": 0.9
  },
  "latency_ms": 1430,
  "token_cost": 0.012,
  "error": null
}
```

如果没有这些字段，后面几乎不可能做系统级归因。

### 4.3 Bad Case Registry

建议把坏例单独维护成一个 registry，而不是散落在评论或截图里。

```text
bad_cases/
  retrieval_miss.jsonl
  context_noise.jsonl
  citation_error.jsonl
  stale_policy.jsonl
  complex_query_failure.jsonl
```

每一条坏例至少要记录：

- query
- 期望答案
- 实际答案
- 检索结果
- 失败桶标签
- 首次发现版本

### 4.4 实验命名与版本纪律

Ragas 文档强调 consistent naming 和 result storage，这一点在工程里远比看起来重要。

建议命名统一包含：

- 改了什么
- 第几个版本
- 日期或时间戳

例如：

```text
baseline_v1
chunk_structured_v2
hybrid_rrf_v3
hybrid_rrf_rerank_v4
agentic_reflective_v5
```

如果实验命名混乱，半年后你甚至很难知道哪个结果对应哪次系统改动。

### 4.5 评估集的构成

本书建议评估集始终由三部分组成：

1. 黄金问题集
2. 生产坏例回放集
3. 新增挑战集

#### 黄金问题集

用于保证系统基本能力不倒退。

#### 生产坏例回放集

用于验证当前改动是否真的修复旧问题。

#### 新增挑战集

用于观察系统边界是否继续外扩。

## 5. 关键技术选型

### 5.1 优先评估什么

当资源有限时，评估优先级应按下面顺序展开：

1. 先记录检索结果
2. 再记录最终上下文
3. 再记录生成答案
4. 最后记录 runtime 成本

理由很简单：  
如果没有前两层，生成层问题几乎无法定位。

### 5.2 离线评估与线上观测的关系

本书默认先做离线评估，再谈线上观测。  
因为你必须先有一套稳定、可重复的离线判断标准，线上数据才有比较意义。

但离线评估也不是万能的，它的边界包括：

- 它无法完整覆盖真实问题分布
- 它可能遗漏新类型输入
- 它容易被小样本偶然性误导

所以后续到第 10 章会再把离线评估接到线上回放与观测。

### 5.3 推荐的技术纪律

| 纪律 | 原因 |
|------|------|
| 一次只改一个关键变量 | 避免收益无法归因 |
| 指标与坏例并存 | 平均分不能替代失败模式 |
| 实验结果必须落盘 | 否则无法回看 |
| 记录系统版本和配置 | 否则无法复现 |
| 成本指标必须跟质量指标一起看 | 否则优化可能不可部署 |

### 5.4 不适用边界

本章不适合被误解成以下几件事：

- 不是要求每个小改动都做重型 benchmark
- 不是要求先把指标体系做得完美再开始迭代
- 不是要求所有指标都自动化才允许开发

本章真正要求的是：  
从现在开始，任何系统增强都必须留下可比较证据。

## 6. 实战案例

### 6.1 案例 D：生产上线前的评估演练

第 9 章切到案例 D。  
假设案例 A 的企业知识问答系统已经完成三次迭代：

- `baseline_v1`
- `chunk_structured_v2`
- `hybrid_rrf_rerank_v3`

现在目标不是立刻上线，而是回答一个更现实的问题：

> 系统是否已经强到值得继续投入，还是应该进入下一条升级路线？

### 6.2 实验集设计

评估集可以分成三层：

| 集合 | 数量 | 用途 |
|------|------|------|
| gold_qa | 50 | 基础制度问答能力 |
| bad_case_replay | 20 | 检查旧问题是否被修复 |
| complex_query_probe | 15 | 检查复杂查询是否仍然失败 |

这里最关键的是第三层。  
因为它正是下一章是否需要进入 agentic / reflective RAG 的证据来源。

### 6.3 一个示例实验表

| 版本 | Recall@5 | context precision | faithfulness | failure rate | latency | 说明 |
|------|----------|-------------------|--------------|--------------|---------|------|
| baseline_v1 | 0.61 | 0.52 | 0.68 | 0.27 | 低 | 基础系统 |
| chunk_structured_v2 | 0.76 | 0.68 | 0.77 | 0.18 | 低中 | 解决条款边界问题 |
| hybrid_rrf_rerank_v3 | 0.88 | 0.80 | 0.85 | 0.11 | 中 | 检索质量显著提升 |

如果只看这张表，系统似乎已经很好。  
但再看复杂查询探针集，可能会出现另一张表：

| 版本 | complex_query_success | fallback rate | 主要失败类型 |
|------|-----------------------|---------------|--------------|
| baseline_v1 | 0.21 | 0.43 | 问题拆解失败 |
| chunk_structured_v2 | 0.24 | 0.39 | 仍不会拆问题 |
| hybrid_rrf_rerank_v3 | 0.29 | 0.34 | 证据足够，但控制流不足 |

这就是 experiment-first 的真正价值：  
它不只告诉你“系统变好了”，还告诉你“它接下来应该往哪条路线升级”。

### 6.4 从评估结论到下一章决策

对案例 D，这一轮评估最可能给出的结论不是“继续微调 reranker”，而是：

1. 简单制度问答已经基本稳住。
2. 复杂、组合式、带条件的问题仍然失败明显。
3. 这些失败不是检索不到，而是不会拆问题、不会重试、不会校验。

这正是下一章引入 Agentic / Reflective RAG 的理由。

## 7. 评估方法

### 7.1 本章本身如何评估

第 9 章虽然讲评估，但它自己也必须遵守全书规则。  
它的目标不是提升某个单项指标，而是提升后续章节的“优化可信度”。

因此，本章的产出应被评估为：

| 产物 | 验收标准 |
|------|----------|
| 统一实验模板 | 后续章节可直接复用 |
| 坏例分桶 | 能指向下一章系统改动 |
| 指标分层 | 能区分检索、上下文、生成、系统问题 |
| 结果落盘规范 | 能复现实验并做跨版本比较 |

### 7.2 推荐监控字段

- experiment_name
- model_version
- retriever_version
- reranker_version
- query_type
- bad_case_bucket
- latency_ms
- total_tokens
- success
- error

### 7.3 Chapter 9 的核心判断

当一套评估闭环已经建立，团队应该能清楚回答：

1. 这次改动到底改了什么。
2. 指标到底是哪个层面变好了。
3. 失败主要集中在哪类问题。
4. 下一章的改动是否有明确证据支撑。

做不到这四点，就说明系统还没有真正进入 experiment-driven engineering。

## 8. 常见失败模式

### 8.1 一次改太多

同时改 chunk、改 rerank、改 prompt、改模型，最后任何收益都不可归因。

### 8.2 只有平均分，没有坏例桶

平均分会掩盖系统边界。  
真正推动演进的，往往是某一类反复出现的小而稳定的失败。

### 8.3 不存检索和上下文

只存最终回答，等于主动放弃大部分排障能力。

### 8.4 只看质量，不看代价

一个指标更高但 latency 翻倍、cost 翻倍的方案，不一定是更好的系统。

### 8.5 把评估写成仪式

如果评估不能真正改变下一章的设计决策，它就只是一个看起来很工程化的流程装饰。

## 9. 与下一章的衔接

现在，评估闭环已经固定下来了。它给出的最重要结论通常不是“继续把检索调得再细一点”，而是“某一类复杂问题已经超出了静态检索管线的能力边界”。接下来需要升级的，不再只是检索配方，而是控制流本身：系统必须学会改写问题、拆解问题、检查上下文是否相关、检查答案是否 grounded。这就是下一章要进入的 Agentic / Reflective RAG。


# 第 10 章 生产部署——持续摄取、权限、观测与托管/自建决策

## 1. 本章要解决的问题

前面九章解决了 RAG 系统的主要能力问题：

- 如何从 Context Engineering 看待 RAG
- 如何搭最小系统
- 如何优化 chunk 和索引
- 如何做 hybrid、RRF、rerank
- 如何建立评估闭环
- 如何加入 agentic / reflective 控制流
- 如何做 GraphRAG 和轻量图式 RAG
- 如何处理复杂文档

第 10 章要解决的是另一个问题：  
这些能力如何长期运行。

生产部署不是把 notebook 包成 API。  
真正上线后，系统必须回答：

1. 新文档如何持续进入系统。
2. 多团队、多租户、多集合如何隔离。
3. 权限如何跟检索结果绑定。
4. 每次回答如何被观测、回放和排障。
5. 哪些能力托管，哪些能力自建。
6. 在成本、延迟、质量之间如何做长期决策。

## 2. 为什么这个问题在今天重要

当前主流平台已经把很多 RAG 能力产品化。  
OpenAI File Search 是 Responses API 下的 hosted tool，基于 vector stores 使用 semantic + keyword search，并允许限制返回结果数量来权衡质量、token usage 和 latency。  
NVIDIA RAG Blueprint 则提供了更完整的自建/私有化路径，包括 Docker、Helm/Kubernetes、continuous ingestion、multi-collection retrieval、observability、enhanced PDF extraction 等。

这意味着生产部署的核心问题不再是“有没有可用技术”，而是“如何做边界决策”：

- 托管能力快，但可控性有限。
- 自建能力可控，但成本、运维和资源要求高。
- 平台能力越来越完整，但企业仍然需要处理权限、审计、回放、数据治理和上线责任。

第 10 章的目标，就是把这些决策拉回工程现实。

## 3. 核心概念与理论

### 3.1 生产 RAG 的四条控制面

生产系统至少有四条控制面：

| 控制面 | 关注点 |
|--------|--------|
| 数据面 | 摄取、解析、索引、更新、删除 |
| 查询面 | 检索、rerank、生成、fallback |
| 治理面 | 权限、租户、审计、合规 |
| 观测面 | traces、metrics、logs、replay |

缺任何一条，都不能算完整生产系统。

### 3.2 持续摄取

NVIDIA 当前 continuous ingestion 文档给出了一条典型 event-driven pipeline：

1. 文件上传到 object storage。
2. 存储事件发布到 Kafka。
3. Kafka consumer 下载新文件。
4. 文件进入 ingestor。
5. 内容被索引到 vector database。
6. 用户通过 UI 或 API 查询。

这条流水线说明，生产 RAG 的 ingestion 不是一次性脚本，而是持续数据管道。

### 3.3 多集合与多租户

NVIDIA 当前 multi-collection retrieval 文档说明，一个查询可以跨多个 collections 检索，并用 reranker 对不同 collection 的 chunks 做统一排序；同时它也明确了限制：multi-collection retrieval 依赖 reranker，且当前有每次查询最多 5 个 collections 的约束。

这给生产系统两个启发：

1. 多集合不是简单并集，跨集合排序必须有统一 rerank。
2. collection 边界不能随意设计，否则查询性能和权限控制都会失控。

### 3.4 观测与回放

NVIDIA 当前 observability 文档使用 OpenTelemetry Collector 和 Zipkin 做 tracing，并通过 Grafana / Prometheus 暴露 metrics。  
文档还明确提到 pipeline stage 包括 query-rewriter、retriever、context-reranker、llm-stream，并可观察 retrieval time、context reranker time、LLM generation time、TTFT 等。

这正好对应本书的系统观：  
RAG 不是一个黑盒 answer API，而是一条可观测流水线。

### 3.5 托管 vs 自建

托管检索适合：

- 快速验证
- 团队运维资源有限
- 数据治理边界允许
- 检索策略不需要深度定制

自建检索适合：

- 权限、审计、私有化要求强
- 需要复杂 ingestion
- 需要多集合和多租户策略
- 需要控制 embedding、rerank、graph、pipeline traces
- 需要和内部系统深度集成

## 4. 系统设计与工程实现

### 4.1 生产 RAG 总架构

```text
Document sources
  - object storage
  - wiki
  - ticket system
  - data catalog
  ↓
Ingestion pipeline
  - parser
  - OCR / table extraction
  - metadata enrichment
  - permission tagging
  ↓
Indexing layer
  - vector index
  - keyword index
  - graph index
  - metadata store
  ↓
Query runtime
  - router
  - retriever
  - reranker
  - generator
  - reflection / fallback
  ↓
Governance and observability
  - authz
  - traces
  - metrics
  - replay
  - audit log
```

### 4.2 持续摄取设计

一个可用的持续摄取系统至少要支持：

- 新增文档
- 更新文档
- 删除文档
- 版本变更
- 解析失败重试
- 索引状态查询

建议状态机如下：

```text
uploaded
  -> parsing
  -> parsed
  -> chunking
  -> indexing
  -> ready
  -> failed
  -> deleted
```

没有状态机，运维时很难知道某份文档到底为什么查不到。

### 4.3 权限绑定

RAG 权限必须在 retrieval 阶段生效，而不是生成后再过滤。  
否则模型可能已经看到不该看的内容。

最小权限模型：

```json
{
  "doc_id": "export_policy",
  "tenant_id": "risk_team",
  "acl": ["data_security", "legal"],
  "sensitivity": "high",
  "effective_date": "2026-01-01"
}
```

查询时必须把用户身份转换成检索过滤条件：

```text
user identity -> allowed tenants -> allowed collections -> allowed documents -> retrieval
```

### 4.4 观测字段

每次请求至少记录：

- request_id
- user_id / tenant_id
- query
- route
- collections
- retrieved chunk ids
- reranked chunk ids
- final context ids
- answer
- citations
- latency by stage
- token usage
- fallback reason
- error

这些字段不是为了好看，而是为了回放。

### 4.5 回放机制

生产 RAG 必须支持两种回放：

#### 单请求回放

用于排查用户投诉：

- 当时检索到了什么
- 当时模型看到了什么
- 当时为什么 fallback 或 hallucinate

#### 批量回放

用于上线前验证：

- 新 embedding 是否破坏旧查询
- 新 parser 是否提升表格问答
- 新 reranker 是否增加 latency
- 新权限规则是否误杀召回

## 5. 关键技术选型

### 5.1 托管检索 vs 自建检索栈

| 维度 | 托管检索 | 自建检索 |
|------|----------|----------|
| 上线速度 | 快 | 慢 |
| 运维成本 | 低 | 高 |
| 检索可控性 | 中低 | 高 |
| 权限深度集成 | 依平台能力 | 可深度定制 |
| 复杂文档解析 | 依平台能力 | 可自定义 |
| GraphRAG / LightRAG | 通常受限 | 可组合 |
| 观测与回放 | 依平台暴露 | 可完整建设 |

### 5.2 Docker、Helm、Kubernetes 怎么选

| 部署方式 | 适合场景 |
|----------|----------|
| 托管 API | 业务验证、轻量产品、团队资源有限 |
| Docker Compose | 单机实验、内部 demo、pipeline 验证 |
| Kubernetes + Helm | 生产集群、GPU 资源管理、多服务治理 |
| Retrieval-only mode | 已有生成服务，只需要检索能力 |

NVIDIA 当前文档中，Docker hosted-model deployment 适合更快测试；self-hosted deployment 需要显著更多本地磁盘用于模型缓存、容器镜像、向量库和日志；Helm/Kubernetes 更接近生产部署方式，但启动和资源要求也更高。

### 5.3 多集合设计

collection 可以按以下方式划分：

- 按租户
- 按业务域
- 按权限级别
- 按文档类型
- 按更新频率

但不要无限拆。  
跨 collection 检索会增加 rerank 压力和上下文长度风险。  
如果每次查询都要跨太多集合，说明 collection 边界设计可能错了。

### 5.4 不适用边界

本章不引入新算法路线。  
它不适合继续讨论：

- 更复杂的 rerank 模型
- 新的 GraphRAG 变体
- 更深的 agent planner
- 具体云厂商采购建议

本章只回答生产系统如何长期运行、如何治理、如何观测、如何做托管/自建边界。

## 6. 实战案例

### 6.1 案例 D：生产上线演练

现在把前面所有能力整合成一个上线演练：

- 案例 A 的企业知识库问答已具备 Hybrid + Agentic
- 案例 B 的跨制度影响分析支持 GraphRAG / LightRAG
- 案例 C 的复杂 PDF 已有结构化 ingestion
- 第 9 章已经建立评估与坏例回放

目标是上线一个企业内部知识系统。

### 6.2 生产流水线设计

```text
文档上传
  ↓
对象存储事件
  ↓
ingestion worker
  ↓
parse / OCR / table extraction
  ↓
metadata and ACL enrichment
  ↓
index build
  - vector
  - keyword
  - graph optional
  ↓
ready for query
```

### 6.3 查询路径设计

```text
user query
  ↓
authz filter
  ↓
query router
  ├─ Hybrid RAG
  ├─ Agentic RAG
  ├─ GraphRAG
  └─ File Search / managed retrieval
  ↓
rerank and context packing
  ↓
generation
  ↓
groundedness check
  ↓
answer + citations
  ↓
trace + metrics + replay record
```

### 6.4 托管/自建决策样例

| 能力 | 第一阶段选择 | 未来升级 |
|------|--------------|----------|
| 基础文档问答 | 托管 File Search | 如权限/观测不足再自建 |
| 高敏感制度库 | 自建检索 | 深度 ACL + audit |
| 复杂 PDF 解析 | 自建 ingestion | 接入更强 parser |
| 跨制度影响分析 | 自建 GraphRAG / LightRAG | 只对高价值集合启用 |
| 线上观测 | 自建 trace + metrics | 接入统一 APM |

这不是技术洁癖，而是风险分层。

## 7. 评估方法

### 7.1 生产前验收

生产前至少跑四组评估：

| 评估 | 目标 |
|------|------|
| 离线 gold set | 基础能力不退化 |
| bad case replay | 旧问题不复发 |
| permission tests | 不越权召回 |
| load tests | latency 和 cost 可控 |

### 7.2 推荐指标

| 层级 | 指标 | 本章重点 |
|------|------|----------|
| 检索层 | Recall@k、nDCG、cross-collection hit quality | 多集合和权限过滤后是否仍然可用 |
| 上下文层 | context precision、context recall、ACL correctness | 上下文是否相关且合法 |
| 生成层 | faithfulness、citation correctness、refusal correctness | 答案是否可信，缺权限时是否正确拒答 |
| 系统层 | p50/p95 latency、token cost、ingestion lag、failure rate、fallback rate | 是否能长期运行 |

### 7.3 线上观测面板

至少应有这些面板：

- query volume
- p50 / p95 / p99 latency
- retrieval latency
- rerank latency
- generation latency
- token usage
- fallback rate
- no-answer rate
- parser failure rate
- ingestion lag
- permission denial count

## 8. 常见失败模式

### 8.1 把上线当成 demo 部署

demo 能跑，不代表生产能维护。  
缺 ingestion 状态、权限、trace、replay 的系统，很难长期运行。

### 8.2 权限后置过滤

如果模型先看到内容，再在答案里过滤，权限已经泄露。  
权限必须进入 retrieval filter。

### 8.3 不记录最终上下文

只记录用户问题和最终答案，无法排查 hallucination、误召回或 rerank 错误。

### 8.4 多集合无边界

集合拆得太碎，会导致跨集合检索和 rerank 成本失控。  
集合拆得太粗，又会导致权限和租户隔离困难。

### 8.5 托管/自建决策一次性定死

托管和自建不是信仰选择。  
一个成熟系统可以同时使用托管 File Search 做低风险知识库，用自建 pipeline 处理高敏感、复杂文档和图式分析。

## 9. 与下一章的衔接

第 10 章是本书的终点，不再引出额外总结章。生产部署把前面所有章节的能力收束为一套长期运行的上下文系统：数据持续进入，检索受权限约束，回答可追溯，失败可回放，质量和成本通过评估与观测持续校准。

