/**
 * Memory Galaxy — v3.2.0
 *
 * Spatial visualization of the memory system as a 3D galaxy.
 * Memories are stars, clusters are related groups.
 * Shows connections between related memories via faint lines.
 *
 * Uses Three.js from the existing vendor bundle.
 */

class MemoryGalaxy {
    constructor(container) {
        this.container = container;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.stars = [];
        this.connections = [];
        this._running = false;
        this._frameId = null;
        this._mouse = { x: 0, y: 0 };
        this._rotation = { x: 0, y: 0 };
        this._targetRotation = { x: 0, y: 0 };
    }

    init() {
        if (!this.container || !window.THREE) return;

        const w = this.container.clientWidth;
        const h = this.container.clientHeight;

        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x050b14);

        // Camera
        this.camera = new THREE.PerspectiveCamera(60, w / h, 0.1, 1000);
        this.camera.position.z = 100;

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.renderer.setSize(w, h);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.container.appendChild(this.renderer.domElement);

        // Star field (background)
        this._createStarField();

        // Mouse interaction
        this.container.addEventListener('mousemove', (e) => {
            const rect = this.container.getBoundingClientRect();
            this._mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
            this._mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
        });

        window.addEventListener('resize', () => this._resize());
    }

    _createStarField() {
        const geo = new THREE.BufferGeometry();
        const count = 500;
        const positions = new Float32Array(count * 3);

        for (let i = 0; i < count * 3; i++) {
            positions[i] = (Math.random() - 0.5) * 400;
        }

        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const mat = new THREE.PointsMaterial({
            color: 0x334466,
            size: 0.3,
            transparent: true,
            opacity: 0.6,
        });

        this.scene.add(new THREE.Points(geo, mat));
    }

    /**
     * Load memories from API and create galaxy
     */
    async loadMemories() {
        try {
            const res = await fetch('/api/memory?limit=200');
            if (!res.ok) return;
            const memories = await res.json();
            this._buildGalaxy(memories);
        } catch (_) {}
    }

    _buildGalaxy(memories) {
        // Clear old stars
        for (const s of this.stars) this.scene.remove(s);
        this.stars = [];
        for (const c of this.connections) this.scene.remove(c);
        this.connections = [];

        if (!memories.length) return;

        // Color by source
        const sourceColors = {
            conversation: 0x00f0ff,
            reflection: 0x8844ff,
            task: 0xffaa00,
            file: 0x00cc66,
            system: 0xff3366,
        };

        // Position memories in a spiral galaxy layout
        const count = memories.length;
        const goldenAngle = Math.PI * (3 - Math.sqrt(5));

        for (let i = 0; i < count; i++) {
            const mem = memories[i];
            const t = i / count;

            // Spiral position
            const radius = Math.sqrt(t) * 50;
            const angle = i * goldenAngle;
            const x = radius * Math.cos(angle);
            const z = radius * Math.sin(angle);
            const y = (Math.random() - 0.5) * 10 * (1 - t);

            // Size based on importance/access count
            const importance = mem.importance || 0.5;
            const size = 0.5 + importance * 2;

            // Color
            const color = sourceColors[mem.source] || 0x00f0ff;

            const geo = new THREE.SphereGeometry(size, 8, 8);
            const mat = new THREE.MeshBasicMaterial({
                color,
                transparent: true,
                opacity: 0.6 + importance * 0.4,
            });

            const mesh = new THREE.Mesh(geo, mat);
            mesh.position.set(x, y, z);
            mesh.userData = { memory: mem, index: i };

            this.scene.add(mesh);
            this.stars.push(mesh);
        }

        // Draw some connection lines between related memories
        for (let i = 0; i < Math.min(count, 50); i++) {
            const a = this.stars[i];
            if (!a) continue;
            // Find nearest neighbor
            let nearest = null;
            let minDist = Infinity;
            for (let j = i + 1; j < Math.min(count, 50); j++) {
                const b = this.stars[j];
                if (!b) continue;
                const d = a.position.distanceTo(b.position);
                if (d < minDist) { minDist = d; nearest = b; }
            }
            if (nearest && minDist < 25) {
                const pts = [a.position, nearest.position];
                const geo = new THREE.BufferGeometry().setFromPoints(pts);
                const mat = new THREE.LineBasicMaterial({
                    color: 0x1a3355,
                    transparent: true,
                    opacity: 0.2,
                });
                const line = new THREE.Line(geo, mat);
                this.scene.add(line);
                this.connections.push(line);
            }
        }
    }

    _resize() {
        if (!this.container || !this.camera || !this.renderer) return;
        const w = this.container.clientWidth;
        const h = this.container.clientHeight;
        this.camera.aspect = w / h;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(w, h);
    }

    start() {
        if (this._running) return;
        this._running = true;
        this._animate();
    }

    stop() {
        this._running = false;
        if (this._frameId) cancelAnimationFrame(this._frameId);
    }

    _animate() {
        if (!this._running) return;
        this._frameId = requestAnimationFrame(() => this._animate());

        // Gentle rotation following mouse
        this._targetRotation.y += 0.001;
        this._targetRotation.x = this._mouse.y * 0.3;
        this._targetRotation.y += this._mouse.x * 0.01;

        this._rotation.x += (this._targetRotation.x - this._rotation.x) * 0.02;
        this._rotation.y += (this._targetRotation.y - this._rotation.y) * 0.02;

        if (this.scene) {
            this.scene.rotation.x = this._rotation.x;
            this.scene.rotation.y = this._rotation.y;
        }

        // Pulse stars gently
        for (const star of this.stars) {
            star.material.opacity = 0.5 + 0.3 * Math.sin(Date.now() * 0.001 + star.userData.index);
        }

        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }
    }

    destroy() {
        this.stop();
        if (this.renderer) {
            this.renderer.dispose();
            if (this.renderer.domElement && this.renderer.domElement.parentNode) {
                this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
            }
        }
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.stars = [];
        this.connections = [];
    }
}

window.MemoryGalaxy = MemoryGalaxy;
