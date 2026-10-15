from agent.agent_protocol import close_complete_site_envelope, site_envelope_errors


def test_closes_tool_call_only_when_every_file_is_complete():
    complete_files = (
        '<tool_call name="write_site">'
        '<file path="src/components/Hero.tsx">export default function Hero() { return null; }</file>'
        '<file path="src/components/Hero.css">.hero { display: block; }</file>'
    )
    recovered = close_complete_site_envelope(complete_files)
    assert recovered.endswith("</tool_call>")
    assert site_envelope_errors(recovered) == []

    incomplete_css = complete_files[:-7]
    assert close_complete_site_envelope(incomplete_css) == incomplete_css
