/* JARVIS State Machine — v6.4.0 Living Intelligence */

class JarvisState {
    constructor() {
        this.current = 'idle';
        this.previous = 'idle';
        this.listeners = [];
        this.history = [];
        this.maxHistory = 50;
        this.transitionTime = Date.now();
        this.lastRaw = 'idle';
    }

    // Golden-rule canonical states: every requested state collapses to one of these.
    static CANONICAL = ['idle', 'listening', 'thinking', 'planning', 'working', 'verifying', 'speaking', 'error'];

    // Aliases so existing callers keep working while the visual surface stays canonical.
    static ALIASES = {
        retrieving: 'working',
        delegating: 'working',
        mission_active: 'working',
        researching: 'working',
        coding: 'working',
        reviewing: 'verifying',
        complete: 'idle',
        success: 'idle',
        warning: 'error'
    };

    set(state) {
        const canonical = JarvisState.ALIASES[state] || state;
        if (!JarvisState.CANONICAL.includes(canonical)) return;
        this.lastRaw = state;
        this.previous = this.current;
        this.current = canonical;
        this.transitionTime = Date.now();

        this.history.push({
            from: this.previous,
            to: canonical,
            raw: state,
            timestamp: Date.now()
        });
        if (this.history.length > this.maxHistory) {
            this.history.shift();
        }

        this.listeners.forEach(fn => {
            try { fn(canonical, this.previous); }
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
    startVerifying() { this.set('verifying'); }
    complete() { this.set('complete'); }
    setError() { this.set('error'); }
    missionActive() { this.set('mission_active'); }
    startResearching() { this.set('researching'); }
    startCoding() { this.set('coding'); }
    setSuccess() { this.set('success'); }
    setWarning() { this.set('warning'); }

    reset() { this.set('idle'); this.history = []; }
}

window.JarvisState = JarvisState;
