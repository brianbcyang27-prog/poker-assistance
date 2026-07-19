/**
 * Knowledge Graph Visualization
 * Force-directed graph showing nodes and edges from the memory system.
 * Renders on a canvas overlay that can be toggled on/off.
 */

class KnowledgeGraphViz {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.nodes = [];
        this.edges = [];
        this.running = false;
        this.alpha = 0.5;
        this.selectedNode = null;
        this.hoveredNode = null;
        this.dragging = false;
        this.dragOffset = { x: 0, y: 0 };
        this.transform = { x: 0, y: 0, scale: 1 };
        this._animFrame = null;
        this.visible = false;
        this._nodeRadiusCache = new Map();

        this.typeColors = {
            concept: '#00f0ff',
            note: '#8855cc',
            entity: '#ffaa00',
            conversation: '#00cc66',
            decision: '#ff5577',
            code: '#ff66aa',
            tag: '#5577dd',
        };
    }

    async init() {
        this.canvas = document.getElementById('graph-canvas');
        if (!this.canvas) {
            this.canvas = document.createElement('canvas');
            this.canvas.id = 'graph-canvas';
            this.canvas.style.cssText = `
                position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                z-index: 1000; pointer-events: none; opacity: 0;
                transition: opacity 0.5s ease;
            `;
            document.body.appendChild(this.canvas);
        }
        this.ctx = this.canvas.getContext('2d');
        this._resize();
        this._boundResize = () => this._resize();
        this._boundMouseDown = (e) => this._onMouseDown(e);
        this._boundMouseMove = (e) => this._onMouseMove(e);
        this._boundMouseUp = () => this._onMouseUp();
        this._boundWheel = (e) => this._onWheel(e);
        window.addEventListener('resize', this._boundResize);
        this.canvas.addEventListener('mousedown', this._boundMouseDown);
        this.canvas.addEventListener('mousemove', this._boundMouseMove);
        this.canvas.addEventListener('mouseup', this._boundMouseUp);
        this.canvas.addEventListener('wheel', this._boundWheel);
    }

    destroy() {
        this._stop();
        if (this._boundResize) window.removeEventListener('resize', this._boundResize);
        if (this._boundMouseDown) this.canvas.removeEventListener('mousedown', this._boundMouseDown);
        if (this._boundMouseMove) this.canvas.removeEventListener('mousemove', this._boundMouseMove);
        if (this._boundMouseUp) this.canvas.removeEventListener('mouseup', this._boundMouseUp);
        if (this._boundWheel) this.canvas.removeEventListener('wheel', this._boundWheel);
        this._hideNodeInfo();
    }

    _resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
        this.transform.x = window.innerWidth / 2;
        this.transform.y = window.innerHeight / 2;
    }

    async toggle() {
        if (this.visible) {
            this.hide();
        } else {
            await this.show();
        }
    }

    async show() {
        this.visible = true;
        this.canvas.style.opacity = '1';
        this.canvas.style.pointerEvents = 'auto';
        await this._loadData();
        if (!this.running) this._start();
    }

    hide() {
        this.visible = false;
        this.canvas.style.opacity = '0';
        this.canvas.style.pointerEvents = 'none';
        this._stop();
    }

    async _loadData() {
        try {
            const res = await fetch('/api/memory/graph?limit=300');
            const data = await res.json();
            this.nodes = (data.nodes || []).map((n, i) => ({
                ...n,
                x: (Math.random() - 0.5) * 600,
                y: (Math.random() - 0.5) * 600,
                vx: 0,
                vy: 0,
                fx: null,
                fy: null,
                index: i,
            }));
            this.edges = (data.edges || []).map(e => ({
                ...e,
                sourceNode: null,
                targetNode: null,
            }));
            // Link edges to node objects
            const idMap = {};
            this.nodes.forEach(n => idMap[n.id] = n);
            this.edges.forEach(e => {
                e.sourceNode = idMap[e.source];
                e.targetNode = idMap[e.target];
            });
            this.edges = this.edges.filter(e => e.sourceNode && e.targetNode);
            this.alpha = 0.8;
            this._nodeRadiusCache.clear();
        } catch (err) {
            console.warn('Failed to load graph data:', err);
        }
    }

    _start() {
        this.running = true;
        const tick = () => {
            if (!this.running) return;
            this._step();
            this._draw();
            this._animFrame = requestAnimationFrame(tick);
        };
        tick();
    }

    _stop() {
        this.running = false;
        if (this._animFrame) cancelAnimationFrame(this._animFrame);
    }

    _step() {
        const alphaDecay = 0.005;
        this.alpha = Math.max(0.01, this.alpha - alphaDecay);

        const cx = 0, cy = 0;
        const repulsion = 800;
        const attraction = 0.005;
        const centering = 0.01;
        const damping = 0.85;

        // Center gravity
        this.nodes.forEach(n => {
            n.vx += (cx - n.x) * centering;
            n.vy += (cy - n.y) * centering;
        });

        // Repulsion (Barnes-Hut simplified: just pairwise for small graphs)
        for (let i = 0; i < this.nodes.length; i++) {
            for (let j = i + 1; j < this.nodes.length; j++) {
                const a = this.nodes[i], b = this.nodes[j];
                let dx = b.x - a.x, dy = b.y - a.y;
                let dist = Math.sqrt(dx * dx + dy * dy) || 1;
                let force = repulsion / (dist * dist);
                force = Math.min(force, 5);
                const fx = (dx / dist) * force * this.alpha;
                const fy = (dy / dist) * force * this.alpha;
                a.vx -= fx; a.vy -= fy;
                b.vx += fx; b.vy += fy;
            }
        }

        // Attraction along edges
        this.edges.forEach(e => {
            if (!e.sourceNode || !e.targetNode) return;
            let dx = e.targetNode.x - e.sourceNode.x;
            let dy = e.targetNode.y - e.sourceNode.y;
            let dist = Math.sqrt(dx * dx + dy * dy) || 1;
            let force = (dist - 100) * attraction * this.alpha;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            e.sourceNode.vx += fx; e.sourceNode.vy += fy;
            e.targetNode.vx -= fx; e.targetNode.vy -= fy;
        });

        // Apply velocity
        this.nodes.forEach(n => {
            if (n.fx != null) { n.x = n.fx; n.vx = 0; }
            else { n.vx *= damping; n.x += n.vx; }
            if (n.fy != null) { n.y = n.fy; n.vy = 0; }
            else { n.vy *= damping; n.y += n.vy; }
        });
    }

    _draw() {
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;
        ctx.clearRect(0, 0, w, h);

        ctx.save();
        ctx.translate(this.transform.x, this.transform.y);
        ctx.scale(this.transform.scale, this.transform.scale);

        // Draw edges
        this.edges.forEach(e => {
            if (!e.sourceNode || !e.targetNode) return;
            ctx.beginPath();
            ctx.moveTo(e.sourceNode.x, e.sourceNode.y);
            ctx.lineTo(e.targetNode.x, e.targetNode.y);
            const isHighlighted = this.selectedNode &&
                (e.source === this.selectedNode.id || e.target === this.selectedNode.id);
            ctx.strokeStyle = isHighlighted ? 'rgba(0, 212, 255, 0.6)' : 'rgba(100, 140, 180, 0.15)';
            ctx.lineWidth = isHighlighted ? 2 : 1;
            ctx.stroke();
        });

        // Draw nodes
        this.nodes.forEach(n => {
            const color = this.typeColors[n.type] || '#ffffff';
            const radius = this._nodeRadius(n);
            const isHovered = this.hoveredNode === n;
            const isSelected = this.selectedNode === n;
            const isConnected = this.selectedNode && this._isConnected(n, this.selectedNode);

            ctx.beginPath();
            ctx.arc(n.x, n.y, radius, 0, Math.PI * 2);

            // Glow
            if (isHovered || isSelected) {
                ctx.shadowColor = color;
                ctx.shadowBlur = 20;
            } else if (isConnected) {
                ctx.shadowColor = color;
                ctx.shadowBlur = 10;
            } else {
                ctx.shadowBlur = 0;
            }

            ctx.fillStyle = isSelected ? '#ffffff' :
                           isHovered ? color :
                           isConnected ? color :
                           this._alpha(color, 0.7);
            ctx.fill();
            ctx.shadowBlur = 0;

            // Label
            if (radius > 4 || isHovered || isSelected || isConnected) {
                ctx.fillStyle = isSelected ? color : 'rgba(200, 220, 240, 0.8)';
                ctx.font = `${isSelected || isHovered ? '12px' : '10px'} "Inter", sans-serif`;
                ctx.textAlign = 'center';
                const label = n.label.length > 20 ? n.label.slice(0, 18) + '..' : n.label;
                ctx.fillText(label, n.x, n.y + radius + 14);
            }
        });

        ctx.restore();
    }

    _nodeRadius(n) {
        const cached = this._nodeRadiusCache.get(n.id);
        if (cached !== undefined) return cached;
        const base = n.type === 'note' ? 7 : n.type === 'decision' ? 6 : 5;
        const connectionBonus = this.edges.filter(
            e => e.source === n.id || e.target === n.id
        ).length * 0.5;
        const radius = Math.min(base + connectionBonus, 15);
        this._nodeRadiusCache.set(n.id, radius);
        return radius;
    }

    _isConnected(a, b) {
        return this.edges.some(e =>
            (e.source === a.id && e.target === b.id) ||
            (e.source === b.id && e.target === a.id)
        );
    }

    _alpha(hex, a) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r},${g},${b},${a})`;
    }

    _screenToWorld(sx, sy) {
        return {
            x: (sx - this.transform.x) / this.transform.scale,
            y: (sy - this.transform.y) / this.transform.scale,
        };
    }

    _nodeAt(sx, sy) {
        const { x, y } = this._screenToWorld(sx, sy);
        for (let i = this.nodes.length - 1; i >= 0; i--) {
            const n = this.nodes[i];
            const r = this._nodeRadius(n);
            if (Math.abs(n.x - x) < r + 5 && Math.abs(n.y - y) < r + 5) return n;
        }
        return null;
    }

    _onMouseDown(e) {
        const node = this._nodeAt(e.clientX, e.clientY);
        if (node) {
            this.selectedNode = node;
            this.dragging = true;
            const world = this._screenToWorld(e.clientX, e.clientY);
            this.dragOffset.x = node.x - world.x;
            this.dragOffset.y = node.y - world.y;
            this._showNodeInfo(node);
        } else {
            this.selectedNode = null;
            this._hideNodeInfo();
            this.dragging = true;
            this.dragOffset.x = e.clientX - this.transform.x;
            this.dragOffset.y = e.clientY - this.transform.y;
        }
    }

    _onMouseMove(e) {
        if (this.dragging) {
            if (this.selectedNode) {
                const world = this._screenToWorld(e.clientX, e.clientY);
                this.selectedNode.fx = world.x + this.dragOffset.x;
                this.selectedNode.fy = world.y + this.dragOffset.y;
                this.selectedNode.x = this.selectedNode.fx;
                this.selectedNode.y = this.selectedNode.fy;
            } else {
                this.transform.x = e.clientX - this.dragOffset.x;
                this.transform.y = e.clientY - this.dragOffset.y;
            }
        } else {
            this.hoveredNode = this._nodeAt(e.clientX, e.clientY);
            this.canvas.style.cursor = this.hoveredNode ? 'pointer' : 'grab';
        }
    }

    _onMouseUp() {
        this.dragging = false;
        if (this.selectedNode) {
            this.selectedNode.fx = null;
            this.selectedNode.fy = null;
        }
    }

    _onWheel(e) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        const world = this._screenToWorld(e.clientX, e.clientY);
        this.transform.scale *= delta;
        this.transform.scale = Math.max(0.2, Math.min(5, this.transform.scale));
        this.transform.x = e.clientX - world.x * this.transform.scale;
        this.transform.y = e.clientY - world.y * this.transform.scale;
    }

    _showNodeInfo(node) {
        let panel = document.getElementById('graph-info-panel');
        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'graph-info-panel';
            panel.style.cssText = `
                position: fixed; bottom: 80px; right: 20px; width: 320px;
                background: rgba(5, 11, 20, 0.95); backdrop-filter: blur(20px);
                border: 1px solid rgba(0, 240, 255, 0.15); border-radius: 12px;
                padding: 16px; z-index: 1001; color: rgba(180, 230, 245, 0.9);
                font-family: 'Inter', sans-serif; font-size: 13px;
                box-shadow: 0 0 30px rgba(0, 240, 255, 0.05);
                animation: panel-slide-in 0.3s ease;
            `;
            document.body.appendChild(panel);
        }
        const connections = this.edges.filter(e => e.source === node.id || e.target === node.id);
        const connList = connections.slice(0, 8).map(e => {
            const otherId = e.source === node.id ? e.target : e.source;
            const other = this.nodes.find(n => n.id === otherId);
            return `<span style="color:${this.typeColors[other?.type] || '#fff'}">${other?.label || otherId}</span>
                    <span style="opacity:0.5;font-size:11px"> ${e.relation}</span>`;
        }).join('<br>');

        panel.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                <span style="color:${this.typeColors[node.type]};font-weight:600">${node.label}</span>
                <span style="font-size:10px;padding:2px 6px;border-radius:4px;background:rgba(0,212,255,0.1);color:rgba(0,212,255,0.7)">${node.type}</span>
            </div>
            ${node.content ? `<div style="font-size:12px;opacity:0.7;margin-bottom:8px;line-height:1.4">${node.content.slice(0, 200)}</div>` : ''}
            <div style="font-size:11px;opacity:0.5;margin-bottom:4px">${connections.length} connections</div>
            <div style="font-size:12px;line-height:1.6">${connList || '<span style="opacity:0.4">No connections</span>'}</div>
        `;
    }

    _hideNodeInfo() {
        const panel = document.getElementById('graph-info-panel');
        if (panel) panel.remove();
    }

    async refresh() {
        await this._loadData();
    }
}

window.KnowledgeGraphViz = KnowledgeGraphViz;
