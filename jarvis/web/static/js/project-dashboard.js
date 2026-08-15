/**
 * ProjectDashboard — v9.2.0 D5 Living Projects.
 * Project cards grid, new-project form, and a live detail panel: goal,
 * current mission, confidence, progress, knowledge/artifacts/decisions,
 * and a recent-activity feed — all from one dashboard snapshot that
 * auto-refreshes on mission.* events.
 */
class ProjectDashboard {
    constructor() {
        this.initialized = false;
        this.container = null;
        this.projects = [];
        this.currentProject = null;
        this.currentTab = 'missions';
        this.snapshot = null;
        this._liveTimer = null;
        this._subscribed = false;
        this._domainColors = {
            engineering: 'var(--dept-engineering)',
            education: 'var(--dept-education)',
            research: 'var(--dept-research)',
            studio: 'var(--dept-studio)',
            finance: 'var(--dept-finance)',
            personal: 'var(--dept-personal)',
            system: 'var(--dept-system)',
        };
    }

    init(container) {
        this.container = container;
        this.initialized = true;
        this._bind();
        this._subscribe();
    }

    _bind() {
        const btn = this.container.querySelector('#mv-new-project-btn');
        if (btn) btn.addEventListener('click', () => this.openNewProject());
    }

    _subscribe() {
        if (this._subscribed || !window.JarvisWS) return;
        this._subscribed = true;
        window.JarvisWS.on('event', (msg) => {
            const ev = msg && msg.data;
            if (!ev || !ev.event_type || !ev.event_type.startsWith('mission.')) return;
            this._scheduleLiveRefresh();
        });
    }

    _scheduleLiveRefresh() {
        clearTimeout(this._liveTimer);
        this._liveTimer = setTimeout(() => this._liveRefresh(), 400);
    }

    async _liveRefresh() {
        if (this.currentProject) {
            await this._loadDetail();
        } else {
            await this.refresh();
        }
    }

    async refresh() {
        if (!this.initialized) return;
        try {
            const res = await fetch('/api/projects');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            this.projects = data.projects || [];
            this._renderGrid();
            this._updateRightPanel();
        } catch (e) {
            const grid = document.getElementById('mv-projects-grid');
            if (grid) grid.innerHTML = `<div class="mv-empty-state">Failed to load projects: ${this._esc(e.message)}</div>`;
        }
    }

    _renderGrid() {
        const grid = document.getElementById('mv-projects-grid');
        if (!grid) return;
        if (this.projects.length === 0) {
            grid.innerHTML = `
                <div class="mv-empty-state">
                    <p>No projects yet — create your first project to track missions and knowledge.</p>
                </div>`;
            return;
        }
        grid.innerHTML = this.projects.map(p => this._cardHtml(p)).join('');
        grid.querySelectorAll('.mv-project-card').forEach(card => {
            card.addEventListener('click', () => this._openDetail(card.dataset.id));
        });
    }

    _cardHtml(p) {
        const deptColor = this._domainColors[p.domain] || 'var(--color-brand-secondary)';
        const statusClass = p.status === 'active' ? 'mv-chip-status-active' : p.status === 'paused' ? 'mv-chip-status-paused' : '';
        const progress = Math.round(p.progress || 0);
        const lastWorked = p.last_worked_on ? this._timeAgo(p.last_worked_on) : 'never';
        return `
            <div class="mv-project-card" data-id="${this._esc(p.id)}" style="--dept-color: ${deptColor}">
                <div class="mv-card-top">
                    <span class="mv-card-name" title="${this._esc(p.name)}">${this._esc(p.name)}</span>
                    <span class="mv-chip mv-chip-domain">${this._esc(p.domain)}</span>
                </div>
                <div class="mv-card-desc">${this._esc(p.description || 'No description')}</div>
                <div class="mv-card-stats">
                    <span class="mv-card-stat"><strong>${p.mission_ids ? p.mission_ids.length : 0}</strong> missions</span>
                    ${p.artifact_count != null ? `<span class="mv-card-stat"><strong>${p.artifact_count}</strong> artifacts</span>` : ''}
                    ${p.decision_count != null ? `<span class="mv-card-stat"><strong>${p.decision_count}</strong> decisions</span>` : ''}
                </div>
                <div class="mv-progress"><div class="mv-progress-fill" style="width: ${progress}%"></div></div>
                <div class="mv-card-meta">
                    <span class="mv-chip ${statusClass}">${this._esc(p.status || 'active')}</span>
                    <span>${this._esc(lastWorked)}</span>
                </div>
            </div>`;
    }

    openNewProject() {
        if (!this.initialized) return;
        const overlay = document.createElement('div');
        overlay.className = 'mv-form-overlay';
        overlay.id = 'mv-new-project-overlay';
        const domains = Object.keys(this._domainColors);
        overlay.innerHTML = `
            <div class="mv-form-card">
                <h3>New Project</h3>
                <div class="mv-field">
                    <label for="mv-np-name">Name</label>
                    <input id="mv-np-name" type="text" placeholder="e.g. jarvis" autocomplete="off">
                </div>
                <div class="mv-field">
                    <label for="mv-np-desc">Description</label>
                    <textarea id="mv-np-desc" placeholder="What is this project about?"></textarea>
                </div>
                <div class="mv-field">
                    <label for="mv-np-domain">Domain</label>
                    <select id="mv-np-domain">
                        ${domains.map(d => `<option value="${d}">${d}</option>`).join('')}
                    </select>
                </div>
                <div class="mv-form-actions">
                    <button class="mv-btn" id="mv-np-cancel">Cancel</button>
                    <button class="mv-btn mv-btn-primary" id="mv-np-create">Create Project</button>
                </div>
            </div>`;
        document.body.appendChild(overlay);
        overlay.querySelector('#mv-np-cancel').addEventListener('click', () => overlay.remove());
        overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
        overlay.querySelector('#mv-np-create').addEventListener('click', async () => {
            const name = overlay.querySelector('#mv-np-name').value.trim();
            if (!name) return;
            const btn = overlay.querySelector('#mv-np-create');
            btn.disabled = true;
            try {
                const res = await fetch('/api/projects', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name,
                        description: overlay.querySelector('#mv-np-desc').value.trim(),
                        domain: overlay.querySelector('#mv-np-domain').value,
                    }),
                });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const project = await res.json();
                overlay.remove();
                await this.refresh();
                this._openDetail(project.id);
            } catch (e) {
                btn.disabled = false;
                const nameEl = overlay.querySelector('#mv-np-name');
                nameEl.style.borderColor = 'var(--color-danger)';
                nameEl.title = `Failed: ${e.message}`;
            }
        });
        overlay.querySelector('#mv-np-name').focus();
    }

    async _openDetail(id) {
        this.currentProject = this.projects.find(p => String(p.id) === String(id));
        if (!this.currentProject) return;
        this.currentTab = 'missions';
        await this._loadDetail();
    }

    async _loadDetail() {
        const p = this.currentProject;
        const detail = document.getElementById('mv-project-detail');
        const grid = document.getElementById('mv-projects-grid');
        if (!detail || !grid) return;
        try {
            const res = await fetch(`/api/projects/${p.id}/dashboard`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            this.snapshot = await res.json();
        } catch (e) {
            this.snapshot = {
                project: p,
                missions: [],
                artifacts: [],
                decisions: [],
                knowledge: [],
                mission_statuses: { planned: 0, active: 0, completed: 0, failed: 0 },
                progress: p.progress || 0,
                current_mission: null,
                confidence: null,
                recent_activity: [],
            };
        }
        const snap = this.snapshot;
        grid.classList.add('hidden');
        detail.classList.remove('hidden');
        const deptColor = this._domainColors[snap.project.domain] || 'var(--color-brand-secondary)';
        detail.innerHTML = `
            <div class="mv-detail-head" style="--dept-color: ${deptColor}">
                <div>
                    <h3>${this._esc(snap.project.name)}</h3>
                    <div class="mv-card-desc">${this._esc(snap.project.description || 'No description')}</div>
                </div>
                <button class="mv-btn mv-btn-ghost" id="mv-detail-back">← Back</button>
            </div>
            ${this._summaryHtml(snap)}
            <div class="mv-tabs">
                <button class="mv-tab ${this.currentTab === 'missions' ? 'active' : ''}" data-tab="missions">Missions</button>
                <button class="mv-tab ${this.currentTab === 'artifacts' ? 'active' : ''}" data-tab="artifacts">Artifacts</button>
                <button class="mv-tab ${this.currentTab === 'decisions' ? 'active' : ''}" data-tab="decisions">Decisions</button>
                <button class="mv-tab ${this.currentTab === 'knowledge' ? 'active' : ''}" data-tab="knowledge">Knowledge</button>
            </div>
            <div class="mv-tab-pane active" id="mv-pane-missions"></div>
            <div class="mv-tab-pane" id="mv-pane-artifacts"></div>
            <div class="mv-tab-pane" id="mv-pane-decisions"></div>
            <div class="mv-tab-pane" id="mv-pane-knowledge"></div>`;

        detail.querySelector('#mv-detail-back').addEventListener('click', () => {
            detail.classList.add('hidden');
            grid.classList.remove('hidden');
            this.currentProject = null;
            this.snapshot = null;
        });
        detail.querySelectorAll('.mv-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                this.currentTab = tab.dataset.tab;
                detail.querySelectorAll('.mv-tab').forEach(t => t.classList.toggle('active', t === tab));
                detail.querySelectorAll('.mv-tab-pane').forEach(pane => {
                    pane.classList.toggle('active', pane.id === `mv-pane-${this.currentTab}`);
                });
                this._loadTab(this.currentTab);
            });
        });

        this._loadTab(this.currentTab);
        this._updateRightPanel(snap.project);
    }

    _summaryHtml(snap) {
        const mission = snap.current_mission;
        const active = (snap.mission_statuses || {}).active || 0;
        const progress = Math.round(snap.progress || 0);
        const confidence = snap.confidence != null ? `${Math.round(snap.confidence * 100)}%` : '—';
        const counts = {
            knowledge: (snap.knowledge || []).length,
            artifacts: (snap.artifacts || []).length,
            decisions: (snap.decisions || []).length,
        };
        return `
            <div class="mv-summary-strip">
                <div class="mv-summary-col">
                    <span class="mv-summary-k">Current Mission</span>
                    <span class="mv-summary-v">${this._esc(mission ? mission.title : 'None active')}</span>
                    ${mission ? `<span class="mv-summary-sub">${this._esc(mission.status)} · ${this._esc(mission.complexity)} · ${this._esc(mission.domain)}</span>` : ''}
                </div>
                <div class="mv-summary-col">
                    <span class="mv-summary-k">Active Missions</span>
                    <span class="mv-summary-v">${active}</span>
                </div>
                <div class="mv-summary-col">
                    <span class="mv-summary-k">Confidence</span>
                    <span class="mv-summary-v">${confidence}</span>
                </div>
                <div class="mv-summary-col">
                    <span class="mv-summary-k">Knowledge</span>
                    <span class="mv-summary-v">${counts.knowledge}</span>
                </div>
                <div class="mv-summary-col">
                    <span class="mv-summary-k">Artifacts</span>
                    <span class="mv-summary-v">${counts.artifacts}</span>
                </div>
                <div class="mv-summary-col">
                    <span class="mv-summary-k">Decisions</span>
                    <span class="mv-summary-v">${counts.decisions}</span>
                </div>
                <div class="mv-summary-progress">
                    <span class="mv-summary-k">Progress</span>
                    <div class="mv-progress"><div class="mv-progress-fill" style="width: ${progress}%"></div></div>
                    <span class="mv-summary-sub">${progress}%</span>
                </div>
            </div>
            ${this._activityHtml(snap.recent_activity || [])}`;
    }

    _activityHtml(entries) {
        if (entries.length === 0) return '';
        return `
            <div class="mv-summary-activity">
                <div class="mv-summary-k">Recent Activity</div>
                ${entries.map(e => `
                    <div class="pd-timeline-item">
                        <span class="pd-timeline-dot pd-dot-${this._esc(e.kind)}"></span>
                        <div class="pd-timeline-content">
                            <span class="pd-timeline-desc">${this._esc(e.label)}</span>
                            <span class="pd-timeline-meta">${this._esc(e.kind)}${e.status ? ` · ${this._esc(e.status)}` : ''} · ${this._esc(this._timeAgo(e.when))}</span>
                        </div>
                    </div>`).join('')}
            </div>`;
    }

    _loadTab(tab) {
        const pane = document.getElementById(`mv-pane-${tab}`);
        if (!pane) return;
        const snap = this.snapshot;
        const data = {
            missions: snap.missions || [],
            artifacts: snap.artifacts || [],
            decisions: snap.decisions || [],
            nodes: snap.knowledge || [],
        };
        pane.innerHTML = this._tabContent(tab, data);
    }

    _tabContent(tab, data) {
        if (tab === 'missions') {
            const missions = data.missions || [];
            if (missions.length === 0) return '<div class="mv-empty-state">No missions yet</div>';
            return missions.map(m => `
                <div class="mv-list-item">
                    <div>
                        <div class="mv-list-item-title">${this._esc(m.title)}</div>
                        <div class="mv-list-item-sub">${this._esc(m.goal || '')}</div>
                    </div>
                    <div class="mv-list-item-meta">
                        <div class="mv-chip ${m.status === 'completed' ? 'mv-chip-status-active' : ''}">${this._esc(m.status)}</div>
                        <div style="margin-top: 4px">${this._esc(m.complexity)} · ${this._esc(m.domain)}</div>
                    </div>
                </div>`).join('');
        }
        if (tab === 'artifacts') {
            const artifacts = data.artifacts || [];
            if (artifacts.length === 0) return '<div class="mv-empty-state">No artifacts yet</div>';
            return artifacts.map(a => `
                <div class="mv-list-item">
                    <div>
                        <div class="mv-list-item-title">${this._esc(a.name)}</div>
                        <div class="mv-list-item-sub">${this._esc(String(a.content || '').slice(0, 120))}</div>
                    </div>
                    <div class="mv-list-item-meta">${this._esc(a.artifact_type)}</div>
                </div>`).join('');
        }
        if (tab === 'decisions') {
            const decisions = data.decisions || [];
            if (decisions.length === 0) return '<div class="mv-empty-state">No decisions recorded</div>';
            return decisions.map(d => `
                <div class="mv-list-item">
                    <div>
                        <div class="mv-list-item-title">${this._esc(d.topic)}</div>
                        <div class="mv-list-item-sub">${this._esc(d.decision)}</div>
                    </div>
                    <div class="mv-list-item-meta">${this._esc(d.reason || '')}</div>
                </div>`).join('');
        }
        if (tab === 'knowledge') {
            const nodes = data.nodes || [];
            if (nodes.length === 0) return '<div class="mv-empty-state">No knowledge nodes yet</div>';
            return nodes.map(n => `
                <div class="mv-list-item">
                    <div>
                        <div class="mv-list-item-title">${this._esc(n.label)}</div>
                        <div class="mv-list-item-sub">${this._esc(n.content || '')}</div>
                    </div>
                    <div class="mv-list-item-meta">${this._esc(n.node_type)}</div>
                </div>`).join('');
        }
        return '';
    }

    _updateRightPanel(project) {
        const summary = document.getElementById('projects-summary');
        if (!summary) return;
        if (project) {
            summary.innerHTML = `
                <div class="mv-right-row"><span>Project</span><strong>${this._esc(project.name)}</strong></div>
                <div class="mv-right-row"><span>Domain</span><strong>${this._esc(project.domain)}</strong></div>
                <div class="mv-right-row"><span>Status</span><strong>${this._esc(project.status)}</strong></div>
                <div class="mv-right-row"><span>Progress</span><strong>${Math.round(project.progress || 0)}%</strong></div>`;
        } else {
            summary.innerHTML = '<span class="right-empty-text">No project selected</span>';
        }
        const status = document.getElementById('projects-status');
        if (status) {
            const active = this.projects.filter(p => p.status === 'active').length;
            const total = this.projects.length;
            status.innerHTML = `<div class="mv-right-row"><span>Active</span><strong>${active} / ${total}</strong></div>`;
        }
    }

    _timeAgo(iso) {
        const then = new Date(iso).getTime();
        if (isNaN(then)) return 'unknown';
        const diff = Date.now() - then;
        const mins = Math.floor(diff / 60000);
        if (mins < 1) return 'just now';
        if (mins < 60) return `${mins}m ago`;
        const hours = Math.floor(mins / 60);
        if (hours < 24) return `${hours}h ago`;
        const days = Math.floor(hours / 24);
        return `${days}d ago`;
    }

    _esc(str) {
        const div = document.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }
}

window.ProjectDashboard = new ProjectDashboard();
