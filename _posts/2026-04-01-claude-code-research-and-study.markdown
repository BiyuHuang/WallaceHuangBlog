---
title: "Claude Code 源码深度剖析：架构分析与学习指南"
date: 2026-04-01
tags: [源码分析, 架构设计, TypeScript, Claude Code]
---

# Claude Code 源码深度剖析：架构分析与学习指南

> 本文是对 Claude Codename "Tengu" 源码的深入分析，从架构设计到核心模块实现，带你系统学习这个复杂的 AI 编码助手项目。

## 目录

- [项目概述](#项目概述)
- [整体架构](#整体架构)
- [学习路径](#学习路径)
- [第1层：基础设施层](#第1层基础设施层)
  - [状态管理](#状态管理)
  - [配置系统](#配置系统)
  - [工具接口](#工具接口)
  - [API 客户端](#api-客户端)
- [第2层：核心业务逻辑层](#第2层核心业务逻辑层)
  - [工具系统](#工具系统)
  - [多Agent系统](#多-agent-系统)
  - [MCP集成](#mcp-集成)
  - [权限系统](#权限系统)
- [第3层：应用编排层](#第3层应用编排层)
  - [查询引擎](#查询引擎)
  - [工具执行器](#工具执行器)
  - [任务系统](#任务系统)
- [第4层：用户界面层](#第4层用户界面层)
  - [REPL接口](#repl-接口)
  - [React组件系统](#react-组件系统)
  - [斜杠命令系统](#斜杠命令系统)
- [后续学习](#后续学习)

---

## 项目概述

Claude Code 是 Anthropic 开发的 AI 驱动编码助手，运行在终端中，基于以下技术栈：

| 技术 | 用途 |
|------|------|
| Node.js/Bun | 运行时 |
| React + Ink | 终端 UI 框架 |
| TypeScript + Zod | 类型安全与运行时验证 |
| Commander.js | CLI 解析 |
| Anthropic SDK | AI API 集成 |
| MCP (Model Context Protocol) | 工具/资源集成 |

---

## 整体架构

### 架构层级图

```
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                         │
│  (UI/CLI - 用户界面层)                                             │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  REPL Interface    React Components   Slash Commands        │  │
│   (交互式终端)         (UI组件)          (60+命令)            │  │
│  │  src/replLauncher.tsx  src/components/  src/commands.ts     │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                            │
│  (Orchestration - 应用编排层)                                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Query Engine      Tool Orchestration   Task System        │  │
│  │  (查询引擎)          (工具编排)           (任务系统)         │  │
│  │  src/QueryEngine.ts  src/services/tools/  src/Task.ts     │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       DOMAIN LAYER                              │
│  (Core Logic - 核心业务逻辑层)                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Tool System       Multi-Agent System    MCP Integration   │  │
│  │  (工具系统)          (多Agent系统)         (MCP集成)         │  │
│  │  src/Tool.ts       src/tools/AgentTool/  src/services/mcp/ │  │
│  │                                                     │  │
│  │  Skills            Permissions            Session History │  │
│  │  (技能)            (权限系统)              (会话历史)        │  │
│  │  src/skills/       src/utils/permissions/ src/assistant/  │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  INFRASTRUCTURE LAYER                          │
│  (基础设施层)                                                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  State Management  API Clients   Settings   Storage         │  │
│  │  (状态管理)          (API客户端)   (配置)      (存储)         │  │
│  │  src/state/        src/services/api/ src/utils/settings/   │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 核心数据流

```
用户输入
   ↓
Presentation Layer (命令解析)
   ↓
Application Layer (QueryEngine.query)
   ↓
   ├─→ 消息规范化
   ├─→ LLM API 调用 (Claude API)
   │      ↓
   │   流式响应 (SSE/WebSocket)
   │      ↓
   │   工具调用请求
   │      ↓
   └─→→ Tool Executor
           ↓
       Domain Layer (Tool.call)
           ├─→ 权限检查
           ├─→ 工具执行
           └─→ 结果返回
           ↓
       Infrastructure Layer (状态更新)
           ↓
       Presentation Layer (UI 渲染)
```

### 架构设计原则

| 原则 | 说明 |
|------|------|
| 分层架构 | 依赖方向从上层指向下层，高层模块不依赖低层模块实现 |
| 工具抽象 | 所有功能通过统一的 `Tool` 接口实现，可扩展性强 |
| 流式处理 | 从 LLM 响应到工具执行都采用流式处理，提供实时反馈 |
| 状态集中 | 使用统一的 AppState 管理所有应用状态 |
| 类型安全 | 使用 TypeScript + Zod 进行编译时和运行时类型检查 |

---

## 学习路径

建议按照以下顺序学习 Claude Code 源码：

1. **第1层：基础设施层** (本文重点)
   - 状态管理：理解状态如何存储和更新
   - 配置系统：学习多源配置合并机制
   - 工具接口：掌握核心抽象
   - API 客户端：了解与外部服务的交互

2. **第2层：核心业务逻辑层**
   - 工具系统：内置工具实现（Bash, FileEdit, WebSearch 等）
   - 多 Agent 系统：Agent 协作机制
   - MCP 集成：动态工具加载
   - 权限系统：安全检查流程

3. **第3层：应用编排层**
   - 查询引擎：LLM 交互流程
   - 工具执行器：工具调用协调
   - 任务系统：后台任务管理

4. **第4层：界面层**
   - REPL 实现：交互式终端
   - 组件库：UI 组件设计
   - 命令系统：斜杠命令处理

---

## 第1层：基础设施层

基础设施层是理解整个系统的基础，包含状态管理、配置、API 客户端等核心设施。

### 状态管理

#### Store 实现

状态管理使用极简的 Store 模式，总共只有 35 行代码：

```typescript
// src/state/store.ts

type Listener = () => void
type OnChange<T> = (args: { newState: T; oldState: T }) => void

export type Store<T> = {
  getState: () => T
  setState: (updater: (prev: T) => T) => void
  subscribe: (listener: Listener) => () => void
}

export function createStore<T>(
  initialState: T,
  onChange?: OnChange<T>,
): Store<T> {
  let state = initialState
  const listeners = new Set<Listener>()

  return {
    getState: () => state,

    setState: (updater: (prev: T) => T) => {
      const prev = state
      const next = updater(prev)
      if (Object.is(next, prev)) return  // 对象引用相同则跳过
      state = next
      onChange?.({ newState: next, oldState: prev })
      for (const listener of listeners) listener()  // 通知所有订阅者
    },

    subscribe: (listener: Listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)  // 返回取消订阅函数
    },
  }
}
```

#### 设计特点

1. **超轻量实现** - 没有使用 Redux、MobX 等复杂状态管理库
2. **函数式更新** - 使用 `(prev: T) => T` 确保状态不可变性
3. **引用相等检查** - 使用 `Object.is()` 检测引用是否变化
4. **发布-订阅模式** - 简单的事件通知机制

#### AppState 类型

```typescript
// src/state/AppStateStore.ts

export type AppState = DeepImmutable<{
  // 不可变状态
  settings: SettingsJson
  verbose: boolean
  mainLoopModel: ModelSetting
  mainLoopModelForSession: ModelSetting
  toolPermissionContext: ToolPermissionContext
  kairosEnabled: boolean
  remoteSessionUrl: string | undefined
  remoteConnectionStatus: 'connecting' | 'connected' | 'reconnecting' | 'disconnected'
  replBridgeEnabled: boolean
  replBridgeConnected: boolean
  replBridgeSessionActive: boolean
  // ... 100+ 个不可变状态字段
}> & {
  // 可变状态（不使用 DeepImmutable）
  tasks: { [taskId: string]: TaskState }
  agentNameRegistry: Map<string, AgentId>
  mcp: {
    clients: MCPServerConnection[]
    tools: Tool[]
    commands: Command[]
    resources: Record<string, ServerResource[]>
    pluginReconnectKey: number
  }
  plugins: {
    enabled: LoadedPlugin[]
    disabled: LoadedPlugin[]
    commands: Command[]
    errors: PluginError[]
    installationStatus: { ... }
    needsRefresh: boolean
  }
  agentDefinitions: AgentDefinitionsResult
  fileHistory: FileHistoryState
  attribution: AttributionState
  todos: { [agentId: string]: TodoList }
  notifications: { current: Notification | null; queue: Notification[] }
  // ... 其他可变状态
}
```

#### 默认状态初始化

```typescript
export function getDefaultAppState(): AppState {
  const initialMode: PermissionMode =
    teammateUtils.isTeammate() && teammateUtils.isPlanModeRequired()
      ? 'plan'
      : 'default'

  return {
    settings: getInitialInitialSettings(),
    tasks: {},
    agentNameRegistry: new Map(),
    verbose: false,
    mainLoopModel: null,
    toolPermissionContext: {
      ...getEmptyToolPermissionContext(),
      mode: initialMode,
    },
    mcp: {
      clients: [],
      tools: [],
      commands: [],
      resources: {},
      pluginReconnectKey: 0,
    },
    // ... 其他默认值
  }
}
```

---

### 配置系统

配置系统支持多源配置合并，具有灵活的优先级管理。

#### 配置源优先级

配置按照从低到高的优先级合并：

```
低优先级 → 高优先级
────────────────────────────
1. pluginSettings     (插件提供的配置)
        ↓
2. userSettings       (~/.claude/settings.json 或 ~/.claude/cowork_settings.json)
        ↓
3. projectSettings    (项目 .claude/settings.json)
        ↓
4. localSettings      (项目 .claude/settings.local.json) - 不加入 git
        ↓
5. flagSettings       (CLI 参数)
        ↓
6. policySettings     (策略配置，"首个有内容的源获胜")
    ├─ remote         (远程托管配置)
    ├─ plist/hklm     (MDM - macOS plist 或 Windows 注册表)
    ├─ file          (managed-settings.json + managed-settings.d/*.json)
    └─ hkcu          (用户注册表/用户级配置)
```

**policySettings 特殊规则**：采用"首个有内容的源获胜"策略，优先级为：
1. Remote（最高）
2. MDM (HKLM / macOS plist)
3. managed-settings.json + managed-settings.d/
4. HKCU（最低 - 用户可写）

#### 配置源类型

```typescript
export type SettingSource =
  | 'pluginSettings'
  | 'userSettings'
  | 'projectSettings'
  | 'localSettings'
  | 'flagSettings'
  | 'policySettings'

export type EditableSettingSource =
  | 'userSettings'
  | 'projectSettings'
  | 'localSettings'
```

#### 核心函数

```typescript
// src/utils/settings/settings.ts

// 获取合并后的所有配置
export function getInitialSettings(): SettingsJson {
  const { settings } = getSettingsWithErrors()
  return settings || {}
}

// 获取特定源的配置
export function getSettingsForSource(
  source: SettingSource,
): SettingsJson | null

// 更新特定源的配置
export function updateSettingsForSource(
  source: EditableSettingSource,
  settings: SettingsJson,
): { error: Error | null }

// 获取带源详情的配置
export function getSettingsWithSources(): SettingsWithSources
```

#### 配置合并策略

```typescript
// 自定义合并函数 - 数组去重合并
export function settingsMergeCustomizer(
  objValue: unknown,
  srcValue: unknown,
): unknown {
  if (Array.isArray(objValue) && Array.isArray(srcValue)) {
    // 数组合并并去重
    return uniq([...objValue, ...srcValue])
  }
  // 其他情况使用 lodash 默认合并行为
  return undefined
}
```

**删除配置的方法**：将字段设置为 `undefined`，例如：
```typescript
updateSettingsForSource('userSettings', {
  permissions: undefined,  // 删除 permissions 配置
})
```

#### 配置类型定义

`SettingsSchema` 使用 Zod 定义，包含 100+ 个配置字段：

```typescript
// src/utils/settings/types.ts

export const SettingsSchema = lazySchema(() =>
  z.object({
    // JSON Schema 引用（用于 IDE 提示）
    $schema: z.literal(CLAUDE_CODE_SETTINGS_SCHEMA_URL).optional(),

    // 认证相关
    apiKeyHelper: z.string().optional(),
    awsCredentialExport: z.string().optional(),
    awsAuthRefresh: z.string().optional(),
    gcpAuthRefresh: z.string().optional(),

    // 权限配置
    permissions: PermissionsSchema().optional(),

    // 模型配置
    model: z.string().optional(),
    availableModels: z.array(z.string()).optional(),
    modelOverrides: z.record(z.string(), z.string()).optional(),

    // MCP 配置
    enableAllProjectMcpServers: z.boolean().optional(),
    enabledMcpjsonServers: z.array(z.string()).optional(),
    disabledMcpjsonServers: z.array(z.string()).optional(),
    allowedMcpServers: z.array(AllowedMcpServerEntrySchema()).optional(),
    deniedMcpServers: z.array(DeniedMcpServerEntrySchema()).optional(),

    // Hooks 配置
    hooks: HooksSchema().optional(),
    disableAllHooks: z.boolean().optional(),
    allowManagedHooksOnly: z.boolean().optional(),

    // 插件配置
    enabledPlugins: z.record(
      z.string(),
      z.union([z.array(z.string()), z.boolean(), z.undefined()])
    ).optional(),
    extraKnownMarketplaces: z.record(
      z.string(),
      ExtraKnownMarketplaceSchema()
    ).optional(),
    strictKnownMarketplaces: z.array(MarketplaceSourceSchema()).optional(),
    blockedMarketplaces: z.array(MarketplaceSourceSchema()).optional(),

    // Worktree 配置
    worktree: z.object({
      symlinkDirectories: z.array(z.string()).optional(),
      sparsePaths: z.array(z.string()).optional(),
    }).optional(),

    // UI 配置
    statusLine: z.object({
      type: z.literal('command'),
      command: z.string(),
      padding: z.number().optional(),
    }).optional(),
    spinnerTipsEnabled: z.boolean().optional(),
    spinnerVerbs: z.object({
      mode: z.enum(['append', 'replace']),
      verbs: z.array(z.string()),
    }).optional(),
    outputStyle: z.string().optional(),
    language: z.string().optional(),

    // 功能开关
    thinkingEnabled: z.boolean().optional(),
    fastMode: z.boolean().optional(),
    autoMemoryEnabled: z.boolean().optional(),
    autoMemoryDirectory: z.string().optional(),
    promptSuggestionEnabled: z.boolean().optional(),

    // 环境变量
    env: z.record(z.string(), z.coerce.string()).optional(),

    // 远程会话配置
    remote: z.object({
      defaultEnvironmentId: z.string().optional(),
    }).optional(),

    // ... 更多配置字段
  }).passthrough()
)
```

#### 权限配置 Schema

```typescript
export const PermissionsSchema = lazySchema(() =>
  z.object({
    allow: z.array(PermissionRuleSchema()).optional(),
    deny: z.array(PermissionRuleSchema()).optional(),
    ask: z.array(PermissionRuleSchema()).optional(),
    defaultMode: z.enum(PERMISSION_MODES).optional(),
    disableBypassPermissionsMode: z.enum(['disable']).optional(),
    additionalDirectories: z.array(z.string()).optional(),
  }).passthrough()
)
```

#### 配置缓存机制

```typescript
// src/utils/settings/settingsCache.ts

// 缓存已解析的文件
const fileCache = new Map<string, { settings: SettingsJson | null; errors: ValidationError[] }>()

// 缓存每个源的配置
const sourceCache = new Map<SettingSource, SettingsJson | null>()

// 会话级缓存（整个会话期间有效）
let sessionCache: SettingsWithErrors | null = null
```

缓存失效时机：
- 配置文件被修改时
- `/reload-plugins` 命令执行
- 内部写入操作完成

---

### 工具接口

`Tool` 是整个系统最重要的抽象接口，所有功能通过工具实现。

#### 工具类型定义

```typescript
// src/Tool.ts

export type Tool<Input, Output, Progress> = {
  // ─── 基本信息 ───
  name: string                                      // 工具名称
  inputSchema: ZodType<Input>                        // 输入参数 Schema

  // ─── 核心方法 ───
  call(
    input: Input,
    context: ToolUseContext,
    onProgress?: (progress: Progress) => void,
  ): Promise<ToolResult<Output>>

  // ─── 权限检查 ───
  checkPermissions(
    input: Input,
    context: ToolUseContext,
  ): Promise<PermissionResult>

  // ─── 状态查询 ───
  isEnabled(): boolean
  isReadOnly(input: Input): boolean
  isConcurrencySafe(input: Input): boolean

  // ─── 描述生成 ───
  description(
    input: Input,
    options: DescriptionOptions,
  ): Promise<string>

  // ─── UI 渲染方法 ───
  renderToolUseMessage(
    input: Partial<Input>,
    options: RenderOptions,
  ): ReactNode

  renderToolResultMessage(
    content: Output,
    options: RenderOptions,
  ): ReactNode
}
```

#### 工具执行上下文

```typescript
export type ToolUseContext = {
  // 状态访问
  getState: () => AppState
  setState: (updater: (prev: AppState) => AppState) => void

  // 消息管理
  messagesRef: { current: Message[] }
  progressMessageRef: { current: ProgressMessage | null }

  // MCP 客户端
  mcpClients: MCPServerConnection[]

  // 工具注册表
  tools: Tool[]

  // 其他上下文
  abortController: AbortController
  querySource: QuerySource
  agentId: AgentId
  canUseTool: CanUseToolFn
  fileStateCache: FileStateCache
  // ... 更多字段
}
```

#### 权限结果类型

```typescript
export type PermissionResult =
  | { allowed: true }
  | {
      allowed: false
      reason: string
      suggestedUserMessage?: string
      bypassPermissionsModeAvailable: boolean
    }
```

#### 工具结果类型

```typescript
export type ToolResult<Content> = {
  content: Content
  error?: Error
  metadata?: ToolResultMetadata
}

export type ToolResultMetadata = {
  success: boolean
  toolName: string
  outputTokenCount?: number
  timeSavedMs?: number
  // ... 更多元数据
}
```

#### 内置工具示例

Claude Code 内置了 30+ 个工具：

| 工具名称 | 用途 | 文件位置 |
|---------|------|---------|
| BashTool | 执行 Shell 命令 | `src/tools/BashTool/` |
| FileReadTool | 读取文件 | `src/tools/FileReadTool/` |
| FileWriteTool | 写入文件 | `src/tools/FileWriteTool/` |
| FileEditTool | 编辑文件 | `src/tools/FileEditTool/` |
| GlobTool | 文件模式匹配 | `src/tools/GlobTool/` |
| GrepTool | 内容搜索 | `src/tools/GrepTool/` |
| WebSearchTool | 网络搜索 | `src/tools/WebSearchTool/` |
| WebFetchTool | 获取网页 | `src/tools/WebFetchTool/` |
| AgentTool | 启动子 Agent | `src/tools/AgentTool/` |
| SkillTool | 执行技能 | `src/tools/SkillTool/` |
| TaskTool | 任务管理 | `src/tools/TaskTool/` |
| NotebookEditTool | 编辑 Jupyter Notebook | `src/tools/NotebookEditTool/` |
| CronTool | 定时任务 | `src/tools/CronTool/` |
| AskUserQuestionTool | 询问用户 | `src/tools/AskUserQuestionTool/` |
| LSPTool | LSP 集成 | `src/tools/LSPTool/` |
| ExitWorktreeTool | 退出 worktree | `src/tools/ExitWorktreeTool/` |

#### MCP 工具

MCP (Model Context Protocol) 提供动态工具：

```typescript
// MCP 提供的动态工具
- ListMcpResourcesTool       // 列出 MCP 资源
- ReadMcpResourceTool        // 读取 MCP 资源
- ListMcpPromptsTool        // 列出 MCP 提示
- GetMcpPromptTool          // 获取 MCP 提示
```

---

### API 客户端

API 客户端模块负责与外部服务的交互。

#### API 客户端架构

```
src/services/api/
├── client.ts           # 通用 API 客户端基类
├── claude.ts           # Claude API 客户端
├── bootstrap.ts        # Bootstrap API
├── filesApi.ts         # 文件存储 API
├── adminRequests.ts    # 管理请求
├── withRetry.ts        # 重试逻辑
├── errorUtils.ts       # 错误处理
├── errors.ts          # 错误类型定义
├── usage.ts           # 使用统计
├── logging.ts         # 日志上报
├── referral.ts        # 推荐链接
└── sessionIngress.ts  # 会话接入
```

#### 通用客户端模式

```typescript
// src/services/api/client.ts

export function createAnthropicClient(options: {
  apiKey: string
  baseURL?: string
  maxRetries?: number
  timeout?: number
}): Anthropic {
  const client = new Anthropic({
    apiKey: options.apiKey,
    baseURL: options.baseURL || DEFAULT_BASE_URL,
    maxRetries: options.maxRetries ?? DEFAULT_MAX_RETRIES,
    timeout: options.timeout ?? DEFAULT_TIMEOUT,
    httpAgent: new httpAgent.Agent({ ... }),
    httpsAgent: new https.Agent({ ... }),
  })

  return client
}
```

#### 重试逻辑

```typescript
// src/services/api/withRetry.ts

export async function withRetry<T>(
  operation: () => Promise<T>,
  options: {
    maxRetries?: number
    delay?: number
    onRetry?: (error: Error, attempt: number) => void
  } = {}
): Promise<T> {
  const maxRetries = options.maxRetries ?? 3
  const delay = options.delay ?? 1000

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await operation()
    } catch (error) {
      if (attempt === maxRetries) throw error
      if (isRetryableError(error)) {
        await sleep(delay * attempt)
        options.onRetry?.(error as as Error, attempt)
      } else {
        throw error
      }
    }
  }
}
```

#### 错误处理

```typescript
// src/services/api/errors.ts

export type ApiError =
  | { type: 'authentication'; message: string }
  | { type: 'rate_limit'; message: string; retryAfter?: number }
  | { type: 'overload'; message: string }
  | { type: 'invalid_request'; message: string }
  | { type: 'server_error'; message: string }
  | { type: 'network_error'; message: string }

export function classifyApiError(error: unknown): ApiError {
  // 根据 error 类型和内容进行分类
}
```

#### Claude API 客户端

```typescript
// src/services/api/claude.ts

export async function createMessages(
  client: Anthropic,
  params: MessagesParams
): Promise<MessageStream> {
  return client.messages.create(params)
}

export async function createMessagesStream(
  client: Anthropic,
  params: MessagesParams,
  onProgress: (delta: MessageStreamEvent) => void
): Promise<AsyncGenerator<MessageStreamEvent>> {
  const stream = await client.messages.create(params, { stream: true })
  for await (const event of stream) {
    onProgress(event)
  }
  return stream
}
```

---

## 第2层：核心业务逻辑层

Domain Layer 是系统的核心，包含工具系统、多 Agent 协作、MCP 集成和权限系统等关键模块。

### 模块交互架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Claude Code Domain Layer                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────┐    ┌─────────────────────┐                         │
│  │   Tool System       │    │  Multi-Agent System │                         │
│  │                     │    │                     │                         │
│  │ • Tool Interface    │◄──►│ • Agent Definition  │                         │
│  │ • buildTool()       │    │ • runAgent()        │                         │
│  │ • 60+ Built-ins     │    │ • forkSubagent()    │                         │
│  │ • Tool Orchestrationation│    │ • Swarm/Teammates   │                         │
│  └─────────────────────┘    └─────────────────────┘                         │
│            ▲                          ▲                                      │
│            │                          │                                      │
│            └────────────┬─────────────┘                                      │
│                         │                                                    │
│         ┌───────────────┴───────────────┐                                    │
│         │                               │                                    │
│  ┌──────▼───────┐              ┌──────▼───────┐                            │
│  │  MCP System  │              │  Permissions  │                            │
│  │              │              │    System     │                            │
│  │ • Multi-     │◄────────────►│ • Rule Engine │                            │
│  │   Transport  │              │ • Classifier  │                            │
│  │ • MCPTool    │              │ • Denial      │                            │
│  │   Wrapper    │              │   Tracking    │                            │
│  │ • Resources  │              │. Permission  │                            │
│  └──────────────┘              │   Hooks       │                            │
│                                  └──────────────┘                            │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 工具系统

工具系统是 Claude Code 的核心抽象，所有功能通过统一的工具接口实现。

#### 核心文件

| 文件路径 | 用途 |
|---------|------|
| `src/Tool.ts` | 工具接口和类型定义 |
| `src/tools/` | 60+ 内置工具实现 |
| `src/services/tools/toolOrchestration.ts` | 工具编排和并发控制 |
| `src/services/tools/toolExecution.ts` | 单个工具执行 |

#### 工具接口完整定义

```typescript
// src/Tool.ts

export type Tool<Input extends AnyObject, Output, P extends ToolProgressData> = {
  // ─── 基本信息 ───
  name: string
  aliases?: string[]
  inputSchema: Input                          // Zod schema for input validation
  inputJSONSchema?: ToolInputJSONSchema      // For MCP tools

  // ─── 核心执行方法 ───
  call(
    args: Input,
    context: ToolUseContext,
    canUseTool: CanUseToolFn,
    parentMessage: AssistantMessage,
    onProgress?: (progress: P) => void,
  ): Promise<ToolResult<Output>>

  // ─── 元数据和 行为 ───
  isEnabled(): boolean
  isConcurrencySafe(input: Input): boolean
  isReadOnly(input: Input): boolean
  isDestructive?(input: Input): boolean
  interruptBehavior?(): 'cancel' | 'block'

  // ─── 权限和验证 ───
  checkPermissions(
    input: Input,
    context: ToolUseContext,
  ): Promise<PermissionResult>

  validateInput?(
    input: Input,
    context: ToolUseContext,
  ): Promise<ValidationResult>

  // ─── 描述和UI渲染 ───
  prompt(options: DescriptionOptions): Promise<string>
  userFacingName(input: Input): string
  renderToolUseMessage(
    input: Partial<Input>,
    options: RenderOptions,
  ): React.ReactNode
  renderToolResultMessage(
    content: Output,
    progress: ToolProgress,
    options: RenderOptions,
  ): React.ReactNode
  // ... 更多渲染方法
}
```

#### 工具构建器模式

`buildTool()` 工厂函数为可选方法提供合理默认值：

```typescript
// 默认策略：fail-closed
const defaults = {
  isConcurrencySafe: false,  // 默认不并发安全
  isReadOnly: false,          // 默认可能有副作用
  isEnabled: () => true,       // 默认启用
  checkPermissions: async () => ({ allowed: true }),
  // ... 更多默认值
}
```

#### 智能批处理和并发控制

```typescript
// src/services/tools/toolOrchestration.ts

// 最大并发数（可通过环境变量配置）
function getMaxToolUseConcurrency(): number {
  return parseInt(
    process.env.CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY || '',
    10
  ) || 10
}

// 工具调用批处理算法
function partitionToolCalls(
  toolUseMessages: ToolUseBlock[],
  toolUseContext: ToolUseContext,
): Batch[] {
  return toolUseMessages.reduce((acc: Batch[], toolUse) => {
    const tool = findToolByName(toolUseContext.options.tools, toolUse.name)
    const isConcurrencySafe = checkConcurrencySafe(tool, toolUse)

    // 如果当前工具并发安全且上一个批也并发安全，合并到同一批
    if (isConcurrencySafe && acc[acc.length - 1]?.isConcurrencySafe) {
      acc[acc.length - 1]!.blocks.push(toolUse)
    } else {
      // 否则创建新批
      acc.push({ isConcurrencySafe, blocks: [toolUse] })
    }
    return acc
  }, [])
}
```

**批处理策略**：
1. **批类型 1**：单个非并发安全工具 → 串行执行
2. **批类型 2**：多个连续的并发安全工具 → 并行执行

**示例**：
```typescript
// 输入工具调用
[Read(file1), Read(file2), Edit(file1), Read(file3)]

// 批处理结果
[
  { isConcurrencySafe: true,  blocks: [Read(file1), Read(file2)] },  // 并行
  { isConcurrencySafe: false, blocks: [Edit(file1)] },             // 串行
  { isConcurrencySafe: true,  blocks: [Read(file3)] },              // 并行
]
```

#### 上下文修改器队列

```typescript
// 并发工具可以返回 contextModifier 函数
// 这些修改器在并行执行期间排队，在批完成后按顺序应用

type MessageUpdate = {
  message?: Message
  newContext: ToolUseContext
  contextModifier?: {
    toolUseID: string
    modifyContext: (context: ToolUseContext) => ToolUseContext
  }
}

// 执行流程：
// 1. 并行执行工具，收集 contextModifiers
// 2. 批完成后，按工具调用顺序应用所有上下文修改
// 3. 防止竞态条件同时允许并行执行
```

#### 工具结果预算系统

```typescript
// src/utils/toolResultStorage.ts

type ContentReplacementState = {
  maxResultSizeChars: number           // 最大结果大小
  currentSize: number                   // 当前已用大小
  replacements: Map<string, string>     // 文件路径 → 内容
}

// 超过限制的工具结果被持久化到磁盘
// Claude 收到预览而非完整内容
```

---

### 多Agent系统

多 Agent 系统支持创建和管理多个 AI Agent，实现复杂的协作任务。

#### 核心文件

| 文件路径 | 用途 |
|---------|------|
| `src/tools/AgentTool/runAgent.ts` | Agent 主执行循环 |
| `src/tools/AgentTool/forkSubagent.ts` | 创建并行子 Agent |
| `src/tools/AgentTool/loadAgentsDir.ts` | 加载 Agent 定义 |
| `src/tools/AgentTool/builtInAgents.ts` | 内置 Agent |
| `src/utils/swarm/` | 多 Agent 团队协调 |
| `src/utils/teammate.ts` | Teammate 协作工具 |

#### Agent 定义类型

```typescript
type AgentDefinition = {
  // 基本信息
  agentType: string
  source: 'builtin' | 'user' | 'plugin' | 'policySettings'

  // Agent 配置
  model?: ModelAlias
  permissionMode?: PermissionMode
  maxTurns?: number
  effort?: number
  omitClaudeMd?: boolean

  // 能力
  mcpServers?: Array<string | ScopedMcpServerConfig>
  skills?: string[]
  hooks?: HookConfig

  // 系统提示
  getSystemPrompt(options: SystemPromptOptions): string

  // 回调（内置 Agent 特有）
  callback?: () => void
}
```

#### Agent 隔离策略

```typescript
// 1. 同步 Agent：与父 Agent 共享状态
type SyncAgent = {
  setAppState: typeof parent.setAppState  // 共享状态更新
  abortController: typeof parent.abortController  // 共享中止控制器
}

// 2. 异步 Agent：完全隔离
type AsyncAgent = {
  abortController: new AbortController()  // 独立的中止控制器
  setAppState: noOpFunction               // 状态更新无操作
}
```

**隔离层次**：
- **权限作用域**：Agent 可定义自己的权限模式（除非父 Agent 在 bypass/acceptEdits 模式）
- **工具限制**：`allowedTools` 参数替换会话级 allow 规则
- **Git Worktree 隔离**：`worktreePath` 提供完整的文件系统隔离

#### 子 Agent 上下文分叉

```typescript
// src/tools/AgentTool/forkSubagent.ts

type ForkedAgentContext = {
  // 克隆文件状态缓存以实现只读一致性
  fileStateCache: cloneFileStateCache(parent.fileStateCache)

  // 通过相同的系统提示前缀共享提示缓存
  useExactTools: parent.useExactTools

  // 记录侧链转录本以实现可恢复性
  sidechainTranscript: recordSidechainTranscript()

  // 保留 toolUseResults 用于可查看的转录本
  preserveToolUseResults: true
}
```

#### Agent MCP 服务器初始化

```typescript
// Agent 可以在 frontmatter 中定义自己的 MCP 服务器

type AgentMcpServer = string | ScopedMcpServerConfig

// string: 查找现有配置（共享）
// object: 创建动态配置（Agent 特有）

// 初始化流程：
// 1. 检查 Agent 是否定义 mcpServers
// 2. 对于每个服务器：
//    - string: 查找现有配置（共享）
//    - object: 创建动态配置（Agent 特有）
// 3. 连接到服务器，获取工具
// 4. 与父工具合并，按名称去重
// 5. 完成后仅清理 Agent 特有的服务器
```

#### Swarm/Teammate 系统

```typescript
// src/utils/swarm/

// 后端抽象
type Backend =
  | ITermBackend    // iTerm2 集成
  | TmuxBackend    // tmux 面板管理
  | InProcessBackend // 进程内执行

// 布局管理
type TeammateLayoutManager = {
  createPane(config: PaneConfig): string  // 创建终端面板
  resizePane(paneId: string, size: number): void
  // ... 更多布局操作
}

// 权限同步
type LeaderPermissionBridge = {
  // 领导将权限决策同步给 worker teammates
  syncPermissions(decision: PermissionDecision): void
}
```

---

### MCP集成

MCP (Model Context Protocol) 允许 Claude Code 动态加载外部工具和资源。

#### 核心文件

| 文件路径 | 用途 |
|---------|------|
| `src/services/mcp/types.ts` | MCP 类型定义和配置 Schema |
| `src/services/mcp/client.ts` | MCP 客户端连接管理 |
| `src/services/mcp/config.ts` | MCP 服务器配置加载 |
| `src/services/mcp/normalization.ts` | 工具名称规范化 |
| `src/tools/MCPTool/MCPTool.ts` | MCP 工具包装器 |

#### 多传输支持

MCP 支持 7+ 种传输类型：

| 传输类型 | 配置 Schema | 用途 |
|---------|-------------|------|
| `stdio` | `{ command, args, env }` | 标准输入输出 |
| `sse` | `{ url, headers, oauth }` | 服务器发送事件 |
| `sse-ide` | `{ url, ideName, ideRunningInWindows }` | IDE 集成 |
| `http` | `{ url, headers, oauth }` | HTTP 轮询 |
| `ws` | `{ url, headers }` | WebSocket |
| `ws-ide` | `{ url, ideName, authToken }` | IDE WebSocket |
| `sdk` | `{ name }` | Claude Agent SDK |
| `claudeai-proxy` | `{ url, id }` | Claude.ai 代理 |

**示例配置**：
```json
{
  "mcpServers": {
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed"]
    },
    "brave-search": {
      "type": "sse",
      "url": "https://brave-search.mcp.dev/sse",
      "oauth": {
        "clientId": "your-client-id"
      }
    }
  }
}
```

#### 工具名称规范化

```typescript
// src/services/mcp/normalization.ts

// 命名模式：mcp__{serverName}__{toolName}
// 防止 MCP 服务器之间的命名冲突

function normalizeToolName(
  serverName: string,
  toolName: string,
): string {
  if (process.env.CLAUDE_AGENT_SDK_MCP_NO_PREFIX) {
    return toolName  // 支持 unprefixed 模式
  }
  return `mcp__${serverName}__${toolName}`
}

// 示例：
// serverName: "filesystem"
// toolName: "read_file"
// 结果: "mcp__filesystem__read_file"
```

#### 连接记忆化

```typescript
// src/services/mcp/client.ts

// 按服务器名称记忆化连接
const connectionCache = new Map<string, MCPServerConnection>()

function connectToServer(
  config: McpServerConfig,
): Promise<MCPServerConnection> {
  const cacheKey = getCacheKey(config)

  if (connectionCache.has(cacheKey)) {
    return connectionCache.get(cacheKey)!  // 复用现有连接
  }

  const connection = await createConnection(config)
  connectionCache.set(cacheKey, connection)
  return connection
}

// 共享连接在父/子 Agent 之间复用
// Agent 特有的内联服务器不被记忆化（Agent 退出时清理）
```

#### MCP 资源系统

```typescript
// MCP 资源独立于工具，提供内容访问

// 资源列表工具
ListMcpResourcesTool → {
  uri?: string  // 可选的 URI 模式
}

// 资源读取工具
ReadMcpResourceTool → {
  uri: string     // 资源 URI
}
```

---

### 权限系统

权限系统确保工具执行的安全性，支持多层权限检查和策略。

#### 核心文件

| 文件路径 | 用途 |
|---------|------|
| `src/utils/permissions/permissions.ts` | 核心权限逻辑 |
| `src/utils/permissions/PermissionResult.ts` | 权限决策类型 |
| `src/utils/permissions/PermissionRule.ts` | 权限规则解析和匹配 |
| `src/utils/permissions/denialTracking.ts` | 拒绝绝跟踪和回退逻辑 |
| `src/hooks/useCanUseTool.tsx` | React hook 用于交互式权限提示 |

#### 权限决策类型

```typescript
// src/utils/permissions/PermissionResult.ts

export type PermissionResult = {
  behavior: 'allow' | 'deny' | 'ask' | 'passthrough'
  updatedInput?: Record<string, unknown>
  decisionReason?: PermissionDecisionReason
  pendingClassifierCheck?: PendingClassifierCheck
}

export type PermissionDecisionReason =
  | { type: 'rule'; rule: PermissionRule }
  | { type: 'classifier'; classifier: string; reason: string }
  | { type: 'hook'; hookName: string; reason?: string }
  | { type: 'mode'; mode: PermissionMode }
  | { type: 'safetyCheck' }
  | { type: 'other' }
  | { type: 'sandboxOverride' }
  | { type: 'autoMode' }
  | { type: 'bypass' }
```

#### 多源规则评估

```typescript
// 权限规则源（优先级顺序）
const SETTING_SOURCES: SettingSource[] = [
  'cliArg',          // 1. 命令行 --allowedTools
  'command',         // 2. 会话 /permissions 命令
  'session',         // 3. 会话特定规则
  'user',            // 4. 用户全局设置
  'project',         // 5. 项目 .claude 目录
  'enterprise',      // 6. 企业策略
]

// 规则匹配优先级：deny > ask > allow
// 精确工具名匹配优先于子命令模式匹配
```

#### 权限模式状态机

```typescript
// src/utils/permissions/PermissionMode.ts

export type PermissionMode =
  | 'default'           // 安全和便利性的平衡
  | 'askFirst'          // 每次工具使用都询问
  | 'acceptEdits'       // 自动批准文件编辑，询问其他
  | 'auto''             // ML 分类器决定（需要 TRANSCRIPT_CLASSIFIER feature）
  | 'bypassPermissions' // 批准所有（仅管理员）
  | 'bubble'             // 委托给父 Agent（用于 teammates）
```

#### 拒绝绝跟踪和回退

```typescript
// src/utils/permissions/denialTracking.ts

export type DenialTrackingState = {
  consecutiveDenials: number
  denialsByTool: Map<string, number>
  lastDenialTime?: number
}

export const DENIAL_LIMITS = {
  consecutive: 3,           // 最多连续拒绝 3 次
  perTool: 5,                // 每个工具最多拒绝 5 次
  resetTimeMs: 60000,       // 60 秒后重置计数
}

// 超过阈值后回退到提示用户
// 防止自动模式中的无限拒绝循环
```

#### 分类器集成

```typescript
// src/utils/permissions/classifierDecision.ts

// 当 TRANSCRIPT_CLASSIFIER 启用时的流程：
// 1. hasPermissionsToUseTool() 调用分类器
// 2. 分类器返回 'allow'/'deny'/'ask' 和置信度
// 3. 如果高置信度，使用分类器决策
// 4. 如果低置信度，回退到手动提示
// 5. 决策按 toolUseID 缓存

export type ClassifierDecision = {
  decision: 'allow' | 'deny' | 'ask'
  confidence: number       // 0-1
  reason?: string
  classifierName: string
}
```

#### 权限 Hook 系统

```typescript
// src/utils/hooks.js

// Hook 类型
type HookType =
  | 'PreToolUse'      // 工具使用前（可修改输入或请求权限）
  | 'PostToolUse'     // 工具使用后（可修改输出或触发副作用）
  | 'SubagentStart'   // 子 Agent 启动时
  | 'SubagentStop'    // 子 Agent 退出时
  | 'TaskCreated'     // 任务创建时
  | 'TaskCompleted'   // 任务完成时

// Hook 定义位置：
// - Agent frontmatter
// - CLAUDE.md 文件
// - 插件代码
```

---

### 模块间集成

```
工具系统流程：
1. Model 生成 tool_use blocks
2. toolOrchestration.partitionToolCalls() 将它们分批
3. runToolsConcurrently() 或 runToolsSerially() 执行批
4. toolExecution.runToolUse() 处理单个工具生命周期：
   - validateInput()
   - checkPermissions()
   - preToolUse hooks
   - tool.call()
   - postToolUse hooks
5. 结果通过 ToolResultBlockParam 流回 Model
```

```
多 Agent 流程：
1. AgentTool.call() 接收到 Agent 请求
2. loadAgentsDir() 查找/加载 AgentDefinition
3. runAgent() 被调用调用：
   - initializeAgentMcpServers() 连接到 Agent 特有的 MCP 服务器
   - createSubagentContext() 创建隔离的上下文
   - registerFrontmatterHooks() 注册 Agent 作用域 hooks
   - query() 运行主 Agent 循环
   - Cleanup: MCP 服务器、hooks、shell tasks、todos
4. 结果作为 Message stream yield 回
5. Teammate 系统 (swarm/) 在终端面板中管理并行 Agents
```

```
MCP 集成流程：
1. mcp/config.ts 从 user/project/enterprise settings 加载服务器配置
2. mcp/client.ts 按需连接到服务器（记忆化）
3. fetchToolsForClient() 从连接的服务器检索工具
4. MCPTool 包装每个 MCP 工具作为本机 Tool 接口
5. 工具合并到主工具池（按名称唯一）
6. AgentTool 可以定义额外的 Agent 特有 MCP 服务器
7. 工具执行通过与本机工具相同的路径流转
```

```
权限系统流程：
1. useCanUseTool() hook 创建 CanUseToolFn
2. toolExecution.runToolUse() 调用 canUseTool(tool, input, ...)
3. canUseTool() 调用 hasPermissionsToUseTool()：
   a. 检查 tool 特有的 checkPermissions()
   b. 评估来自所有源的权限规则
   c. 运行权限 hooks
   d. 调用 ML 分类器（如果启用了）
   e. 检查拒绝跟踪阈值
4. 决策：
   - 'allow': 继续工具执行
   - 'deny': 向 Model 返回错误
   - 'ask': 通过 handleInteractivePermission() 显示交互式提示
5. Swarm: leaderPermissionBridge 将决策同步到 worker teammates
```

---

---

## 第3层：应用编排层

应用编排层负责协调 LLM 交互、工具执行和后台任务，是连接 Domain Layer 和 Presentation Layer 的桥梁。

`★ Insight ─────────────────────────────────────`
应用层采用了 Async Generator 架构模式，使得整个系统能够以流式方式处理 LLM 响应和工具执行结果。这种设计支持:
- **背压控制**: 通过 yield* 控制消息流动速度
- **懒加载**: 只在需要时计算和发送消息
- **组合性**: 各种中间件和处理器可以自然组合
─────────────────────────────────────────────────

### 查询引擎

查询引擎 (`QueryEngine`) 管理整个对话生命周期，从用户输入到最终响应的完整流程。

#### 核心文件

- `src/QueryEngine.ts` - 对话生命周期管理
- `src/query.ts` - 核心查询循环和 LLM 交互
- `src/services/api/claude.ts` - API 通信层

#### QueryEngine 类结构

```typescript
export class QueryEngine {
  private config: QueryEngineConfig
  private mutableMessages: Message[]
  private abortController: AbortController
  private permissionDenials: SDKPermissionDenial[]
  private totalUsage: NonNullableUsage

  constructor(config: QueryEngineConfig) {
    this.config = config
    this.mutableMessages = []
    this.abortController = new AbortController()
    this.permissionDenials = []
    this.totalUsage = { input_tokens: 0, output_tokens: 0 }
  }

  async *submitMessage(
    input: string,
    options?: SubmitMessageOptions
  ): AsyncGenerator<Message, QueryResult>
}
```

**主要职责:**
- 会话状态管理（消息、文件缓存、使用统计）
- 编排主查询循环
- 处理预算限制（最大轮数、USD 预算）
- 管理权限拒绝
- 持久化会话转录

#### 主查询流程

`submitMessage()` 方法实现了主流程:

```typescript
async *submitMessage(
  input: string,
  options?: SubmitMessageOptions
): AsyncGenerator<Message, QueryResult> {
  // 1. 用户输入处理 - 处理斜杠命令和用户上下文
  const processedInput = await this.processInput(input, options)

  // 2. 系统提示构建 - 构建包含工具、MCP 客户端等的系统提示
  const systemPrompt = await this.buildSystemPrompt()

  // 3. 主查询循环 - 调用 query() 函数并产生消息
  let result: QueryResult
  for await (const message of query({
    messages: this.mutableMessages,
    systemPrompt,
    userContext: this.config.userContext,
    systemContext: this.config.systemContext,
    canUseTool: this.canUseTool.bind(this),
    toolUseContext: this.processUserInputContext,
    abortController: this.abortController,
    // ...
  })) {
    yield message
    this.mutableMessages.push(message)
  }

  // 4. 结果累积 - 跟踪使用情况、停止原因和结构化输出
  return {
    usage: this.totalUsage,
    stopReason: result.stopReason,
    permissionDenials: this.permissionDenials,
    // ...
  }
}
```

#### 流式消息处理

系统通过 switch 语句处理各种消息类型：

| 消息类型 | 处理逻辑 |
|---------|---------|
| `assistant` | 捕获停止原因并产生规范化消息 |
| `progress` | 跟踪工具执行进度 |
| `user` | 增加轮数计数器 |
| `stream_event` | 跟踪 API 使用量（message_start, message_delta, message_stop） |
| `attachment` | 处理结构化输出和最大轮数信号 |
| `system` | 处理压缩边界和 API 错误 |

#### 核心查询循环 (src/query.ts)

```typescript
export async function* query({
  messages,
  systemPrompt,
  userContext,
  systemContext,
  canUseTool,
  toolUseContext,
  abortController,
  maxTurns,
  maxUsdBudget,
  // ...
}: QueryOptions): AsyncGenerator<Message, QueryResult> {
  const streamingToolExecutor = new StreamingToolExecutor({
    options: toolUseContext.options,
    canUseTool,
    toolUseContext,
  })

  let turnCount = 0
  let currentBudgetUsd = 0

  while (true) {
    // 检查预算限制
    if (turnCount >= maxTurns || currentBudgetUsd >= maxUsdBudget) {
      yield { type: 'system', content: 'Budget or turn limit reached' }
      break
    }

    // 调用 LLM API
    const response = await callClaudeAPI({
      messages,
      systemPrompt,
      abortController,
    })

    // 处理响应流
    for await (const message of response) {
      if (message.type === 'tool_use') {
        // 将工具调用添加到执行器
        streamingToolExecutor.addToolUse(message)
        continue
      }

      yield message
    }

    // 执行工具并获取结果
    for await (const result of streamingToolExecutor.execute()) {
      yield result
    }

    turnCount++
  }
}
```

---

### 工具执行器

工具执行器负责协调多个工具调用的执行，包括批处理、并发控制和结果管理。

`★ Insight ─────────────────────────────────────`
工具执行器采用了**智能批处理**算法:
- 同一批次中的工具可以并行执行（如果都声明为并发安全）
- 不同批次必须串行执行
- 上下文修改器（context modifiers）在批次间按顺序应用
这种设计在性能和正确性之间取得了良好平衡。
─────────────────────────────────────────────────

#### 核心文件

- `src/services/tools/toolOrchestration.ts` - 批处理工具执行
- `src/services/tools/StreamingToolExecutor.ts` - 流式工具执行
- `src/services/tools/toolExecution.ts` - 单个工具执行
- `src/Tool.ts` - 工具接口定义

#### 工具接口

```typescript
export type Tool<Input extends AnyObject = AnyObject, Output = unknown> = {
  name: string
  call(args: z.infer<Input>, context: ToolUseContext, ...): Promise<ToolResult<Output>>
  inputSchema: Input
  isConcurrencySafe(input: z.infer<Input>): boolean
  isReadOnly(input: z.infer<Input>): boolean
  isEnabled(context: ToolUseContext): boolean
  checkPermissions(input: z.infer<Input>, context: ToolUseContext): PermissionCheckResult
  renderToolUseMessage(input: unknown): React.ReactNode
  renderToolResultMessage(result: unknown): React.ReactNode
}
```

#### 工具编排（批处理模式）

`runTools()` 函数编排工具执行：

```typescript
export async function* runTools({
  toolUseMessages,
  // ...
}: RunToolsOptions): AsyncGenerator<Message> {
  // 1. 分区 - 使用 partitionToolCalls() 将工具调用分成批次
  const batches = partitionToolCalls(toolUseMessages, toolUseContext)

  for (const batch of batches) {
    if (batch.isConcurrencySafe) {
      // 2. 并发执行 - 并发安全的工具并行运行
      const results = await Promise.allSettled(
        batch.blocks.map(block => runToolUse(block, toolUseContext))
      )

      for (const result of results) {
        if (result.status === 'fulfilled') {
          yield* result.value
        }
      }
    } else {
      // 3. 串执行 - 非并发安全的工具逐个运行
      for (const block of batch.blocks) {
        const results = await runToolUse(block, toolUseContext)
        yield* results
      }
    }
  }
}
```

#### 工具分区算法

`partitionToolCalls()` 实现智能批处理：

```typescript
function partitionToolCalls(
  toolUseMessages: ToolUseBlock[],
  toolUseContext: ToolUseContext,
): Batch[] {
  return toolUseMessages.reduce((acc: Batch[], toolUse) => {
    const tool = findToolByName(toolUseContext.options.tools, toolUse.name)

    if (!tool) {
      // 未找到工具，创建新批次
      acc.push({ isConcurrencySafe: false, blocks: [toolUse] })
      return acc
    }

    // 检查工具是否并发安全
    const isConcurrencySafe = tool.isConcurrencySafe(toolUse.input)

    if (isConcurrencySafe && acc[acc.length - 1]?.isConcurrencySafe) {
      // 可以合并到最后一个批次
      acc[acc.length - 1]!.blocks.push(toolUse)
    } else {
      // 创建新批次
      acc.push({ isConcurrencySafe, blocks: [toolUse] })
    }

    return acc
  }, [])
}
```

**批处理示例:**

```
原始工具调用序列:
[Read, Bash, Glob, Glob, Write, Edit]

分区结果:
批次1 (concurrency-safe=true):  [Read]
批次2 (concurrency-safe=false): [Bash]
批次3 (concurrency-safe=true):  [Glob, Glob]
批次4 (concurrency-safe=false): [Write, Edit]

执行策略:
批次1: 并发执行 (单个 Read)
批次2: 串行执行 (Bash)
批次3: 并发执行 (两个 Glob)
批次4: 串行执行 (Write 和 Edit)
```

#### StreamingToolExecutor

`StreamingToolExecutor` 为流式场景提供更复杂的执行控制：

```typescript
export class StreamingToolExecutor {
  private tools: ToolExecution[] = []
  private resultsBuffer: ToolResultMessage[] = []

  addToolUse(toolUse: ToolUseBlock): void {
    const tool = findToolByName(toolUse.name)
    const execution = {
      toolUse,
      tool,
      status: 'pending' as ToolStatus,
      isConcurrencySafe: tool?.isConcurrencySafe(toolUse.input) ?? false,
      result: undefined as ToolResultMessage | undefined,
    }
    this.tools.push(execution)

    // 尝试立即执行
    this.tryExecute()
  }

  async *execute(): AsyncGenerator<Message> {
    while (this.tools.some(t => t.status !== 'completed')) {
      this.tryExecute()

      // 等待正在执行的工具
      await Promise.race(
        this.tools
          .filter(t => t.status === 'executing')
          .map(t => t.resultPromise!)
      )

      // 产生已完成的结果（按顺序）
      while (this.resultsBuffer.length > 0) {
        const result = this.resultsBuffer.shift()!
        yield result
      }
    }
  }

  private canExecuteTool(isConcurrencySafe: boolean): boolean {
    const executingTools = this.tools.filter(t => t.status === 'executing')

    // 没有正在执行的工具，可以执行
    if (executingTools.length === 0) return true

    // 新工具是并发安全的，且所有正在执行的工具也是并发安全的
    if (isConcurrencySafe && executingTools.every(t => t.isConcurrencySafe)) {
      return true
    }

    return false
  }
}
```

**关键特性:**
- 工具在流式传入时就开始执行
- 并发控制（安全工具并行运行）
- 结果缓冲并按顺序产生
- 进度消息立即产生
- Bash 工具错误的兄弟中止
- 流式回退的丢弃机制

#### 单个工具执行

`runToolUse()` 处理单个工具执行：

```typescript
async function* runToolUse(
  toolUse: ToolUseBlock,
  toolUseContext: ToolUseContext
): AsyncGenerator<Message> {
  const { name, id, input } = toolUse
  const tool = findToolByName(toolUseContext.options.tools, name)

  if (!tool) {
    yield { type: 'tool_result', id, content: `Tool not found: ${name}` }
    return
  }

  // 1. 验证输入
  const validatedInput = tool.inputSchema.parse(input)

  // 2. 检查权限
  const permissionCheck = await tool.checkPermissions(validatedInput, toolUseContext)
  if (permissionCheck.allowed === false) {
    yield { type: 'tool_result', id, content: permissionCheck.reason }
    return
  }

  // 3. 调用工具
  const result = await tool.call(validatedInput, toolUseContext)

  // 4. 产生结果
  yield {
    type: 'tool_result',
    id,
    content: result.output,
    isError: result.isError,
  }
}
```

---

### 任务系统

任务系统管理后台任务的执行、跟踪和清理。

#### 核心文件

- `src/Task.ts` - 任务类型和基础功能
- `src/utils/task/` - 任务管理工具

#### 任务类型

```typescript
export type TaskType =
  | 'local_bash'      // 本地 Bash 任务
  | 'local_agent'     // 本地 Agent 任务
  | 'remote_agent'    // 远程 Agent 任务
  | 'in_process_teammate'  // 进程内 Teammate
  | 'local_workflow'  // 本地工作流
  | 'monitor_mcp'     // MCP 监控任务
  | 'dream'           // Dream 任务
```

#### 任务状态

```typescript
export type TaskStatus =
  | 'pending'    // 等待执行
  | 'running'    // 正在执行
  | 'completed'  // 已完成
  | 'failed'     // 失败
  | 'killed'     // 被终止
```

#### 任务 ID 生成

```typescript
const TASK_ID_ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

export function generateTaskId(type: TaskType): string {
  const prefix = getTaskIdPrefix(type)  // 'b' for bash, 'a' for agent, etc.
  const bytes = randomBytes(8)
  let id = prefix
  for (let i = 0; i < 8; i++) {
    id += TASK_ID_ALPHABET[bytes[i]! % TASK_ID_ALPHABET.length]
  }
  return id
}

function getTaskIdPrefix(type: TaskType): string {
  const prefixes = {
    local_bash: 'b',
    local_agent: 'a',
    remote_agent: 'r',
    in_process_teammate: 't',
    local_workflow: 'w',
    monitor_mcp: 'm',
    dream: 'd',
  }
  return prefixes[type]
}
```

**任务 ID 示例:**
- Bash 任务: `bA3fG7kM9`
- Agent 任务: `aB2hK5nP8`
- Remote 任务: `rC4jL6oQ9`

#### 任务状态

```typescript
export type TaskStateBase = {
  id: string                    // 任务 ID
  type: TaskType               // 任务类型
  status: TaskStatus           // 任务状态
  description: string          // 任务描述
  toolUseId?: string           // 关联的工具调用 ID
  startTime: number           // 开始时间戳
  endTime?: number             // 结束时间戳
  outputFile: string           // 磁盘持久化输出文件
  outputOffset: number         // 输出偏移量（用于增量读取）
  notified: boolean            // 是否已通知用户
}
```

#### 任务接口

```typescript
export type Task = {
  name: string
  type: TaskType
  kill(taskId: string, setAppState: SetAppState): Promise<void>
}
```

#### Bash 任务示例

```typescript
export type BashTaskState = TaskStateBase & {
  type: 'local_bash'
  command: string              // 要执行的命令
  cwd?: string                 // 工作目录
  env?: Record<string, string>  // 环境变量
  timeout?: number             // 超时时间
  shellId?: string             // Shell ID
  output: string               // 输出内容
  exitCode?: number            // 退出码
  error?: string               // 错误信息
}

export class BashTask implements Task {
  name = 'bash'
  type = 'local_bash'

  async kill(
    taskId: string,
    setAppState: SetAppState
  ): Promise<void> {
    setAppState(prev => ({
      ...prev,
      tasks: prev.tasks.map(task => {
        if (task.id === taskId && task.status === 'running') {
          return { ...task, status: 'killed', endTime: Date.now() }
        }
        return task
      }),
    }))

    // 实际终止进程
    await this.killProcess(taskId)
  }
}
```

---

### 端到端执行流程

`★ Insight ─────────────────────────────────────`
整个应用层的执行流程形成了一个清晰的**消息驱动架构**:
1. 用户输入 → QueryEngine 处理
2. QueryEngine → query() 生成 LLM 调用
3. query() → LLM API 返回流式响应
4. 工具调用 → StreamingToolExecutor 执行
5. 工具结果 → query() 作为下一轮 LLM 调用的上下文
6. 循环直到完成 → 返回最终结果

这种设计使得所有组件都可以通过消息进行解耦和组合。
─────────────────────────────────────────────────

```
用户输入 "请读取 package.json 并分析依赖"
      ↓
QueryEngine.submitMessage(prompt)
      ↓
处理输入，构建系统提示
      ↓
query() 主循环开始
      ↓
┌─────────────────────────────────┐
│ 第1轮: 调用 LLM API              │
│ 请求: "请读取 package.json 并分析依赖" │
│                              │
│ 响应 (流式):                    │
│ - text: "让我先读取文件..."      │
│ - tool_use: Read("package.json") │
└─────────────────────────────────┘
      ↓
StreamingToolExecutor.addToolUse(Read)
      ↓
┌─────────────────────────────────┐
│ 执行 Read 工具                   │
│ 检查权限: 允许                   │
│ 读取文件内容                     │
│ 返回结果: package.json 内容       │
└─────────────────────────────────┘
      ↓
工具结果返回给 query()
      ↓
┌─────────────────────────────────┐
│ 第2轮: 调用 LLM API              │
│ 上下文: 包含 Read 工具结果        │
│                              │
│ 响应:                          │
│ - text: "这是一个 React 项目..."  │
│ - tool_use: Read("README.md")   │
└─────────────────────────────────┘
      ↓
StreamingToolExecutor.add... (Read)
      ↓
┌─────────────────────────────────┐
│ 执行 Read 工具                   │
│ 返回结果: README.md 内容         │
└─────────────────────────────────┘
      ↓
┌─────────────────────────────────┐
│ 第3轮: 调用 LLM API              │
│ 上下文: 包含所有之前的工具结果     │
│                              │
│ 响应:                          │
│ - text: "分析完成..."            │
│ - stop_reason: "end_turn"       │
└─────────────────────────────────┘
      ↓
查询完成，返回结果给用户
```

---

### 关键设计模式

#### 1. Async Generator 架构

```typescript
async function* processStream() {
  for await (const chunk of source) {
    const processed = transform(chunk)
    yield processed  // 惰性产生，支持背压
  }
}
```

**优势:**
- 支持流式处理，减少内存占用
- 自然的组合方式
- 内置背压控制

#### 2. 并发安全批处理

```typescript
// 工具声明并发安全性
isConcurrencySafe(input: T): boolean {
  return this.toolName === 'Read'  // Read 工具并发安全
}

// 系统自动批处理
const batches = partitionToolCalls(toolCalls)
for (const batch of batches) {
  if (batch.isConcurrencySafe) {
    await Promise.all(batch.map(runTool))
  } else {
    for (const tool of batch) await runTool(tool)
  }
}
```

#### 3. 上下文作为一等公民

```typescript
// ToolUseContext 贯穿所有层级
type ToolUseContext = {
  options: {
    tools: Tool[]
    // ...
  }
  // ...
}

// 不可变更新
const newContext = applyContextModifier(context, modifier)
```

#### 4. Abort Controller 层级

```
query.abortController
  └─ siblingAbortController (Bash 错误级联)
      └─ toolAbortController (每个工具)
```

**用途:**
- 用户取消操作
- 错误时级联中止相关任务
- 超时自动终止

#### 5. 消息驱动架构

```typescript
type Message =
  | { type: 'assistant', content: string }
  | { type: 'tool_use', tool: string, input: unknown }
  | { type: 'tool_result', id: string, content: unknown }
  | { type: 'progress', message: string }
  | { type: 'stream_event', event: StreamEvent }
  // ...
```

**优势:**
- 统一的消息格式
- 易于扩展新的消息类型
- 可持久化到转录存储

---

### 核心文件总结

| 文件 | 用途 |
|------|---------|
| `src/QueryEngine.ts` | 对话生命周期编排 |
| `src/query.ts` | 核心查询循环和 LLM 交互 |
| `src/services/tools/toolOrchestration.ts` | 批处理工具执行逻辑 |
| `src/services/tools/StreamingToolExecutor.ts` | 流式工具执行（含并发控制）|
| `src/services/tools/toolExecution.ts` | 单个工具执行 |
| `src/Tool.ts` | 工具接口和定义 |
| `src/Task.ts` | 任务类型和基础功能 |

这些组件构成了一个强大、可扩展的应用编排层，使 Claude Code 能够处理复杂的智能体工作流，具有适当的编排、并发控制和状态管理。

---

## 第4层：用户界面层

用户界面层负责与用户的所有交互，包括 REPL、React 组件系统和斜杠命令系统。

`★ Insight ─────────────────────────────────────`
Claude Code 采用了 **React + Ink** 框架，将现代 Web 开发模式带到了终端环境:
- 组件化架构便于维护和复用
- 声明式 UI 使状态管理更清晰
- Hook 模式复用逻辑而非代码
- 主题系统支持自定义外观
─────────────────────────────────────────────────

### REPL接口

REPL（Read-Eval-Print Loop）是 Claude Code 的核心交互界面，管理终端会话、输入处理和输出渲染。

#### 核心文件

- `src/replLauncher.tsx` - REPL 初始化和启动
- `src/screens/REPL.tsx` - 主 REPL 屏幕（800KB+）

#### REPL 启动流程

`replLauncher.tsx` 中的 `launchRepl` 函数：

```typescript
export async function launchRepl(
  root: Root,
  appProps: AppWrapperProps,
  replProps: REPLProps,
  renderAndRun: (root: Root, element: React.ReactNode) => Promise<void>
): Promise<void> {
  // 懒加载组件以优化启动性能
  const { App } = await import('./components/App.js');
  const { REPL } = await import('./screens/REPL.js');

  // 组合模式：App 包裹 REPL
  await renderAndRun(root, <App {...appProps}><REPL {...replProps} /></App>);
}
```

**架构特点:**
- 懒加载：App 和 REPL 组件按需加载
- 组合模式：`<App>` 作为外层包装器提供上下文
- 使用 Ink 的渲染引擎

#### REPL 主组件

`src/screens/REPL.tsx` 核心功能：

```typescript
export function REPL({
  replProps,
  setAppState,
  appState,
}: REPLProps) {
  // 自定义 Hooks
  const {
    messages,
    assistantHistory,
    taskListRef,
    commandQueue,
    // ...
  } = useAssistantHistory({ replProps, setAppState, appState })

  const mcpConnectStatuses = useMcpConnectivityStatus(appState.mcpConnections)

  const { tasksWithCollapseEffect } = useTasksV2WithCollapseEffect({
    tasks: appState.tasks,
    setAppState,
  })

  return (
    <FullscreenLayout>
      <Messages messages={messages} />
      <PromptInput {...props} />
      <StatusLine {...statusProps} />
      <TaskListV2 tasks={tasksWithCollapseEffect} />
    </FullscreenLayout>
  )
}
```

**核心职责:**
- 终端状态管理
- 通过 `PromptInput` 处理输入
- 通过 `Messages` 组件渲染消息
- 命令队列处理
- 会话生命周期管理

**关键集成:**
- `useAssistantHistory` - 对话历史管理
- `useCommandQueue` - 命令排队系统
- `useMcpConnectivityStatus` - MCP 服务器连接状态
- `useTasksV2WithCollapseEffect` - 任务管理

---

### React组件系统

Claude Code 基于 Ink（React for CLIs）构建了一套完整的 UI 组件系统。

`★ Insight ─────────────────────────────────────`
Ink 通过虚拟 DOM 抽象了终端 UI，使得开发者可以用 React 模式构建 CLI:
- 使用 `<Box>` 代替 HTML `<div>`
- 使用 `<Text>` 代替 HTML `<span>`
- 支持样式、布局和颜色
- 自动处理终端重绘和光标管理
─────────────────────────────────────────────────

#### 入口点

`src/components/App.tsx` 定义了顶层的上下文提供者层级：

```
FpsMetricsProvider
  └─ StatsProvider
      └─ AppStateProvider
          └─ [children]
```

```typescript
export function App({ children, setAppState }: AppProps) {
  return (
    <FpsMetricsProvider>
      <StatsProvider>
        <AppStateProvider value={{ setAppState }}>
          {children}
        </AppStateProvider>
      </StatsProvider>
    </FpsMetricsProvider>
  )
}
```

**状态管理:**
- `AppStateProvider` - 全局应用状态
- `StatsProvider` - 统计信息跟踪
- `FpsMetricsProvider` - 性能指标（FPS）

#### Ink 集成

`src/ink.ts` 提供了自定义的 Ink 封装：

```typescript
import { render } from 'ink'
import { ThemeProvider, useTheme } from './theme'

// 导出主题化组件
export const Box = (props: BoxProps) => {
  const theme = useTheme()
  // 应用主题并渲染
}

export const Text = (props: TextProps) => {
  const theme = useTheme()
  // 应用主题并渲染
}

// 导出 Hooks
export { useInput, useStdin, useTheme, useStdout }
```

**功能:**
- 用 `ThemeProvider` 包裹所有渲染
- 导出主题化组件：`Box`、`Text`
- 提供 Hooks：`useInput`、`useStdin`、`useTheme` 等
- 重新导出 Ink 原语用于 UI 构建

#### 核心 UI 组件

| 组件 | 路径 | 用途 |
|------|------|------|
| `PromptInput` | `src/components/PromptInput/PromptInput.tsx` | 用户输入、命令类型提示、历史 |
| `Messages` | `src/components/Messages.tsx` | 对话转录渲染 |
| `Message` | `src/components/Message.tsx` | 单条消息渲染器 |
| `StatusLine` | `src/components/StatusLine.tsx` | 底部状态栏 |
| `TaskListV2` | `src/components/TaskListV2.tsx` | 活动任务显示 |
| `FullscreenLayout` | `src/components/FullscreenLayout.tsx` | 布局管理 |

#### PromptInput 组件

`PromptInput` 处理用户输入的核心组件：

```typescript
export function PromptInput({
  onSubmit,
  onCancel,
  onTypeahead,
  history,
  // ...
}: PromptInputProps) {
  const [input, setInput] = useState('')
  const [cursorIndex, setCursorIndex] = useState(0)

  useInput((input: string, key: Key) => {
    // 处理特殊键
    if (key.return) {
      onSubmit(input)
      setInput('')
    } else if (key.ctrl === 'c') {
      onCancel()
    } else if (key.upArrow) {
      // 历史记录导航
      navigateHistory(-1)
    } else {
      // 普通输入
      handleRegularInput(input)
    }
  })

  return (
    <Box>
      <Text dimColor>➜ </Text>
      {isVimMode ? (
        <VimTextInput {...vimProps} />
      ) : (
        <TextInput {...textProps} />
      )}
      {showTypeahead && <TypeaheadSuggestions suggestions={suggestions} />}
      <PromptInputFooter {...footerProps} />
    </Box>
  )
}
```

**功能:**
- 支持普通输入和 Vim 模式
- 命令类型提示和补全
- 历史记录导航（上下箭头）
- Ctrl+C 取消操作

#### Messages 组件

渲染完整的对话历史：

```typescript
export function Messages({ messages, scrollRef }: MessagesProps) {
  return (
    <Box flexDirection="column" flex={1}>
      {messages.map((message, index) => (
        <Message
          key={index}
          message={message}
          isLast={index === messages.length - 1}
        />
      ))}
      <ScrollRef ref={scrollRef} />
    </Box>
  )
}
```

#### Message 组件

渲染单条消息，根据消息类型使用不同的渲染器：

```typescript
export function Message({ message, isLast }: MessageProps) {
  switch (message.type) {
    case 'assistant':
      return <AssistantMessage message={message} />
    case 'user':
      return <UserMessage message={message} />
    case 'tool_use':
      return <ToolUseMessage message={message} />
    case 'tool_result':
      return <ToolResultMessage message={message} />
    case 'progress':
      return <ProgressMessage message={message} />
    default:
      return <UnknownMessage message={message} />
  }
}
```

#### 组件模式

**所有组件共享以下模式:**
- 使用 Ink 的 `<Box>` 和 `<Text>` 原语
- 使用 React hooks 管理状态
- 通过 `useTheme()` 实现主题感知
- 通过 `useInput()` 处理键盘输入

---

### 斜杠命令系统

Claude Code 提供了 60+ 个斜杠命令，所有命令实现统一的接口。

`★ Insight ─────────────────────────────────────`
命令系统采用了**插件架构**:
- 命令可以来自多个源（内置、插件、技能、MCP）
- 所有命令实现统一接口
- 支持懒加载和按需执行
- 类型安全的命令参数
─────────────────────────────────────────────────

#### 命令注册表

`src/commands.ts` 管理所有可用命令的加载和注册。

**命令来源:**
```typescript
export async function getCommands(cwd: string): Promise<Command[]> {
  const commands: Command[] = []

  // 1. 内置命令（60+）
  commands.push(...await loadBuiltInCommands())

  // 2. 插件命令
  commands.push(...await loadPluginCommands(cwd))

  // 3. 技能目录命令
  commands.push(...await loadSkillDirectoryCommands(cwd))

  // 4. 打包的技能
  commands.push(...await loadBundledSkills())

  // 5. 工作流脚本
  commands.push(...await loadWorkflowScripts(cwd))

  // 6. MCP 提供的技能
  commands.push(...await loadMcpProvidedSkills())

  return commands
}
```

#### 命令类型

`src/types/command.ts` 定义了命令类型：

```typescript
type Command = CommandBase & (
  | PromptCommand      // 扩展为发送给模型的提示
  | LocalCommand       // 简单文本输出
  | LocalJSXCommand    // 渲染 React 组件
)

interface CommandBase {
  type: string
  name: string
  aliases?: string[]
  description: string
  enabled?: boolean
  hidden?: boolean
  availabilityRequirement?: AvailabilityRequirement
  load?: () => Promise<CommandModule>
}

interface PromptCommand {
  type: 'prompt'
  prompts: string[]
}

interface LocalCommand {
  type: 'local'
  call: (onDone: () => void, context: CommandContext) => void
}

interface LocalJSXCommand {
  type: 'local-jsx'
  call: (
    onDone: () => void,
    context: CommandContext
  ) => React.ReactElement
}
```

#### 命令示例：/help

**注册: `src/commands/help/index.ts`**
```typescript
const help = {
  type: 'local-jsx',
  name: 'help',
  description: 'Show help and available commands',
  load: () => import('./help.js'),
} satisfies Command

export default help
```

**实现: `src/commands/help/help.tsx`**
```typescript
import React from 'react'
import { Box, Text } from '@/ink'
import { LocalJSXCommandCall } from '@/types/command'

export const call: LocalJSXCommandCall = async (onDone, { options: { commands } }) => {
  return <HelpV2 commands={commands} onClose={onDone} />
}

function HelpV2({ commands, onClose }: HelpV2Props) {
  const groupedCommands = groupCommands(commands)

  return (
    <Box flexDirection="column">
      <Box marginBottom={1}>
        <Text bold>Available Commands:</Text>
      </Box>
      {Object.entries(groupedCommands).map(([category, cmds]) => (
        <Box key={category} flexDirection="column" marginBottom={1}>
          <Text dimColor>{category}</Text>
          {cmds.map(cmd => (
            <Box key={cmd.name}>
              <Text bold>/{cmd.name}</Text>
              <Text dimColor> - {cmd.description}</Text>
            </Box>
          ))}
        </Box>
      ))}
      <Text dimColor>Press any key to close</Text>
    </Box>
  )
}
```

#### 命令路由与执行

```typescript
// 查找命令
export function findCommand(
  name: string,
  commands: Command[]
): Command | undefined {
  const normalizedName = name.startsWith('/') ? name.slice(1) : name

  return commands.find(cmd =>
    cmd.name === normalizedName ||
    cmd.aliases?.includes(normalizedName)
  )
}

// 检查命令是否启用
export function isCommandEnabled(cmd: Command): boolean {
  return cmd.enabled !== false
}

// 检查可用性要求
export function meetsAvailabilityRequirement(
  cmd: Command
): boolean {
  if (!cmd.availabilityRequirement) return true

  const { provider, feature } = cmd.availabilityRequirement

  if (provider === 'anthropic' && feature === 'claude-code') {
    // 检查是否在 Claude Code 环境
    return isClaudeCodeEnvironment()
  }

  return false
}
```

#### 特殊命令集

```typescript
// 在 --remote 模式下可用的命令
const REMOTE_SAFE_COMMANDS = new Set([
  'help',
  'clear',
  'exit',
  // ...
])

// 通过移动/网桥可用的命令
const BRIDGE_SAFE_COMMANDS = new Set([
  'help',
  'status',
  // ...
])
```

#### 命令执行流程

```
用户输入 "/help"
      ↓
PromptInput 检测到斜杠命令
      ↓
调用 findCommand('help', commands)
      ↓
检查命令可用性和权限
      ↓
调用 command.load() 懒加载命令模块
      ↓
执行 command.call(onDone, context)
      ↓
渲染返回的 React 组件
      ↓
用户按键 → onDone() → 关闭命令界面
```

---

### 组件层级与数据流

#### 组件层级树

```
replLauncher.tsx
  └─ App.tsx (上下文提供者)
      ├─ FpsMetricsProvider
      ├─ StatsProvider
      └─ AppStateProvider
          └─ REPL.tsx (主屏幕)
              ├─ FullscreenLayout.tsx
              │   ├─ Messages.tsx (对话历史)
              │   │   └─ Message.tsx (单条消息)
              │   │       ├─ AssistantMessage
              │   │       ├─ UserMessage
              │   │       ├─ ToolUseMessage
              │   │       ├─ ToolResultMessage
              │   │       └─ ProgressMessage
              │   └─ PromptInput.tsx (用户输入)
              │       ├─ TextInput.tsx / VimTextInput.tsx
              │       ├─ TypeaheadSuggestions
              │       └─ PromptInputFooter
              ├─ StatusLine.tsx (底部状态栏)
              └─ TaskListV2.tsx (活动任务列表)
                  └─ TaskItemV2
```

#### 数据流

```
1. 用户输入
   ↓
PromptInput 接收输入
   ↓
   ├─ 斜杠命令 → 命令路由 → 执行命令
   │             ↓
   │         更新 AppState → 触发重渲染
   │
   └─ 普通文本 → 提交给 QueryEngine
                  ↓
              query() 处理
                  ↓
              LLM 调用 → 流式响应
                  ↓
              消息追加到 AppState
                  ↓
              触发 React 重渲染
                  ↓
              Messages 组件显示新消息
```

---

### 关键设计模式

`★ Insight ─────────────────────────────────────`
UI 层的架构设计体现了多个设计模式的合理运用:
1. **组合模式**: App、REPL、Layout 逐层组合
2. **策略模式**: TextInput/VimTextInput 根据配置选择
3. **观察者模式**: AppState 订阅和更新触发重渲染
4. **工厂模式**: 消息根据类型创建不同的渲染器
5. **装饰器模式**: ThemeProvider 包装所有组件
─────────────────────────────────────────────────

#### 1. 懒加载

```typescript
// 命令按需加载
const help = {
  load: () => import('./help.js'),
}

// 组件按需加载
const { REPL } = await import('./screens/REPL.js')
```

**优势:**
- 减少初始加载时间
- 只加载实际使用的功能
- 降低内存占用

#### 2. 上下文驱动的状态

```typescript
// App 级别提供全局状态
<AppStateProvider value={{ setAppState }}>
  <REPL />
</AppStateProvider>

// 子组件通过 Hook 访问
function Component() {
  const { appState, setAppState } = useAppState()

  const handleClick = () => {
    setAppState(prev => ({ ...prev, key: value }))
  }

  return <Box>{appState.value}</Box>
}
```

#### 3. 命令模式

```typescript
// 所有命令实现统一接口
type Command = CommandBase & (
  | PromptCommand
  | LocalCommand
  | LocalJSXCommand
)

// 统一的执行方式
function executeCommand(cmd: Command, context: CommandContext) {
  switch (cmd.type) {
    case 'prompt':
      return handlePrompt(cmd, context)
    case 'local':
      return cmd.call(onDone, context)
    case 'local-jsx':
      return renderComponent(cmd.call(onDone, context))
  }
}
```

#### 4. 主题系统

```typescript
// 主题提供者
const ThemeContext = React.createContext(defaultTheme)

export function ThemeProvider({ children, theme }) {
  return (
    <ThemeContext.Provider value={theme}>
      {children}
    </ThemeContext.Provider>
  )
}

// 使用主题
export function Component() {
  const theme = useTheme()

  return (
    <Text color={theme.colors.primary}>
      {text}
    </Text>
  )
}
```

#### 5. Hook 架构

```typescript
// 自定义 Hook 复用逻辑
function useAssistantHistory({ replProps, setAppState, appState }) {
  const [messages, setMessages] = useState(appState.messages)
  const [history, setHistory] = useState<string[]>([])

  const handleUserMessage = async (input: string) => {
    setHistory(prev => [...prev, input])
    const result = await replProps.queryEngine.submitMessage(input)
    setMessages(prev => [...prev, ...result.messages])
  }

  return {
    messages,
    history,
    handleUserMessage,
  }
}

// 在组件中使用
function REPL() {
  const { messages, handleUserMessage } = useAssistantHistory({ ... })

  return (
    <Box>
      <Messages messages={messages} />
      <PromptInput onSubmit={handleUserMessage} />
    </Box>
  )
}
```

#### 6. 记忆化

```typescript
import memoize from 'lodash-es/memoize'

// 记忆化命令加载
const getCommandsMemoized = memoize(getCommands)

C
```

**优势:**
- 避免重复昂贵的操作
- 提升性能
- 减少内存分配

#### 7. 特性标志

```typescript
// 编译时特性消除
if ('bun' in globalThis && import.meta.env) {
  // 只在 Bun 环境中包含的代码
  const feature = import.meta.env.bun ? require('./feature-bun') : null
}
```

---

### 核心文件总结

| 文件 | 用途 |
|------|---------|
| `src/replLauncher.tsx` | REPL 初始化和启动 |
| `src/screens/REPL.tsx` | 主 REPL 屏幕（800KB+） |
| `src/components/App.tsx` | 顶层上下文提供者 |
| `src/ink.ts` | Ink 集成和主题化导出 |
| `src/commands.ts` | 命令注册表和加载 |
| `src/types/command.ts` | 命令类型定义 |
| `src/components/PromptInput/PromptInput.tsx` | 输入处理组件 |
| `src/components/Messages.tsx` | 对话转录渲染 |
| `src/components/Message.tsx` | 单条消息渲染器 |
| `src/components/StatusLine.tsx` | 底部状态栏 |
| `src/components/TaskListV2.tsx` | 活动任务显示 |

这些组件构建了一个灵活、可维护和高性能的 CLI UI 系统，使 Claude Code 在终端环境中提供了流畅的用户体验。

---

## 后续学习

本文完成了基础设施层、核心业务逻辑层、应用编排层和用户界面层的完整分析，包括：

**第1层：基础设施层**
- ✅ 状态管理：轻量 Store 实现
- ✅ 配置系统：多源配置合并策略
- ✅ 工具接口：核心抽象定义
- ✅ API 客户端：与外部服务交互

**第2层：核心业务逻辑层**
- ✅ 工具系统：智能批处理和并发控制
- ✅ 多 Agent 系统：多种隔离策略和 Swarm 协作
- ✅ MCP 集成：多传输支持和多态工具加载
- ✅ 权限系统：多层安全机制和 ML 分类器集成

**第3层：应用编排层**
- ✅ 查询引擎：LLM 交互和响应流处理
- ✅ 工具执行器：智能批处理和并发控制
- ✅ 任务系统：后台任务管理和生命周期

**第4层：用户界面层**
- ✅ REPL 接口：交互式终端和会话管理
- ✅ React 组件系统：基于 Ink 的终端 UI
- ✅ 斜杠命令系统：60+ 命令的插件架构

### 学习总结

通过对 Claude Code 四层架构的深入学习，我们理解了：

1. **分层架构的清晰边界**
   - 每层有明确的职责
   - 层间通过明确的接口通信
   - 便于测试和维护

2. **核心设计模式的应用**
   - Store 模式（状态管理）
   - 工厂模式（工具创建）
   - 观察者模式（订阅更新）
   - 策略模式（多态行为）
   - 插件模式（命令系统）

3. **高性能优化**
   - 懒加载
   - 记忆化
   - 智能批处理
   - 流式处理

4. **类型安全**
   - TypeScript 编译时类型
   - Zod 运行时验证
   - 类型推导

5. **可扩展性**
   - 插件系统
   - MCP 集成
   - 自定义命令
   - 自定义工具

### 下一步

如果你想深入特定主题，可以考虑：

- **特定工具的实现**（如 BashTool、GitTool）
- **权限系统的详细工作原理**
- **MCP 协议的深入理解**
- **UI 组件的具体实现**
- **性能优化技巧**

如果你有任何问题或想深入某个具体部分，请告诉我！
  - REPL 接口：交互式终端
  - React 组件：UI 组件系统
  - 斜杠命令：60+ 命令实现

如果你有任何问题或想深入某个具体部分，请告诉我！

---

## 参考资料

- [Claude Code GitHub 仓库](https://github.com/anthropics/claude-code)
- [Model Context Protocol (MCP) 规范](https://modelcontextprotocol.io/)
- [Ink - React for CLIs](https://github.com/vadimdemedes/ink)
- [Zod - TypeScript Schema Validation](https://zod.dev/)
