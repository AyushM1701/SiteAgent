"""Bound repair requests to real files and observed local decoding speed."""
import math
import re


def focus_repair_errors(errors):
    compiler = [line for line in errors if '[TypeScript Error]' in line]
    pool = compiler or errors
    target = next((match.group(0) for line in pool
                   if (match := re.search(r'(?:src/)?[\w./-]+\.(?:tsx|ts|css|jsx|js)\b', line))), None)
    if target:
        return [line for line in pool if target in line][:12]
    return pool[:8]


def repair_timeout_seconds(tokens, diagnostics=None, override=None):
    if override is not None:
        return max(30, int(override))
    speed = (diagnostics or {}).get('tokens_per_second', 10)
    if not isinstance(speed, (int, float)) or not math.isfinite(speed) or speed <= 0:
        speed = 10
    return min(600, max(90, math.ceil(tokens / speed * 1.25 + 20)))
