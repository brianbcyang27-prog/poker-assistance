/**
 * JARVIS State Machine v4.0
 * Expanded emotional states for the gold particle sphere
 */

class JarvisState {
    constructor() {
        this.current = 'idle';
        this.previous = 'idle';
        this.listeners = [];
        this.validStates = [
            'idle',
            'listening',
            'thinking',
            'speaking',
            'working',
            'planning',
            'mission_complete',
            'error'
        ];
    }

    set(state) {
        if (state === this.current) return;
        if (!this.validStates.includes(state)) return;

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

    startListening()  { this.set('listening'); }
    stopListening()   { this.set('idle'); }
    startThinking()   { this.set('thinking'); }
    startSpeaking()   { this.set('speaking'); }
    stopSpeaking()    { this.set('idle'); }
    startWorking()    { this.set('working'); }
    stopWorking()     { this.set('idle'); }
    startPlanning()   { this.set('planning'); }
    missionComplete() { this.set('mission_complete'); }
    reportError()     { this.set('error'); }
}

window.JarvisState = JarvisState;
