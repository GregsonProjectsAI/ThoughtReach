const BASE_URL = '';

document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-input');
    const categorySelect = document.getElementById('category-select');
    const resultsContainer = document.getElementById('results-container');
    const statusMessage = document.getElementById('status-message');
    const submitBtn = searchForm.querySelector('button');
    
    // Session state for result cards
    let sessionStates = {};
    let isSearching = false;

    // Initialization
    loadCategories();
    searchInput.focus();

    // Event Listeners
    searchForm.addEventListener('submit', handleSearch);

    async function loadCategories() {
        try {
            const response = await fetch(`${BASE_URL}/categories`);
            if (!response.ok) throw new Error('Failed to fetch categories');
            
            const categories = await response.json();
            
            categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category.id;
                option.textContent = category.name;
                categorySelect.appendChild(option);
            });
        } catch (error) {
            console.error('Category load error:', error);
            // Non-fatal, just log it. "All Categories" remains available.
            statusMessage.textContent = 'Warning: Could not load categories. Ensure backend is running.';
        }
    }

    async function handleSearch(event) {
        event.preventDefault();
        
        if (isSearching) return;
        
        const query = searchInput.value.trim();
        const categoryId = categorySelect.value || null;
        
        if (!query) return;

        isSearching = true;

        // Interaction lock
        if (submitBtn) submitBtn.disabled = true;
        searchInput.disabled = true;

        setStatus('Searching...');
        resultsContainer.innerHTML = '';
        sessionStates = {}; // Always reset state on every search execution

        try {
            const payload = { query, limit: 10 };
            if (categoryId) {
                payload.category_id = categoryId;
            }

            const response = await fetch(`${BASE_URL}/search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.status === 404) {
                setStatus('Category missing or server error. Please refresh and try again.', true);
                return;
            }

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const results = await response.json();
            
            if (results.length === 0) {
                setStatus('No relevant conversations found for this query.');
            } else {
                setStatus('');
                renderResults(results);
            }

        } catch (error) {
            console.error('Search error:', error);
            setStatus('Category missing or server error. Please refresh and try again.', true);
        } finally {
            // Re-enable interactions
            isSearching = false;
            if (submitBtn) submitBtn.disabled = false;
            searchInput.disabled = false;
            searchInput.focus();
        }
    }

    function renderResults(results) {
        results.forEach(result => {
            // Uniquely identify a result by conversation and span indices
            const resultKey = `r:${result.conversation_id}:${result.message_start_index}:${result.message_end_index}`;
            if (!sessionStates[resultKey]) {
                sessionStates[resultKey] = {
                    expanded: false,
                    showPrev: false,
                    showNext: false,
                    fullThread: false,
                    fullThreadContent: ''
                };
            }
            const state = sessionStates[resultKey];

            const card = document.createElement('div');
            card.className = 'result-card';
            
            // Build Score string
            const scorePercent = Math.round(result.similarity_score * 100) + '%';
            
            // Build Category HTML without invented fallbacks
            const categoryBadgeHtml = result.category_name 
                ? `<span class="badge category">${escapeHTML(result.category_name)}</span>`
                : ``;

            const fullText = result.matched_chunk_text || '';
            
            // Build Previous Exchange HTML
            let prevExchangeHtml = '';
            let hasPrevExchange = result.previous_exchange_user_message || result.previous_exchange_assistant_message;
            if (hasPrevExchange) {
                if (result.previous_exchange_user_message) {
                    prevExchangeHtml += `
                        <div class="message user">
                            <div class="message-role">User</div>
                            <div class="message-content">${renderHighlightedText(result.previous_exchange_user_message)}</div>
                        </div>
                    `;
                }
                if (result.previous_exchange_assistant_message) {
                    prevExchangeHtml += `
                        <div class="message assistant">
                            <div class="message-role">Assistant</div>
                            <div class="message-content">${renderHighlightedText(result.previous_exchange_assistant_message)}</div>
                        </div>
                    `;
                }
            }

            // Build Source Exchange HTML
            let sourceExchangeHtml = '';
            if (result.source_user_message) {
                const highlightClass = result.source_user_is_match ? ' highlight-message' : '';
                sourceExchangeHtml += `
                    <div class="message user${highlightClass}">
                        <div class="message-role">User</div>
                        <div class="message-content">${renderHighlightedText(result.source_user_message)}</div>
                    </div>
                `;
            }
            if (result.source_assistant_message) {
                const highlightClass = result.source_assistant_is_match ? ' highlight-message' : '';
                sourceExchangeHtml += `
                    <div class="message assistant${highlightClass}">
                        <div class="message-role">Assistant</div>
                        <div class="message-content">${renderHighlightedText(result.source_assistant_message)}</div>
                    </div>
                `;
            }

            // Build Next Exchange HTML
            let nextExchangeHtml = '';
            let hasNextExchange = result.next_exchange_user_message || result.next_exchange_assistant_message;
            if (hasNextExchange) {
                if (result.next_exchange_user_message) {
                    nextExchangeHtml += `
                        <div class="message user">
                            <div class="message-role">User</div>
                            <div class="message-content">${renderHighlightedText(result.next_exchange_user_message)}</div>
                        </div>
                    `;
                }
                if (result.next_exchange_assistant_message) {
                    nextExchangeHtml += `
                        <div class="message assistant">
                            <div class="message-role">Assistant</div>
                            <div class="message-content">${renderHighlightedText(result.next_exchange_assistant_message)}</div>
                        </div>
                    `;
                }
            }

            // Build HTML
            card.innerHTML = `
                <div class="result-header">
                    <h3 class="result-title">${escapeHTML(result.conversation_title)}</h3>
                    <div class="result-meta">
                        ${categoryBadgeHtml}
                        <span class="score-subtle" title="Similarity Score">${scorePercent}</span>
                        <button class="toggle-btn">Expand</button>
                    </div>
                </div>
                <!-- Collapsed Text View -->
                <div class="snippet-container snippet-preview collapsed-snippet">
                    ${renderHighlightedText(fullText)}
                </div>
                <!-- Expanded Content View -->
                <div class="expanded-content hidden">
                    ${hasPrevExchange ? `
                    <div class="exchange-expansion-controls before">
                        <button class="expand-prev-btn">Show 1 before</button>
                    </div>
                    <div class="surrounding-messages prev-exchange-container hidden">
                        ${prevExchangeHtml}
                    </div>` : ''}

                    ${sourceExchangeHtml ? `
                    <div class="exchange-divider">Source Exchange</div>
                    <div class="surrounding-messages">
                        ${sourceExchangeHtml}
                    </div>` : ''}
                    ${hasNextExchange ? `
                    <div class="surrounding-messages next-exchange-container hidden">
                        ${nextExchangeHtml}
                    </div>
                    <div class="exchange-expansion-controls after">
                        <button class="expand-next-btn">Show 1 after</button>
                    </div>` : ''}
                    
                    <div class="exchange-expansion-controls full-conv-controls">
                        <button class="full-conv-btn">${state.fullThread ? 'Collapse Full Thread' : 'Show Full Thread'}</button>
                    </div>
                    <div class="full-conversation-container ${state.fullThread ? '' : 'hidden'}">
                        ${state.fullThreadContent || ''}
                    </div>
                </div>
            `;

            // Apply initial states from session memory
            if (state.expanded) {
                card.classList.add('expanded');
                card.querySelector('.expanded-content').classList.remove('hidden');
                card.querySelector('.collapsed-snippet').classList.add('hidden');
                card.querySelector('.toggle-btn').textContent = 'Collapse';
            }
            if (state.showPrev) {
                const prevContainer = card.querySelector('.prev-exchange-container');
                if (prevContainer) {
                    prevContainer.classList.remove('hidden');
                    card.querySelector('.expand-prev-btn').textContent = 'Hide 1 before';
                }
            }
            if (state.showNext) {
                const nextContainer = card.querySelector('.next-exchange-container');
                if (nextContainer) {
                    nextContainer.classList.remove('hidden');
                    card.querySelector('.expand-next-btn').textContent = 'Hide 1 after';
                }
            }

            // Expansion Buttons Logic
            const prevBtn = card.querySelector('.expand-prev-btn');
            if (prevBtn) {
                prevBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const container = card.querySelector('.prev-exchange-container');
                    container.classList.toggle('hidden');
                    const isHidden = container.classList.contains('hidden');
                    prevBtn.textContent = isHidden ? 'Show 1 before' : 'Hide 1 before';
                    state.showPrev = !isHidden;
                });
            }

            const nextBtn = card.querySelector('.expand-next-btn');
            if (nextBtn) {
                nextBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const container = card.querySelector('.next-exchange-container');
                    container.classList.toggle('hidden');
                    const isHidden = container.classList.contains('hidden');
                    nextBtn.textContent = isHidden ? 'Show 1 after' : 'Hide 1 after';
                    state.showNext = !isHidden;
                });
            }

            // Full Conversation Logic
            const fullConvBtn = card.querySelector('.full-conv-btn');
            if (fullConvBtn) {
                fullConvBtn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const container = card.querySelector('.full-conversation-container');
                    const isHidden = container.classList.contains('hidden');
                    
                            if (isHidden) {
                                state.fullThread = true;
                                if (state.fullThreadContent) {
                                    container.innerHTML = state.fullThreadContent;
                                    container.classList.remove('hidden');
                                    fullConvBtn.textContent = 'Collapse Full Thread';
                                    return;
                                }

                                try {
                                    fullConvBtn.textContent = 'Loading...';
                                    fullConvBtn.disabled = true;
                                    
                                    const currentQuery = searchInput.value.trim();
                                    const res = await fetch(`${BASE_URL}/conversations/${result.conversation_id}?highlight_query=${encodeURIComponent(currentQuery)}`);
                                    if (!res.ok) throw new Error('API Error');
                                    const conv = await res.json();
                                    
                                    if (conv.messages && conv.messages.length > 0) {
                                        conv.messages.sort((a,b) => a.message_index - b.message_index);
                                        const msgsHtml = conv.messages.map(msg => {
                                            const roleClass = msg.role === 'user' ? 'user' : 'assistant';
                                            const roleLabel = msg.role === 'user' ? 'User' : 'Assistant';
                                            const isMatched = (msg.message_index >= result.message_start_index && msg.message_index <= result.message_end_index);
                                            const highlightClass = isMatched ? ' highlight-message' : '';
                                            
                                            return `
                                                <div class="message ${roleClass}${highlightClass}">
                                                    <div class="message-role">${roleLabel}</div>
                                                    <div class="message-content">${renderHighlightedText(msg.content)}</div>
                                                </div>
                                            `;
                                        }).join('');
                                        
                                        state.fullThreadContent = `
                                            <div class="exchange-divider">Full Chronological Conversation</div>
                                            <div class="surrounding-messages">
                                                ${msgsHtml}
                                            </div>
                                        `;
                                        container.innerHTML = state.fullThreadContent;
                                    } else {
                                        state.fullThreadContent = '<div class="snippet-container">No full conversation text available.</div>';
                                        container.innerHTML = state.fullThreadContent;
                                    }
                                    
                                    container.classList.remove('hidden');
                                    fullConvBtn.textContent = 'Collapse Full Thread';
                                } catch (err) {
                                    console.error(err);
                                    state.fullThread = false;
                                    fullConvBtn.textContent = 'Error loading';
                                } finally {
                                    fullConvBtn.disabled = false;
                                }
                            } else {
                                state.fullThread = false;
                                container.classList.add('hidden');
                                fullConvBtn.textContent = 'Show Full Thread';
                            }
                });
            }

            // Explicit Toggle Logic
            const toggleBtn = card.querySelector('.toggle-btn');
            toggleBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const isExpanding = !card.classList.contains('expanded');
                state.expanded = isExpanding;
                
                if (isExpanding) {
                    expandCard(card);
                } else {
                    collapseCard(card);
                }
            });

            card.addEventListener('click', () => {
                const isExpanding = !card.classList.contains('expanded');
                state.expanded = isExpanding;
                if (isExpanding) {
                    expandCard(card);
                } else {
                    collapseCard(card);
                }
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

    function renderMessages(messages) {
        if (!messages || messages.length === 0) return '<em>No surrounding context available.</em>';
        
        return messages.map(msg => {
            const roleLabel = msg.role === 'user' ? 'User' : 'Assistant';
            const roleClass = msg.role === 'user' ? 'user' : 'assistant';
            return `
                <div class="message ${roleClass}">
                    <div class="message-role">${roleLabel}</div>
                    <div class="message-content">${escapeHTML(msg.content)}</div>
                </div>
            `;
        }).join('');
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

    function escapeHTML(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
});
