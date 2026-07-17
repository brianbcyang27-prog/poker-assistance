/**
 * JARVIS — Living Interface Application
 * The only persistent UI is the neural core and the input bar.
 * Everything else emerges and dissolves.
 */

let currentSessionId = null;
let selectedVoiceId = null;
let graph3d = null;
let currentViewMode = 'core';
let currentChatMode = 'popup';

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
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    if (!message) return;
    input.value = '';

    // Add user message to chat mode
    if (currentChatMode === 'chat') {
        addChatMessage('user', message);
    }

    if (window.jarvisState) window.jarvisState.startThinking();
    if (window.livingUI) window.livingUI.setState('thinking');
    if (graph3d) graph3d.setState('thinking');

    const body = { message, session_id: currentSessionId };
    if (selectedVoiceId) body.voice_id = selectedVoiceId;

    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    })
        .then(r => {
            if (!r.ok) {
                // Try to get error message from JSON, fall back to status text
                return r.text().then(text => {
                    let msg = r.statusText;
                    try { msg = JSON.parse(text).detail || text; } catch (_) { msg = text || msg; }
                    throw new Error(msg);
                });
            }
            return r.json();
        })
        .then(data => {
            currentSessionId = data.session_id;
            setErrorState(false);

            if (currentChatMode === 'chat') {
                addChatMessage('assistant', data.response);
            } else {
                if (window.livingUI) {
                    window.livingUI.showResponse(data.response, data.audio_url);
                }
            }

            if (data.audio_url && window.jarvisState) {
                window.jarvisState.startSpeaking();
                if (window.livingUI) window.livingUI.setState('speaking');
                if (graph3d) graph3d.setState('speaking');
            } else {
                if (window.jarvisState) window.jarvisState.set('idle');
                if (window.livingUI) window.livingUI.setState('idle');
                if (graph3d) graph3d.setState('idle');
            }
        })
        .catch(err => {
            setErrorState(true);
            const msg = err.message || 'Unknown error';
            if (currentChatMode === 'chat') {
                addChatMessage('assistant', 'Error: ' + msg);
            } else {
                if (window.livingUI) window.livingUI.showResponse('Error: ' + msg);
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
}

function _md(text) {
    // Sanitize: strip HTML tags to prevent XSS, then apply markdown
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
    const livingUI = document.getElementById('living-ui');

    if (mode === 'graph') {
        // Hide core + living UI, show 3D graph
        coreCanvas.style.display = 'none';
        graphContainer.style.display = 'block';
        livingUI.style.display = 'none';

        if (!graph3d) {
            graph3d = new Graph3D(graphContainer);
            graph3d.init();
            await graph3d.loadData();
            // Sync current state
            if (window.jarvisState) {
                graph3d.setState(window.jarvisState.state || 'idle');
            }
        }
        graph3d.start();
    } else {
        // Show core + living UI, hide graph
        coreCanvas.style.display = 'block';
        graphContainer.style.display = 'none';
        livingUI.style.display = '';

        if (graph3d) {
            graph3d.stop();
            graph3d.destroy();
            graph3d = null;
        }
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

    // v3.2.0: Initialize new components
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
        // v3.2.0: Connect to Event Bus WebSocket for real-time thought stream
        window.livingUI.connectEvents();
    }

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
