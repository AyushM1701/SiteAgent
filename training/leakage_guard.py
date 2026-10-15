"""
Benchmark evaluation leakage guard for SiteAgent.

Enforces strict separation between the Development Benchmark and the Sealed Final Benchmark.
Maintains and strengthens the 6 mandatory leakage checks:
1. Exact prompt matching
2. Normalized matching (whitespace-collapsed, punctuation-stripped, casefolded)
3. Symbol overlap (PascalCase, backticked identifiers, useX hooks, styles.X)
4. Token similarity (word-level Jaccard similarity)
5. Family-level holdout (family_id, source_task_id, task_id)
6. Semantic similarity checks (character/word n-gram overlap & specification overlap)
"""

import hashlib
import json
import math
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple


BASE_DIR = Path(__file__).resolve().parents[1]
SEALED_BENCHMARK_PATH = BASE_DIR / "data" / "eval" / "sealed_final_benchmark.jsonl"
SEALED_MANIFEST_PATH = BASE_DIR / "data" / "eval" / "sealed_final_benchmark_manifest.json"
DEV_BENCHMARK_PATH = BASE_DIR / "data" / "eval" / "dev_benchmark.jsonl"
LEGACY_BENCHMARK_PATH = BASE_DIR / "data" / "eval" / "react_ts_css_eval_set_combined.jsonl"


def normalize_text(text: str) -> str:
    """Normalize text by casefolding, stripping punctuation, and collapsing whitespace."""
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


COMMON_FRAMEWORK_SYMBOLS = {
    # React & DOM common props, events & primitives
    "onChange", "onClick", "onClose", "onSubmit", "onSelect", "onFocus", "onBlur",
    "children", "value", "defaultValue", "isOpen", "disabled", "size", "color",
    "className", "style", "key", "id", "name", "title", "placeholder", "label",
    "string", "number", "boolean", "any", "void", "null", "undefined", "object",
    "RefObject", "HTMLElement", "HTMLDivElement", "HTMLInputElement", "HTMLButtonElement",
    "ReactNode", "FC", "CSSProperties", "MouseEvent", "KeyboardEvent", "ChangeEvent",
    "role", "code", "step", "steps", "count", "items", "options", "data", "text", "type",
    "aria-label", "aria-expanded", "aria-selected", "aria-checked", "aria-valuenow",
    "aria-valuemin", "aria-valuemax", "aria-hidden", "aria-modal", "aria-disabled",
    "Write", "Build", "Create", "Style", "Implement", "React", "TypeScript", "CSS",
    "HTML", "DOM", "API", "JSON", "The", "When", "If", "Each", "All", "For", "Use",
    "Ensure", "Every", "Add", "Make", "Provide", "Support", "Given", "Component",
}


def extract_symbols(text: str) -> Set[str]:
    """
    Extract domain symbols from prompt or code:
    - PascalCase component identifiers (e.g. PinInputCode, Modal)
    - Backticked code identifier tokens (e.g. `Tooltip`, `delayMs`)
    - Custom React hooks (e.g. useToast, useDebounce)
    - CSS module classes (styles.container)
    - data-testid attributes
    Filters out common framework keywords and primitives.
    """
    if not text:
        return set()
    pascal = set(re.findall(r"\b[A-Z][a-zA-Z0-9]+(?:[A-Z][a-z0-9]+)+\b", text))
    backticks = set(re.findall(r"`([A-Za-z0-9_]+)`", text))
    hooks = set(re.findall(r"\buse[A-Z][a-zA-Z0-9]+\b", text))
    css_classes = set(re.findall(r"styles\.([a-zA-Z0-9_-]+)", text))
    test_ids = set(re.findall(r'data-testid=["\']([^"\']+)["\']', text))
    raw_symbols = {s for s in (pascal | backticks | hooks | css_classes | test_ids) if len(s) > 1}
    return raw_symbols - COMMON_FRAMEWORK_SYMBOLS


def compute_token_jaccard(text1: str, text2: str) -> float:
    """Compute token Jaccard similarity over alphanumeric words."""
    w1 = set(re.findall(r"\b[a-zA-Z0-9_]+\b", text1.lower()))
    w2 = set(re.findall(r"\b[a-zA-Z0-9_]+\b", text2.lower()))
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1 | w2)


def compute_word_cosine_similarity(text1: str, text2: str) -> float:
    """Compute cosine similarity over word frequencies."""
    from collections import Counter
    w1 = Counter(re.findall(r"\b[a-zA-Z0-9_]+\b", text1.lower()))
    w2 = Counter(re.findall(r"\b[a-zA-Z0-9_]+\b", text2.lower()))
    if not w1 or not w2:
        return 0.0
    dot = sum(w1[k] * w2.get(k, 0) for k in w1)
    norm1 = math.sqrt(sum(v * v for v in w1.values()))
    norm2 = math.sqrt(sum(v * v for v in w2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def compute_ngram_dice(text1: str, text2: str, n: int = 3) -> float:
    """Compute character n-gram Dice coefficient over normalized text."""
    t1 = normalize_text(text1)
    t2 = normalize_text(text2)
    if len(t1) < n or len(t2) < n:
        return 0.0
    ngrams1 = {t1[i : i + n] for i in range(len(t1) - n + 1)}
    ngrams2 = {t2[i : i + n] for i in range(len(t2) - n + 1)}
    if not ngrams1 or not ngrams2:
        return 0.0
    return 2.0 * len(ngrams1 & ngrams2) / (len(ngrams1) + len(ngrams2))


def compute_semantic_similarity(text1: str, text2: str) -> float:
    """
    Composite semantic similarity metric:
    Blends word frequency cosine similarity (50%) and character 3-gram Dice coefficient (50%).
    Captures semantic rephrasings and structural overlap without requiring heavy external models.
    """
    cos_sim = compute_word_cosine_similarity(text1, text2)
    dice_sim = compute_ngram_dice(text1, text2, n=3)
    return (0.50 * cos_sim) + (0.50 * dice_sim)


class BenchmarkRecord:
    """Structured representation of a benchmark item."""

    def __init__(
        self,
        task_id: str,
        prompt: str,
        check: Optional[str] = None,
        test_code: Optional[str] = None,
        family_id: Optional[str] = None,
        source_task_id: Optional[str] = None,
        symbols: Optional[Set[str]] = None,
        category: Optional[str] = None,
    ):
        self.task_id = str(task_id)
        self.prompt = prompt.strip()
        self.check = check
        self.test_code = test_code
        self.family_id = str(family_id) if family_id is not None else None
        self.source_task_id = str(source_task_id) if source_task_id is not None else None
        self.category = category
        self.clean_prompt = normalize_text(self.prompt)
        self.symbols = symbols if symbols is not None else extract_symbols(self.prompt)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "task_id": self.task_id,
            "prompt": self.prompt,
        }
        if self.family_id:
            d["family_id"] = self.family_id
        if self.category:
            d["category"] = self.category
        if self.check:
            d["check"] = self.check
        if self.test_code:
            d["test_code"] = self.test_code
        if self.source_task_id:
            d["source_task_id"] = self.source_task_id
        return d


class LeakageViolation:
    """Information about a detected leakage violation."""

    def __init__(
        self,
        check_type: str,
        message: str,
        candidate_identifier: str,
        benchmark_task_id: str,
        candidate_snippet: str,
        benchmark_snippet: str,
        similarity_score: float = 0.0,
    ):
        self.check_type = check_type
        self.message = message
        self.candidate_identifier = candidate_identifier
        self.benchmark_task_id = benchmark_task_id
        self.candidate_snippet = candidate_snippet
        self.benchmark_snippet = benchmark_snippet
        self.similarity_score = similarity_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_type": self.check_type,
            "message": self.message,
            "candidate_identifier": self.candidate_identifier,
            "benchmark_task_id": self.benchmark_task_id,
            "candidate_snippet": self.candidate_snippet,
            "benchmark_snippet": self.benchmark_snippet,
            "similarity_score": round(self.similarity_score, 4),
        }


class LeakageAuditReport:
    """Complete summary of a benchmark leakage audit."""

    def __init__(
        self,
        dataset_path: str,
        benchmark_path: str,
        total_candidate_samples: int,
        total_benchmark_tasks: int,
        violations: List[LeakageViolation],
        peak_token_similarity: float,
        peak_semantic_similarity: float,
        token_threshold: float,
        semantic_threshold: float,
        manifest_verified: bool,
    ):
        self.dataset_path = str(dataset_path)
        self.benchmark_path = str(benchmark_path)
        self.total_candidate_samples = total_candidate_samples
        self.total_benchmark_tasks = total_benchmark_tasks
        self.violations = violations
        self.leak_count = len(violations)
        self.is_clean = (self.leak_count == 0) and manifest_verified
        self.peak_token_similarity = peak_token_similarity
        self.peak_semantic_similarity = peak_semantic_similarity
        self.token_threshold = token_threshold
        self.semantic_threshold = semantic_threshold
        self.manifest_verified = manifest_verified

    @property
    def breakdown(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for v in self.violations:
            counts[v.check_type] = counts.get(v.check_type, 0) + 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_clean": self.is_clean,
            "leak_count": self.leak_count,
            "manifest_verified": self.manifest_verified,
            "total_candidate_samples": self.total_candidate_samples,
            "total_benchmark_tasks": self.total_benchmark_tasks,
            "peak_token_similarity": round(self.peak_token_similarity, 4),
            "peak_semantic_similarity": round(self.peak_semantic_similarity, 4),
            "thresholds": {
                "token_similarity": self.token_threshold,
                "semantic_similarity": self.semantic_threshold,
            },
            "leak_breakdown": self.breakdown,
            "violations": [v.to_dict() for v in self.violations],
        }


class LeakageAuditor:
    """
    Auditor that executes the 6 leakage checks between candidate training/dev data
    and a held-out benchmark.
    """

    def __init__(
        self,
        benchmark_records: List[BenchmarkRecord],
        token_similarity_threshold: float = 0.50,
        semantic_similarity_threshold: float = 0.65,
        symbol_overlap_threshold: float = 0.35,
    ):
        self.benchmark_records = benchmark_records
        self.token_threshold = token_similarity_threshold
        self.semantic_threshold = semantic_similarity_threshold
        self.symbol_threshold = symbol_overlap_threshold

        # Precompute lookup index structures for fast fail-closed checks
        self.exact_prompts: Dict[str, BenchmarkRecord] = {}
        self.clean_prompts: Dict[str, BenchmarkRecord] = {}
        self.family_ids: Dict[str, BenchmarkRecord] = {}
        self.source_task_ids: Dict[str, BenchmarkRecord] = {}
        self.task_ids: Dict[str, BenchmarkRecord] = {}

        for record in benchmark_records:
            self.exact_prompts[record.prompt] = record
            if record.clean_prompt:
                self.clean_prompts[record.clean_prompt] = record
            if record.family_id:
                self.family_ids[record.family_id] = record
            if record.source_task_id:
                self.source_task_ids[record.source_task_id] = record
            if record.task_id:
                self.task_ids[record.task_id] = record

    @classmethod
    def from_file(cls, benchmark_file: str, **kwargs) -> "LeakageAuditor":
        records = load_benchmark_records(benchmark_file)
        return cls(records, **kwargs)

    def audit_prompt(
        self,
        prompt: str,
        identifier: str,
        family_id: Optional[str] = None,
        source_task_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Tuple[List[LeakageViolation], float, float]:
        """Audit a single prompt against all benchmark records."""
        violations: List[LeakageViolation] = []
        p_clean = normalize_text(prompt)
        p_symbols = extract_symbols(prompt)

        max_token_sim = 0.0
        max_semantic_sim = 0.0

        # Check 1: Exact prompt matching
        if prompt in self.exact_prompts:
            match = self.exact_prompts[prompt]
            violations.append(
                LeakageViolation(
                    check_type="exact_prompt_matching",
                    message="Candidate prompt matches benchmark prompt verbatim",
                    candidate_identifier=identifier,
                    benchmark_task_id=match.task_id,
                    candidate_snippet=prompt[:80],
                    benchmark_snippet=match.prompt[:80],
                    similarity_score=1.0,
                )
            )

        # Check 2: Normalized matching
        elif p_clean and p_clean in self.clean_prompts:
            match = self.clean_prompts[p_clean]
            violations.append(
                LeakageViolation(
                    check_type="normalized_matching",
                    message="Candidate prompt normalized form matches benchmark prompt",
                    candidate_identifier=identifier,
                    benchmark_task_id=match.task_id,
                    candidate_snippet=prompt[:80],
                    benchmark_snippet=match.prompt[:80],
                    similarity_score=1.0,
                )
            )

        # Check 5: Family-level holdout (metadata identifiers)
        if family_id and str(family_id) in self.family_ids:
            match = self.family_ids[str(family_id)]
            violations.append(
                LeakageViolation(
                    check_type="family_level_holdout",
                    message=f"Candidate family_id '{family_id}' collides with benchmark family",
                    candidate_identifier=identifier,
                    benchmark_task_id=match.task_id,
                    candidate_snippet=prompt[:80],
                    benchmark_snippet=match.prompt[:80],
                    similarity_score=1.0,
                )
            )
        if source_task_id and str(source_task_id) in self.source_task_ids:
            match = self.source_task_ids[str(source_task_id)]
            violations.append(
                LeakageViolation(
                    check_type="family_level_holdout",
                    message=f"Candidate source_task_id '{source_task_id}' collides with benchmark task",
                    candidate_identifier=identifier,
                    benchmark_task_id=match.task_id,
                    candidate_snippet=prompt[:80],
                    benchmark_snippet=match.prompt[:80],
                    similarity_score=1.0,
                )
            )
        if task_id and str(task_id) in self.task_ids:
            match = self.task_ids[str(task_id)]
            violations.append(
                LeakageViolation(
                    check_type="family_level_holdout",
                    message=f"Candidate task_id '{task_id}' collides with benchmark task",
                    candidate_identifier=identifier,
                    benchmark_task_id=match.task_id,
                    candidate_snippet=prompt[:80],
                    benchmark_snippet=match.prompt[:80],
                    similarity_score=1.0,
                )
            )

        # Iterate through benchmark records for similarity & symbol checks
        for brec in self.benchmark_records:
            token_sim = compute_token_jaccard(prompt, brec.prompt)
            if token_sim > max_token_sim:
                max_token_sim = token_sim

            # Check 4: Token similarity
            if token_sim >= self.token_threshold:
                violations.append(
                    LeakageViolation(
                        check_type="token_similarity",
                        message=f"Token Jaccard similarity {token_sim:.3f} >= threshold {self.token_threshold}",
                        candidate_identifier=identifier,
                        benchmark_task_id=brec.task_id,
                        candidate_snippet=prompt[:80],
                        benchmark_snippet=brec.prompt[:80],
                        similarity_score=token_sim,
                    )
                )

            # Check 3: Symbol overlap
            common_symbols = p_symbols & brec.symbols
            if common_symbols:
                # Symbol collision coupled with moderate token similarity indicates targeted test replication
                if token_sim >= self.symbol_threshold:
                    violations.append(
                        LeakageViolation(
                            check_type="symbol_overlap",
                            message=(
                                f"Shared symbol(s) {common_symbols} with token similarity "
                                f"{token_sim:.3f} >= threshold {self.symbol_threshold}"
                            ),
                            candidate_identifier=identifier,
                            benchmark_task_id=brec.task_id,
                            candidate_snippet=prompt[:80],
                            benchmark_snippet=brec.prompt[:80],
                            similarity_score=token_sim,
                        )
                    )

            # Check 6: Semantic similarity checks
            semantic_sim = compute_semantic_similarity(prompt, brec.prompt)
            if semantic_sim > max_semantic_sim:
                max_semantic_sim = semantic_sim

            if semantic_sim >= self.semantic_threshold:
                violations.append(
                    LeakageViolation(
                        check_type="semantic_similarity_checks",
                        message=(
                            f"Semantic similarity {semantic_sim:.3f} >= threshold "
                            f"{self.semantic_threshold}"
                        ),
                        candidate_identifier=identifier,
                        benchmark_task_id=brec.task_id,
                        candidate_snippet=prompt[:80],
                        benchmark_snippet=brec.prompt[:80],
                        similarity_score=semantic_sim,
                    )
                )

        return violations, max_token_sim, max_semantic_sim


def load_benchmark_records(benchmark_file: str) -> List[BenchmarkRecord]:
    """Load benchmark records from a jsonl file."""
    path = resolve_file_path(benchmark_file)
    if not path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {benchmark_file}")

    records: List[BenchmarkRecord] = []
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as err:
                raise ValueError(f"Invalid JSON record at {benchmark_file}:{idx}") from err

            prompt = data.get("prompt", "").strip()
            if not prompt:
                raise ValueError(f"Benchmark record missing prompt at {benchmark_file}:{idx}")

            task_id = data.get("task_id", f"bench_task_{idx:03d}")
            family_id = data.get("family_id")
            source_task_id = data.get("source_task_id")
            check = data.get("check")
            test_code = data.get("test_code")
            category = data.get("category")

            records.append(
                BenchmarkRecord(
                    task_id=str(task_id),
                    prompt=prompt,
                    check=check,
                    test_code=test_code,
                    family_id=str(family_id) if family_id is not None else None,
                    source_task_id=str(source_task_id) if source_task_id is not None else None,
                    category=category,
                )
            )

    if not records:
        raise ValueError(f"Benchmark contains no usable records: {benchmark_file}")

    return records


def resolve_file_path(filepath: str) -> Path:
    """Resolve file path relative to workspace or base directory."""
    p = Path(filepath)
    if p.is_absolute() and p.exists():
        return p
    candidates = [
        Path(filepath),
        BASE_DIR / filepath,
        BASE_DIR / "data" / filepath,
        BASE_DIR / "data" / "eval" / filepath,
    ]
    for c in candidates:
        if c.exists():
            return c
    return Path(filepath)


def verify_sealed_benchmark_manifest(
    benchmark_path: Optional[str] = None,
    manifest_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Cryptographically verify the sealed final benchmark against its manifest.
    Fails closed if the file has been altered, tampered with, or corrupted.
    """
    b_path = resolve_file_path(benchmark_path or str(SEALED_BENCHMARK_PATH))
    m_path = resolve_file_path(manifest_path or str(SEALED_MANIFEST_PATH))

    if not b_path.exists():
        raise FileNotFoundError(f"Sealed benchmark not found at {b_path}")
    if not m_path.exists():
        raise FileNotFoundError(f"Sealed benchmark manifest not found at {m_path}")

    with open(m_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Compute actual SHA-256
    sha = hashlib.sha256()
    line_count = 0
    with open(b_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(chunk)

    actual_hash = sha.hexdigest()
    expected_hash = manifest.get("sha256")

    # Count records
    with open(b_path, "r", encoding="utf-8") as f:
        line_count = sum(1 for line in f if line.strip())

    expected_count = manifest.get("task_count")

    if actual_hash != expected_hash:
        raise RuntimeError(
            f"SEALED BENCHMARK INTEGRITY VIOLATION: SHA-256 mismatch!\n"
            f"Expected: {expected_hash}\n"
            f"Actual:   {actual_hash}\n"
            f"File: {b_path}"
        )

    if line_count != expected_count:
        raise RuntimeError(
            f"SEALED BENCHMARK INTEGRITY VIOLATION: Task count mismatch!\n"
            f"Expected: {expected_count}\n"
            f"Actual:   {line_count}\n"
            f"File: {b_path}"
        )

    return {
        "status": "sealed_valid",
        "benchmark_file": str(b_path),
        "manifest_file": str(m_path),
        "sha256": actual_hash,
        "task_count": line_count,
        "sealed_at": manifest.get("sealed_at"),
    }


def audit_dataset_against_benchmark(
    dataset_path: str,
    benchmark_path: Optional[str] = None,
    manifest_path: Optional[str] = None,
    token_similarity_threshold: float = 0.50,
    semantic_similarity_threshold: float = 0.65,
    symbol_overlap_threshold: float = 0.35,
    verify_manifest: bool = True,
) -> LeakageAuditReport:
    """
    Exhaustively audit any dataset against a held-out benchmark using the 6 checks.
    """
    b_file = benchmark_path or str(SEALED_BENCHMARK_PATH)
    auditor = LeakageAuditor.from_file(
        b_file,
        token_similarity_threshold=token_similarity_threshold,
        semantic_similarity_threshold=semantic_similarity_threshold,
        symbol_overlap_threshold=symbol_overlap_threshold,
    )

    manifest_verified = True
    if verify_manifest and (manifest_path or Path(b_file).name == "sealed_final_benchmark.jsonl"):
        try:
            verify_sealed_benchmark_manifest(b_file, manifest_path)
            manifest_verified = True
        except (FileNotFoundError, RuntimeError):
            manifest_verified = False
            raise

    d_path = resolve_file_path(dataset_path)
    if not d_path.exists():
        raise FileNotFoundError(f"Dataset not found at: {dataset_path}")

    all_violations: List[LeakageViolation] = []
    peak_token = 0.0
    peak_semantic = 0.0
    total_samples = 0

    with open(d_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as err:
                raise ValueError(f"Invalid record at {dataset_path}:{line_num}") from err

            total_samples += 1
            sample_id = rec.get("task_id", f"sample_{line_num}")
            family_id = rec.get("family_id")
            source_task_id = rec.get("source_task_id")

            # Extract user prompts from conversation messages or raw prompt field
            prompts: List[str] = []
            if "prompt" in rec and isinstance(rec["prompt"], str):
                prompts.append(rec["prompt"].strip())
            if "messages" in rec and isinstance(rec["messages"], list):
                for m in rec["messages"]:
                    if isinstance(m, dict) and m.get("role") == "user":
                        c = m.get("content", "").strip()
                        # Avoid treating simulator feedback as the initial prompt
                        if c and not c.startswith("<observation"):
                            prompts.append(c)

            for p_idx, prompt in enumerate(prompts):
                ident = f"{sample_id}_turn{p_idx + 1}" if len(prompts) > 1 else sample_id
                v_list, t_sim, s_sim = auditor.audit_prompt(
                    prompt=prompt,
                    identifier=f"{ident} (line {line_num})",
                    family_id=family_id,
                    source_task_id=source_task_id,
                    task_id=rec.get("task_id"),
                )
                if t_sim > peak_token:
                    peak_token = t_sim
                if s_sim > peak_semantic:
                    peak_semantic = s_sim
                all_violations.extend(v_list)

    return LeakageAuditReport(
        dataset_path=str(d_path),
        benchmark_path=str(b_file),
        total_candidate_samples=total_samples,
        total_benchmark_tasks=len(auditor.benchmark_records),
        violations=all_violations,
        peak_token_similarity=peak_token,
        peak_semantic_similarity=peak_semantic,
        token_threshold=token_similarity_threshold,
        semantic_threshold=semantic_similarity_threshold,
        manifest_verified=manifest_verified,
    )
