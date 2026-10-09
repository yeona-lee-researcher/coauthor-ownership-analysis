"""Replay invariants: character provenance and episode classification on a synthetic log."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from process_logs import apply_delta, replay


def event(n, name, src, t, delta='', sugg=()):
    return dict(eventNum=n, eventName=name, eventSource=src, eventTimestamp=t, textDelta=delta,
                currentDoc='Prompt.' if name == 'system-initialize' else '', currentSuggestions=list(sugg))


def ins(pos, text):
    return {'ops': [{'retain': pos}, {'insert': text}]} if pos else {'ops': [{'insert': text}]}


def dele(pos, n):
    return {'ops': [{'retain': pos}, {'delete': n}]}


class Provenance(unittest.TestCase):
    def test_delete_of_ai_text_is_counted(self):
        c = dict(u_ins=0, a_ins=0, u_del=0, a_del_by_u=0)
        labels = apply_delta(list('pp'), ins(2, 'abc')['ops'], 'a', c)
        labels = apply_delta(labels, dele(3, 2)['ops'], 'u', c)
        self.assertEqual(labels, list('ppa'))
        self.assertEqual((c['a_ins'], c['u_del'], c['a_del_by_u']), (3, 2, 2))


class Episodes(unittest.TestCase):
    def setUp(self):
        s = [{'index': 0, 'trimmed': 'x', 'original': 'x'}]
        evs = [event(0, 'system-initialize', 'api', 0),
               event(1, 'text-insert', 'user', 1000, ins(7, 'Hi')),           # W
               event(2, 'suggestion-get', 'user', 1500),                      # QA
               event(3, 'suggestion-open', 'api', 3500, sugg=s * 5),
               event(4, 'suggestion-select', 'user', 4000),
               event(5, 'suggestion-close', 'api', 4001),
               event(6, 'text-insert', 'api', 4002, ins(9, 'AI')),
               event(7, 'text-insert', 'user', 30000, ins(11, '!')),         # P (>=10 s) then W
               event(8, 'suggestion-get', 'user', 31000),                     # QN: writer resumes first
               event(9, 'text-insert', 'user', 32000, ins(12, '?')),         # W
               event(10, 'suggestion-get', 'user', 33000),                    # QR: dismissed
               event(11, 'suggestion-open', 'api', 35000, sugg=s * 3),
               event(12, 'suggestion-close', 'user', 36000),
               event(13, 'text-delete', 'user', 37000, dele(9, 2))]          # W deleting AI text
        self.tmp = tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False, encoding='utf-8')
        self.tmp.write('\n'.join(json.dumps(e) for e in evs)); self.tmp.close()

    def tearDown(self):
        Path(self.tmp.name).unlink()

    def test_tokens_and_counts(self):
        labels, c, eps, t0, t_end = replay(Path(self.tmp.name), pause=10)
        self.assertEqual([e['token'] for e in eps], ['W', 'QA', 'P', 'W', 'QN', 'W', 'QR', 'W'])
        self.assertEqual(eps[1]['a_ins'], 2)
        self.assertAlmostEqual(eps[1]['latency'], 2.0)
        self.assertEqual((c['u_ins'], c['a_ins'], c['a_del_by_u']), (4, 2, 2))
        self.assertEqual(labels.count('a'), 0)
        self.assertEqual(eps[-1]['a_del'], 2)

    def test_late_display_marks_unanswered_request(self):
        evs = [json.loads(l) for l in open(self.tmp.name, encoding='utf-8')]
        evs.insert(10, event(9.5, 'suggestion-open', 'api', 32500, sugg=[{'index': 0}]))  # arrives after resuming
        evs.insert(11, event(9.6, 'suggestion-select', 'user', 32600))
        evs.insert(12, event(9.7, 'text-insert', 'api', 32601, ins(13, 'Z')))
        Path(self.tmp.name).write_text('\n'.join(json.dumps(e) for e in evs), encoding='utf-8')
        _, c, eps, _, _ = replay(Path(self.tmp.name), pause=10)
        qn = [e for e in eps if e['token'] == 'QN'][0]
        self.assertTrue(qn.get('answered_late'))
        late = [e for e in eps if e.get('origin') == 'late'][0]
        self.assertEqual((late['token'], late['a_ins']), ('QA', 1))
        self.assertEqual(c['a_ins'], sum(e.get('a_ins', 0) for e in eps))


if __name__ == '__main__':
    unittest.main()
