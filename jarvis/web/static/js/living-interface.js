/**
 * Living Interface
 * Dynamic UI elements that emerge from the neural core.
 * Nothing is static. Everything breathes, drifts, dissolves.
 */

class LivingInterface {
    constructor() {
        this.thoughtStream = document.getElementById('thought-stream');
        this.responseDisplay = document.getElementById('response-display');
        this.missionState = document.getElementById('mission-state');
        this.coreStateEl = document.getElementById('core-state');

        this.thoughtInterval = null;
        this.responseTimeout = null;
        this.currentResponse = null;
        this.missionPollId = null;

        this.thoughts = {
            idle: [
                'Systems nominal',
                'Neural networks at rest',
                'All agents standing by',
                'Awaiting input',
                'Memory banks indexed',
                'Sensors calibrated',
            ],
            listening: [
                'Audio stream active',
                'Processing speech input',
                'Listening...',
            ],
            thinking: [
                'Analyzing intent',
                'Decomposing request',
                'Consulting knowledge base',
                'Planning approach',
                'Evaluating options',
                'Identifying patterns',
                'Mapping to agent capabilities',
                'Synthesizing strategy',
            ],
            working: [
                'Delegating to agents',
                'Coordinating workers',
                'Executing subtasks',
                'Monitoring progress',
                'Reviewing outputs',
                'Aggregating results',
                'Quality checking',
                'Optimizing pipeline',
            ],
            speaking: [
                'Composing response',
                'Generating output',
                'Articulating thoughts',
                'Streaming reply',
            ],
        };

        this._boundPollMissions = this._pollMissions.bind(this);
    }

    /* ---- STATE ---- */

    setState(state) {
        if (this.coreStateEl) {
            this.coreStateEl.textContent = state.toUpperCase();
            this.coreStateEl.classList.toggle('active', state !== 'idle');
        }

        if (state === 'thinking' || state === 'working' || state === 'listening') {
            this._startThoughts(state);
        } else {
            this._stopThoughts();
        }
    }

    /* ---- THOUGHT STREAM ---- */

    _startThoughts(state) {
        this._stopThoughts();
        const pool = this.thoughts[state] || this.thoughts.idle;
        let idx = 0;

        const emit = () => {
            this._emitThought(pool[idx % pool.length]);
            idx++;
        };

        emit();
        this.thoughtInterval = setInterval(emit, 2800 + Math.random() * 800);
    }

    _stopThoughts() {
        if (this.thoughtInterval) {
            clearInterval(this.thoughtInterval);
            this.thoughtInterval = null;
        }
    }

    _emitThought(text) {
        const el = document.createElement('div');
        el.className = 'thought';
        el.textContent = text;

        const cx = window.innerWidth / 2;
        const cy = window.innerHeight / 2;
        const angle = Math.random() * Math.PI * 2;
        const radius = 80 + Math.random() * 100;

        el.style.left = `${cx + Math.cos(angle) * radius}px`;
        el.style.top = `${cy + Math.sin(angle) * radius}px`;
        el.style.setProperty('--drift-x', `${(Math.random() - 0.5) * 50}px`);

        this.thoughtStream.appendChild(el);
        setTimeout(() => el.remove(), 6200);
    }

    /* ---- RESPONSE ---- */

    showResponse(text, audioUrl) {
        this._clearResponse();

        const bubble = document.createElement('div');
        bubble.className = 'response-bubble';
        bubble.innerHTML = `<div class="response-text">${this._md(text)}</div>`;

        this.responseDisplay.appendChild(bubble);
        this.currentResponse = bubble;

        this.responseTimeout = setTimeout(() => this._fadeResponse(), 12000);

        if (audioUrl) this._playAudio(audioUrl);
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
            <div class="mission-detail">${this._esc(m.goal)} &middot; ${m.agents} agents</div>
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
