"""One public Library registry, with explicit broad/narrow relationships.

Legacy labels remain internal evidence. They are never appended by the client
or used to choose a different membership rule after a URL reload.
"""
from research_directions import DIRECTIONS
from research_topics import TOPICS, ALIASES as TOPIC_ALIASES

VERSION = 'library-categories-v2'
RETIRED_IDS = {'data-analysis'}
# These are broader capabilities, not synonyms for the corresponding agent topic.
PARENTS = {
    'scientific-agents': 'ai-for-science',
    'coding-agents': 'software-engineering',
    'efficient-inference': 'systems-optimization',
    'image-video-generation': 'content-generation',
}
BROAD_NAMES = {
    'ai-for-science': ('Scientific Knowledge & Tasks', 'Scientific knowledge and reasoning, science questions, scientific figures, prediction and research tasks. Includes the narrower AI for Science agent-research category.'),
    'data-analysis': ('Data Analysis & SQL', 'Data analysis, database querying and tabular tasks, including Data Analysis Agents.'),
    'software-engineering': ('Programming & Software Engineering', 'Code understanding, generation, testing and repository-level software work, including Coding Agents.'),
    'systems-optimization': ('Systems & Performance', 'Software and system performance, including the narrower Efficient Inference research topic.'),
    'content-generation': ('Content Generation', 'Text, image, video and other generation tasks. Includes Image & Video Generation.'),
}
# Broad IDs retain their original scope. Only deprecated names redirect.
ALIASES = {key: value for key, value in TOPIC_ALIASES.items() if key not in BROAD_NAMES}


def definitions():
    topics = [{**topic, 'membership': 'researchTopics'} for topic in TOPICS]
    used = {topic['id'] for topic in topics}
    capabilities = []
    for direction in DIRECTIONS:
        identity = direction['id']
        if identity in used or identity in ALIASES or identity in RETIRED_IDS:
            continue
        definition = {**direction, 'section': 'General capabilities', 'membership': 'researchDirections'}
        if identity in BROAD_NAMES:
            definition['name'], definition['description'] = BROAD_NAMES[identity]
        if identity == 'ai-for-science':
            definition['searchAliases'] = ['science benchmarks', 'scientific knowledge']
        if identity == 'cybersecurity':
            definition['name'] = 'Cybersecurity Tasks'
            definition['searchAliases'] = ['Cybersecurity']
        if identity == 'gui-grounding':
            definition['section'] = 'Specific tasks'
            definition['description'] = 'Locate a requested interface element from a screenshot. This is a specific task, distinct from completing a computer-use workflow.'
        capabilities.append(definition)
    result = topics + capabilities
    for definition in result:
        if definition['id'] in PARENTS:
            definition['parentId'] = PARENTS[definition['id']]
    ids = {d['id'] for d in result}
    assert len(ids) == len(result)
    assert len({d['name'].casefold() for d in result}) == len(result)
    assert not ids.intersection(ALIASES), 'Canonical IDs cannot also be redirects'
    assert set(ALIASES.values()) <= ids
    return result


def annotate_categories(records):
    registry = definitions()
    order = [d['id'] for d in registry]
    for record in records:
        members = {d['id'] for d in registry if d['id'] in record.get(d['membership'], [])}
        # Broad category counts include each child entry once, even when both
        # the old capability evidence and the newer task review match it.
        members.update(PARENTS[identity] for identity in list(members) if identity in PARENTS)
        record['libraryCategories'] = [identity for identity in order if identity in members]


def category_manifest(records):
    visible = [r for r in records if r.get('displayEligible') is not False and r.get('evaluationMode') != 'viewpoint_probe']
    return {
        'version': VERSION,
        'retiredIds': sorted(RETIRED_IDS),
        'method': 'One membership list for navigation, search, chips, counts and URL filters. Categories overlap; parent categories include their children.',
        'aliases': ALIASES,
        'directions': [{**d, 'count': sum(d['id'] in r.get('libraryCategories', []) for r in visible)} for d in definitions()],
        'unclassifiedCount': sum(not r.get('libraryCategories') for r in visible),
    }
