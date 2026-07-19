/* JARVIS Core — SVG Arc Reactor v5.5.0 Living Intelligence */

class JarvisCore {
    constructor(container) {
        this.container = typeof container === 'string'
            ? document.querySelector(container) : container;
        if (!this.container) return;

        this.w = this.container.clientWidth || 600;
        this.h = this.container.clientHeight || 600;
        this.state = 'idle';
        this.time = 0;
        this.audioVolume = 0;
        this.audioFrequency = 0;
        this.waveform = new Array(64).fill(0);

        this.stateColors = {
            idle:           { core: '#00f0ff', aura: 'rgba(0,240,255,0.08)', ring: '#00f0ff' },
            listening:      { core: '#00ff88', aura: 'rgba(0,255,136,0.12)', ring: '#00ff88' },
            thinking:       { core: '#ffaa00', aura: 'rgba(255,170,0,0.15)', ring: '#ffaa00' },
            speaking:       { core: '#00f0ff', aura: 'rgba(0,240,255,0.12)', ring: '#00f0ff' },
            working:        { core: '#ff6b35', aura: 'rgba(255,107,53,0.12)', ring: '#ff6b35' },
            retrieving:     { core: '#9b59b6', aura: 'rgba(155,89,182,0.12)', ring: '#9b59b6' },
            planning:       { core: '#f39c12', aura: 'rgba(243,156,18,0.15)', ring: '#f39c12' },
            delegating:     { core: '#e74c3c', aura: 'rgba(231,76,60,0.12)', ring: '#e74c3c' },
            reviewing:      { core: '#3498db', aura: 'rgba(52,152,219,0.12)', ring: '#3498db' },
            complete:       { core: '#2ecc71', aura: 'rgba(46,204,113,0.15)', ring: '#2ecc71' },
            error:          { core: '#ff3366', aura: 'rgba(255,51,102,0.2)', ring: '#ff3366' },
            mission_active: { core: '#00f0ff', aura: 'rgba(0,240,255,0.1)', ring: '#00f0ff' },
        };

        this.ringSpeeds = {
            idle:           { inner: 0.003, mid: -0.002, outer: 0.001 },
            listening:      { inner: 0.008, mid: -0.005, outer: 0.003 },
            thinking:       { inner: 0.015, mid: -0.010, outer: 0.006 },
            speaking:       { inner: 0.010, mid: -0.007, outer: 0.004 },
            working:        { inner: 0.020, mid: -0.012, outer: 0.008 },
            retrieving:     { inner: 0.012, mid: -0.008, outer: 0.005 },
            planning:       { inner: 0.018, mid: -0.011, outer: 0.007 },
            delegating:     { inner: 0.025, mid: -0.015, outer: 0.010 },
            reviewing:      { inner: 0.008, mid: -0.005, outer: 0.003 },
            complete:       { inner: 0.002, mid: -0.001, outer: 0.001 },
            error:          { inner: 0.030, mid: -0.020, outer: 0.015 },
            mission_active: { inner: 0.012, mid: -0.008, outer: 0.005 },
        };

        this.currentSpeed = { inner: 0.003, mid: -0.002, outer: 0.001 };
        this.targetSpeed = { ...this.currentSpeed };

        this._init();
        this._animate();
    }

    _init() {
        const ns = 'http://www.w3.org/2000/svg';
        this.svg = document.createElementNS(ns, 'svg');
        this.svg.setAttribute('viewBox', '-300 -300 600 600');
        this.svg.setAttribute('width', '100%');
        this.svg.setAttribute('height', '100%');
        this.svg.style.position = 'absolute';
        this.svg.style.top = '0';
        this.svg.style.left = '0';

        const defs = document.createElementNS(ns, 'defs');

        const glowFilter = this._createFilter(ns, 'glow', 'glow', [
            { type: 'feGaussianBlur', attrs: { stdDeviation: '3', result: 'blur' }},
            { type: 'feMerge', children: ['blur', 'SourceGraphic'] }
        ]);
        defs.appendChild(glowFilter);

        const glowStrong = this._createFilter(ns, 'glow-strong', 'glow-strong', [
            { type: 'feGaussianBlur', attrs: { stdDeviation: '6', result: 'blur' }},
            { type: 'feMerge', children: ['blur', 'SourceGraphic'] }
        ]);
        defs.appendChild(glowStrong);

        const coreGrad = document.createElementNS(ns, 'radialGradient');
        coreGrad.id = 'core-gradient';
        coreGrad.innerHTML = `
            <stop offset="0%" stop-color="#ffffff" stop-opacity="0.9"/>
            <stop offset="40%" stop-color="#00f0ff" stop-opacity="0.7"/>
            <stop offset="100%" stop-color="#0066aa" stop-opacity="0.3"/>
        `;
        defs.appendChild(coreGrad);

        const auraGrad = document.createElementNS(ns, 'radialGradient');
        auraGrad.id = 'core-aura';
        auraGrad.innerHTML = `
            <stop offset="0%" stop-color="#00f0ff" stop-opacity="0.15"/>
            <stop offset="100%" stop-color="#00f0ff" stop-opacity="0"/>
        `;
        defs.appendChild(auraGrad);

        this.svg.appendChild(defs);

        this.auraGroup = document.createElementNS(ns, 'g');
        this.ringGroup = document.createElementNS(ns, 'g');
        this.tickGroup = document.createElementNS(ns, 'g');
        this.coreGroup = document.createElementNS(ns, 'g');
        this.waveGroup = document.createElementNS(ns, 'g');

        this.svg.appendChild(this.auraGroup);
        this.svg.appendChild(this.ringGroup);
        this.svg.appendChild(this.tickGroup);
        this.svg.appendChild(this.coreGroup);
        this.svg.appendChild(this.waveGroup);

        this._createAura(ns);
        this._createCore(ns);
        this._createRings(ns);
        this._createWaveform(ns);

        this.container.appendChild(this.svg);
    }

    _createFilter(ns, id, result, children) {
        const filter = document.createElementNS(ns, 'filter');
        filter.id = id;
        filter.setAttribute('x', '-50%');
        filter.setAttribute('y', '-50%');
        filter.setAttribute('width', '200%');
        filter.setAttribute('height', '200%');
        children.forEach(c => {
            if (c.type === 'feGaussianBlur') {
                const el = document.createElementNS(ns, 'feGaussianBlur');
                Object.entries(c.attrs).forEach(([k,v]) => el.setAttribute(k, v));
                filter.appendChild(el);
            } else if (c.type === 'feMerge') {
                const merge = document.createElementNS(ns, 'feMerge');
                c.children.forEach(r => {
                    const node = document.createElementNS(ns, 'feMergeNode');
                    node.setAttribute('in', r);
                    merge.appendChild(node);
                });
                filter.appendChild(merge);
            }
        });
        return filter;
    }

    _createAura(ns) {
        this.aura = document.createElementNS(ns, 'circle');
        this.aura.setAttribute('r', '140');
        this.aura.setAttribute('fill', 'url(#core-aura)');
        this.auraGroup.appendChild(this.aura);
    }

    _createCore(ns) {
        const glow = document.createElementNS(ns, 'circle');
        glow.setAttribute('r', '38');
        glow.setAttribute('fill', 'none');
        glow.setAttribute('stroke', '#00f0ff');
        glow.setAttribute('stroke-width', '1');
        glow.setAttribute('stroke-opacity', '0.3');
        glow.setAttribute('filter', 'url(#glow)');
        this.coreGroup.appendChild(glow);

        this.coreSphere = document.createElementNS(ns, 'circle');
        this.coreSphere.setAttribute('r', '24');
        this.coreSphere.setAttribute('fill', 'url(#core-gradient)');
        this.coreSphere.setAttribute('filter', 'url(#glow-strong)');
        this.coreGroup.appendChild(this.coreSphere);

        const inner = document.createElementNS(ns, 'circle');
        inner.setAttribute('r', '12');
        inner.setAttribute('fill', '#ffffff');
        inner.setAttribute('fill-opacity', '0.4');
        this.coreGroup.appendChild(inner);

        const center = document.createElementNS(ns, 'circle');
        center.setAttribute('r', '3');
        center.setAttribute('fill', '#ffffff');
        this.coreGroup.appendChild(center);
    }

    _createRings(ns) {
        this.rings = [];
        const configs = [
            { r: 65,  dash: '2 6',   ticks: 12, speed: 0.003 },
            { r: 100, dash: '8 4 2 4', ticks: 24, speed: -0.002 },
            { r: 140, dash: '1 8',   ticks: 36, speed: 0.001 },
        ];

        configs.forEach((cfg, i) => {
            const ring = document.createElementNS(ns, 'circle');
            ring.setAttribute('r', cfg.r);
            ring.setAttribute('fill', 'none');
            ring.setAttribute('stroke', '#00f0ff');
            ring.setAttribute('stroke-width', '0.5');
            ring.setAttribute('stroke-opacity', '0.4');
            ring.setAttribute('stroke-dasharray', cfg.dash);
            this.ringGroup.appendChild(ring);

            for (let t = 0; t < cfg.ticks; t++) {
                const angle = (t / cfg.ticks) * Math.PI * 2;
                const isMajor = t % (cfg.ticks / 4) === 0;
                const len = isMajor ? 8 : 3;
                const x1 = Math.cos(angle) * (cfg.r - len);
                const y1 = Math.sin(angle) * (cfg.r - len);
                const x2 = Math.cos(angle) * cfg.r;
                const y2 = Math.sin(angle) * cfg.r;

                const tick = document.createElementNS(ns, 'line');
                tick.setAttribute('x1', x1);
                tick.setAttribute('y1', y1);
                tick.setAttribute('x2', x2);
                tick.setAttribute('y2', y2);
                tick.setAttribute('stroke', '#00f0ff');
                tick.setAttribute('stroke-width', isMajor ? '1' : '0.5');
                tick.setAttribute('stroke-opacity', isMajor ? '0.6' : '0.3');
                this.tickGroup.appendChild(tick);
            }

            this.rings.push({ el: ring, r: cfg.r, speed: cfg.speed, angle: 0 });
        });
    }

    _createWaveform(ns) {
        this.wavePath = document.createElementNS(ns, 'path');
        this.wavePath.setAttribute('fill', 'none');
        this.wavePath.setAttribute('stroke', '#00f0ff');
        this.wavePath.setAttribute('stroke-width', '1');
        this.wavePath.setAttribute('stroke-opacity', '0.5');
        this.waveGroup.appendChild(this.wavePath);

        this.waveMirror = document.createElementNS(ns, 'path');
        this.waveMirror.setAttribute('fill', 'none');
        this.waveMirror.setAttribute('stroke', '#00f0ff');
        this.waveMirror.setAttribute('stroke-width', '0.5');
        this.waveMirror.setAttribute('stroke-opacity', '0.2');
        this.waveGroup.appendChild(this.waveMirror);
    }

    _animate() {
        this.time += 0.016;

        const lerp = 0.03;
        this.currentSpeed.inner += (this.targetSpeed.inner - this.currentSpeed.inner) * lerp;
        this.currentSpeed.mid += (this.targetSpeed.mid - this.currentSpeed.mid) * lerp;
        this.currentSpeed.outer += (this.targetSpeed.outer - this.currentSpeed.outer) * lerp;

        this.rings[0].angle += this.currentSpeed.inner * 60;
        this.rings[1].angle += this.currentSpeed.mid * 60;
        this.rings[2].angle += this.currentSpeed.outer * 60;

        this.ringGroup.setAttribute('transform', `rotate(${this.rings[0].angle})`);
        this.tickGroup.setAttribute('transform', `rotate(${this.rings[1].angle})`);

        const pulse = Math.sin(this.time * 2) * 0.06;
        this.coreSphere.setAttribute('transform', `scale(${1 + pulse})`);

        const auraBreath = Math.sin(this.time * 1.2) * 0.04;
        this.aura.setAttribute('transform', `scale(${1 + auraBreath})`);

        if (this.audioVolume > 0) {
            const glow = 0.3 + this.audioVolume * 0.7;
            this.coreSphere.setAttribute('filter', 'url(#glow-strong)');
        }

        this._updateWaveform();

        this._raf = requestAnimationFrame(() => this._animate());
    }

    _updateWaveform() {
        const width = 80;
        const height = 30;
        const segW = width / 64;
        let d = `M ${-width/2} 0`;
        let dm = `M ${-width/2} 0`;

        for (let i = 0; i < 64; i++) {
            const x = -width/2 + i * segW;
            const v = this.waveform[i] || 0;
            const amp = this.state === 'idle'
                ? Math.sin(this.time * 0.5 + i * 0.2) * 2
                : v * height * (0.5 + this.audioVolume * 0.5);
            d += ` L ${x} ${amp}`;
            dm += ` L ${x} ${-amp * 0.3}`;
        }

        this.wavePath.setAttribute('d', d);
        this.waveMirror.setAttribute('d', dm);
    }

    setState(newState) {
        const oldState = this.state;
        this.state = newState;
        this.targetSpeed = { ...this.ringSpeeds[newState] || this.ringSpeeds.idle };

        const colors = this.stateColors[newState] || this.stateColors.idle;
        this._updateColors(colors);
    }

    _updateColors(colors) {
        this.rings.forEach(ring => {
            ring.el.setAttribute('stroke', colors.ring);
        });

        const stops = document.querySelectorAll('#core-gradient stop');
        if (stops.length >= 3) {
            stops[1].setAttribute('stop-color', colors.core);
        }

        const auraStops = document.querySelectorAll('#core-aura stop');
        if (auraStops.length >= 2) {
            auraStops[0].setAttribute('stop-color', colors.core);
        }

        this.wavePath.setAttribute('stroke', colors.core);
        this.waveMirror.setAttribute('stroke', colors.core);
    }

    setAudio(volume, frequency, pitch) {
        this.audioVolume = volume || 0;
        this.audioFrequency = frequency || 0;

        if (volume > 0.01) {
            for (let i = 0; i < 64; i++) {
                const h = Math.sin(this.time * 3 + i * 0.3) * volume;
                this.waveform[i] = this.waveform[i] * 0.7 + h * 0.3;
            }
        } else {
            for (let i = 0; i < 64; i++) {
                this.waveform[i] *= 0.95;
            }
        }
    }

    onResize() {
        this.w = this.container.clientWidth || 600;
        this.h = this.container.clientHeight || 600;
    }

    destroy() {
        if (this._raf) cancelAnimationFrame(this._raf);
        this.container.innerHTML = '';
    }
}

window.JarvisCore = JarvisCore;
