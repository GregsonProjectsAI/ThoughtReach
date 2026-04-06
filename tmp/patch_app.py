import re

def main():
    with open('ui/app.js', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update processAndRenderResults
    old_proc = """    function processAndRenderResults() {
        if (!currentSearchResults.length) return;

        const displayMode = document.getElementById('result-display-select').value;
        const sortMode = document.getElementById('result-sort-select').value;
        const searchSummary = document.getElementById('search-summary');
        const searchHint = document.getElementById('search-refinement-hint');
        const headerRow = document.getElementById('results-header-row');

        if (headerRow) headerRow.classList.remove('hidden');

        // 1. Filter (Deduplicate / Top Match)
        let processed = [...currentSearchResults];
        if (displayMode === 'top') {
            const seen = new Set();
            processed = processed.filter(r => {
                if (seen.has(r.conversation_id)) return false;
                seen.add(r.conversation_id);
                return true;
            });
        }"""
        
    new_proc = """    function processAndRenderResults() {
        if (!currentSearchResults.length) return;

        const displayMode = document.getElementById('result-display-select').value;
        const sortMode = document.getElementById('result-sort-select').value;
        const searchSummary = document.getElementById('search-summary');
        const searchHint = document.getElementById('search-refinement-hint');
        const headerRow = document.getElementById('results-header-row');

        if (headerRow) headerRow.classList.remove('hidden');

        let rawResults = [...currentSearchResults];

        // Group by conversation
        const convMap = new Map();
        rawResults.forEach(res => {
            if (!convMap.has(res.conversation_id)) {
                convMap.set(res.conversation_id, {
                    conversation_id: res.conversation_id,
                    conversation_title: res.conversation_title,
                    conversation_summary: res.conversation_summary,
                    conversation_source_type: res.conversation_source_type,
                    category_id: res.category_id,
                    category_name: res.category_name,
                    imported_at: res.imported_at,
                    max_score: 0,
                    excerpts: []
                });
            }
            
            const group = convMap.get(res.conversation_id);
            group.max_score = Math.max(group.max_score, res.similarity_score);
            
            let merged = false;
            for (let i = 0; i < group.excerpts.length; i++) {
                const ext = group.excerpts[i];
                if (res.message_start_index <= ext.message_end_index + 1 && res.message_end_index >= ext.message_start_index - 1) {
                    ext.message_start_index = Math.min(ext.message_start_index, res.message_start_index);
                    ext.message_end_index = Math.max(ext.message_end_index, res.message_end_index);
                    
                    if (res.matched_chunk_text && (!ext.matched_chunk_text || !ext.matched_chunk_text.includes(res.matched_chunk_text.substring(0, 40)))) {
                        ext.matched_chunk_text += '\\n\\n' + res.matched_chunk_text;
                    }
                    ext.similarity_score = Math.max(ext.similarity_score, res.similarity_score);
                    merged = true;
                    break;
                }
            }
            if (!merged && group.excerpts.length < 3) {
                 group.excerpts.push(JSON.parse(JSON.stringify(res))); 
            }
        });
        
        let processedGroups = Array.from(convMap.values());
        processedGroups.forEach(grp => {
            grp.excerpts.sort((a, b) => a.message_start_index - b.message_start_index);
            grp.similarity_score = grp.max_score; // Map for backend sorting compatibility
        });

        if (displayMode === 'top') {
            const seen = new Set();
            processedGroups = processedGroups.filter(r => {
                if (seen.has(r.conversation_id)) return false;
                seen.add(r.conversation_id);
                return true;
            });
        }
        
        let processed = processedGroups;"""

    if old_proc not in content:
        print("FAILED TO MATCH PROC!")
    else:
        content = content.replace(old_proc, new_proc)

    with open('ui/app.js', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    main()
