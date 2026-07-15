/**
 * JARVIS Audio Analyzer
 * Extracts volume, frequency, and pitch from audio
 */

class AudioAnalyzer {
    constructor() {
        this.audioContext = null;
        this.analyser = null;
        this.source = null;
        this.isActive = false;
        this.volume = 0;
        this.frequency = 0;
        this.pitch = 0;
        this.smoothVolume = 0;
        this.smoothFrequency = 0;
        this.smoothPitch = 0;

        // dataArray for frequency analysis
        this.dataArray = null;
        this.frequencyData = null;
    }

    async init() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 2048;
            this.analyser.smoothingTimeConstant = 0.8;

            const bufferLength = this.analyser.frequencyBinCount;
            this.dataArray = new Uint8Array(bufferLength);
            this.frequencyData = new Float32Array(bufferLength);

            return true;
        } catch (e) {
            console.warn('AudioAnalyzer init failed:', e);
            return false;
        }
    }

    async connectMicrophone() {
        if (!this.audioContext) {
            await this.init();
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.source = this.audioContext.createMediaStreamSource(stream);
            this.source.connect(this.analyser);
            this.isActive = true;
            this.analyze();
            return true;
        } catch (e) {
            console.warn('Microphone access denied:', e);
            return false;
        }
    }

    connectAudioElement(audioElement) {
        if (!this.audioContext) {
            this.init();
        }

        if (this.source) {
            try { this.source.disconnect(); } catch (e) {}
        }

        this.source = this.audioContext.createMediaElementSource(audioElement);
        this.source.connect(this.analyser);
        this.analyser.connect(this.audioContext.destination);
        this.isActive = true;
        this.analyze();
    }

    analyze() {
        if (!this.isActive || !this.analyser) return;

        this.analyser.getByteTimeDomainData(this.dataArray);

        // Calculate RMS volume
        let sum = 0;
        for (let i = 0; i < this.dataArray.length; i++) {
            const normalized = (this.dataArray[i] - 128) / 128;
            sum += normalized * normalized;
        }
        this.volume = Math.sqrt(sum / this.dataArray.length);

        // Get frequency data
        this.analyser.getFloatFrequencyData(this.frequencyData);

        // Find dominant frequency
        let maxVal = -Infinity;
        let maxIndex = 0;
        for (let i = 0; i < this.frequencyData.length; i++) {
            if (this.frequencyData[i] > maxVal) {
                maxVal = this.frequencyData[i];
                maxIndex = i;
            }
        }
        this.frequency = maxIndex * this.audioContext.sampleRate / this.analyser.fftSize;

        // Estimate pitch (simplified)
        this.pitch = this.frequency / 1000; // Normalize to 0-1 range roughly

        // Smooth values
        this.smoothVolume += (this.volume - this.smoothVolume) * 0.2;
        this.smoothFrequency += (this.frequency - this.smoothFrequency) * 0.1;
        this.smoothPitch += (this.pitch - this.smoothPitch) * 0.15;

        requestAnimationFrame(() => this.analyze());
    }

    getValues() {
        return {
            volume: this.smoothVolume,
            frequency: this.smoothFrequency,
            pitch: this.smoothPitch,
            rawVolume: this.volume
        };
    }

    disconnect() {
        if (this.source) {
            try { this.source.disconnect(); } catch (e) {}
        }
        this.isActive = false;
    }
}

window.AudioAnalyzer = AudioAnalyzer;
