---
title: "从知识库问答到 Agentic RAG：一份场景驱动的项目启动方法论"
date: 2026-04-17 20:00:00 +0800
description: 在动手搭 RAG 系统之前，真正决定项目成败的不是技术选型，而是场景定义、评估先行和分层迭代。这篇文章把我在 Markdown 知识库问答项目上的 Kickoff 思考过程拆开写给你看。
tags: [AI, RAG, Agent, 知识库]
categories: [Tech]
---

*Written by Biyu Huang.*

---

## 写在前面：为什么要写一份 Kickoff 方法论

RAG 已经不是新概念了。从 2023 年 Naive RAG 流行开始，到 2024 年 Hybrid Search、Contextual Retrieval、Reranker 成为标配，再到 2025 年 Agentic RAG 被所有人挂在嘴边——技术栈的演进速度超过了大多数团队的落地速度。

我见过很多项目在启动时就走错了方向：

- 还没定义清楚用户问题类型，就先去选向量数据库。
- 还没建评估集，就上 Agentic 架构。
- 把 bad case 简单归咎于「模型不够强」，而不是拆开看瓶颈在哪一层。

这篇文章是我在一个 Markdown 知识库问答项目上的 Kickoff 思考过程，核心是三句话：

> **先定义问题，再选方案。分层解决，逐层验证。评估先行。**

---

## 00 核心前提：场景驱动架构，而不是技术驱动架构

所有的架构决策都必须由具体的业务场景和 bad case 数据驱动，而不是跟着技术潮流走。这听起来是废话，但真实的项目里，你会看到大量「因为 LangGraph 很火所以我们要用」、「因为 Agentic RAG 是未来所以我们一上来就做」的决策。

我给自己定了一条 **Decision Ladder**，遇到问题时按顺序往下走：

1. **检索质量差** → 先优化 chunking / embedding / hybrid search / rerank。
2. **单次检索覆盖不全** → 上子问题展开 + 多路检索（Active Recall）。
3. **检索路径无法预先定义** → 才考虑 Agentic RAG（动态决策）。
4. **纯粹生成质量差** → 换更强的 LLM 或优化 Prompt。

每一层都有明确的验证手段，不跨层设计。跨层设计的代价是：一旦系统出问题，你根本不知道是哪一层的锅。

---

## 01 场景确认：在动手之前，把这三个问题回答清楚

Kickoff 会上，我强制自己回答三个问题。如果任何一个答不上来，就不进入技术选型阶段。

### Q1. 知识库是什么？

- **文档格式**：Markdown / PDF / 混合？
- **体量**：多少篇、多久更新一次？
- **领域**：技术文档 / 业务知识 / FAQ？

这三个答案直接决定了解析器、chunking 策略、是否需要增量入库。

### Q2. 用户问题是什么类型？

根据我过去几个项目的数据，一个典型的企业知识库问答，问题分布大致是：

- **单跳事实**（~40%）：某个概念是什么、某个配置值是多少。
- **流程类**（~30%）：怎么做、步骤是什么。
- **多跳推理**（~20%）：A 和 B 的关系、基于 X 推导 Y。
- **比较类**（~10%）：X 和 Y 的区别。

这个分布很重要——**如果你只用单跳问题做评估，会系统性高估你的系统质量 25~30%**。真实分布下多跳和比较类会把 naive RAG 打回原形。

### Q3. 成功标准是什么？

- **检索 Hit Rate**：比如 ≥ 85% @ top5。
- **答案相关性**：比如 RAGAS ≥ 0.8。
- **延迟**：P95 ≤ 3s。
- **成本**：每次 query 的 LLM 调用预算。

没有数字就没有成功标准，没有成功标准就不知道什么时候该停。

---

## 02 技术选型：基于 Markdown 知识库的推荐配置

场景确认完了，才进入技术选型。下面是我这个项目的选型清单，不是最优解，是**在"自建基础设施 + 中文 Markdown 知识库"这个具体场景下**的平衡解。

| 层 | 选型 | 原因 |
|---|---|---|
| 向量数据库 | **Qdrant** | Rust 实现，原生 Hybrid Search，本地部署友好 |
| Embedding 模型 | **BGE-M3** | 中文效果最佳，一次推理同时输出 dense + sparse |
| 子问题生成 LLM | **DeepSeek API** | 低成本，中文推理强，适合高频调用 |
| 最终生成 LLM | **按质量需求选择** | 简单场景 DeepSeek，高质量场景 Claude |
| BM25 索引 | **rank-bm25 + jieba** | 轻量，无额外服务依赖 |
| MD 解析 | **mistune (AST 模式)** | 比正则切割更可靠，支持完整语义结构 |
| 服务框架 | **FastAPI** | 原生异步，适合并行检索场景 |
| 缓存 | **Redis** | 子问题、embedding、检索结果三层缓存 |
| 评估框架 | **RAGAS** | RAG 专用，5 分钟接入，自动化评分 |

几个值得展开的点：

- **BGE-M3 一次推理同时出 dense 和 sparse**，省掉了单独跑 sparse encoder 的成本——这是 M3 相对于 BGE-large + SPLADE 组合的最大工程优势。
- **mistune 的 AST 模式**解决了 Markdown 切割的最大痛点：你可以拿到 heading 树、段落、代码块的结构化表示，而不是用一堆正则去猜。
- **LLM 分两档**：子问题生成这种高频、低难度的任务用 DeepSeek，最终生成看场景。不要一上来就全用最贵的模型。

---

## 03 入库 Pipeline：垃圾进，垃圾出

入库质量决定检索上限。我见过太多项目在检索层疯狂优化，但入库的 chunk 本身就是噪声——这种优化是无效的。

我的入库 pipeline 分五步：

### Step 1. AST 解析

用 mistune 把 Markdown 解析成 AST，提取 heading 树、段落、代码块。**比正则切割可靠一个数量级**。

### Step 2. Header-based 分块

- 按 heading 层级切分，每个 chunk 携带**面包屑路径**（比如 `产品手册 > 第三章 > 3.2 配置项`）。
- 超过 1024 token 的 chunk 按段落二次切。
- 低于 100 token 的 chunk 向下合并，避免碎片。
- 代码块单独存储并打 `type=code` 标签，在检索时可以选择性过滤。

### Step 3. 文档级摘要生成

每篇文档调用一次 LLM 生成 2~3 句摘要。**这是 Anthropic 在 Contextual Retrieval 论文里验证的、收益最大的单点优化**，一次性工作但长期受益。

### Step 4. Chunk 增强

Embedding 的时候不用原始 chunk，而是：

```
[面包屑路径] + [文档摘要] + [chunk 原文]
```

这个增强文本用于向量化。原始 chunk text 单独存储，供最终展示使用。这样既提升了 chunk 的语义完整性，又不污染返回给用户的内容。

### Step 5. 双路编码入库

- BGE-M3 一次推理同时输出 dense（1024 维）和 sparse 向量。
- 写入 Qdrant，payload 包含 `source`、`breadcrumb`、`chunk_type`、`heading_level`。
- 同步构建 BM25 索引并持久化。

---

## 04 Active Recall 检索：主动重建 context，而不是被动堆砌 chunks

这是这个项目里我最想强调的设计理念。

Naive RAG 的逻辑是：**query → 检索 top-k → 把 chunks 塞给 LLM**。

这种模式的问题在于：

1. 单次检索对多跳和比较类问题覆盖不足。
2. top-k 里有大量噪声 chunk，反而干扰生成。
3. LLM 被迫自己在长 context 里做二次筛选。

**Active Recall** 的思路是：模仿人类复习的过程——先把问题拆成小问题，分别回忆答案，再组合起来作答。

整个流程是这样的：

### 1. 意图分类（Fast Path）

规则优先。包含"区别 / 流程 / 比较"等关键词，或 query 长度 > 30 字的，判断需要展开。简单 query 直接走单次 Hybrid 检索 + 生成，不走完整流程。

**这是成本控制的关键**——大部分真实 query 是简单的，不要为了 5% 的复杂 query 给所有请求加 2 秒延迟。

### 2. 子问题生成（Active Recall）

1 次轻量 LLM 调用，生成 3~5 个独立可检索的子问题。Prompt 里要求：

- 陈述句风格，便于和 chunk 做相似度匹配。
- 覆盖不同侧面，不要同义重复。
- 无语义重叠。

### 3. 并行 Hybrid 检索

所有子问题**并行**执行（FastAPI 的 asyncio 在这里派上用场），每一路：

```
dense top-5 + BM25 top-5 → RRF 融合 → 跨路去重 → 每路保留 top-3
```

### 4. 片段压缩提炼

每一路的检索结果 + 对应子问题 → 轻量 LLM → 提炼成 1~2 句核心答案，注明来源 chunk_id。**支持 batch 调用**，把多路 query 合并成一次请求，降低成本。

这一步是 Active Recall 区别于 Naive RAG 的核心——我们不是把 chunks 塞给最终 LLM，而是先把每路的核心答案抽出来。

### 5. Context 组装 + 生成

把所有提炼结果拼装成结构化 context（带来源面包屑），送入最终 LLM 生成答案。

最终 context 的长度通常只有原始 chunks 总和的 1/3，但信息密度更高，幻觉率更低。

---

## 05 Baseline 建立：没有 baseline，就无法判断任何优化是否有效

这是 Kickoff 阶段最容易被跳过的一步，也是我最坚持的一步。

### Step 1. 定义评估指标（分三层）

- **检索层**：Hit Rate、MRR、Recall@3/5。
- **忠实度**：Faithfulness——答案的每个陈述是否在 context 中有支撑。
- **答案质量**：Answer Relevancy、Answer Correctness。

分层的目的是定位瓶颈。如果 Hit Rate 高但 Faithfulness 低，说明问题在生成层；反过来说明问题在检索层。

### Step 2. 构建评估集

- LLM 自动生成 QA 对，人工抽样验证 10~20%。
- **问题类型覆盖**：单跳 40% / 多跳 30% / 流程 20% / 比较 10%。
- **规模**：100 篇以内 → 100~200 条；100~500 篇 → 300~500 条。
- **警告**：仅用简单问题会高估系统 25~30%，真实分布下表现会明显下降。

### Step 3. 跑多个对照 Baseline（控制变量）

- Baseline 0：随机检索（sanity check，用来验证评估集本身的信号强度）
- Baseline 1：BM25-only
- Baseline 2：Dense-only（Naive RAG）
- Baseline 3：Hybrid Search
- Baseline 4：Hybrid + Contextual Retrieval 前缀
- Baseline 5：Active Recall 方案

每一层都是前一层的增量，这样你能清楚看到**每个技术决策带来的具体收益**，而不是一个模糊的"我们的系统效果不错"。

### Step 4. RAGAS 自动化评估

- 同一个评估模型评所有变体，保证对比公平。
- 输出对比表，定位瓶颈在检索层还是生成层。
- **每次优化只改一个变量**，防止混淆收益来源。

---

## 06 迭代路线图：场景驱动，数据驱动，逐层升级

我不相信一次性上线完整方案。真实的路线图应该分阶段，每个阶段都有明确的 Go/No-Go 决策点。

### Phase 1（1~2 周）：基础可用

目标：跑通 Naive RAG，建立评估集和 Baseline 数据。

- Markdown 分块 + 面包屑 metadata。
- BGE-M3 embedding 入库。
- Qdrant Hybrid Search。
- RAGAS 评估接入。
- 构建 300+ 条评估集。

### Phase 2（1~2 周）：Active Recall 核心

目标：上线子问题展开 + 并行检索 + 压缩提炼。

- 意图分类 + Fast Path。
- 子问题生成（Prompt 调优）。
- 并行 Hybrid 检索。
- 片段压缩提炼（batch 化）。
- 与 Phase 1 做 A/B 对比。

**决策点**：对比 Hit Rate 和 Faithfulness 提升幅度，验证 Active Recall 收益。如果提升不显著，回到 Phase 1 继续优化检索层。

### Phase 3（1 周）：工程优化

目标：降延迟、降成本、提稳定性。

- Redis 三层缓存（子问题、embedding、检索结果）。
- 延迟监控 P50/P95/P99。
- 增量入库支持。
- Bad case 收集机制（这个是 Phase 4 的输入）。

### Phase 4（按需）：质量提升

目标：基于 bad case 数据针对性优化。

- BGE-Reranker 重排序。
- 多轮对话 context 管理。
- 文档引用追踪。
- 自适应子问题数量。

**决策点**：分析 bad case 根因。检索层问题 → 优化检索；生成层问题 → 换模型或优化 Prompt。

---

## 07 Agentic RAG 决策：不是必须的升级，是场景驱动的选择

这是我最想劝退的一节。

**Agentic RAG 的正确触发条件**是：当 bad case 中出现**大量**「不看中间检索结果就无法确定下一步检索什么」的失败模式时。

### 这些情况不需要 Agentic RAG

- 检索 chunk 质量差 → 优化入库和 Reranker，在 Fixed Pipeline 内解决。
- 单次检索覆盖不全 → 调整子问题生成策略，在 Fixed Pipeline 内解决。
- 纯粹生成质量差 → 换更强的 LLM 或优化 Prompt。

### 当前落地成本

- 目前仅 ~2% 的组织实现规模化部署，61% 仍在探索阶段。
- 延迟和 token 成本显著增加，调试难度大。
- Gartner 预测：40% 的 Agentic AI 项目将在 2027 年前被叫停。

### 如果真的要上，推荐技术栈

- **LangGraph**（stateful 循环图，原生 Human-in-the-loop）。
- **ReAct 推理模式**（Thought → Action → Observation 循环）。
- **Claude Sonnet 4.6 / Opus 4.7 作为 Orchestrator**（2026 年企业标准）。

---

## 写在最后

如果这篇文章只能留下一句话，我希望是：

> **RAG 项目的成败，80% 在 Kickoff 阶段就决定了。**

不是在你选了哪个向量数据库，不是在你用了哪个最新的 Reranker，而是在你有没有：

- 清楚定义场景和问题类型分布。
- 先建评估集再动手。
- 分层迭代，每次只改一个变量。
- 用 Decision Ladder 决定什么时候该升级到下一层。

其他的都是工程问题，工程问题都有解。

---

*References:*

- *Wang et al. "Speculative RAG: Enhancing Retrieval Augmented Generation through Drafting." EMNLP 2024.*
- *Anthropic. "Contextual Retrieval." 2024.*
- *RAGFlow. "Production RAG Patterns." 2025.*
