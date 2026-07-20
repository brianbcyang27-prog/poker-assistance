/**
 * JARVIS — Unified Dashboard Application v6.0.0
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

    fetch(`/api/chat/stream?${params}`)
        .then(response => {
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
            setErrorState(true);
            _addTerminalLine(`ERROR: ${err.message}`, 'error');
            if (bubble) {
                bubble.innerHTML = _md('Error: ' + err.message);
            } else {
                addChatMessage('assistant', 'Error: ' + err.message);
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
    const responseDisplay = document.getElementById('response-display');
    const terminalLog = document.getElementById('terminal-log');

    // Hide all workspace-specific panels
    if (graphContainer) graphContainer.style.display = 'none';
    if (terminalLog) terminalLog.classList.remove('visible');

    switch (workspace) {
        case 'core':
            if (coreCanvas) coreCanvas.style.display = 'block';
            if (chatContainer) chatContainer.style.display = 'none';
            if (responseDisplay) responseDisplay.style.display = 'none';
            ensureGoldenCore()?.start();
            break;

        case 'chat':
            if (coreCanvas) coreCanvas.style.display = 'none';
            if (chatContainer) chatContainer.style.display = 'flex';
            if (responseDisplay) responseDisplay.style.display = 'none';
            currentChatMode = 'chat';
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
        btn.addEventListener('click', () => switchWorkspace(btn.dataset.workspace));
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
