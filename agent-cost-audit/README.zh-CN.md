# 编码 Agent 的一次任务，应该怎么算成本？

本文由 Kunavo 团队维护，代码和文字使用了 AI 辅助，并通过本地测试核对。全部输入为人工构造的示例，不含客户数据。脚本离线运行，不需要 API Key，也不会产生调用费用。

在编码 Agent 或定时助手里，一个任务可能包含多轮模型请求、工具结果、返修和重试。把总费用除以请求数，得到的是每次请求成本；如果要评估一项工作做完需要多少钱，还要记录最终是否验收。

## 先跑这个例子

环境：Python 3.9 及以上，无第三方依赖。在仓库根目录运行：

```sh
python3 agent-cost-audit/audit.py agent-cost-audit/example.json
python3 -m unittest discover -s agent-cost-audit -p 'test_*.py'
```

示例中有两个工作任务：A 发起两次请求后验收通过；B 发起一次请求但未通过。另有一个健康检查。

| 项目 | 示例结果 |
|---|---:|
| 工作请求数 | 3 |
| 验收通过的任务数 | 1 |
| 工作请求估算费用 | $0.288 |
| 健康检查估算费用 | $0.000039 |
| 每个验收任务的工作成本 | $0.288 |

这些价格是为了演示计算而设定的假设值，不是 Kunavo 或模型厂商的当前报价。按三次请求平均是 $0.096，但失败任务和返修也花了钱。若本轮没有任何任务通过，脚本返回 `null`，不能写成“每项任务零成本”。

“通过”由你定义：测试通过、人工审核通过，或者满足明确的交付标准。API 返回 200 只能说明接口层面的结果，不能自动证明代码正确。

## 缓存读、写与普通输入分开

脚本要求每个请求提供四个互不重叠的 token 数：

```text
uncached_input：普通输入
cache_write：写入缓存的输入
cache_read：从缓存读取的输入
output：输出
```

Anthropic Messages 的普通 `input_tokens` 与缓存读、写字段分开；OpenAI 风格的总输入字段则通常包含详情中的缓存部分。要按实际端点文档归一化，尤其要检查网关是否已经转换过字段，避免重复相加或扣减。

```text
单次请求费用 = (普通输入 × 普通输入单价
              + 缓存写入 × 写入单价
              + 缓存读取 × 读取单价
              + 输出 × 输出单价) / 1,000,000
```

这里单价统一为美元／百万 token。跨请求的缓存读占比应按 token 数加权：总缓存读取 ÷ 总输入。示例任务 A 的占比为 45%，不能只看第二次请求的 90%。

## 用到自己的工作流时

保留同一个任务 ID，把返修、有限重试和最终未完成的工作都纳入费用。健康检查单独统计，并仍计入总成本。流式响应采用一次请求的最终 usage，不能把多条累计 usage 事件重复求和。

缺失 usage 不等于零费用：超时后先对照账单，再填入已确认的数据。脚本会拒绝缺失、负数、小数或布尔值 token，以及重复任务 ID 和非法价格。

每个文件只支持一组费率。跨模型、不同缓存写入 TTL、阶梯价格分别计算，再合并费用；跨模型的同一任务只计一次验收，不能把各文件的分母简单相加。工具费、图片音乐视频、主机费用等另列，这个脚本不计算它们。

可以先拿一个典型编码任务和一个失败任务做对照，再决定模型选择、上下文截断与重试上限。不需要先跑大规模实验。

## 参考

字段语义核对日期：2026-10-07。

- [Anthropic 缓存与 usage 字段](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [OpenAI 缓存与 usage 详情](https://developers.openai.com/api/docs/guides/prompt-caching)
- 使用 Kunavo 的读者可参考 [Cline 配置](https://kunavo.com/docs/integrations/cline?utm_source=github&utm_medium=developer_content&utm_campaign=kn_202610_p09)和 [OpenCode 配置](https://kunavo.com/docs/integrations/opencode?utm_source=github&utm_medium=developer_content&utm_campaign=kn_202610_p09)。离线脚本本身可用于其他提供方。
