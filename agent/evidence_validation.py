"""Canonical binary truth-gate evidence model, separate from quality scores."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal

GateStatus = Literal["passed", "failed", "unverified", "not_requested"]


@dataclass
class GateEvidence:
    status: GateStatus
    checks_run: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    evidence: List[dict] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status in {"passed", "not_requested"}


@dataclass
class ProjectValidation:
    typecheck: GateEvidence
    build: GateEvidence
    lint: GateEvidence
    contract: GateEvidence
    accessibility: GateEvidence
    motion: GateEvidence
    three_d: GateEvidence
    runtime: GateEvidence
    interaction: GateEvidence
    preview: GateEvidence

    @property
    def passed(self) -> bool:
        return all(gate.passed for gate in (
            self.typecheck, self.build, self.lint, self.contract,
            self.accessibility, self.motion, self.three_d, self.runtime,
            self.interaction, self.preview,
        ))

    def to_dict(self) -> Dict[str, dict]:
        return {name: {"status": gate.status, "checks_run": gate.checks_run,
                       "errors": gate.errors, "warnings": gate.warnings,
                       "evidence": gate.evidence}
                for name, gate in self.__dict__.items()}


def validate_interaction_evidence(requirements: list, runner) -> GateEvidence:
    """Run explicit interaction requirements and preserve before/after evidence."""
    evidence, errors = [], []
    for req in requirements:
        try:
            locator = runner.locator(req.selector)
            locator.wait_for(state="visible", timeout=2_000)
            before = req.read_state(runner, locator)
            req.perform(runner, locator)
            after = req.read_state(runner, locator)
            passed = bool(req.assertion(before, after))
            evidence.append({"id": req.id, "selector": req.selector, "before": before, "after": after, "passed": passed})
            if not passed:
                errors.append(f"[Interaction Error] {req.id}: expected state transition was not observed.")
        except Exception as exc:
            errors.append(f"[Interaction Error] {req.id}: {type(exc).__name__}: {exc}")
    if not requirements:
        status: GateStatus = "not_requested"
    elif len(evidence) == len(requirements) and not errors:
        status = "passed"
    else:
        status = "failed"
    return GateEvidence(status=status, checks_run=len(evidence), errors=errors, evidence=evidence)


def validate_interactions(page, requirements) -> GateEvidence:
    """Public page-first API matching the browser validation contract."""
    return validate_interaction_evidence(requirements, page)
