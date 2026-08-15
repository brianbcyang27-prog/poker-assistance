/**
 * KnowledgeGraph — v9.0.0 M2 Project Intelligence.
 * SVG node-link graph of project knowledge, colored by node_type.
 */
class KnowledgeGraph {
    constructor() {
        this.initialized = false;
        this.container = null;
        this.projectId = null;
        this.nodes = [];
        this.edges = [];
        this._nodeTypes = {
            concept: 'var(--dept-engineering)',
            domain: 'var(--dept-education)',
            decision: 'var(--dept-finance)',
            artifact: 'var(--dept-studio)',
            default: 'var(--color-brand-secondary)',
        };
    }

    init(container) {
        this.container = container;
        this.initialized = true;
        this._bind();
    }

    _bind() {
        const sel = this.container.querySelector('#mv-knowledge-project');
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
            const sel = document.getElementById('mv-knowledge-project');
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
        const body = document.getElementById('mv-knowledge-body');
        const empty = document.getElementById('mv-knowledge-empty');
        if (body) body.classList.remove('hidden');
        if (empty) empty.classList.add('hidden');
        await this._loadGraph();
    }

    async _loadGraph() {
        try {
            const res = await fetch(`/api/projects/${this.projectId}/knowledge`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            this.nodes = data.nodes || [];
            this.edges = [];
            for (const node of this.nodes) {
                for (const link of node.links || []) {
                    this.edges.push({ from: link, to: node.id });
                }
            }
            this._render();
            this._updateRightPanel();
        } catch (e) {
            const canvas = document.getElementById('mv-knowledge-graph');
            if (canvas) canvas.innerHTML = `<div class="mv-empty-state">Failed: ${this._esc(e.message)}</div>`;
        }
    }

    _render() {
        const canvas = document.getElementById('mv-knowledge-graph');
        if (!canvas) return;
        canvas.innerHTML = '';
        if (this.nodes.length === 0) {
            canvas.innerHTML = '<div class="mv-empty-state">No knowledge nodes yet — add knowledge from project missions</div>';
            return;
        }

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'mv-graph-svg');
        svg.style.width = '100%';
        svg.style.height = '100%';

        const width = canvas.clientWidth || 600;
        const height = canvas.clientHeight || 400;
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

        const positions = this._layout(width, height);
        const byId = {};
        for (const node of this.nodes) byId[node.id] = node;

        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        defs.innerHTML = `
            <marker id="kg-arrow" viewBox="0 0 10 10" refX="9" refY="5"
                    markerWidth="5" markerHeight="5" orient="auto">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--color-border-emphasis)"/>
            </marker>`;
        svg.appendChild(defs);

        const edgeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        for (const edge of this.edges) {
            const from = positions[edge.from];
            const to = positions[edge.to];
            if (!from || !to) continue;
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', from.x);
            line.setAttribute('y1', from.y);
            line.setAttribute('x2', to.x);
            line.setAttribute('y2', to.y);
            line.setAttribute('class', 'mv-graph-edge');
            line.setAttribute('marker-end', 'url(#kg-arrow)');
            edgeGroup.appendChild(line);
        }
        svg.appendChild(edgeGroup);

        const nodeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        for (const node of this.nodes) {
            const pos = positions[node.id];
            if (!pos) continue;
            const color = this._nodeTypes[node.node_type] || this._nodeTypes.default;
            const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            g.setAttribute('transform', `translate(${pos.x}, ${pos.y})`);
            g.setAttribute('class', 'mv-graph-node');

            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('r', 18);
            circle.setAttribute('fill', color);
            circle.setAttribute('fill-opacity', '0.18');
            circle.setAttribute('stroke', color);
            circle.setAttribute('stroke-width', '1.5');
            g.appendChild(circle);

            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('y', '24');
            label.setAttribute('text-anchor', 'middle');
            label.setAttribute('fill', 'var(--color-text-secondary)');
            label.setAttribute('font-size', '10');
            label.textContent = this._truncate(node.label || node.id, 16);
            g.appendChild(label);

            g.addEventListener('click', () => this._showDetail(node));
            nodeGroup.appendChild(g);
        }
        svg.appendChild(nodeGroup);
        canvas.appendChild(svg);
    }

    _layout(width, height) {
        const positions = {};
        const n = this.nodes.length;
        const cx = width / 2;
        const cy = height / 2;
        const radius = Math.min(width, height) / 2 - 60;
        this.nodes.forEach((node, i) => {
            if (n === 1) {
                positions[node.id] = { x: cx, y: cy };
            } else {
                const angle = (2 * Math.PI * i) / n - Math.PI / 2;
                positions[node.id] = {
                    x: cx + radius * Math.cos(angle),
                    y: cy + radius * Math.sin(angle),
                };
            }
        });
        return positions;
    }

    _showDetail(node) {
        const detail = document.getElementById('mv-knowledge-detail');
        if (!detail) return;
        detail.classList.remove('hidden');
        const links = (node.links || []).map(id => {
            const target = this.nodes.find(n => n.id === id);
            return target ? `<div class="mv-list-item"><span class="mv-list-item-title">${this._esc(target.label)}</span></div>` : '';
        }).join('');
        detail.innerHTML = `
            <div class="mv-panel-title">${this._esc(node.node_type)}</div>
            <h4>${this._esc(node.label)}</h4>
            <p>${this._esc(node.content || 'No content')}</p>
            ${links ? `<div class="mv-panel-title">Linked</div>${links}` : ''}`;
        this._updateRightPanel(node);
    }

    _updateRightPanel(node) {
        const summary = document.getElementById('knowledge-summary');
        if (!summary) return;
        if (!node) {
            summary.innerHTML = '<span class="right-empty-text">No knowledge loaded</span>';
            return;
        }
        summary.innerHTML = `
            <div class="mv-right-row"><span>Node</span><strong>${this._esc(node.label)}</strong></div>
            <div class="mv-right-row"><span>Type</span><strong>${this._esc(node.node_type)}</strong></div>
            <div class="mv-right-row"><span>Links</span><strong>${(node.links || []).length}</strong></div>`;
    }

    _showEmpty() {
        const body = document.getElementById('mv-knowledge-body');
        const empty = document.getElementById('mv-knowledge-empty');
        if (body) body.classList.add('hidden');
        if (empty) empty.classList.remove('hidden');
        this._updateRightPanel(null);
    }

    _truncate(s, max) {
        return s.length > max ? s.slice(0, max) + '…' : s;
    }

    _esc(str) {
        const div = document.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }
}

window.KnowledgeGraph = new KnowledgeGraph();
