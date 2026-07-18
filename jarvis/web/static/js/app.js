/**
 * JARVIS — Unified Dashboard Application v4.0.0
 * LEFT nav | CENTER core | RIGHT conversations + health | BOTTOM terminal + input
 */

let currentSessionId = null;
let selectedVoiceId = null;
let graph3d = null;
let currentViewMode = 'core';
let currentChatMode = 'popup';
let _startTime = Date.now();
let _eventCount = 0;
let _missionCount = 0;

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
        prov.innerHTML = '';
        for (const p of data.providers) {
            const o = document.createElement('option');
            o.value = p;
            o.textContent = p.charAt(0).toUpperCase() + p.slice(1);
            prov.appendChild(o);
        }
        prov.addEventListener('change', () => updateVoiceList(data.voices, prov.value));
        const cur = document.querySelector('[name="tts_provider"]')?.value || 'macos';
        prov.value = cur;
        updateVoiceList(data.voices, cur);
    } catch (_) {}
}

function updateVoiceList(voices, provider) {
    const sel = document.getElementById('tts-voice');
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
    form.elements['nvidia_api_key'].value = '';
}

function showToast(msg) {
    const t = document.getElementById('toast');
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

    if (currentChatMode === 'chat') {
        addChatMessage('user', message);
    }

    _addTerminalLine(`> ${message}`, 'info');

    if (window.jarvisState) window.jarvisState.startThinking();
    if (window.livingUI) window.livingUI.setState('thinking');
    if (graph3d) graph3d.setState('thinking');

    const params = new URLSearchParams({ message });
    if (currentSessionId) params.set('session_id', currentSessionId);

    // Create a streaming assistant bubble in chat mode
    let bubble = null;
    if (currentChatMode === 'chat') {
        bubble = addChatMessage('assistant', '');
    }

    let fullText = '';
    let firstToken = true;

    fetch(`/api/chat/stream?${params}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            function read() {
                reader.read().then(({ done, value }) => {
                    if (done) return;
                    buffer += decoder.decode(value, { stream: true });

                    // Split on double-newline (SSE frame boundary)
                    const frames = buffer.split('\n\n');
                    buffer = frames.pop(); // incomplete frame stays in buffer

                    for (const frame of frames) {
                        const trimmed = frame.trim();
                        if (!trimmed) continue;

                        // Parse one or more "data:" lines
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
                                        if (graph3d) graph3d.setState('speaking');
                                    }
                                    fullText += evt.content;
                                    if (bubble) {
                                        bubble.innerHTML = _md(fullText);
                                        bubble.parentElement.scrollTop = bubble.parentElement.scrollHeight;
                                    }
                                } else if (evt.type === 'done') {
                                    currentSessionId = evt.session_id || currentSessionId;
                                    setErrorState(false);
                                    if (window.jarvisState) window.jarvisState.set('idle');
                                    if (window.livingUI) window.livingUI.setState('idle');
                                    if (graph3d) graph3d.setState('idle');
                                } else if (evt.type === 'state') {
                                    // handled above
                                }
                            } catch (_) {}
                        }
                    }
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
            } else if (currentChatMode === 'chat') {
                addChatMessage('assistant', 'Error: ' + err.message);
            } else if (window.livingUI) {
                window.livingUI.showResponse('Error: ' + err.message);
            }
            if (window.jarvisState) window.jarvisState.set('idle');
            if (window.livingUI) window.livingUI.setState('idle');
            if (graph3d) graph3d.setState('idle');
        });
}

/* ---- Chat Mode Switching ---- */

function setChatMode(mode) {
    currentChatMode = mode;
    const chatContainer = document.getElementById('chat-container');
    const responseDisplay = document.getElementById('response-display');

    if (mode === 'chat') {
        chatContainer.style.display = 'flex';
        responseDisplay.style.display = 'none';
    } else {
        chatContainer.style.display = 'none';
        responseDisplay.style.display = '';
    }
}

function addChatMessage(role, text) {
    const container = document.getElementById('chat-messages');
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

function clearErrorState() {
    setErrorState(false);
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

/* ---- View Mode Switching ---- */

async function setViewMode(mode) {
    currentViewMode = mode;
    const coreCanvas = document.getElementById('jarvis-canvas');
    const graphContainer = document.getElementById('graph-container');

    if (mode === 'graph') {
        coreCanvas.style.display = 'none';
        graphContainer.style.display = 'block';

        if (!graph3d) {
            graph3d = new Graph3D(graphContainer);
            graph3d.init();
            await graph3d.loadData();
            if (window.jarvisState) {
                graph3d.setState(window.jarvisState.state || 'idle');
            }
        }
        graph3d.start();
    } else {
        coreCanvas.style.display = 'block';
        graphContainer.style.display = 'none';

        if (graph3d) {
            graph3d.stop();
            graph3d.destroy();
            graph3d = null;
        }
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

/* ---- Nav Panel Switching ---- */

function switchNavPanel(panelId) {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.panel === panelId);
    });

    const terminalLog = document.getElementById('terminal-log');

    switch (panelId) {
        case 'core':
            setViewMode('core');
            terminalLog.classList.remove('visible');
            break;
        case 'agents':
            setViewMode('core');
            terminalLog.classList.remove('visible');
            // Could show agent hierarchy overlay
            break;
        case 'graph':
            setViewMode('graph');
            terminalLog.classList.remove('visible');
            break;
        case 'health':
            setViewMode('core');
            terminalLog.classList.add('visible');
            _refreshHealth();
            break;
        case 'settings':
            toggleSettings();
            break;
    }
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

            document.getElementById('health-agents').textContent = `${activeWorkers}/${totalWorkers}`;
            document.getElementById('health-kings').textContent = `${totalKings}/4`;
            document.getElementById('health-events').textContent = _eventCount;
            document.getElementById('health-uptime').textContent = _formatUptime(Date.now() - _startTime);
            document.getElementById('health-missions').textContent = _missionCount;

            const statusEl = document.getElementById('health-status');
            statusEl.textContent = 'OK';
            statusEl.className = 'right-status health-ok';
        })
        .catch(() => {
            const statusEl = document.getElementById('health-status');
            statusEl.textContent = 'DOWN';
            statusEl.className = 'right-status';
            statusEl.style.color = '#ff3366';
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
    header.innerHTML = `<span class="agent-card">${data.card_id || '?'}</span> <span class="agent-name">${data.title || data.sender || '?'}</span>`;
    if (data.receiver) {
        header.innerHTML += ` → <span class="agent-recv">${data.receiver}</span>`;
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

/* ---- Init ---- */

document.addEventListener('DOMContentLoaded', async () => {
    try {
        window.jarvisCore = new JarvisCore(document.getElementById('jarvis-canvas'));
    } catch (e) { console.warn('JarvisCore:', e); }

    try {
        window.jarvisState = new JarvisState();
    } catch (e) { console.warn('JarvisState:', e); }

    try {
        window.audioAnalyzer = new AudioAnalyzer();
    } catch (e) { console.warn('AudioAnalyzer:', e); }

    try {
        window.livingUI = new LivingInterface();
    } catch (e) { console.warn('LivingInterface:', e); }

    try {
        window.deptIdentity = new DepartmentIdentity();
        window.deptIdentity.renderAll();
    } catch (e) { console.warn('DepartmentIdentity:', e); }

    try {
        window.explainability = new ExplainabilityOverlay();
    } catch (e) { console.warn('ExplainabilityOverlay:', e); }

    try {
        window.missionDAG = new MissionDAG(document.getElementById('mission-dag-container'));
        window.missionDAG.init();
    } catch (e) { console.warn('MissionDAG:', e); }

    if (window.jarvisState) {
        window.jarvisState.onStateChange(state => {
            if (window.jarvisCore) window.jarvisCore.setState(state);
            if (window.livingUI) window.livingUI.setState(state);
        });
    }

    if (window.jarvisState) window.jarvisState.set('idle');
    if (window.livingUI) {
        window.livingUI.setState('idle');
        window.livingUI.startMissionPolling();
        window.livingUI.connectEvents();
    }

    // Wire up nav panel switching
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => switchNavPanel(btn.dataset.panel));
    });

    loadSettings();

    // Apply view mode and chat mode from settings
    try {
        const res = await fetch('/api/settings');
        const settings = await res.json();
        if (settings.view_mode) {
            setViewMode(settings.view_mode);
        }
        if (settings.chat_mode) {
            setChatMode(settings.chat_mode);
        }
    } catch (_) {}

    // Health polling
    setInterval(_refreshHealth, 10000);
    _refreshHealth();

    // Intercept WS messages for right panel
    const origHandleWS = window.livingUI?._handleWSMessage;
    if (window.livingUI) {
        const orig = window.livingUI._handleWSMessage.bind(window.livingUI);
        window.livingUI._handleWSMessage = function(data) {
            orig(data);
            if (data.type === 'event') {
                _eventCount++;
                const ev = data.data;
                if (ev.event_type) {
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
            if (!ov.classList.contains('hidden')) toggleSettings();
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
