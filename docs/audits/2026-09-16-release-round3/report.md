# 发布日期核查：651条累计核实报告

已对651条全部补做名称＋任务描述检索，初始全量检索抓取911个不重复候选页面（后续定向核查证据另存）；**确认并补入637条，仍有14条未确认到月份。全量检索不等于全部核实完成。**

- 日期精度：{'day': 585, 'month': 52}。
- 其中 245 条是记录所指评测、版本或榜单的论文/公告日期（不等同于独立数据集发布），305 条是底层数据集日期。底层数据集日期在 Library 明确标注，不作为新 benchmark 发布计数；另有 87 条仅核实公开披露日期，同样不计入新发布。
- 未采用仓库创建时间、镜像上传时间、网页抓取时间、后续模型测试时间或同名但无关论文的日期。
- 月份证据不补造具体日。只有年份或没有可靠证据的记录继续保留缺失。

## 累计重要修复

| Benchmark | 已核实日期 | 证据 |
|---|---|---|
| Arena-Hard v2 | 2025-04-23 | [原始来源](https://github.com/lmarena/arena-hard-auto) |
| MMLU-redux-2.0 | 2024-11-07 | [原始来源](https://www.research.ed.ac.uk/en/datasets/mmlu-redux-20/) |
| OSWorld-Verified | 2025-07-28 | [原始来源](https://osworld-v1.xlang.ai/) |
| SWE-bench Multilingual | 2025-05-06 | [原始来源](https://kabirk.com/multilingual) |
| AA ITBench | 2026-05-27 | [原始来源](https://huggingface.co/blog/ibm-research/itbench-aa) |
| EMMA | 2025-01-09 | [原始来源](https://arxiv.org/abs/2501.05444) |
| CSimpleQA | 2024-11-11 | [原始来源](https://arxiv.org/abs/2411.07140) |
| PerceptionTest | 2022-10-12 | [原始来源](https://deepmind.google/blog/measuring-perception-in-ai-models/) |
| ActivityNet | 2015-06 | [原始来源](https://openaccess.thecvf.com/content_cvpr_2015/html/Heilbron_ActivityNet_A_Large-Scale_2015_CVPR_paper.html) |

## 为什么还有未确认项

剩余项分流如下。除上面已接受的证据外，这些是后续核查队列，不代表已证实不能找到日期。

| 下一步 | 条数 |
|---|---|
| 身份或版本冲突，已记录具体原因 | 14 |

### 已发现的具体内容问题

- **KernelBench**：Catalog describes a six-task hardware-roofline benchmark; retrieved ScalingIntelligence paper describes the original multi-level PyTorch/CUDA suite. Resolve exact version/owner before assigning a date.
- **CL-bench**：Catalog describes coding/agentic tasks, but the original CL-bench paper is about context learning. Confirm identity and repair description before accepting the date.
- **UserBench**：Catalog describes developer next-message prediction; retrieved UserBench paper describes user-centric interactive agents. Same name is insufficient.
- **Code Migration**：Multiple distinct benchmarks (CODEMENV, MigrationBench, JMigBench) match this generic task label. Need original benchmark identifier.
- **AA-Index**：Search hits for geomagnetic aa index are unrelated to Artificial Analysis. Composite-index version also unspecified.
- **WebArena-Verified**：Round62 resolved: original PR1 merged December5,2025 with actual812task data and258Hard IDs. Distinguish this public artifact from collaborator preview, planned December4 launch and later PyPI packaging.

## 对网站的影响

| 项目 | 更新前 | 更新后 |
|---|---:|---:|
| Library 日期精度：day | 2218 | 2803 |
| Library 日期精度：month | 1 | 53 |
| Library 日期精度：year | 5 | 1 |
| Library 日期精度：unknown | 646 | 13 |
| Trends 最近1个月发布 family 数 | 350 | 375 |
| Trends 最近3个月发布 family 数 | 1133 | 1205 |
| Trends 最近6个月发布 family 数 | 1590 | 1689 |
| Trends 最近12个月发布 family 数 | 1634 | 1754 |

- 统一更新日期证据表，再生成 Library 与 Trends；没有为单个页面维护另一份日期。
- 分类仍为 research-topics-v4；GitHub star 历史与 attention 算法未改动。
- 历史日期补齐会改变历史发布计数。只有完整到日且符合统计资格的记录进入日界限窗口；月份日期与底层数据集引用不会冒充独立新发布。
- Radar 的近期发现/更新流不会把这些补齐历史日期的记录伪装成今日新发布。
- 本轮仅生成本地数据和静态站点，未推送或部署。

## 文件

- [逐条核查页面](review.html)：可搜索651条，筛选已确认和待核实，并打开证据来源。
- [全部651条](all-651.json)、[已接受证据](reviewed.json)、[剩余清单](remaining.json)、[统计收据](receipt.json)。
- 检索与页面缓存：工作区 outputs/release-date-round3/。

## 后续补全方法

1. 先修复身份冲突：为每条记录确认 canonical benchmark、版本、所有者和原始网址。不要继续仅靠名称找日期。
2. 对同一数据集的分项/指标/供应商镜像建立共同来源；底层数据集日期与该版本发布日期分别保存。
3. 对内部评测另记首次公开报告日期；不要把报告日期伪称数据集发布。
4. 逐条补版本公告、作者项目页或论文v1；有年月只保存年月。保留失败原因以便下一轮定向重试。
