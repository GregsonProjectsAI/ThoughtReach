const BASE_URL = '';

document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-input');
    const categorySelect = document.getElementById('category-select');
    const resultsContainer = document.getElementById('results-container');
    const statusMessage = document.getElementById('status-message');

    // Initialization
    loadCategories();

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
        
        const query = searchInput.value.trim();
        const categoryId = categorySelect.value || null;
        
        if (!query) return;

        setStatus('Searching...');
        resultsContainer.innerHTML = '';

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
        }
    }

    function renderResults(results) {
        results.forEach(result => {
            const card = document.createElement('div');
            card.className = 'result-card';
            
            // Build Score string
            const scorePercent = Math.round(result.similarity_score * 100) + '%';
            
            // Build Category HTML without invented fallbacks
            const categoryBadgeHtml = result.category_name 
                ? `<span class="badge category">${escapeHTML(result.category_name)}</span>`
                : ``;

            const fullText = result.matched_chunk_text || '';
            
            // Build Summary HTML
            const summaryHtml = result.conversation_summary 
                ? `<div class="snippet-container summary-snippet" style="margin-bottom: 1rem;">
                    <strong>Summary:</strong><br/>
                    ${escapeHTML(result.conversation_summary)}
                   </div>` 
                : '';

            // Build HTML
            card.innerHTML = `
                <div class="result-header">
                    <h3 class="result-title">${escapeHTML(result.conversation_title)}</h3>
                    <div class="result-meta">
                        ${categoryBadgeHtml}
                        <span class="badge score">${scorePercent}</span>
                    </div>
                </div>
                <!-- Collapsed Text View -->
                <div class="snippet-container snippet-preview collapsed-snippet">
                    ${renderHighlightedText(fullText)}
                </div>
                <!-- Expanded Content View -->
                <div class="expanded-content hidden">
                    ${summaryHtml}
                    <div class="snippet-container full-snippet" style="margin-bottom: 1rem;">
                        <strong>Matched Text:</strong><br/>
                        ${renderHighlightedText(fullText)}
                    </div>
                    <div class="surrounding-messages">
                        <strong>Context:</strong>
                        ${renderMessages(result.surrounding_messages)}
                    </div>
                </div>
            `;

            // Toggle logic on click
            card.addEventListener('click', () => {
                const isExpanded = card.classList.toggle('expanded');
                const content = card.querySelector('.expanded-content');
                const collapsedSnippet = card.querySelector('.collapsed-snippet');
                
                if (isExpanded) {
                    content.classList.remove('hidden');
                    collapsedSnippet.classList.add('hidden');
                } else {
                    content.classList.add('hidden');
                    collapsedSnippet.classList.remove('hidden');
                }
            });

            resultsContainer.appendChild(card);
        });
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
