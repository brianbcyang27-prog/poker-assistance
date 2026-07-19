/**
 * JARVIS Voice - Web Speech API Integration
 * Triggers state changes for visualization
 */

let recognition = null;
let _isRecognizing = false;

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
        if (window.jarvisState) {
            window.jarvisState.startListening();
        }
    };

    recognition.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }
        document.getElementById('message-input').value = transcript;
    };

    recognition.onend = () => {
        _isRecognizing = false;
        document.getElementById('mic-btn').classList.remove('active');
        if (window.jarvisState) {
            window.jarvisState.set('idle');
        }
        const input = document.getElementById('message-input');
        if (input.value.trim()) {
            sendMessage();
        }
    };

    recognition.onerror = (event) => {
        console.warn('Speech recognition error:', event.error);
        _isRecognizing = false;
        document.getElementById('mic-btn').classList.remove('active');
        if (window.jarvisState) {
            window.jarvisState.set('idle');
        }
    };
}

function toggleVoice() {
    if (!recognition) {
        alert('Speech recognition not supported in this browser. Use Chrome or Edge.');
        return;
    }

    const btn = document.getElementById('mic-btn');
    if (_isRecognizing) {
        recognition.stop();
        btn.classList.remove('active');
    } else {
        btn.classList.add('active');
        recognition.start();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initSpeechRecognition();

    // Initialize audio analyzer
    if (window.audioAnalyzer) {
        window.audioAnalyzer.init();
    }
});
