import copy
import unittest
from pipeline.library_identity import merge_library_identities


class LibraryIdentityTests(unittest.TestCase):
    def test_reviewed_merge_retains_links_sources_and_saved_redirect(self):
        rows=[{'id':'a','name':'Alias','links':{'code':'https://example.org/code'},'catalogSources':[{'catalog':'one','url':'https://one.test'}]}, {'id':'b','name':'Canonical','links':{},'catalogSources':[{'catalog':'two','url':'https://two.test'}]}, {'id':'c','name':'Canonical 2.0','links':{}}]
        original=copy.deepcopy(rows)
        result, redirects=merge_library_identities(rows,{'merges':[{'fromId':'a','toId':'b'}]})
        self.assertEqual(rows,original)
        self.assertEqual(redirects,{'a':'b'})
        self.assertEqual({r['id']for r in result},{'b','c'})
        canonical=next(r for r in result if r['id']=='b')
        self.assertEqual(len(canonical['catalogSources']),2)
        self.assertIn('Alias',canonical['aliases'])
        self.assertEqual(canonical['links']['code'],'https://example.org/code')
        self.assertEqual(merge_library_identities(result,{'merges':[{'fromId':'a','toId':'b'}]}),(result,redirects))

    def test_identical_names_are_not_enough_to_merge(self):
        rows=[{'id':'a','name':'Same'},{'id':'b','name':'Same'}]
        self.assertEqual(len(merge_library_identities(rows,{})[0]),2)

    def test_missing_target_fails_without_losing_records(self):
        with self.assertRaises(ValueError):
            merge_library_identities([{'id':'a','name':'A'}],{'merges':[{'fromId':'a','toId':'missing'}]})
