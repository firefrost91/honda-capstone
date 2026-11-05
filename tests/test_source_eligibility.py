import json
import unittest
from rag.config import EVAL_DIR
from rag.corpus import load_document_catalog, load_passages


class EligibilityTests(unittest.TestCase):
    def test_ineligible_documents_do_not_enter_the_index(self):
        catalog = load_document_catalog()
        passages = load_passages()
        blocked = {sid for sid, doc in catalog.items() if doc.get('index_eligible') is False}
        self.assertIn('proj_np37_hilliard_construction_update', blocked)
        self.assertTrue(blocked.isdisjoint(p.source_id for p in passages))
        self.assertTrue(any(p.kind == 'data_card' for p in passages))

    def test_expected_sources_have_retrievable_text(self):
        ids = {p.source_id for p in load_passages() if p.kind == 'chunk'}
        questions = json.loads((EVAL_DIR/'stakeholder_questions.json').read_text())['questions']
        self.assertEqual(len(questions), 34)
        for q in questions:
            self.assertTrue(q['expected_sources'])
            for prefix in q['expected_sources']:
                self.assertTrue(any(s.startswith(prefix) for s in ids), (q['id'], prefix))
