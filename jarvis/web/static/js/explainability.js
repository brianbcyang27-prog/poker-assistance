/**
 * Explainability Overlay — v3.2.0
 *
 * Click any agent or task to see reasoning, confidence,
 * model used, capabilities matched, relevant memories,
 * execution time, and decisions made.
 *
 * Shows a floating panel with structured details.
 */

class ExplainabilityOverlay {
    constructor() {
        this.panel = document.getElementById('explain-panel');
        this.overlay = document.getElementById('explain-overlay');
        this._active = false;

        if (this.overlay) {
            this.overlay.addEventListener('click', () => this.hide());
        }
    }

    /**
     * Show explanation for an agent or task
     * @param {string} type - 'agent' | 'task' | 'decision'
     * @param {object} data - Agent/task data with reasoning details
     * @param {number} x - Click X position
     * @param {number} y - Click Y position
     */
    show(type, data, x, y) {
        if (!this.panel || !this.overlay) return;

        this.overlay.classList.add('visible');
        this.panel.classList.add('visible');

        // Position panel near click but keep in viewport
        const pw = 380;
        const ph = 500;
        const px = Math.min(x + 20, window.innerWidth - pw - 20);
        const py = Math.min(y - 20, window.innerHeight - ph - 20);
        this.panel.style.left = `${Math.max(20, px)}px`;
        this.panel.style.top = `${Math.max(20, py)}px`;

        this.panel.innerHTML = this._buildContent(type, data);
        this._active = true;
    }

    hide() {
        if (!this.panel || !this.overlay) return;
        this.panel.classList.remove('visible');
        this.overlay.classList.remove('visible');
        this._active = false;
    }

    get isVisible() { return this._active; }

    _buildContent(type, data) {
        const header = this._buildHeader(type, data);
        const reasoning = this._buildReasoning(data);
        const metrics = this._buildMetrics(data);
        const capabilities = this._buildCapabilities(data);
        const memories = this._buildMemories(data);
        const timeline = this._buildTimeline(data);

        return `
            ${header}
            <div class="explain-body">
                ${reasoning}
                ${metrics}
                ${capabilities}
                ${memories}
                ${timeline}
            </div>
        `;
    }

    _buildHeader(type, data) {
        const icons = { agent: '\uD83E\uDD16', task: '\uD83D\uDCCB', decision: '\uD83D\uDD0D' };
        const colors = {
            engineering: 'var(--color-engineering)',
            research: 'var(--color-research)',
            personal: 'var(--color-personal)',
            system: 'var(--color-system)',
        };
        const dept = data.department || 'engineering';
        const color = colors[dept] || 'var(--color-primary)';

        return `
            <div class="explain-header" style="--accent: ${color}">
                <div class="explain-icon">${icons[type] || '\u2022'}</div>
                <div class="explain-title">
                    <h3>${this._esc(data.name || data.id || 'Unknown')}</h3>
                    <span class="explain-type">${type.toUpperCase()}</span>
                </div>
                <button class="explain-close" onclick="window.explainability.hide()">\u2715</button>
            </div>
        `;
    }

    _buildReasoning(data) {
        const thoughts = data.thoughts || data.reasoning || [];
        if (thoughts.length === 0) return '';

        const items = thoughts.map(t => `
            <li class="reasoning-step">
                <span class="step-icon">${t.icon || '\u2022'}</span>
                <span class="step-text">${this._esc(t.text || t)}</span>
                ${t.confidence ? `<span class="step-conf">${Math.round(t.confidence * 100)}%</span>` : ''}
            </li>
        `).join('');

        return `
            <div class="explain-section">
                <h4>Reasoning Chain</h4>
                <ul class="reasoning-chain">${items}</ul>
            </div>
        `;
    }

    _buildMetrics(data) {
        const metrics = [
            { label: 'Confidence', value: data.confidence != null ? `${Math.round(data.confidence * 100)}%` : 'N/A', bar: data.confidence },
            { label: 'Model', value: data.model || 'llama-3.1-8b-instruct' },
            { label: 'Duration', value: data.duration != null ? `${(data.duration / 1000).toFixed(1)}s` : 'N/A' },
            { label: 'Tokens Used', value: data.tokens_used || 'N/A' },
            { label: 'Temperature', value: data.temperature || '0.7' },
        ].filter(m => m.value !== 'N/A' || m.bar);

        return `
            <div class="explain-section">
                <h4>Performance</h4>
                <div class="explain-metrics">
                    ${metrics.map(m => `
                        <div class="metric-row">
                            <span class="metric-label">${m.label}</span>
                            ${m.bar != null
                                ? `<div class="metric-bar-wrap"><div class="metric-bar" style="width:${m.bar * 100}%"></div></div>`
                                : `<span class="metric-value">${m.value}</span>`
                            }
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    _buildCapabilities(data) {
        const caps = data.capabilities || [];
        if (caps.length === 0) return '';

        return `
            <div class="explain-section">
                <h4>Capabilities Used</h4>
                <div class="explain-tags">
                    ${caps.map(c => `<span class="explain-tag">${this._esc(c)}</span>`).join('')}
                </div>
            </div>
        `;
    }

    _buildMemories(data) {
        const mems = data.memories || data.retrieved_memory || [];
        if (mems.length === 0) return '';

        return `
            <div class="explain-section">
                <h4>Relevant Memories</h4>
                <div class="explain-memories">
                    ${mems.map(m => `
                        <div class="memory-item">
                            <span class="mem-source">${this._esc(m.source || 'unknown')}</span>
                            <span class="mem-text">${this._esc(m.content || m.text || '')}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    _buildTimeline(data) {
        const events = data.timeline || data.events || [];
        if (events.length === 0) return '';

        const items = events.map(e => `
            <li class="timeline-event">
                <span class="tl-time">${e.time || ''}</span>
                <span class="tl-icon">${e.icon || '\u2022'}</span>
                <span class="tl-text">${this._esc(e.text || e.event_type || '')}</span>
            </li>
        `).join('');

        return `
            <div class="explain-section">
                <h4>Event Timeline</h4>
                <ul class="explain-timeline">${items}</ul>
            </div>
        `;
    }

    _esc(s) {
        const d = document.createElement('div');
        d.textContent = String(s);
        return d.innerHTML;
    }
}

window.ExplainabilityOverlay = ExplainabilityOverlay;
