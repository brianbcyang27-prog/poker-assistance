/**
 * JARVIS Core - Gold Neural Particle Visualization
 * Three.js powered holographic AI core
 * 
 * Emotional States:
 *   idle          - Slow breathing, calm gold
 *   listening     - Particles move inward, focused
 *   thinking      - Fast orbiting, bright
 *   speaking      - Pulse with voice amplitude
 *   working       - Internal turbulence
 *   planning      - Energy streams
 *   mission_complete - Golden wave
 *   error         - Small red pulse
 */

class JarvisCore {
    constructor(container) {
        this.container = container;
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.particleCount = 2000;
        this.coreRadius = 2.0;
        this.state = 'idle';
        this.mode = 'workspace'; // 'workspace' or 'voice'
        this.time = 0;
        this.mouse = { x: 0, y: 0 };

        // Audio reactive
        this.audioVolume = 0;
        this.audioFrequency = 0;
        this.audioPitch = 0;
        this.targetScale = 1.0;
        this.currentScale = 1.0;

        // State interpolation targets
        this.targetRotationSpeed = 0.001;
        this.currentRotationSpeed = 0.001;
        this.targetChaos = 0;
        this.currentChaos = 0;
        this.targetBrightness = 0.6;
        this.currentBrightness = 0.6;
        this.targetBloom = 1.5;
        this.currentBloom = 1.5;

        // Gold color base
        this.baseColor = new THREE.Color(0xffd700);
        this.errorColor = new THREE.Color(0xff4466);

        this.init();
    }

    init() {
        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.FogExp2(0x000308, 0.06);

        this.camera = new THREE.PerspectiveCamera(60, this.width / this.height, 0.1, 100);
        this.camera.position.z = 5;

        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true,
            powerPreference: 'high-performance'
        });
        this.renderer.setSize(this.width, this.height);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.setClearColor(0x000308, 1);
        this.container.appendChild(this.renderer.domElement);

        this.setupPostProcessing();
        this.createParticles();
        this.createInnerGlow();
        this.createOuterRing();
        this.createNeuralConnections();
        this.createAmbientParticles();
        this.createEnergyStreams();

        window.addEventListener('resize', () => this.onResize());
        window.addEventListener('mousemove', (e) => this.onMouseMove(e));

        this.animate();
    }

    setupPostProcessing() {
        this.renderScene = new THREE.RenderPass(this.scene, this.camera);
        this.bloomPass = new THREE.UnrealBloomPass(
            new THREE.Vector2(this.width, this.height),
            1.5, 0.4, 0.85
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

            const phi = Math.acos(2 * Math.random() - 1);
            const theta = Math.random() * Math.PI * 2;
            const r = this.coreRadius * (0.8 + Math.random() * 0.4);

            positions[i3]     = r * Math.sin(phi) * Math.cos(theta);
            positions[i3 + 1] = r * Math.sin(phi) * Math.sin(theta);
            positions[i3 + 2] = r * Math.cos(phi);

            // Gold color palette: warm golds, slight variation
            const hue = 0.12 + Math.random() * 0.04;  // gold range (0.12 = 43deg)
            const saturation = 0.8 + Math.random() * 0.2;
            const lightness = 0.45 + Math.random() * 0.25;
            const color = new THREE.Color().setHSL(hue, saturation, lightness);
            colors[i3]     = color.r;
            colors[i3 + 1] = color.g;
            colors[i3 + 2] = color.b;

            sizes[i] = Math.random() * 3 + 1;

            velocities[i3]     = (Math.random() - 0.5) * 0.01;
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
        this.originalColors = new Float32Array(colors);

        const material = new THREE.ShaderMaterial({
            uniforms: {
                time: { value: 0 },
                brightness: { value: 0.6 },
                volume: { value: 0 },
                colorMix: { value: 0.0 }  // 0 = gold, 1 = error red
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
                uniform float colorMix;
                uniform vec3 baseColor;  // not used directly, colors are per-particle

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
                color: { value: new THREE.Color(0xffd700) },
                volume: { value: 0 }
            },
            vertexShader: `
                varying vec3 vNormal;
                void main() {
                    vNormal = normalize(normalMatrix * normal);
                    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                }
            `,
            fragmentShader: `
                uniform float time;
                uniform vec3 color;
                uniform float volume;
                varying vec3 vNormal;

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
        const geometry = new THREE.TorusGeometry(this.coreRadius * 1.3, 0.015, 16, 100);
        const material = new THREE.MeshBasicMaterial({
            color: 0xffd700,
            transparent: true,
            opacity: 0.25
        });
        this.outerRing = new THREE.Mesh(geometry, material);
        this.outerRing.rotation.x = Math.PI / 2;
        this.scene.add(this.outerRing);

        const geometry2 = new THREE.TorusGeometry(this.coreRadius * 1.5, 0.008, 16, 100);
        const material2 = new THREE.MeshBasicMaterial({
            color: 0xcc8800,
            transparent: true,
            opacity: 0.12
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
            const phi1 = Math.acos(2 * Math.random() - 1);
            const theta1 = Math.random() * Math.PI * 2;
            const phi2 = Math.acos(2 * Math.random() - 1);
            const theta2 = Math.random() * Math.PI * 2;
            const r = this.coreRadius;

            positions[i6]     = r * Math.sin(phi1) * Math.cos(theta1);
            positions[i6 + 1] = r * Math.sin(phi1) * Math.sin(theta1);
            positions[i6 + 2] = r * Math.cos(phi1);
            positions[i6 + 3] = r * Math.sin(phi2) * Math.cos(theta2);
            positions[i6 + 4] = r * Math.sin(phi2) * Math.sin(theta2);
            positions[i6 + 5] = r * Math.cos(phi2);

            const color = new THREE.Color(0xffd700);
            colors[i6]     = color.r; colors[i6 + 1] = color.g; colors[i6 + 2] = color.b;
            colors[i6 + 3] = color.r; colors[i6 + 4] = color.g; colors[i6 + 5] = color.b;
        }

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        const material = new THREE.LineBasicMaterial({
            vertexColors: true,
            transparent: true,
            opacity: 0.12,
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
            positions[i * 3]     = (Math.random() - 0.5) * 20;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 20;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 20;
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        const material = new THREE.PointsMaterial({
            color: 0xffd700,
            size: 0.02,
            transparent: true,
            opacity: 0.2,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });

        this.ambientParticles = new THREE.Points(geometry, material);
        this.scene.add(this.ambientParticles);
    }

    createEnergyStreams() {
        // Visible during 'planning' state - streams of energy flowing outward
        const streamCount = 8;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(streamCount * 6);
        const colors = new Float32Array(streamCount * 6);

        for (let i = 0; i < streamCount; i++) {
            const angle = (i / streamCount) * Math.PI * 2;
            const i6 = i * 6;

            // Inner point on sphere
            positions[i6]     = this.coreRadius * 0.5 * Math.cos(angle);
            positions[i6 + 1] = 0;
            positions[i6 + 2] = this.coreRadius * 0.5 * Math.sin(angle);

            // Outer point
            positions[i6 + 3] = this.coreRadius * 2.5 * Math.cos(angle);
            positions[i6 + 4] = (Math.random() - 0.5) * 1.0;
            positions[i6 + 5] = this.coreRadius * 2.5 * Math.sin(angle);

            const color = new THREE.Color(0xffd700);
            colors[i6]     = color.r; colors[i6 + 1] = color.g; colors[i6 + 2] = color.b;
            colors[i6 + 3] = color.r; colors[i6 + 4] = color.g; colors[i6 + 5] = color.b;
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        const material = new THREE.LineBasicMaterial({
            vertexColors: true,
            transparent: true,
            opacity: 0,
            blending: THREE.AdditiveBlending
        });

        this.energyStreams = new THREE.LineSegments(geometry, material);
        this.scene.add(this.energyStreams);
    }

    // ============================================
    // STATE MANAGEMENT
    // ============================================

    setState(newState) {
        if (this.state === newState) return;
        this.state = newState;

        // Reset colors to gold (unless error)
        this.resetColors();

        switch (newState) {
            case 'idle':
                this.targetRotationSpeed = 0.001;
                this.targetChaos = 0;
                this.targetBrightness = 0.6;
                this.targetBloom = 1.5;
                this.targetScale = 1.0;
                break;

            case 'listening':
                this.targetRotationSpeed = 0.002;
                this.targetChaos = 0.15;
                this.targetBrightness = 0.8;
                this.targetBloom = 1.8;
                this.targetScale = 0.95;  // particles contract inward
                break;

            case 'thinking':
                this.targetRotationSpeed = 0.006;
                this.targetChaos = 0.8;
                this.targetBrightness = 1.0;
                this.targetBloom = 2.2;
                this.targetScale = 1.05;
                break;

            case 'speaking':
                this.targetRotationSpeed = 0.003;
                this.targetChaos = 0.3;
                this.targetBrightness = 0.9;
                this.targetBloom = 2.0;
                this.targetScale = 1.0;
                break;

            case 'working':
                this.targetRotationSpeed = 0.005;
                this.targetChaos = 0.6;
                this.targetBrightness = 1.0;
                this.targetBloom = 2.5;
                this.targetScale = 1.02;
                break;

            case 'planning':
                this.targetRotationSpeed = 0.003;
                this.targetChaos = 0.4;
                this.targetBrightness = 0.85;
                this.targetBloom = 2.0;
                this.targetScale = 1.0;
                // Show energy streams
                if (this.energyStreams) this.energyStreams.material.opacity = 0.3;
                break;

            case 'mission_complete':
                this.targetRotationSpeed = 0.001;
                this.targetChaos = 0;
                this.targetBrightness = 1.0;
                this.targetBloom = 3.0;
                this.targetScale = 1.2;  // golden wave expansion
                // Brief flash then return to idle
                setTimeout(() => {
                    this.setState('idle');
                }, 2000);
                break;

            case 'error':
                this.targetRotationSpeed = 0.001;
                this.targetChaos = 0.2;
                this.targetBrightness = 0.7;
                this.targetBloom = 1.8;
                this.targetScale = 0.95;
                this.setErrorColors();
                // Return to idle after pulse
                setTimeout(() => {
                    this.setState('idle');
                }, 3000);
                break;
        }
    }

    resetColors() {
        const colors = this.particleGeometry.attributes.color.array;
        for (let i = 0; i < colors.length; i++) {
            colors[i] = this.originalColors[i];
        }
        this.particleGeometry.attributes.color.needsUpdate = true;

        // Reset energy streams
        if (this.energyStreams) this.energyStreams.material.opacity = 0;

        // Reset inner glow to gold
        if (this.innerGlow) this.innerGlow.material.uniforms.color.value.set(0xffd700);
    }

    setErrorColors() {
        const colors = this.particleGeometry.attributes.color.array;
        const errColor = new THREE.Color(0xff4466);
        for (let i = 0; i < this.particleCount; i++) {
            const i3 = i * 3;
            colors[i3]     = errColor.r;
            colors[i3 + 1] = errColor.g;
            colors[i3 + 2] = errColor.b;
        }
        this.particleGeometry.attributes.color.needsUpdate = true;

        if (this.innerGlow) this.innerGlow.material.uniforms.color.value.set(0xff4466);
    }

    // ============================================
    // MODES
    // ============================================

    setMode(newMode) {
        this.mode = newMode;
        if (newMode === 'voice') {
            this.camera.position.z = 3.5;
            this.targetScale = 1.1;
        } else {
            this.camera.position.z = 5;
            this.targetScale = 1.0;
        }
    }

    setAudio(volume, frequency, pitch) {
        this.audioVolume = volume;
        this.audioFrequency = frequency;
        this.audioPitch = pitch;
    }

    // ============================================
    // EVENTS
    // ============================================

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

    // ============================================
    // ANIMATION LOOP
    // ============================================

    animate() {
        requestAnimationFrame(() => this.animate());
        this.time += 0.016;

        // Smooth interpolation
        const lerp = (a, b, t) => a + (b - a) * t;
        this.currentRotationSpeed = lerp(this.currentRotationSpeed, this.targetRotationSpeed, 0.05);
        this.currentChaos = lerp(this.currentChaos, this.targetChaos, 0.05);
        this.currentBrightness = lerp(this.currentBrightness, this.targetBrightness, 0.05);
        this.currentScale = lerp(this.currentScale, this.targetScale, 0.08);
        this.currentBloom = lerp(this.currentBloom, this.targetBloom, 0.05);

        // Rotate particles
        this.particles.rotation.y += this.currentRotationSpeed;
        this.particles.rotation.x = this.mouse.y * 0.08;
        this.particles.rotation.z = this.mouse.x * 0.04;

        // Update particle positions
        const positions = this.particleGeometry.attributes.position.array;
        for (let i = 0; i < this.particleCount; i++) {
            const i3 = i * 3;
            const offset = this.particleOffsets[i];

            const angle = this.time * 0.5 + offset;
            const orbitalX = Math.sin(angle) * this.currentChaos * 0.1;
            const orbitalY = Math.cos(angle) * this.currentChaos * 0.1;
            const breathe = Math.sin(this.time * 1.5 + offset) * 0.05;

            positions[i3]     += (orbitalX + this.particleVelocities[i3] * this.currentChaos) * 0.1;
            positions[i3 + 1] += (orbitalY + this.particleVelocities[i3 + 1] * this.currentChaos) * 0.1;
            positions[i3 + 2] += breathe;

            // Keep on sphere
            const x = positions[i3], y = positions[i3 + 1], z = positions[i3 + 2];
            const dist = Math.sqrt(x * x + y * y + z * z);
            const targetDist = this.coreRadius * (0.8 + Math.sin(this.time + offset) * 0.1);
            if (dist > 0) {
                const scale = targetDist / dist;
                positions[i3]     *= scale;
                positions[i3 + 1] *= scale;
                positions[i3 + 2] *= scale;
            }
        }
        this.particleGeometry.attributes.position.needsUpdate = true;

        // Shader uniforms
        this.particles.material.uniforms.time.value = this.time;
        this.particles.material.uniforms.brightness.value = this.currentBrightness;
        this.particles.material.uniforms.volume.value = this.audioVolume;

        // Inner glow
        this.innerGlow.material.uniforms.time.value = this.time;
        this.innerGlow.material.uniforms.volume.value = this.audioVolume;
        this.innerGlow.scale.setScalar(this.currentScale * (1.0 + this.audioVolume * 0.3));

        // Outer rings
        this.outerRing.rotation.z += 0.002;
        this.outerRing2.rotation.z -= 0.001;
        this.outerRing.scale.setScalar(this.currentScale);
        this.outerRing2.scale.setScalar(this.currentScale * 0.9);

        // Neural connections
        this.neuralLines.material.opacity = 0.08 + this.currentChaos * 0.25;
        this.neuralLines.rotation.y += this.currentRotationSpeed * 0.5;

        // Energy streams rotation
        if (this.energyStreams) {
            this.energyStreams.rotation.y += 0.003;
        }

        // Ambient particles
        this.ambientParticles.rotation.y += 0.0002;
        this.ambientParticles.rotation.x += 0.0001;

        // Bloom
        this.bloomPass.strength = this.currentBloom;

        // Render
        this.composer.render();
    }
}

window.JarvisCore = JarvisCore;
