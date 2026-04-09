const BASE_URL = 'http://127.0.0.1:8000';

document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-input');
    const categorySelect = document.getElementById('category-select');
    const resultDisplaySelect = document.getElementById('result-display-select');
    const resultSortSelect = document.getElementById('result-sort-select');
    const resultsContainer = document.getElementById('results-container');
    const statusMessage = document.getElementById('status-message');
    const submitBtn = searchForm.querySelector('button');

    const searchView = document.getElementById('search-view');
    const importView = document.getElementById('import-view');
    const libraryView = document.getElementById('library-view');
    const navSearchBtn = document.getElementById('nav-search-btn');
    const navImportBtn = document.getElementById('nav-import-btn');
    const navHomeBtn = document.getElementById('nav-home-btn');
    const navLibraryBtn = document.getElementById('nav-library-btn');
    const navBackBtn = document.getElementById('nav-back-btn');

    const importProjectSelect = document.getElementById('import-project');
    const newProjectInput = document.getElementById('new-project-input');
    const importTitleInput = document.getElementById('import-title');
    const importStatusDiv = document.getElementById('import-status');

    let sessionStates = {};
    let visitedResults = new Set();
    let activeSearchController = null;
    let currentSearchResults = [];
    let searchReturnContext = null;
    let searchScrollPos = 0;
    let searchSelection = { start: 0, end: 0 };
    let searchInputScrollLeft = 0;
    let currentLibraryId = null;
    let viewStack = []; // Simple stack for browser-style back navigation
    const SEARCH_LIMIT = 50;

    // Sync search state to session
    searchInput.addEventListener('input', () => {
        sessionStorage.setItem('thoughtreach_last_search_query', searchInput.value);
    });
    categorySelect.addEventListener('change', () => {
        sessionStorage.setItem('thoughtreach_last_category_id', categorySelect.value);
    });
    if (resultDisplaySelect) {
        resultDisplaySelect.addEventListener('change', () => {
            sessionStorage.setItem('thoughtreach_last_display_mode', resultDisplaySelect.value);
            processAndRenderResults();
        });
    }
    if (resultSortSelect) {
        resultSortSelect.addEventListener('change', () => {
            sessionStorage.setItem('thoughtreach_last_sort_mode', resultSortSelect.value);
            processAndRenderResults();
        });
    }

    loadCategories();

    // Restore last search query from session
    const lastQuery = sessionStorage.getItem('thoughtreach_last_search_query');
    if (lastQuery) {
        searchInput.value = lastQuery;
    }

    // Restore last display/sort modes
    const lastDisplayMode = sessionStorage.getItem('thoughtreach_last_display_mode');
    if (lastDisplayMode && resultDisplaySelect) {
        resultDisplaySelect.value = lastDisplayMode;
    }
    const lastSortMode = sessionStorage.getItem('thoughtreach_last_sort_mode');
    if (lastSortMode && resultSortSelect) {
        resultSortSelect.value = lastSortMode;
    }

    searchInput.focus();
    navHomeBtn.classList.add('hidden');
    searchForm.addEventListener('submit', handleSearch);

    // ── Navigation Toggles ────────────────────────────────────────────────────
    navSearchBtn.addEventListener('click', () => {
        searchView.classList.remove('hidden');
        importView.classList.add('hidden');
        libraryView.classList.add('hidden');
        navSearchBtn.classList.add('active');
        navImportBtn.classList.remove('active');
        navLibraryBtn.classList.remove('active');
        navHomeBtn.classList.add('hidden');
        viewStack.push('search');
        updateNavVisibility();

        // Restore overall page scroll
        window.scrollTo(0, searchScrollPos);

        // Restore caret/selection position
        if (searchInput) searchInput.setSelectionRange(searchSelection.start, searchSelection.end);

        // Restore input horizontal scroll
        if (searchInput) searchInput.scrollLeft = searchInputScrollLeft;
    });

    function updateNavVisibility() {
        const isSearch = !searchView.classList.contains('hidden');
        navHomeBtn.classList.toggle('hidden', isSearch);
        navBackBtn.classList.toggle('hidden', isSearch);
    }

    navBackBtn.addEventListener('click', () => {
        const openView = document.getElementById('library-open-view');
        if (openView && !openView.classList.contains('hidden')) {
            const backToSearchBtn = document.getElementById('library-back-to-search-btn');
            if (backToSearchBtn && !backToSearchBtn.classList.contains('hidden')) {
                backToSearchBtn.click();
            } else {
                document.getElementById('library-back-btn').click();
            }
        } else if (viewStack.length > 0) {
            const prevView = viewStack.pop();
            // If the popped view is the current one, pop again
            const currentView = !searchView.classList.contains('hidden') ? 'search' :
                                (!importView.classList.contains('hidden') ? 'import' : 'library');
            
            let target = prevView;
            if (target === currentView && viewStack.length > 0) {
                target = viewStack.pop();
            }

            if (target === 'import') navImportBtn.click();
            else if (target === 'library') navLibraryBtn.click();
            else navSearchBtn.click();
            
            // Pop the one we just added via the click listener
            viewStack.pop();
        } else {
            navSearchBtn.click();
        }
    });

    navHomeBtn.addEventListener('click', () => {
        viewStack = [];
        navSearchBtn.click();
    });

    navImportBtn.addEventListener('click', () => {
        // Track overall page scroll before leaving Search
        if (!searchView.classList.contains('hidden')) {
            searchScrollPos = window.scrollY;
            searchSelection.start = searchInput.selectionStart;
            searchSelection.end = searchInput.selectionEnd;
            searchInputScrollLeft = searchInput.scrollLeft;
        }

        importView.classList.remove('hidden');
        searchView.classList.add('hidden');
        libraryView.classList.add('hidden');
        navImportBtn.classList.add('active');
        navSearchBtn.classList.remove('active');
        navLibraryBtn.classList.remove('active');
        navHomeBtn.classList.remove('hidden');
        viewStack.push('import');
        updateNavVisibility();
    });

    async function loadCategories() {
        try {
            const response = await fetch(`${BASE_URL}/categories`);
            if (!response.ok) throw new Error('Failed to fetch categories');
            const categories = await response.json();
            categories.forEach(category => {
                const opt1 = document.createElement('option');
                opt1.value = category.id;
                opt1.textContent = category.name;
                categorySelect.appendChild(opt1);

                if (importProjectSelect) {
                    const opt2 = document.createElement('option');
                    opt2.value = category.id;
                    opt2.textContent = category.name;
                    importProjectSelect.add(opt2, importProjectSelect.options[importProjectSelect.options.length - 1]);
                }
            });

            // Restore last project ID from session if it exists
            const lastProjectId = sessionStorage.getItem('thoughtreach_last_project_id');
            if (lastProjectId && importProjectSelect) {
                // Verify it exists in the new list before selecting
                if ([...importProjectSelect.options].some(o => o.value === lastProjectId)) {
                    importProjectSelect.value = lastProjectId;
                }
            }

            // Restore last search category filter
            const lastSearchCategoryId = sessionStorage.getItem('thoughtreach_last_category_id');
            if (lastSearchCategoryId) {
                if ([...categorySelect.options].some(o => o.value === lastSearchCategoryId)) {
                    categorySelect.value = lastSearchCategoryId;
                }
            }
        } catch (error) {
            console.error('Category load error:', error);
            statusMessage.textContent = 'Warning: Could not load categories. Ensure backend is running.';
        }
    }

    async function handleSearch(event) {
        event.preventDefault();
        const query = searchInput.value.trim();
        const categoryId = categorySelect.value || null;
        if (!query) return;

        if (activeSearchController) {
            activeSearchController.abort();
            activeSearchController = null;
        }

        const controller = new AbortController();
        activeSearchController = controller;

        if (submitBtn) submitBtn.disabled = true;
        searchInput.disabled = true;
        setStatus('Searching...');
        resultsContainer.innerHTML = '';
        document.getElementById('results-header-row').classList.add('hidden');
        sessionStates = {};
        currentSearchResults = [];
        visitedResults.clear();

        try {
            const payload = { query, limit: SEARCH_LIMIT };
            if (categoryId) payload.category_id = categoryId;

            const response = await fetch(`${BASE_URL}/search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                signal: controller.signal
            });

            if (controller.signal.aborted) return;
            if (response.status === 404) {
                setStatus('Category missing or server error. Please refresh and try again.', true);
                return;
            }
            if (!response.ok) throw new Error(`Server error: ${response.status}`);

            const results = await response.json();

            const searchSummary = document.getElementById('search-summary');
            if (results.length === 0) {
                searchSummary.classList.add('hidden'); // Hide if nothing found to keep focus on empty state
                resultsContainer.innerHTML = `
                    <div class="empty-state no-results">
                        <h3>No matches found</h3>
                        <p>Try fewer words, a different phrase, or searching by the title in the Library.</p>
                    </div>
                `;
                setStatus('');
            } else {
                currentSearchResults = [...results];
                document.getElementById('result-display-select').value = 'all';
                document.getElementById('result-sort-select').value = 'relevant';
                document.getElementById('results-header-row').classList.remove('hidden');

                setStatus('');
                processAndRenderResults();
            }
        } catch (error) {
            if (error.name === 'AbortError') return;
            console.error('Search error:', error);
            setStatus('Search failed. Please try again.', true);
        } finally {
            if (activeSearchController === controller) {
                activeSearchController = null;
                if (submitBtn) submitBtn.disabled = false;
                searchInput.disabled = false;
                searchInput.focus();
            }
        }
    }

    // ── Structured Conversation Helpers ───────────────────────────────────────

    function buildLineIndex(messages) {
        const allLines = [];
        const lineToMsgIndex = [];
        messages.forEach((msg, mi) => {
            const msgLines = (msg.content || '').split('\n');
            msgLines.forEach(line => {
                allLines.push(line);
                lineToMsgIndex.push(mi);
            });
        });
        return { allLines, lineToMsgIndex };
    }

    function findMatchedLineRange(allLines, matchedChunkText) {
        const stripped = matchedChunkText.replace(/\[\[(.*?)\]\]/g, '$1').trim();
        const chunkLines = stripped.split('\n').map(l => l.trim()).filter(Boolean);
        if (chunkLines.length === 0) return { start: 0, end: 0 };
        const firstLine = chunkLines[0];
        let startIdx = -1;
        for (let i = 0; i < allLines.length; i++) {
            if (allLines[i].trim() === firstLine) {
                let match = true;
                for (let j = 0; j < Math.min(chunkLines.length, 3); j++) {
                    if ((allLines[i + j] || '').trim() !== chunkLines[j]) { match = false; break; }
                }
                if (match) { startIdx = i; break; }
            }
        }
        if (startIdx === -1) return { start: 0, end: Math.min(chunkLines.length - 1, allLines.length - 1) };
        return { start: startIdx, end: startIdx + chunkLines.length - 1 };
    }

    function renderContextLines(allLines, messages, lineToMsgIndex, fromLine, toLine, matchStart, matchEnd, lastAddedMsgIdx = null) {
        fromLine = Math.max(0, fromLine);
        toLine = Math.min(allLines.length - 1, toLine);
        if (fromLine > toLine) return '<em style="opacity:0.5">No surrounding context available.</em>';
        let html = '';
        let lastMsgIdx = -1;
        for (let i = fromLine; i <= toLine; i++) {
            const mi = lineToMsgIndex[i];
            const msg = messages[mi];
            if (mi !== lastMsgIdx) {
                lastMsgIdx = mi;
                const roleLabel = msg.role === 'user' ? 'User' : 'Assistant';
                const roleClass = msg.role === 'user' ? 'ctx-role-user' : 'ctx-role-assistant';
                const isNew = (mi === lastAddedMsgIdx);
                html += `<div class="ctx-role-label ${roleClass}${isNew ? ' newly-revealed' : ''}">${roleLabel}</div>`;
            }
            const isInMatch = (i >= matchStart && i <= matchEnd);
            const lineHtml = renderHighlightedText(allLines[i]) || '&nbsp;';
            const isNewLine = (mi === lastAddedMsgIdx);
            html += `<div class="ctx-line${isInMatch ? ' ctx-line-match' : ''}${isNewLine ? ' newly-revealed' : ''}">${lineHtml}</div>`;
        }
        return html;
    }

    // ── Paragraph Context Helpers (raw text imports) ──────────────────────────

    function buildParagraphIndex(messages) {
        // For paragraph-split imports each "message" content is a single paragraph block.
        // We just return all messages as ordered paragraphs.
        return messages.map((msg, i) => ({
            index: i,
            role: msg.role,
            content: msg.content,
            message_index: msg.message_index
        }));
    }

    function findMatchedParagraphRange(paras, matchedChunkText) {
        // Returns { start, end } in message_index space (not array index), so that
        // the isMatched check in renderParagraphContext (which uses absIdx = p.message_index)
        // correctly highlights the matched paragraph for mid-document results where
        // message_index !== array position.
        const stripped = matchedChunkText.replace(/\[\[(.*?)\]\]/g, '$1').trim();
        for (let i = 0; i < paras.length; i++) {
            if (paras[i].content.includes(stripped.slice(0, 60))) {
                const mi = paras[i].message_index;
                return { start: mi, end: mi };
            }
        }
        // Fallback: use the message_index of the first paragraph in the visible set.
        const fallback = paras.length > 0 ? paras[0].message_index : 0;
        return { start: fallback, end: fallback };
    }

    function renderParagraphContext(paras, fromPara, toPara, matchStart, matchEnd, lastAddedIdx = null) {
        if (!paras || !paras.length) return '<em style="opacity:0.5">No surrounding context available.</em>';
        let html = '';
        paras.forEach(p => {
            const absIdx = p.message_index;
            if (absIdx < fromPara || absIdx > toPara) return;

            const isMatched = (absIdx >= matchStart && absIdx <= matchEnd);
            const isNew = (absIdx === lastAddedIdx);

            let pClass = 'para-block';
            if (isMatched) pClass += ' para-block-match';
            else pClass += ' para-block-revealed';
            if (isNew) pClass += ' newly-revealed';

            html += `<div class="${pClass}">${renderParagraphText(p.content) || '&nbsp;'}</div>`;
        });
        if (!html) return '<em style="opacity:0.5">No surrounding context available.</em>';
        return html;
    }

    // ── Source-type detection ─────────────────────────────────────────────────
    // The system uses "paste" for all imports currently. We distinguish structured
    // (explicit user/assistant messages) from raw-text imports by whether the
    // search result includes role-attributed source messages. If source_user_message
    // or source_assistant_message is present, this is a structured conversation.
    // Otherwise it was a raw text import with alternating paragraph roles.
    function isStructuredConversation(result) {
        // A true structured conversation requires source_type === 'structured' AND
        // evidence of actual assistant-role messages in the conversation.
        //
        // This guards against raw text accidentally imported with the default
        // 'Structured' mode selected: those get source_type='structured' stored but
        // have ONLY 'user' role messages. Without this guard they would enter the
        // line-by-line structured rendering path and Next/Previous buttons would
        // step through individual lines rather than full paragraph blocks.
        if (result.conversation_source_type === 'raw') return false;

        // Presence of an assistant message in the Layer 2 result confirms real
        // User/Assistant dialogue. Also check surrounding messages for assistant role
        // as a secondary signal (handles edge cases near the end of a conversation).
        const hasAssistantInL2 = result.source_assistant_message !== null &&
            result.source_assistant_message !== undefined;
        const hasPrevAssistant = result.previous_exchange_assistant_message !== null &&
            result.previous_exchange_assistant_message !== undefined;
        const hasNextAssistant = result.next_exchange_assistant_message !== null &&
            result.next_exchange_assistant_message !== undefined;
        const hasAssistantInSurroundings = (result.surrounding_messages || [])
            .some(m => m.role !== 'user');
            
        return hasAssistantInL2 || hasPrevAssistant || hasNextAssistant || hasAssistantInSurroundings;
    }

    // ── Card rendering ────────────────────────────────────────────────────────

    function renderResults(groups) {
        resultsContainer.innerHTML = '';
        groups.forEach(group => {
            const resultKey = `group:${group.conversation_id}`;
            if (!sessionStates[resultKey]) {
                sessionStates[resultKey] = {
                    expanded: false,
                    excerpts: group.excerpts.map(ex => ({
                        message_start_index: ex.message_start_index,
                        message_end_index: ex.message_end_index,
                        expanded: false,
                        lineContextBefore: 10,
                        lineContextAfter: 10,
                        paraRadius: 3,
                        visibleParaStart: null,
                        visibleParaEnd: null,
                        totalMessages: group.results[0].message_count || 0,
                        fullThread: false,
                        messages: null,
                        lineIndex: null,
                        matchedLineRange: null,
                        paragraphs: null,
                        matchedParaRange: null,
                        lastAddedIdx: null,
                        visited: false
                    }))
                };
            }
            const groupState = sessionStates[resultKey];
            const structured = group.results.some(res => isStructuredConversation(res));

            const card = document.createElement('div');
            card.className = 'result-card' + (visitedResults.has(group.conversation_id) ? ' visited' : '');

            const maxScorePercent = Math.round(group.max_score * 100) + '%';
            const importDateStr = formatLibraryDate(group.imported_at);
            const sourceBadgeCls = structured ? 'library-type-structured' : 'library-type-raw';
            const sourceBadgeText = structured ? 'Structured Conversation' : 'Raw Imported Text';

            let whyMatchedSuffix = '';
            if (structured && group.results && group.results.length > 0) {
                const topResult = group.results[0];
                if (topResult.source_assistant_is_match && !topResult.source_user_is_match) {
                    whyMatchedSuffix = ' Strongest match in assistant response.';
                } else if (topResult.source_user_is_match && !topResult.source_assistant_is_match) {
                    whyMatchedSuffix = ' Strongest match in user prompt.';
                } else if (topResult.source_user_is_match && topResult.source_assistant_is_match) {
                    whyMatchedSuffix = ' Strongest match in user prompt and assistant response.';
                }
            }

            let excerptsHtml = group.excerpts.map((ex, i) => {
                const exState = groupState.excerpts[i];
                const fullText = ex.matched_chunk_text || '';

                const expandControlsTop = structured
                    ? `<div class="context-controls-top">
                           <button class="ctx-expand-btn prev-line-btn">Previous Line</button>
                           <button class="ctx-expand-btn prev-para-btn">Previous Message</button>
                       </div>`
                    : `<div class="context-controls-top">
                           <button class="ctx-expand-btn prev-line-btn">Previous Line</button>
                           <button class="ctx-expand-btn prev-para-btn">Previous Paragraph</button>
                       </div>`;

                const expandControlsBottom = structured
                    ? `<div class="context-controls">
                           <button class="ctx-expand-btn next-line-btn">Next Line</button>
                           <button class="ctx-expand-btn next-para-btn">Next Message</button>
                           <button class="full-conv-btn">Full Thread</button>
                       </div>`
                    : `<div class="context-controls">
                           <button class="ctx-expand-btn next-line-btn">Next Line</button>
                           <button class="ctx-expand-btn next-para-btn">Next Paragraph</button>
                           <button class="full-conv-btn">Full Text</button>
                       </div>`;

                return `
                    <div class="excerpt-wrapper" data-index="${i}">
                        <div class="section-label section-label-match">Match ${i + 1}</div>
                        <div class="snippet-container snippet-preview${exState.expanded ? ' hidden' : ''}">
                            ${renderHighlightedText(fullText)}
                        </div>
                        <div class="expanded-content${exState.expanded ? '' : ' hidden'}">
                            <div class="matched-text-block">
                                ${renderHighlightedText(fullText)}
                            </div>
                            <div class="context-header">
                                <span class="section-label section-label-context">Context</span>
                                <span class="context-radius-badge" data-key="context-label">Loading...</span>
                            </div>
                            <div class="context-position-label" data-key="context-position"></div>
                            ${expandControlsTop}
                            <div class="context-block" data-key="context-content">
                                <div class="context-loading">Loading context...</div>
                            </div>
                            ${expandControlsBottom}
                            <div class="full-conversation-container hidden"></div>
                        </div>
                    </div>
                `;
            }).join('');

            card.innerHTML = `
                <div class="result-header">
                    <div class="title-visited-row" style="display: flex; align-items: baseline; gap: 0.5rem; flex: 1;">
                        <span class="visited-indicator">&#10003;</span>
                        <h3 class="result-title">${escapeHTML(group.conversation_title)}</h3>
                    </div>
                    <div class="result-actions">
                        <button class="toggle-btn">${groupState.expanded ? 'Collapse' : 'Expand'}</button>
                        <button class="library-nav-btn" data-id="${group.conversation_id}">Open in Library</button>
                    </div>
                </div>
                <div class="result-meta-row">
                    <span class="meta-item badge category" title="Project">${escapeHTML(group.category_name || 'Uncategorised')}</span>
                    <span class="meta-item badge ${sourceBadgeCls}" title="Type">${sourceBadgeText}</span>
                    <span class="meta-item meta-date" title="Original Date">${importDateStr || 'Date unknown'}</span>
                    <span class="meta-item score-subtle" title="Relevance Score">${maxScorePercent} Match</span>
                </div>
                <div class="result-why-matched">
                    ${group.excerpts.length === 1 
                        ? `Matched 1 excerpt in this ${structured ? 'conversation' : 'imported item'}.${whyMatchedSuffix}`
                        : `Matched ${group.excerpts.length} excerpts in this ${structured ? 'conversation' : 'imported item'}.${whyMatchedSuffix}`}
                </div>
                <div class="excerpts-container${groupState.expanded ? '' : ' hidden'}">
                    ${excerptsHtml}
                </div>
            `;

            group.excerpts.forEach((ex, i) => {
                const exState = groupState.excerpts[i];
                const wrapper = card.querySelector(`.excerpt-wrapper[data-index="${i}"]`);

                function renderExcerptContext() {
                    if (!exState.messages) return;
                    let html = '';
                    let label = '';
                    let posLabel = '';

                    const pStart = exState.visibleParaStart;
                    const pEnd = exState.visibleParaEnd;

                    if (structured) {
                        // ── Structured conversation: line-based rendering ──
                        const { allLines, lineToMsgIndex } = exState.lineIndex;
                        const { start: matchStart, end: matchEnd } = exState.matchedLineRange;
                        const rBefore = exState.lineContextBefore;
                        const rAfter = exState.lineContextAfter;

                        let fromLine = Math.max(0, matchStart - rBefore);
                        let toLine = Math.min(allLines.length - 1, matchEnd + rAfter);

                        let firstLineOfP = fromLine;
                        let lastLineOfP = toLine;

                        if (pStart !== null) {
                            for (let i = 0; i < lineToMsgIndex.length; i++) {
                                if (lineToMsgIndex[i] === pStart) { firstLineOfP = i; break; }
                            }
                        }
                        if (pEnd !== null) {
                            for (let i = lineToMsgIndex.length - 1; i >= 0; i--) {
                                if (lineToMsgIndex[i] === pEnd) { lastLineOfP = i; break; }
                            }
                        }

                        const effectiveFrom = Math.min(fromLine, firstLineOfP);
                        const effectiveTo = Math.max(toLine, lastLineOfP);

                        html = renderContextLines(allLines, exState.messages, lineToMsgIndex, effectiveFrom, effectiveTo, matchStart, matchEnd, exState.lastAddedIdx);

                        const vStartIdx = lineToMsgIndex[effectiveFrom] + 1;
                        const vEndIdx = lineToMsgIndex[effectiveTo] + 1;
                        const msgCount = vEndIdx - vStartIdx + 1;
                        label = `${msgCount} msgs | -${rBefore}/+${rAfter} lines`;
                        posLabel = vStartIdx === vEndIdx ? `Message ${vStartIdx}` : `Messages ${vStartIdx}–${vEndIdx}`;
                    } else {
                        // ── Raw-text import: paragraph-based rendering ──
                        // Use the line counters to compute how many paragraphs to show
                        // within the outer pStart/pEnd window. Each "Next Line" click
                        // widens lineContextAfter by 1, which we translate to the
                        // message_index of that line via the line index, then clamp to
                        // [pStart, pEnd] so paragraph-level boundaries remain the hard limit.
                        const { allLines, lineToMsgIndex } = exState.lineIndex;
                        const { start: matchStart, end: matchEnd } = exState.matchedLineRange;
                        const rBefore = exState.lineContextBefore;
                        const rAfter = exState.lineContextAfter;

                        // Compute line-driven para boundaries
                        const lineFrom = Math.max(0, matchStart - rBefore);
                        const lineTo = Math.min(allLines.length - 1, matchEnd + rAfter);
                        const lineDrivenParaStart = exState.messages[lineToMsgIndex[lineFrom]].message_index;
                        const lineDrivenParaEnd = exState.messages[lineToMsgIndex[lineTo]].message_index;

                        // Clamp within the paragraph-level window: use union so the
                        // line-driven slice can only EXPAND pStart/pEnd, never shrink it.
                        const effectiveParaStart = Math.min(pStart, lineDrivenParaStart);
                        const effectiveParaEnd = Math.max(pEnd, lineDrivenParaEnd);

                        const { start: matchParaStart, end: matchParaEnd } = exState.matchedParaRange || { start: pStart, end: pEnd };
                        html = renderParagraphContext(exState.paragraphs, effectiveParaStart, effectiveParaEnd, matchParaStart, matchParaEnd, exState.lastAddedIdx);

                        const count = exState.paragraphs.filter(p => p.message_index >= effectiveParaStart && p.message_index <= effectiveParaEnd).length;
                        label = `${count} para${count !== 1 ? 's' : ''} | -${rBefore}/+${rAfter} lines`;
                        posLabel = effectiveParaStart === effectiveParaEnd ? `Paragraph ${effectiveParaStart + 1}` : `Paragraphs ${effectiveParaStart + 1}–${effectiveParaEnd + 1}`;
                    }

                    wrapper.querySelector('[data-key="context-content"]').innerHTML = html;
                    wrapper.querySelector('[data-key="context-label"]').textContent = label;
                    wrapper.querySelector('[data-key="context-position"]').textContent = posLabel;
                }

                function scrollToNewContent(direction) {
                    const ctxBlock = wrapper.querySelector('.context-block');
                    const newlyRevealed = ctxBlock.querySelectorAll('.newly-revealed');
                    if (newlyRevealed.length === 0) return;
                    const target = direction === 'up' ? newlyRevealed[0] : newlyRevealed[newlyRevealed.length - 1];
                    target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }

                wrapper.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (e.target.closest('button')) return;
                    exState.expanded = !exState.expanded;
                    wrapper.querySelector('.snippet-preview').classList.toggle('hidden', exState.expanded);
                    wrapper.querySelector('.expanded-content').classList.toggle('hidden', !exState.expanded);
                    if (exState.expanded) onOpenExcerpt(ex, exState);
                });

                wrapper.querySelector('.prev-line-btn').addEventListener('click', (e) => {
                    e.stopPropagation();
                    exState.lineContextBefore++;
                    const { start: matchStart } = exState.matchedLineRange;
                    const newFromLine = Math.max(0, matchStart - exState.lineContextBefore);
                    exState.lastAddedIdx = exState.lineIndex.lineToMsgIndex[newFromLine];
                    renderExcerptContext();
                    scrollToNewContent('up');
                });

                wrapper.querySelector('.prev-para-btn').addEventListener('click', async (e) => {
                    e.stopPropagation();
                    if (exState.visibleParaStart > 0) {
                        exState.visibleParaStart--;
                        const idx = exState.visibleParaStart;
                        exState.lastAddedIdx = idx;
                        if (!exState.messages.some(m => m.message_index === idx)) {
                            const res = await fetch(`${BASE_URL}/conversations/${group.conversation_id}?start_index=${idx}&end_index=${idx}`);
                            const conv = await res.json();
                            exState.messages = [...exState.messages, ...(conv.messages || [])].sort((a, b) => a.message_index - b.message_index);
                            exState.paragraphs = buildParagraphIndex(exState.messages);
                        }
                        // If the newly revealed paragraph is short, also pull in the next adjacent block
                        // (treats tightly-related short blocks as one readable section).
                        if (!structured && exState.visibleParaStart > 0) {
                            const revealedMsg = exState.messages.find(m => m.message_index === idx);
                            const isShort = revealedMsg && revealedMsg.content.replace(/\s/g, '').length <= 80;
                            if (isShort) {
                                exState.visibleParaStart--;
                                const idx2 = exState.visibleParaStart;
                                if (!exState.messages.some(m => m.message_index === idx2)) {
                                    const res2 = await fetch(`${BASE_URL}/conversations/${group.conversation_id}?start_index=${idx2}&end_index=${idx2}`);
                                    const conv2 = await res2.json();
                                    exState.messages = [...exState.messages, ...(conv2.messages || [])].sort((a, b) => a.message_index - b.message_index);
                                    exState.paragraphs = buildParagraphIndex(exState.messages);
                                }
                            }
                        }
                        renderExcerptContext();
                        scrollToNewContent('up');
                    }
                });

                wrapper.querySelector('.next-line-btn').addEventListener('click', (e) => {
                    e.stopPropagation();
                    exState.lineContextAfter++;
                    const { end: matchEnd } = exState.matchedLineRange;
                    const newToLine = Math.min(exState.lineIndex.allLines.length - 1, matchEnd + exState.lineContextAfter);
                    exState.lastAddedIdx = exState.lineIndex.lineToMsgIndex[newToLine];
                    renderExcerptContext();
                    scrollToNewContent('down');
                });

                wrapper.querySelector('.next-para-btn').addEventListener('click', async (e) => {
                    e.stopPropagation();
                    if (exState.visibleParaEnd < exState.totalMessages - 1) {
                        exState.visibleParaEnd++;
                        const idx = exState.visibleParaEnd;
                        exState.lastAddedIdx = idx;
                        if (!exState.messages.some(m => m.message_index === idx)) {
                            const res = await fetch(`${BASE_URL}/conversations/${group.conversation_id}?start_index=${idx}&end_index=${idx}`);
                            const conv = await res.json();
                            exState.messages = [...exState.messages, ...(conv.messages || [])].sort((a, b) => a.message_index - b.message_index);
                            exState.paragraphs = buildParagraphIndex(exState.messages);
                        }
                        // If the newly revealed paragraph is short, also pull in the next adjacent block
                        // (treats tightly-related short blocks as one readable section).
                        if (!structured && exState.visibleParaEnd < exState.totalMessages - 1) {
                            const revealedMsg = exState.messages.find(m => m.message_index === idx);
                            const isShort = revealedMsg && revealedMsg.content.replace(/\s/g, '').length <= 80;
                            if (isShort) {
                                exState.visibleParaEnd++;
                                const idx2 = exState.visibleParaEnd;
                                if (!exState.messages.some(m => m.message_index === idx2)) {
                                    const res2 = await fetch(`${BASE_URL}/conversations/${group.conversation_id}?start_index=${idx2}&end_index=${idx2}`);
                                    const conv2 = await res2.json();
                                    exState.messages = [...exState.messages, ...(conv2.messages || [])].sort((a, b) => a.message_index - b.message_index);
                                    exState.paragraphs = buildParagraphIndex(exState.messages);
                                }
                            }
                        }
                        renderExcerptContext();
                        scrollToNewContent('down');
                    }
                });

                async function onOpenExcerpt(targetEx, targetExState) {
                    if (targetExState.messages || targetExState.loading) return;
                    targetExState.loading = true;

                    const mStart = targetEx.message_start_index;
                    const mEnd = targetEx.message_end_index;
                    const currentQuery = searchInput.value.trim();
                    const snippetContainer = wrapper.querySelector('[data-key="context-content"]');

                    try {
                        let conv;
                        if (structured) {
                            const res = await fetch(`${BASE_URL}/conversations/${group.conversation_id}?highlight_query=${encodeURIComponent(currentQuery)}`);
                            if (!res.ok) throw new Error(`HTTP ${res.status}`);
                            conv = await res.json();
                        } else {
                            // If totalMessages was 0 initialized, we use a large fallback so fEnd is at least mEnd + 1
                            const total = targetExState.totalMessages || 10000;
                            const fStart = Math.max(0, mStart - 2);
                            const fEnd = Math.min(total - 1, mEnd + 1);
                            const res = await fetch(`${BASE_URL}/conversations/${group.conversation_id}?highlight_query=${encodeURIComponent(currentQuery)}&start_index=${fStart}&end_index=${fEnd}`);
                            if (!res.ok) throw new Error(`HTTP ${res.status}`);
                            conv = await res.json();
                        }

                        if (conv) {
                            targetExState.messages = (conv.messages || []).sort((a, b) => a.message_index - b.message_index);
                            
                            // Capture actual count from server if available
                            if (conv.message_count !== undefined) {
                                targetExState.totalMessages = conv.message_count;
                            }

                            if (structured) {
                                targetExState.lineIndex = buildLineIndex(targetExState.messages);
                                targetExState.matchedLineRange = findMatchedLineRange(targetExState.lineIndex.allLines, targetEx.matched_chunk_text);
                                targetExState.visibleParaStart = targetEx.message_start_index;
                                targetExState.visibleParaEnd = targetEx.message_end_index;
                                targetExState.paragraphs = buildParagraphIndex(targetExState.messages);
                            } else {
                                targetExState.paragraphs = buildParagraphIndex(targetExState.messages);
                                targetExState.matchedParaRange = findMatchedParagraphRange(targetExState.paragraphs, targetEx.matched_chunk_text);
                                targetExState.visibleParaStart = conv.messages && conv.messages.length ? conv.messages[0].message_index : 0;
                                targetExState.visibleParaEnd = conv.messages && conv.messages.length ? conv.messages[conv.messages.length - 1].message_index : 0;

                                // Index lines for raw text navigation
                                targetExState.lineIndex = buildLineIndex(targetExState.messages);
                                targetExState.matchedLineRange = findMatchedLineRange(targetExState.lineIndex.allLines, targetEx.matched_chunk_text);
                            }
                        }
                        renderExcerptContext();
                    } catch (err) {
                        console.error('Excerpt context load failed:', err);
                        if (snippetContainer) {
                            snippetContainer.innerHTML = `<div class="context-error">Failed to load context. <button class="retry-btn" style="font-size:0.7rem; padding: 2px 4px;">Retry</button></div>`;
                            snippetContainer.querySelector('.retry-btn').onclick = (e) => {
                                e.stopPropagation();
                                targetExState.loading = false;
                                onOpenExcerpt(targetEx, targetExState);
                            };
                        }
                    } finally {
                        targetExState.loading = false;
                    }
                }
            });

            function toggleExpand(e) {
                if (e) e.stopPropagation();
                groupState.expanded = !groupState.expanded;
                card.classList.toggle('expanded', groupState.expanded);
                card.querySelector('.excerpts-container').classList.toggle('hidden', !groupState.expanded);
                card.querySelector('.toggle-btn').textContent = groupState.expanded ? 'Collapse' : 'Expand';
                
                // Mark viewed on any expansion
                if (groupState.expanded) {
                    visitedResults.add(group.conversation_id);
                    card.classList.add('visited');
                }

                // If expanding for the first time in this session, auto-expand the first excerpt
                if (groupState.expanded && group.excerpts.length > 0 && !groupState.excerpts[0].expanded) {
                    const firstEx = card.querySelector('.excerpt-wrapper');
                    if (firstEx) firstEx.click();
                }
            }
            card.querySelector('.toggle-btn').addEventListener('click', toggleExpand);
            card.addEventListener('click', toggleExpand);
            card.querySelector('.library-nav-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                visitedResults.add(group.conversation_id);
                card.classList.add('visited');
                highlightLibraryItem(group.conversation_id);
            });

            resultsContainer.appendChild(card);
        });
    }

    function expandCard(card) {
        card.classList.add('expanded');
        card.querySelector('.expanded-content').classList.remove('hidden');
        card.querySelector('.collapsed-snippet').classList.add('hidden');
        card.querySelector('.toggle-btn').textContent = 'Collapse';
    }

    function collapseCard(card) {
        card.classList.remove('expanded');
        card.querySelector('.expanded-content').classList.add('hidden');
        card.querySelector('.collapsed-snippet').classList.remove('hidden');
        card.querySelector('.toggle-btn').textContent = 'Expand';
    }

    function setStatus(msg, isError = false) {
        statusMessage.textContent = msg;
        statusMessage.style.color = isError ? 'red' : 'inherit';
    }

    function renderHighlightedText(text) {
        if (!text) return '';
        const escaped = escapeHTML(text);
        return escaped.replace(/\[\[(.*?)\]\]/g, '<span class="highlight">$1</span>');
    }

    // ── Raw paragraph text renderer ───────────────────────────────────────────
    // Used exclusively for raw-text import paragraph blocks.
    // Identical to renderHighlightedText but also converts \n → <br> so that
    // within-paragraph line breaks (poetry stanzas, multi-line prose) are
    // preserved visually. Structured conversation paths use renderHighlightedText.
    function renderParagraphText(text) {
        if (!text) return '';
        const escaped = escapeHTML(text);
        const highlighted = escaped.replace(/\[\[(.*?)\]\]/g, '<span class="highlight">$1</span>');
        return highlighted.replace(/\n/g, '<br>');
    }

    function escapeHTML(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ── Import Flow ───────────────────────────────────────────────────────────

    if (importProjectSelect) {
        importProjectSelect.addEventListener('change', () => {
            if (importProjectSelect.value === 'new') {
                newProjectInput.classList.remove('hidden');
                newProjectInput.required = true;
                newProjectInput.focus();
            } else {
                newProjectInput.classList.add('hidden');
                newProjectInput.required = false;
                if (importProjectSelect.value) {
                    sessionStorage.setItem('thoughtreach_last_project_id', importProjectSelect.value);
                }
            }
        });
    }

    const modeRadios = document.querySelectorAll('input[name="import-mode"]');

    // Restore mode
    const lastMode = sessionStorage.getItem('thoughtreach_last_import_mode');
    if (lastMode) {
        modeRadios.forEach(r => {
            if (r.value === lastMode) r.checked = true;
        });
    }

    const importTextarea = document.getElementById('import-text');

    // ── Success State Clearance ──────────────────────────────────────────────
    function clearImportStatus() {
        if (importStatusDiv) {
            importStatusDiv.innerHTML = '';
            importStatusDiv.textContent = '';
        }
    }

    importTitleInput.addEventListener('input', clearImportStatus);
    importTextarea.addEventListener('input', clearImportStatus);
    importProjectSelect.addEventListener('change', clearImportStatus);
    newProjectInput.addEventListener('input', clearImportStatus);
    modeRadios.forEach(r => r.addEventListener('change', (e) => {
        const mode = e.target.value;
        sessionStorage.setItem('thoughtreach_last_import_mode', mode);
        updatePlaceholder(mode);
        clearImportStatus();
    }));

    function updatePlaceholder(mode) {
        if (mode === 'structured') {
            importTextarea.placeholder = "User: How do I build this?\n\nAssistant: You can follow these steps...";
        } else {
            importTextarea.placeholder = "Paste your raw text or notes here. Paragraphs will be preserved for retrieval.";
        }
    }

    // Initial call for restored mode
    const currentMode = document.querySelector('input[name="import-mode"]:checked')?.value;
    if (currentMode) updatePlaceholder(currentMode);

    const importForm = document.getElementById('import-form');
    if (importForm) {
        importForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const importBtn = document.getElementById('import-submit-btn');
            const statusDiv = importStatusDiv;

            const title = importTitleInput.value.trim();
            const text = importTextarea.value.trim();
            const mode = document.querySelector('input[name="import-mode"]:checked')?.value || 'paste';
            let projectId = importProjectSelect.value;
            let projectName = '';

            if (!title || !text || !projectId) return;

            importBtn.disabled = true;
            importStatusDiv.classList.add('status-stable');
            statusDiv.style.color = 'inherit';

            // ── Live import progress ticker ────────────────────────────────────
            // Gives clear "still working" feedback for large imports without any
            // backend changes. Estimates phase from elapsed time.
            const importStartTime = Date.now();
            const phases = [
                'Analysing text…',
                'Splitting into chunks…',
                'Generating embeddings…',
                'Storing in database…',
                'Finalising import…',
            ];
            let phaseIdx = 0;

            function updateImportStatus() {
                const elapsed = Math.floor((Date.now() - importStartTime) / 1000);
                // Advance phase hint every 8 seconds
                phaseIdx = Math.min(Math.floor(elapsed / 8), phases.length - 1);
                const dots = '.'.repeat((elapsed % 3) + 1);
                statusDiv.textContent = `Importing${dots}  ${phases[phaseIdx]}  (${elapsed}s)`;
            }

            updateImportStatus(); // immediate first render
            const importTicker = setInterval(updateImportStatus, 1000);

            try {
                // If creating a new project
                if (projectId === 'new') {
                    const newName = newProjectInput.value.trim();
                    if (!newName) throw new Error('Project name is required');
                    projectName = newName;

                    const catRes = await fetch(`${BASE_URL}/categories`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: newName })
                    });

                    if (!catRes.ok) {
                        const errText = await catRes.text();
                        if (catRes.status === 409) throw new Error('A project with that name already exists');
                        throw new Error('Failed to create project: ' + errText);
                    }

                    const catData = await catRes.json();
                    projectId = catData.id;

                    // Add to dropdowns locally
                    const opt1 = new Option(newName, projectId);
                    const opt2 = new Option(newName, projectId);
                    importProjectSelect.add(opt2, importProjectSelect.options[importProjectSelect.options.length - 1]);
                    categorySelect.appendChild(opt1);

                    // Keep the newly created project selected and save to session
                    importProjectSelect.value = projectId;
                    sessionStorage.setItem('thoughtreach_last_project_id', projectId);
                    newProjectInput.classList.add('hidden');
                    newProjectInput.required = false;
                    newProjectInput.value = '';
                } else {
                    projectName = importProjectSelect.options[importProjectSelect.selectedIndex].text;
                }

                const payload = {
                    title: title,
                    raw_text: text,
                    category_id: projectId,
                    source_type: mode
                };

                const res = await fetch(`${BASE_URL}/ingest/paste`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!res.ok) throw new Error('Import failed completely');
                const data = await res.json();

                if (data.status === 'skipped') {
                    clearInterval(importTicker);
                    const metricsHtml = renderImportMetricsHtml(data.metrics, true);

                    importStatusDiv.classList.add('status-stable');
                    statusDiv.innerHTML = `
                        <div class="import-duplicate-panel">
                            <div class="import-duplicate-header">
                                <span style="font-size: 1.1rem;">&#9888;</span>
                                Duplicate content detected — ingestion skipped.
                            </div>
                            ${metricsHtml}
                        </div>
                    `.trim();
                    statusDiv.style.color = 'inherit';
                } else {
                    clearInterval(importTicker);
                    const sourceTypeLabel = mode === 'structured' ? 'Structured Conversation' : 'Raw Imported Text';
                    const metricsHtml = renderImportMetricsHtml(data.metrics, false);

                    importStatusDiv.classList.add('status-stable');
                    statusDiv.innerHTML = `
                        <div class="import-success-panel">
                            <div class="import-success-header">
                                <span style="font-size: 1.1rem;">&#10004;</span>
                                Ingestion Complete
                            </div>
                            <div class="import-success-meta">
                                <span><strong>Project:</strong> ${escapeHTML(projectName)}</span>
                                <span><strong>Title:</strong> ${escapeHTML(title)}</span>
                                <span><strong>Type:</strong> ${sourceTypeLabel}</span>
                            </div>
                            ${metricsHtml}
                            <div class="import-success-actions">
                                <button class="import-success-btn" id="import-open-library-btn">Open in Library</button>
                                <button class="import-success-btn" id="import-search-now-btn">Search Now</button>
                            </div>
                        </div>
                    `.trim();
                    statusDiv.style.color = 'inherit';

                    // Clear fields but preserve project and mode selection
                    importTextarea.value = '';
                    importTextarea.scrollTop = 0;
                    importTextarea.setSelectionRange(0, 0);
                    importTitleInput.value = '';
                    importTitleInput.focus();
                    importTitleInput.select();
                    importTitleInput.scrollIntoView({ behavior: 'smooth', block: 'center' });

                    // Attach action listeners
                    const openLibBtn = document.getElementById('import-open-library-btn');
                    if (openLibBtn) {
                        openLibBtn.addEventListener('click', () => {
                            highlightLibraryItem(data.conversation_id);
                        });
                    }
                    const searchNowBtn = document.getElementById('import-search-now-btn');
                    if (searchNowBtn) {
                        searchNowBtn.addEventListener('click', () => {
                            navSearchBtn.click();
                            searchInput.value = title;
                            searchInput.focus();
                        });
                    }

                    // Metrics copy functionality
                    attachMetricsListeners(data.metrics, title);
                }
            } catch (err) {
                clearInterval(importTicker);
                console.error(err);
                importStatusDiv.classList.add('status-stable');
                statusDiv.textContent = `Error: ${err.message}`;
                statusDiv.style.color = 'red';
            } finally {
                importBtn.disabled = false;
            }
        });
    }

    // ── Library View ──────────────────────────────────────────────────────────


    navLibraryBtn.addEventListener('click', () => {
        // Track Search results scroll before leaving
        if (!searchView.classList.contains('hidden')) {
            searchScrollPos = window.scrollY;
        }

        libraryView.classList.remove('hidden');
        searchView.classList.add('hidden');
        importView.classList.add('hidden');
        navLibraryBtn.classList.add('active');
        navSearchBtn.classList.remove('active');
        navImportBtn.classList.remove('active');
        navHomeBtn.classList.remove('hidden');
        viewStack.push('library');
        updateNavVisibility();
        // Load lazily on first visit; after that use refresh button
        if (!libraryView.dataset.loaded) {
            loadLibrary();
        }
    });

    document.getElementById('library-refresh-btn').addEventListener('click', loadLibrary);

    document.getElementById('library-back-btn').addEventListener('click', () => {
        document.getElementById('library-open-view').classList.add('hidden');
        document.getElementById('library-delete-confirm').classList.add('hidden');
        document.getElementById('library-content').parentElement.querySelector('.library-header').classList.remove('hidden');
        document.getElementById('library-content').classList.remove('hidden');
        currentLibraryId = null;
    });

    const libraryDeleteBtn = document.getElementById('library-delete-btn');
    const libraryDeleteConfirm = document.getElementById('library-delete-confirm');
    const libraryDeleteCancelBtn = document.getElementById('library-delete-cancel-btn');
    const libraryDeleteProceedBtn = document.getElementById('library-delete-proceed-btn');

    libraryDeleteBtn.addEventListener('click', () => {
        libraryDeleteConfirm.classList.remove('hidden');
    });

    libraryDeleteCancelBtn.addEventListener('click', () => {
        libraryDeleteConfirm.classList.add('hidden');
    });

    libraryDeleteProceedBtn.addEventListener('click', async () => {
        if (!currentLibraryId) return;
        libraryDeleteProceedBtn.disabled = true;
        const originalText = libraryDeleteProceedBtn.textContent;
        libraryDeleteProceedBtn.textContent = 'Deleting...';
        try {
            const res = await fetch(`${BASE_URL}/conversations/${currentLibraryId}`, {
                method: 'DELETE'
            });
            if (!res.ok) throw new Error('Failed to delete conversation');

            // Clean up search state if this ID is there
            if (currentSearchResults && currentSearchResults.length > 0) {
                currentSearchResults = currentSearchResults.filter(r => r.conversation_id !== currentLibraryId);
                processAndRenderResults();
            }

            // Return to list and refresh
            libraryDeleteConfirm.classList.add('hidden');
            document.getElementById('library-back-btn').click();
            loadLibrary();
        } catch (err) {
            console.error(err);
            alert('Failed to delete: ' + err.message);
        } finally {
            libraryDeleteProceedBtn.disabled = false;
            libraryDeleteProceedBtn.textContent = originalText;
        }
    });

    async function loadLibrary() {
        const container = document.getElementById('library-content');
        container.innerHTML = '<div class="library-empty">Loading...</div>';
        try {
            const res = await fetch(`${BASE_URL}/library`);
            if (!res.ok) throw new Error('Failed to fetch library');
            const items = await res.json();

            libraryView.dataset.loaded = 'true';

            if (items.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <h3>Nothing imported yet</h3>
                        <p>Use the <strong>Import</strong> tab to add your first conversation or archives to the library.</p>
                    </div>
                `;
                return;
            }

            // Group by project (category), uncategorised items put in an "Uncategorised" group
            const groups = {};
            items.forEach(item => {
                const key = item.category_id || '__none__';
                const label = item.category_name || 'Uncategorised';
                if (!groups[key]) groups[key] = { label, items: [] };
                groups[key].items.push(item);
            });

            // Sort groups: named projects alpha, uncategorised last
            const sortedKeys = Object.keys(groups).sort((a, b) => {
                if (a === '__none__') return 1;
                if (b === '__none__') return -1;
                return groups[a].label.localeCompare(groups[b].label);
            });

            container.innerHTML = '';
            sortedKeys.forEach(key => {
                const group = groups[key];
                const groupEl = document.createElement('div');
                groupEl.className = 'library-project-group';

                const toggle = document.createElement('button');
                toggle.className = 'library-project-toggle open';
                toggle.innerHTML = `
                    ${escapeHTML(group.label)}
                    <span class="library-project-count">${group.items.length}</span>
                    <span class="library-project-chevron">&#9654;</span>
                `;
                groupEl.appendChild(toggle);

                const list = document.createElement('div');
                list.className = 'library-item-list';

                group.items.forEach(item => {
                    const isRaw = (item.source_type === 'raw');
                    const typeLabel = isRaw ? 'Raw Imported Text' : 'Structured Conversation';
                    const typeCls = isRaw ? 'library-type-raw' : 'library-type-structured';
                    const dateStr = formatLibraryDate(item.imported_at);

                    const row = document.createElement('div');
                    row.className = 'library-item';
                    row.innerHTML = `
                        <span class="library-item-title" title="${escapeHTML(item.title)}">${escapeHTML(item.title)}</span>
                        <span class="library-type-badge ${typeCls}" style="font-size: 0.6rem;">${typeLabel}</span>
                        <span class="library-item-date">${dateStr}</span>
                        <div class="library-item-actions">
                            <button class="library-open-btn" data-id="${item.id}" data-title="${escapeHTML(item.title)}" data-source="${item.source_type}" data-project="${escapeHTML(group.label)}">Open</button>
                            <button class="library-row-delete-btn" data-id="${item.id}" title="Delete this conversation">Delete</button>
                        </div>
                    `;
                    row.addEventListener('click', (e) => {
                        if (e.target.closest('button')) return;
                        const openBtn = row.querySelector('.library-open-btn');
                        if (openBtn) openBtn.click();
                    });
                    list.appendChild(row);
                });

                groupEl.appendChild(list);
                container.appendChild(groupEl);

                // Collapse / expand toggle
                toggle.addEventListener('click', () => {
                    const isOpen = toggle.classList.contains('open');
                    toggle.classList.toggle('open', !isOpen);
                    list.classList.toggle('hidden', isOpen);
                });
            });

            // Open buttons
            container.querySelectorAll('.library-open-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const id = btn.dataset.id;
                    const title = btn.dataset.title;
                    const source = btn.dataset.source;
                    const project = btn.dataset.project;
                    await openLibraryItem(id, title, source, project);
                });
            });

            // Row-level delete buttons
            container.querySelectorAll('.library-row-delete-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    currentLibraryId = btn.dataset.id;
                    // Show confirmation UI (which is shared)
                    document.getElementById('library-delete-confirm').classList.remove('hidden');
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                });
            });

        } catch (err) {
            console.error(err);
            container.innerHTML = `<div class="library-empty">Failed to load library. Is the backend running?</div>`;
        }
    }

    async function openLibraryItem(id, title, source, project, anchor = null) {
        currentLibraryId = id;

        const libraryContent = document.getElementById('library-content');
        const libraryHeader = libraryContent.previousElementSibling; // .library-header
        const openView = document.getElementById('library-open-view');
        const openContent = document.getElementById('library-open-content');

        // Update header meta
        document.getElementById('library-open-title').textContent = title;
        document.getElementById('library-open-project').textContent = project ? `in ${project}` : '';

        const isRaw = (source === 'raw');
        const typeBadge = document.getElementById('library-open-type-badge');
        typeBadge.textContent = isRaw ? 'Raw Imported Text' : 'Structured Conversation';
        typeBadge.className = `library-open-type-badge library-type-badge ${isRaw ? 'library-type-raw' : 'library-type-structured'}`;

        openContent.innerHTML = '<em style="opacity:0.5">Loading...</em>';

        // Switch visibility
        libraryContent.classList.add('hidden');
        libraryHeader.classList.add('hidden');
        openView.classList.remove('hidden');

        // Manage "Back to Search Result" button visibility
        const backToSearchBtn = document.getElementById('library-back-to-search-btn');
        if (anchor && searchReturnContext && searchReturnContext.conversationId === id) {
            backToSearchBtn.classList.remove('hidden');
        } else {
            backToSearchBtn.classList.add('hidden');
        }

        try {
            const res = await fetch(`${BASE_URL}/conversations/${id}`);
            if (!res.ok) throw new Error('Not found');
            const conv = await res.json();
            const messages = (conv.messages || []).sort((a, b) => a.message_index - b.message_index);

            // Update header with date from conv
            if (conv.imported_at) {
                document.getElementById('library-open-date').textContent = `• Imported ${formatLibraryDate(conv.imported_at)}`;
            }

            if (isRaw) {
                // Raw: render paragraphs, mark matched block if we have anchor
                openContent.innerHTML = messages.map((m, i) => {
                    const isMatch = anchor && anchor.matchedText &&
                        m.content.includes(anchor.matchedText.substring(0, 80));
                    return `<div class="para-block para-block-revealed${isMatch ? ' lib-anchor-target' : ''}" data-msg-idx="${i}">${renderParagraphText(m.content)}</div>`;
                }).join('');
            } else {
                // Structured: render user/assistant messages, mark by index range
                openContent.innerHTML = messages.map(m => {
                    const roleClass = m.role === 'user' ? 'user' : 'assistant';
                    const roleLabel = m.role === 'user' ? 'User' : 'Assistant';
                    const isMatch = anchor &&
                        m.message_index >= anchor.msgStart &&
                        m.message_index <= anchor.msgEnd;
                    return `
                        <div class="message ${roleClass}${isMatch ? ' lib-anchor-target' : ''}" data-msg-idx="${m.message_index}">
                            <div class="message-role">${roleLabel}</div>
                            <div class="message-content">${escapeHTML(m.content)}</div>
                        </div>
                    `.trim();
                }).join('');
            }

            // Scroll to and flash the anchor target
            const anchorEl = openContent.querySelector('.lib-anchor-target');
            if (anchorEl) {
                // Small delay to allow layout
                setTimeout(() => {
                    anchorEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    anchorEl.classList.add('lib-anchor-flash');
                    setTimeout(() => anchorEl.classList.remove('lib-anchor-flash'), 3000);
                }, 80);
            }
        } catch (err) {
            openContent.innerHTML = `<em style="color:red">Failed to load content.</em>`;
            console.error(err);
        }
    }

    function formatLibraryDate(isoStr) {
        if (!isoStr) return '';
        const d = new Date(isoStr);
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    }

    const librarySearchTitleBtn = document.getElementById('library-search-title-btn');
    if (librarySearchTitleBtn) {
        librarySearchTitleBtn.addEventListener('click', () => {
            const title = document.getElementById('library-open-title').textContent;
            if (!title) return;

            // Clear return context as this is a fresh manual search
            searchReturnContext = null;
            const backBtn = document.getElementById('library-back-to-search-btn');
            if (backBtn) backBtn.classList.add('hidden');

            navSearchBtn.click();
            searchInput.value = title;
            sessionStorage.setItem('thoughtreach_last_search_query', title);

            // Reset filters to "All" for new broad-scoped library-origin search
            categorySelect.value = '';
            sessionStorage.setItem('thoughtreach_last_category_id', '');

            // Reset sort to "Most Relevant"
            const sortSelect = document.getElementById('result-sort-select');
            if (sortSelect) {
                sortSelect.value = 'relevant';
                sessionStorage.setItem('thoughtreach_last_sort_mode', 'relevant');
            }

            // Reset display mode to "All Matches"
            const displaySelect = document.getElementById('result-display-select');
            if (displaySelect) {
                displaySelect.value = 'all';
                sessionStorage.setItem('thoughtreach_last_display_mode', 'all');
            }

            searchInput.focus();
        });
    }

    async function highlightLibraryItem(id, anchor = null) {
        navLibraryBtn.click();

        // Polling wait if library content isn't fully rendered after tab click
        const maxWait = 3000;
        const startWait = Date.now();
        while ((!libraryView.dataset.loaded || !libraryView.querySelector(`.library-open-btn`)) && (Date.now() - startWait < maxWait)) {
            await new Promise(r => setTimeout(r, 100));
        }

        const openBtn = libraryView.querySelector(`.library-open-btn[data-id="${id}"]`);
        if (openBtn) {
            const row = openBtn.parentElement;
            const group = row.closest('.library-project-group');
            const toggle = group.querySelector('.library-project-toggle');
            const list = group.querySelector('.library-item-list');

            // Expand project if hidden
            if (list.classList.contains('hidden') || !toggle.classList.contains('open')) {
                toggle.click();
            }

            // If coming from search with anchor, open the item directly at the matched location.
            if (anchor) {
                const title = openBtn.dataset.title;
                const source = anchor.source || openBtn.dataset.source;
                const project = openBtn.dataset.project;
                await openLibraryItem(id, title, source, project, anchor);
            } else {
                // Fallback: just scroll and flash the library list row 
                row.scrollIntoView({ behavior: 'smooth', block: 'center' });
                row.classList.remove('item-highlight');
                void row.offsetWidth;
                row.classList.add('item-highlight');
            }
        }
    }

    // ── Return to Search Result Logic ──────────────────────────────────────────

    const backToSearchBtn = document.getElementById('library-back-to-search-btn');
    if (backToSearchBtn) {
        backToSearchBtn.addEventListener('click', () => {
            if (!searchReturnContext) {
                navSearchBtn.click();
                searchInput.focus();
                return;
            }

            // Restore state
            navSearchBtn.click();
            searchInput.value = searchReturnContext.query;
            sessionStorage.setItem('thoughtreach_last_search_query', searchReturnContext.query);
            categorySelect.value = searchReturnContext.categoryId;
            sessionStorage.setItem('thoughtreach_last_category_id', searchReturnContext.categoryId);

            document.getElementById('result-sort-select').value = searchReturnContext.sortMode;
            sessionStorage.setItem('thoughtreach_last_sort_mode', searchReturnContext.sortMode);

            document.getElementById('result-display-select').value = searchReturnContext.displayMode;
            sessionStorage.setItem('thoughtreach_last_display_mode', searchReturnContext.displayMode);

            // Highlight the card if it still exists (result was cached)
            highlightSearchResult(searchReturnContext.conversationId);
        });
    }

    async function highlightSearchResult(conversationId) {
        // Switch to tab
        navSearchBtn.click();

        // Check if results exist
        const cards = resultsContainer.querySelectorAll('.result-card');
        let targetCard = null;

        // Try to find card by its Open in Library button data-id
        for (const card of cards) {
            const btn = card.querySelector('.library-nav-btn');
            if (btn && btn.dataset.id === conversationId) {
                targetCard = card;
                break;
            }
        }

        if (targetCard) {
            targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });

            // Add flash highlight style
            targetCard.classList.remove('item-highlight');
            void targetCard.offsetWidth; // Trigger reflow 
            targetCard.classList.add('item-highlight');
        } else {
            // Fallback: search input focus
            searchInput.focus();
        }
    }

    // ── Search Results Processing ────────────────────────────────────────────

    function processAndRenderResults() {
        if (!currentSearchResults.length) return;

        const sortMode = document.getElementById('result-sort-select').value;
        const searchSummary = document.getElementById('search-summary');
        const searchHint = document.getElementById('search-refinement-hint');
        const headerRow = document.getElementById('results-header-row');

        if (headerRow) headerRow.classList.remove('hidden');

        // Group by conversation_id
        const groupMap = new Map();
        currentSearchResults.forEach(res => {
            if (!groupMap.has(res.conversation_id)) {
                groupMap.set(res.conversation_id, {
                    conversation_id: res.conversation_id,
                    conversation_title: res.conversation_title,
                    category_name: res.category_name,
                    conversation_source_type: res.conversation_source_type,
                    imported_at: res.imported_at,
                    max_score: res.similarity_score,
                    results: []
                });
            }
            const group = groupMap.get(res.conversation_id);
            group.results.push(res);
            if (res.similarity_score > group.max_score) {
                group.max_score = res.similarity_score;
            }
        });

        const groups = Array.from(groupMap.values());

        // Process each group's results into merged excerpts
        groups.forEach(group => {
            // Sort by message position
            group.results.sort((a, b) => a.message_start_index - b.message_start_index);

            const merged = [];
            group.results.forEach(res => {
                if (merged.length > 0) {
                    const last = merged[merged.length - 1];
                    // Overlap or adjacency merging
                    if (res.message_start_index <= last.message_end_index + 1) {
                        last.message_start_index = Math.min(last.message_start_index, res.message_start_index);
                        last.message_end_index = Math.max(last.message_end_index, res.message_end_index);
                        return;
                    }
                }
                merged.push({
                    message_start_index: res.message_start_index,
                    message_end_index: res.message_end_index,
                    matched_chunk_text: res.matched_chunk_text
                });
            });
            group.excerpts = merged;
        });

        // 2. Update Summary
        const isCapped = (currentSearchResults.length === SEARCH_LIMIT);
        const itemCount = groups.length;
        const resCount = currentSearchResults.length;
        const categoryId = categorySelect.value;
        const projectText = (categoryId && categorySelect.selectedIndex > 0)
            ? ` in Project: <strong>${escapeHTML(categorySelect.options[categorySelect.selectedIndex].text)}</strong>`
            : '';

        const countPrefix = isCapped ? 'Showing first ' : '';
        const itemWord = itemCount === 1 ? 'imported item' : 'imported items';

        searchSummary.innerHTML = `${countPrefix}<strong>${resCount}</strong> matches across <strong>${itemCount}</strong> ${itemWord}${projectText}`;
        searchSummary.classList.remove('hidden');

        if (isCapped) {
            searchHint.classList.remove('hidden');
        } else {
            searchHint.classList.add('hidden');
        }

        // 3. Sort groups
        if (sortMode === 'relevant') {
            groups.sort((a, b) => b.max_score - a.max_score);
        } else if (sortMode === 'newest') {
            groups.sort((a, b) => new Date(b.imported_at) - new Date(a.imported_at));
        } else if (sortMode === 'oldest') {
            groups.sort((a, b) => new Date(a.imported_at) - new Date(b.imported_at));
        }

        renderResults(groups);
    }

    document.getElementById('result-display-select').addEventListener('change', processAndRenderResults);
    document.getElementById('result-sort-select').addEventListener('change', processAndRenderResults);

    // ── Metrics Rendering Helpers ────────────────────────────────────────────

    function renderImportMetricsHtml(metrics, isDuplicate = false) {
        if (!metrics || !metrics.stages) return '';

        let innerContent = '';
        if (isDuplicate) {
            innerContent = `
                <div class="metrics-row">
                    <span><strong>Size Checked:</strong> ${metrics.import_size_chars.toLocaleString()} chars</span>
                </div>
                <div class="metrics-row">
                    <span class="metrics-label" style="color: #c2410c;">Duplicate Check:</span> ${metrics.stages.duplicate_check_s}s
                </div>
            `;
        } else {
            const stages = metrics.stages;
            const keys = ['parse_s', 'msg_and_chunk_build_s', 'embed_s', 'db_write_s'];
            let slowest = '';
            let maxVal = -1;
            keys.forEach(k => {
                if (stages[k] > maxVal) {
                    maxVal = stages[k];
                    slowest = k;
                }
            });

            const fmt = (k, label, val) => {
                const isSlowest = (k === slowest);
                const cls = isSlowest ? 'class="slowest-stage-highlight"' : '';
                const hint = isSlowest ? ' (slowest)' : '';
                return `<span ${cls}>${label}: ${val}s${hint}</span>`;
            };

            innerContent = `
                <div class="metrics-header-row">
                    <span style="font-weight: 700; opacity: 0.9;">Import Performance</span>
                    <button class="metrics-copy-btn" id="metrics-copy-btn" title="Copy metrics to clipboard">Copy</button>
                </div>
                <div class="metrics-row">
                    <span><strong>Import stats:</strong> ${metrics.import_size_chars.toLocaleString()} chars | ${metrics.paragraph_count} paras | ${metrics.chunk_count} chunks | ${metrics.embedding_count} embeddings</span>
                </div>
                <div class="metrics-row">
                    <span class="metrics-label">Total Duration:</span> ${metrics.total_s}s
                </div>
                <div class="metrics-row" style="font-size: 0.68rem; opacity: 0.8;">
                    <span><strong>Stages:</strong> 
                        ${fmt('parse_s', 'Parse', stages.parse_s)} | 
                        ${fmt('msg_and_chunk_build_s', 'Build', stages.msg_and_chunk_build_s)} | 
                        ${fmt('embed_s', 'Embed', stages.embed_s)} | 
                        ${fmt('db_write_s', 'DB Write', stages.db_write_s)}
                    </span>
                </div>
            `;
        }

        const panelClass = isDuplicate ? 'import-duplicate-metrics' : 'import-performance-metrics';

        return `
            <div class="metrics-toggle-container">
                <button class="metrics-view-toggle" id="metrics-view-toggle" data-expanded="false">Show diagnostics</button>
                <div id="metrics-content-wrapper" class="hidden">
                    <div class="${panelClass}">
                        ${innerContent}
                    </div>
                </div>
            </div>
        `.trim();
    }

    function attachMetricsListeners(metrics, title) {
        const toggleBtn = document.getElementById('metrics-view-toggle');
        const contentWrapper = document.getElementById('metrics-content-wrapper');
        if (toggleBtn && contentWrapper) {
            toggleBtn.addEventListener('click', () => {
                const isExpanded = toggleBtn.getAttribute('data-expanded') === 'true';
                const nextExpanded = !isExpanded;
                toggleBtn.setAttribute('data-expanded', nextExpanded);
                toggleBtn.textContent = nextExpanded ? 'Hide diagnostics' : 'Show diagnostics';
                contentWrapper.classList.toggle('hidden', !nextExpanded);
            });
        }

        const copyBtn = document.getElementById('metrics-copy-btn');
        if (!copyBtn || !metrics) return;

        copyBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const m = metrics;
            const s = m.stages;
            const text = [
                `Import Performance Summary:`,
                `Title: ${title}`,
                `Total Time: ${m.total_s}s`,
                `Stats: ${m.import_size_chars.toLocaleString()} chars | ${m.paragraph_count} paras | ${m.chunk_count} chunks | ${m.embedding_count} embeddings`,
                `Stages: Parse: ${s.parse_s}s | Build: ${s.msg_and_chunk_build_s}s | Embed: ${s.embed_s}s | DB Write: ${s.db_write_s}s`
            ].join('\n');

            try {
                await navigator.clipboard.writeText(text);
                const originalText = copyBtn.textContent;
                copyBtn.textContent = 'Copied!';
                copyBtn.classList.add('success');
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                    copyBtn.classList.remove('success');
                }, 2000);
            } catch (err) {
                console.error('Failed to copy metrics:', err);
                copyBtn.textContent = 'Failed';
                setTimeout(() => { copyBtn.textContent = 'Copy'; }, 2000);
            }
        });
    }
});
