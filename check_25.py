import json
o = json.load(open('search_evaluation_output.json'))
for e in o.get('entries', []):
    if e['query_id'] == 'EVAL-C025':
        top = e.get('actual_results', [{}])[0].get('conversation_title', 'None')
        rank = e.get('matched_rank')
        print(f"Top 1: {top} | Found at rank: {rank}")
