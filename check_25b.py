import json
o = json.load(open('search_evaluation_output.json'))
for e in o.get('entries', []):
    if e['query_id'] == 'EVAL-C025':
        res = e.get('actual_results', [])
        print([r.get('conversation_title') for r in res])
