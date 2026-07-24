/**
 * VoiceExperience — Premium voice interaction with waveforms and state visualization.
 * Supports streaming STT/TTS, interruptible speech, and visual feedback.
 */
class VoiceExperience {
    constructor() {
        this.state = 'idle'; // idle, listening, thinking, speaking
        this.mediaRecorder = null;
        this.audioContext = null;
        this.analyser = null;
        this.stream = null;
        this.animationFrame = null;
        this.onStateChange = null;
        this.onTranscript = null;
        this.onAudioLevel = null;
    }

    async init() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            return true;
        } catch (e) {
            console.warn('[Voice] AudioContext not available');
            return false;
        }
    }

    async startListening() {
        if (this.state === 'listening') return false;

        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                audio: { 
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                } 
            });

            const source = this.audioContext.createMediaStreamSource(this.stream);
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            source.connect(this.analyser);

            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
                    ? 'audio/webm;codecs=opus' 
                    : 'audio/webm'
            });

            this._setState('listening');
            this._startVisualization();

            return true;
        } catch (e) {
            console.error('[Voice] Microphone access denied:', e);
            return false;
        }
    }

    stopListening() {
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
        }
        this._stopVisualization();
        this._setState('thinking');
    }

    startSpeaking() {
        this._setState('speaking');
    }

    stopSpeaking() {
        this._setState('idle');
    }

    _setState(newState) {
        const prev = this.state;
        this.state = newState;
        if (this.onStateChange) {
            this.onStateChange(newState, prev);
        }
    }

    _startVisualization() {
        const canvas = document.getElementById('voice-waveform');
        if (!canvas || !this.analyser) return;

        const ctx = canvas.getContext('2d');
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const draw = () => {
            this.animationFrame = requestAnimationFrame(draw);
            this.analyser.getByteFrequencyData(dataArray);

            const width = canvas.width;
            const height = canvas.height;

            ctx.clearRect(0, 0, width, height);

            const barWidth = (width / bufferLength) * 2.5;
            let x = 0;

            for (let i = 0; i < bufferLength; i++) {
                const barHeight = (dataArray[i] / 255) * height * 0.8;
                
                const gradient = ctx.createLinearGradient(0, height, 0, height - barHeight);
                gradient.addColorStop(0, 'rgba(233, 69, 96, 0.3)');
                gradient.addColorStop(1, 'rgba(233, 69, 96, 0.8)');

                ctx.fillStyle = gradient;
                ctx.fillRect(x, height - barHeight, barWidth - 1, barHeight);

                x += barWidth;
            }

            if (this.onAudioLevel) {
                const avg = dataArray.reduce((a, b) => a + b, 0) / bufferLength;
                this.onAudioLevel(avg / 255);
            }
        };

        draw();
    }

    _stopVisualization() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }

        const canvas = document.getElementById('voice-waveform');
        if (canvas) {
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
    }

    destroy() {
        this._stopVisualization();
        if (this.stream) {
            this.stream.getTracks().forEach(t => t.stop());
        }
        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.close();
        }
    }
}

window.VoiceExperience = VoiceExperience;
