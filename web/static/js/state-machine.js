/**
 * JARVIS State Machine
 * Manages visualization states and transitions
 */

class JarvisState {
    constructor() {
        this.current = 'idle';
        this.previous = 'idle';
        this.listeners = [];
        this.transitionTimeout = null;
    }

    set(state) {
        if (state === this.current) return;
        if (!['idle', 'listening', 'thinking', 'speaking', 'working'].includes(state)) return;

        this.previous = this.current;
        this.current = state;

        this.listeners.forEach(fn => fn(state, this.previous));
    }

    get() {
        return this.current;
    }

    onStateChange(fn) {
        this.listeners.push(fn);
    }

    // Auto-transition helpers
    startListening() {
        this.set('listening');
    }

    stopListening() {
        this.set('idle');
    }

    startThinking() {
        this.set('thinking');
    }

    startSpeaking() {
        this.set('speaking');
    }

    stopSpeaking() {
        this.set('idle');
    }

    startWorking() {
        this.set('working');
    }

    stopWorking() {
        this.set('idle');
    }
}

window.JarvisState = JarvisState;
