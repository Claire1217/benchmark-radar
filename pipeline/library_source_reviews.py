"""Apply source-reviewed Library task definitions and explicit evaluation roles."""
import copy
from taxonomy import normalize_taxonomy

def apply_source_reviews(records, payload):
    by_id={r['id']:r for r in records}
    for addition in payload.get('additions',[]):
        if addition['id'] in by_id:
            raise ValueError('Reviewed addition collides with existing ID: '+addition['id'])
        row=copy.deepcopy(addition);row.update(normalize_taxonomy(row));records.append(row);by_id[row['id']]=row
    for review in payload.get('reviews',[]):
        row=by_id[review['id']]
        if not review.get('sources') or not review.get('directions'):
            raise ValueError('Source review requires evidence and task directions')
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
            if review['parentId'] not in by_id: raise ValueError('Missing parent benchmark')
            row['benchmarkParentId']=review['parentId']
    # Resource-only reviews do not change task taxonomy or release dates.
    for review in payload.get('resourceReviews', []):
        row = by_id[review['id']]
        if review.get('kind') not in {'data', 'code'} or not review.get('sources'):
            raise ValueError('Resource review requires a data/code link and evidence')
        url = review.get('url', '')
        if not url.startswith('https://') or url not in review['sources']:
            raise ValueError('Reviewed resource URL must be an HTTPS evidence source')
        row.setdefault('links', {})[review['kind']] = url
        row.setdefault('resourceProvenance', {})[review['kind']] = copy.deepcopy(review)
    for pending in payload.get('pending', []):
        row = by_id[pending['id']]
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
