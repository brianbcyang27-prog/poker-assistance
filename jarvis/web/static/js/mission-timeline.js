/**
 * MissionTimeline — Premium timeline visualization for mission execution.
 * Shows step-by-step execution with tool cards, duration, and status.
 */
class MissionTimeline {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.events = [];
        this.milestones = [];
    }

    setTimeline(events) {
        this.events = events || [];
        this.render();
    }

    setMilestones(milestones) {
        this.milestones = milestones || [];
        this.render();
    }

    addEvent(event) {
        this.events.push(event);
        this.render();
    }

    /**
     * v9.2.0 D4 — Live Activity Stream: append WS events to the timeline
     * incrementally instead of full re-renders. Idempotent per instance.
     */
    subscribe() {
        if (this._subscribed || !window.JarvisWS) return;
        this._subscribed = true;
        this._handler = (msg) => {
            if (!msg || msg.type !== 'event' || !msg.data || !msg.data.event_type) return;
            const entry = this._fromLiveEvent(msg.data);
            if (entry) this._prepend(entry);
        };
        window.JarvisWS.on('event', this._handler);
    }

    unsubscribe() {
        if (this._subscribed && window.JarvisWS && this._handler) {
            window.JarvisWS.off('event', this._handler);
        }
        this._subscribed = false;
        this._handler = null;
    }

    /** Map a WS activity event onto a timeline entry (best-effort). */
    _fromLiveEvent(ev) {
        const type = ev.event_type || '';
        const status = /fail|error/.test(type) ? 'failed'
            : /complete|completed|report|factcheck|done/.test(type) ? 'success'
            : /start|planning|delegated|step/.test(type) ? 'running'
            : 'pending';
        return {
            event_type: type,
            label: ev.label || type,
            icon: ev.icon,
            status: status,
            description: ev.payload && (ev.payload.task || ev.payload.action || ev.payload.summary),
            agent_id: ev.source,
            _live: true,
        };
    }

    /** Insert one live entry without rebuilding the whole track. */
    _prepend(entry) {
        this.events.push(entry);
        if (this.events.length > 100) this.events.shift();
        if (!this.container) return;

        let track = this.container.querySelector('.timeline-track');
        if (!track) {
            this.container.innerHTML = '<div class="timeline-track"></div>';
            track = this.container.querySelector('.timeline-track');
        }
        track.insertAdjacentHTML('beforeend', this._renderEvent(entry, this.events.length - 1));

        while (track.children.length > 100) {
            track.removeChild(track.firstChild);
        }
        this.container.scrollTop = this.container.scrollHeight;
    }

    render() {
        if (!this.container) return;

        if (this.events.length === 0) {
            this.container.innerHTML = `
                <div class="timeline-empty">
                    <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
                        <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                    </svg>
                    <p>No timeline events yet</p>
                </div>
            `;
            return;
        }

        const html = this.events.map((event, i) => this._renderEvent(event, i)).join('');
        this.container.innerHTML = `<div class="timeline-track">${html}</div>`;
    }

    _renderEvent(event, index) {
        const icon = this._getEventIcon(event.event_type);
        const statusClass = event.status || 'pending';
        const duration = event.duration_ms ? this._formatDuration(event.duration_ms) : '';

        return `
            <div class="timeline-item ${statusClass}" style="--delay: ${index * 0.05}s">
                <div class="timeline-marker">
                    <div class="timeline-dot ${statusClass}">${icon}</div>
                    ${index < this.events.length - 1 ? '<div class="timeline-line"></div>' : ''}
                </div>
                <div class="timeline-content">
                    <div class="timeline-header">
                        <span class="timeline-label">${this._escHtml(event.label || event.event_type)}</span>
                        ${duration ? `<span class="timeline-duration">${duration}</span>` : ''}
                    </div>
                    ${event.description ? `<p class="timeline-description">${this._escHtml(event.description)}</p>` : ''}
                    ${event.agent_id ? `<span class="timeline-agent">${this._escHtml(event.agent_id)}</span>` : ''}
                </div>
            </div>
        `;
    }

    _getEventIcon(type) {
        const icons = {
            'mission.start': '▶',
            'mission.complete': '✓',
            'mission.fail': '✗',
            'task.start': '●',
            'task.complete': '✓',
            'task.fail': '✗',
            'tool.call': '⚡',
            'tool.result': '→',
            'milestone': '◆',
            'default': '○'
        };
        return icons[type] || icons['default'];
    }

    _formatDuration(ms) {
        if (ms < 1000) return `${ms}ms`;
        if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
        return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
    }

    _escHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

/**
 * ToolCard — Compact tool execution card for conversations.
 */
class ToolCard {
    static render(tools) {
        if (!tools || tools.length === 0) return '';

        return `
            <div class="tool-cards">
                ${tools.map(tool => ToolCard._renderCard(tool)).join('')}
            </div>
        `;
    }

    static _renderCard(tool) {
        const statusClass = tool.ok ? 'success' : tool.error ? 'failed' : 'pending';
        const icon = ToolCard._getToolIcon(tool.name);
        const duration = tool.duration_ms ? ToolCard._formatDuration(tool.duration_ms) : '';

        return `
            <div class="tool-card ${statusClass}">
                <div class="tool-card-icon">${icon}</div>
                <div class="tool-card-info">
                    <span class="tool-card-name">${ToolCard._escHtml(tool.name)}</span>
                    <span class="tool-card-status">${tool.ok ? 'Done' : tool.error || 'Running...'}</span>
                </div>
                ${duration ? `<span class="tool-card-duration">${duration}</span>` : ''}
            </div>
        `;
    }

    static _getToolIcon(name) {
        const icons = {
            'browser': '🌐',
            'file': '📂',
            'memory': '🧠',
            'terminal': '💻',
            'vision': '👁',
            'search': '🔍',
            'code': '📝',
            'default': '⚡'
        };
        
        const lower = (name || '').toLowerCase();
        for (const [key, icon] of Object.entries(icons)) {
            if (lower.includes(key)) return icon;
        }
        return icons['default'];
    }

    static _formatDuration(ms) {
        if (ms < 1000) return `${ms}ms`;
        if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
        return `${Math.floor(ms / 60000)}m`;
    }

    static _escHtml(str) {
        const div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    }
}

/**
 * ActivityStream — v9.2.0 D4 live activity feed for the right-home panel.
 * Renders WS events (mission/king/worker/review/computer/...) in real time
 * with category-colored dots and relative timestamps. Newest entries append
 * at the bottom, bounded to maxEntries.
 */
class ActivityStream {
    constructor(containerId, opts = {}) {
        this.container = document.getElementById(containerId);
        this.maxEntries = opts.maxEntries || 60;
        this._seen = new Set();
        this._unsubEvent = null;
        this._unsubConv = null;
    }

    subscribe() {
        if (!this.container || !window.JarvisWS) return;
        this._unsubEvent = window.JarvisWS.on('event', (msg) => {
            const ev = msg && msg.data;
            if (!ev || !ev.event_type) return;
            const key = `${ev.event_type}:${ev.timestamp || ''}`;
            if (this._seen.has(key)) return;
            this._seen.add(key);
            if (this._seen.size > 400) this._seen.clear();
            this.addEntry({
                type: ev.event_type,
                label: ev.label || ev.event_type,
                icon: ev.icon || '•',
                source: ev.source,
                time: ev.timestamp ? ev.timestamp * 1000 : Date.now(),
                receiver: '',
            });
        });
        this._unsubConv = window.JarvisWS.on('agent_conversation', (msg) => {
            const data = msg && msg.data;
            if (!data || !data.content) return;
            const key = `conv:${data.card_id || ''}:${data.content.slice(0, 40)}`;
            if (this._seen.has(key)) return;
            this._seen.add(key);
            this.addEntry({
                type: 'agent_conversation',
                label: data.content,
                icon: '◉',
                source: data.title || data.sender || data.card_id || '',
                time: Date.now(),
                receiver: data.receiver || '',
            });
        });
    }

    addEntry(entry) {
        if (!this.container) return;
        const placeholder = this.container.querySelector('.right-empty-text');
        if (placeholder) placeholder.remove();

        const el = document.createElement('div');
        el.className = 'livestream-item';
        el.innerHTML = `
            <span class="livestream-dot ${this._categoryClass(entry.type)}">${this._esc(entry.icon)}</span>
            <div class="livestream-content">
                <div class="livestream-label">${this._esc(entry.label)}</div>
                <div class="livestream-meta">${this._esc(entry.source)}${entry.receiver ? ` → ${this._esc(entry.receiver)}` : ''}</div>
            </div>
            <span class="livestream-time">${this._relTime(entry.time)}</span>
        `;
        this.container.appendChild(el);
        requestAnimationFrame(() => el.classList.add('visible'));

        while (this.container.children.length > this.maxEntries) {
            this.container.removeChild(this.container.firstChild);
        }
    }

    _categoryClass(type) {
        const t = type || '';
        if (/fail|error/.test(t)) return 'failed';
        if (t.startsWith('computer')) return 'computer';
        if (t.startsWith('mission')) return 'mission';
        if (t.startsWith('review')) return 'review';
        if (t.startsWith('king') || t.startsWith('jarvis')) return 'king';
        if (t.startsWith('worker')) return 'worker';
        return 'system';
    }

    _relTime(ts) {
        if (!ts) return '';
        const s = Math.max(0, Math.floor((Date.now() - ts) / 1000));
        if (s < 5) return 'now';
        if (s < 60) return `${s}s`;
        if (s < 3600) return `${Math.floor(s / 60)}m`;
        if (s < 86400) return `${Math.floor(s / 3600)}h`;
        return `${Math.floor(s / 86400)}d`;
    }

    _esc(str) {
        const div = document.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }
}

window.MissionTimeline = MissionTimeline;
window.ToolCard = ToolCard;
window.ActivityStream = ActivityStream;
