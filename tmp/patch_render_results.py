import re

def main():
    with open('ui/app.js', 'r', encoding='utf-8') as f:
        content = f.read()

    # We want to replace `function renderResults(results) { ... }` up to where `card.querySelector('.library-nav-btn').addEventListener...` ends.
    # Because `renderResults` is huge, I will use regular expressions or string index matching.

    start_str = "    function renderResults(results) {"
    
    # We must find the end of `renderResults`. It ends after `resultsContainer.appendChild(card);`
    # and `        });` and `    }`
    end_str = """        });\n    }\n\n    function expandCard(card) {"""
    
    start_idx = content.find(start_str)
    end_idx = content.find(end_str)
    
    if start_idx == -1 or end_idx == -1:
        print("COULD NOT FIND START OR END!")
        return
        
    old_block = content[start_idx:end_idx + len("""        });\n    }""")]
    
    new_block = """    function renderResults(groups) {
        resultsContainer.innerHTML = '';
        groups.forEach(group => {
            const structured = isStructuredConversation(group);

            const card = document.createElement('div');
            // We use group.visited? We don't have visited on group but the first time it expands we can mark the group visited?
            // Actually, we'll track visited on the group itself in session states later or just keep it simple.
            card.className = 'result-card'; 

            const scorePercent = Math.round(group.max_score * 100) + '%';
            const categoryBadgeHtml = group.category_name
                ? `<span class="badge category">${escapeHTML(group.category_name)}</span>`
                : '';
                
            const importDateStr = formatLibraryDate(group.imported_at);
            const sourceBadgeCls = structured ? 'library-type-structured' : 'library-type-raw';
            const sourceBadgeText = structured ? 'Structured Conversation' : 'Raw Imported Text';
            const projectName = group.category_name || 'Uncategorised';
            const provenanceLabel = structured
                ? '<span class="provenance-label">Structured Conversation</span>'
                : '<span class="provenance-label">Imported Text</span>';

            const contextTypeLabel = structured ? 'Surrounding Context' : 'Surrounding Text';
            const contextInitBadge = structured ? 'Showing ±10 lines' : 'Showing ±3 paragraphs';

            const expandControlsTop = structured
                ? ''
                : `<div class="context-controls-top">
                       <button class="ctx-expand-btn prev-para-btn">Previous Paragraph</button>
                   </div>`;

            const expandControlsBottom = structured
                ? `<button class="ctx-expand-btn" data-radius="25">±25 lines</button>
                   <button class="ctx-expand-btn" data-radius="50">±50 lines</button>
                   <button class="full-conv-btn">Show Full Thread</button>`
                : `<button class="ctx-expand-btn next-para-btn">Next Paragraph</button>
                   <button class="full-conv-btn">Show Full Text</button>`;

            // Master Expand Button handler toggles all excerpts
            let isExpanded = false;
            
            // Build the card HTML
            let excerptsHtml = group.excerpts.map((result, idx) => {
                const fullText = result.matched_chunk_text || '';
                let rawMatchedParaText = fullText;
                if (!structured) {
                    const surroundings = result.surrounding_messages || [];
                    const matchedMsg = surroundings.find(m => m.position === 0);
                    if (matchedMsg && matchedMsg.content && matchedMsg.content.trim()) {
                        const currentQuery = searchInput.value.trim();
                        const queryTerms = currentQuery.split(/\\s+/).filter(Boolean);
                        let highlightedContent = matchedMsg.content;
                        if (queryTerms.length > 0) {
                            const termPattern = queryTerms.map(t => t.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&')).join('|');
                            const hlRe = new RegExp(`(${termPattern})`, 'gi');
                            highlightedContent = highlightedContent.replace(hlRe, '[[$1]]');
                        }
                        rawMatchedParaText = highlightedContent;
                    }
                }
                
                const showTitle = group.excerpts.length > 1;
                const titleHtml = showTitle ? `<div style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin: 1rem 0 0.5rem 0; opacity: 0.6; font-weight: 600;">Relevant Excerpt ${idx + 1}</div>` : '';
                
                return `
                <div class="excerpt-wrapper" data-idx="${idx}">
                    ${titleHtml}
                    <div class="snippet-container snippet-preview collapsed-snippet">
                        ${renderHighlightedText(fullText)}
                    </div>
                    <div class="expanded-content hidden">
                        <div class="section-label section-label-match">Matched Text</div>
                        <div class="matched-text-block">
                            ${structured ? renderHighlightedText(fullText) : renderParagraphText(rawMatchedParaText)}
                        </div>
                        <div class="context-header">
                            <span class="section-label section-label-context">${contextTypeLabel}</span>
                            <span class="context-radius-badge" data-key="context-label">${contextInitBadge}</span>
                        </div>
                        <div class="context-position-label" data-key="context-position"></div>
                        ${expandControlsTop}
                        <div class="context-block" data-key="context-content">
                            <div class="context-loading">Loading context...</div>
                        </div>
                        <div class="context-controls">
                            ${expandControlsBottom}
                        </div>
                        <div class="full-conversation-container hidden"></div>
                    </div>
                </div>`;
            }).join('');

            card.innerHTML = `
                <div class="result-header">
                    <div class="title-visited-row" style="display: flex; align-items: baseline; gap: 0.5rem; flex: 1;">
                        <span class="visited-indicator">&#10003;</span>
                        <h3 class="result-title">${escapeHTML(group.conversation_title)}</h3>
                    </div>
                    <div class="result-meta">
                        ${provenanceLabel}
                        <span class="score-subtle" title="Similarity Score">${scorePercent}</span>
                        <button class="toggle-btn">Expand</button>
                        <button class="library-nav-btn" 
                            data-id="${group.conversation_id}"
                            data-source="${group.conversation_source_type}"
                            data-msg-start="${group.excerpts[0].message_start_index}"
                            data-msg-end="${group.excerpts[0].message_end_index}"
                            data-matched-text="${escapeHTML(group.excerpts[0].matched_chunk_text || '')}"
                        >Open in Library</button>
                    </div>
                </div>
                <div class="result-provenance-row">
                    <div class="result-provenance-item">
                        <span class="result-provenance-title">${escapeHTML(projectName)}</span>
                    </div>
                    <div class="result-provenance-item">
                        <span class="library-type-badge ${sourceBadgeCls}">${sourceBadgeText}</span>
                    </div>
                    <div class="result-provenance-item">
                        <span>${importDateStr}</span>
                    </div>
                    <div class="result-provenance-item" style="opacity:0.6; margin-left:auto;">
                        <span class="result-provenance-title" style="font-size: 0.65rem;">${escapeHTML(group.conversation_title)}</span>
                    </div>
                </div>
                <div class="excerpts-container">
                    ${excerptsHtml}
                </div>
            `;
            
            // Reusable functions
            async function fetchRange(result, start, end) {
                const currentQuery = searchInput.value.trim();
                const url = `${BASE_URL}/conversations/${result.conversation_id}?highlight_query=${encodeURIComponent(currentQuery)}&start_index=${start}&end_index=${end}`;
                const res = await fetch(url);
                if (!res.ok) throw new Error('API error');
                const conv = await res.json();
                return conv.messages || [];
            }
            
            // Loop over excerpts to bind handlers
            group.excerpts.forEach((result, idx) => {
                const resultKey = `r:${result.conversation_id}:${result.message_start_index}:${result.message_end_index}`;
                if (!sessionStates[resultKey]) {
                    sessionStates[resultKey] = {
                        expanded: false,
                        contextRadius: 10,
                        paraRadius: 3,
                        visibleParaStart: null,
                        visibleParaEnd: null,
                        totalMessages: result.message_count || 0,
                        fullThread: false,
                        messages: null,
                        lineIndex: null,
                        matchedLineRange: null,
                        paragraphs: null,
                        matchedParaRange: null,
                        lastAddedIdx: null,
                        visited: false
                    };
                }
                const state = sessionStates[resultKey];
                
                const excerptWrapper = card.querySelector(`.excerpt-wrapper[data-idx="${idx}"]`);
                const fullText = result.matched_chunk_text || '';
                
                function renderCardContext() {
                    if (!state.messages) return;
                    let html = '';
                    let label = '';
                    let posLabel = '';
                    if (structured) {
                        if (!state.lineIndex) return;
                        const { allLines, lineToMsgIndex } = state.lineIndex;
                        const { start: matchStart, end: matchEnd } = state.matchedLineRange;
                        const r = state.contextRadius;

                        const fromLine = Math.max(0, matchStart - r);
                        const toLine = Math.min(allLines.length - 1, matchEnd + r);
                        const vStartIdx = lineToMsgIndex[fromLine] + 1;
                        const vEndIdx = lineToMsgIndex[toLine] + 1;
                        const total = state.totalMessages;

                        html = renderContextLines(allLines, state.messages, lineToMsgIndex, fromLine, toLine, matchStart, matchEnd, state.lastAddedIdx);
                        label = `Showing ±${r} lines`;

                        if (vStartIdx === vEndIdx) {
                            posLabel = `Message ${vStartIdx} of ${total}`;
                        } else {
                            posLabel = `Messages ${vStartIdx}–${vEndIdx} of ${total}`;
                        }
                    } else {
                        if (!state.paragraphs) return;
                        const { start: mps, end: mpe } = state.matchedParaRange;
                        const start = state.visibleParaStart;
                        const end = state.visibleParaEnd;
                        html = renderParagraphContext(state.paragraphs, start, end, mps, mpe, state.lastAddedIdx);

                        const visibleParas = state.paragraphs.filter(
                            p => p.message_index >= start && p.message_index <= end
                        );
                        const count = visibleParas.length;
                        label = `Showing ${count} paragraph${count !== 1 ? 's' : ''}`;

                        if (start === end) {
                            posLabel = `Paragraph ${start + 1} of ${state.totalMessages}`;
                        } else {
                            posLabel = `Paragraphs ${start + 1}–${end + 1} of ${state.totalMessages}`;
                        }

                        const prevBtn = excerptWrapper.querySelector('.prev-para-btn');
                        const nextBtn = excerptWrapper.querySelector('.next-para-btn');
                        if (prevBtn) prevBtn.disabled = (start <= 0);
                        if (nextBtn) nextBtn.disabled = (end >= state.totalMessages - 1);
                    }
                    excerptWrapper.querySelector('[data-key="context-content"]').innerHTML = html;
                    excerptWrapper.querySelector('[data-key="context-label"]').textContent = label;
                    excerptWrapper.querySelector('[data-key="context-position"]').textContent = posLabel;

                    const threadContainer = excerptWrapper.querySelector('.full-conversation-container');
                    const fullConvBtn = excerptWrapper.querySelector('.full-conv-btn');
                    if (threadContainer && fullConvBtn) {
                        if (state.fullThread) {
                            const dividerLabel = structured ? 'Full Chronological Conversation' : 'Full Imported Text';
                            const bodyHtml = structured ? buildFullThreadHtml() : buildFullTextHtml();
                            const wrapClass = structured ? 'surrounding-messages' : 'para-context-block';
                            threadContainer.innerHTML = `<div class="exchange-divider">${dividerLabel}</div><div class="${wrapClass}">${bodyHtml}</div>`;
                            threadContainer.classList.remove('hidden');
                            fullConvBtn.textContent = structured ? 'Collapse Full Thread' : 'Collapse Full Text';
                        } else {
                            threadContainer.classList.add('hidden');
                            fullConvBtn.textContent = structured ? 'Show Full Thread' : 'Show Full Text';
                        }
                    }
                }
                
                function buildFullThreadHtml() {
                    return state.messages.map(msg => {
                        const roleClass = msg.role === 'user' ? 'user' : 'assistant';
                        const roleLabel = msg.role === 'user' ? 'User' : 'Assistant';
                        const isMatched = (msg.message_index >= result.message_start_index && msg.message_index <= result.message_end_index);
                        return `
                            <div class="message ${roleClass}${isMatched ? ' highlight-message' : ''}">
                                <div class="message-role">${roleLabel}</div>
                                <div class="message-content">${renderHighlightedText(msg.content)}</div>
                            </div>
                        `;
                    }).join('');
                }

                function buildFullTextHtml() {
                    if (!state.paragraphs) return '';
                    return state.paragraphs.map(p => {
                        const isMatched = (
                            p.message_index >= state.matchedParaRange.start &&
                            p.message_index <= state.matchedParaRange.end
                        );
                        return `<div class="${isMatched ? 'para-block para-block-match' : 'para-block'}">${renderParagraphText(p.content)}</div>`;
                    }).join('');
                }

                async function onExpand() {
                    if (!state.messages) {
                        try {
                            const mStart = result.message_start_index;
                            const mEnd = result.message_end_index;

                            let initialMessages;
                            if (structured) {
                                const currentQuery = searchInput.value.trim();
                                const res = await fetch(`${BASE_URL}/conversations/${result.conversation_id}?highlight_query=${encodeURIComponent(currentQuery)}`);
                                const conv = await res.json();
                                initialMessages = conv.messages || [];
                            } else {
                                const fetchStart = Math.max(0, mStart - 2);
                                const fetchEnd = Math.min(state.totalMessages - 1, mEnd + 1);
                                initialMessages = await fetchRange(result, fetchStart, fetchEnd);
                                state.visibleParaStart = fetchStart;
                                state.visibleParaEnd = fetchEnd;
                            }

                            state.messages = initialMessages.sort((a, b) => a.message_index - b.message_index);

                            if (structured) {
                                state.lineIndex = buildLineIndex(state.messages);
                                state.matchedLineRange = findMatchedLineRange(state.lineIndex.allLines, fullText);
                            } else {
                                state.paragraphs = buildParagraphIndex(state.messages);
                                state.matchedParaRange = findMatchedParagraphRange(state.paragraphs, fullText);
                            }
                        } catch (err) {
                            console.error(err);
                            excerptWrapper.querySelector('[data-key="context-content"]').innerHTML = '<em style="color:red">Failed to load content.</em>';
                            return;
                        }
                    }
                    renderCardContext();
                }

                // If state was expanded during previous render map it back
                if (state.expanded) {
                    isExpanded = true;
                }
                
                // Need to expose onExpand for the master toggle
                excerptWrapper._onExpand = onExpand;
                
                // ±N expansion buttons (Structured)
                excerptWrapper.querySelectorAll('.ctx-expand-btn[data-radius]').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const r = parseInt(btn.dataset.radius, 10);
                        state.contextRadius = r;
                        state.lastAddedIdx = null; // No single specific new item for fixed jumps
                        renderCardContext();
                    });
                });

                // Paragraph Expansion (Raw)
                if (!structured) {
                    const prevBtn = excerptWrapper.querySelector('.prev-para-btn');
                    const nextBtn = excerptWrapper.querySelector('.next-para-btn');

                    prevBtn.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        if (state.visibleParaStart > 0) {
                            state.visibleParaStart--;
                            const idx = state.visibleParaStart;
                            state.lastAddedIdx = idx;
                            if (!state.messages.some(m => m.message_index === idx)) {
                                try {
                                    const newMsgs = await fetchRange(result, idx, idx);
                                    state.messages = [...state.messages, ...newMsgs].sort((a, b) => a.message_index - b.message_index);
                                    state.paragraphs = buildParagraphIndex(state.messages);
                                } catch (err) { console.error(err); }
                            }
                            renderCardContext();
                            
                            const newlyRevealed = excerptWrapper.querySelector('.newly-revealed');
                            if (newlyRevealed) {
                                newlyRevealed.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                            }
                        }
                    });

                    nextBtn.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        if (state.visibleParaEnd < state.totalMessages - 1) {
                            state.visibleParaEnd++;
                            const idx = state.visibleParaEnd;
                            state.lastAddedIdx = idx;
                            if (!state.messages.some(m => m.message_index === idx)) {
                                try {
                                    const newMsgs = await fetchRange(result, idx, idx);
                                    state.messages = [...state.messages, ...newMsgs].sort((a, b) => a.message_index - b.message_index);
                                    state.paragraphs = buildParagraphIndex(state.messages);
                                } catch (err) { console.error(err); }
                            }
                            renderCardContext();
                            
                            const newlyRevealed = excerptWrapper.querySelector('.newly-revealed');
                            if (newlyRevealed) {
                                newlyRevealed.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                            }
                        }
                    });
                }

                const fullConvBtn = excerptWrapper.querySelector('.full-conv-btn');
                fullConvBtn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const container = excerptWrapper.querySelector('.full-conversation-container');
                    const isHidden = container.classList.contains('hidden');
                    if (isHidden) {
                        if (!structured && state.messages.length < state.totalMessages) {
                            try {
                                const currentQuery = searchInput.value.trim();
                                const res = await fetch(`${BASE_URL}/conversations/${result.conversation_id}?highlight_query=${encodeURIComponent(currentQuery)}`);
                                if (res.ok) {
                                    const conv = await res.json();
                                    state.messages = (conv.messages || []).sort((a, b) => a.message_index - b.message_index);
                                    state.paragraphs = buildParagraphIndex(state.messages);
                                }
                            } catch (err) { console.error(err); }
                        }
                        state.fullThread = true;
                        renderCardContext();
                    } else {
                        state.fullThread = false;
                        renderCardContext();
                    }
                });
            });

            // Master toggle for all excerpts in card
            function toggleExpand(e) {
                if (e) e.stopPropagation();
                isExpanded = !isExpanded;
                
                if (isExpanded) {
                    card.classList.add('expanded');
                    card.classList.add('visited');
                    card.querySelector('.toggle-btn').textContent = 'Collapse';
                    
                    // Mark all excerpts in session as visited/expanded
                    group.excerpts.forEach((result, idx) => {
                        const resultKey = `r:${result.conversation_id}:${result.message_start_index}:${result.message_end_index}`;
                        const state = sessionStates[resultKey];
                        if (state) {
                            state.expanded = true;
                            state.visited = true;
                        }
                        const wrapper = card.querySelector(`.excerpt-wrapper[data-idx="${idx}"]`);
                        wrapper.querySelector('.expanded-content').classList.remove('hidden');
                        wrapper.querySelector('.collapsed-snippet').classList.add('hidden');
                        if (wrapper._onExpand) wrapper._onExpand();
                    });
                    
                } else {
                    card.classList.remove('expanded');
                    card.querySelector('.toggle-btn').textContent = 'Expand';
                    
                    group.excerpts.forEach((result, idx) => {
                        const resultKey = `r:${result.conversation_id}:${result.message_start_index}:${result.message_end_index}`;
                        const state = sessionStates[resultKey];
                        if (state) {
                            state.expanded = false;
                        }
                        const wrapper = card.querySelector(`.excerpt-wrapper[data-idx="${idx}"]`);
                        wrapper.querySelector('.expanded-content').classList.add('hidden');
                        wrapper.querySelector('.collapsed-snippet').classList.remove('hidden');
                    });
                }
            }

            card.querySelector('.toggle-btn').addEventListener('click', toggleExpand);
            card.addEventListener('click', toggleExpand);

            card.querySelector('.library-nav-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                
                card.classList.add('visited');
                group.excerpts.forEach(r => {
                     const k = `r:${r.conversation_id}:${r.message_start_index}:${r.message_end_index}`;
                     if(sessionStates[k]) sessionStates[k].visited = true;
                });

                searchReturnContext = {
                    query: searchInput.value,
                    categoryId: categorySelect.value,
                    sortMode: document.getElementById('result-sort-select').value,
                    displayMode: document.getElementById('result-display-select').value,
                    conversationId: group.conversation_id
                };

                const btn = e.currentTarget;
                const anchor = {
                    source: btn.dataset.source,
                    msgStart: parseInt(btn.dataset.msgStart, 10),
                    msgEnd: parseInt(btn.dataset.msgEnd, 10),
                    matchedText: btn.dataset.matchedText || ''
                };
                highlightLibraryItem(group.conversation_id, anchor);
            });
            
            // Check if any excerpt was previously expanded
            if (isExpanded) {
                 isExpanded = false; // toggleExpand flips it back
                 toggleExpand();
            } else {
                 // Check if visited
                 let anyVisited = group.excerpts.some(r => {
                      const k = `r:${r.conversation_id}:${r.message_start_index}:${r.message_end_index}`;
                      return sessionStates[k] && sessionStates[k].visited;
                 });
                 if (anyVisited) {
                      card.classList.add('visited');
                 }
            }

            resultsContainer.appendChild(card);
        });
    }"""

    content = content.replace(old_block, new_block)

    with open('ui/app.js', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    main()
