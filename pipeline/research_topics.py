"""Shared editorial topics and benchmark-native task facets, with traceable evidence.

All records are processed, but incomplete metadata stays explicitly unresolved.
No claim of semantic/full-paper verification is made by the automatic rules.
"""
from pathlib import Path
import hashlib,json,re,copy
ROOT=Path(__file__).resolve().parents[1]
VERSION='research-topics-v3'
CONFIG=json.loads((ROOT/'data/research_topics.json').read_text())
TOPICS=CONFIG['topics']
RULES=json.loads((ROOT/'data/research_topic_rules.json').read_text())
REVIEWS=json.loads((ROOT/'data/research_topic_reviews.json').read_text())
ALIASES={'self-improvement-rsi':'self-improving-agents','deep-research':'search-research','ai-for-science':'scientific-agents','ai-scientist':'scientific-agents','ai-r-d':'ai-research-agents','data-analysis':'data-analysis-agents','embodied-ai':'embodied-vla','audio-speech':'realtime-multimodal','systems-optimization':'efficient-inference','content-generation':'image-video-generation'}
# Legacy broad labels remain available as Library filters, not silently remapped to narrower topics.
FACETS={
 'tasks':{
  'Software development':r'code generation|code editing|software engineering|bug.fix|repository.level|codebase|refactoring|program synthesis',
  'Terminal operations':r'terminal|command.line|system administration|devops',
  'Computer operation':r'computer.use|gui agents?|desktop tasks|mobile agents?|web navigation|cross.app',
  'GUI grounding':r'gui grounding|screen(?:shot)? grounding|element (?:grounding|localization)|locating.*interface',
  'Search and retrieval':r'retrieval|web search|information gathering|web.browsing|search agents?',
  'Research synthesis':r'deep research|literature review|evidence synthesis|research.agent|research reports?',
  'Tool calling':r'tool.call|function.call|api (?:calls?|calling)|tool.use|tool selection',
  'Data analysis':r'data (?:analysis|science)|spreadsheet|statistical analysis|tabular|database|sql',
  'AI research and engineering':r'machine.learning (?:research|engineering|methods)|ml research|training algorithms|hyperparameter|kaggle|algorithmic design',
  'Scientific research':r'scientific (?:research|discovery|computing)|experimental design|computational (?:biology|chemistry)|bioinformatics',
  'Question answering':r'question.answer|\bqa\b|multiple.choice|knowledge questions',
  'Mathematical problem solving':r'mathematical|theorem|formal proof|olympiad|algebra',
  'Language understanding':r'language understanding|commonsense|coreference|linguistic',
  'Translation':r'translation|cross.lingual',
  'Document parsing':r'\bocr\b|document parsing|text recognition|reading order|table extraction',
  'Document understanding':r'document understanding|document question|chart understanding|infographic',
  'Visual understanding':r'image understanding|visual question|visual perception|visual reasoning|object detection',
  'Video understanding':r'video (?:understanding|reasoning|comprehension|question)|temporal grounding',
  'Speech and audio':r'speech|audio|spoken|acoustic|sound recognition',
  'Image and video generation':r'image (?:generation|editing)|video (?:generation|editing)|text.to.image|text.to.video',
  'World modeling':r'world.model|action.conditioned.*prediction|physical consistency',
  'Robot control':r'robotic|robot manipulation|embodied|vision.language.action|locomotion',
  'Cybersecurity':r'cybersecurity|cyber|vulnerability|exploit|capture.the.flag|\bctf\b',
  'Systems efficiency':r'inference (?:latency|throughput|efficiency)|quantization|gpu kernel|kernel optimization|kv.cache',
  'Agent development':r'harness|agent construction|reusable skills|skill learning',
  'Professional workflows':r'office|enterprise|customer.service|customer support|business workflow|professional task',
  'Evaluation and judging':r'judge|judging|evaluation metric|calibration|rubric quality'
 },
 'capabilities':{
  'Planning':r'planning|plan generation|orchestration',
  'Long-horizon execution':r'long.horizon|multi.step|multi.turn|multi.day',
  'Persistent memory':r'agent memory|persistent memory|long.term memory|longitudinal memory|relational memory|memory polic|cross.session.*memory',
  'Long-context understanding':r'long.context|long.document|context length|multi.document',
  'Personalization':r'personaliz|user preferences|user history',
  'Grounding':r'grounding|localization',
  'Instruction following':r'instruction.following|constraint satisfaction|format compliance|structured output',
  'Logical reasoning':r'logical reasoning|deduct|inductive|commonsense',
  'Causal reasoning':r'causal|counterfactual|intervention',
  'Spatial reasoning':r'spatial|3d reasoning|geometry consistency',
  'Coordination':r'collaboration|coordination|negotiation|inter.agent',
  'Learning and adaptation':r'self.improv|self.evol|continual learning|learning across episodes|skill learning',
  'Recovery':r'failure recovery|error recovery|recover.*fail|environment repair',
  'Safety and permissions':r'safety|permission|prompt injection|privacy|unsafe|authorization',
  'Reliability':r'robustness|reliability|failure detection|honesty|hallucination',
  'Verification':r'verification|verifier|fact.check|source verification'
 },
 'environments':{'Terminal':r'terminal|command.line|cli','Repository':r'repository|codebase|github issue','Web':r'web|browser','Desktop':r'desktop|windows|ubuntu|macos','Mobile':r'mobile|android|ios|smartphone','API':r'api|mcp|function.call','Simulator':r'simulator|simulation|simulated','Physical robot':r'real.robot|physical robot|real.world robot','Notebook':r'notebook|jupyter','Spreadsheet':r'spreadsheet|workbook'},
 'modalities':{'Image':r'image|screenshot|visual|photograph','Video':r'video|movie|film|clips','Audio':r'audio|speech|acoustic|sound','Text':r'text|language|document|question|dialogue','Code':r'code|program|repository|sql|kernel','Structured data':r'tabular|spreadsheet|database|structured data','3D':r'3d|point cloud|mesh','Action':r'action sequences|robot control|motor|actuation'},
 'protocols':{'Interactive execution':r'interactive|execution.based|executable tasks|agent scaffold|multi.turn','Static answers':r'multiple.choice|question.answer|\bqa\b|classification','Outcome verification':r'unit tests|verifier|executable tests|test cases|state verification','Trajectory evaluation':r'trajector|process.level|step.level','Cross-session':r'cross.session|multi.session|longitudinal|multi.day','Learning across episodes':r'held.out.*improv|retained experience|learning across|self.evolution','Human judgment':r'human.annotated|human evaluation|human judgment','Model judgment':r'llm.as.judge|mllm judg|judge model|rubric.based'}
}

def match(pattern,text):
    # Prevent substring hits (GUI inside paralinguistic) and arbitrary cross-sentence evidence.
    return re.search(r'(?<!\w)(?:'+pattern.replace('.*','[^.\\n]{0,180}')+r')(?!\w)',text,re.I)

def source(record):
    p=record.get('descriptionProvenance') or {}
    return p.get('sourceUrl') or next(iter(p.get('sources') or []),None) or (record.get('links') or {}).get('report')

def evidence(pattern,text,record):
    m=match(pattern,text)
    if not m:return None
    return {'basis':'task-description-rule','excerpt':text[max(0,m.start()-45):m.end()+90], 'sourceUrl':source(record)}

def annotate_topics(records):
    for r in records:
        text=(r.get('description') or r.get('oneLine') or '').strip()
        original=copy.deepcopy({k:r.get(k) for k in ('topics','capabilities','capabilityGroups','applicationDomains','industrySectors','construction','annotation','readiness','area')})
        values={};proof={}
        for axis,patterns in FACETS.items():
            proof[axis]={k:e for k,pat in patterns.items() if (e:=evidence(pat,text,r))};values[axis]=list(proof[axis])
        topics={k:e for k,pat in RULES.items() if (e:=evidence(pat,text,r))}
        # Concrete object/target guards. Names of methods, source corpora and solver pipelines are not targets.
        if match(r'(?:self.evolving|self.updating|self.improving) (?:safety |software.security )?benchmark|benchmark.*(?:self.evolving|self.updating)',text) and not match(r'evaluat\w*.*(?:self.evolving agents|agent self.evolution)',text):
            topics.pop('self-improving-agents',None);proof['capabilities'].pop('Learning and adaptation',None);proof['protocols'].pop('Learning across episodes',None)
        if match(r'multi.agent (?:pipeline|system.*baseline)|built by a multi.agent|we (?:further )?propose.*multi.agent',text) and not match(r'evaluat\w* (?:multi.agent (?:collaboration|coordination|systems)|agent coordination)',text):topics.pop('multi-agent',None)
        if match(r'remote sensing|land.cover|user preferences in head.to.head|failure detection across sessions',text):topics.pop('agent-memory',None);proof['capabilities'].pop('Persistent memory',None)
        if match(r'world.model',text) and match(r'language world models|gui world models|simulate agentic environments',text):topics.pop('world-models',None)
        if match(r'paper only|catalog.listed benchmark; original.source verification|no official.*documentation|not.*defined.*benchmark protocol',text):topics={}
        review=REVIEWS.get(r.get('id'));review_state=None
        if review:
            if review.get('descriptionHash')==hashlib.sha256(text.encode()).hexdigest():
                review_state='applied'
                for k in review.get('remove',[]):topics.pop(k,None)
                for k in review.get('add',[]):topics[k]={'basis':'task-description-reviewed','excerpt':review['reason'],'sourceUrl':source(r),'reviewedAt':review['reviewedAt']}
            else:review_state='stale-review-needs-revalidation'
        # Source-reviewed task directions are authoritative for sparse catalog entries.
        trusted=r.get('taskReview') or {}
        to_topic={'coding-agents':'coding-agents','computer-use':'computer-use','gui-grounding':'computer-use','agent-memory':'agent-memory','deep-research':'search-research','multi-agent':'multi-agent','tool-use':'tool-use','data-analysis':'data-analysis-agents'}
        for d in trusted.get('directions',[]):
            if d in to_topic:topics[to_topic[d]]={'basis':'primary-source-reviewed','excerpt':trusted.get('note') or text,'sourceUrl':next(iter(trusted.get('sources') or []),None)}
        # Keep legacy metadata available but separate from the independently derived task attributes.
        r['benchmarkTaxonomy']={'version':VERSION,'sourceLabels':original,**{axis:list(p) for axis,p in proof.items()},'evidence':proof,'evaluationRole':r.get('evaluationRole') or r.get('recordType') or 'unspecified','status':'supported-description' if any(proof.values()) else 'needs-source-review','sourceUrl':source(r)}
        r['researchTopics']=[t['id'] for t in TOPICS if t['id'] in topics]
        r['researchTopicEvidence']={k:topics[k] for k in r['researchTopics']}
        flags=[]
        if not text or len(text)<65:flags.append('sparse-task-description')
        if not r['researchTopics']:flags.append('no-supported-featured-topic')
        if r.get('dataStatus')=='catalog-listed-unverified':flags.append('catalog-source-unverified')
        if review_state=='stale-review-needs-revalidation':flags.append(review_state)
        if r.get('identityReviewNote'):flags.append('identity-review-pending')
        r['topicClassification']={'version':VERSION,'status':'supported' if topics else 'unresolved-or-outside-featured-topics','method':'task-description rules plus source/hash-bound reviews','reviewFlags':flags,'reviewState':review_state}

def topic_manifest(records):
    visible=[r for r in records if r.get('displayEligible') is not False and r.get('evaluationMode')!='viewpoint_probe']
    return {'version':VERSION,'method':'Editorial discovery topics; evidence-backed description classification, not full-paper verification. Topics overlap. Native metadata is preserved separately.','aliases':ALIASES,'directions':[{**t,'count':sum(t['id'] in r.get('researchTopics',[]) for r in visible)} for t in TOPICS],'unclassifiedCount':sum(not r.get('researchTopics') for r in visible)}
