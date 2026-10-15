"""Build original reference-inspired websites and bounded, verified SFT records.

Run without --publish to assemble previews. After browser verification, --publish
requires source-hash-matched verification evidence. Source websites aren't copied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.agent_protocol import SITE_AGENT_SYSTEM_PROMPT, WriteSiteAction, format_chatml, parse_agent_output

DATA = ROOT / "data/premium_reference"
PREVIEW = ROOT / "examples/reference-curriculum"
SITES = {
    "margin": {
        "reference": "https://ellipsus.com/#introduction", "family": "editorial_workspace",
        "description": "Margin, an original fictional writing workspace: warm paper, aubergine ink, clay accent, expressive serif type, layered notes, generous editorial spacing.",
        "tokens": ":root{--paper:#f7f0e4;--ink:#302831;--accent:#a34829;--line:#c7bdb0}",
        "sections": {"Hero": "A centered editorial hero with layered dimensional paper artwork and anchors to intro, workspace and plans. Keep decorative art out of the accessibility tree; reduced motion disables entrance animation.",
                     "Workspace": "An editable local notebook with a live whitespace-delimited word count and an aria-pressed toggle that shows/hides editorial notes. No backend or persistence.",
                     "Principles": "A dark editorial manifesto with three numbered principles, a large serif heading, and a responsive three-column layout.",
                     "Plans": "An illustrative personal plan: monthly $10, annual $8 per month / $96 billed yearly. An accessible switch updates the price and billing description together. CTA reaches #workspace; no purchase.",
                     "Footer": "A compact responsive footer identifying the fictional workspace and linking back to #intro."}},
    "fieldwork": {
        "reference": "https://mode.com", "family": "analytics_platform",
        "description": "Fieldwork, an original fictional analytics platform: dark forest ink, bright lime, warm cream, large serif headline blocks and precise interface typography. All chart data is illustrative.",
        "tokens": ":root{--paper:#f0f1e5;--cream:#f0f1e5;--ink:#123d32;--lime:#cce877;--line:#afbea0}",
        "sections": {"Hero": "A bold offset-block serif hero, CSS dimensional data-column illustration, and links to #capabilities, #architecture and #questions. No invented customers or metrics.",
                     "Capabilities": "An analytics console with Overview, Retention and Acquisition tabs; arrow/Home/End keyboard navigation and roving tabIndex. Each view updates six sample chart bars and a matching accessible table in a details disclosure. Selected state, panel labels and focus must stay consistent.",
                     "Architecture": "An alternating numbered process stack connecting Source, Shape, Explore and Decide beside a large editorial explanation. Preserve order on mobile.",
                     "Questions": "Three native details disclosures explaining sample data, keyboard operation and local state. Every summary must open its answer with keyboard or pointer.",
                     "Footer": "A dark responsive footer with a fictional-platform disclaimer, sample-data label and link to #intro."}},
    "parallax": {
        "reference": "https://ventriloc.ca/en/", "family": "dimensional_consultancy",
        "description": "Parallax, an original fictional data/design consultancy: ivory, charcoal, muted copper, oversized sans type, spacious composition and CSS 3D panels. All work is explicitly conceptual, not client claims.",
        "tokens": ":root{--paper:#f7f5ef;--ink:#292725;--copper:#92613f;--line:#cec7bc}",
        "sections": {"Hero": "A split consultancy hero with floating CSS 3D interface panels, a pause/resume button using aria-pressed, reduced-motion support and navigation to #services, #work and #contact. Controls must remain visible.",
                     "Services": "An accessible accordion for Strategy, Engineering and Experience. First panel opens initially; clicking its header closes it. Only one panel opens at once. Synchronize aria-expanded, aria-controls and hidden content.",
                     "Projects": "Three explicitly labeled concept projects, one each for Experience, Engineering and Strategy. All/category filter buttons update aria-pressed, the rendered cards and a singular/plural live result count.",
                     "Contact": "A local project-brief form with a required textarea of at least ten characters. The submit handler prevents navigation and shows honest no-send/no-storage status. Editing resets success; no network request.",
                     "Footer": "A minimal responsive footer identifying the fictional studio and linking to #intro."}},
}

BASE_CSS = """*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:20px}body{margin:0;background:var(--paper);color:var(--ink);font-family:Arial,sans-serif}a{color:inherit;text-decoration:none}button,input,textarea{font:inherit}p{line-height:1.75}button,a,summary,input,textarea{touch-action:manipulation}a:focus-visible,button:focus-visible,summary:focus-visible,textarea:focus-visible,[tabindex]:focus-visible{outline:3px solid #79649f;outline-offset:5px}.eyebrow{font:10px/1.6 monospace;letter-spacing:.13em}section{scroll-margin-top:20px}[hidden]{display:none!important}.skip{position:absolute;left:15px;top:-100px;z-index:20;background:var(--ink);color:var(--paper);padding:15px}.skip:focus{top:15px}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
"""


PALETTES = json.loads((DATA / 'palettes.json').read_text(encoding='utf-8'))
for _site, _palette in PALETTES.items():
    SITES[_site]['tokens'] += ':root{' + ''.join(f'{key}:{value};' for key, value in _palette.items()) + '}'


def source_hash(site):
    payload = SITES[site]["tokens"] + BASE_CSS
    for path in sorted((DATA / "source" / site).glob("*")):
        payload += path.name + path.read_text(encoding="utf-8")
    return hashlib.sha256(payload.encode()).hexdigest()


def envelope(files):
    return '<thought>Implement the requested section with complete files, responsive styling and honest, accessible behavior.</thought>\n<tool_call name="write_site">\n' + ''.join(f'<file path="{name}">\n{code}\n</file>\n' for name, code in files.items()) + '</tool_call>'


def build_previews():
    for site, spec in SITES.items():
        dest = PREVIEW / site
        components = dest / "src/components"
        components.mkdir(parents=True, exist_ok=True)
        for source in (DATA / "source" / site).glob("*"):
            (components / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        (dest / "base.css").write_text(spec["tokens"] + BASE_CSS, encoding="utf-8")
        imports = '\n'.join(f'import {name} from "./src/components/{name}";' for name in spec["sections"])
        body = ''.join(f'<{name}/>' for name in spec["sections"])
        (dest / "main.tsx").write_text('import React from "react";import {createRoot} from "react-dom/client";import "./base.css";\n' + imports + '\ncreateRoot(document.getElementById("root")!).render(<><a className="skip" href="#main">Skip to content</a><main id="main">' + body + '</main></>);', encoding="utf-8")
        (dest / "index.html").write_text(f'<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{site.title()} — Original training reference</title></head><body><div id="root"></div><script type="module" src="./main.tsx"></script></body></html>', encoding="utf-8")
    PREVIEW.mkdir(parents=True, exist_ok=True)
    links = ''.join(f'<a href="./{site}/"><strong>{site.title()}</strong><p>{spec["description"]}</p><span>Explore original reference →</span></a>' for site,spec in SITES.items())
    (PREVIEW / "index.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reference curriculum</title><style>body{margin:0;padding:7vw;background:#101211;color:#e9eadf;font:16px/1.7 Arial}h1{font-size:clamp(40px,6vw,76px);line-height:1;letter-spacing:-.06em}section{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:24px}a{padding:30px;border:1px solid #777b6a;border-radius:14px;color:inherit;text-decoration:none}a:hover{background:#252923}strong{font:36px Georgia}span{font-size:12px;color:#cee7a5}p{color:#bbc0af;font-size:14px}</style><h1>Three perspectives.<br />One quality standard.</h1><p>Original, hand-authored training references. These are not generated by the local model.</p><section>' + links + '</section></html>', encoding="utf-8")
    print(json.dumps({site:source_hash(site) for site in SITES}, indent=2))


def publish():
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(ROOT / "my-react-agent-lora/tokenizer.json"))
    records = []
    behavior_repairs = {
        ('margin', 'Workspace'): ('onChange={event => setText(event.target.value)}', 'onChange={() => undefined}', 'Typing does not update the controlled editor or word count.'),
        ('fieldwork', 'Capabilities'): ('onClick={()=>setActive(label)}', "onClick={()=>setActive('Overview')}", 'Clicking Retention or Acquisition leaves Overview selected.'),
        ('parallax', 'Projects'): ("projects.filter(project=>category==='All'||project.category===category)", 'projects.filter(()=>true)', 'Selecting Engineering still renders all three projects and the wrong result count.'),
    }
    for site, spec in SITES.items():
        proof = json.loads((DATA / "verification" / f"{site}.json").read_text(encoding="utf-8"))
        if proof.get("source_sha256") != source_hash(site) or not proof.get("passed"):
            raise ValueError(f"Missing or stale verification: {site}")
        for section, instruction in spec["sections"].items():
            files = {f"src/components/{section}.{ext}": (DATA / "source" / site / f"{section}.{ext}").read_text(encoding="utf-8") for ext in ("tsx", "css")}
            target = envelope(files)
            parsed = parse_agent_output(target)
            if not isinstance(parsed.action, WriteSiteAction) or dict(parsed.action.files) != {k:v.strip() for k,v in files.items()}:
                raise ValueError(f"Protocol roundtrip failed for {site}/{section}")
            prompt = f'Build the {section} section for {spec["description"]}\n{instruction}\nWrite exactly src/components/{section}.tsx and {section}.css. Export default {section}. No code fences. Close each file tag before starting the next. The existing global reset provides border-box sizing, zero body margin, Arial, inherited link colors, visible focus outlines and reduced-motion scrolling. Use the existing theme tokens for all colors:\n{spec["tokens"]}'
            base = {"task_id": f"reference_{site}_{section.lower()}", "source_task_id":f"reference_{site}","family_id":f"reference_{spec['family']}","provenance":{"author":"Codex","source_sha256":source_hash(site),"verification_file":f"data/premium_reference/verification/{site}.json","reference_url":spec["reference"],"original_implementation":True}}
            records.append({**base,"messages":[{"role":"system","content":SITE_AGENT_SYSTEM_PROMPT},{"role":"user","content":prompt},{"role":"assistant","content":target}]})
            if section == "Hero":
                # A synthetic malformed envelope; it is input context, never a loss target.
                broken = target.replace('</file>', '', 1)
                repair_prompt = f'Repair the file envelope for {spec["description"]} Keep the supplied implementation and existing theme variable names unchanged.\nPrevious invalid output:\n' + broken + '\n<observation status="error">The first file is missing its closing tag. Return both complete files with one closing file tag per file; no markdown fences.</observation>'
                records.append({**base,"task_id":base["task_id"]+"_repair_envelope","synthetic_repair":True,"messages":[{"role":"system","content":SITE_AGENT_SYSTEM_PROMPT},{"role":"user","content":repair_prompt},{"role":"assistant","content":target}]})
            if (site, section) in behavior_repairs:
                good, bad, symptom = behavior_repairs[(site, section)]
                if target.count(good) != 1:
                    raise ValueError(f'Repair mutation no longer matches {site}/{section}')
                faulty_tsx = files[f'src/components/{section}.tsx'].replace(good, bad, 1)
                repair_prompt = prompt + '\nSynthetic debugging exercise. The following deliberately faulty TSX has this defect: ' + symptom + '\nReturn both the complete corrected TSX and its complete CSS.\n' + faulty_tsx
                records.append({**base, 'task_id':base['task_id']+'_repair_behavior', 'synthetic_repair':True, 'messages':[{'role':'system','content':SITE_AGENT_SYSTEM_PROMPT},{'role':'user','content':repair_prompt},{'role':'assistant','content':target}]})
    for row in records:
        target_tokens = len(tokenizer.encode(row["messages"][-1]["content"],add_special_tokens=False).ids)
        total_tokens = len(tokenizer.encode(format_chatml(row["messages"],False),add_special_tokens=False).ids)+1
        if target_tokens > 4096 or total_tokens > 8192:
            raise ValueError(f'{row["task_id"]}: budget exceeded ({target_tokens}/{total_tokens})')
        row.update(token_count=total_tokens,target_tokens=target_tokens)
    (DATA / "train.jsonl").write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in records),encoding="utf-8")
    report = {"independent_sites":len(SITES),"section_examples":15,"synthetic_protocol_repairs":3,"total_examples":len(records),"max_target_tokens":max(r['target_tokens'] for r in records),"max_total_tokens":max(r['token_count'] for r in records),"tokenizer_sha256":hashlib.sha256((ROOT/'my-react-agent-lora/tokenizer.json').read_bytes()).hexdigest(),"source_hashes":{site:source_hash(site) for site in SITES},"training_performed":False,"limits":"Browser/type/protocol verification does not prove model quality. No source-site assets or code copied."}
    report['synthetic_behavior_repairs'] = len(behavior_repairs)
    (DATA / "report.json").write_text(json.dumps(report,indent=2)+'\n',encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish",action="store_true")
    args=parser.parse_args()
    build_previews()
    if args.publish: publish()
