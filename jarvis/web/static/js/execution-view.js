/**
 * ExecutionView — v9.0.0 M2 Project Intelligence.
 * Live mission console: status header, timeline, DAG, and member activity.
 */
class ExecutionView {
    constructor() {
        this.initialized = false;
        this.container = null;
        this.projectId = null;
        this.missionId = null;
        this.timeline = null;
        this.dag = null;
        this._pollId = null;
        this._activitySeen = new Set();
    }

    init(container) {
        this.container = container;
        this.initialized = true;
        this._bind();
    }

    _bind() {
        const sel = this.container.querySelector('#mv-execution-project');
        if (sel) {
            sel.addEventListener('change', () => {
                this.projectId = sel.value || null;
                this._onProjectSelected();
            });
        }
    }

    async refreshProjects() {
        if (!this.initialized) return;
        try {
            const res = await fetch('/api/projects');
            if (!res.ok) return;
            const data = await res.json();
            const sel = document.getElementById('mv-execution-project');
            if (!sel) return;
            const current = sel.value;
            sel.innerHTML = '<option value="">Select project…</option>' +
                (data.projects || []).map(p =>
                    `<option value="${p.id}" ${String(p.id) === current ? 'selected' : ''}>${this._esc(p.name)}</option>`
                ).join('');
            if (current && !sel.value) {
                this.projectId = null;
                this._showEmpty();
            }
        } catch (_) {}
    }

    async _onProjectSelected() {
        if (!this.projectId) {
            this._showEmpty();
            return;
        }
        const body = document.getElementById('mv-execution-body');
        const empty = document.getElementById('mv-execution-empty');
        if (body) body.classList.remove('hidden');
        if (empty) empty.classList.add('hidden');

        await this._loadMissions();
        this._startPolling();
    }

    async _loadMissions() {
        try {
            const res = await fetch(`/api/projects/${this.projectId}/missions`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            const missions = data.missions || [];
            this.missionId = missions.length > 0 ? missions[0].id : null;

            const status = document.getElementById('mv-execution-status');
            const timelineEl = document.getElementById('mv-execution-timeline');
            const dagEl = document.getElementById('mv-execution-dag');

            if (!missions.length) {
                if (status) status.innerHTML = `<div class="mv-status-info"><span class="mv-status-title">No missions</span><span class="mv-status-sub">Create a mission from a project-scoped task</span></div>`;
                if (timelineEl) timelineEl.innerHTML = '';
                if (dagEl) dagEl.innerHTML = '';
                this._updateRightPanel(null);
                return;
            }

            const mission = missions[0];
            if (status) {
                const dotClass = mission.status === 'completed' ? 'completed' : mission.status === 'failed' ? 'failed' : 'active';
                status.innerHTML = `
                    <div class="mv-status-dot ${dotClass}"></div>
                    <div class="mv-status-info">
                        <span class="mv-status-title">${this._esc(mission.title)}</span>
                        <span class="mv-status-sub">${this._esc(mission.goal || '')}</span>
                    </div>
                    <div class="mv-chip mv-chip-domain" style="margin-left:auto">${this._esc(mission.complexity)}</div>
                    <div class="mv-chip ${mission.status === 'completed' ? 'mv-chip-status-active' : ''}">${this._esc(mission.status)}</div>`;
            }

            if (!this.timeline && window.MissionTimeline) {
                this.timeline = new MissionTimeline('mv-execution-timeline');
            }
            if (this.timeline) {
                this.timeline.setTimeline([{
                    event_type: 'mission.start',
                    label: mission.title,
                    description: mission.goal || '',
                    status: mission.status,
                }]);
            }

            if (!this.dag && window.MissionDAG) {
                this.dag = new MissionDAG(dagEl);
                this.dag.init();
            }
            await this._loadTimeline();
            this._updateRightPanel(mission);
        } catch (e) {
            const status = document.getElementById('mv-execution-status');
            if (status) status.innerHTML = `<div class="mv-status-info"><span class="mv-status-title">Error</span><span class="mv-status-sub">${this._esc(e.message)}</span></div>`;
        }
    }

    async _loadTimeline() {
        if (!this.projectId || !this.dag) return;
        try {
            const res = await fetch(`/api/projects/${this.projectId}/timeline`);
            if (!res.ok) return;
            const data = await res.json();
            this.dag.render({
                nodes: (data.nodes || []).map((n, i) => ({
                    ...n,
                    name: n.label || n.name,
                    layer: i,
                })),
                edges: (data.edges || []).map(e => ({
                    from: e.from ?? e.source,
                    to: e.to ?? e.target,
                })),
            });
        } catch (_) {}
    }

    async _loadDashboard() {
        if (!this.projectId) return;
        try {
            const res = await fetch(`/api/projects/${this.projectId}/dashboard`);
            if (!res.ok) return;
            const data = await res.json();
            const missions = data.missions || [];
            if (missions.length > 0 && this.timeline) {
                this.timeline.setMilestones(missions);
            }
        } catch (_) {}
    }

    _startPolling() {
        this._stopPolling();
        this._pollId = setInterval(() => {
            this._loadMissions();
            this._loadTimeline();
        }, 5000);
    }

    _stopPolling() {
        if (this._pollId) {
            clearInterval(this._pollId);
            this._pollId = null;
        }
    }

    _showEmpty() {
        this._stopPolling();
        const body = document.getElementById('mv-execution-body');
        const empty = document.getElementById('mv-execution-empty');
        if (body) body.classList.add('hidden');
        if (empty) empty.classList.remove('hidden');
        this._updateRightPanel(null);
    }

    _updateRightPanel(mission) {
        const summary = document.getElementById('execution-summary');
        if (!summary) return;
        if (!mission) {
            summary.innerHTML = '<span class="right-empty-text">No mission running</span>';
            return;
        }
        summary.innerHTML = `
            <div class="mv-status-line">
                <span class="mv-status-dot ${mission.status === 'completed' ? 'completed' : 'active'}"></span>
                <strong>${this._esc(mission.title)}</strong>
            </div>
            <div class="mv-status-line"><span>Status</span><strong style="margin-left:auto">${this._esc(mission.status)}</strong></div>
            <div class="mv-status-line"><span>Complexity</span><strong style="margin-left:auto">${this._esc(mission.complexity)}</strong></div>
            <div class="mv-status-line"><span>Domain</span><strong style="margin-left:auto">${this._esc(mission.domain)}</strong></div>`;
    }

    _esc(str) {
        const div = document.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }
}

window.ExecutionView = new ExecutionView();
