/**
 * JARVIS Core — Arc Reactor Holographic Interface
 *
 * Central pulsing sphere + 3 concentric rings with technical ticks,
 * rotating at offset speeds. Integrated audio waveform.
 * Hyper-futuristic, minimalist sci-fi holographic aesthetic.
 */

class JarvisCore {
    constructor(container) {
        this.container = container;
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.state = 'idle';
        this.time = 0;
        this.audioVolume = 0;
        this.audioFrequency = 0;
        this.waveformData = new Float32Array(64).fill(0);
        this._animFrame = null;

        // Ring rotation speeds (radians per frame)
        this.ringSpeeds = { inner: 0.003, mid: -0.002, outer: 0.001 };
        this.targetRingSpeeds = { ...this.ringSpeeds };

        this.init();
    }

    init() {
        this.container.innerHTML = '';
        this.container.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            z-index: 0; display: flex; align-items: center; justify-content: center;
            background: #050b14; overflow: hidden;
        `;

        // SVG viewBox centered at 0,0
        const size = 600;
        this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        this.svg.setAttribute('viewBox', `${-size/2} ${-size/2} ${size} ${size}`);
        this.svg.setAttribute('width', '100%');
        this.svg.setAttribute('height', '100%');
        this.svg.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;';
        this.container.appendChild(this.svg);

        // Defs for filters and gradients
        const defs = this._svgEl('defs');
        defs.innerHTML = `
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="4" result="blur"/>
                <feComposite in="SourceGraphic" in2="blur" operator="over"/>
            </filter>
            <filter id="glow-strong" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="8" result="blur"/>
                <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
            <filter id="glow-soft" x="-100%" y="-100%" width="300%" height="300%">
                <feGaussianBlur stdDeviation="16" result="blur"/>
                <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
            <radialGradient id="core-gradient" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stop-color="#00f0ff" stop-opacity="0.9"/>
                <stop offset="40%" stop-color="#00c8dd" stop-opacity="0.5"/>
                <stop offset="100%" stop-color="#006680" stop-opacity="0"/>
            </radialGradient>
            <radialGradient id="core-aura" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stop-color="#00f0ff" stop-opacity="0.15"/>
                <stop offset="100%" stop-color="#00f0ff" stop-opacity="0"/>
            </radialGradient>
            <linearGradient id="ring-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#00f0ff" stop-opacity="0.8"/>
                <stop offset="50%" stop-color="#00f0ff" stop-opacity="0.3"/>
                <stop offset="100%" stop-color="#00f0ff" stop-opacity="0.8"/>
            </linearGradient>
        `;
        this.svg.appendChild(defs);

        // Layer groups (render order)
        this.auraGroup = this._svgEl('g', { filter: 'url(#glow-soft)' });
        this.ringGroup = this._svgEl('g');
        this.coreGroup = this._svgEl('g', { filter: 'url(#glow)' });
        this.waveGroup = this._svgEl('g');
        this.tickGroup = this._svgEl('g');

        this.svg.appendChild(this.auraGroup);
        this.svg.appendChild(this.ringGroup);
        this.svg.appendChild(this.tickGroup);
        this.svg.appendChild(this.coreGroup);
        this.svg.appendChild(this.waveGroup);

        this._createAura();
        this._createCore();
        this._createRings();
        this._createWaveform();

        window.addEventListener('resize', () => this._onResize());
        this._animate();
    }

    /* ===== SVG Helpers ===== */

    _svgEl(tag, attrs = {}) {
        const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
        for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
        return el;
    }

    _svgCircle(cx, cy, r, attrs = {}) {
        return this._svgEl('circle', { cx, cy, r, ...attrs });
    }

    _svgPath(d, attrs = {}) {
        return this._svgEl('path', { d, ...attrs });
    }

    _svgLine(x1, y1, x2, y2, attrs = {}) {
        return this._svgEl('line', { x1, y1, x2, y2, ...attrs });
    }

    /* ===== Aura ===== */

    _createAura() {
        // Outer soft glow aura
        this.aura = this._svgCircle(0, 0, 140, {
            fill: 'url(#core-aura)', opacity: '1'
        });
        this.auraGroup.appendChild(this.aura);
    }

    /* ===== Core Sphere ===== */

    _createCore() {
        // Outer glow ring
        this.coreGlow = this._svgCircle(0, 0, 38, {
            fill: 'none', stroke: '#00f0ff', 'stroke-width': '0.5', opacity: '0.3'
        });
        this.coreGroup.appendChild(this.coreGlow);

        // Main sphere
        this.coreSphere = this._svgCircle(0, 0, 24, {
            fill: 'url(#core-gradient)', opacity: '0.95'
        });
        this.coreGroup.appendChild(this.coreSphere);

        // Inner highlight
        this.coreInner = this._svgCircle(0, 0, 12, {
            fill: '#00f0ff', opacity: '0.4'
        });
        this.coreGroup.appendChild(this.coreInner);

        // Center dot
        this.coreDot = this._svgCircle(0, 0, 3, {
            fill: '#ffffff', opacity: '0.9'
        });
        this.coreGroup.appendChild(this.coreDot);
    }

    /* ===== Concentric Rings ===== */

    _createRings() {
        this.rings = {};

        // Ring definitions: radius, dash pattern, stroke width
        const ringDefs = {
            inner: { r: 65, dash: '2 6', width: 1.2, opacity: 0.7 },
            mid:   { r: 100, dash: '8 4 2 4', width: 1.0, opacity: 0.5 },
            outer: { r: 140, dash: '1 8', width: 0.8, opacity: 0.35 },
        };

        for (const [name, def] of Object.entries(ringDefs)) {
            const g = this._svgEl('g');

            // Main ring circle
            const circle = this._svgCircle(0, 0, def.r, {
                fill: 'none',
                stroke: '#00f0ff',
                'stroke-width': def.width,
                'stroke-dasharray': def.dash,
                opacity: def.opacity,
            });
            g.appendChild(circle);

            // Tick marks
            const tickCount = name === 'inner' ? 12 : name === 'mid' ? 24 : 36;
            for (let i = 0; i < tickCount; i++) {
                const angle = (i / tickCount) * Math.PI * 2;
                const isMajor = i % (tickCount / 4) === 0;
                const isMinor = i % 3 === 0;

                const len = isMajor ? 8 : isMinor ? 5 : 3;
                const r1 = def.r - len;
                const r2 = def.r;

                const x1 = Math.cos(angle) * r1;
                const y1 = Math.sin(angle) * r1;
                const x2 = Math.cos(angle) * r2;
                const y2 = Math.sin(angle) * r2;

                const tick = this._svgLine(x1, y1, x2, y2, {
                    stroke: isMajor ? '#ffaa00' : '#00f0ff',
                    'stroke-width': isMajor ? 1.2 : 0.5,
                    opacity: isMajor ? 0.7 : isMinor ? 0.4 : 0.2,
                });
                g.appendChild(tick);

                // Crosshair at cardinal points
                if (isMajor) {
                    const cx = Math.cos(angle) * def.r;
                    const cy = Math.sin(angle) * def.r;
                    const chSize = 3;
                    const ch = this._svgEl('g', { opacity: '0.5' });
                    ch.appendChild(this._svgLine(cx - chSize, cy, cx + chSize, cy, {
                        stroke: '#ffaa00', 'stroke-width': 0.6
                    }));
                    ch.appendChild(this._svgLine(cx, cy - chSize, cx, cy + chSize, {
                        stroke: '#ffaa00', 'stroke-width': 0.6
                    }));
                    g.appendChild(ch);
                }
            }

            // Orbiting dot
            const orbitDot = this._svgCircle(def.r, 0, 2, {
                fill: '#00f0ff', opacity: '0.8', filter: 'url(#glow)'
            });
            g.appendChild(orbitDot);
            this.rings[name] = { group: g, circle, orbitDot, radius: def.r };

            this.ringGroup.appendChild(g);
        }

        // Crosshair at center (subtle)
        const chGroup = this._svgEl('g', { opacity: '0.15' });
        chGroup.appendChild(this._svgLine(-8, 0, 8, 0, { stroke: '#00f0ff', 'stroke-width': 0.5 }));
        chGroup.appendChild(this._svgLine(0, -8, 0, 8, { stroke: '#00f0ff', 'stroke-width': 0.5 }));
        this.coreGroup.appendChild(chGroup);
    }

    /* ===== Audio Waveform ===== */

    _createWaveform() {
        this.wavePath = this._svgPath('', {
            fill: 'none',
            stroke: '#00f0ff',
            'stroke-width': 1.5,
            opacity: '0.7',
            filter: 'url(#glow)',
        });
        this.waveGroup.appendChild(this.wavePath);

        // Mirror waveform (below center)
        this.wavePathMirror = this._svgPath('', {
            fill: 'none',
            stroke: '#00f0ff',
            'stroke-width': 1,
            opacity: '0.3',
        });
        this.waveGroup.appendChild(this.wavePathMirror);
    }

    _updateWaveform() {
        const points = [];
        const mirrorPoints = [];
        const w = 40; // half-width of waveform
        const segments = this.waveformData.length;

        for (let i = 0; i < segments; i++) {
            const t = i / (segments - 1);
            const x = -w + t * w * 2;
            const amp = this.waveformData[i] * 12;
            const y = -amp;
            const yMirror = amp * 0.6;
            points.push(`${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`);
            mirrorPoints.push(`${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${yMirror.toFixed(1)}`);
        }

        this.wavePath.setAttribute('d', points.join(' '));
        this.wavePathMirror.setAttribute('d', mirrorPoints.join(' '));
    }

    /* ===== Animation Loop ===== */

    _animate() {
        this._animFrame = requestAnimationFrame(() => this._animate());
        this.time += 0.016;

        // Smooth ring speed interpolation
        for (const name of ['inner', 'mid', 'outer']) {
            this.ringSpeeds[name] += (this.targetRingSpeeds[name] - this.ringSpeeds[name]) * 0.03;
        }

        // Rotate rings
        if (this.rings.inner) {
            const innerAngle = this.time * this.ringSpeeds.inner * 60;
            const midAngle = this.time * this.ringSpeeds.mid * 60;
            const outerAngle = this.time * this.ringSpeeds.outer * 60;
            this.rings.inner.group.setAttribute('transform', `rotate(${innerAngle})`);
            this.rings.mid.group.setAttribute('transform', `rotate(${midAngle})`);
            this.rings.outer.group.setAttribute('transform', `rotate(${outerAngle})`);
        }

        // Core pulse
        const pulse = 1.0 + Math.sin(this.time * 2) * 0.06;
        this.coreSphere.setAttribute('r', 24 * pulse);
        this.coreGlow.setAttribute('r', 38 * pulse);
        this.coreInner.setAttribute('r', 12 * pulse);
        this.coreInner.setAttribute('opacity', 0.3 + Math.sin(this.time * 3) * 0.1);

        // Aura breathe
        const auraPulse = 1.0 + Math.sin(this.time * 1.2) * 0.04;
        this.aura.setAttribute('r', 140 * auraPulse);

        // Audio reactivity — scale core glow with volume
        const volScale = 1.0 + this.audioVolume * 0.4;
        this.coreGlow.setAttribute('r', 38 * pulse * volScale);
        this.coreGlow.setAttribute('opacity', 0.2 + this.audioVolume * 0.5);

        // Waveform
        this._updateWaveform();
    }

    /* ===== Public API ===== */

    setState(newState) {
        if (this.state === newState) return;
        this.state = newState;

        switch (newState) {
            case 'idle':
                this.targetRingSpeeds = { inner: 0.003, mid: -0.002, outer: 0.001 };
                break;
            case 'listening':
                this.targetRingSpeeds = { inner: 0.006, mid: -0.004, outer: 0.002 };
                break;
            case 'thinking':
                this.targetRingSpeeds = { inner: 0.012, mid: -0.008, outer: 0.005 };
                break;
            case 'speaking':
                this.targetRingSpeeds = { inner: 0.008, mid: -0.005, outer: 0.003 };
                break;
            case 'working':
                this.targetRingSpeeds = { inner: 0.010, mid: -0.007, outer: 0.004 };
                break;
        }
    }

    setAudio(volume, frequency, pitch) {
        this.audioVolume = volume;
        this.audioFrequency = frequency;

        // Generate waveform from volume + frequency
        for (let i = 0; i < this.waveformData.length; i++) {
            const t = i / this.waveformData.length;
            const baseWave = Math.sin(t * Math.PI * 4 + this.time * 8) * volume;
            const freqMod = Math.sin(t * Math.PI * 2 * (frequency / 500)) * volume * 0.5;
            const noise = (Math.random() - 0.5) * volume * 0.3;
            const target = baseWave + freqMod + noise;
            this.waveformData[i] += (target - this.waveformData[i]) * 0.3;
        }

        // Idle breathing waveform when no audio
        if (volume < 0.01) {
            for (let i = 0; i < this.waveformData.length; i++) {
                const t = i / this.waveformData.length;
                const idle = Math.sin(t * Math.PI * 3 + this.time * 1.5) * 0.08;
                this.waveformData[i] += (idle - this.waveformData[i]) * 0.05;
            }
        }
    }

    onResize() {
        this.width = window.innerWidth;
        this.height = window.innerHeight;
    }

    destroy() {
        if (this._animFrame) cancelAnimationFrame(this._animFrame);
        this.container.innerHTML = '';
    }
}

window.JarvisCore = JarvisCore;
