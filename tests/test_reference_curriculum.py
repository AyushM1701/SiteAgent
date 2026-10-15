import json
import re
import unittest
from unittest.mock import patch

from data_pipeline import build_reference_curriculum as curriculum
from data_pipeline.prepare_quality_training import group_families
from agent.agent_protocol import WriteSiteAction, parse_agent_output


class ReferenceCurriculumTests(unittest.TestCase):
    def test_heading_gate_does_not_misclassify_descendant_captions(self):
        from agent.style_ingest import StyleSpec, validate_css_conformance
        spec = StyleSpec(name='test', colors={'--ink':'#000'})
        self.assertFalse(validate_css_conformance('.section-title>p{font-size:14px}.chart-title span{font-size:8px}', spec))
        self.assertTrue(validate_css_conformance('h2{font-size:8px}', spec))

    def test_color_tokens_follow_runtime_style_gate(self):
        from agent.style_ingest import StyleSpec, validate_css_conformance
        for site, spec in curriculum.SITES.items():
            declared = set(re.findall(r'(--[\w-]+):', spec['tokens']))
            for path in (curriculum.DATA/'source'/site).glob('*.css'):
                css = path.read_text(encoding='utf-8')
                self.assertFalse(validate_css_conformance(css, StyleSpec(name=site, colors={'--paper':'#ffffff'})), path.name)
                self.assertTrue(set(re.findall(r'var\((--[\w-]+)', css)) <= declared, path.name)

    def test_explicit_families_remain_together_despite_different_sections(self):
        rows = [
            {'task_id': str(i), 'family_id': family, 'messages': [
                {'role': 'user', 'content': str(i)},
                {'role': 'assistant', 'content': str(i)}]}
            for i, family in enumerate(['site-a', 'site-b', 'site-a'])
        ]
        families = group_families(rows)
        self.assertEqual(families[0], families[2])
        self.assertNotEqual(families[0], families[1])

    def test_stale_visual_evidence_blocks_publication(self):
        with patch.object(curriculum, 'source_hash', return_value='modified-source'):
            with self.assertRaisesRegex(ValueError, 'stale verification'):
                curriculum.publish()

    def test_complete_targets_and_current_source_evidence(self):
        rows = [json.loads(line) for line in (curriculum.DATA / 'train.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual(len(rows), 21)
        self.assertEqual(len({r['family_id'] for r in rows}), 3)
        for row in rows:
            self.assertLessEqual(row['token_count'], 8192)
            self.assertLessEqual(row['target_tokens'], 4096)
            action = parse_agent_output(row['messages'][-1]['content']).action
            self.assertIsInstance(action, WriteSiteAction)
            self.assertEqual(len(action.files), 2)
            site = row['source_task_id'].removeprefix('reference_')
            self.assertEqual(row['provenance']['source_sha256'], curriculum.source_hash(site))
            for filename, content in action.files:
                expected = (curriculum.DATA / 'source' / site / filename.split('/')[-1]).read_text(encoding='utf-8')
                self.assertEqual(content.strip(), expected.strip())


if __name__ == '__main__':
    unittest.main()
