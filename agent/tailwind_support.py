"""Recognize generated Tailwind utilities before preparing a Vite site."""

from __future__ import annotations

import re
from typing import Mapping


_STANDALONE = {
    "absolute", "block", "contents", "fixed", "flex", "grid", "hidden",
    "inline", "inline-block", "inline-flex", "relative", "sticky",
    "italic", "uppercase", "lowercase", "truncate", "underline", "border",
    "antialiased", "container", "sr-only", "not-sr-only",
}
_PREFIXES = (
    "bg-", "text-", "border-", "rounded-", "px-", "py-", "pt-", "pb-",
    "pl-", "pr-", "p-", "mx-", "my-", "mt-", "mb-", "ml-", "mr-",
    "m-", "gap-", "gap-x-", "gap-y-", "grid-cols-", "max-w-", "min-w-",
    "max-h-", "min-h-", "w-", "h-", "font-", "tracking-", "leading-",
    "shadow-", "duration-", "opacity-", "z-", "top-", "bottom-", "left-",
    "right-", "items-", "justify-", "self-", "overflow-", "transition-",
    "backdrop-", "space-x-", "space-y-", "flex-", "basis-", "grow-",
    "shrink-", "cursor-", "select-", "ring-", "outline-", "animate-",
    "divide-", "inset-", "min-h-", "min-w-", "from-", "to-", "via-",
)
_VARIANTS = {"sm", "md", "lg", "xl", "2xl", "hover", "focus", "focus-visible", "active", "dark", "group-hover", "disabled"}


def is_tailwind_utility(token: str) -> bool:
    """Recognize common utility syntax without treating BEM names as utilities."""
    pieces = token.split(":")
    if len(pieces) > 1 and not all(part in _VARIANTS for part in pieces[:-1]):
        return False
    base = pieces[-1].lstrip("!-")
    return base in _STANDALONE or any(base.startswith(prefix) for prefix in _PREFIXES)


def site_uses_tailwind(files: Mapping[str, str], minimum: int = 3) -> bool:
    """Require several utility tokens so a single class does not switch styling modes."""
    found: set[str] = set()
    for path, source in files.items():
        if not path.endswith((".tsx", ".jsx")):
            continue
        for match in re.finditer(r'className\s*=\s*["\']([^"\']+)["\']', source):
            for token in match.group(1).split():
                if is_tailwind_utility(token):
                    found.add(token)
                    if len(found) >= minimum:
                        return True
    return False
