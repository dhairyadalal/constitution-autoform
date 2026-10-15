"""Render the paper narrative from the frozen run without replacing its explorer report."""
from __future__ import annotations

import html
import json
import re
import sys
import tempfile
from pathlib import Path

from build_preliminary import build
from autoform.paths import ROOT


def render_paper(run_dir: Path, output_path: Path) -> None:
    template_path = Path(__file__).with_name('paper-template.html')
    # Reuse the original hash checks and saved-evidence collection. Only presentation differs.
    with tempfile.TemporaryDirectory(prefix='constitution-paper-') as temp:
        intermediate = Path(temp) / 'report.html'
        build(run_dir, intermediate, template_path)
        rendered = intermediate.read_text(encoding='utf-8')
    match = re.search(r'<script type="application/json" id="evidence-data">(.*?)</script>', rendered, re.S)
    if match is None:
        raise ValueError('Missing embedded evidence')
    data = json.loads(match.group(1))
    valid = [c for c in data['candidates'].values() if c['validity']['schema'] == 'valid']
    inc = [c for c in valid if c['document'].endswith('-inconsistent')]
    case_counts = {}
    agreed = total = 0
    for c in valid:
        for case, phases in c['diagnostics'].items():
            for phase, actions in phases.items():
                for action, outcome in actions.items():
                    total += 1
                    agreed += outcome['status'] == data['references'][c['document']][case][phase][action]['status']
    for c in inc:
        status = c['diagnostics']['C05']['initial']['send_redacted_alert']['status']
        case_counts[status] = case_counts.get(status, 0) + 1
    # Guard the narrative's descriptive values against accidental use with another run.
    expected = {'conflicting':16, 'required':10, 'pending':4, 'unknown':1}
    if case_counts != expected or (agreed,total) != (720,945):
        raise ValueError('Case outcomes differ from the paper narrative')
    if data['stats']['review_verdicts'] != {'supported':137,'unsupported':12,'uncertain':102,'disputed_or_incomplete':261}:
        raise ValueError('Review outcomes differ from the paper narrative')
    for mode, size in [('direct',15),('structured',16)]:
        group = [c for c in inc if c['mode']==mode]
        if len(group)!=size or sum(bool(c['coherence']['conflicts']) for c in group)!=8:
            raise ValueError('Prompt comparison differs from the paper narrative')
    bars=[]
    for label, key, color in [('Unanimously supported','supported','#176b62'),('Unanimously unsupported','unsupported','#a34b37'),('Unanimously uncertain','uncertain','#b48835'),('Mixed judgments','disputed_or_incomplete','#677e87')]:
        count=data['stats']['review_verdicts'][key]
        bars.append(f'<div class="review-row"><span>{label}</span><div class="review-track"><span class="review-fill" style="width:{100*count/512:.4f}%;background:{color}"></span></div><span class="review-value">{count}</span></div>')
    readers=[]
    for name, clauses in data['documents'].items():
        pieces=[]
        for number, clause in clauses.items():
            title=html.escape(clause['title'])
            text=html.escape(clause['text'])
            text=re.sub(r'\*\*(.*?)\*\*',r'<strong>\1</strong>',text)
            text=re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)',r'<em>\1</em>',text)
            text=re.sub(r'`([^`]+)`',r'<code>\1</code>',text)
            pieces.append(f'<h4>{number}. {title}</h4><p>'+text.replace('\n\n','</p><p>')+'</p>')
        # Include document title and preamble as well as the numbered clauses.
        raw=(ROOT/'data/benchmark/constitutions'/f'{name}.md').read_text(encoding='utf-8')
        preamble=raw.split('**1.')[0].strip().split('\n',1)
        heading=html.escape(preamble[0].lstrip('# '))
        intro=html.escape(preamble[1].strip()) if len(preamble)>1 else ''
        readers.append(f'<details class="doc-reader"><summary>{html.escape(name.replace("-"," "))} · {len(clauses)} clauses</summary><div class="doc-body"><h3>{heading}</h3><p>{intro}</p>'+''.join(pieces)+'</div></details>')
    method_rows=[]
    observed={}
    for method in data['run']['config']['methods']:
        group=[c for c in valid if c['method']==method]
        attempted=[c for c in data['candidates'].values() if c['method']==method]
        inconsistent=[c for c in group if c['document'].endswith('-inconsistent')]
        conflicts=sum(bool(c['coherence']['conflicts']) for c in inconsistent)
        core_matches=sum(len(c['fidelity']['matched']) for c in group)
        core_total=core_matches+sum(len(c['fidelity']['missing_design_rules']) for c in group)
        case_agree=case_total=0
        for c in group:
            for case_id,phases in c['diagnostics'].items():
                for phase,actions in phases.items():
                    for action,outcome in actions.items():
                        case_total+=1
                        case_agree+=outcome['status']==data['references'][c['document']][case_id][phase][action]['status']
        quotes=sum(c['validity']['source_trace']=='valid' for c in group)
        rules=sum(len(c['rules']) for c in group)
        supported=sum(v['verdict']=='supported' for c in group for v in c['review']['rule_verdicts'].values())
        observed[method]=(len(group),len(attempted),conflicts,len(inconsistent),core_matches,core_total,case_agree,case_total,quotes,rules,supported)
        cells=[method.upper() if method!='isabelle' else 'Isabelle',f'{len(group)}/{len(attempted)}',f'{conflicts}/{len(inconsistent)}',f'{core_matches}/{core_total}',f'{case_agree}/{case_total}',f'{quotes}/{len(group)}',f'{supported}/{rules}']
        method_rows.append('<tr>'+''.join(f'<td>{html.escape(value)}</td>' for value in cells)+'</tr>')
    expected_methods={
        'smt':(15,16,6,7,90,142,186,225,11,134,37),
        'fol':(16,16,4,8,80,152,174,240,12,127,31),
        'asp':(16,16,4,8,97,152,200,240,10,141,44),
        'isabelle':(16,16,2,8,72,152,160,240,14,110,25),
    }
    if observed!=expected_methods:
        raise ValueError('Target quality measures differ from the written comparison')
    rendered=rendered.replace('{{REVIEW_BARS}}',''.join(bars)).replace('{{DOCUMENTS}}',''.join(readers)).replace('{{METHOD_QUALITY_ROWS}}',''.join(method_rows))
    if re.search(r'\{\{[A-Z_]+\}\}',rendered):
        raise ValueError('Unfilled template field')
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(rendered,encoding='utf-8')
    print(f'Wrote {output_path} ({len(rendered.encode()):,} bytes)')


if __name__ == '__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python reports/build_paper.py runs/<frozen-run>')
    render_paper((ROOT/sys.argv[1]).resolve(), ROOT/'reports/constitution-study-paper.html')
