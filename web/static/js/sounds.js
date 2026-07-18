/**
 * JARVIS Sound System v4.0
 * Subtle, professional audio feedback
 * Uses Web Audio API to generate tones programmatically
 */

class JarvisSounds {
    constructor() {
        this.ctx = null;
        this.enabled = true;
        this.volume = 0.15; // Very subtle
        this.initialized = false;
    }

    init() {
        if (this.initialized) return;
        try {
            this.ctx = new (window.AudioContext || window.webkitAudioContext)();
            this.initialized = true;
        } catch (e) {
            this.enabled = false;
        }
    }

    _ensureContext() {
        if (!this.ctx) this.init();
        if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
        return this.ctx && this.ctx.state === 'running';
    }

    // Play a simple tone
    _tone(freq, duration, type = 'sine', vol = this.volume) {
        if (!this.enabled || !this._ensureContext()) return;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = type;
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(vol, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start();
        osc.stop(this.ctx.currentTime + duration);
    }

    // === Sound Effects ===

    missionAssigned() {
        // Two ascending tones
        this._tone(440, 0.15, 'sine');
        setTimeout(() => this._tone(660, 0.2, 'sine'), 100);
    }

    taskComplete() {
        // Quick bright chord
        this._tone(523, 0.12, 'sine');
        setTimeout(() => this._tone(659, 0.12, 'sine'), 50);
        setTimeout(() => this._tone(784, 0.2, 'sine'), 100);
    }

    thinking() {
        // Very subtle low pulse
        this._tone(220, 0.08, 'sine', this.volume * 0.5);
    }

    voiceStart() {
        // Warm ascending
        this._tone(330, 0.1, 'sine');
        setTimeout(() => this._tone(440, 0.15, 'sine'), 80);
    }

    voiceStop() {
        // Warm descending
        this._tone(440, 0.1, 'sine');
        setTimeout(() => this._tone(330, 0.15, 'sine'), 80);
    }

    notification() {
        // Gentle ping
        this._tone(880, 0.15, 'sine', this.volume * 0.7);
        setTimeout(() => this._tone(1100, 0.2, 'sine', this.volume * 0.5), 120);
    }

    error() {
        // Low descending
        this._tone(300, 0.15, 'sawtooth', this.volume * 0.4);
        setTimeout(() => this._tone(200, 0.25, 'sawtooth', this.volume * 0.3), 100);
    }

    toggle() {
        this.enabled = !this.enabled;
        return this.enabled;
    }
}

window.JarvisSounds = new JarvisSounds();
