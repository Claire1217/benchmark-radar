"""Apply source-reviewed Library task definitions and explicit evaluation roles."""
import copy
from library_release_dates import _resolve
from taxonomy import normalize_taxonomy

def apply_source_reviews(records, payload, redirects=None):
    """Apply reviews; return review ids that no longer resolve to any record.

    A newly admitted Radar record can absorb a reviewed catalog row of the same
    name, so reviewed ids follow the merge redirects. A review with no surviving
    target is reported, not fatal, so one stale review cannot block the publish.
    """
    redirects=redirects or {}
    by_id={r['id']:r for r in records}
    orphaned=[]
    def target(identity):
        resolved=_resolve(identity,by_id,redirects)
        if resolved is None: orphaned.append(identity)
        return by_id.get(resolved)
    for addition in payload.get('additions',[]):
        if addition['id'] in by_id:
            raise ValueError('Reviewed addition collides with existing ID: '+addition['id'])
        row=copy.deepcopy(addition);row.update(normalize_taxonomy(row));records.append(row);by_id[row['id']]=row
    for review in payload.get('reviews',[]):
        if not review.get('sources') or not review.get('directions'):
            raise ValueError('Source review requires evidence and task directions')
        row=target(review['id'])
        if row is None: continue
        row['taskReview']=copy.deepcopy(review)
        row['taskReview']['reviewedAt']=review.get('reviewedAt', payload['reviewedAt'])
        if review.get('displayName') and review['displayName'] != row['name']:
            row['aliases'] = list(dict.fromkeys([*row.get('aliases', []), row['name']]))
            row['name'] = review['displayName']
        if review.get('description'):
            row['previousDescription']=row.get('description')
            row['description']=row['oneLine']=review['description']
        row['descriptionProvenance']={'basis':'primary-source-reviewed','sources':review['sources'],'reviewedAt':review.get('reviewedAt', payload['reviewedAt'])}
        row['dataStatus']='primary-source-reviewed'
        row.setdefault('links',{})['project']=review['sources'][0]
        row['evaluationRole']=review['role']
        if review.get('parentId'):
            parent=target(review['parentId'])
            if parent is not None: row['benchmarkParentId']=parent['id']
    # Publisher reviews are independent of task and adoption classifications.
    for review in payload.get('publisherReviews', []):
        publishers = review.get('publishers', [])
        if not publishers or any(not p.get('name') or p.get('role') != 'benchmark-publisher'
                                 or not p.get('sourceUrl', '').startswith('https://') for p in publishers):
            raise ValueError('Publisher review requires names, publisher roles and HTTPS evidence')
        row = target(review['id'])
        if row is None: continue
        row['publishers'] = copy.deepcopy(publishers)
        row['publisherProvenance'] = {'basis': 'primary-source-reviewed',
                                     'reviewedAt': review.get('reviewedAt', payload['reviewedAt'])}
    # Resource-only reviews do not change task taxonomy or release dates.
    for review in payload.get('resourceReviews', []):
        if review.get('kind') not in {'data', 'code'} or not review.get('sources'):
            raise ValueError('Resource review requires a data/code link and evidence')
        url = review.get('url', '')
        if not url.startswith('https://') or url not in review['sources']:
            raise ValueError('Reviewed resource URL must be an HTTPS evidence source')
        row = target(review['id'])
        if row is None: continue
        row.setdefault('links', {})[review['kind']] = url
        row.setdefault('resourceProvenance', {})[review['kind']] = copy.deepcopy(review)
    for pending in payload.get('pending', []):
        row = target(pending['id'])
        if row is None: continue
        row['identityReviewNote'] = pending['note']
        if pending.get('description'):
            row['previousDescription'] = row.get('description')
            row['description'] = row['oneLine'] = pending['description']
            row['descriptionProvenance'] = {
                'basis': 'identity-unresolved',
                'sources': pending.get('sources', []),
                'reviewedAt': payload['reviewedAt'],
            }
    records.sort(key=lambda r:(r['name'].casefold(),r['id']))
    return list(dict.fromkeys(orphaned))
