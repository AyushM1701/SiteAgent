"""Fix JSX comment syntax in r3f_performance_fix_v1 record."""
import json
from pathlib import Path

draft = Path("data/r3f_trajectories/r3f_draft.jsonl")
rows = [json.loads(l) for l in draft.read_text(encoding="utf-8").splitlines()]

for r in rows:
    if r["task_id"] == "r3f_performance_fix_v1":
        for msg in r["messages"]:
            if msg["role"] == "assistant":
                c = msg["content"]
                # JSX comments cannot appear between element attributes.
                # These three patterns produce TS1005 — fix them to inline comments above.
                c = c.replace(
                    'frameloop="demand"{/* fix 2 */}',
                    'frameloop="demand"'
                )
                c = c.replace(
                    'dpr={[1, 1.5]}{/* fix 1: no 4K canvas */}',
                    'dpr={[1, 1.5]}'
                )
                c = c.replace(
                    '<ambientLight intensity={0.6} />{/* fix 3+5: 2 lights, no shadows */}',
                    '<ambientLight intensity={0.6} />'
                )
                msg["content"] = c
                print("Patched r3f_performance_fix_v1 JSX comments")

draft.write_text(
    "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
    encoding="utf-8",
)
print("Saved", len(rows), "records")
