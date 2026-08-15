/**
 * DigitalTwin — Mini avatar reflecting JARVIS's current state.
 * Persistent presence indicator with state-driven animations.
 */
class DigitalTwin {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.state = 'idle';
        this.energy = 100;
        this._interval = null;
    }

    init() {
        if (!this.container) return;
        this.render();
        this._startEnergyDrain();
    }

    setState(state) {
        const prev = this.state;
        this.state = state;
        if (this.container) {
            this.render();
        }
    }

    setEnergy(level) {
        this.energy = Math.max(0, Math.min(100, level));
        if (this.container) {
            const ring = this.container.querySelector('.twin-energy-ring');
            if (ring) {
                const circumference = 2 * Math.PI * 18;
                ring.style.strokeDashoffset = circumference * (1 - this.energy / 100);
            }
        }
    }

    render() {
        if (!this.container) return;

        const stateConfig = {
            idle: { color: 'var(--text-muted)', label: 'Idle', pulse: false },
            thinking: { color: 'var(--info)', label: 'Thinking', pulse: true },
            planning: { color: '#7aa2ff', label: 'Planning', pulse: true },
            working: { color: 'var(--info)', label: 'Working', pulse: true },
            verifying: { color: '#e8f6ff', label: 'Verifying', pulse: true },
            speaking: { color: 'var(--accent)', label: 'Speaking', pulse: true },
            listening: { color: 'var(--success)', label: 'Listening', pulse: true },
            error: { color: 'var(--danger)', label: 'Error', pulse: false },
        };

        const cfg = stateConfig[this.state] || stateConfig['idle'];

        this.container.innerHTML = `
            <div class="twin-avatar ${this.state}">
                <svg viewBox="0 0 44 44" class="twin-ring">
                    <circle cx="22" cy="22" r="18" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="3"/>
                    <circle cx="22" cy="22" r="18" fill="none" stroke="${cfg.color}" stroke-width="3"
                        stroke-dasharray="${2 * Math.PI * 18}"
                        stroke-dashoffset="${2 * Math.PI * 18 * (1 - this.energy / 100)}"
                        stroke-linecap="round"
                        class="twin-energy-ring"
                        transform="rotate(-90 22 22)"/>
                </svg>
                <div class="twin-core ${cfg.pulse ? 'pulse' : ''}">
                    <div class="twin-glow" style="background: ${cfg.color}"></div>
                </div>
            </div>
            <span class="twin-label">${cfg.label}</span>
        `;
    }

    _startEnergyDrain() {
        this._interval = setInterval(() => {
            if (document.hidden) return;
            if (this.container && this.container.offsetParent === null) return;
            if (this.state === 'thinking' || this.state === 'speaking') {
                this.setEnergy(this.energy - 0.5);
            } else if (this.state === 'idle') {
                this.setEnergy(Math.min(100, this.energy + 0.2));
            }
        }, 1000);
    }

    destroy() {
        if (this._interval) clearInterval(this._interval);
    }
}

window.DigitalTwin = DigitalTwin;