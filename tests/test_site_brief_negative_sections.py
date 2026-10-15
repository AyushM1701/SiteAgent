from agent.site_brief import extract_sections_from_prompt


def test_negated_testimonials_do_not_create_section_and_architecture_is_retained():
    prompt = (
        "Build a SaaS landing page with a workflow architecture diagram and "
        "transparent pricing. Do not invent stock testimonials."
    )
    sections = extract_sections_from_prompt(prompt, "saas")
    assert "architecture" in sections
    assert "pricing" in sections
    assert "testimonials" not in sections
