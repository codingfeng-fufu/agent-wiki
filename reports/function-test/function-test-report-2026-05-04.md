# 全功能测试报告

生成时间：2026-05-04 15:38 CST

## 一句话结论

本次完整离线功能测试通过。项目当前 wiki 有 48 个页面、8 个 source；pytest 全量通过，health 无 issue，CLI/daemon/doctor/release smoke 通过，Python search benchmark 达到 release gate。

## 终端截图

![Full function test terminal](function-test-terminal.png)

原始终端 transcript：[`function-test-transcript.txt`](function-test-transcript.txt)

## 测试范围

| 模块 | 覆盖内容 | 结果 |
| --- | --- | --- |
| Tooling | `llmw --version`、Python 版本 | 通过 |
| Unit / integration tests | 全量 pytest | 134 passed in 41.16s |
| Offline health | `llmw health check --root .` | 通过，issues=0 |
| CLI smoke | context、doctor、next、plan、apply、maintain、source、ingest、search、MCP、query、agent、release、package、install-agent 等 help 路径 | 通过 |
| Search daemon | start/status/query/stop | 通过 |
| Doctor smoke | `llmw doctor --no-codex --json` | 通过 |
| Release command smoke | `llmw release check --no-tests --no-benchmark --no-sdist --no-codex --json` | 通过 |
| Search benchmark | 102 个 benchmark query，provider=python，top_k=5 | 通过 |
| Live LLM smoke | `llmw llm check`、`llmw query`、`llmw health audit` | 通过 |
| Deep qmd benchmark | qmd/llmw deep benchmark | 未跑，属于可选向量检索外部依赖项 |

## Search Benchmark 摘要

```json
{
  "queries": 102,
  "top_k": 5,
  "precision_at_k": 0.21568627450980357,
  "precision_at_k_ceiling": 0.23529411764705857,
  "recall_at_k": 0.9493464052287582,
  "f1_at_k": 0.34232026143790806,
  "hit_rate_at_k": 0.9705882352941176,
  "mrr_at_k": 0.8977124183006537,
  "by_category": {
    "analysis-paraphrase": {
      "queries": 2,
      "precision_at_k": 0.2,
      "recall_at_k": 1.0,
      "f1_at_k": 0.33333333333333337,
      "hit_rate_at_k": 1.0,
      "mrr_at_k": 0.6
    },
    "analysis-title": {
      "queries": 2,
      "precision_at_k": 0.2,
      "recall_at_k": 1.0,
      "f1_at_k": 0.33333333333333337,
      "hit_rate_at_k": 1.0,
      "mrr_at_k": 1.0
    },
    "concept-paraphrase": {
      "queries": 37,
      "precision_at_k": 0.18378378378378388,
      "recall_at_k": 0.918918918918919,
      "f1_at_k": 0.3063063063063064,
      "hit_rate_at_k": 0.918918918918919,
      "mrr_at_k": 0.8207207207207207
    },
    "concept-title": {
      "queries": 37,
      "precision_at_k": 0.2000000000000001,
      "recall_at_k": 1.0,
      "f1_at_k": 0.3333333333333334,
      "hit_rate_at_k": 1.0,
      "mrr_at_k": 1.0
    },
    "cross-cutting": {
      "queries": 8,
      "precision_at_k": 0.475,
      "recall_at_k": 0.7291666666666666,
      "f1_at_k": 0.5729166666666667,
      "hit_rate_at_k": 1.0,
      "mrr_at_k": 0.9375
    },
    "source-paraphrase": {
      "queries": 8,
      "precision_at_k": 0.19999999999999998,
      "recall_at_k": 1.0,
      "f1_at_k": 0.3333333333333334,
      "hit_rate_at_k": 1.0,
      "mrr_at_k": 0.84375
    },
    "source-title": {
      "queries": 8,
      "precision_at_k": 0.19999999999999998,
      "recall_at_k": 1.0,
      "f1_at_k": 0.3333333333333334,
      "hit_rate_at_k": 1.0,
      "mrr_at_k": 0.84375
    }
  }
}
```

关键指标：

- queries: 102
- precision_at_k: 0.2157
- recall_at_k: 0.9493
- f1_at_k: 0.3423
- hit_rate_at_k: 0.9706
- mrr_at_k: 0.8977

## Health 摘要

```json
{
  "ok": true,
  "issues": []
}
```

## 外部依赖说明

这份报告覆盖了可复现的离线功能测试，并额外打开了真实 LLM smoke。真实 LLM 调用使用当前默认 provider `qwen_plus`，报告和 transcript 不记录任何 API key。`RUN_DEEP_SEARCH_BENCHMARK=0` 是有意设置：

- deep qmd benchmark 依赖可选向量检索后端。
- LLM/query/ingest 的核心路径已由单元测试、mock provider QA 报告和 ingest 用户体验模拟覆盖。

## 产物

- 截图：[`function-test-terminal.png`](function-test-terminal.png)
- Transcript：[`function-test-transcript.txt`](function-test-transcript.txt)
- HTML 渲染源：[`function-test-terminal.html`](function-test-terminal.html)
- 复现脚本：[`run_function_test_report.py`](run_function_test_report.py)
