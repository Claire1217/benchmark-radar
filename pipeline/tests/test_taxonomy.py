import unittest

from pipeline.taxonomy import normalize_taxonomy


class TaxonomyTests(unittest.TestCase):
    def test_general_ai_is_scope_not_application_domain(self):
        result = normalize_taxonomy({"area": "Code & Software", "primaryDomain": "General AI", "applicationDomains": ["General AI"]})
        self.assertEqual(result["capabilityGroups"], ["Coding & Software Engineering"])
        self.assertEqual(result["applicationDomains"], [])
        self.assertEqual(result["domainScope"], "general")

    def test_mathematics_labels_merge_into_one_capability(self):
        result = normalize_taxonomy({"area": "Language & Knowledge", "primaryDomain": "Mathematics & Formal Science", "applicationDomains": ["Mathematics & Formal Science"]})
        self.assertEqual(result["capabilityGroups"], ["Mathematics & Formal Sciences"])
        self.assertEqual(result["applicationDomains"], [])

    def test_application_domains_are_merged_without_losing_capability(self):
        result = normalize_taxonomy({"area": "Robotics & Embodied AI", "primaryDomain": "Manufacturing & Process Control", "applicationDomains": ["Manufacturing & Process Control"]})
        self.assertEqual(result["capabilityGroups"], ["Robotics & Embodied Intelligence"])
        self.assertEqual(result["applicationDomains"], ["Industrial & Engineering"])
        self.assertEqual(result["domainScope"], "specific")

    def test_tool_calling_can_coexist_with_agents(self):
        result = normalize_taxonomy({"area": "Agents & Tool Use", "primaryDomain": "General AI", "capabilities": ["Tool use"]})
        self.assertEqual(result["capabilityGroups"], ["Agents", "Tool Calling"])


if __name__ == "__main__":
    unittest.main()
