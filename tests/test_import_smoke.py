"""
tests/test_import_smoke.py - Automated Smoke Import Test Suite.

Verifies that core agent, server, evaluation, and data pipeline modules can be imported
in clean execution environments without missing dependencies or circular import errors.
Enforces P0-01 self-containment guarantees.
"""

import importlib
import pytest


SMOKE_MODULES = [
    "agent.stock_photos",
    "agent.site_brief",
    "agent.agent",
    "agent.agent_protocol",
    "agent.design_plan",
    "agent.site_file_normalizer",
    "agent.tailwind_support",
    "agent.ecommerce_repair",
    "agent.visual_judge",
    "agent.style_ingest",
    "server.app",
    "evaluation.motion_benchmark",
    "data_pipeline.build_dataset",
    "data_pipeline.curate_dataset",
    "data_pipeline.generate_trajectories",
]


@pytest.mark.parametrize("mod_name", SMOKE_MODULES)
def test_smoke_import_module(mod_name: str):
    """Smoke test importing each essential pipeline module."""
    mod = importlib.import_module(mod_name)
    assert mod is not None, f"Module {mod_name} imported as None"


def test_site_brief_stock_photos_bindings():
    """Explicitly verify agent.site_brief has access to agent.stock_photos symbols."""
    import agent.site_brief as sb
    assert hasattr(sb, "resolve_site_images"), "agent.site_brief missing resolve_site_images"
    assert hasattr(sb, "fetch_single_image"), "agent.site_brief missing fetch_single_image"
    assert hasattr(sb, "_resolve_curated_stock_photo"), "agent.site_brief missing _resolve_curated_stock_photo"
    assert hasattr(sb, "_STOCK_PHOTO_CURATED_CATALOG"), "agent.site_brief missing _STOCK_PHOTO_CURATED_CATALOG"
