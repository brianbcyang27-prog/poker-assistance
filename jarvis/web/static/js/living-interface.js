/**
 * Neural Thought Stream — v3.2.0
 *
 * Live reasoning timeline that shows JARVIS thinking in real time.
 * Receives events from the Event Bus via WebSocket and displays
 * them as a flowing reasoning chain.
 *
 * Replaces the old static thought bubble system.
 */

class LivingInterface {
    constructor() {
        this.thoughtStream = document.getElementById('thought-stream');
        this.responseDisplay = document.getElementById('response-display');
        this.missionState = document.getElementById('mission-state');
        this.coreStateEl = document.getElementById('core-state');
        this.coreLabelEl = document.getElementById('core-label');

        this.responseTimeout = null;
        this.currentResponse = null;
        this.missionPollId = null;

        // Thought stream state
        this._thoughts = [];
        this._maxThoughts = 12;
        this._ws = null;
        this._eventQueue = [];
        this._processingEvents = false;

        // State-specific thought templates (fallback when no real events)
        this._fallbackThoughts = {
            idle: ['Systems nominal', 'Neural networks at rest', 'All agents standing by'],
            listening: ['Audio stream active', 'Processing speech input'],
            thinking: ['Analyzing intent', 'Decomposing request', 'Consulting knowledge base'],
            working: ['Delegating to agents', 'Coordinating workers', 'Monitoring progress'],
            speaking: ['Composing response', 'Generating output'],
            retrieving: ['Searching memory stores', 'Retrieving related context', 'Loading knowledge graph'],
            planning: ['Building execution plan', 'Analyzing dependencies', 'Optimizing task order'],
            delegating: ['Assigning workers', 'Distributing tasks', 'Activating specialist agents'],
            reviewing: ['Evaluating results', 'Checking quality', 'Verifying completeness'],
            complete: ['Mission accomplished', 'Results compiled', 'Returning response'],
        };

        this._boundPollMissions = this._pollMissions.bind(this);
    }

    /* ---- STATE ---- */

    setState(state) {
        if (this.coreStateEl) {
            this.coreStateEl.textContent = state.toUpperCase();
            this.coreStateEl.classList.toggle('active', state !== 'idle');
        }

        // Update core label with state-specific messaging
        if (this.coreLabelEl) {
            const labels = {
                idle: 'JARVIS',
                thinking: 'ANALYZING',
                listening: 'LISTENING',
                speaking: 'SPEAKING',
                working: 'EXECUTING',
                retrieving: 'RETRIEVING',
                planning: 'PLANNING',
                delegating: 'DELEGATING',
                reviewing: 'REVIEWING',
                complete: 'COMPLETE',
            };
            this.coreLabelEl.textContent = labels[state] || 'JARVIS';
        }

        // Start/stop fallback thoughts based on state
        if (state === 'thinking' || state === 'working' || state === 'listening'
            || state === 'retrieving' || state === 'planning' || state === 'delegating'
            || state === 'reviewing') {
            this._startFallbackThoughts(state);
        } else if (state === 'idle' || state === 'complete') {
            this._stopFallbackThoughts();
            if (state === 'complete') {
                this._emitThought({ icon: '\u2714', text: 'Mission complete', type: 'complete' });
            }
        }
    }

    /* ---- WEBSOCKET EVENTS ---- */

    connectEvents(wsUrl) {
        if (this._ws) return;
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = wsUrl || `${protocol}//${location.host}/ws/agents`;

        try {
            this._ws = new WebSocket(url);
            this._ws.onmessage = (e) => this._handleWSMessage(e);
            this._ws.onclose = () => { this._ws = null; setTimeout(() => this.connectEvents(wsUrl), 3000); };
            this._ws.onerror = () => {};
        } catch (_) {}
    }

    _handleWSMessage(event) {
        try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'event') {
                this._processEvent(msg.data);
            } else if (msg.type === 'status') {
                this._updateAgentStatus(msg.data);
            } else if (msg.type === 'visual_state') {
                // v3.2.0: Wire Event Bus → Three.js core
                if (window.jarvisState) {
                    window.jarvisState.setState(msg.state);
                }
                if (window.graph3d) {
                    window.graph3d.setState(msg.state);
                }
            }
        } catch (_) {}
    }

    _processEvent(data) {
        const eventMap = {
            'jarvis.thinking': { icon: '\U0001f9e0', text: 'Analyzing your request', type: 'process' },
            'jarvis.delegated': { icon: '\u2b07', text: `Delegating to ${data.payload?.intent || 'specialist'}`, type: 'delegate' },
            'jarvis.responded': { icon: '\u2714', text: 'Preparing response', type: 'complete' },
            'king.planning': { icon: '\U0001f4cb', text: `Planning: ${data.payload?.task || 'strategy'}`, type: 'plan' },
            'king.delegated': { icon: '\U0001f464', text: `Assigned ${data.payload?.workers || 'workers'}`, type: 'delegate' },
            'king.completed': { icon: '\U0001f44d', text: `Review: ${data.payload?.task || 'results'}`, type: 'review' },
            'worker.started': { icon: '\u25b6', text: `${data.source} started`, type: 'work' },
            'worker.completed': { icon: '\u2714', text: `${data.source} done (conf: ${data.payload?.confidence || '?'})`, type: 'work' },
            'worker.error': { icon: '\u274c', text: `${data.source} error`, type: 'error' },
        };

        const mapped = eventMap[data.event_type];
        if (mapped) {
            this._emitThought(mapped);
        }

        // Auto-map event type to visual state
        const stateMap = {
            'jarvis.thinking': 'thinking',
            'jarvis.delegated': 'delegating',
            'jarvis.responded': 'speaking',
            'king.planning': 'planning',
            'king.delegated': 'delegating',
            'king.completed': 'reviewing',
            'worker.started': 'working',
            'worker.completed': 'working',
            'worker.error': 'working',
        };
        const newState = stateMap[data.event_type];
        if (newState && window.jarvisState) {
            window.jarvisState.setState(newState);
        }
    }

    _updateAgentStatus(data) {
        // Update agent activity indicator
        if (data.kings) {
            let activeCount = 0;
            for (const [_, king] of Object.entries(data.kings)) {
                if (king.state !== 'idle') activeCount++;
                if (king.workers) {
                    for (const [__, worker] of Object.entries(king.workers)) {
                        if (worker.state !== 'idle') activeCount++;
                    }
                }
            }
            // Could update a live agent count display here
        }
    }

    /* ---- THOUGHT STREAM ---- */

    _startFallbackThoughts(state) {
        this._stopFallbackThoughts();
        const pool = this._fallbackThoughts[state] || this._fallbackThoughts.idle;
        let idx = 0;

        const emit = () => {
            this._emitThought({
                icon: '\u2022',
                text: pool[idx % pool.length],
                type: 'process',
            });
            idx++;
        };

        emit();
        this._fallbackInterval = setInterval(emit, 3000 + Math.random() * 1000);
    }

    _stopFallbackThoughts() {
        if (this._fallbackInterval) {
            clearInterval(this._fallbackInterval);
            this._fallbackInterval = null;
        }
    }

    _emitThought(thought) {
        const el = document.createElement('div');
        el.className = `thought thought-${thought.type || 'process'}`;

        const iconSpan = document.createElement('span');
        iconSpan.className = 'thought-icon';
        iconSpan.textContent = thought.icon || '\u2022';

        const textSpan = document.createElement('span');
        textSpan.className = 'thought-text';
        textSpan.textContent = thought.text;

        el.appendChild(iconSpan);
        el.appendChild(textSpan);

        // Position around the core
        const cx = window.innerWidth / 2;
        const cy = window.innerHeight / 2;
        const angle = Math.random() * Math.PI * 2;
        const radius = 100 + Math.random() * 120;

        el.style.left = `${cx + Math.cos(angle) * radius}px`;
        el.style.top = `${cy + Math.sin(angle) * radius}px`;
        el.style.setProperty('--drift-x', `${(Math.random() - 0.5) * 40}px`);

        this.thoughtStream.appendChild(el);
        this._thoughts.push(el);

        // Trim old thoughts
        while (this._thoughts.length > this._maxThoughts) {
            const old = this._thoughts.shift();
            if (old && old.parentNode) old.remove();
        }

        // Auto-remove after animation
        setTimeout(() => {
            if (el.parentNode) el.remove();
            const idx = this._thoughts.indexOf(el);
            if (idx >= 0) this._thoughts.splice(idx, 1);
        }, 6200);
    }

    /* ---- RESPONSE ---- */

    showResponse(text, audioUrl) {
        this._clearResponse();

        const bubble = document.createElement('div');
        bubble.className = 'response-bubble';

        // Add reasoning details if available
        const reasoningHtml = this._buildReasoningDetails();
        bubble.innerHTML = `
            <div class="response-text">${this._md(text)}</div>
            ${reasoningHtml}
        `;

        this.responseDisplay.appendChild(bubble);
        this.currentResponse = bubble;

        this.responseTimeout = setTimeout(() => this._fadeResponse(), 15000);

        if (audioUrl) this._playAudio(audioUrl);
    }

    _buildReasoningDetails() {
        // Show last few thoughts as reasoning trail
        const recent = this._thoughts.slice(-4);
        if (recent.length === 0) return '';

        const items = recent.map(el => {
            const icon = el.querySelector('.thought-icon')?.textContent || '';
            const text = el.querySelector('.thought-text')?.textContent || '';
            return `<span class="reasoning-step">${icon} ${text}</span>`;
        }).join('');

        return `<div class="reasoning-trail">${items}</div>`;
    }

    _fadeResponse() {
        if (this.currentResponse) {
            this.currentResponse.classList.add('fading');
            setTimeout(() => this._clearResponse(), 600);
        }
    }

    _clearResponse() {
        if (this.responseTimeout) { clearTimeout(this.responseTimeout); this.responseTimeout = null; }
        if (this.currentResponse) { this.currentResponse.remove(); this.currentResponse = null; }
    }

    _playAudio(url) {
        const audio = new Audio(url);
        audio.addEventListener('ended', () => {
            if (window.jarvisState) window.jarvisState.stopSpeaking();
            this.setState('idle');
        });
        audio.play().catch(() => {});
    }

    /* ---- MISSIONS ---- */

    startMissionPolling() {
        this._pollMissions();
        this.missionPollId = setInterval(this._boundPollMissions, 5000);
    }

    async _pollMissions() {
        try {
            const res = await fetch('/api/workspace');
            const workspaces = await res.json();
            const active = workspaces.find(w => w.status !== 'completed' && w.status !== 'failed');
            if (active) {
                this._showMission({
                    goal: active.goal,
                    progress: active.progress || 0,
                    agents: (active.tasks || []).length,
                });
            } else {
                this._hideMission();
            }
        } catch (_) {}
    }

    _showMission(m) {
        this.missionState.innerHTML = `
            <div class="mission-label">Active Mission</div>
            <div class="mission-bar"><div class="mission-fill" style="width:${m.progress}%"></div></div>
            <div class="mission-detail">${this._esc(m.goal)} \u00b7 ${m.agents} agents</div>
        `;
        this.missionState.classList.add('visible');
    }

    _hideMission() {
        this.missionState.classList.remove('visible');
    }

    /* ---- HELPERS ---- */

    _md(text) {
        return text
            .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }

    _esc(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }
}

window.LivingInterface = LivingInterface;
