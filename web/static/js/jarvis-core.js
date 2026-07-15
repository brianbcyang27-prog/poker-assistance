/**
 * JARVIS Core - Neural Memory Particle Visualization
 * Three.js powered holographic AI core
 */

class JarvisCore {
    constructor(container) {
        this.container = container;
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.particleCount = 2000;
        this.coreRadius = 2.0;
        this.state = 'idle';
        this.time = 0;
        this.mouse = { x: 0, y: 0 };

        // Audio reactive properties
        this.audioVolume = 0;
        this.audioFrequency = 0;
        this.audioPitch = 0;
        this.targetScale = 1.0;
        this.currentScale = 1.0;

        // State targets
        this.targetRotationSpeed = 0.001;
        this.currentRotationSpeed = 0.001;
        this.targetChaos = 0;
        this.currentChaos = 0;
        this.targetBrightness = 0.6;
        this.currentBrightness = 0.6;

        this.init();
    }

    init() {
        // Scene
        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.FogExp2(0x000510, 0.08);

        // Camera
        this.camera = new THREE.PerspectiveCamera(60, this.width / this.height, 0.1, 100);
        this.camera.position.z = 5;

        // Renderer
        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true,
            powerPreference: 'high-performance'
        });
        this.renderer.setSize(this.width, this.height);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.setClearColor(0x000510, 1);
        this.container.appendChild(this.renderer.domElement);

        // Post-processing
        this.setupPostProcessing();

        // Particles
        this.createParticles();

        // Inner glow sphere
        this.createInnerGlow();

        // Outer ring
        this.createOuterRing();

        // Neural connections
        this.createNeuralConnections();

        // Ambient particles
        this.createAmbientParticles();

        // Events
        window.addEventListener('resize', () => this.onResize());
        window.addEventListener('mousemove', (e) => this.onMouseMove(e));

        // Start animation
        this.animate();
    }

    setupPostProcessing() {
        this.renderScene = new THREE.RenderPass(this.scene, this.camera);

        this.bloomPass = new THREE.UnrealBloomPass(
            new THREE.Vector2(this.width, this.height),
            1.5,   // strength
            0.4,   // radius
            0.85   // threshold
        );

        this.composer = new THREE.EffectComposer(this.renderer);
        this.composer.addPass(this.renderScene);
        this.composer.addPass(this.bloomPass);
    }

    createParticles() {
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(this.particleCount * 3);
        const colors = new Float32Array(this.particleCount * 3);
        const sizes = new Float32Array(this.particleCount);
        const velocities = new Float32Array(this.particleCount * 3);
        const offsets = new Float32Array(this.particleCount);

        for (let i = 0; i < this.particleCount; i++) {
            const i3 = i * 3;

            // Distribute on sphere with some variation
            const phi = Math.acos(2 * Math.random() - 1);
            const theta = Math.random() * Math.PI * 2;
            const r = this.coreRadius * (0.8 + Math.random() * 0.4);

            positions[i3] = r * Math.sin(phi) * Math.cos(theta);
            positions[i3 + 1] = r * Math.sin(phi) * Math.sin(theta);
            positions[i3 + 2] = r * Math.cos(phi);

            // Cyan/blue holographic colors
            const hue = 0.55 + Math.random() * 0.1;  // cyan range
            const saturation = 0.7 + Math.random() * 0.3;
            const lightness = 0.4 + Math.random() * 0.3;
            const color = new THREE.Color().setHSL(hue, saturation, lightness);
            colors[i3] = color.r;
            colors[i3 + 1] = color.g;
            colors[i3 + 2] = color.b;

            sizes[i] = Math.random() * 3 + 1;

            // Random velocity for organic movement
            velocities[i3] = (Math.random() - 0.5) * 0.01;
            velocities[i3 + 1] = (Math.random() - 0.5) * 0.01;
            velocities[i3 + 2] = (Math.random() - 0.5) * 0.01;

            offsets[i] = Math.random() * Math.PI * 2;
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

        this.particleVelocities = velocities;
        this.particleOffsets = offsets;
        this.particleGeometry = geometry;

        const material = new THREE.ShaderMaterial({
            uniforms: {
                time: { value: 0 },
                brightness: { value: 0.6 },
                volume: { value: 0 }
            },
            vertexShader: `
                attribute float size;
                attribute vec3 color;
                varying vec3 vColor;
                varying float vBrightness;
                uniform float time;
                uniform float brightness;
                uniform float volume;

                void main() {
                    vColor = color;
                    vBrightness = brightness;

                    vec3 pos = position;
                    float scale = 1.0 + volume * 0.3;
                    pos *= scale;

                    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
                    gl_PointSize = size * (300.0 / -mvPosition.z) * (1.0 + volume * 0.5);
                    gl_Position = projectionMatrix * mvPosition;
                }
            `,
            fragmentShader: `
                varying vec3 vColor;
                varying float vBrightness;

                void main() {
                    float dist = length(gl_PointCoord - vec2(0.5));
                    if (dist > 0.5) discard;

                    float alpha = 1.0 - smoothstep(0.0, 0.5, dist);
                    alpha *= vBrightness;

                    vec3 glow = vColor * 1.5;
                    gl_FragColor = vec4(glow, alpha);
                }
            `,
            transparent: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });

        this.particles = new THREE.Points(geometry, material);
        this.scene.add(this.particles);
    }

    createInnerGlow() {
        const geometry = new THREE.SphereGeometry(this.coreRadius * 0.4, 32, 32);
        const material = new THREE.ShaderMaterial({
            uniforms: {
                time: { value: 0 },
                color: { value: new THREE.Color(0x00d4ff) },
                volume: { value: 0 }
            },
            vertexShader: `
                varying vec3 vNormal;
                varying vec3 vPosition;
                void main() {
                    vNormal = normalize(normalMatrix * normal);
                    vPosition = position;
                    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                }
            `,
            fragmentShader: `
                uniform float time;
                uniform vec3 color;
                uniform float volume;
                varying vec3 vNormal;
                varying vec3 vPosition;

                void main() {
                    float intensity = pow(0.65 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.0);
                    float pulse = 1.0 + sin(time * 2.0) * 0.1 + volume * 0.4;
                    vec3 glow = color * intensity * pulse;
                    gl_FragColor = vec4(glow, intensity * 0.6);
                }
            `,
            transparent: true,
            blending: THREE.AdditiveBlending,
            side: THREE.BackSide,
            depthWrite: false
        });

        this.innerGlow = new THREE.Mesh(geometry, material);
        this.scene.add(this.innerGlow);
    }

    createOuterRing() {
        const geometry = new THREE.TorusGeometry(this.coreRadius * 1.3, 0.02, 16, 100);
        const material = new THREE.MeshBasicMaterial({
            color: 0x00d4ff,
            transparent: true,
            opacity: 0.3
        });

        this.outerRing = new THREE.Mesh(geometry, material);
        this.outerRing.rotation.x = Math.PI / 2;
        this.scene.add(this.outerRing);

        // Second ring
        const geometry2 = new THREE.TorusGeometry(this.coreRadius * 1.5, 0.01, 16, 100);
        const material2 = new THREE.MeshBasicMaterial({
            color: 0x0088cc,
            transparent: true,
            opacity: 0.15
        });

        this.outerRing2 = new THREE.Mesh(geometry2, material2);
        this.outerRing2.rotation.x = Math.PI / 3;
        this.outerRing2.rotation.y = Math.PI / 4;
        this.scene.add(this.outerRing2);
    }

    createNeuralConnections() {
        const lineCount = 50;
        const positions = new Float32Array(lineCount * 6);
        const colors = new Float32Array(lineCount * 6);

        for (let i = 0; i < lineCount; i++) {
            const i6 = i * 6;

            // Random points on sphere surface
            const phi1 = Math.acos(2 * Math.random() - 1);
            const theta1 = Math.random() * Math.PI * 2;
            const phi2 = Math.acos(2 * Math.random() - 1);
            const theta2 = Math.random() * Math.PI * 2;

            const r = this.coreRadius;

            positions[i6] = r * Math.sin(phi1) * Math.cos(theta1);
            positions[i6 + 1] = r * Math.sin(phi1) * Math.sin(theta1);
            positions[i6 + 2] = r * Math.cos(phi1);

            positions[i6 + 3] = r * Math.sin(phi2) * Math.cos(theta2);
            positions[i6 + 4] = r * Math.sin(phi2) * Math.sin(theta2);
            positions[i6 + 5] = r * Math.cos(phi2);

            const color = new THREE.Color(0x00d4ff);
            colors[i6] = color.r;
            colors[i6 + 1] = color.g;
            colors[i6 + 2] = color.b;
            colors[i6 + 3] = color.r;
            colors[i6 + 4] = color.g;
            colors[i6 + 5] = color.b;
        }

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        const material = new THREE.LineBasicMaterial({
            vertexColors: true,
            transparent: true,
            opacity: 0.15,
            blending: THREE.AdditiveBlending
        });

        this.neuralLines = new THREE.LineSegments(geometry, material);
        this.scene.add(this.neuralLines);
    }

    createAmbientParticles() {
        const count = 500;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(count * 3);

        for (let i = 0; i < count; i++) {
            const i3 = i * 3;
            positions[i3] = (Math.random() - 0.5) * 20;
            positions[i3 + 1] = (Math.random() - 0.5) * 20;
            positions[i3 + 2] = (Math.random() - 0.5) * 20;
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const material = new THREE.PointsMaterial({
            color: 0x00d4ff,
            size: 0.02,
            transparent: true,
            opacity: 0.3,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });

        this.ambientParticles = new THREE.Points(geometry, material);
        this.scene.add(this.ambientParticles);
    }

    setState(newState) {
        if (this.state === newState) return;
        this.state = newState;

        switch (newState) {
            case 'idle':
                this.targetRotationSpeed = 0.001;
                this.targetChaos = 0;
                this.targetBrightness = 0.6;
                this.bloomPass.strength = 1.5;
                break;
            case 'listening':
                this.targetRotationSpeed = 0.002;
                this.targetChaos = 0.2;
                this.targetBrightness = 0.8;
                this.bloomPass.strength = 1.8;
                break;
            case 'thinking':
                this.targetRotationSpeed = 0.005;
                this.targetChaos = 0.8;
                this.targetBrightness = 1.0;
                this.bloomPass.strength = 2.2;
                break;
            case 'speaking':
                this.targetRotationSpeed = 0.003;
                this.targetChaos = 0.3;
                this.targetBrightness = 0.9;
                this.bloomPass.strength = 2.0;
                break;
            case 'working':
                this.targetRotationSpeed = 0.004;
                this.targetChaos = 0.6;
                this.targetBrightness = 1.0;
                this.bloomPass.strength = 2.5;
                break;
        }
    }

    setAudio(volume, frequency, pitch) {
        this.audioVolume = volume;
        this.audioFrequency = frequency;
        this.audioPitch = pitch;
        this.targetScale = 1.0 + volume * 0.5;
    }

    onResize() {
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.camera.aspect = this.width / this.height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(this.width, this.height);
        this.composer.setSize(this.width, this.height);
    }

    onMouseMove(event) {
        this.mouse.x = (event.clientX / this.width) * 2 - 1;
        this.mouse.y = -(event.clientY / this.height) * 2 + 1;
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        this.time += 0.016;

        // Smooth interpolation
        this.currentRotationSpeed += (this.targetRotationSpeed - this.currentRotationSpeed) * 0.05;
        this.currentChaos += (this.targetChaos - this.currentChaos) * 0.05;
        this.currentBrightness += (this.targetBrightness - this.currentBrightness) * 0.05;
        this.currentScale += (this.targetScale - this.currentScale) * 0.1;

        // Rotate particles
        this.particles.rotation.y += this.currentRotationSpeed;
        this.particles.rotation.x = this.mouse.y * 0.1;
        this.particles.rotation.z = this.mouse.x * 0.05;

        // Update particle positions with chaos
        const positions = this.particleGeometry.attributes.position.array;
        for (let i = 0; i < this.particleCount; i++) {
            const i3 = i * 3;
            const offset = this.particleOffsets[i];

            // Orbital motion
            const angle = this.time * 0.5 + offset;
            const orbitalX = Math.sin(angle) * this.currentChaos * 0.1;
            const orbitalY = Math.cos(angle) * this.currentChaos * 0.1;

            // Breathing effect
            const breathe = Math.sin(this.time * 1.5 + offset) * 0.05;

            // Apply chaos displacement
            positions[i3] += (orbitalX + this.particleVelocities[i3] * this.currentChaos) * 0.1;
            positions[i3 + 1] += (orbitalY + this.particleVelocities[i3 + 1] * this.currentChaos) * 0.1;
            positions[i3 + 2] += breathe;

            // Keep particles on sphere surface
            const x = positions[i3];
            const y = positions[i3 + 1];
            const z = positions[i3 + 2];
            const dist = Math.sqrt(x * x + y * y + z * z);
            const targetDist = this.coreRadius * (0.8 + Math.sin(this.time + offset) * 0.1);

            if (dist > 0) {
                const scale = targetDist / dist;
                positions[i3] *= scale;
                positions[i3 + 1] *= scale;
                positions[i3 + 2] *= scale;
            }
        }
        this.particleGeometry.attributes.position.needsUpdate = true;

        // Update shader uniforms
        this.particles.material.uniforms.time.value = this.time;
        this.particles.material.uniforms.brightness.value = this.currentBrightness;
        this.particles.material.uniforms.volume.value = this.audioVolume;

        // Inner glow
        this.innerGlow.material.uniforms.time.value = this.time;
        this.innerGlow.material.uniforms.volume.value = this.audioVolume;
        const glowScale = this.currentScale * (1.0 + this.audioVolume * 0.3);
        this.innerGlow.scale.setScalar(glowScale);

        // Outer rings
        this.outerRing.rotation.z += 0.002;
        this.outerRing2.rotation.z -= 0.001;
        this.outerRing.scale.setScalar(this.currentScale);
        this.outerRing2.scale.setScalar(this.currentScale * 0.9);

        // Neural connections
        this.neuralLines.material.opacity = 0.1 + this.currentChaos * 0.3;
        this.neuralLines.rotation.y += this.currentRotationSpeed * 0.5;

        // Ambient particles drift
        this.ambientParticles.rotation.y += 0.0002;
        this.ambientParticles.rotation.x += 0.0001;

        // Render
        this.composer.render();
    }
}

// Export
window.JarvisCore = JarvisCore;
