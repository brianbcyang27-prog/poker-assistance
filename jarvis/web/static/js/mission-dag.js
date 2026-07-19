/**
 * Mission DAG Visualizer — v3.2.0
 *
 * Renders a live DAG (directed acyclic graph) of mission tasks
 * on the main page. Shows task dependencies, status, and
 * parallel execution paths.
 *
 * Uses SVG with animated edges and status-colored nodes.
 */

class MissionDAG {
    constructor(container) {
        this.container = container;
        this.svg = null;
        this.nodes = new Map();
        this.edges = [];
        this._pollId = null;
        this._width = 0;
        this._height = 0;
    }

    init() {
        if (!this.container) return;

        this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        this.svg.setAttribute('class', 'mission-dag-svg');
        this.svg.style.width = '100%';
        this.svg.style.height = '100%';
        this.container.appendChild(this.svg);

        // Defs for gradients and arrows
        const defs = this._createEl('defs');
        defs.innerHTML = `
            <marker id="dag-arrow" viewBox="0 0 10 10" refX="9" refY="5"
                    markerWidth="6" markerHeight="6" orient="auto">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--color-primary)"/>
            </marker>
            <linearGradient id="dag-edge-active" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stop-color="var(--color-primary)" stop-opacity="0.3"/>
                <stop offset="100%" stop-color="var(--color-primary)" stop-opacity="1"/>
            </linearGradient>
            <filter id="dag-glow">
                <feGaussianBlur stdDeviation="3" result="blur"/>
                <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
        `;
        this.svg.appendChild(defs);

        // Layer groups
        this._edgeGroup = this._createEl('g', { class: 'dag-edges' });
        this._nodeGroup = this._createEl('g', { class: 'dag-nodes' });
        this.svg.appendChild(this._edgeGroup);
        this.svg.appendChild(this._nodeGroup);

        this._resize();
        window.addEventListener('resize', () => this._resize());
    }

    _createEl(tag, attrs = {}) {
        const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
        for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
        return el;
    }

    _resize() {
        if (!this.container || !this.svg) return;
        this._width = this.container.clientWidth;
        this._height = this.container.clientHeight;
        this.svg.setAttribute('viewBox', `0 0 ${this._width} ${this._height}`);
    }

    /**
     * Update DAG with mission data from /api/system/dag
     */
    async update() {
        try {
            const res = await fetch('/api/system/dag');
            if (!res.ok) return;
            const data = await res.json();
            this.render(data);
        } catch (_) {}
    }

    /**
     * Render DAG from structured data
     * data = { nodes: [{id, name, status, layer, agent}], edges: [{from, to}] }
     */
    render(data) {
        if (!this.svg) return;

        this._edgeGroup.innerHTML = '';
        this._nodeGroup.innerHTML = '';
        this.nodes.clear();
        this.edges = data.edges || [];

        const nodes = data.nodes || [];
        if (nodes.length === 0) {
            this._renderEmpty();
            return;
        }

        // Layout: arrange by layer (topological order)
        const layers = {};
        for (const node of nodes) {
            const layer = node.layer || 0;
            if (!layers[layer]) layers[layer] = [];
            layers[layer].push(node);
        }

        const layerKeys = Object.keys(layers).map(Number).sort((a, b) => a - b);
        const maxLayer = layerKeys.length;
        const nodeR = 22;
        const vSpacing = this._height / (maxLayer + 1);

        // Position nodes
        for (const layerIdx of layerKeys) {
            const layerNodes = layers[layerIdx];
            const hSpacing = this._width / (layerNodes.length + 1);
            for (let i = 0; i < layerNodes.length; i++) {
                const node = layerNodes[i];
                node._x = hSpacing * (i + 1);
                node._y = vSpacing * (layerIdx + 1);
                node._r = nodeR;
                this.nodes.set(node.id, node);
            }
        }

        // Draw edges
        for (const edge of this.edges) {
            const from = this.nodes.get(edge.from);
            const to = this.nodes.get(edge.to);
            if (!from || !to) continue;

            const isActive = this._isEdgeActive(from, to);
            const line = this._createEl('line', {
                x1: from._x, y1: from._y + nodeR,
                x2: to._x, y2: to._y - nodeR,
                stroke: isActive ? 'url(#dag-edge-active)' : 'var(--color-line)',
                'stroke-width': isActive ? 2 : 1,
                'stroke-dasharray': isActive ? 'none' : '4,4',
                'marker-end': 'url(#dag-arrow)',
                class: isActive ? 'dag-edge-active' : 'dag-edge',
            });
            this._edgeGroup.appendChild(line);
        }

        // Draw nodes
        for (const node of nodes) {
            const g = this._createEl('g', {
                transform: `translate(${node._x}, ${node._y})`,
                class: `dag-node dag-node-${node.status || 'pending'}`,
            });

            // Circle
            const circle = this._createEl('circle', {
                r: nodeR,
                fill: this._nodeColor(node.status),
                stroke: this._nodeStroke(node.status),
                'stroke-width': 2,
                filter: node.status === 'active' ? 'url(#dag-glow)' : 'none',
            });
            g.appendChild(circle);

            // Label
            const text = this._createEl('text', {
                y: nodeR + 16,
                'text-anchor': 'middle',
                fill: 'var(--color-text-secondary)',
                'font-size': '11',
            });
            text.textContent = this._truncate(node.name || node.id, 12);
            g.appendChild(text);

            // Status icon
            const icon = this._createEl('text', {
                y: 5,
                'text-anchor': 'middle',
                fill: '#fff',
                'font-size': '14',
            });
            icon.textContent = this._statusIcon(node.status);
            g.appendChild(icon);

            this._nodeGroup.appendChild(g);
        }
    }

    _renderEmpty() {
        const text = this._createEl('text', {
            x: this._width / 2, y: this._height / 2,
            'text-anchor': 'middle',
            fill: 'var(--color-text-muted)',
            'font-size': '14',
        });
        text.textContent = 'No active missions';
        this._nodeGroup.appendChild(text);
    }

    _isEdgeActive(from, to) {
        const activeStatuses = ['active', 'running', 'working'];
        return activeStatuses.includes(from.status) || activeStatuses.includes(to.status);
    }

    _nodeColor(status) {
        const map = {
            active: '#00f0ff22',
            running: '#00f0ff22',
            working: '#ffaa0022',
            completed: '#00cc6622',
            failed: '#ff336622',
            pending: '#ffffff08',
        };
        return map[status] || '#ffffff08';
    }

    _nodeStroke(status) {
        const map = {
            active: '#00f0ff',
            running: '#00f0ff',
            working: '#ffaa00',
            completed: '#00cc66',
            failed: '#ff3366',
            pending: '#333',
        };
        return map[status] || '#333';
    }

    _statusIcon(status) {
        const map = {
            active: '\u25b6',
            running: '\u25b6',
            working: '\u2699',
            completed: '\u2714',
            failed: '\u274c',
            pending: '\u25cb',
        };
        return map[status] || '\u25cb';
    }

    _truncate(s, max) {
        return s.length > max ? s.slice(0, max) + '\u2026' : s;
    }

    /**
     * Start polling for DAG updates
     */
    startPolling(intervalMs = 5000) {
        this.update();
        this._pollId = setInterval(() => this.update(), intervalMs);
    }

    stopPolling() {
        if (this._pollId) {
            clearInterval(this._pollId);
            this._pollId = null;
        }
    }

    destroy() {
        this.stopPolling();
        if (this.svg) this.svg.remove();
    }
}

window.MissionDAG = MissionDAG;
