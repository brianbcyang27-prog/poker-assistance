/* JARVIS Unified Timeline v1.0.0 — Live event log panel */

const UNIFIED_TIMELINE_CSS = `
#ut-panel {
    position: fixed;
    top: 0;
    right: 0;
    width: 400px;
    height: 100vh;
    background: #0a0a0f;
    border-left: 1px solid rgba(0, 240, 255, 0.08);
    z-index: 50;
    display: flex;
    flex-direction: column;
    font-family: 'SF Mono', 'Fira Code', 'SF Pro Display', -apple-system, monospace;
    font-size: 12px;
    color: rgba(180, 230, 245, 0.9);
    transform: translateX(0);
    transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1);
    box-shadow: -8px 0 24px rgba(0, 0, 0, 0.6);
}

#ut-panel.collapsed {
    transform: translateX(400px);
}

#ut-toggle {
    position: fixed;
    top: 50%;
    right: 0;
    transform: translateY(-50%);
    width: 28px;
    height: 64px;
    background: #1a1a2e;
    border: 1px solid rgba(0, 240, 255, 0.12);
    border-right: none;
    border-radius: 6px 0 0 6px;
    color: #00f0ff;
    cursor: pointer;
    z-index: 51;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    transition: all 0.2s ease;
    writing-mode: vertical-rl;
    letter-spacing: 2px;
    text-transform: uppercase;
    font-size: 9px;
    gap: 4px;
}

#ut-toggle:hover {
    background: rgba(0, 240, 255, 0.1);
    box-shadow: 0 0 16px rgba(0, 240, 255, 0.15);
}

#ut-panel.collapsed + #ut-toggle {
    right: 0;
}

#ut-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid rgba(0, 240, 255, 0.08);
    flex-shrink: 0;
    background: #0d0d18;
}

#ut-title {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: rgba(0, 240, 255, 0.8);
}

#ut-count {
    font-size: 10px;
    color: rgba(80, 140, 170, 0.5);
    font-family: 'SF Mono', monospace;
}

#ut-toolbar {
    display: flex;
    gap: 6px;
    padding: 8px 12px;
    border-bottom: 1px solid rgba(0, 240, 255, 0.06);
    flex-shrink: 0;
    flex-wrap: wrap;
    align-items: center;
    background: #0a0a0f;
}

#ut-search {
    flex: 1;
    min-width: 140px;
    background: rgba(0, 240, 255, 0.04);
    border: 1px solid rgba(0, 240, 255, 0.08);
    border-radius: 4px;
    padding: 5px 10px;
    color: rgba(180, 230, 245, 0.9);
    font-size: 11px;
    font-family: inherit;
    outline: none;
    transition: border-color 0.15s ease;
}

#ut-search:focus {
    border-color: rgba(0, 240, 255, 0.3);
    box-shadow: 0 0 8px rgba(0, 240, 255, 0.08);
}

#ut-search::placeholder {
    color: rgba(80, 140, 170, 0.3);
}

#ut-export-btn {
    background: rgba(0, 240, 255, 0.06);
    border: 1px solid rgba(0, 240, 255, 0.1);
    border-radius: 4px;
    color: rgba(0, 240, 255, 0.7);
    padding: 4px 8px;
    cursor: pointer;
    font-size: 10px;
    font-family: inherit;
    transition: all 0.15s ease;
    white-space: nowrap;
}

#ut-export-btn:hover {
    background: rgba(0, 240, 255, 0.12);
    color: #00f0ff;
}

#ut-filter-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    padding: 0 12px 8px 12px;
    flex-shrink: 0;
    background: #0a0a0f;
}

.ut-filter-badge {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    border-radius: 12px;
    background: rgba(0, 240, 255, 0.04);
    border: 1px solid rgba(0, 240, 255, 0.06);
    color: rgba(80, 140, 170, 0.6);
    font-size: 9px;
    cursor: pointer;
    transition: all 0.15s ease;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    user-select: none;
}

.ut-filter-badge:hover {
    background: rgba(0, 240, 255, 0.08);
    border-color: rgba(0, 240, 255, 0.15);
}

.ut-filter-badge.active {
    background: rgba(0, 240, 255, 0.12);
    border-color: rgba(0, 240, 255, 0.25);
    color: #00f0ff;
}

.ut-filter-badge .ut-filter-count {
    background: rgba(0, 240, 255, 0.15);
    padding: 0 4px;
    border-radius: 8px;
    font-size: 8px;
    font-family: 'SF Mono', monospace;
    color: #00f0ff;
}

.ut-filter-badge.active .ut-filter-count {
    background: rgba(0, 240, 255, 0.25);
}

#ut-event-list {
    flex: 1;
    overflow-y: auto;
    padding: 4px 0;
}

#ut-event-list::-webkit-scrollbar {
    width: 3px;
}

#ut-event-list::-webkit-scrollbar-track {
    background: transparent;
}

#ut-event-list::-webkit-scrollbar-thumb {
    background: rgba(0, 240, 255, 0.1);
    border-radius: 3px;
}

#ut-event-list::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 240, 255, 0.2);
}

.ut-event {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 6px 14px;
    border-bottom: 1px solid rgba(0, 240, 255, 0.02);
    transition: background 0.15s ease;
    cursor: default;
}

.ut-event:hover {
    background: rgba(0, 240, 255, 0.03);
}

.ut-event-icon {
    width: 20px;
    text-align: center;
    font-size: 13px;
    flex-shrink: 0;
    line-height: 1.4;
}

.ut-event-body {
    flex: 1;
    min-width: 0;
}

.ut-event-header {
    display: flex;
    align-items: baseline;
    gap: 6px;
    margin-bottom: 1px;
}

.ut-event-timestamp {
    font-size: 9px;
    color: rgba(80, 140, 170, 0.35);
    font-family: 'SF Mono', monospace;
    flex-shrink: 0;
}

.ut-event-source {
    font-size: 9px;
    color: rgba(0, 240, 255, 0.5);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.ut-event-type {
    font-size: 8px;
    color: rgba(80, 140, 170, 0.3);
    font-family: 'SF Mono', monospace;
}

.ut-event-description {
    font-size: 11px;
    color: rgba(180, 230, 245, 0.7);
    line-height: 1.4;
    word-break: break-word;
}

.ut-event-details {
    font-size: 9px;
    color: rgba(80, 140, 170, 0.4);
    margin-top: 2px;
    font-family: 'SF Mono', monospace;
    line-height: 1.3;
    display: none;
    white-space: pre-wrap;
}

.ut-event.details-open .ut-event-details {
    display: block;
}

.ut-event-details-toggle {
    font-size: 8px;
    color: rgba(0, 240, 255, 0.3);
    cursor: pointer;
    margin-top: 2px;
    user-select: none;
    display: inline-block;
}

.ut-event-details-toggle:hover {
    color: #00f0ff;
}

#ut-new-events {
    display: none;
    padding: 6px 14px;
    background: rgba(0, 240, 255, 0.06);
    border-bottom: 1px solid rgba(0, 240, 255, 0.1);
    color: #00f0ff;
    font-size: 10px;
    text-align: center;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 1px;
    flex-shrink: 0;
    transition: background 0.15s ease;
}

#ut-new-events:hover {
    background: rgba(0, 240, 255, 0.1);
}

#ut-new-events.visible {
    display: block;
}

.ut-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: rgba(80, 140, 170, 0.25);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
}
`;

class UnifiedTimeline {
    constructor(options = {}) {
        this._events = [];
        this._maxEvents = 200;
        this._ws = null;
        this._reconnectTimer = null;
        this._activeFilters = new Set();
        this._searchTerm = '';
        this._isCollapsed = options.collapsed !== undefined ? options.collapsed : false;
        this._userScrolledUp = false;
        this._newEventCount = 0;
        this._containerCreated = false;

        this._EVENT_ICONS = {
            'worker.started': '⚙️',
            'worker.completed': '✅',
            'worker.error': '❌',
            'worker.tool_call': '🔧',
            'worker.help_request': '🤝',
            'worker.result_shared': '📤',
            'king.planning': '📋',
            'king.delegated': '📨',
            'king.completed': '👑',
            'mission.started': '🚀',
            'mission.completed': '🎯',
            'mission.failed': '💥',
            'jarvis.thinking': '🧠',
            'jarvis.delegated': '🎯',
            'jarvis.responded': '💬',
            'system.started': '⚡',
        };

        this._EVENT_CATEGORIES = {
            'worker': ['worker.started', 'worker.completed', 'worker.error', 'worker.tool_call', 'worker.help_request', 'worker.result_shared'],
            'king': ['king.planning', 'king.delegated', 'king.completed'],
            'mission': ['mission.started', 'mission.completed', 'mission.failed'],
            'jarvis': ['jarvis.thinking', 'jarvis.delegated', 'jarvis.responded'],
            'system': ['system.started'],
        };

        this._injectCSS();
        this._createDOM(options.container);
        this._bindEvents();

        if (options.wsUrl !== false) {
            this.connect(options.wsUrl);
        }
    }

    _injectCSS() {
        if (document.getElementById('ut-styles')) return;
        const style = document.createElement('style');
        style.id = 'ut-styles';
        style.textContent = UNIFIED_TIMELINE_CSS;
        document.head.appendChild(style);
    }

    _createDOM(container) {
        let panel = container;
        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'ut-panel';
            document.body.appendChild(panel);
            this._containerCreated = true;
        } else {
            panel.id = 'ut-panel';
        }

        panel.innerHTML = `
            <div id="ut-header">
                <span id="ut-title">⏱ Timeline</span>
                <span id="ut-count">0</span>
            </div>
            <div id="ut-toolbar">
                <input type="text" id="ut-search" placeholder="Search events..." spellcheck="false">
                <button id="ut-export-btn" title="Export as JSON">📥 JSON</button>
            </div>
            <div id="ut-filter-bar"></div>
            <div id="ut-new-events">↑ New events</div>
            <div id="ut-event-list">
                <div class="ut-empty">No events yet</div>
            </div>
        `;

        this._panel = panel;
        this._eventList = panel.querySelector('#ut-event-list');
        this._countEl = panel.querySelector('#ut-count');
        this._searchInput = panel.querySelector('#ut-search');
        this._exportBtn = panel.querySelector('#ut-export-btn');
        this._filterBar = panel.querySelector('#ut-filter-bar');
        this._newEventsBar = panel.querySelector('#ut-new-events');

        let toggle = document.getElementById('ut-toggle');
        if (!toggle) {
            toggle = document.createElement('button');
            toggle.id = 'ut-toggle';
            toggle.textContent = 'Timeline';
            document.body.appendChild(toggle);
        }

        this._toggleBtn = toggle;

        if (this._isCollapsed) {
            panel.classList.add('collapsed');
        }

        this._buildFilterBadges();
        this._render();
    }

    _buildFilterBadges() {
        this._filterBar.innerHTML = '';
        const allCategories = ['worker', 'king', 'mission', 'jarvis', 'system'];

        const badgeAll = document.createElement('span');
        badgeAll.className = 'ut-filter-badge active';
        badgeAll.dataset.filter = '__all__';
        badgeAll.innerHTML = '<span>All</span>';
        badgeAll.addEventListener('click', () => this._toggleFilter('__all__'));
        this._filterBar.appendChild(badgeAll);

        allCategories.forEach(cat => {
            const badge = document.createElement('span');
            badge.className = 'ut-filter-badge';
            badge.dataset.filter = cat;
            badge.innerHTML = `<span>${cat}</span><span class="ut-filter-count">0</span>`;
            badge.addEventListener('click', () => this._toggleFilter(cat));
            this._filterBar.appendChild(badge);
        });

        this._filterBadges = this._filterBar.querySelectorAll('.ut-filter-badge');
    }

    _toggleFilter(filter) {
        if (filter === '__all__') {
            if (this._activeFilters.size === 0) return;
            this._activeFilters.clear();
            this._filterBadges.forEach(b => b.classList.remove('active'));
            this._filterBadges[0].classList.add('active');
            this._render();
            return;
        }

        const badgeAll = this._filterBadges[0];
        badgeAll.classList.remove('active');

        if (this._activeFilters.has(filter)) {
            this._activeFilters.delete(filter);
        } else {
            this._activeFilters.add(filter);
        }

        if (this._activeFilters.size === 0) {
            badgeAll.classList.add('active');
        }

        this._updateBadgeStates();
        this._render();
    }

    _updateBadgeStates() {
        this._filterBadges.forEach(b => {
            if (b.dataset.filter === '__all__') return;
            b.classList.toggle('active', this._activeFilters.has(b.dataset.filter));
        });
    }

    _bindEvents() {
        this._eventList.addEventListener('scroll', () => {
            const { scrollTop, scrollHeight, clientHeight } = this._eventList;
            const atBottom = scrollHeight - scrollTop - clientHeight < 40;
            this._userScrolledUp = !atBottom;
            if (atBottom && this._newEventCount > 0) {
                this._newEventCount = 0;
                this._newEventsBar.classList.remove('visible');
            }
        });

        this._newEventsBar.addEventListener('click', () => {
            this._scrollToBottom();
        });

        this._searchInput.addEventListener('input', (e) => {
            this._searchTerm = e.target.value.toLowerCase();
            this._render();
        });

        this._exportBtn.addEventListener('click', () => this._exportJSON());

        this._toggleBtn.addEventListener('click', () => {
            this._isCollapsed = !this._isCollapsed;
            this._panel.classList.toggle('collapsed', this._isCollapsed);
        });
    }

    _scrollToBottom() {
        this._eventList.scrollTop = this._eventList.scrollHeight;
        this._userScrolledUp = false;
        this._newEventCount = 0;
        this._newEventsBar.classList.remove('visible');
    }

    connect(wsUrl) {
        if (this._ws && this._ws.readyState === WebSocket.OPEN) return;

        const url = wsUrl || `ws://${location.host}/ws/agents`;
        this._ws = new WebSocket(url);

        this._ws.onopen = () => {
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
                console.error('[UnifiedTimeline] WS parse error:', e);
            }
        };

        this._wsReconnects = this._wsReconnects || 0;
        this._ws.onclose = () => {
            this._wsReconnects++;
            if (this._wsReconnects > 20) return;
            this._reconnectTimer = setTimeout(() => this.connect(wsUrl), 3000);
        };

        this._ws.onerror = () => {};
    }

    _handleWSMessage(data) {
        if (data.type === 'event') {
            this.addEvent(data.data);
        } else if (data.type === 'status') {
            this._handleStatusEvent(data.data);
        } else if (data.type === 'mission_progress') {
            this.addEvent({
                event_type: 'mission.progress',
                source: 'mission',
                label: data.data.goal || 'Mission in progress',
                payload: data.data,
            });
        }
    }

    _handleStatusEvent(data) {
        if (!data || !data.kings) return;
        Object.values(data.kings).forEach(king => {
            if (king.workers) {
                Object.values(king.workers).forEach(worker => {
                    if (worker.last_event) {
                        this.addEvent({
                            event_type: worker.last_event.type || 'worker.status',
                            source: worker.card_id || 'worker',
                            label: worker.last_event.label || worker.status || 'status update',
                            payload: worker.last_event,
                            agent_name: worker.name || worker.card_id,
                        });
                    }
                });
            }
        });
    }

    addEvent(eventData) {
        if (!eventData || !eventData.event_type) return;

        const event = {
            id: `evt_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
            timestamp: Date.now(),
            event_type: eventData.event_type,
            source: eventData.source || 'system',
            label: eventData.label || eventData.event_type,
            icon: eventData.icon || this._EVENT_ICONS[eventData.event_type] || '◉',
            description: eventData.description || eventData.label || eventData.event_type,
            details: eventData.details || (eventData.payload ? JSON.stringify(eventData.payload, null, 2) : null),
            agent_name: eventData.agent_name || eventData.source || null,
            payload: eventData.payload || null,
        };

        this._events.push(event);

        if (this._events.length > this._maxEvents) {
            this._events.shift();
        }

        this._updateCounts();
        this._render();

        if (!this._userScrolledUp) {
            requestAnimationFrame(() => this._scrollToBottom());
        } else {
            this._newEventCount++;
            this._newEventsBar.textContent = `↑ ${this._newEventCount} new event${this._newEventCount > 1 ? 's' : ''}`;
            this._newEventsBar.classList.add('visible');
        }
    }

    _getFilteredEvents() {
        let events = this._events;

        if (this._activeFilters.size > 0) {
            events = events.filter(e => {
                const prefix = e.event_type.split('.')[0];
                return this._activeFilters.has(prefix);
            });
        }

        if (this._searchTerm) {
            const term = this._searchTerm.toLowerCase();
            events = events.filter(e =>
                e.event_type.toLowerCase().includes(term) ||
                e.source.toLowerCase().includes(term) ||
                (e.description && e.description.toLowerCase().includes(term)) ||
                (e.agent_name && e.agent_name.toLowerCase().includes(term))
            );
        }

        return events;
    }

    _render() {
        const filtered = this._getFilteredEvents();

        if (filtered.length === 0) {
            this._eventList.innerHTML = '<div class="ut-empty">No events to display</div>';
            return;
        }

        const fragment = document.createDocumentFragment();

        filtered.forEach(event => {
            const el = document.createElement('div');
            el.className = 'ut-event';
            el.dataset.eventId = event.id;

            const time = new Date(event.timestamp);
            const timeStr = time.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });

            const icon = event.icon || '◉';
            const category = event.event_type.split('.')[0];

            el.innerHTML = `
                <div class="ut-event-icon">${icon}</div>
                <div class="ut-event-body">
                    <div class="ut-event-header">
                        <span class="ut-event-timestamp">${timeStr}</span>
                        <span class="ut-event-source">${this._escapeHtml(event.source)}</span>
                        <span class="ut-event-type">${this._escapeHtml(event.event_type)}</span>
                    </div>
                    <div class="ut-event-description">${this._escapeHtml(event.description)}</div>
                    ${event.details ? `<div class="ut-event-details-toggle" data-event-id="${event.id}">▶ details</div><div class="ut-event-details">${this._escapeHtml(event.details)}</div>` : ''}
                </div>
            `;

            const toggle = el.querySelector('.ut-event-details-toggle');
            if (toggle) {
                toggle.addEventListener('click', (e) => {
                    e.stopPropagation();
                    el.classList.toggle('details-open');
                    toggle.textContent = el.classList.contains('details-open') ? '▼ details' : '▶ details';
                });
            }

            fragment.appendChild(el);
        });

        this._eventList.innerHTML = '';
        this._eventList.appendChild(fragment);
    }

    _updateCounts() {
        this._countEl.textContent = this._events.length;

        const counts = {};
        this._events.forEach(e => {
            const cat = e.event_type.split('.')[0];
            counts[cat] = (counts[cat] || 0) + 1;
        });

        this._filterBar.querySelectorAll('.ut-filter-badge').forEach(badge => {
            if (badge.dataset.filter === '__all__') return;
            const count = counts[badge.dataset.filter] || 0;
            const countEl = badge.querySelector('.ut-filter-count');
            if (countEl) countEl.textContent = count;
            badge.style.display = count === 0 ? 'none' : '';
        });
    }

    _exportJSON() {
        const data = {
            exportTime: new Date().toISOString(),
            totalEvents: this._events.length,
            events: this._events,
        };

        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `jarvis-timeline-${new Date().toISOString().slice(0, 10)}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    destroy() {
        if (this._ws) {
            this._ws.close();
            this._ws = null;
        }
        if (this._reconnectTimer) {
            clearTimeout(this._reconnectTimer);
            this._reconnectTimer = null;
        }
        if (this._containerCreated && this._panel && this._panel.parentNode) {
            this._panel.parentNode.removeChild(this._panel);
        }
        const toggle = document.getElementById('ut-toggle');
        if (toggle) toggle.remove();
        const style = document.getElementById('ut-styles');
        if (style) style.remove();
    }
}

window.UnifiedTimeline = UnifiedTimeline;
