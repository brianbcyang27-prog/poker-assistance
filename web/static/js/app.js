/**
 * JARVIS v4.0.0 - Main Application Orchestrator
 * "LIVING INTERFACE"
 */

const JARVIS = {
    sessionId: null,
    voiceMode: false,
    messageCount: 0,
    startTime: Date.now(),

    // ============================================
    // INITIALIZATION
    // ============================================

    init() {
        this.chat.init();
        this.voice.init();
        this.keyboard.init();
        this.command.init();
        this.intel.init();
        
        // v5.0.0 — Initialize OS and Agent modules
        if (this.os) this.os.init();
        if (this.agents) this.agents.init();
    },

    // ============================================
    // WORKSPACE MANAGEMENT
    // ============================================

    workspace: {
        current: 'chat',

        switch(id) {
            if (this.current === id) return;

            // Deactivate current
            const currentView = document.getElementById(`view-${this.current}`);
            if (currentView) currentView.classList.remove('active');

            // Deactivate nav
            const currentNav = document.querySelector(`.nav-item[data-workspace="${this.current}"]`);
            if (currentNav) currentNav.classList.remove('active');

            // Activate new
            this.current = id;
            const newView = document.getElementById(`view-${id}`);
            if (newView) {
                newView.classList.add('active');
                newView.style.animation = 'none';
                newView.offsetHeight; // trigger reflow
                newView.style.animation = '';
            }

            const newNav = document.querySelector(`.nav-item[data-workspace="${id}"]`);
            if (newNav) newNav.classList.add('active');

            // Update header
            // (handled by each view's own header)

            // Update sphere state based on workspace
            if (window.jarvisState) {
                if (id === 'chat') {
                    window.jarvisState.set('idle');
                }
            }
        },

        openSub(workspace, sub) {
            // Future: open sub-workspace views
            console.log(`Opening ${sub} in ${workspace}`);
        }
    },

    // ============================================
    // CHAT SYSTEM
    // ============================================

    chat: {
        init() {
            const input = document.getElementById('chat-input');
            if (input) {
                input.addEventListener('input', () => {
                    input.style.height = 'auto';
                    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
                });
            }
        },

        send() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            if (!message) return;

            this.appendMessage('user', message);
            input.value = '';
            input.style.height = 'auto';

            // Update state
            if (window.jarvisState) window.jarvisState.startThinking();
            this.showTyping();

            JARVIS.intel.addThinking('JARVIS', 'Processing request...');

            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message,
                    session_id: JARVIS.sessionId,
                }),
            })
            .then(r => r.json())
            .then(data => {
                this.removeTyping();
                JARVIS.sessionId = data.session_id;
                this.appendMessage('assistant', data.response);
                JARVIS.messageCount++;

                if (data.audio_url) {
                    if (window.jarvisState) window.jarvisState.startSpeaking();
                    this.playAudio(data.audio_url);
                } else {
                    if (window.jarvisState) window.jarvisState.set('idle');
                }

                JARVIS.intel.addThinking('JARVIS', 'Response delivered');
                JARVIS.intel.incrementApiCalls();
            })
            .catch(err => {
                this.removeTyping();
                this.appendMessage('assistant', `Error: ${err.message}`);
                if (window.jarvisState) window.jarvisState.set('idle');
                JARVIS.intel.addThinking('System', `Error: ${err.message}`);
            });
        },

        appendMessage(role, content) {
            const container = document.getElementById('chat-messages');
            const div = document.createElement('div');
            div.className = `chat-message ${role}`;

            const prefix = role === 'assistant'
                ? `<div style="margin-bottom:var(--space-2); color:var(--gold); font-size:var(--text-xs); letter-spacing:var(--tracking-widest); text-transform:uppercase;">JARVIS</div>`
                : '';

            div.innerHTML = prefix + this.renderMarkdown(content);
            container.appendChild(div);
            container.scrollTop = container.scrollHeight;

            JARVIS.messageCount++;
            const countEl = document.getElementById('message-count');
            if (countEl) countEl.textContent = JARVIS.messageCount;
        },

        renderMarkdown(text) {
            return text
                .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="lang-$1">$2</code></pre>')
                .replace(/`([^`]+)`/g, '<code>$1</code>')
                .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                .replace(/\n/g, '<br>');
        },

        showTyping() {
            const container = document.getElementById('chat-messages');
            const div = document.createElement('div');
            div.id = 'typing-indicator';
            div.className = 'typing-indicator';
            div.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
            container.appendChild(div);
            container.scrollTop = container.scrollHeight;
        },

        removeTyping() {
            const el = document.getElementById('typing-indicator');
            if (el) el.remove();
        },

        playAudio(url) {
            const audio = new Audio(url);
            if (window.audioAnalyzer && window.audioAnalyzer.audioContext) {
                try { window.audioAnalyzer.connectAudioElement(audio); } catch (e) {}
            }

            const updateViz = () => {
                if (window.audioAnalyzer && window.audioAnalyzer.isActive) {
                    const v = window.audioAnalyzer.getValues();
                    if (window.jarvisCore) window.jarvisCore.setAudio(v.volume, v.frequency, v.pitch);
                }
                if (!audio.paused) requestAnimationFrame(updateViz);
            };

            audio.addEventListener('play', updateViz);
            audio.addEventListener('ended', () => {
                if (window.jarvisState) window.jarvisState.stopSpeaking();
                if (window.jarvisCore) window.jarvisCore.setAudio(0, 0, 0);
            });
            audio.play().catch(() => {});
        }
    },

    // ============================================
    // VOICE SYSTEM
    // ============================================

    voice: {
        recognition: null,
        active: false,

        init() {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) return;

            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';

            this.recognition.onresult = (event) => {
                const transcript = Array.from(event.results)
                    .map(r => r[0].transcript)
                    .join('');

                const input = document.getElementById('chat-input');
                if (input) input.value = transcript;

                const voiceTranscript = document.getElementById('voice-transcript');
                if (voiceTranscript) voiceTranscript.textContent = transcript;
            };

            this.recognition.onend = () => {
                this.active = false;
                this.updateButton();
                const input = document.getElementById('chat-input');
                if (input && input.value.trim()) {
                    JARVIS.chat.send();
                }
                if (window.jarvisState) window.jarvisState.stopListening();
                const voiceTranscript = document.getElementById('voice-transcript');
                if (voiceTranscript) voiceTranscript.textContent = '';
            };
        },

        toggle() {
            if (!this.recognition) return;
            if (this.active) {
                this.recognition.stop();
            } else {
                this.recognition.start();
                this.active = true;
                this.updateButton();
                if (window.jarvisState) window.jarvisState.startListening();
            }
        },

        updateButton() {
            const btns = document.querySelectorAll('#chat-mic-btn, #dock-voice-btn');
            btns.forEach(btn => btn.classList.toggle('active', this.active));
        }
    },

    // ============================================
    // VOICE MODE (Full-screen cinematic)
    // ============================================

    toggleVoiceMode() {
        this.voiceMode = !this.voiceMode;
        const overlay = document.getElementById('voice-overlay');
        const app = document.getElementById('app');
        const btn = document.getElementById('voice-mode-btn');

        if (this.voiceMode) {
            overlay.classList.add('active');
            app.classList.add('voice-mode');
            btn.classList.add('active');
            if (window.jarvisCore) window.jarvisCore.setMode('voice');
        } else {
            overlay.classList.remove('active');
            app.classList.remove('voice-mode');
            btn.classList.remove('active');
            if (window.jarvisCore) window.jarvisCore.setMode('workspace');
        }
    },

    // ============================================
    // INTELLIGENCE PANEL
    // ============================================

    intel: {
        thinkingLines: [],
        maxLines: 50,
        apiCalls: 0,
        totalTokens: 0,

        init() {
            // Connect to WebSocket for live updates (when backend supports it)
            this.connectWebSocket();
        },

        connectWebSocket() {
            try {
                const ws = new WebSocket(`ws://${window.location.host}/ws/intel`);
                ws.onmessage = (e) => {
                    try {
                        const data = JSON.parse(e.data);
                        this.handleUpdate(data);
                    } catch (err) {}
                };
                ws.onclose = () => {
                    // Retry in 5s
                    setTimeout(() => this.connectWebSocket(), 5000);
                };
            } catch (e) {
                // WebSocket not available yet, use polling
                this.startPolling();
            }
        },

        startPolling() {
            setInterval(() => this.fetchUpdates(), 3000);
        },

        fetchUpdates() {
            fetch('/api/intel')
                .then(r => r.json())
                .then(data => this.handleUpdate(data))
                .catch(() => {});
        },

        handleUpdate(data) {
            if (data.status) {
                const el = document.getElementById('intel-status');
                if (el) { el.textContent = data.status; }
            }
            if (data.mission) {
                this.updateMission(data.mission);
            }
            if (data.thinking) {
                this.addThinking(data.thinking.agent, data.thinking.message);
            }
            if (data.agents) {
                this.updateAgents(data.agents);
            }
            if (data.cost !== undefined) {
                this.updateCost(data.cost);
            }
        },

        addThinking(agent, message) {
            const stream = document.getElementById('thinking-stream');
            if (!stream) return;

            // Clear placeholder
            if (this.thinkingLines.length === 0) {
                stream.innerHTML = '';
            }

            const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
            const line = document.createElement('div');
            line.className = 'thinking-line';
            line.innerHTML = `<span style="color:var(--text-tertiary); font-size:10px;">${time}</span> <span class="agent-name">${agent}</span> <span class="action">${message}</span>`;
            stream.appendChild(line);

            this.thinkingLines.push(line);
            if (this.thinkingLines.length > this.maxLines) {
                const old = this.thinkingLines.shift();
                if (old.parentNode) old.parentNode.removeChild(old);
            }

            stream.scrollTop = stream.scrollHeight;
        },

        updateMission(mission) {
            const section = document.getElementById('intel-mission-section');
            if (section) section.style.display = 'block';

            const title = document.getElementById('intel-mission-title');
            const progress = document.getElementById('intel-mission-progress');
            const pct = document.getElementById('intel-mission-pct');
            const eta = document.getElementById('intel-mission-eta');

            if (title) title.textContent = mission.title || '-';
            if (progress) progress.style.width = `${mission.progress || 0}%`;
            if (pct) pct.textContent = `${mission.progress || 0}%`;
            if (eta) eta.textContent = `ETA: ${mission.eta || '--'}`;
        },

        updateAgents(agents) {
            const container = document.getElementById('intel-agents');
            if (!container || !agents.length) return;

            container.innerHTML = agents.map(a => `
                <div class="intel-card" style="padding:var(--space-2) var(--space-3); margin-bottom:var(--space-1);">
                    <div style="display:flex; align-items:center; gap:var(--space-2);">
                        <div style="width:6px; height:6px; border-radius:50%; background:${a.active ? 'var(--gold)' : 'var(--text-tertiary)'}; ${a.active ? 'animation:pulse-dot 1.5s ease-in-out infinite;' : ''}"></div>
                        <span style="font-size:var(--text-xs); color:var(--text-primary);">${a.name}</span>
                        <span style="font-size:10px; color:var(--text-tertiary); margin-left:auto;">${a.role || ''}</span>
                    </div>
                    ${a.task ? `<div style="font-size:10px; color:var(--text-tertiary); margin-top:2px; padding-left:14px;">${a.task}</div>` : ''}
                </div>
            `).join('');
        },

        incrementApiCalls() {
            this.apiCalls++;
            const el = document.getElementById('intel-api-calls');
            if (el) el.textContent = this.apiCalls;
        },

        updateCost(cost) {
            const el = document.getElementById('intel-cost');
            if (el) el.textContent = `$${cost.toFixed(4)}`;
            const dockEl = document.getElementById('dock-cost');
            if (dockEl) dockEl.textContent = `$${cost.toFixed(4)}`;
        }
    },

    // ============================================
    // MISSIONS
    // ============================================

    missions: {
        active: [],

        createNew() {
            // Switch to chat and prompt
            JARVIS.workspace.switch('chat');
            JARVIS.chat.appendMessage('assistant', 'What would you like me to work on? Describe your mission.');
        }
    },

    // ============================================
    // COMMAND PALETTE
    // ============================================

    command: {
        commands: [
            { label: 'Switch to Chat', action: () => JARVIS.workspace.switch('chat'), shortcut: '1', icon: 'chat' },
            { label: 'Switch to Work', action: () => JARVIS.workspace.switch('work'), shortcut: '2', icon: 'work' },
            { label: 'Switch to Think', action: () => JARVIS.workspace.switch('think'), shortcut: '3', icon: 'think' },
            { label: 'Switch to Build', action: () => JARVIS.workspace.switch('build'), shortcut: '4', icon: 'build' },
            { label: 'Switch to Control', action: () => JARVIS.workspace.switch('control'), shortcut: '5', icon: 'control' },
            { label: 'Switch to Observe', action: () => JARVIS.workspace.switch('observe'), shortcut: '6', icon: 'observe' },
            { label: 'Missions', action: () => JARVIS.workspace.switch('missions'), shortcut: '7', icon: 'missions' },
            { label: 'Settings', action: () => JARVIS.workspace.switch('settings'), shortcut: '8', icon: 'settings' },
            { label: 'Toggle Voice Mode', action: () => JARVIS.toggleVoiceMode(), shortcut: 'V', icon: 'voice' },
            { label: 'Toggle Voice Input', action: () => JARVIS.voice.toggle(), shortcut: 'M', icon: 'mic' },
        ],

        open() {
            const overlay = document.getElementById('command-palette');
            const input = document.getElementById('palette-input');
            overlay.classList.add('open');
            input.value = '';
            input.focus();
            this.filter('');
        },

        close() {
            const overlay = document.getElementById('command-palette');
            overlay.classList.remove('open');
        },

        filter(query) {
            const container = document.getElementById('palette-results');
            const filtered = query
                ? this.commands.filter(c => c.label.toLowerCase().includes(query.toLowerCase()))
                : this.commands;

            container.innerHTML = filtered.map((c, i) => `
                <div class="command-palette-item ${i === 0 ? 'selected' : ''}" onclick="JARVIS.command.executeCommand(${this.commands.indexOf(c)})">
                    <span class="item-label">${c.label}</span>
                    <span class="item-shortcut">${c.shortcut}</span>
                </div>
            `).join('');
        },

        execute(query) {
            const match = this.commands.find(c => c.label.toLowerCase().includes(query.toLowerCase()));
            if (match) {
                match.action();
                this.close();
            }
        },

        executeCommand(index) {
            this.commands[index].action();
            this.close();
        }
    },

    // ============================================
    // KEYBOARD SHORTCUTS
    // ============================================

    keyboard: {
        init() {
            document.addEventListener('keydown', (e) => {
                // Cmd+K / Ctrl+K - Command Palette
                if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                    e.preventDefault();
                    JARVIS.command.open();
                }

                // Escape - Close overlays
                if (e.key === 'Escape') {
                    JARVIS.command.close();
                    if (JARVIS.voiceMode) JARVIS.toggleVoiceMode();
                }

                // Number keys 1-8 for workspace switching (when not in input)
                if (!e.metaKey && !e.ctrlKey && !e.altKey) {
                    const target = e.target;
                    const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA';
                    if (!isInput) {
                        const workspaces = ['chat', 'work', 'think', 'build', 'control', 'observe', 'missions', 'settings'];
                        const num = parseInt(e.key);
                        if (num >= 1 && num <= 8) {
                            JARVIS.workspace.switch(workspaces[num - 1]);
                        }
                    }
                }
            });
        }
    },

    // ============================================
    // PANEL TOGGLE
    // ============================================

    togglePanel() {
        const app = document.getElementById('app');
        app.classList.toggle('panel-collapsed');
    }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    JARVIS.init();
});
