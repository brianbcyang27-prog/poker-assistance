/**
 * VisionExperience — Screen/camera capture with AI analysis and annotation overlay.
 */
class VisionExperience {
    constructor() {
        this.stream = null;
        this.videoEl = null;
        this.captureCanvas = null;
        this.isCapturing = false;
        this.onCapture = null;
        this.onAnalysis = null;
    }

    async startScreenCapture() {
        try {
            this.stream = await navigator.mediaDevices.getDisplayMedia({
                video: { cursor: 'always' },
                audio: false
            });
            this._attachStream();
            this.isCapturing = true;
            return true;
        } catch (e) {
            console.warn('[Vision] Screen capture denied:', e.message);
            return false;
        }
    }

    async startCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'user', width: 1280, height: 720 }
            });
            this._attachStream();
            this.isCapturing = true;
            return true;
        } catch (e) {
            console.warn('[Vision] Camera access denied:', e.message);
            return false;
        }
    }

    stopCapture() {
        if (this.stream) {
            this.stream.getTracks().forEach(t => t.stop());
            this.stream = null;
        }
        if (this.videoEl) {
            this.videoEl.srcObject = null;
        }
        this.isCapturing = false;
    }

    captureFrame() {
        if (!this.videoEl || !this.videoEl.videoWidth) return null;

        if (!this.captureCanvas) {
            this.captureCanvas = document.createElement('canvas');
        }

        const video = this.videoEl;
        this.captureCanvas.width = video.videoWidth;
        this.captureCanvas.height = video.videoHeight;

        const ctx = this.captureCanvas.getContext('2d');
        ctx.drawImage(video, 0, 0);

        const dataUrl = this.captureCanvas.toDataURL('image/jpeg', 0.85);

        if (this.onCapture) {
            this.onCapture(dataUrl);
        }

        return dataUrl;
    }

    annotateFrame(dataUrl, annotations) {
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement('canvas');
                canvas.width = img.width;
                canvas.height = img.height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0);

                if (annotations && annotations.length > 0) {
                    for (const ann of annotations) {
                        ctx.strokeStyle = ann.color || '#e94560';
                        ctx.lineWidth = ann.lineWidth || 3;
                        ctx.strokeRect(ann.x, ann.y, ann.w, ann.h);

                        if (ann.label) {
                            ctx.fillStyle = ann.color || '#e94560';
                            ctx.font = `bold ${ann.fontSize || 14}px system-ui`;
                            ctx.fillText(ann.label, ann.x, ann.y - 6);
                        }
                    }
                }

                resolve(canvas.toDataURL('image/jpeg', 0.85));
            };
            img.src = dataUrl;
        });
    }

    _attachStream() {
        if (!this.videoEl) {
            this.videoEl = document.getElementById('vision-video');
        }
        if (this.videoEl && this.stream) {
            this.videoEl.srcObject = this.stream;
            this.videoEl.play().catch(() => {});
        }
    }

    destroy() {
        this.stopCapture();
        this.captureCanvas = null;
    }
}

window.VisionExperience = VisionExperience;
