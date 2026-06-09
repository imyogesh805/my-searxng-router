document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const searchInput = document.getElementById('searchInput');
    const submitBtn = document.getElementById('submitBtn');
    const aiToggle = document.getElementById('aiToggle');
    const devToggle = document.getElementById('devToggle');
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    const resultsSection = document.getElementById('resultsSection');
    const aiSummaryCard = document.getElementById('aiSummaryCard');
    const aiResponseContent = document.getElementById('aiResponseContent');
    const sourcesList = document.getElementById('sourcesList');

    // Settings Modal Elements
    const settingsBtn = document.getElementById('settingsBtn');
    const settingsModal = document.getElementById('settingsModal');
    const closeSettingsBtn = document.getElementById('closeSettingsBtn');
    const saveSettingsBtn = document.getElementById('saveSettingsBtn');
    const providerUrlInput = document.getElementById('providerUrl');
    const providerKeyInput = document.getElementById('providerKey');
    const providerModelInput = document.getElementById('providerModel');

    // Crawl Viewer Modal Elements
    const crawlModal = document.getElementById('crawlModal');
    const closeCrawlBtn = document.getElementById('closeCrawlBtn');
    const crawlModalTitle = document.getElementById('crawlModalTitle');
    const crawlModalContent = document.getElementById('crawlModalContent');

    // Cache of crawled pages from the last search
    let currentSources = [];

    // Load configurations from LocalStorage
    function loadSettings() {
        providerUrlInput.value = localStorage.getItem('ai_provider_url') || 'https://api.groq.com/openai/v1';
        providerKeyInput.value = localStorage.getItem('ai_provider_key') || '';
        providerModelInput.value = localStorage.getItem('ai_provider_model') || 'llama3-8b-8192';
    }

    // Save configurations to LocalStorage
    function saveSettings() {
        localStorage.setItem('ai_provider_url', providerUrlInput.value.trim());
        localStorage.setItem('ai_provider_key', providerKeyInput.value.trim());
        localStorage.setItem('ai_provider_model', providerModelInput.value.trim());
        hideElement(settingsModal);
    }

    // Helper functions for visibility
    function showElement(el) {
        el.classList.remove('hidden');
    }
    function hideElement(el) {
        el.classList.add('hidden');
    }

    // Auto-growing textarea for search box
    searchInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    // Settings Modal Triggers
    settingsBtn.addEventListener('click', () => {
        loadSettings();
        showElement(settingsModal);
    });
    closeSettingsBtn.addEventListener('click', () => hideElement(settingsModal));
    saveSettingsBtn.addEventListener('click', saveSettings);

    // Close Modals when clicking outside content area
    window.addEventListener('click', (e) => {
        if (e.target === settingsModal) hideElement(settingsModal);
        if (e.target === crawlModal) hideElement(crawlModal);
    });

    // Close Crawl Modal
    closeCrawlBtn.addEventListener('click', () => hideElement(crawlModal));

    // Handle submit search action
    async function handleSearch() {
        const queryText = searchInput.value.trim();
        if (!queryText) return;

        // Reset UI
        hideElement(resultsSection);
        showElement(statusIndicator);
        statusText.textContent = "Executing search query on SearXNG...";
        submitBtn.disabled = true;

        // Gather Provider configuration
        const providerUrl = localStorage.getItem('ai_provider_url') || providerUrlInput.value.trim();
        const providerKey = localStorage.getItem('ai_provider_key') || providerKeyInput.value.trim();
        const providerModel = localStorage.getItem('ai_provider_model') || providerModelInput.value.trim();

        const useAi = aiToggle.checked;
        const devFocus = devToggle.checked;

        // Build Payload
        const payload = {
            query: queryText,
            use_ai: useAi,
            dev_focus: devFocus
        };

        // Attach provider settings if available
        if (providerUrl || providerKey || providerModel) {
            payload.provider = {
                base_url: providerUrl || undefined,
                api_key: providerKey || undefined,
                model: providerModel || undefined
            };
        }

        try {
            // Update progress message
            if (useAi) {
                statusText.textContent = "Crawling targets & synthesizing AI summary...";
            } else {
                statusText.textContent = "Searching web targets and extracting page layouts...";
            }

            const response = await fetch('/api/research', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Query execution failed.");
            }

            const data = await response.json();
            displayResults(data, useAi);

        } catch (err) {
            alert(`Error: ${err.message}`);
            hideElement(statusIndicator);
        } finally {
            submitBtn.disabled = false;
        }
    }

    // Trigger Search on Button Click
    submitBtn.addEventListener('click', handleSearch);

    // Trigger Search on Enter (Shift+Enter to newline)
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSearch();
        }
    });

    // Display Results in split-screen format
    function displayResults(data, useAi) {
        hideElement(statusIndicator);
        showElement(resultsSection);

        // Display AI summary panel
        if (useAi) {
            showElement(aiSummaryCard);
            aiResponseContent.textContent = data.research_summary || "No research summary was returned.";
        } else {
            // Hide AI Summary Card if AI is disabled
            hideElement(aiSummaryCard);
        }

        // Render crawled sources
        sourcesList.innerHTML = '';
        currentSources = data.crawled_pages || [];

        if (currentSources.length === 0) {
            sourcesList.innerHTML = '<p class="modal-desc">No web pages were successfully crawled for this query.</p>';
            return;
        }

        currentSources.forEach((source, index) => {
            const item = document.createElement('div');
            item.className = 'source-item';
            
            const titleText = source.title || `Source #${index + 1}`;
            const displayTitle = titleText.length > 55 ? titleText.substring(0, 52) + '...' : titleText;

            item.innerHTML = `
                <div class="source-title">${displayTitle}</div>
                <a href="${source.url}" target="_blank" class="source-link">${source.url}</a>
                <div class="source-actions">
                    <button class="action-btn view-crawl-btn" data-index="${index}">
                        <i class="fa-solid fa-code"></i> View Crawl Markdown
                    </button>
                </div>
            `;
            sourcesList.appendChild(item);
        });

        // Add click event listeners to "View Crawl Markdown" buttons
        document.querySelectorAll('.view-crawl-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const idx = parseInt(this.getAttribute('data-index'));
                openCrawlViewer(idx);
            });
        });
    }

    // Open Raw Crawl Viewer Modal
    function openCrawlViewer(index) {
        const sourceDoc = currentSources[index];
        if (!sourceDoc) return;

        crawlModalTitle.textContent = sourceDoc.title || "Raw Crawled Content";
        crawlModalContent.textContent = sourceDoc.markdown || "No content extracted from this page.";
        showElement(crawlModal);
    }

    // Initialize inputs on page load
    loadSettings();
});
