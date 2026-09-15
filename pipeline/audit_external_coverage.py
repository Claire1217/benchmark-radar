#!/usr/bin/env python3
"""Read-only anchor coverage and identity-risk audit. Never assigns or merges records."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

def norm(value):
    return re.sub(r'[^\w]+', '', value.casefold())

def visible(row):
    return row.get('displayEligible') is not False and row.get('evaluationMode') != 'viewpoint_probe'

def run(index_path, anchors_path, output):
    raw=index_path.read_bytes(); data=json.loads(raw)
    records=data['records']; public=[r for r in records if visible(r)]
    anchors=json.loads(anchors_path.read_text())
    output.mkdir(parents=True,exist_ok=True)
    results=[]
    for a in anchors:
        names={norm(n) for n in [a['name']]+a['aliases']}
        exact=[]; related=[]
        paper=re.search(r'arxiv.org/abs/(\d{4}\.\d+)',a['sourceUrl'])
        for r in records:
            labels=[r['name']]+[v for v in r.get('aliases',[]) if isinstance(v,str)]
            links=' '.join(str(v or '') for v in r.get('links',{}).values())
            match=any(norm(n) in names for n in labels)
            if paper and paper[1] in links: match=True
            if match: exact.append(r)
            elif any(len(n)>3 and n in norm(r['name']) for n in names): related.append(r)
        eligible=[r for r in exact if visible(r)]
        status=('identity-review' if a.get('identityIssue') and exact else
                'no-exact-match' if not exact else
                'hidden-only' if not eligible else
                'direction-gap' if not any(set(a['directions'])<=set(r.get('researchDirections',[])) for r in eligible) else
                'anchor-covered')
        results.append({**a,'status':status,'matches':[{'id':r['id'],'name':r['name'],'visible':visible(r),'directions':r.get('researchDirections',[]),'description':r.get('description'),'links':r.get('links')} for r in exact],
                        'relatedCandidates':[{'id':r['id'],'name':r['name']} for r in related]})
    descriptions=defaultdict(list)
    for r in public:
        d=norm(r.get('description') or '')
        if len(d)>90: descriptions[d].append({'id':r['id'],'name':r['name'],'familyId':r.get('familyId')})
    duplicates=[group for group in descriptions.values() if len(group)>1]
    categories=[]
    for d in data['manifest']['researchTaxonomy']['directions']:
        members=[r for r in public if d['id'] in r.get('researchDirections',[])]
        tag_only=sum(r.get('researchDirectionEvidence',{}).get(d['id'],{}).get('basis')=='tag' for r in members)
        refs=[r for r in results if d['id'] in r['directions']]
        categories.append({'id':d['id'],'name':d['name'],'visibleRecords':len(members),'tagOnlyMemberships':tag_only,
          'unverifiedCatalogRecords':sum(r.get('dataStatus')=='catalog-listed-unverified' for r in members),
          'anchors':len(refs),'anchorStatuses':dict(Counter(r['status'] for r in refs))})
    summary={'snapshotSHA256':hashlib.sha256(raw).hexdigest(),'records':len(records),'visibleRecords':len(public),
      'visibleUnclassified':sum(not r.get('researchDirections') for r in public),'categories':len(categories),
      'anchors':len(results),'anchorStatuses':dict(Counter(r['status'] for r in results)),
      'sameDescriptionCandidateGroups':len(duplicates),
      'limitations':'Purposive primary-source anchor sample, not exhaustive coverage or an accuracy estimate. Name matches require identity review; same descriptions do not prove duplicates. No classifications changed.'}
    for name,obj in [('summary',summary),('categories',categories),('anchor-results',results),('duplicate-candidates',duplicates)]:
        (output/(name+'.json')).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    labels={'identity-review':'身份/版本待核对','no-exact-match':'未匹配到准确条目','hidden-only':'仅隐藏条目','direction-gap':'已收录但目标分类缺失','anchor-covered':'该参照条目已覆盖'}
    lines=['# 全类别外部参照审核（2026-09-15）','',
      f"范围：{len(records)} 条记录，{len(public)} 条公开可见；{len(categories)} 个类别逐类检查，{len(results)} 个有一手来源的参照条目。",'',
      '这是定向抽样，不是领域全量数据集清单，也不能据此计算全站准确率。类别内记录数不是独立数据集家族数。当前仅生成审查结果，尚未改写线上标签或合并实体。','',
      '## 核心结论','',
      'GUI 的五条结果混合了评测层级。更广泛的漏收录、描述不足、同名异物与版本设置重复计数，说明分类与身份数据需要一起修正。', '',
      f"公开记录中 {summary['visibleUnclassified']} 条没有研究类别；发现 {len(duplicates)} 组长描述完全相同的候选，均须核对，不能自动合并。",'',
      '## 29 类结构检查','',
      '“仅标签证据”按当前这个类别的成员证据计算；不是对条目真假的判定。“外部参照通过”只证明所选条目能在该类找到。','',
      '| 类别 | 可见条目 | 仅标签证据 | 未核验目录条目 | 外部参照结果 |','|---|---:|---:|---:|---|']
    for c in categories:
        text='；'.join(labels[k]+': '+str(v) for k,v in c['anchorStatuses'].items())
        lines.append(f"| {c['name']} | {c['visibleRecords']} | {c['tagOnlyMemberships']} | {c['unverifiedCatalogRecords']} | {text} |")
    lines+=['','## 外部参照逐项比对','',
      '未匹配项已比较名称、已登记别名，以及来源为 arXiv 时的论文 ID；派生版本仅列为候选，不当作原版覆盖。仍可能存在尚未登记的别名。','',
      '| 外部条目 | 评测层级 | 结论 | 本库准确匹配 / 相关候选 | 一手来源与依据 |','|---|---|---|---|---|']
    for r in results:
        matches=', '.join(v['name'] for v in r['matches']) or '无'
        related=', '.join(v['name'] for v in r['relatedCandidates']) or '无'
        lines.append(f"| {r['name']} | {r['entityRole']} | {labels[r['status']]} | 匹配：{matches}；候选：{related} | [来源]({r['sourceUrl']})：{r['evidenceSummary']} |")
    lines+=['','## 现有 GUI 五条的逐项判断','',
      '| 当前条目 | 审核结论 |', '|---|---|',
      '| ScreenSpot | 定位基准；原版/v2 的具体身份需补足。 |',
      '| ScreenSpot Pro | 独立专业 GUI grounding 基准。 |',
      '| VisualWebBench | 综合套件中有明确 grounding 轨道，保留但注明层级。 |',
      '| MobileWorld | [官方仓库](https://github.com/Tongyi-MAI/MobileWorld)评估完整移动任务，不能仅由简介提到 grounding 就计为独立定位测试。 |',
      '| OSWorld Screenshot-only | [官方项目](https://osworld-v1.xlang.ai/)的截图观察设置；应归属交互基准的设置关系，不能仅凭使用截图判为定位评测。 |', '',
      '本轮 GUI 参照额外核对到 GroundUI-1K、OSWorld-G、UI-Vision、UI-I2E-Bench、VenusBench-GD 和 ScreenSpot-v2；这仍不是完整领域清单。', '',
      '后续扩展队列：已发现 [GUI-Primitives](https://arxiv.org/abs/2608.21832)；FineState-Bench 存在 [2025 论文](https://arxiv.org/abs/2508.09241)与 [2026 论文](https://arxiv.org/abs/2604.27974)，必须先查明关系，未计入本轮 37 项统计。', '']
    lines+=['','## 需要区分的实体关系','',
      '- alias：同一对象的不同名称，例如 MMMU val / validation 的现有描述完全相同，需用划分与协议核实。',
      '- version / subset / split：ScreenSpot-v2、GroundUI-1K、MMMU validation 保留可搜索关系，但不能各自冒充独立家族。',
      '- track：UI-Vision 和 VisualWebBench 含 grounding 评测；显示套件并注明轨道，不凭任务数量增加家族数。',
      '- setting：OSWorld Screenshot-only、Video-MME 有无字幕属于观察或评测设置。',
      '- adapter：ScienceAgentBench 的 Harbor 包属于运行适配，适配说明不能替代任务说明。',
      '- homonym：AIR-Bench 音频与 AIR-BENCH 安全同名不同研究，应按论文和发布者区分。','',
      '## 同描述候选（不自动合并）','']
    for g in duplicates: lines.append('- '+' / '.join(r['name'] for r in g))
    lines+=['','## 统一修正方案与验收','',
      '1. 先整理身份：为经核实条目建立 canonical benchmark、版本/划分/轨道/设置/适配关系；来源不确定的保持待核对。不能仅靠名称去重，也不能把现有随机 familyId 当成已审定家族。',
      '2. 再补任务证据：保存官方任务、输入输出、评分对象、来源与审核日期；把平台安装说明放到适配信息。',
      '3. 再统一分类：主要评测目标与仅涉及能力分开；GUI 需要明确定位输出/评分依据，网页检索不能仅因 navigation 归为电脑操作。',
      '4. 分类计数先明确表示“匹配条目”；只有完成身份归并后才显示“基准家族数”，展开版本和设置不增加家族数。',
      f'5. 同时补覆盖：{len(results)} 项中未匹配的官方基准建立收录队列；验证来源、实体关系与可见性后再导入，不能把模型/训练方法误收为新基准。',
      '6. 验收包含正例、相邻类反例、同名异物、版本/设置不重复计数，以及每个参照条目的检索入口。未解决事项须保留明细，不能因内部单测通过就宣称领域完整。','',
      '## 可复现性','',f"索引 SHA-256：`{summary['snapshotSHA256']}`。",'',
      '`anchors.json` 为人工审核的一手来源参照；`anchor-results.json`、`categories.json`、`duplicate-candidates.json` 为此快照的计算结果。审查脚本不修改网站数据。']
    (output/'report.md').write_text('\n'.join(lines)+'\n')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--index',type=Path,default=Path('data/library_index.json'));p.add_argument('--anchors',type=Path,default=Path('docs/audits/coverage-20260915/anchors.json'));p.add_argument('--output',type=Path,default=Path('docs/audits/coverage-20260915'))
    a=p.parse_args();print(json.dumps(run(a.index,a.anchors,a.output),ensure_ascii=False,indent=2))
