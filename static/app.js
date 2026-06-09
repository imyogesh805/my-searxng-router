document.addEventListener('DOMContentLoaded', () => {
    // DOM
    const searchInput      = document.getElementById('searchInput');
    const submitBtn        = document.getElementById('submitBtn');
    const aiToggle         = document.getElementById('aiToggle');
    const devToggle        = document.getElementById('devToggle');
    const pipelineSteps    = document.getElementById('pipelineSteps');
    const resultsSection   = document.getElementById('resultsSection');
    const aiSummaryCard    = document.getElementById('aiSummaryCard');
    const aiResponseContent= document.getElementById('aiResponseContent');
    const streamingDot     = document.getElementById('streamingDot');
    const sourcesCard      = document.getElementById('sourcesCard');
    const sourcesList      = document.getElementById('sourcesList');
    const sourcesHeader    = document.getElementById('sourcesHeader');

    // Settings
    const settingsBtn      = document.getElementById('settingsBtn');
    const settingsModal    = document.getElementById('settingsModal');
    const closeSettingsBtn = document.getElementById('closeSettingsBtn');
    const saveSettingsBtn  = document.getElementById('saveSettingsBtn');
    const providerUrlInput = document.getElementById('providerUrl');
    const providerKeyInput = document.getElementById('providerKey');
    const providerModelInput = document.getElementById('providerModel');

    // Crawl modal
    const crawlModal       = document.getElementById('crawlModal');
    const closeCrawlBtn    = document.getElementById('closeCrawlBtn');
    const crawlModalTitle  = document.getElementById('crawlModalTitle');
    const crawlModalContent= document.getElementById('crawlModalContent');

    let currentCrawledPages = [];
    let activeReader = null;

    // ── Settings ──────────────────────────────────────────────────────────────
    function loadSettings() {
        providerUrlInput.value   = localStorage.getItem('ai_provider_url')   || 'https://api.groq.com/openai/v1';
        providerKeyInput.value   = localStorage.getItem('ai_provider_key')   || '';
        providerModelInput.value = localStorage.getItem('ai_provider_model') || 'llama3-8b-8192';
    }

    function saveSettings() {
        localStorage.setItem('ai_provider_url',   providerUrlInput.value.trim());
        localStorage.setItem('ai_provider_key',   providerKeyInput.value.trim());
        localStorage.setItem('ai_provider_model', providerModelInput.value.trim());
        hide(settingsModal);
    }

    const testProviderBtn = document.getElementById('testProviderBtn');
    const pingResult      = document.getElementById('pingResult');

    settingsBtn.addEventListener('click', () => { loadSettings(); show(settingsModal); });
    closeSettingsBtn.addEventListener('click', () => hide(settingsModal));
    saveSettingsBtn.addEventListener('click', saveSettings);

    testProviderBtn.addEventListener('click', async () => {
        const base_url = providerUrlInput.value.trim()   || 'https://api.groq.com/openai/v1';
        const api_key  = providerKeyInput.value.trim();
        const model    = providerModelInput.value.trim() || 'llama3-8b-8192';

        if (!api_key) {
            pingResult.className = 'ping-result ping-error';
            pingResult.textContent = '⚠️ Enter an API key first.';
            show(pingResult);
            return;
        }

        testProviderBtn.disabled = true;
        testProviderBtn.innerHTML = '<span class="step-spinner"></span> Testing...';
        pingResult.className = 'ping-result';
        pingResult.textContent = '';
        hide(pingResult);

        try {
            const res = await fetch('/api/ping', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ base_url, api_key, model })
            });
            const data = await res.json();

            if (data.ok) {
                const speed = data.ms < 800 ? '🟢 Fast' : data.ms < 2000 ? '🟡 Medium' : '🔴 Slow';
                pingResult.className = 'ping-result ping-success';
                pingResult.textContent = `${speed} — ${data.ms}ms — Model: ${data.model} — Reply: "${data.reply}"`;
            } else {
                pingResult.className = 'ping-result ping-error';
                pingResult.textContent = `❌ Failed: ${data.error}`;
            }
            show(pingResult);
        } catch (e) {
            pingResult.className = 'ping-result ping-error';
            pingResult.textContent = `❌ Network error: ${e.message}`;
            show(pingResult);
        } finally {
            testProviderBtn.disabled = false;
            testProviderBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Test Connection';
        }
    });
    window.addEventListener('click', e => {
        if (e.target === settingsModal) hide(settingsModal);
        if (e.target === crawlModal)    hide(crawlModal);
    });
    closeCrawlBtn.addEventListener('click', () => hide(crawlModal));

    // ── Helpers ───────────────────────────────────────────────────────────────
    function show(el) { el.classList.remove('hidden'); }
    function hide(el) { el.classList.add('hidden'); }

    searchInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = this.scrollHeight + 'px';
    });

    // ── Pipeline step indicator ───────────────────────────────────────────────
    function addStep(text, phase) {
        show(pipelineSteps);
        const existing = pipelineSteps.querySelector('.step-active');
        if (existing) {
            existing.classList.remove('step-active');
            existing.classList.add('step-done');
            const icon = existing.querySelector('.step-icon');
            if (icon) icon.className = 'step-icon fa-solid fa-check';
        }
        if (phase === 'error') {
            const el = document.createElement('div');
            el.className = 'pipeline-step step-error';
            el.innerHTML = `<i class="step-icon fa-solid fa-triangle-exclamation"></i><span>${text}</span>`;
            pipelineSteps.appendChild(el);
            return;
        }
        if (phase === 'search_done' || phase === 'done') return;

        const el = document.createElement('div');
        el.className = 'pipeline-step step-active';
        el.innerHTML = `<span class="step-spinner"></span><span>${text}</span>`;
        pipelineSteps.appendChild(el);
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function finishSteps() {
        pipelineSteps.querySelectorAll('.step-active').forEach(el => {
            el.classList.remove('step-active');
            el.classList.add('step-done');
            const icon = el.querySelector('.step-spinner');
            if (icon) {
                icon.outerHTML = '<i class="step-icon fa-solid fa-check"></i>';
            }
        });
    }

    // ── Render sources ────────────────────────────────────────────────────────
    function renderSources(results) {
        show(sourcesCard);
        show(resultsSection);
        sourcesList.innerHTML = '';
        currentCrawledPages = [];

        results.forEach(result => {
            const item = document.createElement('div');
            item.className = 'source-item';
            item.dataset.url = result.url;
            item.innerHTML = `
                <div class="source-title">
                    <a href="${result.url}" target="_blank" rel="noopener">${result.title}</a>
                </div>
                <div class="source-url-text">${result.url}</div>
                <div class="source-snippet">${result.content || 'No snippet available.'}</div>
            `;
            sourcesList.appendChild(item);
        });
    }

    // ── Add crawled badge to source item ──────────────────────────────────────
    function markSourceCrawled(page) {
        currentCrawledPages.push(page);
        const idx = currentCrawledPages.length - 1;
        const item = sourcesList.querySelector(`[data-url="${page.url}"]`);
        if (item && !item.querySelector('.view-crawl-btn')) {
            const actions = document.createElement('div');
            actions.className = 'source-actions';
            actions.style.marginTop = '0.75rem';
            actions.innerHTML = `
                <button class="action-btn view-crawl-btn" data-index="${idx}">
                    <i class="fa-solid fa-code"></i> View Crawled Content
                </button>
            `;
            item.appendChild(actions);
            actions.querySelector('.view-crawl-btn').addEventListener('click', function () {
                openCrawlViewer(parseInt(this.dataset.index));
            });
            // Highlight the crawled source card
            item.classList.add('source-crawled');
        }
    }

    function openCrawlViewer(index) {
        const page = currentCrawledPages[index];
        if (!page) return;
        crawlModalTitle.textContent = page.title || 'Raw Crawled Content';
        crawlModalContent.textContent = page.markdown || 'No content extracted.';
        show(crawlModal);
    }

    // ── Main search handler ───────────────────────────────────────────────────
    async function handleSearch() {
        const queryText = searchInput.value.trim();
        if (!queryText) return;

        // Cancel any previous stream
        if (activeReader) {
            try { activeReader.cancel(); } catch (_) {}
            activeReader = null;
        }

        // Reset UI
        hide(resultsSection);
        hide(aiSummaryCard);
        hide(sourcesCard);
        pipelineSteps.innerHTML = '';
        hide(pipelineSteps);
        aiResponseContent.textContent = '';
        sourcesList.innerHTML = '';
        currentCrawledPages = [];
        streamingDot.classList.remove('hidden');
        submitBtn.disabled = true;

        const useAi    = aiToggle.checked;
        const devFocus = devToggle.checked;

        const providerUrl   = localStorage.getItem('ai_provider_url')   || '';
        const providerKey   = localStorage.getItem('ai_provider_key')   || '';
        const providerModel = localStorage.getItem('ai_provider_model') || 'llama3-8b-8192';

        const payload = {
            query: queryText,
            use_ai: useAi,
            dev_focus: devFocus,
            provider: {
                base_url: providerUrl   || undefined,
                api_key:  providerKey   || undefined,
                model:    providerModel || undefined
            }
        };

        try {
            const response = await fetch('/api/research/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const err = await response.json();
                addStep(`Error: ${err.detail || 'Request failed'}`, 'error');
                submitBtn.disabled = false;
                return;
            }

            const reader = response.body.getReader();
            activeReader = reader;
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split('\n\n');
                buffer = parts.pop(); // keep incomplete chunk

                for (const part of parts) {
                    if (!part.trim()) continue;

                    let eventType = 'message';
                    let dataStr   = '';

                    for (const line of part.split('\n')) {
                        if (line.startsWith('event: ')) eventType = line.slice(7).trim();
                        if (line.startsWith('data: '))  dataStr   = line.slice(6).trim();
                    }

                    let data;
                    try { data = JSON.parse(dataStr); } catch (_) { continue; }

                    switch (eventType) {

                        case 'step':
                            addStep(data.text, data.phase);
                            break;

                        case 'sources':
                            sourcesHeader.textContent = useAi ? 'Sources' : 'Search Results';
                            renderSources(data.results || []);
                            if (useAi) {
                                show(aiSummaryCard);
                                show(resultsSection);
                                resultsSection.style.gridTemplateColumns = '1.6fr 1fr';
                            } else {
                                resultsSection.style.gridTemplateColumns = '1fr';
                            }
                            break;

                        case 'crawled':
                            if (data.page) markSourceCrawled(data.page);
                            break;

                        case 'token':
                            show(aiSummaryCard);
                            show(resultsSection);
                            aiResponseContent.textContent += data.text;
                            aiResponseContent.scrollTop = aiResponseContent.scrollHeight;
                            break;

                        case 'done':
                            finishSteps();
                            streamingDot.classList.add('hidden');
                            submitBtn.disabled = false;
                            activeReader = null;
                            break;
                    }
                }
            }

        } catch (err) {
            addStep(`Connection error: ${err.message}`, 'error');
        } finally {
            submitBtn.disabled = false;
            streamingDot.classList.add('hidden');
            activeReader = null;
        }
    }

    submitBtn.addEventListener('click', handleSearch);
    searchInput.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSearch();
        }
    });

    loadSettings();
});
