import json
o = json.load(open('search_evaluation_output.json'))
ids = ['EVAL-C013', 'EVAL-C025', 'EVAL-C027']
for e in o.get('entries', []):
    if e['query_id'] in ids:
        pass_val = e.get('evaluation_pass')
        top = e.get('actual_results', [{}])[0].get('conversation_title', 'None')
        rank = e.get('matched_rank')
        print(f"ID: {e['query_id']} | Pass: {pass_val} | Top: {top} | Rank: {rank}")
