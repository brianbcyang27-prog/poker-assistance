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

window.MissionTimeline = MissionTimeline;
window.ToolCard = ToolCard;
