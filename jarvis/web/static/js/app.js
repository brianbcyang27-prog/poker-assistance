/**
 * JARVIS — Unified Dashboard Application v6.5.0
 * LEFT nav (workspace-based) | CENTER core | RIGHT conversations + health | BOTTOM input
 */

let currentSessionId = null;
let goldenCore = null;
let commandMap = null;
let knowledgeGraph = null;
let memoryGalaxy = null;
let currentWorkspace = 'core';
let currentChatMode = 'chat';
let _startTime = Date.now();
let _eventCount = 0;

/* ---- Golden Neural Core lifecycle ---- */

let chatBg = null;

function ensureGoldenCore() {
    if (goldenCore) return goldenCore;

    const container = document.getElementById('golden-core-container');
    if (!container || !window.Graph3D) return null;

    try {
        goldenCore = new Graph3D(container);
        goldenCore.init();
        goldenCore.loadData();
        goldenCore.start();
        return goldenCore;
    } catch (e) {
        console.warn('GoldenCore:', e);
        goldenCore = null;
        return null;
    }
}

/* ---- Settings overlay ---- */

function toggleSettings() {
    document.getElementById('settings-overlay').classList.toggle('hidden');
    // Load voice clone status and providers when settings are opened
    if (!document.getElementById('settings-overlay').classList.contains('hidden')) {
        loadVoiceCloneStatus();
        loadProviders();
    }
}

async function loadSettings() {
    try {
        const res = await fetch('/api/settings');
        const settings = await res.json();
        const form = document.getElementById('settings-form');
        for (const [key, value] of Object.entries(settings)) {
            const el = form.elements[key];
            if (!el) continue;
            if (el.type === 'checkbox') el.checked = !!value;
            else el.value = value;
        }
        await loadVoiceModels();
        await loadPermissions();
    } catch (_) {}
}

async function loadVoiceModels() {
    try {
        const res = await fetch('/api/voice/models');
        const data = await res.json();
        const prov = document.getElementById('tts-provider');
        const voice = document.getElementById('tts-voice');
        if (!prov || !voice) return;
        prov.innerHTML = '';
        for (const p of data.providers) {
            const o = document.createElement('option');
            o.value = p;
            o.textContent = p.charAt(0).toUpperCase() + p.slice(1);
            prov.appendChild(o);
        }
        if (window._voiceProviderHandler) prov.removeEventListener('change', window._voiceProviderHandler);
        window._voiceProviderHandler = () => updateVoiceList(data.voices, prov.value);
        prov.addEventListener('change', window._voiceProviderHandler);
        const cur = document.querySelector('[name="tts_provider"]')?.value || 'macos';
        prov.value = cur;
        updateVoiceList(data.voices, cur);
    } catch (_) {}
}

/* ---- Provider Management ---- */

async function loadProviders() {
    const container = document.getElementById('providers-list');
    if (!container) return;
    
    try {
        const res = await fetch('/api/voice/providers');
        const data = await res.json();
        
        container.innerHTML = data.providers.map(p => `
            <div class="provider-card ${p.enabled ? 'provider-active' : ''}" data-provider="${p.id}">
                <div class="provider-header">
                    <div class="provider-info">
                        <span class="provider-name">${p.name}</span>
                        <span class="provider-category">${p.category}</span>
                    </div>
                    <div class="provider-status">
                        ${p.enabled ? '<span class="status-badge active">Active</span>' : ''}
                        ${p.installed ? '<span class="status-badge installed">Installed</span>' : '<span class="status-badge not-installed">Not Installed</span>'}
                    </div>
                </div>
                <div class="provider-desc">${p.description}</div>
                ${p.requirements ? `<div class="provider-reqs">Requires: ${p.requirements}</div>` : ''}
                ${p.requires_api_key ? `<div class="provider-api-key">${p.has_api_key ? 'API key configured' : 'API key required'}</div>` : ''}
                <div class="provider-actions">
                    ${!p.installed ? `
                        <button class="btn-action btn-sm" onclick="installProvider('${p.id}')">
                            Install
                        </button>
                    ` : `
                        ${!p.enabled ? `
                            <button class="btn-action btn-sm" onclick="enableProvider('${p.id}')">
                                Enable
                            </button>
                            <button class="btn-action btn-sm btn-danger" onclick="uninstallProvider('${p.id}')">
                                Uninstall
                            </button>
                        ` : `
                            <span class="provider-active-label">Currently Active</span>
                        `}
                    `}
                </div>
            </div>
        `).join('');
    } catch (_) {
        container.innerHTML = '<p class="empty-state">Failed to load providers</p>';
    }
}

async function installProvider(providerId) {
    const card = document.querySelector(`[data-provider="${providerId}"]`);
    if (card) {
        const btn = card.querySelector('.btn-action');
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Installing...';
        }
    }
    
    try {
        const res = await fetch(`/api/voice/providers/${providerId}/install`, { method: 'POST' });
        const data = await res.json();
        
        if (res.ok) {
            await loadProviders();
            await loadVoiceModels();
        } else {
            alert(data.detail || 'Installation failed');
            if (card) {
                const btn = card.querySelector('.btn-action');
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = 'Install';
                }
            }
        }
    } catch (_) {
        alert('Installation failed');
        if (card) {
            const btn = card.querySelector('.btn-action');
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Install';
            }
        }
    }
}

async function uninstallProvider(providerId) {
    if (!confirm(`Are you sure you want to uninstall ${providerId}?`)) return;
    
    try {
        const res = await fetch(`/api/voice/providers/${providerId}/uninstall`, { method: 'POST' });
        const data = await res.json();
        
        if (res.ok) {
            await loadProviders();
            await loadVoiceModels();
        } else {
            alert(data.detail || 'Uninstall failed');
        }
    } catch (_) {
        alert('Uninstall failed');
    }
}

async function enableProvider(providerId) {
    try {
        const res = await fetch(`/api/voice/providers/${providerId}/enable`, { method: 'POST' });
        const data = await res.json();
        
        if (res.ok) {
            // Update the TTS provider select
            const provSelect = document.getElementById('tts-provider');
            if (provSelect) provSelect.value = providerId;
            
            await loadProviders();
            await loadVoiceModels();
        } else {
            alert(data.detail || 'Failed to enable provider');
        }
    } catch (_) {
        alert('Failed to enable provider');
    }
}

async function disableProvider(providerId) {
    try {
        const res = await fetch(`/api/voice/providers/${providerId}/disable`, { method: 'POST' });
        const data = await res.json();
        
        if (res.ok) {
            await loadProviders();
        } else {
            alert(data.detail || 'Failed to disable provider');
        }
    } catch (_) {
        alert('Failed to disable provider');
    }
}

async function loadPermissions() {
    const container = document.getElementById('permissions-list');
    if (!container) return;
    
    try {
        const res = await fetch('/api/system/permissions');
        const data = await res.json();
        const permissions = data.permissions || [];
        
        container.innerHTML = permissions.map(p => `
            <div class="permission-row">
                <div class="permission-info">
                    <div class="permission-name">${p.name}</div>
                    <div class="permission-desc">${p.description}</div>
                    <div class="permission-reason">${p.reason}</div>
                </div>
                <label class="permission-toggle">
                    <input type="checkbox" ${p.enabled ? 'checked' : ''} 
                           onchange="togglePermission('${p.name}', this.checked)">
                    <span class="toggle-slider"></span>
                </label>
            </div>
        `).join('');
    } catch (_) {
        container.innerHTML = '<p class="empty-state">Failed to load permissions</p>';
    }
}

async function togglePermission(name, enabled) {
    try {
        await fetch('/api/system/permissions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ permission: name, enabled })
        });
    } catch (_) {}
}

function updateVoiceList(voices, provider) {
    const sel = document.getElementById('tts-voice');
    if (!sel) return;
    const cur = document.querySelector('[name="tts_voice"]')?.value || '';
    sel.innerHTML = '<option value="">Default</option>';
    for (const v of (voices[provider] || [])) {
        const o = document.createElement('option');
        o.value = v.id;
        o.textContent = `${v.name} (${v.language})`;
        sel.appendChild(o);
    }
    if (cur) sel.value = cur;
}

async function saveSettings() {
    const form = document.getElementById('settings-form');
    const data = {};
    for (const el of form.elements) {
        if (!el.name) continue;
        if (el.type === 'checkbox') data[el.name] = el.checked;
        else if (el.type === 'number') data[el.name] = parseFloat(el.value);
        else data[el.name] = el.value;
    }
    try {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        showToast(res.ok ? 'Settings saved' : 'Error saving');
    } catch (e) { showToast('Error: ' + e.message); }
}

function resetSettings() {
    if (!confirm('Reset all settings to defaults?')) return;
    const defaults = {
        nvidia_model: 'meta/llama-3.1-8b-instruct',
        default_llm_temperature: 0.7,
        max_tokens: 4096,
        confidence_threshold: 0.9,
        require_confirmation: true,
        tts_enabled: true,
        stt_enabled: true,
        host: '127.0.0.1',
        port: 8000,
    };
    const form = document.getElementById('settings-form');
    for (const [k, v] of Object.entries(defaults)) {
        const el = form.elements[k];
        if (!el) continue;
        if (el.type === 'checkbox') el.checked = v;
        else el.value = v;
    }
    const apiKey = form.elements['nvidia_api_key'];
    if (apiKey) apiKey.value = '';
}

function showToast(msg) {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2500);
}

/* ---- Chat ---- */

function sendMessage() {
    sendMessageStreaming();
}

/* ---- Streaming Chat ---- */

function sendMessageStreaming() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    if (!message) return;
    input.value = '';

    addChatMessage('user', message);
    _addTerminalLine(`> ${message}`, 'info');

    if (window.jarvisState) window.jarvisState.startThinking();
    if (window.livingUI) window.livingUI.setState('thinking');
    if (goldenCore) goldenCore.setState('thinking');

    const params = new URLSearchParams({ message });
    if (currentSessionId) params.set('session_id', currentSessionId);

    let bubble = addChatMessage('assistant', '');
    let fullText = '';
    let firstToken = true;

    // Add timeout to prevent loading forever
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    
    fetch(`/api/chat/stream?${params}`, { signal: controller.signal })
        .then(response => {
            clearTimeout(timeout);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            function processBuffer() {
                const frames = buffer.split('\n\n');
                buffer = frames.pop();
                for (const frame of frames) {
                    const trimmed = frame.trim();
                    if (!trimmed) continue;
                    for (const rawLine of trimmed.split('\n')) {
                        const line = rawLine.trim();
                        if (!line.startsWith('data: ')) continue;
                        try {
                            const evt = JSON.parse(line.slice(6));
                            if (evt.type === 'token') {
                                if (firstToken) {
                                    firstToken = false;
                                    if (window.jarvisState) window.jarvisState.startSpeaking();
                                    if (window.livingUI) window.livingUI.setState('speaking');
                                    if (goldenCore) goldenCore.setState('speaking');
                                }
                                fullText += evt.content;
                                if (bubble) {
                                    bubble.innerHTML = _md(fullText);
                                    bubble.parentElement.scrollTop = bubble.parentElement.scrollHeight;
                                }
                            } else if (evt.type === 'done') {
                                currentSessionId = evt.session_id || currentSessionId;
                                setErrorState(false);
                                if (bubble && fullText) {
                                    bubble.innerHTML = _md(fullText);
                                }
                                if (window.jarvisState) window.jarvisState.set('idle');
                                if (window.livingUI) window.livingUI.setState('idle');
                                if (goldenCore) goldenCore.setState('idle');
                            }
                        } catch (_) {}
                    }
                }
            }

            function read() {
                reader.read().then(({ done, value }) => {
                    if (done) {
                        processBuffer();
                        return;
                    }
                    buffer += decoder.decode(value, { stream: true });
                    processBuffer();
                    read();
                });
            }
            read();
        })
        .catch(err => {
            clearTimeout(timeout);
            setErrorState(true);
            const errorMsg = err.name === 'AbortError' 
                ? 'Request timed out. Please try again.'
                : 'Error: ' + err.message;
            _addTerminalLine(`ERROR: ${errorMsg}`, 'error');
            if (bubble) {
                bubble.innerHTML = _md(errorMsg);
            } else {
                addChatMessage('assistant', errorMsg);
            }
            if (window.jarvisState) window.jarvisState.set('idle');
            if (window.livingUI) window.livingUI.setState('idle');
            if (goldenCore) goldenCore.setState('idle');
        });
}

function addChatMessage(role, text) {
    const container = document.getElementById('chat-messages');
    if (!container) return null;
    const msg = document.createElement('div');
    msg.className = `chat-msg ${role}`;
    msg.innerHTML = role === 'assistant' ? _md(text) : _escHtml(text);
    container.appendChild(msg);
    container.parentElement.scrollTop = container.parentElement.scrollHeight;
    return msg;
}

function _md(text) {
    const clean = text.replace(/<[^>]*>/g, '');
    return clean
        .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
}

function _escHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

/* ---- Error State ---- */

let _errorState = false;

function setErrorState(isError) {
    _errorState = isError;
    document.body.classList.toggle('system-error', isError);
}

/* ---- Knowledge Graph ---- */

let graphViz = null;

async function toggleGraph() {
    if (!graphViz) {
        graphViz = new KnowledgeGraphViz();
        await graphViz.init();
    }
    await graphViz.toggle();
}

/* ---- Workspace Switching ---- */

async function switchWorkspace(workspace) {
    currentWorkspace = workspace;

    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.workspace === workspace);
    });

    const coreCanvas = document.getElementById('golden-core-container');
    const graphContainer = document.getElementById('graph-container');
    const chatContainer = document.getElementById('chat-container');
    const projectsContainer = document.getElementById('projects-container');
    const computerContainer = document.getElementById('computer-container');
    const metricsContainer = document.getElementById('metrics-container');
    const logsContainer = document.getElementById('logs-container');
    const voiceContainer = document.getElementById('voice-container');
    const responseDisplay = document.getElementById('response-display');
    const terminalLog = document.getElementById('terminal-log');

    // Hide all workspace-specific panels
    if (graphContainer) graphContainer.style.display = 'none';
    if (projectsContainer) projectsContainer.style.display = 'none';
    if (computerContainer) computerContainer.style.display = 'none';
    if (metricsContainer) metricsContainer.style.display = 'none';
    if (logsContainer) logsContainer.style.display = 'none';
    if (voiceContainer) voiceContainer.style.display = 'none';
    if (terminalLog) terminalLog.classList.remove('visible');

    switch (workspace) {
        case 'core':
            if (coreCanvas) coreCanvas.style.display = 'block';
            if (chatContainer) chatContainer.style.display = 'none';
            if (responseDisplay) responseDisplay.style.display = 'none';
            if (chatBg) { chatBg.stop(); chatBg = null; }
            ensureGoldenCore()?.start();
            break;

        case 'chat':
            if (coreCanvas) coreCanvas.style.display = 'none';
            if (chatContainer) chatContainer.style.display = 'flex';
            if (responseDisplay) responseDisplay.style.display = 'none';
            currentChatMode = 'chat';
            if (!chatBg && window.ChatBackground) {
                chatBg = new ChatBackground(document.getElementById('chat-core-bg'));
                chatBg.start();
            }
            await loadChatHistory();
            break;

        case 'engineering':
            if (coreCanvas) coreCanvas.style.display = 'none';
            if (chatContainer) chatContainer.style.display = 'none';
            if (responseDisplay) responseDisplay.style.display = 'none';
            if (graphContainer) {
                graphContainer.style.display = 'block';
                if (!commandMap) {
                    try { commandMap = new CommandMap(); } catch (e) { console.warn('CommandMap:', e); }
                }
            }
            break;

        case 'research':
            if (coreCanvas) coreCanvas.style.display = 'none';
            if (chatContainer) chatContainer.style.display = 'none';
            if (responseDisplay) responseDisplay.style.display = 'none';
            await showKnowledgeGraph();
            break;

        case 'memory':
            if (coreCanvas) coreCanvas.style.display = 'none';
            if (chatContainer) chatContainer.style.display = 'none';
            if (responseDisplay) responseDisplay.style.display = 'none';
            await showMemoryGalaxy();
            break;

        case 'voice':
            if (coreCanvas) coreCanvas.style.display = 'none';
            if (chatContainer) chatContainer.style.display = 'none';
            if (responseDisplay) responseDisplay.style.display = 'none';
            const voiceContainer = document.getElementById('voice-container');
            if (voiceContainer) {
                voiceContainer.style.display = 'flex';
                initVoiceWorkspace();
            }
            break;

        case 'projects':
            if (coreCanvas) coreCanvas.style.display = 'none';
            if (chatContainer) chatContainer.style.display = 'none';
            if (responseDisplay) responseDisplay.style.display = 'none';
            if (projectsContainer) {
                projectsContainer.style.display = 'flex';
                await loadProjects();
            }
            break;

        case 'computer':
            if (coreCanvas) coreCanvas.style.display = 'none';
            if (chatContainer) chatContainer.style.display = 'none';
            if (responseDisplay) responseDisplay.style.display = 'none';
            if (computerContainer) computerContainer.style.display = 'flex';
            break;

        case 'metrics':
            if (coreCanvas) coreCanvas.style.display = 'none';
            if (chatContainer) chatContainer.style.display = 'none';
            if (responseDisplay) responseDisplay.style.display = 'none';
            if (metricsContainer) {
                metricsContainer.style.display = 'flex';
                await loadMetrics();
            }
            break;

        case 'logs':
            if (coreCanvas) coreCanvas.style.display = 'none';
            if (chatContainer) chatContainer.style.display = 'none';
            if (responseDisplay) responseDisplay.style.display = 'none';
            if (logsContainer) {
                logsContainer.style.display = 'flex';
                await loadLogs();
            }
            break;

        case 'settings':
            toggleSettings();
            break;
    }

    // The renderer is expensive on laptops and should not keep animating behind
    // another workspace. The core resumes without losing its visual state.
    if (workspace !== 'core' && goldenCore) goldenCore.stop();
}

/* ---- Chat History ---- */

async function loadChatHistory() {
    if (!currentSessionId) {
        try {
            const res = await fetch('/api/chat/sessions?limit=1');
            const data = await res.json();
            if (data.sessions && data.sessions.length > 0) {
                currentSessionId = data.sessions[0].session_id;
            }
        } catch (_) {}
    }

    if (!currentSessionId) return;

    try {
        const res = await fetch(`/api/chat/history/${currentSessionId}`);
        const messages = await res.json();
        const container = document.getElementById('chat-messages');
        if (!container) return;
        container.innerHTML = '';
        for (const msg of messages) {
            addChatMessage(msg.role, msg.content);
        }
    } catch (_) {}
}

/* ---- Knowledge Graph Workspace ---- */

async function showKnowledgeGraph() {
    const container = document.getElementById('research-container');
    if (!container) return;
    container.style.display = 'block';
    container.innerHTML = '';

    if (!knowledgeGraph) {
        try {
            knowledgeGraph = new KnowledgeGraphViz();
            knowledgeGraph.container = container;
            await knowledgeGraph.init();
        } catch (e) { console.warn('KnowledgeGraph:', e); }
    }
}

/* ---- Memory Galaxy Workspace ---- */

async function showMemoryGalaxy() {
    const container = document.getElementById('memory-container');
    if (!container) return;
    container.style.display = 'block';

    if (!memoryGalaxy) {
        try {
            memoryGalaxy = new MemoryGalaxy(container);
            memoryGalaxy.init();
            memoryGalaxy.start();
            await memoryGalaxy.loadMemories();
        } catch (e) { console.warn('MemoryGalaxy:', e); }
    }
}

/* ---- Terminal Log ---- */

function _addTerminalLine(text, type) {
    const entries = document.getElementById('terminal-entries');
    if (!entries) return;

    const line = document.createElement('div');
    line.className = `terminal-line ${type || ''}`;
    const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    line.textContent = `[${time}] ${text}`;
    entries.appendChild(line);

    while (entries.children.length > 50) {
        entries.removeChild(entries.firstChild);
    }

    entries.parentElement.scrollTop = entries.parentElement.scrollHeight;
}

/* ---- Health Panel ---- */

function _refreshHealth() {
    fetch('/api/agents')
        .then(r => r.json())
        .then(data => {
            const kings = data.kings || {};
            let totalWorkers = 0, activeWorkers = 0;
            let totalKings = Object.keys(kings).length;
            for (const king of Object.values(kings)) {
                const workers = king.workers || {};
                totalWorkers += Object.keys(workers).length;
                for (const w of Object.values(workers)) {
                    if (w.state !== 'idle') activeWorkers++;
                }
            }

            const el = document.getElementById('health-agents');
            if (el) el.textContent = `${activeWorkers}/${totalWorkers}`;
            const kel = document.getElementById('health-kings');
            if (kel) kel.textContent = `${totalKings}/4`;
            const eel = document.getElementById('health-events');
            if (eel) eel.textContent = _eventCount;
            const uel = document.getElementById('health-uptime');
            if (uel) uel.textContent = _formatUptime(Date.now() - _startTime);

            const statusEl = document.getElementById('health-status');
            if (statusEl) {
                statusEl.textContent = 'OK';
                statusEl.className = 'right-status health-ok';
            }
        })
        .catch(() => {
            const statusEl = document.getElementById('health-status');
            if (statusEl) {
                statusEl.textContent = 'DOWN';
                statusEl.className = 'right-status';
                statusEl.style.color = '#ff3366';
            }
        });
}

function _formatUptime(ms) {
    const s = Math.floor(ms / 1000);
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    if (m < 60) return `${m}m`;
    const h = Math.floor(m / 60);
    return `${h}h ${m % 60}m`;
}

/* ---- Agent Conversation Stream ---- */

function _addAgentConversation(data) {
    const stream = document.getElementById('agent-conversation-stream');
    if (!stream) return;

    const el = document.createElement('div');
    el.className = 'agent-msg';

    const header = document.createElement('div');
    header.className = 'agent-msg-header';
    const cardSpan = document.createElement('span');
    cardSpan.className = 'agent-card';
    cardSpan.textContent = data.card_id || '?';
    const nameSpan = document.createElement('span');
    nameSpan.className = 'agent-name';
    nameSpan.textContent = data.title || data.sender || '?';
    header.appendChild(cardSpan);
    header.appendChild(nameSpan);
    if (data.receiver) {
        const arrow = document.createTextNode(' → ');
        const recvSpan = document.createElement('span');
        recvSpan.className = 'agent-recv';
        recvSpan.textContent = data.receiver;
        header.appendChild(arrow);
        header.appendChild(recvSpan);
    }

    const body = document.createElement('div');
    body.className = 'agent-msg-body';
    body.textContent = data.content || '';

    el.appendChild(header);
    el.appendChild(body);
    stream.appendChild(el);

    stream.scrollTop = stream.scrollHeight;

    requestAnimationFrame(() => el.classList.add('visible'));

    while (stream.children.length > 30) {
        stream.removeChild(stream.firstChild);
    }
}

/* ---- Session List ---- */

async function loadSessionList() {
    try {
        const res = await fetch('/api/chat/sessions?limit=20');
        const data = await res.json();
        const list = document.getElementById('session-list');
        if (!list || !data.sessions) return;
        list.innerHTML = '';
        for (const session of data.sessions) {
            const item = document.createElement('div');
            item.className = 'session-item';
            item.dataset.sessionId = session.session_id;
            const preview = document.createElement('div');
            preview.className = 'session-preview';
            preview.textContent = session.preview || 'New conversation';
            const meta = document.createElement('div');
            meta.className = 'session-meta';
            meta.textContent = `${session.message_count} messages`;
            item.appendChild(preview);
            item.appendChild(meta);
            item.addEventListener('click', () => {
                currentSessionId = session.session_id;
                loadChatHistory();
                document.querySelectorAll('.session-item').forEach(s => s.classList.remove('active'));
                item.classList.add('active');
            });
            list.appendChild(item);
        }
    } catch (_) {}
}

/* ---- Init ---- */

document.addEventListener('DOMContentLoaded', async () => {
    // Initialize state machine
    try {
        window.jarvisState = new JarvisState();
    } catch (e) { console.warn('JarvisState:', e); }

    // Initialize audio analyzer
    try {
        window.audioAnalyzer = new AudioAnalyzer();
    } catch (e) { console.warn('AudioAnalyzer:', e); }

    // Initialize living interface (WebSocket events)
    try {
        window.livingUI = new LivingInterface();
    } catch (e) { console.warn('LivingInterface:', e); }

    // Initialize department identity badges
    try {
        window.deptIdentity = new DepartmentIdentity();
        window.deptIdentity.renderAll();
    } catch (e) { console.warn('DepartmentIdentity:', e); }

    // Initialize explainability overlay
    try {
        window.explainability = new ExplainabilityOverlay();
    } catch (e) { console.warn('ExplainabilityOverlay:', e); }

    // Initialize mission DAG
    try {
        window.missionDAG = new MissionDAG(document.getElementById('mission-dag-container'));
        window.missionDAG.init();
    } catch (e) { console.warn('MissionDAG:', e); }

    // Wire up state changes to all visual systems
    if (window.jarvisState) {
        window.jarvisState.onStateChange(state => {
            if (goldenCore) goldenCore.setState(state);
            if (window.livingUI) window.livingUI.setState(state);
        });
    }

    // Set initial state
    if (window.jarvisState) window.jarvisState.set('idle');
    if (window.livingUI) {
        window.livingUI.setState('idle');
        window.livingUI.startMissionPolling();
        window.livingUI.connectEvents();
    }

    // Wire up workspace navigation
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.dataset.workspace) switchWorkspace(btn.dataset.workspace);
        });
    });

    // Load settings and apply modes
    await loadSettings();
    try {
        const res = await fetch('/api/settings');
        const settings = await res.json();
        if (settings.chat_mode) {
            currentChatMode = settings.chat_mode;
        }
    } catch (_) {}

    // Set default workspace to chat (modern AI assistant mode)
    switchWorkspace('chat');

    // Health polling
    setInterval(_refreshHealth, 10000);
    _refreshHealth();

    // Load session list for chat sidebar
    loadSessionList();

    // Intercept WebSocket messages for right panel
    if (window.livingUI) {
        const orig = window.livingUI._handleWSMessage.bind(window.livingUI);
        window.livingUI._handleWSMessage = function(data) {
            orig(data);
            if (data.type === 'event') {
                _eventCount++;
                const ev = data.data;
                if (ev && ev.event_type) {
                    _addTerminalLine(`${ev.icon || '•'} ${ev.label || ev.event_type}`, '');
                }
            }
            if (data.type === 'agent_conversation') {
                _addAgentConversation(data.data);
            }
            if (data.type === 'status' && data.data) {
                _updateHealthFromStatus(data.data);
            }
        };
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', e => {
        if ((e.ctrlKey || e.metaKey) && e.key === ',') {
            e.preventDefault();
            toggleSettings();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 'g') {
            e.preventDefault();
            toggleGraph();
        }
        if (e.key === 'Escape') {
            const ov = document.getElementById('settings-overlay');
            if (ov && !ov.classList.contains('hidden')) toggleSettings();
            else if (graphViz && graphViz.visible) graphViz.hide();
        }
    });

    // Developer mode toggle
    const devToggle = document.getElementById('dev-mode-toggle');
    if (devToggle) {
        devToggle.addEventListener('click', () => {
            const devItems = document.querySelector('.dev-only');
            const isActive = devToggle.classList.toggle('active');
            if (devItems) devItems.style.display = isActive ? 'flex' : 'none';
        });
    }
});

function _updateHealthFromStatus(status) {
    if (!status || !status.kings) return;
    let totalWorkers = 0, activeWorkers = 0;
    for (const king of Object.values(status.kings)) {
        const workers = king.workers || {};
        totalWorkers += Object.keys(workers).length;
        for (const w of Object.values(workers)) {
            if (w.state !== 'idle') activeWorkers++;
        }
    }
    const el = document.getElementById('health-agents');
    if (el) el.textContent = `${activeWorkers}/${totalWorkers}`;
}

/* ---- Computer Actions ---- */

async function computerAction(action, params = {}) {
    const output = document.getElementById('computer-output');
    if (output) output.textContent = 'Executing...';
    
    try {
        const res = await fetch('/api/computer/action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, params })
        });
        const data = await res.json();
        if (output) output.textContent = JSON.stringify(data, null, 2);
        return data;
    } catch (e) {
        if (output) output.textContent = 'Error: ' + e.message;
        return null;
    }
}

async function executeTerminal() {
    const input = document.getElementById('terminal-command');
    if (!input || !input.value.trim()) return;
    
    const command = input.value.trim();
    input.value = '';
    
    await computerAction('shell_execute', { command });
}

/* ---- Projects ---- */

async function loadProjects() {
    const container = document.getElementById('projects-list');
    if (!container) return;
    
    try {
        const res = await fetch('/api/workspace');
        const data = await res.json();
        const projects = data.workspaces || [];
        
        if (projects.length === 0) {
            container.innerHTML = '<p class="empty-state">No projects found</p>';
            return;
        }
        
        container.innerHTML = projects.map(p => `
            <div class="project-card">
                <h3>${p.name || 'Untitled'}</h3>
                <p>${p.description || 'No description'}</p>
                <span class="project-status">${p.status || 'unknown'}</span>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = '<p class="empty-state">Failed to load projects</p>';
    }
}

/* ---- Metrics ---- */

async function loadMetrics() {
    const container = document.getElementById('metrics-content');
    if (!container) return;
    
    try {
        const [healthRes, agentsRes] = await Promise.all([
            fetch('/api/system/health'),
            fetch('/api/agents')
        ]);
        const health = await healthRes.json();
        const agents = await agentsRes.json();
        
        container.innerHTML = `
            <div class="metrics-grid">
                <div class="metric-card">
                    <h4>System Health</h4>
                    <p class="metric-value">${health.status || 'unknown'}</p>
                </div>
                <div class="metric-card">
                    <h4>Agents</h4>
                    <p class="metric-value">${agents.length || 0}</p>
                </div>
                <div class="metric-card">
                    <h4>Uptime</h4>
                    <p class="metric-value">${health.uptime || '0s'}</p>
                </div>
            </div>
        `;
    } catch (e) {
        container.innerHTML = '<p class="empty-state">Failed to load metrics</p>';
    }
}

/* ---- Logs ---- */

async function loadLogs() {
    const container = document.getElementById('logs-content');
    if (!container) return;
    
    try {
        const res = await fetch('/api/system/events?limit=50');
        const data = await res.json();
        const events = data.events || [];
        
        if (events.length === 0) {
            container.innerHTML = '<p class="empty-state">No events recorded</p>';
            return;
        }
        
        container.innerHTML = events.map(e => `
            <div class="log-entry">
                <span class="log-time">${e.timestamp || ''}</span>
                <span class="log-type">${e.event_type || ''}</span>
                <span class="log-message">${e.label || e.message || ''}</span>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = '<p class="empty-state">Failed to load logs</p>';
    }
}

/* ---- Voice Cloning ---- */

async function loadVoiceCloneStatus() {
    const statusEl = document.getElementById('clone-status-text');
    const profilesListEl = document.getElementById('clone-profiles-list');
    
    try {
        const res = await fetch('/api/voice/clone/status');
        const data = await res.json();
        
        if (statusEl) {
            if (data.available) {
                statusEl.textContent = `Ready (${data.profiles_count} profiles)`;
                statusEl.style.color = '#4ade80';
            } else {
                statusEl.textContent = data.error || 'Not available';
                statusEl.style.color = '#f87171';
            }
        }
        
        // Load profiles
        const profilesRes = await fetch('/api/voice/clone/profiles');
        const profilesData = await profilesRes.json();
        
        if (profilesListEl && profilesData.profiles) {
            profilesListEl.innerHTML = profilesData.profiles.map(p => `
                <div class="setting-row">
                    <div class="setting-info">
                        <div class="setting-name">${p.name}</div>
                        <div class="setting-desc">ID: ${p.profile_id}</div>
                    </div>
                    <div class="setting-control">
                        <button onclick="testCloneVoice('${p.profile_id}')" class="btn-action btn-small">Test</button>
                        <button onclick="deleteCloneProfile('${p.profile_id}')" class="btn-action btn-small btn-danger">Delete</button>
                    </div>
                </div>
            `).join('');
        }
    } catch (e) {
        if (statusEl) {
            statusEl.textContent = 'Failed to load status';
            statusEl.style.color = '#f87171';
        }
    }
}

async function uploadCloneProfile() {
    const nameInput = document.getElementById('clone-voice-name');
    const fileInput = document.getElementById('clone-voice-file');
    
    if (!nameInput?.value || !fileInput?.files?.length) {
        alert('Please enter a name and select an audio file');
        return;
    }
    
    const formData = new FormData();
    formData.append('name', nameInput.value);
    formData.append('audio', fileInput.files[0]);
    
    try {
        const res = await fetch('/api/voice/clone/profiles', {
            method: 'POST',
            body: formData
        });
        
        const data = await res.json();
        
        if (res.ok) {
            alert(`Voice profile "${data.profile.name}" created!`);
            nameInput.value = '';
            fileInput.value = '';
            loadVoiceCloneStatus();
        } else {
            alert(`Error: ${data.detail || 'Failed to create profile'}`);
        }
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

async function deleteCloneProfile(profileId) {
    if (!confirm('Delete this voice profile?')) return;
    
    try {
        const res = await fetch(`/api/voice/clone/profiles/${profileId}`, {
            method: 'DELETE'
        });
        
        if (res.ok) {
            loadVoiceCloneStatus();
        } else {
            alert('Failed to delete profile');
        }
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

async function testCloneVoice(profileId) {
    const text = prompt('Enter text to speak with this voice:', 'Hello, this is a test of the voice cloning system.');
    if (!text) return;
    
    try {
        const formData = new FormData();
        formData.append('text', text);
        formData.append('profile_id', profileId);
        formData.append('language', 'en');
        
        const res = await fetch('/api/voice/clone/generate', {
            method: 'POST',
            body: formData
        });
        
        if (res.ok) {
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            audio.play();
        } else {
            const data = await res.json();
            alert(`Error: ${data.detail || 'Failed to generate voice'}`);
        }
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

/* ============================================================
   VOICE WORKSPACE
   ============================================================ */

// Voice workspace state
let voiceState = {
    selectedFile: null,
    recordedBlob: null,
    mediaRecorder: null,
    audioChunks: [],
    isRecording: false,
    recordingTimer: null,
    recordingSeconds: 0,
    liveSTT: null,
    isListening: false,
    selectedProfile: null
};

// Initialize voice workspace
function initVoiceWorkspace() {
    // Load voice status
    loadVoiceWorkspaceStatus();
    
    // Load voice profiles
    loadVoiceProfiles();
    
    // Load built-in voices
    loadBuiltinProviders();
    
    // Setup file upload handlers
    setupVoiceFileUpload();
    
    // Setup tab switching
    setupVoiceTabs();
    
    // Setup textarea auto-resize
    const textarea = document.getElementById('voice-test-text');
    if (textarea) {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
    }
}

// Load voice workspace status
async function loadVoiceWorkspaceStatus() {
    const statusEl = document.getElementById('voice-status');
    if (!statusEl) return;
    
    try {
        const res = await fetch('/api/voice/clone/status');
        const data = await res.json();
        
        const dot = statusEl.querySelector('.status-dot');
        const text = statusEl.querySelector('.status-text');
        
        if (data.tts_installed) {
            dot.classList.add('online');
            text.textContent = data.model_loaded 
                ? `Voice cloning ready (${data.profiles_count} profiles)`
                : `TTS installed, model loads on first use (${data.profiles_count} profiles)`;
        } else {
            dot.classList.add('offline');
            text.textContent = data.error || 'Voice cloning not available';
        }
    } catch (e) {
        console.error('Failed to load voice status:', e);
    }
}

// Load voice profiles
async function loadVoiceProfiles() {
    const listEl = document.getElementById('voice-profiles-list');
    const selectEl = document.getElementById('voice-test-profile');
    if (!listEl) return;
    
    try {
        const res = await fetch('/api/voice/clone/profiles');
        const data = await res.json();
        
        if (!data.profiles || data.profiles.length === 0) {
            listEl.innerHTML = '<p class="empty-state">No voice profiles yet. Create one above.</p>';
            return;
        }
        
        // Update profiles list
        listEl.innerHTML = data.profiles.map(p => `
            <div class="voice-profile-card" data-id="${p.profile_id}">
                <div class="profile-info">
                    <span class="profile-name">${p.name}</span>
                    <span class="profile-id">${p.profile_id}</span>
                </div>
                <div class="profile-actions">
                    <button class="btn-action btn-small" onclick="playProfileAudio('${p.profile_id}')">Listen</button>
                    <button class="btn-action btn-small" onclick="selectProfileForTest('${p.profile_id}', '${p.name}')">Use</button>
                    <button class="btn-action btn-small btn-danger" onclick="deleteVoiceProfile('${p.profile_id}')">Delete</button>
                </div>
            </div>
        `).join('');
        
        // Update test profile select
        if (selectEl) {
            selectEl.innerHTML = '<option value="">Select a voice profile...</option>' + 
                data.profiles.map(p => `<option value="${p.profile_id}">${p.name}</option>`).join('');
        }
    } catch (e) {
        console.error('Failed to load profiles:', e);
    }
}

// Setup file upload handlers
function setupVoiceFileUpload() {
    const dropZone = document.getElementById('voice-drop-zone');
    const fileInput = document.getElementById('voice-file-input');
    
    if (!dropZone || !fileInput) return;
    
    // Click to browse
    dropZone.addEventListener('click', () => fileInput.click());
    
    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleVoiceFile(e.target.files[0]);
        }
    });
    
    // Drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleVoiceFile(e.dataTransfer.files[0]);
        }
    });
}

// Handle selected file
function handleVoiceFile(file) {
    voiceState.selectedFile = file;
    voiceState.recordedBlob = null;
    
    const fileInfo = document.getElementById('voice-file-info');
    const createBtn = document.getElementById('voice-create-btn');
    
    if (fileInfo) {
        fileInfo.classList.remove('hidden');
        fileInfo.querySelector('.file-name').textContent = file.name;
    }
    
    if (createBtn) {
        createBtn.disabled = false;
    }
    
    updateCreateButton();
}

// Remove selected file
function removeVoiceFile() {
    voiceState.selectedFile = null;
    
    const fileInfo = document.getElementById('voice-file-info');
    const fileInput = document.getElementById('voice-file-input');
    
    if (fileInfo) fileInfo.classList.add('hidden');
    if (fileInput) fileInput.value = '';
    
    updateCreateButton();
}

// Setup voice tabs
function setupVoiceTabs() {
    const tabs = document.querySelectorAll('.voice-tab');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // Show corresponding mode
            const source = tab.dataset.source;
            document.querySelectorAll('.voice-mode').forEach(mode => mode.classList.remove('active'));
            document.getElementById(`voice-${source}-mode`).classList.add('active');
            
            // Update create button state
            updateCreateButton();
        });
    });
}

// Update create button state
function updateCreateButton() {
    const createBtn = document.getElementById('voice-create-btn');
    const nameInput = document.getElementById('voice-profile-name');
    const activeTab = document.querySelector('.voice-tab.active');
    
    if (!createBtn || !nameInput) return;
    
    const hasName = nameInput.value.trim().length > 0;
    const isUploadMode = activeTab?.dataset.source === 'upload';
    const hasFile = isUploadMode ? voiceState.selectedFile !== null : voiceState.recordedBlob !== null;
    
    createBtn.disabled = !(hasName && hasFile);
}

// Toggle voice recording
async function toggleVoiceRecord() {
    if (voiceState.isRecording) {
        stopRecording();
    } else {
        await startRecording();
    }
}

// Start recording
async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        voiceState.mediaRecorder = new MediaRecorder(stream);
        voiceState.audioChunks = [];
        
        voiceState.mediaRecorder.ondataavailable = (event) => {
            voiceState.audioChunks.push(event.data);
        };
        
        voiceState.mediaRecorder.onstop = () => {
            const blob = new Blob(voiceState.audioChunks, { type: 'audio/wav' });
            voiceState.recordedBlob = blob;
            voiceState.selectedFile = null;
            
            // Show recorded audio player
            const recordedAudio = document.getElementById('voice-recorded-audio');
            const player = document.getElementById('voice-recorded-player');
            
            if (recordedAudio && player) {
                const url = URL.createObjectURL(blob);
                player.src = url;
                recordedAudio.classList.remove('hidden');
            }
            
            // Stop waveform
            if (voiceState.waveformAnimation) {
                cancelAnimationFrame(voiceState.waveformAnimation);
            }
            
            updateCreateButton();
        };
        
        voiceState.mediaRecorder.start();
        voiceState.isRecording = true;
        
        // Update UI
        const btn = document.getElementById('voice-record-btn');
        btn.classList.add('recording');
        btn.querySelector('.record-text').textContent = 'Stop Recording';
        
        // Show timer
        const timer = document.getElementById('voice-record-timer');
        timer.classList.remove('hidden');
        
        // Start timer
        voiceState.recordingSeconds = 0;
        voiceState.recordingTimer = setInterval(() => {
            voiceState.recordingSeconds++;
            const mins = Math.floor(voiceState.recordingSeconds / 60).toString().padStart(2, '0');
            const secs = (voiceState.recordingSeconds % 60).toString().padStart(2, '0');
            timer.querySelector('.timer-display').textContent = `${mins}:${secs}`;
        }, 1000);
        
        // Show waveform
        const waveformContainer = document.getElementById('voice-waveform');
        waveformContainer.classList.remove('hidden');
        startWaveform(stream);
        
    } catch (e) {
        console.error('Failed to start recording:', e);
        alert('Could not access microphone. Please allow microphone access.');
    }
}

// Stop recording
function stopRecording() {
    if (voiceState.mediaRecorder && voiceState.isRecording) {
        voiceState.mediaRecorder.stop();
        voiceState.isRecording = false;
        
        // Stop all tracks
        voiceState.mediaRecorder.stream.getTracks().forEach(track => track.stop());
        
        // Clear timer
        clearInterval(voiceState.recordingTimer);
        
        // Update UI
        const btn = document.getElementById('voice-record-btn');
        btn.classList.remove('recording');
        btn.querySelector('.record-text').textContent = 'Start Recording';
        
        document.getElementById('voice-record-timer').classList.add('hidden');
        document.getElementById('voice-waveform').classList.add('hidden');
    }
}

// Start waveform visualization
function startWaveform(stream) {
    const canvas = document.getElementById('waveform-canvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    
    analyser.fftSize = 256;
    source.connect(analyser);
    
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    
    function draw() {
        voiceState.waveformAnimation = requestAnimationFrame(draw);
        
        analyser.getByteFrequencyData(dataArray);
        
        ctx.fillStyle = 'rgba(5, 11, 20, 0.3)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        const barWidth = (canvas.width / bufferLength) * 2.5;
        let x = 0;
        
        for (let i = 0; i < bufferLength; i++) {
            const barHeight = (dataArray[i] / 255) * canvas.height;
            
            const gradient = ctx.createLinearGradient(0, canvas.height, 0, canvas.height - barHeight);
            gradient.addColorStop(0, '#fbbf24');
            gradient.addColorStop(1, '#f59e0b');
            
            ctx.fillStyle = gradient;
            ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
            
            x += barWidth + 1;
        }
    }
    
    draw();
}

// Clear recording
function clearRecording() {
    voiceState.recordedBlob = null;
    
    const recordedAudio = document.getElementById('voice-recorded-audio');
    if (recordedAudio) recordedAudio.classList.add('hidden');
    
    updateCreateButton();
}

// Create voice profile
async function createVoiceProfile() {
    const nameInput = document.getElementById('voice-profile-name');
    const createBtn = document.getElementById('voice-create-btn');
    
    if (!nameInput?.value.trim()) {
        alert('Please enter a profile name');
        return;
    }
    
    const name = nameInput.value.trim();
    const isUploadMode = document.querySelector('.voice-tab.active')?.dataset.source === 'upload';
    
    let audioBlob;
    if (isUploadMode && voiceState.selectedFile) {
        audioBlob = voiceState.selectedFile;
    } else if (!isUploadMode && voiceState.recordedBlob) {
        audioBlob = voiceState.recordedBlob;
    } else {
        alert('Please upload or record audio first');
        return;
    }
    
    createBtn.disabled = true;
    createBtn.textContent = 'Creating...';
    
    try {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('audio', audioBlob, isUploadMode ? voiceState.selectedFile.name : 'recording.wav');
        
        const res = await fetch('/api/voice/clone/profiles', {
            method: 'POST',
            body: formData
        });
        
        const data = await res.json();
        
        if (res.ok) {
            // Clear inputs
            nameInput.value = '';
            removeVoiceFile();
            clearRecording();
            
            // Reload profiles
            await loadVoiceProfiles();
            await loadVoiceWorkspaceStatus();
            
            alert(`Voice profile "${name}" created successfully!`);
        } else {
            alert(`Error: ${data.detail || 'Failed to create profile'}`);
        }
    } catch (e) {
        alert(`Error: ${e.message}`);
    } finally {
        createBtn.disabled = false;
        createBtn.textContent = 'Create Profile';
        updateCreateButton();
    }
}

// Delete voice profile
async function deleteVoiceProfile(profileId) {
    if (!confirm('Delete this voice profile?')) return;
    
    try {
        const res = await fetch(`/api/voice/clone/profiles/${profileId}`, {
            method: 'DELETE'
        });
        
        if (res.ok) {
            await loadVoiceProfiles();
            await loadVoiceWorkspaceStatus();
        } else {
            alert('Failed to delete profile');
        }
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

// Play profile audio
function playProfileAudio(profileId) {
    const audio = new Audio(`/api/voice/clone/profiles/${profileId}/audio`);
    audio.play();
}

// Select profile for test
function selectProfileForTest(profileId, profileName) {
    voiceState.selectedProfile = profileId;
    
    const selectEl = document.getElementById('voice-test-profile');
    if (selectEl) {
        selectEl.value = profileId;
    }
    
    // Enable speak button
    const speakBtn = document.getElementById('voice-speak-btn');
    if (speakBtn) speakBtn.disabled = false;
}

// Test voice speak
async function testVoiceSpeak() {
    const profileId = document.getElementById('voice-test-profile')?.value;
    const text = document.getElementById('voice-test-text')?.value;
    const language = document.getElementById('voice-test-language')?.value || 'en';
    const statusEl = document.getElementById('voice-test-status');
    
    if (!profileId) {
        alert('Please select a voice profile');
        return;
    }
    
    if (!text?.trim()) {
        alert('Please enter text to speak');
        return;
    }
    
    // Show status
    statusEl?.classList.remove('hidden');
    statusEl.querySelector('.status-message').textContent = 'Generating speech...';
    statusEl.querySelector('.status-indicator').classList.add('speaking');
    
    try {
        const formData = new FormData();
        formData.append('text', text);
        formData.append('profile_id', profileId);
        formData.append('language', language);
        
        const res = await fetch('/api/voice/clone/generate', {
            method: 'POST',
            body: formData
        });
        
        if (res.ok) {
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            
            statusEl.querySelector('.status-message').textContent = 'Playing...';
            
            audio.onended = () => {
                statusEl.querySelector('.status-message').textContent = 'Done';
                statusEl.querySelector('.status-indicator').classList.remove('speaking');
                setTimeout(() => statusEl?.classList.add('hidden'), 2000);
            };
            
            audio.play();
        } else {
            const data = await res.json();
            statusEl.querySelector('.status-message').textContent = `Error: ${data.detail || 'Generation failed'}`;
            statusEl.querySelector('.status-indicator').classList.remove('speaking');
        }
    } catch (e) {
        statusEl.querySelector('.status-message').textContent = `Error: ${e.message}`;
        statusEl.querySelector('.status-indicator').classList.remove('speaking');
    }
}

// Toggle live STT
async function toggleLiveSTT() {
    if (voiceState.isListening) {
        stopLiveSTT();
    } else {
        await startLiveSTT();
    }
}

// Start live STT
async function startLiveSTT() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // Use Web Speech API for live transcription
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            voiceState.liveSTT = new SpeechRecognition();
            voiceState.liveSTT.continuous = true;
            voiceState.liveSTT.interimResults = true;
            voiceState.liveSTT.lang = 'en-US';
            
            voiceState.liveSTT.onresult = (event) => {
                const sttOutput = document.getElementById('voice-stt-output');
                const ttsOutput = document.getElementById('voice-tts-output');
                
                let interimTranscript = '';
                let finalTranscript = '';
                
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += transcript;
                    } else {
                        interimTranscript += transcript;
                    }
                }
                
                // Update STT output
                if (sttOutput) {
                    sttOutput.innerHTML = `
                        <p class="final-text">${finalTranscript}</p>
                        <p class="interim-text">${interimTranscript}</p>
                    `;
                }
                
                // If we have final text, speak it with cloned voice
                if (finalTranscript) {
                    speakWithClonedVoice(finalTranscript);
                }
            };
            
            voiceState.liveSTT.start();
            voiceState.isListening = true;
            
            // Update UI
            const btn = document.getElementById('voice-stt-btn');
            btn.textContent = 'Stop Listening';
            btn.classList.add('recording');
            
        } else {
            alert('Speech recognition not supported in this browser. Please use Chrome.');
        }
        
    } catch (e) {
        console.error('Failed to start STT:', e);
        alert('Could not access microphone. Please allow microphone access.');
    }
}

// Stop live STT
function stopLiveSTT() {
    if (voiceState.liveSTT) {
        voiceState.liveSTT.stop();
        voiceState.liveSTT = null;
    }
    
    voiceState.isListening = false;
    
    // Update UI
    const btn = document.getElementById('voice-stt-btn');
    btn.textContent = 'Start Listening';
    btn.classList.remove('recording');
}

// Speak with cloned voice
async function speakWithClonedVoice(text) {
    const profileId = document.getElementById('voice-test-profile')?.value;
    const language = document.getElementById('voice-test-language')?.value || 'en';
    const ttsOutput = document.getElementById('voice-tts-output');
    const statusEl = document.getElementById('voice-tts-status');
    
    if (!profileId) {
        if (ttsOutput) {
            ttsOutput.innerHTML = '<p class="placeholder-text">Select a voice profile first</p>';
        }
        return;
    }
    
    // Show typing effect
    if (ttsOutput) {
        ttsOutput.innerHTML = '<p class="typing-text"></p>';
        const typingEl = ttsOutput.querySelector('.typing-text');
        
        // Typing animation
        let i = 0;
        const typeInterval = setInterval(() => {
            if (i < text.length) {
                typingEl.textContent += text.charAt(i);
                i++;
            } else {
                clearInterval(typeInterval);
            }
        }, 50);
    }
    
    // Show speaking status
    statusEl?.classList.remove('hidden');
    
    try {
        const formData = new FormData();
        formData.append('text', text);
        formData.append('profile_id', profileId);
        formData.append('language', language);
        
        const res = await fetch('/api/voice/clone/generate', {
            method: 'POST',
            body: formData
        });
        
        if (res.ok) {
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            
            audio.onended = () => {
                statusEl?.classList.add('hidden');
            };
            
            audio.play();
        } else {
            console.error('Voice generation failed');
            statusEl?.classList.add('hidden');
        }
    } catch (e) {
        console.error('Voice generation error:', e);
        statusEl?.classList.add('hidden');
    }
}

// Load built-in TTS providers
async function loadBuiltinProviders() {
    const providerSelect = document.getElementById('voice-builtin-provider');
    if (!providerSelect) return;
    
    try {
        const res = await fetch('/api/voice/models');
        const data = await res.json();
        
        providerSelect.innerHTML = '<option value="">Select provider...</option>' +
            Object.keys(data.voices || {}).map(p => `<option value="${p}">${p}</option>`).join('');
    } catch (e) {
        console.error('Failed to load providers:', e);
    }
}

// Load built-in voices for selected provider
async function loadBuiltinVoices() {
    const provider = document.getElementById('voice-builtin-provider')?.value;
    const voiceSelect = document.getElementById('voice-builtin-voice');
    if (!provider || !voiceSelect) return;
    
    try {
        const res = await fetch('/api/voice/models');
        const data = await res.json();
        
        const voices = data.voices?.[provider] || [];
        voiceSelect.innerHTML = '<option value="">Select voice...</option>' +
            voices.map(v => `<option value="${v.id}">${v.name || v.id}</option>`).join('');
    } catch (e) {
        console.error('Failed to load voices:', e);
    }
}

// Test built-in voice
async function testBuiltinVoice() {
    const provider = document.getElementById('voice-builtin-provider')?.value;
    const voice = document.getElementById('voice-builtin-voice')?.value;
    const text = document.getElementById('voice-test-text')?.value || 'Hello, this is a test.';
    
    if (!provider) {
        alert('Please select a provider');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('text', text);
        formData.append('voice', voice || '');
        formData.append('provider', provider);
        
        const res = await fetch('/api/voice/generate', {
            method: 'POST',
            body: formData
        });
        
        if (res.ok) {
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            audio.play();
        } else {
            const data = await res.json();
            alert(`Error: ${data.detail || 'Generation failed'}`);
        }
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

// Initialize voice workspace when switching to it
document.addEventListener('DOMContentLoaded', () => {
    // Add event listener for voice workspace
    const voiceBtn = document.querySelector('[data-workspace="voice"]');
    if (voiceBtn) {
        voiceBtn.addEventListener('click', () => {
            setTimeout(initVoiceWorkspace, 100);
        });
    }
    
    // Add input listener for profile name
    const nameInput = document.getElementById('voice-profile-name');
    if (nameInput) {
        nameInput.addEventListener('input', updateCreateButton);
    }
});
