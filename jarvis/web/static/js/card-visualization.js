/**
 * Card Visualization - Agent hierarchy display
 * Shows the poker card hierarchy with live status
 */

class CardVisualization {
    constructor(container) {
        this.container = container;
        this.cards = new Map();
        this.connections = [];
        this.init();
    }
    
    init() {
        this.container.innerHTML = `
            <div class="card-tree">
                <div class="card-node jarvis-node" id="card-jarvis">
                    <div class="card-face jarvis">
                        <span class="card-label">JARVIS</span>
                        <span class="card-title">Chief Executive</span>
                    </div>
                </div>
                <div class="card-children" id="king-container"></div>
            </div>
        `;
        
        this.kingContainer = document.getElementById('king-container');
    }
    
    update(hierarchy) {
        if (!hierarchy || !hierarchy.kings) return;
        
        // Update JARVIS state
        const jarvisNode = document.getElementById('card-jarvis');
        if (jarvisNode) {
            jarvisNode.className = `card-node jarvis-node state-${hierarchy.jarvis?.state || 'idle'}`;
        }
        
        // Update Kings
        this.kingContainer.innerHTML = '';
        
        hierarchy.kings.forEach(king => {
            const kingEl = this.createKingNode(king);
            this.kingContainer.appendChild(kingEl);
        });
    }
    
    createKingNode(king) {
        const suitColors = {
            spades: '#00d4ff',
            hearts: '#ff4466',
            diamonds: '#ffaa00',
            clubs: '#00ff88'
        };
        
        const suitSymbols = {
            spades: '♠',
            hearts: '♥',
            diamonds: '♦',
            clubs: '♣'
        };
        
        const color = suitColors[king.suit] || '#00d4ff';
        const symbol = suitSymbols[king.suit] || '?';
        
        const kingEl = document.createElement('div');
        kingEl.className = `card-branch`;
        kingEl.innerHTML = `
            <div class="card-node king-node state-${king.state}" style="--suit-color: ${color}">
                <div class="card-face king">
                    <span class="card-symbol">${symbol}</span>
                    <span class="card-rank">K</span>
                    <span class="card-name">${king.name}</span>
                </div>
            </div>
            <div class="card-children workers-container">
                ${king.workers.map(w => this.createWorkerCard(w, color, symbol)).join('')}
            </div>
        `;
        
        return kingEl;
    }
    
    createWorkerCard(worker, color, suitSymbol) {
        const rankSymbols = {
            queen: 'Q',
            jack: 'J',
            ten: '10',
            nine: '9',
            eight: '8',
            seven: '7',
            six: '6',
            five: '5',
            four: '4',
            three: '3',
            two: '2'
        };
        
        // Extract rank from card_id (e.g., "♠Q" -> "Q")
        const rank = worker.card_id?.replace(/[♠♥♦♣]/, '') || '?';
        
        return `
            <div class="card-node worker-node state-${worker.state}">
                <div class="card-face worker" style="--suit-color: ${color}">
                    <span class="card-symbol-mini">${suitSymbol}</span>
                    <span class="card-rank-mini">${rank}</span>
                </div>
                <div class="card-tooltip">${worker.name || worker.card_id}</div>
            </div>
        `;
    }
}

// Export
window.CardVisualization = CardVisualization;
