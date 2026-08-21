# LangGraph 多智能体旅行规划项目——Agent 岗位面试作战手册

> 目标：不是把项目背下来，而是做到面试官从项目架构、LangGraph、Agent、MCP、Tool Calling、并发、Prompt、Structured Output、工程化、RAG、Memory、Eval 一路追问，你都知道“当前怎么做、为什么这么做、有什么问题、下一步怎么改”。

---

# 一、先确定你的项目定位

## 1. 一句话介绍

这是一个基于 **LangGraph + LangChain + MCP** 构建的多智能体旅行规划系统，通过景点、天气、酒店三个专业 Agent 并行获取外部信息，再由 Planner Agent 汇总生成多日旅行计划，并结合确定性算法完成路线估算、天气适配、预算及行程强度评分，同时提供行程二次调整能力。

这句话建议背熟。

---

# 二、30 秒版本项目介绍

面试官：

> 简单介绍一下你这个 Agent 项目。

回答：

我做的是一个基于 LangGraph 的多智能体旅行规划系统。

整个系统把旅行规划拆成了景点搜索、天气查询、酒店推荐和最终行程规划四个 Agent。景点、天气和酒店三个任务之间不存在强依赖，所以我使用 LangGraph StateGraph 把它们设计成三个并行节点，从 START 同时执行，完成后通过 Join 节点汇总 State，再交给 Planner Agent 统一生成最终行程。

工具层通过 MCP 接入高德地图，Agent 可以自主调用 POI、天气等外部工具，而不是依赖模型自己生成事实数据。

最终计划生成后，我还增加了一层确定性后处理，根据经纬度计算路线距离、行程强度、天气适配度和预算评分，并支持轻松模式、雨天模式、路线优化和景点替换等交互操作。

后端是 FastAPI，前端使用 Vue3 + TypeScript。

---

# 三、1～2 分钟完整项目介绍

如果面试官说：

> 详细说一下。

回答：

这个项目主要解决的问题是传统 LLM 旅行规划容易出现信息幻觉，而且一次 Prompt 很难同时完成搜索、判断和规划。

所以我的整体设计思路是把“信息获取”和“决策规划”拆开。

第一层是 Research Agent，包括：

- Attraction Agent
- Weather Agent
- Hotel Agent

这些 Agent 不直接依赖模型知识，而是要求必须调用 MCP Tool 获取外部数据。

由于这三个任务彼此独立，我最开始其实使用的是串行流程：

景点 → 天气 → 酒店 → Planner。

后来我发现这三个任务之间不存在数据依赖，因此重构为 LangGraph 并行结构：

```text
                    Attraction Agent
                   /
START ----------- Weather Agent -------- Join -------- Planner
                   \
                    Hotel Agent
```

三个分支共享一个 TypedDict State，分别写入：

```text
attractions
weather_info
hotels
```

并使用 Reducer 处理并行状态更新。

然后 Planner Agent 根据前面获取的信息生成 TripPlan。

但是我没有把所有逻辑全部交给 LLM。像距离计算、路线紧凑度、预算评分、天气适配这类确定性问题，我放到了 Python Service 中处理。

所以整个架构其实是：

```text
LLM Agent
+
Tool Calling
+
Workflow Orchestration
+
Deterministic Algorithm
```

而不是完全依赖大模型。

最后通过 FastAPI 提供接口，Vue3 前端展示地图、天气、预算、每日路线和评分，同时支持用户对生成结果进行二次调整。

---

# 四、一定要能画出的系统架构

面试的时候可以直接画：

```text
                        User
                          │
                          ▼
                  Vue3 / TypeScript
                          │
                          ▼
                       FastAPI
                          │
                          ▼
                 TripPlannerWorkflow
                    LangGraph
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
        Attraction      Weather       Hotel
          Agent          Agent         Agent
             │            │            │
             └────────────┼────────────┘
                          │
                       MCP Tools
                          │
                    AMap MCP Server
                          │
                    高德地图服务
                          │
                          ▼
                        Join
                          │
                          ▼
                    Planner Agent
                          │
                          ▼
                      TripPlan
                          │
                          ▼
              Enhancement Service
              ┌────────┬─────────┐
              │        │         │
            Route    Score     Weather
             │         │        Tips
             ▼         ▼
                   Final Plan
```

面试官看到这个图以后，一般会从下面几个方向追问：

1. 为什么需要 Multi-Agent？
2. 为什么要 LangGraph？
3. Agent 怎么共享数据？
4. 为什么可以并行？
5. MCP 是什么？
6. Tool Calling 怎么发生？
7. Planner 怎么保证数据真实？
8. LLM 输出错误怎么办？
9. 为什么不全部让 LLM 做？
10. 怎么上线到生产环境？

后面逐个准备。

---

# 五、核心问题：为什么要做 Multi-Agent？

## 面试官

> 为什么不直接一个 Agent 做到底？

回答重点不是：

> 多 Agent 比较高级。

这是错误回答。

应该回答：

旅行规划实际上包含多个性质不同的子任务。

例如：

```text
信息检索
天气查询
酒店推荐
旅行规划
路线优化
```

它们需要的 Prompt、Tool 和上下文并不相同。

如果全部塞给一个 Agent，会有几个问题：

第一，上下文越来越复杂。

第二，一个 Agent 面对大量 Tool 时，Tool Selection 的复杂度会提高。

第三，不同任务没办法独立并行。

第四，某个任务失败以后，很难单独处理。

第五，Prompt 很容易同时承担“搜索规则 + 天气规则 + 酒店规则 + 规划规则”，长期维护困难。

因此我把领域能力拆成专业 Agent。

不过我也不会认为“Agent 越多越好”。

如果任务逻辑完全确定，比如明确知道现在就是查询天气，那么生产环境甚至可以直接调用 Weather Tool，而不是再经过一个 Agent。

所以我的理解是：

> Multi-Agent 应该用于职责隔离和动态决策，而不是为了多 Agent 而多 Agent。

这个回答非常重要。

---

# 六、为什么用 LangGraph，而不是纯 LangChain？

推荐回答：

LangChain 更适合解决 Model、Prompt、Tool、Agent 等组件封装问题。

而我的需求已经不只是单个 Agent，而是存在：

```text
并行
状态共享
Join
条件分支
错误处理
未来可能的人机交互
```

所以更适合使用 Graph 描述整个执行流程。

LangGraph 的一个核心价值就是把 Agent Application 显式建模为：

```text
Node
Edge
State
Conditional Edge
Reducer
```

这样整个执行流程是可控的，而不是把所有逻辑都隐藏在一次 Agent Loop 中。

当前 LangGraph 官方也仍然将 Graph API 中的 State、Reducer、分支和并行作为核心编排机制。

---

# 七、LangGraph Workflow 必须会讲到源码级

你项目中核心结构：

```python
workflow = StateGraph(TripPlannerState)

workflow.add_node("search_attractions", ...)
workflow.add_node("check_weather", ...)
workflow.add_node("find_hotels", ...)
workflow.add_node("join_research_results", ...)
workflow.add_node("plan_itinerary", ...)
workflow.add_node("handle_error", ...)
```

然后：

```text
START
 ├─ search_attractions
 ├─ check_weather
 └─ find_hotels
```

三路执行结束：

```text
[
 search_attractions,
 check_weather,
 find_hotels
]
        ↓
join_research_results
```

之后：

```text
check_error
    ↓
continue → plan_itinerary
error    → handle_error
```

所以严格来说，你这个 Graph 同时包含：

**Fan-out**

```text
START → 多个 Node
```

和：

**Fan-in**

```text
多个 Node → Join
```

这两个词可以记住。

---

# 八、为什么三个 Research Agent 可以并行？

答案：

因为它们之间没有数据依赖。

景点搜索需要：

```text
city
preferences
```

天气查询需要：

```text
city
```

酒店查询需要：

```text
city
accommodation
```

它们全部只依赖用户原始 TripRequest。

因此：

```text
Attraction
Weather
Hotel
```

没有必要串行等待。

原版：

```text
Attraction → Weather → Hotel
```

理论延迟近似：

```text
T = T1 + T2 + T3
```

并行后：

```text
T ≈ max(T1,T2,T3)
```

再加上一些 Graph 调度和后续 Planner 开销。

注意：

**不要告诉面试官“性能提升了 60%”之类数字。**

因为当前项目没有 Benchmark。

如果问提升多少：

> 目前项目主要完成了架构层面的串行转并行，还没有做严格 P95 latency benchmark，因此我不会直接给一个虚假的百分比。从执行模型上，它把三个独立网络/LLM任务的累计等待改成接近最大单任务等待，下一步会用 LangSmith Trace 或自定义埋点统计各节点耗时和 P50/P95。

这是非常好的回答。

---

# 九、什么是 State？

你的：

```python
class TripPlannerState(TypedDict):
```

主要包括：

```text
request
user_input

attractions
weather_info
hotels

messages

trip_plan
error
current_step
```

回答：

State 是整个 Graph 执行过程中共享的数据载体。

每个 Node：

```text
读取 State
    ↓
执行逻辑
    ↓
返回 Partial State Update
```

而不是直接把整个对象随意修改。

例如 Attraction Agent 返回：

```python
{
    "attractions": attractions,
    "messages": [...]
}
```

Weather Agent 返回：

```python
{
    "weather_info": weather_info
}
```

最终 LangGraph 根据 State Schema 合并这些 Update。

---

# 十、Reducer 是什么？

这个是非常高概率问题。

项目中：

```python
messages: Annotated[List[Dict], add_messages]
```

表示多个节点写 messages 时不是简单覆盖，而是通过：

```text
add_messages
```

合并。

另一个：

```python
error: Annotated[Optional[str], update_error]
```

Reducer：

```python
def update_error(prev, new):
    return prev or new
```

目的是：

多个并行 Agent 同时可能返回 error。

如果没有 Reducer，并行更新同一个 State Key 会产生冲突或覆盖问题。

所以 Reducer 本质上定义：

> 多个 Node 对同一个 State Key 产生 Update 时，这些 Update 应该如何合并。

官方 LangGraph 文档同样强调，每个 State Key 都有自己的 Reducer；如果没有指定 Reducer，默认更新通常是覆盖。

---

# 十一、面试官可能继续攻击你的 Reducer

面试官：

> `prev or new` 有什么问题？

这个问题你要会。

回答：

当前实现的目标只是保留一个错误，能够实现“有任意 Agent 失败，就进入错误分支”。

但是它并不是最理想的生产设计。

如果 Attraction 和 Weather 同时失败：

```text
Attraction error
Weather error
```

最终只会保存其中一个。

而且“第一个”错误实际可能受并行执行和合并顺序影响。

更好的方案是：

```python
errors: Annotated[list[AgentError], operator.add]
```

或者：

```python
errors = {
    "attraction": ...,
    "weather": ...,
    "hotel": ...
}
```

这样能够保留每个 Branch 的错误状态。

然后 Join 判断：

```text
全部失败 → fallback

部分失败 → degraded planning

全部成功 → normal planning
```

这比当前“一处失败整个流程 fallback”更合理。

这一段属于加分回答。

---

# 十二、为什么需要 Join Node？

回答：

Join 并不是为了做复杂计算。

它主要提供一个显式同步点：

```text
Research Agents
       ↓
等待全部分支
       ↓
Join
       ↓
统一判断状态
       ↓
Planner
```

好处：

1. Planner 不会在 Research 尚未全部完成时执行。
2. 可以统一做 Error Check。
3. 将来可以在 Join 里做结果去重、数据质量检查、Ranking。
4. Graph 拓扑更加清晰。

---

# 十三、Agent 到底是什么？

面试千万别回答：

> Agent 就是会调用工具的大模型。

不完整。

推荐回答：

我认为 Agent 是：

> 以 LLM 作为决策组件，在目标和上下文约束下，可以动态选择下一步行为，并通过 Tool 与外部环境交互的一种执行系统。

通常包含：

```text
Model
Prompt
State / Context
Tools
Decision Loop
Stop Condition
```

而 Workflow 与 Agent 最大区别之一：

Workflow：

```text
路径主要由开发者提前定义
```

Agent：

```text
下一步行为可能由模型动态决定
```

你的项目其实是：

> 外层 Deterministic Workflow + 内层 Agent。

这是一个非常好的架构表述。

---

# 十四、你这个项目是不是“真正的多 Agent”？

如果面试官比较苛刻，可能问：

> 这些 Agent 之间又没有直接对话，你凭什么叫 Multi-Agent？

回答：

我这里的 Multi-Agent 不是 Agent-to-Agent Chat 类型，而是：

> Orchestrated Multi-Agent。

也就是由 LangGraph 作为 Supervisor / Orchestration Layer，多个具有独立 Role、Prompt、Tool Calling 能力的 Agent 分工完成子任务，通过 Shared State 进行间接协作。

它们不需要直接互相发送自然语言消息。

协作过程是：

```text
Agent
 ↓
Structured State
 ↓
Graph
 ↓
Other Agent
```

我更倾向这种模式，因为业务系统里比自由 Agent Chat 更容易控制。

---

# 十五、为什么 Attraction / Weather / Hotel 都用了 Agent？

这个问题其实对项目是一种挑战。

推荐回答：

当前版本主要有两个考虑：

第一，希望每个领域节点能够根据 MCP Server 暴露出来的工具进行 Tool Selection。

第二，为未来加入多个搜索工具、点评工具、天气源等能力保留扩展空间。

但是如果生产环境中 Weather 节点永远只调用：

```text
maps_weather
```

那么确实没有必要每次经过 LLM。

更合理的生产优化是：

```text
明确任务
→ deterministic tool call

存在动态 Tool Selection
→ Agent
```

这样可以降低：

```text
token cost
latency
tool-selection error
```

这是非常成熟的回答。

---

# 十六、Tool Calling 是怎么发生的？

流程：

```text
User Query
    ↓
Agent
    ↓
LLM 判断是否调用 Tool
    ↓
生成 Tool Call
    ↓
LangChain 执行 Tool
    ↓
Tool Result
    ↓
返回 Model
    ↓
Model 决定是否继续调用
    ↓
Final Answer
```

项目里使用：

```python
create_agent(
    model=llm,
    tools=tools,
    system_prompt=...
)
```

Search Agent Prompt 中明确要求：

```text
必须使用 Tool
不要自己编造
```

所以 Agent 会调用 MCP Tool 获取数据。

---

# 十七、MCP 是什么？

建议回答：

MCP，全称 Model Context Protocol。

可以把它理解为：

> AI 应用与外部 Tool / Resource / Context Provider 之间的一层标准协议。

传统方式：

```text
Agent → 自己写高德 SDK
Agent → 自己写数据库 SDK
Agent → 自己写 GitHub SDK
Agent → 自己写文件系统
```

每一个都要单独适配。

MCP 的目标是：

```text
AI Application
       ↓
      MCP
       ↓
MCP Server
       ↓
External System
```

项目中是：

```text
LangChain Agent
       ↓
langchain-mcp-adapters
       ↓
MCP Tool
       ↓
stdio
       ↓
amap-mcp-server
       ↓
高德 API
```

MCP 官方定义中，Server 可以向模型暴露 Tool，每个 Tool 具有名称、描述及输入 Schema，从而让模型调用外部系统。

---

# 十八、为什么 MCP 比直接写 REST API 好？

不要绝对说“更好”。

回答：

取决于场景。

直接 REST：

优点：

```text
控制简单
调用路径短
性能容易优化
```

MCP：

优点：

```text
标准化 Tool 接口
方便不同 Agent Host 复用
Tool Discovery 更自然
减少不同模型应用重复适配
```

所以：

如果只是一个固定业务服务，我可能直接 REST。

如果希望一套工具同时提供给多个 Agent / IDE / AI Application，MCP 的复用价值会更大。

---

# 十九、项目中的 MCP 怎么启动？

代码中：

```python
connection = {
    "command": "uvx",
    "args": ["amap-mcp-server"],
    "transport": "stdio"
}
```

含义：

宿主程序通过子进程方式运行：

```text
amap-mcp-server
```

然后通过：

```text
stdin/stdout
```

进行 MCP 通信。

再通过：

```python
load_mcp_tools(...)
```

把 MCP Server 暴露出来的 Tool 转换为 LangChain BaseTool。

---

# 二十、为什么要缓存 MCP Tools？

项目中：

```python
_cached_tools
```

因为 MCP Tool 初始化涉及：

```text
启动 Server
建立连接
发现 Tools
构造 Tool 对象
```

如果每个 HTTP Request 都重新执行，会造成额外开销。

所以使用进程级缓存。

不过生产环境进一步需要考虑：

```text
连接失效
Server Restart
并发安全
健康检查
缓存重建
```

---

# 二十一、为什么还写了 Async Tool Wrapper？

这是你项目里一个很适合深挖的点。

一些 MCP Tool 主要提供异步 `_arun()`。

而当前 Agent 调用链采用：

```python
agent.invoke()
```

同步执行。

因此项目通过 Wrapper：

```text
sync _run
   ↓
async _arun
```

并使用：

```text
asyncio
nest_asyncio
```

做兼容。

回答到这里即可。

然后主动补一句：

> 不过这个方案更像兼容层。生产环境我更倾向把整条链路改成 async-first，例如 FastAPI → graph.ainvoke → agent.ainvoke → async MCP Tool，而不是长期依赖同步包装。

这句话非常重要。

---

# 二十二、为什么 FastAPI 已经 async 了，你 Graph 还是 sync？

项目目前：

```python
async def plan_trip(...):
```

内部：

```python
workflow.plan_trip(request)
```

然后：

```python
graph.invoke(...)
```

也就是：

```text
Async HTTP Endpoint
       ↓
Sync Graph
```

面试官问到时千万不要硬说没问题。

正确回答：

这是当前版本需要继续优化的地方。

因为同步 Agent / LLM 网络调用可能阻塞当前 Event Loop，影响 FastAPI 的并发能力。

生产化会改成：

```text
FastAPI
   ↓
await workflow.plan_trip_async()
   ↓
await graph.ainvoke()
   ↓
await agent.ainvoke()
   ↓
Async MCP Tool
```

如果还有 CPU 密集算法，再考虑：

```text
Thread Pool
Process Pool
```

而不是阻塞 Event Loop。

---

# 二十三、LLM 层怎么设计？

项目：

```python
ChatOpenAI(
    api_key,
    base_url,
    model
)
```

模型参数来自：

```text
OPENAI_API_KEY
OPENAI_BASE_URL
OPENAI_MODEL
```

因此模型调用层并没有完全绑死某一家平台，而是可以连接兼容 OpenAI 接口的服务。

同时使用 Singleton：

```text
_llm_instance
```

避免每次请求重复初始化 Model Client。

---

# 二十四、为什么 temperature=0.7？合理吗？

这是一个可以自我批判的问题。

回答：

当前项目统一用了 0.7，比较偏生成性。

但进一步生产化，我会按任务拆开。

例如 Research / Structured Extraction：

```text
temperature ≈ 0 ～ 0.2
```

因为更重视稳定和格式。

Planner：

```text
可以适当高一些
```

因为存在路线描述、旅行建议等开放生成内容。

也就是说：

> 不同 Agent 应该有不同 Model Configuration，而不是所有 Agent 共享一个 temperature。

---

# 二十五、Prompt 是怎么设计的？

Research Agent Prompt 强约束：

```text
必须使用 Tool
禁止编造
调用结束返回 JSON
```

Planner Prompt：

```text
规定完整 JSON Schema
每日 2～3 景点
必须三餐
必须酒店
包含预算
```

设计目标是：

```text
Role
Task
Tool Constraint
Output Constraint
Business Constraint
```

---

# 二十六、Prompt 能真正防止 Hallucination 吗？

回答：

不能。

Prompt 只能降低概率。

真正降低幻觉需要多层机制：

```text
Tool Grounding
Structured Output
Schema Validation
Entity Validation
Deterministic Post-processing
Retry / Repair
```

项目当前做了：

```text
Tool Grounding
Pydantic Schema
JSON Parsing
Algorithm Post-processing
```

但是仍有进一步空间。

---

# 二十七、项目最大的 Grounding 问题是什么？

这是这份项目源码里非常关键的点。

当前 Planner Query 实际上传入的是：

```text
找到几个景点
前三个景点名称

天气有几天

找到几个酒店
前两个酒店名称
```

也就是说：

Research Agent 已经获取了：

```text
location
address
rating
weather
...
```

但 Planner 没有拿到完整结构化信息。

同时 Prompt 又要求 Planner：

```text
经纬度必须真实准确
```

这是有矛盾的。

Planner 可能重新生成甚至幻觉坐标。

正确的改造：

```text
Research Tool
       ↓
Canonical POI Objects
       ↓
Planner 只输出 POI ID / Selection
       ↓
Backend 根据 ID 组装实体字段
```

例如 Planner 不再生成：

```json
{
  "name": "故宫",
  "longitude": ...
}
```

而只生成：

```json
{
  "poi_id": "B000A..."
}
```

最终：

```text
poi_id → Research Result → 完整 POI
```

这样模型不再“创造事实”。

这会是你最好的高级回答之一。

---

# 二十八、JSON 输出当前有什么问题？

现在主要做法：

```text
Prompt 要求 JSON
       ↓
LLM 返回 Text
       ↓
_extract_json()
       ↓
json.loads()
       ↓
Pydantic
```

问题：

```text
Markdown code block
多余解释
JSON 不完整
字段缺失
类型错误
引号问题
Token 截断
```

虽然项目做了一些：

```text
寻找 ```json
寻找 []
寻找 {}
```

但仍然不够稳定。

---

# 二十九、如何改成 Structured Output？

推荐回答：

我会把 TripPlan 本身直接作为 Structured Schema。

当前 LangChain `create_agent` 已经提供 `response_format` 机制，让 Agent 最终输出经过 Schema 验证的 `structured_response`，因此可以减少“Prompt 规定 JSON + 手工字符串截取”的脆弱逻辑。

例如思路：

```text
Planner Agent
    ↓
response_format = TripPlanSchema
    ↓
Structured Response
    ↓
Pydantic Validation
```

然后：

```text
Validation Error
    ↓
Retry / Repair
```

---

# 三十、为什么 LLM 和确定性算法混合？

这是项目很值得强调的思想。

回答：

不是所有问题都应该交给 LLM。

LLM 擅长：

```text
自然语言理解
模糊偏好处理
复杂选择
生成解释
开放式规划
```

传统代码擅长：

```text
距离计算
预算求和
排序
规则校验
评分
权限
状态机
```

因此我的设计原则是：

> LLM 负责不确定性决策，代码负责确定性约束。

项目中：

```text
Planner → LLM
```

但：

```text
Haversine Distance
Nearest Neighbor
Budget Score
Weather Score
Packing Rules
```

由 Python 计算。

这个思路非常符合业务 Agent。

---

# 三十一、Haversine 是什么？

用于计算地球上两个经纬度坐标之间的大圆距离。

核心考虑：

地球不是平面，所以不能直接：

```text
sqrt((lon1-lon2)^2 + (lat1-lat2)^2)
```

项目里使用：

```text
Earth Radius ≈ 6371 km
```

然后计算两点球面距离。

不过：

> Haversine 得到的是空间直线意义上的地理距离，不是真实道路距离。

---

# 三十二、为什么 Haversine 不能直接做真实路线？

因为现实路线受到：

```text
道路结构
单行线
河流
桥梁
地铁线路
拥堵
步行通道
```

影响。

所以：

```text
Haversine 5 km
```

真实开车可能：

```text
8 km
```

甚至更多。

因此当前项目的路线能力应该描述为：

> 基于地理距离的轻量路线估算与排序。

而不是：

> 高德实时最优路线。

这条一定记住。

---

# 三十三、Nearest Neighbor 是什么？

当前路线重排：

```text
Hotel
 ↓
寻找最近景点
 ↓
到达该景点
 ↓
继续寻找最近景点
 ↓
...
```

就是最近邻贪心。

时间复杂度大概：

```text
O(n²)
```

对于每天：

```text
2～5 个景点
```

完全够用。

---

# 三十四、Nearest Neighbor 是最优解吗？

不是。

它只是 Greedy Heuristic。

可能出现：

```text
前面选择局部最优
导致后面整体路线更长
```

如果做更严格路线规划：

可以建模成：

```text
TSP / VRP
```

再使用：

```text
2-opt
Dynamic Programming
OR-Tools
Genetic Algorithm
```

但旅行规划还存在：

```text
开放时间
时间窗
吃饭时间
天气
酒店
预约
```

所以更接近：

> Vehicle Routing / Scheduling with Constraints。

这个回答会比较高级。

---

# 三十五、当前为什么不直接上 TSP？

因为每天只有少量景点。

如果：

```text
2～3 个节点
```

为此引入复杂 Solver 意义有限。

当前最近邻：

```text
简单
可解释
计算快
```

已经足够用于 Demo 和初步优化。

真正生产化后，随着约束变多，再升级为 Constraint Solver。

---

# 三十六、行程评分怎么做？

项目每天计算四个维度：

```text
route_compactness
intensity
budget_friendliness
weather_fit
```

然后：

```text
overall =
(route + intensity + budget + weather) / 4
```

### 路线紧凑度

距离越大，扣分越多。

### 强度

把：

```text
景点游览分钟
+
交通分钟
```

作为当天 Load。

目标大概围绕合理的日间活动时长。

### 预算

根据用户：

```text
经济
舒适
豪华
```

设定不同日预算参考值。

### 天气

恶劣天气 + 室外景点：

```text
降低评分
```

---

# 三十七、评分为什么不用 LLM？

回答：

评分需要：

```text
可重复
稳定
可解释
```

如果让 LLM 给同一个 Plan 打两次分：

可能：

```text
82
87
```

确定性规则：

同一个输入得到同一个结果。

所以这里优先用规则。

未来可以：

```text
规则分
+
Learning-to-Rank
+
用户反馈
```

逐渐优化，而不是直接让 LLM 打分。

---

# 三十八、行程调整算 Human-in-the-loop 吗？

严格回答：

> 当前版本具有用户反馈后重新调整 Plan 的交互能力，但还不是严格意义上的 LangGraph Human-in-the-loop。

当前是：

```text
User 点击按钮
      ↓
新的 HTTP Request
      ↓
reorder_day()
```

而真正 LangGraph HITL 通常是：

```text
Graph Running
      ↓
interrupt
      ↓
保存 Checkpoint
      ↓
等待 Human Input
      ↓
Command(resume)
      ↓
继续执行
```

官方 LangGraph 的 Interrupt/Persistence 就是为这种暂停、保存 State、人工输入后恢复执行的模式设计。

---

# 三十九、怎么把项目升级成真正 HITL？

例如生成初步计划：

```text
Research
   ↓
Draft Planner
   ↓
interrupt
```

给用户：

```text
方案 A
方案 B
```

用户：

```text
选择 A
+
不要故宫
```

然后：

```text
Command(resume=user_feedback)
```

Graph 继续：

```text
Optimize
   ↓
Final Plan
```

此时配合 Checkpointer：

```text
thread_id = user/session
```

就可以恢复同一次旅行规划。

---

# 四十、Memory 和 State 区别？

非常常见。

### State

当前一次 Graph Execution 的工作状态。

例如：

```text
attractions
hotels
weather
```

### Short-term Memory

同一个会话 / thread 多轮之间保留信息。

例如：

```text
上一轮用户说每天最多两个景点
```

LangGraph 可以通过 Checkpointer 保存 thread-scoped State。

### Long-term Memory

跨 Conversation 保存用户长期偏好：

```text
用户喜欢博物馆
不吃辣
预算偏经济
```

通常需要外部持久化系统。

---

# 四十一、你项目有 Memory 吗？

回答：

当前版本没有真正做持久化 Memory。

目前：

```text
每次 TripRequest
→ 新建 Initial State
→ 执行 Graph
```

没有：

```text
Checkpointer
thread_id
User Memory Store
```

所以简历不能写：

> 实现 Agent 长期记忆。

如果面试官问未来：

> 我会把短期执行状态用 LangGraph Checkpointer 持久化，用户长期偏好单独进入 Profile / Memory Store，并明确区分 Session State 和 Long-Term User Preference。

---

# 四十二、RAG 是什么？

推荐回答：

RAG 是 Retrieval-Augmented Generation。

基本过程：

```text
User Query
     ↓
Retriever
     ↓
Relevant Documents
     ↓
Prompt Context
     ↓
LLM Generation
```

它解决的核心不是：

> 让模型变聪明。

而是：

> 给模型补充当前任务需要的外部知识。

---

# 四十三、这个项目用了 RAG 吗？

没有。

MCP Tool Calling：

```text
调用外部 API
```

RAG：

```text
检索知识库文档
```

属于两个不同概念。

不要把：

```text
高德 POI Tool
```

说成 RAG。

---

# 四十四、旅行项目如果加入 RAG，可以检索什么？

例如：

```text
旅行攻略
景区说明
当地政策
历史文化资料
用户收藏攻略
企业内部旅行知识库
景点注意事项
```

但实时数据：

```text
天气
营业状态
实时交通
酒店价格
```

仍更适合：

```text
Tool / API
```

所以理想结构：

```text
Static/Semistructured Knowledge → RAG

Realtime World State → Tool Calling
```

---

# 四十五、Embedding 是什么？

Embedding 把：

```text
Text
```

映射到：

```text
Dense Vector
```

语义相近的文本：

```text
Vector Distance 更近
```

然后通过：

```text
Cosine Similarity
Dot Product
Euclidean Distance
```

寻找相似 Document。

---

# 四十六、Chunk 怎么设计？

不要回答固定“500 Token”。

应该说：

Chunk Strategy 要根据数据结构设计。

比如旅游攻略：

```text
按景点
按章节
按段落
```

比机械每 500 Token 更合理。

需要平衡：

```text
Chunk 太大 → 噪音大
Chunk 太小 → 上下文断裂
```

还要考虑：

```text
Overlap
Metadata
Parent-child retrieval
```

---

# 四十七、Vector DB 和 Elasticsearch 区别？

面试 Agent 岗很可能问。

Vector DB：

```text
Semantic Similarity
```

Elasticsearch：

传统强项：

```text
BM25
关键词
Filter
Aggregation
```

生产 RAG 往往做：

```text
Hybrid Search
=
BM25
+
Vector Retrieval
```

之后再：

```text
Reranking
```

---

# 四十八、什么是 Rerank？

第一阶段 Retriever：

```text
Top 50
```

强调 Recall。

第二阶段 Reranker：

```text
Top 5
```

强调 Precision。

例如：

```text
Embedding Retrieval
       ↓
Cross Encoder / Reranker
       ↓
LLM
```

---

# 四十九、Agent 为什么会陷入死循环？

可能：

```text
模型不停调用 Tool
Tool 返回无效结果
模型再次调用同一个 Tool
```

生产环境要有限制：

```text
max_steps
max_tool_calls
timeout
token budget
duplicate call detection
```

以及：

```text
Stop Condition
```

---

# 五十、怎么防 Tool 被乱调用？

可以从五层控制：

```text
Tool Description
Tool Schema
Prompt Policy
Runtime Permission
Business Validation
```

例如：

支付 Tool：

绝不能只靠：

```text
Prompt：不要乱支付。
```

应该：

```text
LLM 提出 Action
      ↓
Backend 校验
      ↓
Human Approval
      ↓
真正支付
```

---

# 五十一、Agent 安全有哪些问题？

重点准备：

```text
Prompt Injection
Indirect Prompt Injection
Sensitive Data Leakage
Excessive Tool Permission
Arbitrary Code Execution
SQL Injection
SSRF
Tool Result Poisoning
```

原则：

> LLM 不应该成为最终权限控制层。

权限必须由业务后端校验。

---

# 五十二、什么是 Prompt Injection？

用户：

```text
Ignore previous instructions...
```

试图覆盖 System Instruction。

Indirect Prompt Injection：

恶意内容藏在：

```text
网页
PDF
邮件
Tool Result
```

Agent 读取后被诱导执行危险操作。

---

# 五十三、怎么防 Prompt Injection？

不能完全依赖 Prompt。

要：

```text
Least Privilege
Tool Allowlist
Input Validation
Output Validation
Sensitive Action Approval
Sandbox
Domain Filtering
Permission Boundary
```

核心思想：

> 即使模型被骗，也不能拥有无限权限。

---

# 五十四、生产 Agent 怎么做可观测性？

至少记录：

```text
request_id
thread_id
model
prompt version
node
latency
token usage
tool call
tool input
tool output
retry
error
final status
```

然后看：

```text
P50/P95 Latency
Token Cost
Tool Success Rate
Task Success Rate
Fallback Rate
```

项目 requirements 中已经存在 LangSmith，但当前代码没有完整 Eval/Trace 实践，因此只能说：

> 具备接入条件 / 后续准备接入。

不能说已经做完。

---

# 五十五、Agent 怎么做 Evaluation？

这是现在 Agent 岗很重要的问题。

至少分四层。

### 1. Component Eval

例如：

```text
POI Search Accuracy
Weather Tool Success
JSON Parse Rate
```

### 2. Trajectory Eval

检查：

```text
Agent 有没有选择正确 Tool
有没有重复调用
执行路径是否合理
```

### 3. Final Answer Eval

例如：

```text
景点真实性
行程可行性
预算准确性
天气适配
```

### 4. Online Metrics

例如：

```text
用户采纳率
修改次数
重新生成率
完成率
```

---

# 五十六、LLM-as-a-Judge 能不能直接作为 Eval？

可以使用，但不能作为唯一标准。

因为 Judge 自身也会：

```text
有偏差
不稳定
偏好某类表达
```

最好组合：

```text
Deterministic Metrics
+
Human Evaluation
+
LLM Judge
+
Business Metrics
```

---

# 五十七、你的项目如何设计 Eval Dataset？

可以准备：

```text
北京历史文化 3 日游
上海亲子 2 日游
杭州老人友好
重庆美食
三亚雨天
低预算
高温天气
用户要求每天最多两景点
```

每个 Case 设置 Constraint。

例如：

```text
每天 ≤ 2 景点
预算 ≤ X
雨天室外景点 ≤ 1
不能出现城市外 POI
```

然后自动检测：

```text
Constraint Satisfaction Rate
```

---

# 五十八、项目当前错误处理怎么做？

三个 Research Agent：

```text
try
 ↓
error → State.error
```

Join 后：

```text
_check_error()
```

如果存在 Error：

```text
handle_error
```

然后：

```text
_create_fallback_plan
```

所以 Graph 不会直接崩掉。

---

# 五十九、这个错误策略有什么不足？

目前属于：

> Fail One → Fallback All。

例如：

天气接口失败：

```text
Attractions OK
Hotel OK
Weather Fail
```

理论上仍然可以生成一个：

```text
无天气数据的行程
```

但当前会直接进入 fallback。

更好的：

```text
Partial Failure
     ↓
Degraded Mode
```

例如：

```text
Weather unavailable
→ Planner 正常规划
→ UI 显示天气暂不可用
```

只有：

```text
关键数据全部失败
```

再 fallback。

---

# 六十、Fallback Plan 有什么问题？

当前 fallback 使用模拟景点，并且坐标是基于固定数值生成。

它适合作为：

```text
开发阶段演示 / 防止接口完全空白
```

但不适合生产。

生产应该：

```text
明确告诉用户实时服务不可用
```

而不是返回看起来真实、实际上虚构的景点。

这体现一个原则：

> Graceful Degradation 不等于伪造数据。

非常值得讲。

---

# 六十一、还有哪些源码层问题？

这部分是“面试官看你 GitHub”的保命区。

## 问题 1：Planner Grounding 不充分

前面已经讲。

---

## 问题 2：同步 Graph 阻塞 Async FastAPI

优化：

```text
ainvoke
async Tool
```

---

## 问题 3：失败过度降级

优化：

```text
Branch-level error
Partial planning
```

---

## 问题 4：Structured Output 不够稳

优化：

```text
response_format + Pydantic
```

---

## 问题 5：真实路线没有进入核心规划

当前核心路线：

```text
Haversine + Speed Estimate
```

不是：

```text
AMap actual routing
```

下一步：

```text
景点顺序候选
     ↓
高德 Route Matrix / Route API
     ↓
真实行驶时间
     ↓
Optimize
```

---

## 问题 6：部分 Map Service 仍是 TODO

例如独立的 POI / Weather Service 中存在：

```text
Tool 调完以后
TODO parse
return []
```

主 Trip Workflow 因为直接通过 Agent MCP Tool 获取数据，所以不完全依赖这些 API。

但从工程完整度来说，这部分应该补齐。

---

## 问题 7：Health Check 存在历史代码问题

Map Service Health Endpoint 仍访问了旧结构字段。

生产环境应该：

```text
真正 ping MCP Server
检查 Tool Discovery
检查 LLM
检查外部 API
```

而不是只检查 Python 对象是否存在。

---

## 问题 8：坐标解析失败时可能回退到 0,0

这会污染：

```text
距离
路线评分
地图
```

更合理：

```text
invalid coordinate
→ None / validation error
→ geocode repair
```

---

## 问题 9：Enhancement 被重复执行

TripPlan parse 阶段已经 enhance 一次，而 Workflow 返回前又 enhance。

由于当前 Enhancement 基本是重新计算，因此结果问题不大，但存在重复计算。

应该把 Enhancement 责任集中在一个 Layer。

---

# 六十二、如果让你现在重构项目，你怎么做？

这是超级高频题。

可以直接回答以下架构：

```text
                   API Gateway
                        │
                        ▼
                Trip Agent Service
                        │
                  LangGraph Runtime
                        │
           ┌────────────┼────────────┐
           ▼            ▼            ▼
         POI Node    Weather Node   Hotel Node
           │            │            │
       Tool/API      Tool/API      Tool/API
           └────────────┼────────────┘
                        ▼
                    Normalize
                        ▼
                 Candidate Store
                        ▼
                  Planner Agent
                只输出 Entity ID
                        ▼
                 Constraint Engine
             ┌──────────┼──────────┐
             ▼          ▼          ▼
          Routing     Budget    Time Window
             │
             ▼
            Eval
             │
             ▼
         Human Review
             │
             ▼
          Final Plan
```

关键改变：

```text
固定任务 → Direct Tool
动态决策 → Agent

文本 JSON → Structured Output

实体重新生成 → Entity ID Grounding

同步 → Async

One-failure fallback → Partial degradation

直线距离 → Real Route API

无 Memory → Checkpointer + User Profile

无 Eval → Offline Dataset + Online Metrics
```

---

# 六十三、如果数据量和用户量上来了怎么办？

分层回答。

### API

```text
FastAPI 多 Worker
Load Balancer
```

### Agent

不能简单无限并发，因为 LLM Provider 有：

```text
RPM
TPM
Concurrency Limit
```

需要：

```text
Semaphore
Rate Limiter
Queue
```

### Cache

适合缓存：

```text
POI
景点详情
城市信息
```

天气：

TTL 更短。

LLM：

可以根据：

```text
Prompt Hash
```

缓存部分确定请求。

### Async

网络 IO：

```text
async
```

### Background Task

如果旅行规划需要几十秒：

```text
POST /trip
→ task_id

Worker
→ Agent Workflow

GET/SSE/WebSocket
→ progress
```

---

# 六十四、为什么不把整个请求都扔 Celery？

如果是：

```text
5～30 秒
```

且希望 Streaming：

可以直接异步服务。

如果：

```text
长时间任务
需要可靠重试
用户离开页面后继续运行
```

更适合：

```text
Task Queue
```

例如：

```text
Celery / Redis
```

架构依需求决定。

---

# 六十五、Agent Streaming 怎么做？

可以展示：

```text
正在搜索景点
已找到 12 个景点
正在查询天气
正在生成计划
```

而不是用户等 20 秒白屏。

实现可以：

```text
LangGraph Stream
      ↓
SSE
      ↓
Frontend
```

Agent 当前可使用 `stream`/`invoke` 等 Graph/Agent 执行方式。

---

# 六十六、SSE 和 WebSocket 怎么选？

只需要：

```text
Server → Client
```

持续推送 Agent Progress：

SSE 很合适。

需要：

```text
双向实时交互
```

例如用户随时打断：

WebSocket 更合适。

---

# 六十七、Token Cost 怎么优化？

可以讲：

```text
小模型处理简单任务
大模型负责最终规划

固定任务不经过 LLM

减少 Tool List

压缩 Context

结构化 State 不重复转自然语言

Prompt Cache

RAG Top-K 控制

历史消息总结

Output Token Limit
```

项目当前还有一个非常明显的优化机会：

天气查询这种固定操作：

```text
直接 Tool
```

可能比：

```text
LLM → Tool → LLM
```

便宜很多。

---

# 六十八、为什么 Agent 应该限制 Tool 数量？

Tool 越多：

模型需要在更大的 Action Space 里做选择。

可能导致：

```text
Tool Selection Error
Prompt 变长
Schema Token 增多
```

因此可以：

```text
Router
 ↓
选择 Tool Set
 ↓
Domain Agent
```

而不是给所有 Agent 100 个 Tool。

---

# 六十九、什么是 Context Engineering？

不仅仅是 Prompt Engineering。

你可以理解为：

> 决定某一时刻，模型到底能看到什么信息。

包括：

```text
System Prompt
Conversation
Retrieved Docs
Tool Results
User Profile
Current State
Memory
```

好的 Agent 很大程度取决于：

```text
在正确时间给模型正确上下文。
```

而不是单纯写一个很长 Prompt。

---

# 七十、为什么你这个项目的 Planner Context 还可以优化？

因为 Research 层已经拿到了结构化信息。

但 Planner 只拿：

```text
数量 + 少量名称
```

应该改成：

```text
经过裁剪的 Candidate Objects
```

比如：

```text
ID
Name
Location
Category
Ticket
Rating
Opening Hours
```

这就是 Context Engineering。

---

# 七十一、如果上下文太长怎么办？

不能全部塞给 Planner。

可以：

```text
Retrieve
Filter
Rank
Compress
```

例如 100 个 POI：

先选：

```text
Top 15
```

Planner 再从 Top 15 中做组合。

也可以按：

```text
区域
类型
用户偏好
```

先做 Candidate Generation。

---

# 七十二、Agent 和传统后端最大的区别是什么？

非常适合你的回答：

传统后端：

```text
Input
 ↓
if/else
 ↓
Service
 ↓
Deterministic Output
```

Agent：

```text
Input
 ↓
Model Decision
 ↓
Dynamic Tool
 ↓
External Observation
 ↓
Next Decision
```

它带来了：

```text
灵活性
```

也带来：

```text
不确定性
```

所以 Agent 工程真正重要的是：

> 怎么把 LLM 的不确定性放进传统软件工程的确定性边界里。

这句话很适合你。

---

# 七十三、Java 后端经验对 Agent 有什么帮助？

推荐回答：

我觉得 Agent 开发不是完全新的软件工程体系。

以前 Java 后端解决：

```text
领域建模
状态流转
接口
权限
缓存
第三方服务
可靠性
```

现在 Agent 系统仍然要解决这些。

只是原来的：

```text
Service Orchestration
```

部分变成：

```text
Agent Workflow
```

原来的：

```text
第三方 SDK
```

可能变成：

```text
Agent Tool / MCP
```

原来的：

```text
if/else 决策
```

某些模糊问题变成：

```text
LLM Decision
```

所以我的优势是：

> 不只是会调模型，而是知道怎么把 Agent 放进一个真实业务系统。

---

# 七十四、为什么从 Java 后端转 Agent？

建议形成固定答案：

我最开始主要做 Java 后端，所以对真实业务系统的状态、数据模型、接口设计和第三方系统集成比较熟悉。

后来随着大模型的发展，我发现很多过去非常难通过固定规则解决的问题，比如自然语言需求理解、多步骤信息获取和动态任务规划，可以交给 LLM + Agent。

所以我并不是完全放弃后端，而是把原有的软件工程能力迁移到 Agent 应用开发。

现在我的关注点主要是：

```text
LangGraph Workflow
Tool Calling
MCP
RAG
Memory
Evaluation
Agent Engineering
```

我希望做的是能够真正接业务系统的 Agent，而不只是聊天 Demo。

---

# 七十五、你如何理解 Vibe Coding？

如果面试官提：

不要回答：

> 以后不用会代码了。

推荐：

我认为 AI Coding 大幅降低了实现成本，但并没有降低对工程判断的要求。

现在真正重要的是：

```text
问题拆解
Architecture
Context
Validation
Debugging
Evaluation
```

AI 可以快速生成代码，但：

```text
该不该这么设计
边界条件是什么
数据是否可信
失败如何恢复
```

还是需要开发者决定。

---

# 七十六、如果面试官问：项目是不是 AI 写的？

不要慌。

回答：

开发过程中我会使用 AI Coding 提高开发效率，但项目架构、模块拆分、Agent Workflow、问题定位和最终代码验收是我负责的。

例如项目最初 Research Node 是串行的，后来根据任务之间的数据依赖关系，我把它重新设计成了三路并行 + Join，同时增加了 State Reducer 解决并行写状态的问题。

我认为现在区分工程师能力的不是有没有用 AI 写代码，而是：

> 代码出现问题以后，能不能解释、修改、验证以及继续演进系统。

然后面试官大概率会开始问源码。

前面这份资料就是为了让你扛住这里。

---

# 七十七、一个高级面试官可能问：这三个 Research Agent 真的需要 LLM 吗？

最佳回答：

不一定。

这个项目当前更多是：

```text
Agent Architecture Exploration
```

如果业务流程固定，我反而会进一步去 Agent 化。

例如：

```text
Weather
```

直接调用 Tool。

POI Search：

如果 Query 需要从复杂自然语言生成：

```text
LLM Query Rewrite
      ↓
Search Tool
```

Planner：

由于需要综合：

```text
用户模糊偏好
天气
预算
景点
```

更适合保留 LLM。

我的原则是：

> 能 deterministic 就 deterministic，只在真正需要语言推理和动态决策的位置用 Agent。

---

# 七十八、Agent 与 Workflow 怎么选？

Workflow：

适合：

```text
明确步骤
强约束
需要稳定执行
```

Agent：

适合：

```text
开放任务
动态选择工具
路径无法提前确定
```

生产系统往往是：

```text
Workflow outside
Agent inside
```

你的项目正好可以这样解释。

---

# 七十九、什么时候使用 Multi-Agent？

适合：

```text
职责明显不同
需要不同 Tool
需要不同 Prompt
存在并行任务
需要权限隔离
上下文需要隔离
```

不适合：

```text
任务很简单
所有 Agent 都干一样的事
只是为了“高级”
```

Multi-Agent 有成本：

```text
Latency
Token
Debug Difficulty
Coordination Complexity
```

---

# 八十、如果让你重新做这个项目，你还会用 4 个 Agent 吗？

很优秀的回答是：

不会完全照搬。

我可能会调整为：

```text
Query Understanding Agent

        ↓

┌─────────────┬─────────────┬─────────────┐
POI Tool      Weather Tool   Hotel Tool
Direct        Direct         Direct

        ↓

Candidate Normalizer

        ↓

Planner Agent

        ↓

Constraint Engine
```

也就是说：

研究层不一定全部需要 Agent。

这是从“会 Agent”到“会设计 Agent 系统”的区别。

---

# 八十一、如果酒店 Tool 超时怎么办？

Production Answer：

```text
Timeout
 ↓
Retry with exponential backoff
 ↓
Circuit Breaker
 ↓
Fallback / Partial Planning
```

同时记录：

```text
Tool Latency
Tool Failure Rate
```

不要无限重试。

---

# 八十二、什么是幂等性？Agent 为什么需要？

例如 Agent 调用：

```text
send_email
pay_order
create_ticket
```

如果 Model Retry：

可能重复执行。

所以 Side Effect Tool 需要：

```text
idempotency_key
```

以及：

```text
business transaction
```

避免：

```text
重复付款
重复发邮件
重复创建订单
```

---

# 八十三、Tool 分为哪两类？

你可以自己分类：

### Read Tool

```text
Search
Weather
Database Query
```

风险较低。

### Write / Side-effect Tool

```text
Send Email
Delete
Payment
Create Order
Deploy
```

高风险。

高风险 Tool 应加入：

```text
Authorization
Confirmation
Audit
HITL
```

---

# 八十四、如果要求设计一个企业级 Agent，你首先考虑什么？

不要第一句就说 LangGraph。

应该先问业务：

```text
目标是什么？
输入是什么？
允许什么 Tool？
失败代价？
是否允许自动执行？
数据从哪来？
怎么判断成功？
```

然后才选技术。

一个好的流程：

```text
Business Goal
↓
Task Decomposition
↓
Deterministic vs Agent
↓
Tool Boundary
↓
State
↓
Workflow
↓
Memory
↓
Guardrail
↓
Evaluation
↓
Observability
```

---

# 八十五、这个项目的最大亮点怎么总结？

如果只能讲三个：

## 亮点一

**LangGraph 并行 Multi-Agent Workflow**

从：

```text
串行
```

重构为：

```text
Fan-out + Join
```

并处理共享 State。

## 亮点二

**MCP Tool Integration**

将实时外部数据能力接入 Agent。

## 亮点三

**LLM + Deterministic Algorithm**

不是让 LLM 负责所有逻辑。

---

# 八十六、项目最大的不足怎么总结？

主动说三个即可：

## 1. Planner Grounding

Research Result 传递不完整。

## 2. Async Architecture

当前 HTTP async，但 Graph 主链仍 sync。

## 3. Production Engineering

还缺：

```text
Checkpoint
Memory
Eval
Tracing
Tests
Real Routing
```

主动承认这三个不会减分。

反而说明你懂项目边界。

---

# 八十七、面试官问：为什么没有数据库？

回答：

当前版本定位是旅行规划 Agent Demo，TripPlan 直接在请求生命周期中生成和返回，没有实现用户体系和持久化。

如果产品化：

至少增加：

```text
User
Trip
TripVersion
Preference
AgentRun
ToolCall
```

其中：

```text
Trip / Version → relational database

Short-term agent checkpoint → LangGraph checkpointer

Long-term user preference → memory/profile store
```

---

# 八十八、怎么支持行程版本？

数据库：

```text
trip
trip_version
```

例如：

```text
Trip 1001

Version 1 原始
Version 2 雨天
Version 3 低预算
```

每次修改：

```text
不直接覆盖
```

而是创建：

```text
New Version
```

这样支持：

```text
Diff
Rollback
Audit
```

---

# 八十九、怎么实现用户偏好 Memory？

例如用户说：

```text
以后旅行不要安排爬山。
```

首先判断：

这是否属于：

```text
long-term preference
```

如果是：

```text
User Profile Store
```

保存：

```json
{
  "avoid": ["爬山"],
  "preferred": ["博物馆"]
}
```

新 Trip：

```text
Request
+
Profile
↓
Planner Context
```

而不是把用户所有历史聊天都无限塞给模型。

---

# 九十、怎么处理 Memory 冲突？

旧：

```text
喜欢经济型酒店
```

新：

```text
以后想住五星酒店
```

不能简单 append。

需要：

```text
Memory Update
```

可以：

```text
latest wins
```

也可以给：

```text
timestamp
confidence
source
```

并区分：

```text
long-term preference
temporary trip preference
```

---

# 九十一、系统如何保证旅行计划一定满足规则？

不要依赖 Prompt。

例如规则：

```text
每天最多 3 景点
```

应该：

```text
Planner
 ↓
Validator
 ↓
Constraint Check
```

如果：

```text
len(attractions)>3
```

就：

```text
Repair
```

这叫：

> Generate → Validate → Repair。

---

# 九十二、Validator 可以检查什么？

```text
日期连续
每天景点数量
酒店存在
经纬度范围
景点城市
重复景点
预算
天气冲突
时间冲突
开放时间
交通距离
```

---

# 九十三、怎么验证经纬度真实？

不要让 Planner 自己生成。

应该：

```text
Tool 返回 POI
    ↓
POI ID
    ↓
Backend 保存 Location
```

Planner 只能：

```text
select POI ID
```

这样从数据结构上杜绝模型生成坐标。

---

# 九十四、为什么最终 Plan 也最好不要全部让 LLM 构造？

因为：

```text
LLM 擅长“选择”
不擅长“数据库实体一致性”
```

所以可以：

Planner 输出：

```json
{
  "day1": ["poi_101", "poi_205"]
}
```

后端组装：

```text
POI 101
POI 205
酒店
天气
路线
```

最终 JSON。

这样：

```text
事实字段 → backend
决策字段 → LLM
```

这是一条非常重要的 Agent 工程原则。

---

# 九十五、系统设计题：生产级 Travel Agent

可以画：

```text
                  Client
                    │
                 Gateway
                    │
               Trip Service
                    │
              LangGraph Runtime
                    │
         ┌──────────┴───────────┐
         │                      │
     User Memory              Planner
         │                      │
         ▼                      ▼
    Profile DB             Research Router
                           /      |       \
                          /       |        \
                       POI     Weather    Hotel
                        │        │          │
                    MCP/API   MCP/API    MCP/API
                          \      |       /
                           \     |      /
                          Candidate Store
                                │
                           Planner LLM
                                │
                         Structured Output
                                │
                         Constraint Engine
                         /       |       \
                    Route      Time      Budget
                       │
                 Real Map Routing
                       │
                     Eval
                       │
                Optional HITL
                       │
                   Persist
                       │
                     UI
```

横切能力：

```text
Tracing
Rate Limit
Security
Retry
Cache
Cost Control
Eval
```

---

# 九十六、HR 面：你在项目里最大的挑战？

推荐回答：

项目一开始我把景点、天气和酒店查询设计成串行执行，实现比较直接，但整体等待时间比较长。

后来分析发现三个任务只依赖用户原始 Request，并不存在相互依赖。

因此我重新设计 LangGraph 拓扑，把三个节点从串行改成 START 后并行执行，再通过 Join 汇总。

并行以后又遇到了多个 Node 写共享 State 的问题，所以进一步使用 Reducer 处理 messages 和 error 等状态的合并。

这件事让我比较深地理解到，Agent 项目不仅是 Prompt 和模型调用，本质上仍然是一个并发、状态和可靠性问题。

---

# 九十七、HR 面：你最满意的技术设计？

推荐回答：

我比较满意的是没有把旅行规划完全交给大模型。

像路线距离、预算、天气评分这种确定性逻辑，我仍然使用传统程序完成。

因为如果所有问题都交给 LLM，系统虽然开发很快，但结果会不稳定、不可重复，也难测试。

所以这个项目让我形成了一个比较明确的 Agent 开发理念：

> 让 LLM 负责模糊判断，让程序负责确定性约束。

---

# 九十八、HR 面：项目有什么做得不好的？

回答千万不要：

> 没什么问题。

回答：

现在我认为主要有三个地方需要继续改。

第一是 Planner Grounding，目前 Planner 接收到的 Research 信息还不够完整。

第二是 Async 架构，FastAPI 虽然是 async，但核心 Workflow 仍然使用同步 invoke。

第三是 Evaluation，目前更多依赖人工体验，还缺标准 Dataset 和自动化指标。

如果继续做，我会优先解决这三个问题，而不是继续堆更多功能。

---

# 九十九、HR 面：如果加入公司，你希望做什么？

推荐：

我比较希望做真正有业务闭环的 Agent 项目，不只是 Chatbot。

例如：

```text
企业知识 Agent
业务流程 Agent
数据分析 Agent
客服 Agent
运营 Agent
研发 Agent
```

我比较感兴趣的是：

> 怎么把 LLM 的推理能力和现有业务系统、数据库、API、权限体系结合起来。

---

# 一百、最后必须背熟的 15 句话

面试前反复背这些。

### 1

> 我的系统是外层 LangGraph Workflow + 内层 LangChain Agent 的组合。

### 2

> Multi-Agent 不是越多越好，职责明确、工具不同或可以并行时才值得拆。

### 3

> 三个 Research Agent 只依赖 TripRequest，因此可以并行执行。

### 4

> Reducer 解决的是多个节点更新同一个 State Key 时如何合并的问题。

### 5

> Join 是并行分支完成后的同步点。

### 6

> MCP 为 AI Application 和外部 Tool 提供标准化连接方式。

### 7

> Prompt 不能真正保证不幻觉，Grounding 和 Validation 才是关键。

### 8

> LLM 负责模糊决策，传统程序负责确定性逻辑。

### 9

> Haversine 是直线地理距离，不是真实道路距离。

### 10

> 最近邻是贪心近似，不保证全局最优。

### 11

> 当前 Planner Grounding 最大的问题是没有消费完整 Research Result。

### 12

> 当前 async FastAPI + sync Graph 是需要继续优化的一点。

### 13

> 当前用户调整是交互式 Re-planning，但还不是 LangGraph Interrupt 意义上的 HITL。

### 14

> 当前没有真正持久化 Memory / RAG / Eval，我会明确区分“已实现”和“准备升级”。

### 15

> 我的优势不是单纯会调模型，而是能够把 Agent 和真实业务系统结合起来。

---

# 附录 A：项目真实技术栈

## AI / Agent

```text
LangGraph 1.0.2
LangChain 1.2.0
langchain-openai
langchain-mcp-adapters
MCP
ChatOpenAI
```

## Backend

```text
Python
FastAPI
Pydantic v2
asyncio
nest_asyncio
HTTPX
```

## Tool

```text
AMap MCP Server
stdio Transport
High德地图
```

## Frontend

```text
Vue 3
TypeScript
Vite
Ant Design Vue
Axios
AMap JavaScript API
html2canvas
jsPDF
```

---

# 附录 B：项目中没有真正完成的能力

面试绝对不要主动吹成已经完成：

```text
RAG
Vector Database
持久化 Memory
LangGraph Checkpointer
真正 LangGraph Interrupt HITL
完善 LangSmith Evaluation
真实路网路线优化进入主 Workflow
生产级高可用
完整 Automated Test
CI/CD
数据库持久化
```

正确表达：

> 我理解这些技术，并且知道如果产品化应该在哪里加入，但当前项目版本没有全部实现。

---

# 附录 C：2026 年面试可额外了解的 LangGraph / MCP 方向

LangGraph 官方当前的 Persistence/Checkpointer 可以按 thread 保存 Graph State，用于短期记忆、HITL、容错恢复等场景。

Interrupt 可以在 Graph 执行过程中暂停执行，配合持久化等待外部输入，然后继续恢复 Workflow。

LangChain 当前的 Agent 已支持 Structured Output，因此项目里的手工 JSON 截取逻辑是一个非常明确的升级点。

MCP 官方协议仍在快速演进。2026 年 7 月发布的新一版规范进一步推进了 stateless protocol core，因此如果面试官专门问 MCP 最新发展，可以把“更利于可靠性和可扩展部署”作为一个额外了解点，但不要把这个最新规范说成你当前项目已经采用。

---

# 附录 D：面试准备优先级

如果时间不够，按以下顺序复习：

**第一优先级**

```text
项目架构
LangGraph
State
Reducer
并行
Join
Agent
Tool Calling
MCP
```

**第二优先级**

```text
Structured Output
Async
Error Handling
Grounding
Hallucination
HITL
Memory
RAG
```

**第三优先级**

```text
Evaluation
Observability
Agent Security
Prompt Injection
Scaling
Cost
System Design
```

最终目标不是把 100 个问题逐字背下来。

而是形成一个统一思维模型：

```text
业务问题
   ↓
哪些部分 deterministic？
   ↓
哪些部分需要 LLM？
   ↓
需要什么 Tools？
   ↓
State 怎么设计？
   ↓
Workflow 怎么编排？
   ↓
失败怎么办？
   ↓
如何 Grounding？
   ↓
如何 Validate？
   ↓
如何 Eval？
   ↓
如何上线？
```

如果你能按这个逻辑回答，绝大多数 Agent 应用开发岗位的项目面都不会只停留在“会不会 LangChain”这个层面。