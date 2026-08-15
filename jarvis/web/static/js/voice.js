/* JARVIS Voice — Web Speech + TTS orchestration (v9.2.0 Voice First)
 * Push-to-talk + click toggle, natural interruption (barge-in),
 * voice-activity indication via AudioAnalyzer, and a speak-aloud helper.
 * Golden Core stays synchronized through jarvisState (single source of truth).
 */

let recognition = null;
let _isRecognizing = false;
let _speaking = false;
let _currentAudio = null;
let _pttDown = null;
let _pttHeld = false;
let _vadRaf = null;

function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn('Speech recognition not supported');
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
        _isRecognizing = true;
        const btn = document.getElementById('mic-btn');
        if (btn) btn.classList.add('listening');
        if (window.jarvisState) window.jarvisState.startListening();
        _startVadMonitor();
    };

    recognition.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }
        const input = document.getElementById('message-input');
        if (input) input.value = transcript;
        // Natural interruption: the moment the user speaks, cut off JARVIS.
        jarvisStopSpeaking();
    };

    recognition.onend = () => {
        _isRecognizing = false;
        _stopVadMonitor();
        const btn = document.getElementById('mic-btn');
        if (btn) {
            btn.classList.remove('listening');
            btn.style.removeProperty('--voice-level');
        }
        if (window.jarvisState && !_speaking) window.jarvisState.set('idle');
        const input = document.getElementById('message-input');
        if (input && input.value.trim() && !_pttHeld) {
            window.jarvisLastInputViaVoice = true;
            sendMessage();
        }
    };

    recognition.onerror = (event) => {
        console.warn('Speech recognition error:', event.error);
        _isRecognizing = false;
        _stopVadMonitor();
        const btn = document.getElementById('mic-btn');
        if (btn) {
            btn.classList.remove('listening');
            btn.style.removeProperty('--voice-level');
        }
        if (window.jarvisState && !_speaking) window.jarvisState.set('idle');
    };
}

function startVoiceInput() {
    if (!recognition) return;
    if (_isRecognizing) return;
    jarvisStopSpeaking();
    try {
        recognition.start();
    } catch (e) {
        console.warn('Speech recognition start failed:', e);
    }
}

function stopVoiceInput() {
    if (!recognition) return;
    if (!_isRecognizing) return;
    try {
        recognition.stop();
    } catch (e) {
        console.warn('Speech recognition stop failed:', e);
    }
}

function toggleVoice() {
    if (!recognition) {
        console.warn('Speech recognition not supported in this browser. Use Chrome or Edge.');
        return;
    }
    if (_isRecognizing) {
        stopVoiceInput();
    } else {
        startVoiceInput();
    }
}

function _wirePushToTalk() {
    const btn = document.getElementById('mic-btn');
    if (!btn) return;

    btn.addEventListener('pointerdown', (e) => {
        if (e.pointerType === 'mouse' && e.button !== 0) return;
        _pttDown = Date.now();
        _pttHeld = false;
        startVoiceInput();
    });

    btn.addEventListener('pointerup', () => {
        if (_pttDown === null) return;
        const held = Date.now() - _pttDown;
        _pttDown = null;
        if (held >= 400) {
            _pttHeld = true;
            stopVoiceInput();
        }
    });

    btn.addEventListener('pointerleave', () => {
        if (_pttDown !== null) {
            _pttDown = null;
            _pttHeld = true;
            stopVoiceInput();
        }
    });

    btn.addEventListener('click', (e) => {
        if (_pttHeld) {
            _pttHeld = false;
            e.preventDefault();
            return;
        }
        toggleVoice();
    });
}

function _startVadMonitor() {
    if (_vadRaf) return;
    const btn = document.getElementById('mic-btn');
    if (!window.audioAnalyzer) return;

    const loop = () => {
        if (!_isRecognizing) { _vadRaf = null; return; }
        if (window.audioAnalyzer.isActive) {
            const v = window.audioAnalyzer.getValues().volume || 0;
            const level = Math.min(1, v * 6);
            btn.style.setProperty('--voice-level', String(level));
            btn.classList.toggle('voice-active', level > 0.08);
        }
        _vadRaf = requestAnimationFrame(loop);
    };
    _vadRaf = requestAnimationFrame(loop);
}

function _stopVadMonitor() {
    if (_vadRaf) {
        cancelAnimationFrame(_vadRaf);
        _vadRaf = null;
    }
    const btn = document.getElementById('mic-btn');
    if (btn) btn.classList.remove('voice-active');
}

async function _ensureAnalyzerMic() {
    if (!window.audioAnalyzer) return;
    if (window.audioAnalyzer.isActive) return;
    try {
        await window.audioAnalyzer.connectMicrophone();
    } catch (e) {
        console.warn('Voice-activity monitor unavailable:', e);
    }
}

function jarvisStopSpeaking() {
    if (_currentAudio) {
        try { _currentAudio.pause(); _currentAudio = null; } catch (e) {}
    }
    _speaking = false;
    if (window.jarvisState && window.jarvisState.get() === 'speaking') {
        window.jarvisState.set('idle');
    }
}

async function jarvisSpeak(text) {
    if (!text || !text.trim()) return;
    try {
        jarvisStopSpeaking();
        const form = new FormData();
        form.append('text', text);
        const res = await fetch('/api/voice/generate', { method: 'POST', body: form });
        if (!res.ok) {
            console.warn('TTS generate failed:', res.status);
            return;
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        _currentAudio = audio;
        _speaking = true;
        if (window.jarvisState) window.jarvisState.startSpeaking();

        audio.onended = () => {
            jarvisStopSpeaking();
            URL.revokeObjectURL(url);
        };
        audio.onerror = () => {
            jarvisStopSpeaking();
            URL.revokeObjectURL(url);
        };
        await audio.play();
    } catch (e) {
        console.warn('jarvisSpeak failed:', e);
    }
}

function initVoice() {
    initSpeechRecognition();
    _wirePushToTalk();
    _ensureAnalyzerMic();

    if (window.audioAnalyzer) {
        window.audioAnalyzer.init();
    }

    const btn = document.getElementById('mic-btn');
    if (btn && recognition) {
        btn.addEventListener('pointerdown', () => { _ensureAnalyzerMic(); }, { once: true });
    }
}

window.jarvisSpeak = jarvisSpeak;
window.jarvisStopSpeaking = jarvisStopSpeaking;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initVoice);
} else {
    initVoice();
}
