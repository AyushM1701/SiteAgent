"""Agent package."""
from agent.config import ModelRuntimeConfig

__all__ = [
    "AgentModelRunner",
    "MockAgentEngine",
    "ModelRuntimeConfig",
    "run_agent_on_example",
    "run_site_agent_on_example",
    "auto_scaffold_section",
    "rewrite_fallback_sections",
    "parse_agent_output",
    "WriteSiteAction",
    "sanitize_css_for_spec",
    "execute_test_suite",
    "scrub_think_blocks",
    "set_default_tokenizer",
    "register_tokenizer",
    "get_default_tokenizer",
    "ValidationResult",
    "InteractionValidationResult",
    "VisualValidationResult",
    "resolve_project_path",
]

def __getattr__(name: str):
    if name in __all__:
        import agent.agent as _agent
        if hasattr(_agent, name):
            val = getattr(_agent, name)
            globals()[name] = val
            return val
        import agent.agent_protocol as _protocol
        if hasattr(_protocol, name):
            val = getattr(_protocol, name)
            globals()[name] = val
            return val
        import agent.project_validator as _validator
        if hasattr(_validator, name):
            val = getattr(_validator, name)
            globals()[name] = val
            return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
