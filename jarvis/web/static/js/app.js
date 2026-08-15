/**
 * JARVIS — Unified Dashboard Application v8.0.0
 * LEFT nav (3 items) | CENTER workspace | RIGHT context | BOTTOM input
 */

let currentSessionId = localStorage.getItem('jarvis_session_id');
let currentWorkspace = 'home';
let currentChatMode = 'chat';
let _startTime = Date.now();
let _eventCount = 0;
let _healthInterval = null;

/* ---- Chat State ---- */
let _chatStreaming = false;
let _chatAbortController = null;

/* ---- Golden Neural Core lifecycle ---- */

let chatBg = null;

/* ---- Settings overlay ---- */

function toggleSettings() {
    document.getElementById('settings-overlay').classList.toggle('hidden');
    if (!document.getElementById('settings-overlay').classList.contains('hidden')) {
        loadVoiceCloneStatus();
        loadProviders();
        setupVoiceFileUpload();
        setupVoiceTabs();
        loadVoiceProfiles();
        loadBuiltinProviders();
        const textarea = document.getElementById('voice-test-text');
        if (textarea && !textarea.dataset.autoResize) {
            textarea.dataset.autoResize = 'true';
            textarea.addEventListener('input', function() {
                this.style.height = 'auto';
                this.style.height = this.scrollHeight + 'px';
            });
        }
        // Open first collapsible card in voice panel
        document.querySelectorAll('#panel-voice .settings-card:has(.settings-card-header)').forEach(c => c.classList.add('open'));
    }
}

function applyDeveloperMode(enabled) {
    const dashboard = document.getElementById('dashboard');
    const toggle = document.getElementById('dev-mode-toggle');
    if (!dashboard) return;
    dashboard.classList.toggle('dev-mode', enabled);
    if (toggle) {
        toggle.classList.toggle('active', enabled);
        toggle.setAttribute('aria-pressed', enabled ? 'true' : 'false');
    }
    localStorage.setItem('jarvis_developer_mode', enabled ? '1' : '0');
}

function toggleDeveloperMode() {
    const dashboard = document.getElementById('dashboard');
    applyDeveloperMode(!(dashboard && dashboard.classList.contains('dev-mode')));
}

function switchSettingsSection(sectionId) {
    document.querySelectorAll('.settings-nav-item').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.section === sectionId);
    });
    document.querySelectorAll('.settings-panel').forEach(panel => {
        panel.classList.remove('active', 'search-match');
    });
    const panel = document.getElementById(`panel-${sectionId}`);
    if (panel) panel.classList.add('active');
}

function filterSettings(query) {
    const q = query.toLowerCase().trim();
    if (!q) {
        document.querySelectorAll('.settings-panel').forEach(p => {
            p.classList.remove('search-match');
            p.style.display = '';
        });
        document.querySelectorAll('.settings-nav-item').forEach(btn => {
            btn.style.display = '';
        });
        switchSettingsSection(document.querySelector('.settings-nav-item.active')?.dataset.section || 'ai-model');
        return;
    }
    document.querySelectorAll('.settings-panel').forEach(panel => {
        const text = panel.textContent.toLowerCase();
        const match = text.includes(q);
        panel.classList.toggle('search-match', match);
        panel.style.display = match ? '' : 'none';
    });
    document.querySelectorAll('.settings-nav-item').forEach(btn => {
        const section = btn.dataset.section;
        const panel = document.getElementById(`panel-${section}`);
        btn.style.display = panel && panel.style.display !== 'none' ? '' : 'none';
    });
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
        setupVoiceFileUpload();
        setupVoiceTabs();
        loadVoiceProfiles();
        loadBuiltinProviders();
        // Setup textarea auto-resize (guarded against duplicate listeners)
        const textarea = document.getElementById('voice-test-text');
        if (textarea && !textarea.dataset.autoResize) {
            textarea.dataset.autoResize = 'true';
            textarea.addEventListener('input', function() {
                this.style.height = 'auto';
                this.style.height = this.scrollHeight + 'px';
            });
        }
    } catch (e) { console.warn('Failed to load settings:', e); }
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
    } catch (e) { console.warn('Failed to load voice models:', e); }
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
        // Architecture defaults
        active_architecture: 'jarvis_native',
        arch_planning_depth: 2,
        arch_verification_strictness: 0.8,
        arch_auto_reflect: true,
        arch_skill_extraction: true,
        arch_memory_retention_days: 30,
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
    if (window.jarvisStopSpeaking) window.jarvisStopSpeaking();
    sendMessageStreaming();
}

/* ---- Streaming Chat ---- */

function sendMessageStreaming() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    if (!message) return;
    if (_chatStreaming) return;
    input.value = '';

    // Hide empty state on first message
    _hideChatEmptyState();

    addChatMessage('user', message);
    _addTerminalLine(`> ${message}`, 'info');

    if (window.jarvisState) window.jarvisState.startThinking();
    if (window.livingUI) window.livingUI.setState('thinking');
    if (goldenCore) goldenCore.setState('thinking');

    _sendMessageAsync(message);
}

async function _sendMessageAsync(message) {
    // Ensure session exists before streaming
    if (!currentSessionId) {
        try {
            const res = await fetch('/api/chat/sessions', { method: 'POST' });
            const data = await res.json();
            if (data.ok && data.session_id) {
                currentSessionId = data.session_id;
                localStorage.setItem('jarvis_session_id', currentSessionId);
            }
        } catch (e) { console.warn('Failed to create session:', e); }
    }

    const params = new URLSearchParams({ message });
    if (currentSessionId) params.set('session_id', currentSessionId);

    let bubble = addChatMessage('assistant', '');
    let fullText = '';
    let firstToken = true;
    let toolCalls = [];

    _chatStreaming = true;
    _chatAbortController = new AbortController();
    const timeout = setTimeout(() => _chatAbortController.abort(), 30000);
    
    fetch(`/api/chat/stream?${params}`, { signal: _chatAbortController.signal })
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
                            } else if (evt.type === 'tool_calls') {
                                toolCalls = evt.calls || [];
                                if (toolCalls.length > 0 && window.MissionTimeline) {
                                    const panel = document.getElementById('timeline-panel');
                                    if (panel) panel.style.display = '';
                                    if (!window._missionTimeline) {
                                        window._missionTimeline = new MissionTimeline('mission-timeline');
                                        window._missionTimeline.subscribe();
                                    }
                                    window._missionTimeline.setTimeline(toolCalls.map(tc => ({
                                        event_type: tc.ok ? 'tool.complete' : 'tool.fail',
                                        label: tc.name || 'Tool call',
                                        status: tc.ok ? 'success' : 'failed',
                                        description: tc.error || (tc.ok ? 'Completed' : ''),
                                        duration_ms: tc.duration_ms
                                    })));
                                }
                            } else if (evt.type === 'mission_start') {
                                // Auto-switch to chat workspace if not already there, then show mission panel
                                if (currentWorkspace !== 'chat') {
                                    switchWorkspace('chat');
                                }
                                if (window.missionPanel) {
                                    window.missionPanel.show(evt.mission);
                                }
                            } else if (evt.type === 'mission_plan') {
                                // Update mission panel with plan
                                if (window.missionPanel && window.missionPanel.currentMission) {
                                    window.missionPanel.currentMission.plan = evt.plan;
                                    window.missionPanel.renderPlan(evt.plan);
                                }
                            } else if (evt.type === 'mission_step') {
                                // Update step status in mission panel
                                if (window.missionPanel && evt.step && evt.result) {
                                    const stepId = evt.step.id;
                                    const status = evt.result.success ? 'success' : 'failed';
                                    window.missionPanel.updateStepStatus(stepId, status, {
                                        tools: evt.result.output?.tools,
                                        output: typeof evt.result.output === 'object' ? JSON.stringify(evt.result.output) : String(evt.result.output),
                                        duration_ms: evt.result.duration_ms
                                    });
                                }
                            } else if (evt.type === 'mission_verify') {
                                // Render verification results in verification tab
                                if (window.missionPanel) {
                                    window.missionPanel.renderVerification(evt.verification);
                                }
                            } else if (evt.type === 'mission_reflect') {
                                // Render reflection in reflection tab
                                if (window.missionPanel) {
                                    window.missionPanel.renderReflection(evt.reflection);
                                }
                            } else if (evt.type === 'done') {
                                currentSessionId = evt.session_id || currentSessionId;
                                if (currentSessionId) localStorage.setItem('jarvis_session_id', currentSessionId);
                                _chatStreaming = false;
                                _chatAbortController = null;
                                setErrorState(false);
                                if (bubble && fullText) {
                                    bubble.remove();
                                    bubble = addChatMessage('assistant', fullText, { toolCalls });
                                }
                                if (window.jarvisState) window.jarvisState.set('idle');
                                if (window.livingUI) window.livingUI.setState('idle');
                                if (goldenCore) goldenCore.setState('idle');
                                // Close the voice loop: speak the final result aloud
                                if (window.jarvisLastInputViaVoice && window.jarvisSpeak && fullText) {
                                    window.jarvisLastInputViaVoice = false;
                                    window.jarvisSpeak(fullText);
                                }
                                // Refresh sidebar to show updated conversation
                                loadSessionList();
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
                }).catch(err => {
                    clearTimeout(timeout);
                    _chatStreaming = false;
                    _chatAbortController = null;
                    setErrorState(true);
                    const errorMsg = err?.name === 'AbortError'
                        ? 'Request timed out. Please try again.'
                        : 'Error: ' + (err?.message || 'Stream read failed');
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
            read();
        })
        .catch(err => {
            clearTimeout(timeout);
            _chatStreaming = false;
            _chatAbortController = null;
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

function addChatMessage(role, text, meta) {
    const container = document.getElementById('chat-messages');
    if (!container) return null;
    const msg = document.createElement('div');
    msg.className = `chat-msg ${role}`;

    if (role === 'assistant') {
        const { thinking, content } = splitThinking(text);
        let html = '';

        if (thinking) {
            html += `<div class="chat-thinking">
                <button class="thinking-toggle" onclick="this.parentElement.classList.toggle('open')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
                    <span>Reasoning</span>
                </button>
                <div class="thinking-body">${_md(thinking)}</div>
            </div>`;
        }

        html += `<div class="chat-content">${_md(content)}</div>`;

        if (meta && meta.toolCalls && meta.toolCalls.length > 0) {
            html += `<div class="chat-tool-summary">
                <button class="tool-toggle" onclick="this.parentElement.classList.toggle('open')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
                    <span>${meta.toolCalls.length} tool call${meta.toolCalls.length > 1 ? 's' : ''}</span>
                </button>
                <div class="tool-list">
                    ${meta.toolCalls.map(tc => `<div class="tool-item ${tc.ok ? 'success' : 'failed'}">
                        <span class="tool-icon">${tc.ok ? '✓' : '✗'}</span>
                        <span class="tool-name">${_escHtml(tc.name)}</span>
                        <span class="tool-status">${tc.ok ? 'Done' : tc.error || 'Failed'}</span>
                    </div>`).join('')}
                </div>
            </div>`;
        }

        msg.innerHTML = html;
    } else {
        msg.innerHTML = _escHtml(text);
    }

    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    return msg;
}

function splitThinking(text) {
    const thinkPatterns = [
        /^(I (?:can |will |'ll |would |should )).{20,}/m,
        /^(Here(?:'s| is) (?:what I'll| the plan| how)).{20,}/m,
        /^(Let me ).{20,}/m,
        /^(To (?:do this|create|make|help)).{20,}/m,
        /^(I (?:understand|see|notice)).{20,}/m,
    ];

    const lines = text.split('\n');
    let thinkingEnd = 0;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;
        const isThinkLine = thinkPatterns.some(p => p.test(line));
        if (isThinkLine && i < 6) {
            thinkingEnd = i + 1;
        } else if (thinkingEnd > 0) {
            break;
        }
    }

    if (thinkingEnd > 0 && thinkingEnd < lines.length) {
        return {
            thinking: lines.slice(0, thinkingEnd).join('\n').trim(),
            content: lines.slice(thinkingEnd).join('\n').trim()
        };
    }
    return { thinking: null, content: text };
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


/* ---- Workspace Switching ---- */

async function switchWorkspace(workspace) {
    // Settings is a modal overlay, not a workspace view: open it without
    // hiding the current view (otherwise the workspace stays blank after
    // the overlay closes).
    if (workspace === 'settings') {
        toggleSettings();
        return;
    }

    const prev = currentWorkspace;
    currentWorkspace = workspace;

    // Save state of previous workspace
    if (prev && window.workspaceMgr) {
        workspaceMgr.switchTo(workspace);
    }

    // Update nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.workspace === workspace);
    });

    // Get all workspace views
    const views = document.querySelectorAll('.workspace-view');
    const homeContainer = document.getElementById('home-container');
    const chatContainer = document.getElementById('chat-container');
    const responseDisplay = document.getElementById('response-display');
    const terminalLog = document.getElementById('terminal-log');

    // Hide all workspace views with fade transition
    views.forEach(v => {
        v.classList.remove('active');
        v.style.display = 'none';
    });

    if (terminalLog) terminalLog.classList.remove('visible');
    if (responseDisplay) responseDisplay.style.display = 'none';

    // Lazy-load workspace-specific scripts
    if (workspace === 'chat') {
        try {
            await Promise.all([
                window._loadScript('/static/js/chat-background.js?v=9.2.0'),
                window._loadScript('/static/js/voice-experience.js?v=9.2.0'),
                window._loadScript('/static/js/vision-experience.js?v=9.2.0'),
                window._loadScript('/static/js/computer-control.js?v=9.2.0'),
            ]);
        } catch (e) {
            console.warn('Failed to load chat workspace scripts:', e);
        }
    }

    if (workspace === 'projects') {
        try {
            await window._loadScript('/static/js/project-dashboard.js?v=9.2.0');
            if (window.ProjectDashboard && !window.ProjectDashboard.initialized) {
                window.ProjectDashboard.init(document.getElementById('projects-container'));
            }
            window.ProjectDashboard.refresh();
        } catch (e) {
            console.warn('Failed to load project dashboard scripts:', e);
        }
    }

    if (workspace === 'execution') {
        try {
            const loads = [window._loadScript('/static/js/execution-view.js?v=9.2.0')];
            if (typeof MissionDAG === 'undefined') {
                loads.push(window._loadScript('/static/js/mission-dag.js?v=9.2.0'));
            }
            if (typeof MissionTimeline === 'undefined') {
                loads.push(window._loadScript('/static/js/mission-timeline.js?v=9.2.0'));
            }
            await Promise.all(loads);
            if (window.ExecutionView && !window.ExecutionView.initialized) {
                window.ExecutionView.init(document.getElementById('execution-container'));
            }
            window.ExecutionView.refreshProjects();
        } catch (e) {
            console.warn('Failed to load execution view scripts:', e);
        }
    }

    if (workspace === 'knowledge') {
        try {
            await window._loadScript('/static/js/knowledge-graph.js?v=9.2.0');
            if (window.KnowledgeGraph && !window.KnowledgeGraph.initialized) {
                window.KnowledgeGraph.init(document.getElementById('knowledge-container'));
            }
            window.KnowledgeGraph.refreshProjects();
        } catch (e) {
            console.warn('Failed to load knowledge graph scripts:', e);
        }
    }

    switch (workspace) {
        case 'home':
            if (homeContainer) {
                homeContainer.style.display = 'block';
                homeContainer.classList.add('active');
            }
            if (chatBg) { chatBg.stop(); chatBg = null; }
            if (window.goldenCore && !window.goldenCore.running) window.goldenCore.start();
            break;

        case 'chat':
            if (chatContainer) {
                chatContainer.style.display = 'flex';
                chatContainer.classList.add('active');
            }
            currentChatMode = 'chat';
            if (!chatBg && window.ChatBackground) {
                chatBg = new ChatBackground(document.getElementById('chat-core-bg'));
                chatBg.start();
            }
            await loadChatHistory();
            break;

        case 'projects':
            if (homeContainer) homeContainer.style.display = 'none';
            if (chatContainer) chatContainer.style.display = 'none';
            const projectsContainer = document.getElementById('projects-container');
            if (projectsContainer) {
                projectsContainer.style.display = 'flex';
                projectsContainer.classList.add('active');
            }
            break;

        case 'execution':
            if (homeContainer) homeContainer.style.display = 'none';
            if (chatContainer) chatContainer.style.display = 'none';
            const executionContainer = document.getElementById('execution-container');
            if (executionContainer) {
                executionContainer.style.display = 'flex';
                executionContainer.classList.add('active');
            }
            break;

        case 'knowledge':
            if (homeContainer) homeContainer.style.display = 'none';
            if (chatContainer) chatContainer.style.display = 'none';
            const knowledgeContainer = document.getElementById('knowledge-container');
            if (knowledgeContainer) {
                knowledgeContainer.style.display = 'flex';
                knowledgeContainer.classList.add('active');
            }
            break;
    }

    // Performance: stop chat background when not on chat
    if (workspace !== 'chat' && chatBg) {
        chatBg.stop();
        chatBg = null;
    }

    // Show/hide global new-chat FAB (hidden when on chat, since sidebar button is available)
    const fab = document.getElementById('global-new-chat');
    if (fab) {
        if (workspace === 'chat') {
            fab.classList.remove('visible');
        } else {
            fab.classList.add('visible');
        }
    }

    // Update dynamic right sidebar context
    _updateSidebarContext(workspace);
}

/* ---- Chat History ---- */

async function loadChatHistory() {
    if (!currentSessionId) {
        try {
            const res = await fetch('/api/chat/sessions?limit=1');
            if (!res.ok) return;
            const data = await res.json();
            if (data.sessions && data.sessions.length > 0) {
                currentSessionId = data.sessions[0].session_id;
                // Load history for this session
                const historyRes = await fetch(`/api/chat/history/${currentSessionId}`);
                if (!historyRes.ok) return;
                const messages = await historyRes.json();
                const container = document.getElementById('chat-messages');
                if (container) {
                    container.innerHTML = '';
                    for (const msg of messages) {
                        addChatMessage(msg.role, msg.content);
                    }
                }
                return;
            }
        } catch (_) {}
    }

    if (!currentSessionId) {
        _showChatEmptyState();
        return;
    }

    try {
        const res = await fetch(`/api/chat/history/${currentSessionId}`);
        if (!res.ok) return;
        const messages = await res.json();
        const container = document.getElementById('chat-messages');
        if (!container) return;
        container.innerHTML = '';

        if (messages.length === 0) {
            _showChatEmptyState();
        } else {
            for (const msg of messages) {
                addChatMessage(msg.role, msg.content);
            }
        }
    } catch (_) {
        _showChatEmptyState();
    }
}

/* ---- Knowledge Graph Workspace ---- */


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
            for (const king of Object.values(kings)) {
                const workers = king.workers || {};
                totalWorkers += Object.keys(workers).length;
                for (const w of Object.values(workers)) {
                    if (w.state !== 'idle') activeWorkers++;
                }
            }

            const el = document.getElementById('health-agents');
            if (el) el.textContent = `${activeWorkers}/${totalWorkers}`;
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

    fetch('/api/domains')
        .then(r => r.json())
        .then(data => {
            const domains = data.domains || [];
            const userDomains = domains.filter(d => d.domain !== 'system');
            const del = document.getElementById('health-domains');
            if (del) del.textContent = `${userDomains.length}/6`;
        })
        .catch(() => {
            const del = document.getElementById('health-domains');
            if (del) del.textContent = '-';
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

/* ---- Dynamic Sidebar Context ---- */

function _updateSidebarContext(workspace) {
    // Hide all contexts
    document.querySelectorAll('.right-context').forEach(ctx => {
        ctx.style.display = 'none';
    });
    // Show the matching context
    const target = document.getElementById(`right-${workspace}`);
    if (target) {
        target.style.display = 'flex';
    } else {
        // Fallback to home context
        const home = document.getElementById('right-home');
        if (home) home.style.display = 'flex';
    }
}

/* ---- Session Management ---- */

async function startNewChat() {
    // 1. Abort any in-flight streaming request
    if (_chatAbortController) {
        _chatAbortController.abort();
        _chatAbortController = null;
    }
    _chatStreaming = false;

    // 2. Reset all temporary chat state
    _resetChatState();

    // 3. Create new session on server
    try {
        const res = await fetch('/api/chat/sessions', { method: 'POST' });
        const data = await res.json();
        if (data.ok && data.session_id) {
            currentSessionId = data.session_id;
            localStorage.setItem('jarvis_session_id', currentSessionId);
        } else {
            currentSessionId = null;
        }
    } catch (e) {
        console.warn('Failed to create session:', e);
        currentSessionId = null;
    }

    // 4. Clear the chat messages container
    const container = document.getElementById('chat-messages');
    if (container) container.innerHTML = '';

    // 5. Show empty state
    _showChatEmptyState();

    // 6. Hide mission timeline
    const timeline = document.getElementById('timeline-panel');
    if (timeline) timeline.style.display = 'none';

    // 7. Switch to chat workspace
    switchWorkspace('chat');

    // 8. Reload session sidebar
    await loadSessionList();

    // 9. Focus input
    const input = document.getElementById('message-input');
    if (input) input.focus();
}

function _resetChatState() {
    // Reset streaming state
    _chatStreaming = false;
    _chatAbortController = null;

    // Reset UI state managers
    if (window.jarvisState) window.jarvisState.set('idle');
    if (window.livingUI) window.livingUI.setState('idle');
    if (goldenCore) goldenCore.setState('idle');

    // Clear terminal log
    const entries = document.getElementById('terminal-entries');
    if (entries) entries.innerHTML = '';

    // Clear error state
    setErrorState(false);
}

function _showChatEmptyState() {
    const container = document.getElementById('chat-messages');
    if (!container) return;
    container.innerHTML = `
        <div class="chat-empty-state">
            <div class="chat-empty-icon">
                <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="1">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
            </div>
            <h3>How can I help you today?</h3>
            <p>Start a conversation with JARVIS</p>
        </div>`;
}

function _hideChatEmptyState() {
    const emptyState = document.querySelector('.chat-empty-state');
    if (emptyState) emptyState.remove();
}

async function loadSessionList() {
    try {
        const res = await fetch('/api/chat/sessions?limit=20');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const list = document.getElementById('session-list');
        if (!list || !data.sessions) return;
        list.innerHTML = '';
        for (const session of data.sessions) {
            const item = document.createElement('div');
            item.className = 'session-item';
            if (session.session_id === currentSessionId) item.classList.add('active');
            item.dataset.sessionId = session.session_id;

            const header = document.createElement('div');
            header.className = 'session-header';

            const preview = document.createElement('div');
            preview.className = 'session-preview';
            preview.textContent = session.title || session.preview || 'New conversation';
            const meta = document.createElement('div');
            meta.className = 'session-meta';
            meta.textContent = `${session.message_count} messages`;
            const actions = document.createElement('div');
            actions.className = 'session-actions';

            const renameBtn = document.createElement('button');
            renameBtn.type = 'button';
            renameBtn.className = 'session-action-btn';
            renameBtn.textContent = 'Rename';
            renameBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                renameSession(session.session_id, session.title || session.preview || 'New conversation');
            });

            const deleteBtn = document.createElement('button');
            deleteBtn.type = 'button';
            deleteBtn.className = 'session-action-btn danger';
            deleteBtn.textContent = 'Delete';
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                deleteSession(session.session_id);
            });

            actions.appendChild(renameBtn);
            actions.appendChild(deleteBtn);
            header.appendChild(preview);
            header.appendChild(actions);
            item.appendChild(header);
            item.appendChild(meta);
            item.addEventListener('click', () => {
                // Save current state before switching (messages are saved per-message in DB)
                if (_chatStreaming && _chatAbortController) {
                    _chatAbortController.abort();
                    _chatStreaming = false;
                    _chatAbortController = null;
                }
                currentSessionId = session.session_id;
                loadChatHistory();
                document.querySelectorAll('.session-item').forEach(s => s.classList.remove('active'));
                item.classList.add('active');
            });
            list.appendChild(item);
        }
    } catch (_) {}
}

async function renameSession(sessionId, currentTitle) {
    const title = prompt('Rename conversation', currentTitle || 'New conversation');
    if (title === null) return;

    try {
        const res = await fetch(`/api/chat/sessions/${sessionId}/rename`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title }),
        });
        if (res.ok) {
            await loadSessionList();
        }
    } catch (_) {}
}

async function deleteSession(sessionId) {
    if (!confirm('Delete this conversation?')) return;

    try {
        const res = await fetch(`/api/chat/sessions/${sessionId}`, { method: 'DELETE' });
        if (res.ok) {
            if (currentSessionId === sessionId) {
                currentSessionId = null;
                localStorage.removeItem('jarvis_session_id');
                _resetChatState();
                const container = document.getElementById('chat-messages');
                if (container) container.innerHTML = '';
                _showChatEmptyState();
            }
            await loadSessionList();
            if (currentSessionId) {
                await loadChatHistory();
            }
        }
    } catch (_) {}
}

/* ---- Home Workspace ---- */

function _initHome() {
    // Set greeting based on time of day
    const hour = new Date().getHours();
    const greetingEl = document.getElementById('home-greeting-text');
    if (greetingEl) {
        if (hour < 6) greetingEl.textContent = 'Good night';
        else if (hour < 12) greetingEl.textContent = 'Good morning';
        else if (hour < 17) greetingEl.textContent = 'Good afternoon';
        else greetingEl.textContent = 'Good evening';
    }

    // Load project context
    _loadHomeContext();

    // Load recent conversations
    _loadHomeRecent();

    // Load suggestions
    _loadHomeSuggestions();

    // Wire input
    const input = document.getElementById('home-message-input');
    if (input) {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendHomeMessage();
            }
        });
    }
}

async function _loadHomeContext() {
    const el = document.getElementById('home-project-context');
    if (!el) return;
    try {
        const res = await fetch('/api/workspace');
        if (!res.ok) return;
        const data = await res.json();
        const projects = Array.isArray(data) ? data : (data.workspaces || []);
        if (projects.length > 0) {
            const active = projects.find(p => p.status === 'active') || projects[0];
            el.textContent = active.goal || active.name || '';
        }
    } catch (e) { console.warn('Failed to load project context:', e); }
}

async function _loadHomeRecent() {
    const list = document.getElementById('home-recent-list');
    const section = document.getElementById('home-recent-section');
    if (!list || !section) return;
    try {
        const res = await fetch('/api/chat/sessions');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const sessions = data.sessions || data || [];
        if (sessions.length === 0) {
            section.style.display = 'none';
            return;
        }
        list.innerHTML = sessions.slice(0, 5).map(s => `
            <div class="home-list-item" onclick="loadSession('${s.id || s.session_id || ''}')">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <span>${s.title || s.name || 'Untitled conversation'}</span>
            </div>
        `).join('');
    } catch (e) {
        console.warn('Failed to load recent sessions:', e);
        section.style.display = 'none';
    }
}

function _loadHomeSuggestions() {
    const container = document.getElementById('home-suggestions');
    if (!container) return;
    const suggestions = [
        'Help me debug a problem',
        'Explain this code',
        'Write a function',
        'Review my changes',
        'What should I work on?',
    ];
    container.innerHTML = suggestions.map(s => `
        <button class="home-suggestion-chip" onclick="sendHomeMessage('${s.replace(/'/g, "\\'")}')">${s}</button>
    `).join('');
}

function sendHomeMessage(text) {
    const input = document.getElementById('home-message-input');
    const message = text || (input ? input.value.trim() : '');
    if (!message) return;
    if (input) input.value = '';

    switchWorkspace('chat').then(() => {
        _sendMessageAfterWorkspaceReady(message);
    });
}

function _sendMessageAfterWorkspaceReady(message) {
    const chatInput = document.getElementById('message-input');
    if (chatInput && chatInput.offsetParent !== null) {
        chatInput.value = message;
        chatInput.dispatchEvent(new Event('input'));
        sendMessage();
        return;
    }
    // Chat workspace loads asynchronously — retry until it's visible
    let attempts = 0;
    const timer = setInterval(() => {
        const el = document.getElementById('message-input');
        if ((el && el.offsetParent !== null) || ++attempts >= 20) {
            clearInterval(timer);
            if (el && el.offsetParent !== null) {
                el.value = message;
                el.dispatchEvent(new Event('input'));
                sendMessage();
            }
        }
    }, 50);
}

/* ---- Init ---- */

function dismissOnboarding() {
    const overlay = document.getElementById('onboarding-overlay');
    if (overlay) overlay.classList.add('hidden');
    localStorage.setItem('jarvis_onboarded', '1');
}

document.addEventListener('DOMContentLoaded', async () => {
    // Show onboarding on first visit
    if (!localStorage.getItem('jarvis_onboarded')) {
        const overlay = document.getElementById('onboarding-overlay');
        if (overlay) overlay.classList.remove('hidden');
    }

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
        if (window.livingUI.connectEvents) {
            window.livingUI.connectEvents();
        }
    } catch (e) { console.warn('LivingInterface:', e); }

    // Lazy-load explainability + mission DAG (not needed on initial load)
    window._loadScript('/static/js/explainability.js?v=9.2.0').then(() => {
        try { window.explainability = new ExplainabilityOverlay(); } catch (e) { console.warn('Explainability init failed:', e); }
    }).catch(() => {});
    window._loadScript('/static/js/mission-dag.js?v=9.2.0').then(() => {
        try {
            window.missionDAG = new MissionDAG(document.getElementById('mission-dag-container'));
            window.missionDAG.init();
        } catch (e) { console.warn('MissionDAG init failed:', e); }
    }).catch(() => {});
    window._loadScript('/static/js/mission-timeline.js?v=9.2.0').catch(() => {});
    window._loadScript('/static/js/graph-3d.js?v=9.2.0').then(() => {
        if (window.Graph3D) {
            try {
                window.goldenCore = new Graph3D(document.getElementById('golden-core-container'));
                window.goldenCore.init();
                window.goldenCore.loadData();
                window.goldenCore.start();
            } catch (e) {
                console.warn('Golden core visualization unavailable:', e);
            }
        }
    }).catch(() => {});
    window._loadScript('/static/js/digital-twin.js?v=9.2.0').then(() => {
        if (window.DigitalTwin) {
            window._digitalTwin = new DigitalTwin('digital-twin-container');
            window._digitalTwin.init();
            if (window.jarvisState) {
                window.jarvisState.onStateChange(state => window._digitalTwin.setState(state));
            }
        }
    }).catch(() => {});

    // Wire up state changes to all visual systems
    if (window.jarvisState) {
        window.jarvisState.onStateChange(state => {
            if (window.goldenCore) window.goldenCore.setState(state);
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

    // Initialize workspace state manager
    if (window.WorkspaceManager) {
        window.workspaceMgr = new WorkspaceManager();
        window.workspaceMgr._hydrate();
    }

    applyDeveloperMode(localStorage.getItem('jarvis_developer_mode') === '1');

    // Wire up workspace navigation
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.id === 'dev-mode-toggle' || btn.dataset.workspace === 'developer') {
                window.location.href = '/dashboard';
                return;
            }
            if (btn.dataset.workspace) {
                if (btn.dataset.workspace === 'chat' && currentWorkspace === 'chat') {
                    startNewChat();
                } else {
                    switchWorkspace(btn.dataset.workspace);
                }
            }
        });
    });

    // Initialize Command Palette (⌘K)
    if (window.CommandPalette) {
        window._cmdPalette = new CommandPalette();
        document.addEventListener('keydown', (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                window._cmdPalette.toggle();
            }
        });
    }

    // Load settings and apply modes
    await loadSettings();
    try {
        const res = await fetch('/api/settings');
        const settings = await res.json();
        if (settings.chat_mode) {
            currentChatMode = settings.chat_mode;
        }
    } catch (_) {}

    // Set default workspace to home
    switchWorkspace('home');

    // Initialize home workspace
    _initHome();

    // Health polling (stored for cleanup)
    _healthInterval = setInterval(_refreshHealth, 10000);
    _refreshHealth();

    // Load session list for chat sidebar
    loadSessionList();

    // Wire new-chat button
    const newChatBtn = document.getElementById('new-chat-btn');
    if (newChatBtn) {
        newChatBtn.addEventListener('click', () => startNewChat());
    }

    // Show global new-chat FAB on initial load (home workspace)
    const globalFab = document.getElementById('global-new-chat');
    if (globalFab) globalFab.classList.add('visible');

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
            if (data.type === 'status' && data.data) {
                _updateHealthFromStatus(data.data);
            }
        };
    }

    // v9.2.0 D4: unified live activity stream on the right-home panel
    if (window.ActivityStream && !window.activityStream) {
        window.activityStream = new ActivityStream('agent-conversation-stream');
        window.activityStream.subscribe();
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', e => {
        if ((e.ctrlKey || e.metaKey) && e.key === ',') {
            e.preventDefault();
            toggleSettings();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            startNewChat();
        }
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'D') {
            e.preventDefault();
            toggleDeveloperMode();
        }
        if (e.key === 'Escape') {
            const ov = document.getElementById('settings-overlay');
            if (ov && !ov.classList.contains('hidden')) toggleSettings();
        }
    });

    // Animate loading steps
    const steps = document.querySelectorAll('.loading-step');
    const statusEl = document.getElementById('loading-status');
    const barFill = document.getElementById('loading-bar-fill');
    const etaEl = document.getElementById('loading-eta');
    const stepNames = ['Checking Python', 'Loading Dependencies', 'Connecting Database', 'Loading Configuration', 'Preparing Agents', 'Loading Voice', 'Connecting Browser', 'Almost Ready'];
    
    for (let i = 0; i < steps.length; i++) {
        await new Promise(r => setTimeout(r, 150 + Math.random() * 200));
        // Mark previous as done
        if (i > 0) steps[i - 1].classList.remove('active'), steps[i - 1].classList.add('done');
        steps[i].classList.add('active');
        if (statusEl) statusEl.textContent = stepNames[i] || 'Loading...';
        if (barFill) barFill.style.width = `${((i + 1) / steps.length) * 100}%`;
        if (etaEl) {
            const remaining = Math.ceil((steps.length - i - 1) * 0.2);
            etaEl.textContent = remaining > 0 ? `~${remaining}s remaining` : 'Ready';
        }
    }
    // Mark last as done
    if (steps.length > 0) {
        steps[steps.length - 1].classList.remove('active');
        steps[steps.length - 1].classList.add('done');
    }
    if (statusEl) statusEl.textContent = 'JARVIS Ready';
    if (etaEl) etaEl.textContent = '';

    // Dismiss loading screen with premium fade
    requestAnimationFrame(() => {
        setTimeout(() => {
            const loadingScreen = document.getElementById('loading-screen');
            const app = document.getElementById('app');
            if (loadingScreen) loadingScreen.classList.add('hidden');
            if (app) {
                app.style.transition = 'opacity 0.8s cubic-bezier(0.16, 1, 0.3, 1)';
                app.style.opacity = '1';
            }
        }, 400);
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

/* ---- Projects ---- */


/* ---- Metrics ---- */



/* ---- Voice Cloning ---- */

async function loadVoiceCloneStatus() {
    const statusEl = document.getElementById('clone-status-text');
    const profilesListEl = document.getElementById('clone-profiles-list');
    
    try {
        const res = await fetch('/api/voice/clone/status');
        if (!res.ok) return;
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
        if (!profilesRes.ok) return;
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

async function loadSession(sessionId) {
    if (!sessionId) return;
    if (_chatStreaming && _chatAbortController) {
        _chatAbortController.abort();
        _chatStreaming = false;
        _chatAbortController = null;
    }
    currentSessionId = sessionId;
    localStorage.setItem('jarvis_session_id', sessionId);
    await switchWorkspace('chat');
    await loadChatHistory();
    loadSessionList();
}

async function testCloneVoice(profileId) {
    if (!profileId) return;
    try {
        const res = await fetch(`/api/voice/clone/profiles/${profileId}/audio`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.onended = () => URL.revokeObjectURL(url);
        await audio.play();
    } catch (e) {
        alert('Could not play reference audio: ' + e.message);
    }
}

async function deleteCloneProfile(profileId) {
    if (!profileId) return;
    if (!confirm('Delete this voice profile?')) return;
    try {
        const res = await fetch(`/api/voice/clone/profiles/${profileId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        await loadVoiceCloneStatus();
    } catch (e) {
        alert('Could not delete voice profile: ' + e.message);
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
    selectedProfile: null,
    audioContext: null,
    waveformAnimation: null
};

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
let _voiceUploadInit = false;
let _voiceTabsInit = false;

function setupVoiceFileUpload() {
    if (_voiceUploadInit) return;
    const dropZone = document.getElementById('voice-drop-zone');
    const fileInput = document.getElementById('voice-file-input');
    
    if (!dropZone || !fileInput) return;
    _voiceUploadInit = true;
    
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
    if (_voiceTabsInit) return;
    const tabs = document.querySelectorAll('.voice-tab');
    if (tabs.length === 0) return;
    _voiceTabsInit = true;
    
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
    
    // Release audio resources — cancel render loop and close context
    if (voiceState.waveformAnimation) {
        cancelAnimationFrame(voiceState.waveformAnimation);
        voiceState.waveformAnimation = null;
    }
    if (voiceState.audioContext) {
        voiceState.audioContext.close().catch(() => {});
        voiceState.audioContext = null;
    }
}

// Start waveform visualization
function startWaveform(stream) {
    const canvas = document.getElementById('waveform-canvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!voiceState.audioContext) {
        voiceState.audioContext = new AudioContext();
    }
    const audioContext = voiceState.audioContext;
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

// Load built-in TTS providers
async function loadBuiltinProviders() {
    const providerSelect = document.getElementById('voice-builtin-provider');
    if (!providerSelect) return;
    
    try {
        const res = await fetch('/api/voice/models');
        const data = await res.json();
        
        providerSelect.innerHTML = '<option value="">Select provider...</option>' +
            Object.keys(data.voices || {}).map(p => `<option value="${p}">${p}</option>`).join('');
        const cur = document.querySelector('[name="tts_provider"]')?.value || 'macos';
        providerSelect.value = cur;
        await loadBuiltinVoices();
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
        const cur = document.querySelector('[name="tts_voice"]')?.value || '';
        if (cur) voiceSelect.value = cur;
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
    // Voice workspace initialization is now handled by settings page
    
    // Add input listener for profile name
    const nameInput = document.getElementById('voice-profile-name');
    if (nameInput) {
        nameInput.addEventListener('input', updateCreateButton);
    }
});
