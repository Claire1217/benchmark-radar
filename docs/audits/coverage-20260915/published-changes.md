# 本次发布的修正

- 新增 15 个一手来源核实的基准/明确版本，包括音频 AIR-Bench（与安全 AIR-BENCH 分开）。
- 明确 GUI 评测对象：定位基准、含 grounding 轨道的套件、交互任务和观察设置。
- 补齐 GroundUI-1K、OSWorld-G、SWE-bench、BrowseComp、ScienceAgentBench 的任务证据与分类。
- 合并 MMMU val / validation；保留验证集与母基准的关系。
- 为 ScreenSpot-v2、MMMU validation、DocVQA test、OSWorld Screenshot-only 保存父基准关系；页面标注条目层级。
- 数量标为 entries，仍计可搜索条目，不宣称全部是独立数据集家族。
- KernelBench 身份保留待审核提示；其他同描述候选没有足够证据，未自动合并。
- 原始 report.md 与 anchor-results.json 是修正前快照，保留供复核，不代表修改后状态。

生成后：2869 条记录，2667 条公开可见；GUI Grounding 为 9 条，包括明确版本与综合套件轨道，不是 9 个独立家族。
