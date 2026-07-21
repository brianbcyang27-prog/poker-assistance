/* JARVIS State Machine — v6.4.0 Living Intelligence */

class JarvisState {
    constructor() {
        this.current = 'idle';
        this.previous = 'idle';
        this.listeners = [];
        this.history = [];
        this.maxHistory = 50;
        this.transitionTime = Date.now();
    }

    set(state) {
        const validStates = [
            'idle', 'listening', 'thinking', 'speaking', 'working',
            'retrieving', 'planning', 'delegating', 'reviewing',
            'complete', 'error', 'mission_active'
        ];
        if (!validStates.includes(state)) return;

        this.previous = this.current;
        this.current = state;
        this.transitionTime = Date.now();

        this.history.push({
            from: this.previous,
            to: state,
            timestamp: Date.now()
        });
        if (this.history.length > this.maxHistory) {
            this.history.shift();
        }

        this.listeners.forEach(fn => {
            try { fn(state, this.previous); }
            catch (e) { console.error('State listener error:', e); }
        });
    }

    get() { return this.current; }
    getPrevious() { return this.previous; }
    getTransitionAge() { return Date.now() - this.transitionTime; }
    getHistory() { return [...this.history]; }

    onStateChange(fn) { this.listeners.push(fn); }
    offStateChange(fn) { this.listeners = this.listeners.filter(l => l !== fn); }

    startListening() { this.set('listening'); }
    stopListening() { this.set('idle'); }
    startThinking() { this.set('thinking'); }
    startSpeaking() { this.set('speaking'); }
    stopSpeaking() { this.set('idle'); }
    startWorking() { this.set('working'); }
    stopWorking() { this.set('idle'); }
    startRetrieving() { this.set('retrieving'); }
    startPlanning() { this.set('planning'); }
    startDelegating() { this.set('delegating'); }
    startReviewing() { this.set('reviewing'); }
    complete() { this.set('complete'); }
    setError() { this.set('error'); }
    missionActive() { this.set('mission_active'); }

    reset() { this.set('idle'); this.history = []; }
}

window.JarvisState = JarvisState;
