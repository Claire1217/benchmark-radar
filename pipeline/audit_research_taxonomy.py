#!/usr/bin/env python3
"""Write a complete, reproducible record-level taxonomy audit, without assigning labels."""
import argparse
from collections import Counter
import json
from pathlib import Path


def audit(before, after, output):
    previous = {r['id']: r for r in before['records']}
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for record in after['records']:
        old = previous.get(record['id'], {})
        prior = set(old.get('researchDirections', []))
        current = set(record.get('researchDirections', []))
        rows.append({
            'id': record['id'], 'name': record['name'],
            'visible': record.get('displayEligible') is not False and record.get('evaluationMode') != 'viewpoint_probe',
            'before': sorted(prior), 'after': sorted(current),
            'added': sorted(current-prior), 'removed': sorted(prior-current),
            'description': record.get('description') or record.get('oneLine'),
            'source': record.get('links', {}).get('report'),
            'evidence': record.get('researchDirectionEvidence', {}),
            'facets': record.get('researchFacets', {}),
            'reviewFlags': record.get('researchClassification', {}).get('reviewFlags', []),
        })
    flags = Counter(flag for row in rows for flag in row['reviewFlags'])
    def counts(records):
        return Counter(d for r in records if r.get('displayEligible') is not False and r.get('evaluationMode') != 'viewpoint_probe' for d in r.get('researchDirections', []))
    summary = {
        'scope': 'All Library records, metadata and description evidence; not full-paper verification',
        'beforeVersion': before['manifest']['researchTaxonomy']['version'],
        'afterVersion': after['manifest']['researchTaxonomy']['version'],
        'recordsAudited': len(rows),
        'visibleRecords': sum(row['visible'] for row in rows),
        'recordsWithMembershipChanges': sum(bool(row['added'] or row['removed']) for row in rows),
        'unclassifiedBefore': sum(not r.get('researchDirections') for r in before['records']),
        'unclassifiedAfter': sum(not row['after'] for row in rows),
        'reviewFlags': dict(flags),
        'countsBefore': dict(counts(before['records'])), 'countsAfter': dict(counts(after['records'])),
    }
    (output/'records.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows))
    (output/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    lines = ['# 分类全库审查', '',
             f"审查 {len(rows)} 条记录；{summary['recordsWithMembershipChanges']} 条的类别成员关系发生变化。", '',
             '这是全库元数据与分类逻辑审查，不代表已逐篇阅读全文。自动规则的证据和待复核标记保存在 records.jsonl。', '',
             f"无受支持分类：{summary['unclassifiedBefore']} → {summary['unclassifiedAfter']}。未分类记录仍可搜索，不强制分入某类。", '',
             '## 类别计数（只计公开可见记录）', '', '| 类别 | 旧值 | 新值 |', '|---|---:|---:|']
    for d in after['manifest']['researchTaxonomy']['directions']:
        lines.append(f"| {d['name']} | {summary['countsBefore'].get(d['id'], '新增')} | {d['count']} |")
    lines += ['', '## 主题变更逐项证据', '']
    themes = {'ai-for-science', 'self-improvement-rsi'}
    for row in rows:
        if themes.intersection(row['added']+row['removed']):
            lines += [f"### {row['name']}", '', f"新增：{', '.join(row['added']) or '无'}；移除：{', '.join(row['removed']) or '无'}。", '', row['description'] or '描述不足', '']
            if row['source']:
                lines += [f"[来源]({row['source']})", '']
    (output/'report.md').write_text('\n'.join(lines)+'\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--before', required=True, type=Path)
    parser.add_argument('--after', default='data/library_index.json', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(json.loads(args.before.read_text()), json.loads(args.after.read_text()), args.output), indent=2))
