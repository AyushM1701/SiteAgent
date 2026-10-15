from agent.agent_protocol import parse_agent_output, site_envelope_errors


def test_write_site_accepts_file_name_attribute():
    response = '''<tool_call name="write_site">
<file name="src/components/Header.tsx">export default function Header() { return <header>Hi</header>; }</file>
<file name="src/components/Header.css">header { color: white; }</file>
</tool_call>'''
    action = parse_agent_output(response).action
    assert site_envelope_errors(response) == []
    assert [path for path, _ in action.files] == [
        "src/components/Header.tsx",
        "src/components/Header.css",
    ]
