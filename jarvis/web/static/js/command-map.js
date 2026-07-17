/**
 * JARVIS Agent Command Map
 * Interactive visualization of the JARVIS hierarchy
 */

class CommandMap {
    constructor() {
        this.svg = document.getElementById('hierarchy-svg');
        this.bgCanvas = document.getElementById('bg-canvas');
        this.bgCtx = this.bgCanvas.getContext('2d');
        
        this.nodes = new Map();
        this.agentData = new Map(); // Store full agent data
        this.energyLines = [];
        this.flowParticles = [];
        this.particles = [];
        
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        
        this.centerX = this.width / 2;
        this.centerY = this.height / 2 - 40;
        
        // Pan and zoom
        this.viewBox = { x: 0, y: 0, w: this.width, h: this.height };
        this.zoom = 1;
        this.pan = { x: 0, y: 0 };
        this.isDragging = false;
        this.dragStart = { x: 0, y: 0 };
        this.dragPanStart = { x: 0, y: 0 };
        
        this.hierarchy = null;
        this.ws = null;
        this.animationFrame = null;
        
        this.selectedAgent = null;
        
        this.init();
    }
    
    init() {
        this.resizeCanvas();
        this.initParticles();
        this.connectWebSocket();
        this.setupInteraction();
        this.animate();
        
        window.addEventListener('resize', () => this.resizeCanvas());
        
        // Start fetching data
        this.fetchHierarchy();
    }
    
    resizeCanvas() {
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.centerX = this.width / 2;
        this.centerY = this.height / 2 - 40;
        
        this.bgCanvas.width = this.width;
        this.bgCanvas.height = this.height;
        this.updateViewBox();
    }
    
    updateViewBox() {
        const w = this.width / this.zoom;
        const h = this.height / this.zoom;
        const x = this.pan.x - w / 2;
        const y = this.pan.y - h / 2;
        this.svg.setAttribute('viewBox', `${x} ${y} ${w} ${h}`);
    }
    
    // ============ INTERACTION (Pan, Zoom, Click) ============
    
    setupInteraction() {
        // Mouse wheel zoom
        this.svg.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            this.zoom = Math.max(0.3, Math.min(3, this.zoom * delta));
            this.updateViewBox();
        }, { passive: false });
        
        // Drag to pan
        this.svg.addEventListener('mousedown', (e) => {
            if (e.target.closest('.king-node, .worker-node, .jarvis-node')) return;
            this.isDragging = true;
            this.dragStart = { x: e.clientX, y: e.clientY };
            this.dragPanStart = { ...this.pan };
            this.svg.style.cursor = 'grabbing';
        });
        
        window.addEventListener('mousemove', (e) => {
            if (!this.isDragging) return;
            const dx = (e.clientX - this.dragStart.x) / this.zoom;
            const dy = (e.clientY - this.dragStart.y) / this.zoom;
            this.pan.x = this.dragPanStart.x - dx;
            this.pan.y = this.dragPanStart.y - dy;
            this.updateViewBox();
        });
        
        window.addEventListener('mouseup', () => {
            this.isDragging = false;
            this.svg.style.cursor = 'grab';
        });
        
        // Set default cursor
        this.svg.style.cursor = 'grab';
        
        // Click to select agent
        this.svg.addEventListener('click', (e) => {
            const node = e.target.closest('.king-node, .worker-node, .jarvis-node');
            if (node) {
                const cardId = node.dataset.cardId;
                if (cardId && this.agentData.has(cardId)) {
                    this.selectAgent(cardId);
                }
            }
        });
        
        // Escape to deselect
        window.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.deselectAgent();
            }
        });
    }
    
    // ============ PARTICLES ============
    
    initParticles() {
        this.particles = [];
        for (let i = 0; i < 100; i++) {
            this.particles.push({
                x: Math.random() * this.width,
                y: Math.random() * this.height,
                vx: (Math.random() - 0.5) * 0.3,
                vy: (Math.random() - 0.5) * 0.3,
                size: Math.random() * 2 + 0.5,
                alpha: Math.random() * 0.3 + 0.1,
            });
        }
    }
    
    drawParticles() {
        this.bgCtx.clearRect(0, 0, this.width, this.height);
        
        // Draw background gradient
        const gradient = this.bgCtx.createRadialGradient(
            this.centerX, this.centerY, 0,
            this.centerX, this.centerY, Math.max(this.width, this.height) / 2
        );
        gradient.addColorStop(0, '#0a0f1e');
        gradient.addColorStop(0.5, '#050a14');
        gradient.addColorStop(1, '#000510');
        this.bgCtx.fillStyle = gradient;
        this.bgCtx.fillRect(0, 0, this.width, this.height);
        
        // Draw and update particles
        this.bgCtx.fillStyle = '#00d4ff';
        for (const p of this.particles) {
            p.x += p.vx;
            p.y += p.vy;
            
            if (p.x < 0) p.x = this.width;
            if (p.x > this.width) p.x = 0;
            if (p.y < 0) p.y = this.height;
            if (p.y > this.height) p.y = 0;
            
            this.bgCtx.globalAlpha = p.alpha;
            this.bgCtx.beginPath();
            this.bgCtx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            this.bgCtx.fill();
        }
        this.bgCtx.globalAlpha = 1;
    }
    
    // ============ WEBSOCKET ============
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/agents`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === 'status') {
                this.updateHierarchy(msg.data);
            }
        };
        
        this.ws.onclose = () => {
            setTimeout(() => this.connectWebSocket(), 3000);
        };
        
        this.ws.onerror = () => {
            this.ws.close();
        };
    }
    
    async fetchHierarchy() {
        try {
            const res = await fetch('/api/agents/hierarchy');
            this.hierarchy = await res.json();
            this.renderHierarchy();
        } catch (e) {
            console.log('Waiting for hierarchy data...');
            setTimeout(() => this.fetchHierarchy(), 2000);
        }
    }
    
    updateHierarchy(data) {
        if (data.card_id && !data.jarvis) {
            const kingsArray = [];
            if (data.kings) {
                for (const [kingId, kingData] of Object.entries(data.kings)) {
                    const workersArray = [];
                    if (kingData.workers) {
                        for (const [workerId, workerData] of Object.entries(kingData.workers)) {
                            workersArray.push(workerData);
                        }
                    }
                    kingsArray.push({ ...kingData, workers: workersArray });
                }
            }
            this.hierarchy = {
                jarvis: { card_id: data.card_id, name: data.name, state: data.state },
                kings: kingsArray
            };
        } else {
            this.hierarchy = data;
        }
        
        this.renderHierarchy();
        this.updateStatusOverlay();
        
        // Update selected agent panel if open
        if (this.selectedAgent && this.agentData.has(this.selectedAgent)) {
            this.updateDetailPanel(this.agentData.get(this.selectedAgent));
        }
    }
    
    // ============ HIERARCHY RENDERING ============
    
    renderHierarchy() {
        if (!this.hierarchy) return;
        
        const nodesGroup = document.getElementById('nodes');
        const linesGroup = document.getElementById('energy-lines');
        const flowGroup = document.getElementById('flow-particles');
        
        if (!nodesGroup || !linesGroup || !flowGroup) return;
        
        nodesGroup.innerHTML = '';
        linesGroup.innerHTML = '';
        flowGroup.innerHTML = '';
        this.energyLines = [];
        this.agentData.clear();
        
        const jarvis = this.hierarchy.jarvis;
        const kings = this.hierarchy.kings || [];
        
        if (!jarvis) return;
        
        // Store JARVIS data
        this.agentData.set('J', {
            card_id: 'J',
            name: 'JARVIS',
            state: jarvis.state || 'idle',
            role: 'Chief Executive AI',
            title: 'JARVIS',
            personality: 'Professional, efficient, slightly witty. Proactive in suggesting solutions.',
            abilities: [
                'Intent analysis and task delegation',
                'Multi-agent coordination',
                'Natural language understanding',
                'Planning and strategy',
                'Result synthesis and communication'
            ],
            thinking: this.getThinkingProcess('J', jarvis.state),
            currentTask: jarvis.state !== 'idle' ? 'Processing user request...' : 'Awaiting instructions',
            suit: null,
            type: 'jarvis'
        });
        
        // Draw JARVIS node
        this.drawJarvisNode(nodesGroup, jarvis);
        
        // Calculate positions for kings
        const kingCount = kings.length;
        const kingRadius = Math.min(this.width * 0.3, 350);
        const kingStartAngle = -Math.PI / 2;
        
        kings.forEach((king, i) => {
            const angle = kingStartAngle + (i * 2 * Math.PI) / kingCount;
            const kx = this.centerX + Math.cos(angle) * kingRadius;
            const ky = this.centerY + Math.sin(angle) * kingRadius;
            
            // Store king data
            const kingAbilities = this.getKingAbilities(king.suit);
            this.agentData.set(king.card_id, {
                ...king,
                role: 'King',
                abilities: kingAbilities,
                thinking: this.getThinkingProcess(king.card_id, king.state),
                currentTask: king.state !== 'idle' ? `Managing ${king.name} operations...` : 'Awaiting delegation from JARVIS',
                type: 'king'
            });
            
            // Draw energy line from JARVIS to King
            this.drawEnergyLine(linesGroup, this.centerX, this.centerY, kx, ky, king.suit);
            
            // Draw King node
            this.drawKingNode(nodesGroup, king, kx, ky);
            
            // Draw worker nodes
            const workers = king.workers || [];
            const workerCount = workers.length;
            const workerRadius = Math.min(this.width * 0.15, 150);
            const workerStartAngle = angle - Math.PI / 3;
            const workerSpread = (2 * Math.PI) / 3;
            
            workers.forEach((worker, j) => {
                const wAngle = workerStartAngle + (j * workerSpread) / Math.max(workerCount - 1, 1);
                const wx = kx + Math.cos(wAngle) * workerRadius;
                const wy = ky + Math.sin(wAngle) * workerRadius;
                
                // Store worker data
                const workerAbilities = this.getWorkerAbilities(worker.card_id, king.suit);
                this.agentData.set(worker.card_id, {
                    ...worker,
                    suit: king.suit,
                    role: 'Worker',
                    abilities: workerAbilities,
                    thinking: this.getThinkingProcess(worker.card_id, worker.state),
                    currentTask: worker.state !== 'idle' ? `Executing ${worker.name} task...` : `Standing by for ${king.name} orders`,
                    type: 'worker'
                });
                
                // Draw energy line from King to Worker
                this.drawEnergyLine(linesGroup, kx, ky, wx, wy, king.suit, true);
                
                // Draw Worker node
                this.drawWorkerNode(nodesGroup, worker, wx, wy, king.suit);
            });
        });
    }
    
    getThinkingProcess(cardId, state) {
        if (state === 'idle') return 'Awaiting input...';
        if (state === 'thinking') return 'Analyzing request and planning approach...';
        if (state === 'planning') return 'Breaking down task into subtasks...';
        if (state === 'working') return 'Actively processing and generating output...';
        if (state === 'reviewing') return 'Evaluating results for quality and accuracy...';
        return 'Processing...';
    }
    
    getKingAbilities(suit) {
        const abilities = {
            spades: [
                'Software architecture design',
                'Code quality enforcement',
                'Team assembly and delegation',
                'Technical decision making',
                'Review and approval of work'
            ],
            hearts: [
                'Calendar management',
                'Email drafting and filtering',
                'Task prioritization',
                'Schedule coordination',
                'Personal productivity'
            ],
            diamonds: [
                'Web research and analysis',
                'Documentation review',
                'Fact verification',
                'Source credibility assessment',
                'Information synthesis'
            ],
            clubs: [
                'File system operations',
                'Terminal command execution',
                'Application management',
                'System security review',
                'Resource monitoring'
            ]
        };
        return abilities[suit] || [];
    }
    
    getWorkerAbilities(cardId, suit) {
        const rank = cardId?.replace(/[♠♥♦♣]/, '') || '';
        
        const workerAbilities = {
            '♠Q': ['System design', 'Architecture patterns', 'Code review', 'Technical specifications'],
            '♠J': ['API development', 'Database design', 'Server logic', 'Authentication'],
            '♠10': ['UI/UX design', 'HTML/CSS/JS', 'Responsive layouts', 'Animations'],
            '♠9': ['React components', 'State management', 'Performance optimization', 'Hooks'],
            '♠8': ['Python development', 'FastAPI/Django', 'Async patterns', 'Data processing'],
            '♠7': ['Unit testing', 'Integration tests', 'Test automation', 'TDD'],
            '♠6': ['Technical writing', 'API documentation', 'User guides', 'README files'],
            '♠5': ['WCAG compliance', 'Screen reader support', 'Keyboard navigation', 'ARIA'],
            '♥Q': ['Schedule management', 'Meeting planning', 'Time optimization', 'Reminders'],
            '♥J': ['Email drafting', 'Inbox management', 'Priority filtering', 'Responses'],
            '♥10': ['Task organization', 'Deadline tracking', 'Priority setting', 'Progress notes'],
            '♥9': ['Appointment scheduling', 'Time zone handling', 'Conflict resolution', 'Coordination'],
            '♦Q': ['Web searches', 'Data gathering', 'Source evaluation', 'Information extraction'],
            '♦J': ['Library documentation', 'API references', 'Version lookup', 'Example finding'],
            '♦10': ['Claim verification', 'Cross-referencing', 'Source validation', 'Accuracy checks'],
            '♣Q': ['File operations', 'Directory management', 'Backup strategies', 'Organization'],
            '♣J': ['Shell commands', 'Script writing', 'Process automation', 'System monitoring'],
            '♣10': ['App lifecycle', 'Process control', 'Resource allocation', 'Performance tuning']
        };
        
        return workerAbilities[cardId] || ['General task execution'];
    }
    
    drawJarvisNode(parent, jarvis) {
        if (!jarvis) return;
        
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('class', 'jarvis-node');
        g.setAttribute('data-card-id', 'J');
        g.setAttribute('transform', `translate(${this.centerX}, ${this.centerY})`);
        
        // Outer glow ring
        const outerRing = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        outerRing.setAttribute('r', '55');
        outerRing.setAttribute('fill', 'none');
        outerRing.setAttribute('stroke', '#00d4ff');
        outerRing.setAttribute('stroke-width', '1');
        outerRing.setAttribute('opacity', '0.3');
        outerRing.setAttribute('class', 'pulse-ring');
        g.appendChild(outerRing);
        
        // Middle ring
        const midRing = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        midRing.setAttribute('r', '45');
        midRing.setAttribute('fill', 'none');
        midRing.setAttribute('stroke', '#00d4ff');
        midRing.setAttribute('stroke-width', '2');
        midRing.setAttribute('opacity', '0.5');
        g.appendChild(midRing);
        
        // Core circle
        const core = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        core.setAttribute('r', '35');
        core.setAttribute('fill', 'rgba(0, 212, 255, 0.1)');
        core.setAttribute('stroke', '#00d4ff');
        core.setAttribute('stroke-width', '2');
        core.setAttribute('filter', 'url(#glow-cyan)');
        core.setAttribute('class', 'core-circle');
        g.appendChild(core);
        
        // Inner pulse
        const innerPulse = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        innerPulse.setAttribute('r', '15');
        innerPulse.setAttribute('fill', 'rgba(0, 212, 255, 0.3)');
        innerPulse.setAttribute('class', 'inner-pulse');
        g.appendChild(innerPulse);
        
        // Label
        const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        label.setAttribute('y', '65');
        label.setAttribute('text-anchor', 'middle');
        label.setAttribute('fill', '#00d4ff');
        label.setAttribute('font-size', '14');
        label.setAttribute('font-weight', '600');
        label.setAttribute('letter-spacing', '3');
        label.textContent = 'JARVIS';
        g.appendChild(label);
        
        // Status
        const status = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        status.setAttribute('y', '80');
        status.setAttribute('text-anchor', 'middle');
        status.setAttribute('fill', 'rgba(150, 200, 255, 0.6)');
        status.setAttribute('font-size', '10');
        status.setAttribute('letter-spacing', '1');
        status.textContent = (jarvis.state || 'idle').toUpperCase();
        g.appendChild(status);
        
        // Click handler
        g.style.cursor = 'pointer';
        g.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectAgent('J');
        });
        
        parent.appendChild(g);
        this.nodes.set('J', { el: g, x: this.centerX, y: this.centerY });
    }
    
    drawKingNode(parent, king, x, y) {
        const suitColors = {
            spades: '#00d4ff',
            hearts: '#ff4466',
            diamonds: '#ffaa00',
            clubs: '#00ff88'
        };
        const color = suitColors[king.suit] || '#00d4ff';
        
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('class', 'king-node');
        g.setAttribute('data-card-id', king.card_id);
        g.setAttribute('transform', `translate(${x}, ${y})`);
        
        // Hexagon background
        const hex = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        const size = 40;
        const points = [];
        for (let i = 0; i < 6; i++) {
            const angle = (Math.PI / 3) * i - Math.PI / 6;
            points.push(`${Math.cos(angle) * size},${Math.sin(angle) * size}`);
        }
        hex.setAttribute('points', points.join(' '));
        hex.setAttribute('fill', `${color}15`);
        hex.setAttribute('stroke', color);
        hex.setAttribute('stroke-width', '2');
        hex.setAttribute('filter', `url(#glow-${king.suit === 'spades' ? 'cyan' : king.suit === 'hearts' ? 'red' : king.suit === 'diamonds' ? 'yellow' : 'green'})`);
        g.appendChild(hex);
        
        // Suit symbol
        const suitSymbols = { spades: '♠', hearts: '♥', diamonds: '♦', clubs: '♣' };
        const symbol = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        symbol.setAttribute('text-anchor', 'middle');
        symbol.setAttribute('y', '-5');
        symbol.setAttribute('fill', color);
        symbol.setAttribute('font-size', '24');
        symbol.textContent = suitSymbols[king.suit] || '?';
        g.appendChild(symbol);
        
        // Rank
        const rank = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        rank.setAttribute('text-anchor', 'middle');
        rank.setAttribute('y', '15');
        rank.setAttribute('fill', '#ffffff');
        rank.setAttribute('font-size', '14');
        rank.setAttribute('font-weight', '700');
        rank.textContent = 'K';
        g.appendChild(rank);
        
        // Name label
        const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        label.setAttribute('y', '55');
        label.setAttribute('text-anchor', 'middle');
        label.setAttribute('fill', color);
        label.setAttribute('font-size', '10');
        label.setAttribute('letter-spacing', '1');
        label.textContent = king.name || 'KING';
        g.appendChild(label);
        
        // Status indicator
        const stateColors = {
            idle: '#666',
            working: '#00ff88',
            planning: '#ffaa00',
            reviewing: '#00d4ff',
        };
        const stateDot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        stateDot.setAttribute('cy', '35');
        stateDot.setAttribute('r', '4');
        stateDot.setAttribute('fill', stateColors[king.state] || '#666');
        if (king.state !== 'idle') {
            stateDot.setAttribute('class', 'state-pulse');
        }
        g.appendChild(stateDot);
        
        // Click handler
        g.style.cursor = 'pointer';
        g.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectAgent(king.card_id);
        });
        
        parent.appendChild(g);
        this.nodes.set(king.card_id, { el: g, x, y });
    }
    
    drawWorkerNode(parent, worker, x, y, suit) {
        const suitColors = {
            spades: '#00d4ff',
            hearts: '#ff4466',
            diamonds: '#ffaa00',
            clubs: '#00ff88'
        };
        const color = suitColors[suit] || '#00d4ff';
        
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('class', 'worker-node');
        g.setAttribute('data-card-id', worker.card_id);
        g.setAttribute('transform', `translate(${x}, ${y})`);
        
        // Card rectangle
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', '-18');
        rect.setAttribute('y', '-24');
        rect.setAttribute('width', '36');
        rect.setAttribute('height', '48');
        rect.setAttribute('rx', '4');
        rect.setAttribute('fill', `${color}10`);
        rect.setAttribute('stroke', color);
        rect.setAttribute('stroke-width', '1');
        rect.setAttribute('opacity', '0.7');
        g.appendChild(rect);
        
        // Suit symbol (small)
        const suitSymbols = { spades: '♠', hearts: '♥', diamonds: '♦', clubs: '♣' };
        const symbol = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        symbol.setAttribute('text-anchor', 'middle');
        symbol.setAttribute('y', '-5');
        symbol.setAttribute('fill', color);
        symbol.setAttribute('font-size', '14');
        symbol.textContent = suitSymbols[suit] || '?';
        g.appendChild(symbol);
        
        // Rank
        const rankText = worker.card_id?.replace(/[♠♥♦♣]/, '') || '?';
        const rank = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        rank.setAttribute('text-anchor', 'middle');
        rank.setAttribute('y', '12');
        rank.setAttribute('fill', '#ffffff');
        rank.setAttribute('font-size', '11');
        rank.setAttribute('font-weight', '600');
        rank.textContent = rankText;
        g.appendChild(rank);
        
        // Status dot
        const stateColors = {
            idle: '#333',
            working: '#00ff88',
            error: '#ff4466',
        };
        const stateDot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        stateDot.setAttribute('cy', '28');
        stateDot.setAttribute('r', '3');
        stateDot.setAttribute('fill', stateColors[worker.state] || '#333');
        if (worker.state !== 'idle') {
            stateDot.setAttribute('class', 'state-pulse');
        }
        g.appendChild(stateDot);
        
        // Click handler
        g.style.cursor = 'pointer';
        g.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectAgent(worker.card_id);
        });
        
        parent.appendChild(g);
        this.nodes.set(worker.card_id, { el: g, x, y });
    }
    
    drawEnergyLine(parent, x1, y1, x2, y2, suit, isWorker = false) {
        const suitColors = {
            spades: '#00d4ff',
            hearts: '#ff4466',
            diamonds: '#ffaa00',
            clubs: '#00ff88'
        };
        const color = suitColors[suit] || '#00d4ff';
        
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', x1);
        line.setAttribute('y1', y1);
        line.setAttribute('x2', x2);
        line.setAttribute('y2', y2);
        line.setAttribute('stroke', color);
        line.setAttribute('stroke-width', isWorker ? '1' : '2');
        line.setAttribute('opacity', isWorker ? '0.2' : '0.4');
        line.setAttribute('stroke-dasharray', isWorker ? '4,4' : 'none');
        parent.appendChild(line);
        
        if (!isWorker) {
            this.createFlowParticle(parent, x1, y1, x2, y2, color);
        }
    }
    
    createFlowParticle(parent, x1, y1, x2, y2, color) {
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('r', '3');
        circle.setAttribute('fill', color);
        circle.setAttribute('filter', 'url(#glow-cyan)');
        circle.setAttribute('class', 'flow-particle');
        
        const animX = document.createElementNS('http://www.w3.org/2000/svg', 'animate');
        animX.setAttribute('attributeName', 'cx');
        animX.setAttribute('from', x1);
        animX.setAttribute('to', x2);
        animX.setAttribute('dur', `${2 + Math.random() * 2}s`);
        animX.setAttribute('repeatCount', 'indefinite');
        circle.appendChild(animX);
        
        const animY = document.createElementNS('http://www.w3.org/2000/svg', 'animate');
        animY.setAttribute('attributeName', 'cy');
        animY.setAttribute('from', y1);
        animY.setAttribute('to', y2);
        animY.setAttribute('dur', `${2 + Math.random() * 2}s`);
        animY.setAttribute('repeatCount', 'indefinite');
        circle.appendChild(animY);
        
        parent.appendChild(circle);
    }
    
    // ============ AGENT SELECTION & DETAIL PANEL ============
    
    selectAgent(cardId) {
        this.selectedAgent = cardId;
        const agent = this.agentData.get(cardId);
        if (!agent) return;
        
        // Highlight selected node
        document.querySelectorAll('.king-node, .worker-node, .jarvis-node').forEach(el => {
            el.classList.remove('selected');
        });
        const node = this.nodes.get(cardId);
        if (node) {
            node.el.classList.add('selected');
        }
        
        this.showDetailPanel(agent);
    }
    
    deselectAgent() {
        this.selectedAgent = null;
        document.querySelectorAll('.king-node, .worker-node, .jarvis-node').forEach(el => {
            el.classList.remove('selected');
        });
        this.hideDetailPanel();
    }
    
    showDetailPanel(agent) {
        const panel = document.getElementById('detail-panel');
        if (!panel) return;
        
        this.updateDetailPanel(agent);
        panel.classList.remove('hidden');
    }
    
    updateDetailPanel(agent) {
        const suitSymbols = { spades: '♠', hearts: '♥', diamonds: '♦', clubs: '♣' };
        const suitColors = {
            spades: '#00d4ff',
            hearts: '#ff4466',
            diamonds: '#ffaa00',
            clubs: '#00ff88'
        };
        
        const cardId = `${suitSymbols[agent.suit] || ''}${agent.card_id?.replace(/[♠♥♦♣]/, '') || ''}`;
        const color = suitColors[agent.suit] || '#00d4ff';
        
        document.getElementById('detail-card-id').textContent = cardId;
        document.getElementById('detail-card-id').style.color = color;
        document.getElementById('detail-name').textContent = agent.name || '';
        document.getElementById('detail-role').textContent = agent.role || '';
        
        // State
        const stateEl = document.getElementById('detail-state');
        stateEl.textContent = (agent.state || 'idle').toUpperCase();
        // Remove all state classes
        stateEl.className = 'detail-state-badge';
        // Add the appropriate state class
        const stateClass = agent.state || 'idle';
        const validStates = ['idle', 'thinking', 'planning', 'working', 'reviewing', 'waiting', 'completed', 'error'];
        if (validStates.includes(stateClass)) {
            stateEl.classList.add(`state-${stateClass}`);
        }
        
        // Thinking process
        document.getElementById('detail-thinking').textContent = agent.thinking || 'Awaiting input...';
        
        // Current task
        document.getElementById('detail-task').textContent = agent.currentTask || 'No active task';
        
        // Abilities
        const abilitiesList = document.getElementById('detail-abilities');
        abilitiesList.innerHTML = (agent.abilities || []).map(a => 
            `<li>${a}</li>`
        ).join('');
        
        // Personality (for JARVIS and Kings)
        const personalityEl = document.getElementById('detail-personality');
        if (agent.personality) {
            personalityEl.textContent = agent.personality;
            personalityEl.parentElement.style.display = 'block';
        } else {
            personalityEl.parentElement.style.display = 'none';
        }
    }
    
    hideDetailPanel() {
        const panel = document.getElementById('detail-panel');
        if (panel) panel.classList.add('hidden');
    }
    
    // ============ TOOLTIP ============
    
    showTooltip(event, agent, type) {
        // Don't show tooltip if detail panel is open
        if (this.selectedAgent) return;
        
        const tooltip = document.getElementById('agent-tooltip');
        const suitSymbols = { spades: '♠', hearts: '♥', diamonds: '♦', clubs: '♣' };
        
        tooltip.querySelector('.tooltip-card-id').textContent = 
            `${suitSymbols[agent.suit] || ''}${agent.card_id?.replace(/[♠♥♦♣]/, '') || ''}`;
        tooltip.querySelector('.tooltip-name').textContent = agent.name || '';
        tooltip.querySelector('.tooltip-state').textContent = (agent.state || 'idle').toUpperCase();
        tooltip.querySelector('.tooltip-role').textContent = agent.title || agent.role || type;
        tooltip.querySelector('.tooltip-personality').textContent = agent.personality || '';
        
        tooltip.style.left = `${event.clientX + 15}px`;
        tooltip.style.top = `${event.clientY + 15}px`;
        tooltip.classList.remove('hidden');
    }
    
    hideTooltip() {
        document.getElementById('agent-tooltip').classList.add('hidden');
    }
    
    // ============ STATUS ============
    
    updateStatusOverlay() {
        if (!this.hierarchy) return;
        
        const kings = this.hierarchy.kings || [];
        let totalAgents = 1;
        let activeAgents = this.hierarchy.jarvis?.state !== 'idle' ? 1 : 0;
        
        kings.forEach(king => {
            totalAgents++;
            if (king.state !== 'idle') activeAgents++;
            
            (king.workers || []).forEach(worker => {
                totalAgents++;
                if (worker.state !== 'idle') activeAgents++;
            });
        });
        
        document.getElementById('agent-count').textContent = `${activeAgents}/${totalAgents}`;
        document.getElementById('system-status').textContent = 
            this.hierarchy.jarvis?.state?.toUpperCase() || 'READY';
    }
    
    // ============ ANIMATION ============
    
    animate() {
        this.drawParticles();
        this.animationFrame = requestAnimationFrame(() => this.animate());
    }
}

// Global functions
function toggleMissions() {
    const panel = document.getElementById('missions-panel');
    panel.classList.toggle('hidden');
}

function closeDetailPanel() {
    if (window.commandMap) {
        window.commandMap.deselectAgent();
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    window.commandMap = new CommandMap();
    
    // Fetch missions
    async function loadMissions() {
        try {
            const res = await fetch('/api/workspace');
            const workspaces = await res.json();
            const content = document.getElementById('missions-content');
            
            if (workspaces.length === 0) {
                content.innerHTML = '<div class="mission-empty">No active missions</div>';
                document.getElementById('mission-count').textContent = '0';
                return;
            }
            
            document.getElementById('mission-count').textContent = workspaces.length;
            
            content.innerHTML = workspaces.map(w => `
                <div class="mission-card">
                    <div class="mission-goal">${w.goal}</div>
                    <div class="mission-meta">
                        <span>${w.owner}</span>
                        <span>${w.status}</span>
                    </div>
                    <div class="mission-progress">
                        <div class="mission-progress-bar" style="width: ${w.progress}%"></div>
                    </div>
                </div>
            `).join('');
        } catch (e) {}
    }
    
    loadMissions();
    setInterval(loadMissions, 5000);
});

/* v3.2.0: Open explainability panel for selected agent */
function openExplainPanel() {
    if (!window.commandMap || !window.commandMap.selectedAgent) return;
    const agent = window.commandMap.agentData.get(window.commandMap.selectedAgent);
    if (!agent) return;

    // Build explanation data from agent info
    const explainData = {
        name: agent.name || agent.card_id,
        id: agent.card_id,
        department: agent.suit === 'spades' ? 'engineering' :
                    agent.suit === 'hearts' ? 'research' :
                    agent.suit === 'diamonds' ? 'personal' : 'system',
        confidence: agent.confidence || 0.85,
        model: agent.model || 'meta/llama-3.1-8b-instruct',
        duration: agent.lastDuration || null,
        thoughts: agent.thoughts || [
            { icon: '\u2022', text: agent.thinking || 'Awaiting task', confidence: agent.confidence || 0.5 }
        ],
        capabilities: agent.abilities || [],
        memories: agent.relevantMemories || [],
        timeline: agent.timeline || [],
    };

    if (window.explainability) {
        window.explainability.show('agent', explainData, window.innerWidth / 2, window.innerHeight / 2);
    }
}
