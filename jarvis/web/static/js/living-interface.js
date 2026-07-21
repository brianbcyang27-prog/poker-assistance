/* JARVIS Living Interface v6.4.0 — Real-time Intelligence Display */

class LivingInterface {
    constructor() {
        this.thoughtStream = document.getElementById('thought-stream');
        this.responseDisplay = document.getElementById('response-display');
        this.missionState = document.getElementById('mission-state');
        this.coreState = document.getElementById('core-state');
        this.coreLabel = document.getElementById('core-label');

        this._thoughts = [];
        this._maxThoughts = 15;
        this._ws = null;
        this._reconnectTimer = null;
        this._fallbackInterval = null;
        this._agentConversations = [];
        this._maxConversations = 20;

        this._stateThoughts = {
            idle: [
                { icon: '◉', text: 'Systems nominal' },
                { icon: '◎', text: 'Monitoring environment' },
                { icon: '◇', text: 'Memory consolidation active' },
                { icon: '○', text: 'Awaiting instructions' },
            ],
            listening: [
                { icon: '◉', text: 'Audio input active' },
                { icon: '◎', text: 'Processing speech' },
                { icon: '◇', text: 'Voice recognized' },
            ],
            thinking: [
                { icon: '◉', text: 'Analyzing intent...' },
                { icon: '◎', text: 'Searching memories...' },
                { icon: '◇', text: 'Reviewing context...' },
                { icon: '◈', text: 'Building understanding...' },
                { icon: '◆', text: 'Processing request...' },
            ],
            planning: [
                { icon: '◉', text: 'Decomposing task...' },
                { icon: '◎', text: 'Creating mission plan...' },
                { icon: '◇', text: 'Assigning workers...' },
                { icon: '◈', text: 'Building DAG...' },
            ],
            delegating: [
                { icon: '◉', text: 'Dispatching to kings...' },
                { icon: '◎', text: 'Forming team...' },
                { icon: '◇', text: 'Activating workers...' },
            ],
            working: [
                { icon: '◉', text: 'Executing tasks...' },
                { icon: '◎', text: 'Workers collaborating...' },
                { icon: '◇', text: 'Processing data...' },
                { icon: '◈', text: 'Building solution...' },
            ],
            reviewing: [
                { icon: '◉', text: 'Quality review...' },
                { icon: '◎', text: 'Checking results...' },
                { icon: '◇', text: 'Validating output...' },
            ],
            retrieving: [
                { icon: '◉', text: 'Querying knowledge graph...' },
                { icon: '◎', text: 'Searching documents...' },
                { icon: '◇', text: 'Retrieving memories...' },
            ],
            speaking: [
                { icon: '◉', text: 'Generating response...' },
                { icon: '◎', text: 'Synthesizing answer...' },
            ],
            complete: [
                { icon: '✓', text: 'Mission complete' },
                { icon: '◉', text: 'Results delivered' },
            ],
            error: [
                { icon: '✗', text: 'Error detected' },
                { icon: '⚠', text: 'Attempting recovery...' },
            ],
            mission_active: [
                { icon: '◉', text: 'Mission in progress...' },
                { icon: '◎', text: 'Workers active...' },
            ],
        };
    }

    setState(state) {
        if (this.coreState) {
            this.coreState.textContent = state.toUpperCase().replace('_', ' ');
        }
        if (this.coreLabel) {
            this.coreLabel.classList.toggle('active', state !== 'idle');
        }

        if (this._fallbackInterval) {
            clearInterval(this._fallbackInterval);
            this._fallbackInterval = null;
        }

        if (state !== 'idle') {
            this._startFallbackThoughts(state);
        }
    }

    connectEvents(wsUrl) {
        if (this._ws && this._ws.readyState === WebSocket.OPEN) return;

        const url = wsUrl || `ws://${location.host}/ws/agents`;
        this._ws = new WebSocket(url);

        this._ws.onopen = () => {
            console.log('[JARVIS] WebSocket connected');
            if (this._reconnectTimer) {
                clearTimeout(this._reconnectTimer);
                this._reconnectTimer = null;
            }
        };

        this._ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this._handleWSMessage(data);
            } catch (e) {
                console.error('[JARVIS] WS parse error:', e);
            }
        };

        this._ws.onclose = () => {
            console.log('[JARVIS] WebSocket closed, reconnecting in 3s...');
            this._reconnectTimer = setTimeout(() => this.connectEvents(wsUrl), 3000);
        };

        this._ws.onerror = (err) => {
            console.error('[JARVIS] WebSocket error:', err);
        };
    }

    _handleWSMessage(data) {
        switch (data.type) {
            case 'event':
                this._processEvent(data.data);
                break;
            case 'status':
                this._updateAgentStatus(data.data);
                break;
            case 'visual_state':
                if (window.jarvisState) {
                    window.jarvisState.set(data.state);
                }
                break;
            case 'agent_conversation':
                this._addAgentConversation(data.data);
                break;
            case 'mission_progress':
                this._updateMissionProgress(data.data);
                break;
        }
    }

    _processEvent(data) {
        const { event_type, source, payload, label, icon } = data;

        const thought = {
            icon: icon || '◉',
            text: label || event_type,
            source: source,
            type: event_type,
        };

        this._emitThought(thought);

        const stateMap = {
            'jarvis.thinking': 'thinking',
            'jarvis.delegated': 'delegating',
            'jarvis.responded': 'speaking',
            'king.planning': 'planning',
            'king.delegated': 'delegating',
            'king.completed': 'reviewing',
            'worker.started': 'working',
            'worker.completed': 'working',
            'worker.error': 'error',
        };

        if (stateMap[event_type] && window.jarvisState) {
            window.jarvisState.set(stateMap[event_type]);
        }
    }

    _updateAgentStatus(data) {
        if (!data || !data.kings) return;
        window._agentStatusData = data;
    }

    _startFallbackThoughts(state) {
        const thoughts = this._stateThoughts[state] || this._stateThoughts.idle;
        let idx = 0;

        this._fallbackInterval = setInterval(() => {
            if (idx < thoughts.length) {
                this._emitThought(thoughts[idx]);
                idx++;
            } else {
                idx = 0;
            }
        }, 3500);
    }

    _stopFallbackThoughts() {
        if (this._fallbackInterval) {
            clearInterval(this._fallbackInterval);
            this._fallbackInterval = null;
        }
    }

    _emitThought(thought) {
        if (!this.thoughtStream) return;

        const el = document.createElement('div');
        el.className = 'thought';

        const iconSpan = document.createElement('span');
        iconSpan.className = 'thought-icon';
        iconSpan.textContent = thought.icon || '◉';

        const textSpan = document.createElement('span');
        textSpan.className = 'thought-text';
        textSpan.textContent = thought.text || '';

        if (thought.source) {
            const sourceSpan = document.createElement('span');
            sourceSpan.className = 'thought-source';
            sourceSpan.textContent = thought.source;
            el.appendChild(iconSpan);
            el.appendChild(textSpan);
            el.appendChild(sourceSpan);
        } else {
            el.appendChild(iconSpan);
            el.appendChild(textSpan);
        }

        const driftX = (Math.random() - 0.5) * 60;
        el.style.setProperty('--drift-x', `${driftX}px`);

        this.thoughtStream.appendChild(el);
        this._thoughts.push(el);

        requestAnimationFrame(() => el.classList.add('visible'));

        setTimeout(() => {
            el.classList.add('fading');
            setTimeout(() => {
                el.remove();
                this._thoughts = this._thoughts.filter(t => t !== el);
            }, 800);
        }, 5800);

        while (this._thoughts.length > this._maxThoughts) {
            const old = this._thoughts.shift();
            old.remove();
        }
    }

    _addAgentConversation(data) {
        const { sender, receiver, content, card_id, title } = data;

        this._agentConversations.push({
            sender, receiver, content, card_id, title,
            timestamp: Date.now()
        });

        if (this._agentConversations.length > this._maxConversations) {
            this._agentConversations.shift();
        }

        const stream = document.getElementById('agent-conversation-stream');
        if (!stream) return;

        const el = document.createElement('div');
        el.className = 'agent-msg';

        const header = document.createElement('div');
        header.className = 'agent-msg-header';
        header.innerHTML = `<span class="agent-card">${card_id || '?'}</span> <span class="agent-name">${title || sender}</span>`;
        if (receiver) {
            header.innerHTML += ` → <span class="agent-recv">${receiver}</span>`;
        }

        const body = document.createElement('div');
        body.className = 'agent-msg-body';
        body.textContent = content;

        el.appendChild(header);
        el.appendChild(body);
        stream.appendChild(el);

        stream.scrollTop = stream.scrollHeight;

        requestAnimationFrame(() => el.classList.add('visible'));

        while (stream.children.length > 20) {
            stream.removeChild(stream.firstChild);
        }
    }

    _updateMissionProgress(data) {
        if (!this.missionState) return;

        const { goal, progress, agents_active, status } = data;

        this.missionState.classList.remove('hidden');
        this.missionState.innerHTML = `
            <div class="mission-label">MISSION ACTIVE</div>
            <div class="mission-progress-bar">
                <div class="mission-progress-fill" style="width: ${(progress || 0) * 100}%"></div>
            </div>
            <div class="mission-detail">${goal || 'Processing...'}</div>
            <div class="mission-agents">${agents_active || 0} agents active</div>
        `;
    }

    showResponse(text, audioUrl) {
        if (!this.responseDisplay) return;

        let bubble = this.responseDisplay.querySelector('.response-bubble');
        if (!bubble) {
            bubble = document.createElement('div');
            bubble.className = 'response-bubble';

            const content = document.createElement('div');
            content.className = 'response-text';
            bubble.appendChild(content);

            const reasoning = this._buildReasoningDetails();
            if (reasoning) {
                const details = document.createElement('div');
                details.className = 'response-reasoning';
                bubble.appendChild(details);
            }

            this.responseDisplay.innerHTML = '';
            this.responseDisplay.appendChild(bubble);
            this.responseDisplay.classList.remove('hidden');
            requestAnimationFrame(() => bubble.classList.add('visible'));
        }

        const contentEl = bubble.querySelector('.response-text');
        if (contentEl) contentEl.innerHTML = (typeof _md === 'function' ? _md : (t => t))(text || '');

        const reasoning = this._buildReasoningDetails();
        let detailsEl = bubble.querySelector('.response-reasoning');
        if (reasoning) {
            if (!detailsEl) {
                detailsEl = document.createElement('div');
                detailsEl.className = 'response-reasoning';
                bubble.appendChild(detailsEl);
            }
            detailsEl.innerHTML = reasoning;
        }

        if (this._responseTimer) clearTimeout(this._responseTimer);
        this._responseTimer = setTimeout(() => this._fadeResponse(), 20000);

        if (audioUrl) this._playAudio(audioUrl);
    }

    _buildReasoningDetails() {
        const recent = this._thoughts.slice(-4);
        if (recent.length === 0) return '';

        const items = recent.map(t => {
            const text = t.querySelector('.thought-text')?.textContent || '';
            return `<li>${text}</li>`;
        }).join('');

        return `<div class="reasoning-label">Reasoning trail:</div><ul>${items}</ul>`;
    }

    _fadeResponse() {
        if (this.responseDisplay) {
            const bubble = this.responseDisplay.querySelector('.response-bubble');
            if (bubble) {
                bubble.classList.add('fading');
                setTimeout(() => {
                    this.responseDisplay.classList.add('hidden');
                    this.responseDisplay.innerHTML = '';
                }, 600);
            }
        }
    }

    _playAudio(url) {
        try {
            const audio = new Audio(url);
            audio.onended = () => {
                if (window.jarvisState) window.jarvisState.stopSpeaking();
            };
            audio.play().catch(() => {});
        } catch (e) {}
    }

    startMissionPolling() {
        this._pollMissions();
        this._missionPollInterval = setInterval(() => this._pollMissions(), 5000);
    }

    stopMissionPolling() {
        if (this._missionPollInterval) {
            clearInterval(this._missionPollInterval);
            this._missionPollInterval = null;
        }
    }

    async _pollMissions() {
        try {
            const res = await fetch('/api/workspace');
            if (!res.ok) return;
            const data = await res.json();
            const workspaces = data.workspaces || [];
            const active = workspaces.find(w => w.status === 'working');
            if (active) {
                this._showMission(active);
            }
        } catch (e) {}
    }

    _showMission(m) {
        if (!this.missionState) return;
        const progress = m.progress || 0;
        const pct = Math.round(progress * 100);

        this.missionState.classList.remove('hidden');
        this.missionState.innerHTML = `
            <div class="mission-label">MISSION ACTIVE</div>
            <div class="mission-progress-bar">
                <div class="mission-progress-fill" style="width: ${pct}%"></div>
            </div>
            <div class="mission-detail">${m.goal || 'Processing...'}</div>
        `;
    }
}

window.LivingInterface = LivingInterface;
