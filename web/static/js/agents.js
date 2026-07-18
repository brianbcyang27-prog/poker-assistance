/**
 * JARVIS v5.0.0 - Agent Status Module
 * Real-time agent orchestration display
 */

const JARVIS_AGENTS = {
    initialized: false,
    workers: [],
    tasks: [],
    pollInterval: null,

    async init() {
        try {
            await this.refreshWorkers();
            await this.refreshTasks();
            this.initialized = true;
            this.startPolling();
            this.renderPanel();
        } catch (e) {
            console.warn('Agent orchestration not available:', e);
        }
    },

    startPolling() {
        this.pollInterval = setInterval(() => {
            this.refreshWorkers();
            this.refreshTasks();
            this.renderPanel();
        }, 3000);
    },

    async refreshWorkers() {
        try {
            const resp = await fetch('/api/agents/pool/workers');
            if (resp.ok) {
                const data = await resp.json();
                this.workers = data.workers || [];
            }
        } catch (e) {
            // Silent fail
        }
    },

    async refreshTasks() {
        try {
            const resp = await fetch('/api/agents/tasks');
            if (resp.ok) {
                const data = await resp.json();
                this.tasks = data.tasks || [];
            }
        } catch (e) {
            // Silent fail
        }
    },

    renderPanel() {
        const container = document.getElementById('intel-agents');
        if (!container) return;

        if (this.workers.length === 0 && this.tasks.length === 0) {
            container.innerHTML = `
                <div class="intel-card" style="text-align:center; color:var(--text-tertiary); font-size:var(--text-xs); padding:var(--space-4);">
                    No active agents
                </div>`;
            return;
        }

        let html = '';

        // Workers
        if (this.workers.length > 0) {
            html += '<div style="margin-bottom:var(--space-3);">';
            html += '<div style="font-size:var(--text-xs); color:var(--text-tertiary); margin-bottom:var(--space-2); letter-spacing:var(--tracking-widest); text-transform:uppercase;">Workers</div>';
            for (const worker of this.workers) {
                const stateColor = this.getStateColor(worker.state);
                html += `
                    <div class="intel-card" style="padding:var(--space-2) var(--space-3); margin-bottom:var(--space-2);">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-size:var(--text-sm); font-weight:var(--weight-medium);">${worker.card_id} ${worker.name}</span>
                            <span style="font-size:10px; color:${stateColor};">${worker.state.toUpperCase()}</span>
                        </div>
                        ${worker.current_task ? `<div style="font-size:10px; color:var(--text-tertiary); margin-top:2px;">Working on: ${worker.current_task}</div>` : ''}
                    </div>`;
            }
            html += '</div>';
        }

        // Tasks
        if (this.tasks.length > 0) {
            html += '<div>';
            html += '<div style="font-size:var(--text-xs); color:var(--text-tertiary); margin-bottom:var(--space-2); letter-spacing:var(--tracking-widest); text-transform:uppercase;">Active Tasks</div>';
            for (const task of this.tasks.slice(0, 5)) {
                const statusColor = this.getStatusColor(task.status);
                html += `
                    <div class="intel-card" style="padding:var(--space-2) var(--space-3); margin-bottom:var(--space-2);">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-size:var(--text-sm); font-weight:var(--weight-medium);">${task.name}</span>
                            <span style="font-size:10px; color:${statusColor};">${task.status.toUpperCase()}</span>
                        </div>
                        <div style="font-size:10px; color:var(--text-tertiary); margin-top:2px;">
                            ${task.king} → ${task.worker} · ${task.action}
                        </div>
                    </div>`;
            }
            html += '</div>';
        }

        container.innerHTML = html;
    },

    getStateColor(state) {
        const colors = {
            idle: 'var(--text-tertiary)',
            busy: 'var(--gold)',
            offline: 'var(--text-tertiary)',
            error: 'var(--danger)',
        };
        return colors[state] || 'var(--text-tertiary)';
    },

    getStatusColor(status) {
        const colors = {
            pending: 'var(--text-tertiary)',
            queued: 'var(--text-tertiary)',
            running: 'var(--gold)',
            completed: 'var(--success)',
            failed: 'var(--danger)',
            cancelled: 'var(--text-tertiary)',
            timeout: 'var(--warning)',
        };
        return colors[status] || 'var(--text-tertiary)';
    },

    // ── API Methods ──────────────────────────────────

    async delegateTask(name, king, worker, action, params = {}, priority = 'normal') {
        const resp = await fetch('/api/agents/delegate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, king, worker, action, params, priority }),
        });
        return await resp.json();
    },

    async cancelTask(taskId) {
        const resp = await fetch(`/api/agents/tasks/${taskId}/cancel`, { method: 'POST' });
        return await resp.json();
    },

    async getStats() {
        const resp = await fetch('/api/agents/stats');
        return await resp.json();
    },
};

// Initialize on load
if (typeof JARVIS !== 'undefined') {
    JARVIS.agents = JARVIS_AGENTS;
}
