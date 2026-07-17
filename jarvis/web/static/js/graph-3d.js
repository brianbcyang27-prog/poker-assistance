/**
 * Interactive 3D Neural Sphere — Three.js / WebGL
 *
 * Golden particle network + constellation web + holographic rings.
 * Post-processing bloom, mouse parallax, neural pulse animation.
 */

class Graph3D {
    constructor(container) {
        this.container = container;
        this.W = window.innerWidth;
        this.H = window.innerHeight;
        this.time = 0;
        this.mouse = { x: 0, y: 0, tx: 0, ty: 0 };
        this.running = false;
        this._raf = null;
        this.state = 'idle';

        // Particle count
        this.NODE_COUNT = 800;
        this.SPACE_RADIUS = 12;
        this.CONNECT_DIST = 3.2;

        // State-driven targets
        this.targetBloom = 1.8;
        this.targetRotSpeed = 0.0006;
        this.currentRotSpeed = 0.0006;
        this.targetRingSpeedMult = 1.0;
        this.currentRingSpeedMult = 1.0;
        this.targetLineOpacity = 0.35;
        this.currentLineOpacity = 0.35;
        this.targetCorePulseSpeed = 1.5;
        this.targetMaxPulses = 1;
        this.currentMaxPulses = 1;
        this.targetPulseSpeedMult = 1.0;
        this.currentPulseSpeedMult = 1.0;

        // v3.2.0: Ambient and state-specific
        this._targetColorShift = 0; // 0=gold, 0.3=cyan-gold
        this._currentColorShift = 0;
        this._targetParticleDrift = 0.0002;
        this._currentParticleDrift = 0.0002;
        this._ambientPhase = 0;
        this._memoryFlashTimer = 0;
        this._delegationBurstTimer = 0;
        this._completionPulseTimer = 0;
        this._breathPhase = 0;

        // Golden palette
        this.GOLD = 0xffaa00;
        this.GOLD_BRIGHT = 0xfff0b3;
        this.GOLD_DIM = 0x996600;
    }

    /* ================================================================
       INIT
       ================================================================ */

    init() {
        this.container.innerHTML = '';

        // ---- Renderer ----
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
        this.renderer.setSize(this.W, this.H);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.setClearColor(0x000000, 1);
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.0;
        this.container.appendChild(this.renderer.domElement);

        // ---- Scene ----
        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.FogExp2(0x000000, 0.015);

        // ---- Camera ----
        this.camera = new THREE.PerspectiveCamera(50, this.W / this.H, 0.1, 200);
        this.camera.position.set(0, 0, 28);

        // ---- Orbit (custom damped) ----
        this.orbit = { theta: 0, phi: Math.PI / 2, radius: 28, target: new THREE.Vector3() };
        this.orbitDamping = { theta: 0, phi: 0 };

        // ---- Post-processing (Bloom) ----
        this._setupBloom();

        // ---- Build scene objects ----
        this._createParticleNetwork();
        this._createConstellationWeb();
        this._createHolographicRings();
        this._createCoreGlow();

        // ---- Events ----
        window.addEventListener('resize', () => this._onResize());
        window.addEventListener('mousemove', (e) => this._onMouseMove(e));
        this.container.addEventListener('wheel', (e) => this._onWheel(e), { passive: false });
        this.container.addEventListener('mousedown', () => this._dragging = true);
        window.addEventListener('mouseup', () => this._dragging = false);
        window.addEventListener('mousemove', (e) => {
            if (this._dragging) {
                this.orbitDamping.theta -= e.movementX * 0.004;
                this.orbitDamping.phi -= e.movementY * 0.004;
                this.orbitDamping.phi = Math.max(0.3, Math.min(Math.PI - 0.3, this.orbitDamping.phi));
            }
        });
    }

    _setupBloom() {
        this.renderPass = new THREE.RenderPass(this.scene, this.camera);

        this.bloomPass = new THREE.UnrealBloomPass(
            new THREE.Vector2(this.W, this.H),
            1.8,   // strength — intense glow
            0.6,   // radius — soft spread
            0.15   // threshold — let most gold through
        );

        this.composer = new THREE.EffectComposer(this.renderer);
        this.composer.addPass(this.renderPass);
        this.composer.addPass(this.bloomPass);
    }

    /* ================================================================
       PARTICLE NETWORK (Nodes)
       ================================================================ */

    _createParticleNetwork() {
        const count = this.NODE_COUNT;
        const positions = new Float32Array(count * 3);
        const colors = new Float32Array(count * 3);
        const sizes = new Float32Array(count);
        const phases = new Float32Array(count);

        for (let i = 0; i < count; i++) {
            // Spherical distribution
            const r = this.SPACE_RADIUS * Math.cbrt(Math.random());
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(2 * Math.random() - 1);

            positions[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
            positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
            positions[i * 3 + 2] = r * Math.cos(phi);

            // Golden color variation
            const t = Math.random();
            const color = new THREE.Color();
            if (t < 0.7) {
                color.setHex(this.GOLD);
            } else if (t < 0.92) {
                color.setHex(this.GOLD_BRIGHT);
            } else {
                color.setHex(this.GOLD_DIM);
            }
            color.multiplyScalar(0.6 + Math.random() * 0.4);

            colors[i * 3]     = color.r;
            colors[i * 3 + 1] = color.g;
            colors[i * 3 + 2] = color.b;

            sizes[i] = 1.5 + Math.random() * 2.5;
            phases[i] = Math.random() * Math.PI * 2;
        }

        this.nodePositions = positions;
        this.nodePhases = phases;
        this.nodeCount = count;

        // Create glow texture (soft circle)
        const texCanvas = document.createElement('canvas');
        texCanvas.width = 64;
        texCanvas.height = 64;
        const ctx = texCanvas.getContext('2d');
        const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
        gradient.addColorStop(0, 'rgba(255,255,255,1)');
        gradient.addColorStop(0.15, 'rgba(255,240,180,0.8)');
        gradient.addColorStop(0.4, 'rgba(255,170,0,0.3)');
        gradient.addColorStop(1, 'rgba(255,170,0,0)');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 64, 64);
        const glowTexture = new THREE.CanvasTexture(texCanvas);

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

        const material = new THREE.ShaderMaterial({
            uniforms: {
                uTime: { value: 0 },
                uTexture: { value: glowTexture },
            },
            vertexShader: `
                attribute float size;
                attribute vec3 color;
                varying vec3 vColor;
                varying float vSize;
                uniform float uTime;
                void main() {
                    vColor = color;
                    vSize = size;
                    vec4 mv = modelViewMatrix * vec4(position, 1.0);
                    gl_PointSize = size * (250.0 / -mv.z);
                    gl_Position = projectionMatrix * mv;
                }
            `,
            fragmentShader: `
                uniform sampler2D uTexture;
                varying vec3 vColor;
                varying float vSize;
                void main() {
                    vec4 tex = texture2D(uTexture, gl_PointCoord);
                    gl_FragColor = vec4(vColor * tex.rgb, tex.a * 0.85);
                }
            `,
            transparent: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        });

        this.particles = new THREE.Points(geometry, material);
        this.particlesGroup = new THREE.Group();
        this.particlesGroup.add(this.particles);
        this.scene.add(this.particlesGroup);
    }

    /* ================================================================
       CONSTELLATION WEB (Connections)
       ================================================================ */

    _createConstellationWeb() {
        const maxEdges = 3000;
        const linePositions = new Float32Array(maxEdges * 6);
        const lineColors = new Float32Array(maxEdges * 6);

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(lineColors, 3));

        const material = new THREE.LineBasicMaterial({
            vertexColors: true,
            transparent: true,
            opacity: 0.35,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        });

        this.lines = new THREE.LineSegments(geometry, material);
        this.lines.geometry.setDrawRange(0, 0);
        this.particlesGroup.add(this.lines);

        this.linePositions = linePositions;
        this.lineColors = lineColors;
        this.maxEdges = maxEdges;
    }

    _updateConstellationWeb() {
        const pos = this.nodePositions;
        const count = this.nodeCount;
        const maxDist = this.CONNECT_DIST;
        const lp = this.linePositions;
        const lc = this.lineColors;
        let edgeIdx = 0;

        // Only sample a subset each frame for perf
        const step = Math.max(1, Math.floor(count / 200));

        for (let i = 0; i < count && edgeIdx < this.maxEdges; i += step) {
            const ax = pos[i * 3], ay = pos[i * 3 + 1], az = pos[i * 3 + 2];
            for (let j = i + 1; j < count && edgeIdx < this.maxEdges; j += 1) {
                const dx = pos[j * 3] - ax;
                const dy = pos[j * 3 + 1] - ay;
                const dz = pos[j * 3 + 2] - az;
                const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
                if (dist < maxDist) {
                    const idx = edgeIdx * 6;
                    const alpha = 1.0 - dist / maxDist;
                    const brightness = 0.15 + alpha * 0.6;

                    lp[idx]     = pos[i * 3];
                    lp[idx + 1] = pos[i * 3 + 1];
                    lp[idx + 2] = pos[i * 3 + 2];
                    lp[idx + 3] = pos[j * 3];
                    lp[idx + 4] = pos[j * 3 + 1];
                    lp[idx + 5] = pos[j * 3 + 2];

                    // Golden line color
                    lc[idx]     = 1.0 * brightness;
                    lc[idx + 1] = 0.67 * brightness;
                    lc[idx + 2] = 0.0;
                    lc[idx + 3] = 1.0 * brightness;
                    lc[idx + 4] = 0.67 * brightness;
                    lc[idx + 5] = 0.0;

                    edgeIdx++;
                }
            }
        }

        this.lines.geometry.attributes.position.needsUpdate = true;
        this.lines.geometry.attributes.color.needsUpdate = true;
        this.lines.geometry.setDrawRange(0, edgeIdx * 2);
        this.edgeCount = edgeIdx;
    }

    /* ================================================================
       NEURAL PULSE (Data packet animation on lines)
       ================================================================ */

    _createPulse() {
        // Pool of pulse meshes — multiple dots traveling simultaneously
        this.pulsePool = [];
        this.pulsePoolSize = 12;
        const geo = new THREE.SphereGeometry(0.12, 8, 8);
        for (let i = 0; i < this.pulsePoolSize; i++) {
            const mat = new THREE.MeshBasicMaterial({
                color: this.GOLD_BRIGHT,
                transparent: true,
                opacity: 0,
            });
            const mesh = new THREE.Mesh(geo, mat);
            mesh.visible = false;
            this.particlesGroup.add(mesh);
            this.pulsePool.push({
                mesh,
                active: false,
                t: 0,
                speed: 0,
                src: new THREE.Vector3(),
                dst: new THREE.Vector3(),
            });
        }
        this.activePulseCount = 0;
    }

    _spawnPulse() {
        if (this.edgeCount === 0) return;
        // Find an inactive slot
        for (const p of this.pulsePool) {
            if (p.active) continue;
            const idx = Math.floor(Math.random() * this.edgeCount) * 6;
            const lp = this.linePositions;
            p.src.set(lp[idx], lp[idx + 1], lp[idx + 2]);
            p.dst.set(lp[idx + 3], lp[idx + 4], lp[idx + 5]);
            p.t = 0;
            p.speed = (1.5 + Math.random() * 2.0) * this.currentPulseSpeedMult;
            p.active = true;
            p.mesh.visible = true;
            this.activePulseCount++;
            return;
        }
    }

    _updatePulse(dt) {
        // Spawn new pulses to match target count
        while (this.activePulseCount < this.targetMaxPulses) {
            this._spawnPulse();
        }

        // Update all active pulses
        for (const p of this.pulsePool) {
            if (!p.active) continue;
            p.t += dt * p.speed;
            if (p.t >= 1) {
                p.active = false;
                p.mesh.visible = false;
                p.mesh.material.opacity = 0;
                this.activePulseCount--;
            } else {
                p.mesh.position.lerpVectors(p.src, p.dst, p.t);
                const alpha = p.t < 0.3 ? p.t / 0.3 : (1 - p.t) / 0.7;
                p.mesh.material.opacity = alpha * 0.9;
                p.mesh.scale.setScalar(0.7 + alpha * 0.6);
            }
        }
    }

    /* ================================================================
       HOLOGRAPHIC RINGS (Concentric shells)
       ================================================================ */

    _createHolographicRings() {
        this.ringGroup = new THREE.Group();

        const ringDefs = [
            { radius: 14, tube: 0.03, segments: 120, dash: 3, gap: 4, speed: 0.08, axis: 'y' },
            { radius: 17, tube: 0.02, segments: 160, dash: 5, gap: 6, speed: -0.05, axis: 'x' },
            { radius: 20, tube: 0.015, segments: 200, dash: 2, gap: 8, speed: 0.03, axis: 'y' },
        ];

        this.rings = [];

        for (const def of ringDefs) {
            const points = [];
            for (let i = 0; i <= def.segments; i++) {
                const angle = (i / def.segments) * Math.PI * 2;
                points.push(new THREE.Vector3(
                    Math.cos(angle) * def.radius,
                    0,
                    Math.sin(angle) * def.radius
                ));
            }

            const geo = new THREE.BufferGeometry().setFromPoints(points);
            const mat = new THREE.LineDashedMaterial({
                color: this.GOLD,
                dashSize: def.dash,
                gapSize: def.gap,
                transparent: true,
                opacity: 0.3,
                blending: THREE.AdditiveBlending,
                depthWrite: false,
            });

            const ring = new THREE.Line(geo, mat);
            ring.computeLineDistances();
            ring.userData = { speed: def.speed, axis: def.axis, baseOpacity: 0.3 };
            this.ringGroup.add(ring);
            this.rings.push(ring);

            // Add tick marks at intervals
            const tickCount = Math.floor(def.segments / 8);
            const tickGroup = new THREE.Group();
            for (let i = 0; i < tickCount; i++) {
                const angle = (i / tickCount) * Math.PI * 2;
                const isMajor = i % 4 === 0;
                const len = isMajor ? 0.8 : 0.3;
                const inner = def.radius - len;
                const outer = def.radius;

                const tickGeo = new THREE.BufferGeometry().setFromPoints([
                    new THREE.Vector3(Math.cos(angle) * inner, 0, Math.sin(angle) * inner),
                    new THREE.Vector3(Math.cos(angle) * outer, 0, Math.sin(angle) * outer),
                ]);
                const tickMat = new THREE.LineBasicMaterial({
                    color: isMajor ? this.GOLD_BRIGHT : this.GOLD,
                    transparent: true,
                    opacity: isMajor ? 0.6 : 0.2,
                    blending: THREE.AdditiveBlending,
                });
                tickGroup.add(new THREE.Line(tickGeo, tickMat));
            }
            ring.add(tickGroup);
        }

        // Offset focal aperture ring (the "gaze")
        const apertureGeo = new THREE.RingGeometry(2.5, 3.5, 64);
        const apertureMat = new THREE.MeshBasicMaterial({
            color: this.GOLD,
            transparent: true,
            opacity: 0.08,
            side: THREE.DoubleSide,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        });
        this.aperture = new THREE.Mesh(apertureGeo, apertureMat);
        this.aperture.position.z = 0.5;
        this.ringGroup.add(this.aperture);

        // Aperture crosshair
        const chMat = new THREE.LineBasicMaterial({
            color: this.GOLD_BRIGHT, transparent: true, opacity: 0.15,
            blending: THREE.AdditiveBlending,
        });
        const ch1 = new THREE.Line(new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(-4, 0, 0.5), new THREE.Vector3(4, 0, 0.5)
        ]), chMat);
        const ch2 = new THREE.Line(new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(0, -4, 0.5), new THREE.Vector3(0, 4, 0.5)
        ]), chMat);
        this.ringGroup.add(ch1, ch2);

        this.scene.add(this.ringGroup);
    }

    /* ================================================================
       CORE GLOW
       ================================================================ */

    _createCoreGlow() {
        const geo = new THREE.SphereGeometry(1.5, 32, 32);
        const mat = new THREE.ShaderMaterial({
            uniforms: {
                uTime: { value: 0 },
                uColor: { value: new THREE.Color(this.GOLD) },
            },
            vertexShader: `
                varying vec3 vNormal;
                void main() {
                    vNormal = normalize(normalMatrix * normal);
                    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                }
            `,
            fragmentShader: `
                uniform float uTime;
                uniform vec3 uColor;
                varying vec3 vNormal;
                void main() {
                    float intensity = pow(0.55 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.5);
                    float pulse = 1.0 + sin(uTime * 1.5) * 0.15;
                    vec3 glow = uColor * intensity * pulse * 1.2;
                    gl_FragColor = vec4(glow, intensity * 0.5);
                }
            `,
            transparent: true,
            blending: THREE.AdditiveBlending,
            side: THREE.BackSide,
            depthWrite: false,
        });

        this.coreGlow = new THREE.Mesh(geo, mat);
        this.scene.add(this.coreGlow);
    }

    /* ================================================================
       DATA LOADING
       ================================================================ */

    async loadData() {
        try {
            const res = await fetch('/api/memory/graph?limit=300');
            const data = await res.json();
            if (data.nodes && data.nodes.length > 10) {
                this._mapGraphToNodes(data.nodes, data.edges || []);
            }
        } catch (e) {
            console.warn('Graph3D: load failed, using generated sphere');
        }
        this._updateConstellationWeb();
        this._createPulse();
    }

    _mapGraphToNodes(graphNodes, graphEdges) {
        const count = Math.min(graphNodes.length, this.NODE_COUNT);
        const pos = this.nodePositions;

        for (let i = 0; i < count; i++) {
            // Place graph nodes on sphere surface, preserving relative structure
            const phi = Math.acos(2 * (i / count) - 1);
            const theta = (i / count) * Math.PI * 2 * (1 + (graphNodes[i]?.type === 'note' ? 0.3 : 0));
            const r = this.SPACE_RADIUS * (0.5 + Math.random() * 0.5);

            pos[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
            pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
            pos[i * 3 + 2] = r * Math.cos(phi);
        }

        this.particles.geometry.attributes.position.needsUpdate = true;
    }

    /* ================================================================
       STATE — Brain activity visualization
       ================================================================ */

    setState(newState) {
        if (this.state === newState) return;
        const oldState = this.state;
        this.state = newState;

        switch (newState) {
            case 'idle':
                this.targetBloom = 1.8;
                this.targetRotSpeed = 0.0006;
                this.targetRingSpeedMult = 1.0;
                this.targetLineOpacity = 0.35;
                this.targetCorePulseSpeed = 1.5;
                this.targetMaxPulses = 1;
                this.targetPulseSpeedMult = 1.0;
                this._targetColorShift = 0; // gold
                this._targetParticleDrift = 0.0002;
                break;
            case 'thinking':
                this.targetBloom = 3.0;
                this.targetRotSpeed = 0.003;
                this.targetRingSpeedMult = 3.0;
                this.targetLineOpacity = 0.7;
                this.targetCorePulseSpeed = 4.0;
                this.targetMaxPulses = 8;
                this.targetPulseSpeedMult = 3.5;
                this._targetColorShift = 0; // bright gold
                this._targetParticleDrift = 0.001;
                break;
            case 'listening':
                this.targetBloom = 2.2;
                this.targetRotSpeed = 0.0015;
                this.targetRingSpeedMult = 1.8;
                this.targetLineOpacity = 0.5;
                this.targetCorePulseSpeed = 2.5;
                this.targetMaxPulses = 3;
                this.targetPulseSpeedMult = 1.8;
                this._targetColorShift = 0;
                this._targetParticleDrift = 0.0005;
                break;
            case 'speaking':
                this.targetBloom = 2.5;
                this.targetRotSpeed = 0.002;
                this.targetRingSpeedMult = 2.0;
                this.targetLineOpacity = 0.55;
                this.targetCorePulseSpeed = 3.0;
                this.targetMaxPulses = 4;
                this.targetPulseSpeedMult = 2.2;
                this._targetColorShift = 0;
                this._targetParticleDrift = 0.0006;
                break;
            case 'working':
                this.targetBloom = 2.8;
                this.targetRotSpeed = 0.0025;
                this.targetRingSpeedMult = 2.5;
                this.targetLineOpacity = 0.6;
                this.targetCorePulseSpeed = 3.5;
                this.targetMaxPulses = 6;
                this.targetPulseSpeedMult = 2.8;
                this._targetColorShift = 0;
                this._targetParticleDrift = 0.0008;
                break;
            // ---- v3.2.0: New AI states ----
            case 'retrieving':
                // Particles flow inward — memory convergence
                this.targetBloom = 2.6;
                this.targetRotSpeed = 0.001;
                this.targetRingSpeedMult = 1.5;
                this.targetLineOpacity = 0.65;
                this.targetCorePulseSpeed = 2.0;
                this.targetMaxPulses = 5;
                this.targetPulseSpeedMult = 2.0;
                this._targetColorShift = 0.3; // cyan-gold blend
                this._targetParticleDrift = -0.001; // inward drift
                this._triggerMemoryFlash = true;
                break;
            case 'planning':
                // Network expands — new branches appear
                this.targetBloom = 2.4;
                this.targetRotSpeed = 0.002;
                this.targetRingSpeedMult = 2.2;
                this.targetLineOpacity = 0.55;
                this.targetCorePulseSpeed = 3.0;
                this.targetMaxPulses = 4;
                this.targetPulseSpeedMult = 2.5;
                this._targetColorShift = 0.15; // slight warm shift
                this._targetParticleDrift = 0.0005;
                this._expandNetwork = true;
                break;
            case 'delegating':
                // Energy pulses travel outward — delegation burst
                this.targetBloom = 3.2;
                this.targetRotSpeed = 0.0035;
                this.targetRingSpeedMult = 3.5;
                this.targetLineOpacity = 0.75;
                this.targetCorePulseSpeed = 4.5;
                this.targetMaxPulses = 12;
                this.targetPulseSpeedMult = 4.0;
                this._targetColorShift = 0.1;
                this._targetParticleDrift = 0.0015;
                this._delegationBurst = true;
                break;
            case 'reviewing':
                // Golden energy returns — calm assessment
                this.targetBloom = 2.0;
                this.targetRotSpeed = 0.0008;
                this.targetRingSpeedMult = 1.2;
                this.targetLineOpacity = 0.45;
                this.targetCorePulseSpeed = 2.0;
                this.targetMaxPulses = 3;
                this.targetPulseSpeedMult = 1.5;
                this._targetColorShift = 0.05;
                this._targetParticleDrift = 0.0003;
                break;
            case 'complete':
                // Entire network settles — calm completion pulse
                this.targetBloom = 2.2;
                this.targetRotSpeed = 0.0004;
                this.targetRingSpeedMult = 0.8;
                this.targetLineOpacity = 0.4;
                this.targetCorePulseSpeed = 1.2;
                this.targetMaxPulses = 2;
                this.targetPulseSpeedMult = 1.0;
                this._targetColorShift = 0;
                this._targetParticleDrift = 0.0001;
                this._completionPulse = true;
                break;
        }

        // Emit state change event for other systems
        window.dispatchEvent(new CustomEvent('jarvis-state-change', {
            detail: { from: oldState, to: newState }
        }));
    }

    /* ================================================================
       RENDER LOOP
       ================================================================ */

    start() {
        if (this.running) return;
        this.running = true;
        this._lastTime = performance.now();
        this._animate();
    }

    stop() {
        this.running = false;
        if (this._raf) cancelAnimationFrame(this._raf);
    }

    _animate() {
        if (!this.running) return;
        this._raf = requestAnimationFrame(() => this._animate());

        const now = performance.now();
        const dt = Math.min((now - this._lastTime) / 1000, 0.05);
        this._lastTime = now;
        this.time += dt;

        // ---- Smooth interpolation toward targets ----
        const lerp = 0.04;
        this.currentRotSpeed += (this.targetRotSpeed - this.currentRotSpeed) * lerp;
        this.currentRingSpeedMult += (this.targetRingSpeedMult - this.currentRingSpeedMult) * lerp;
        this.currentLineOpacity += (this.targetLineOpacity - this.currentLineOpacity) * lerp;
        this.currentMaxPulses += (this.targetMaxPulses - this.currentMaxPulses) * lerp;
        this.currentPulseSpeedMult += (this.targetPulseSpeedMult - this.currentPulseSpeedMult) * lerp;
        this._currentColorShift += ((this._targetColorShift || 0) - this._currentColorShift) * lerp;
        this._currentParticleDrift += ((this._targetParticleDrift || 0) - this._currentParticleDrift) * lerp;

        // ---- Ambient breathing (always active, subtle) ----
        this._breathPhase += dt * 0.8;
        this._ambientPhase += dt;
        const breathScale = 1.0 + Math.sin(this._breathPhase) * 0.008; // very subtle
        this.particlesGroup.scale.setScalar(breathScale);

        // ---- Mouse parallax ----
        this.mouse.x += (this.mouse.tx - this.mouse.x) * 0.04;
        this.mouse.y += (this.mouse.ty - this.mouse.y) * 0.04;

        // ---- Orbit camera ----
        this.orbit.theta += (this.orbitDamping.theta - this.orbit.theta) * 0.06;
        this.orbit.phi += (this.orbitDamping.phi - this.orbit.phi) * 0.06;

        // Auto-rotate (faster when thinking)
        this.orbitDamping.theta += this.currentRotSpeed;

        const r = this.orbit.radius;
        this.camera.position.x = r * Math.sin(this.orbit.phi) * Math.sin(this.orbit.theta) + this.mouse.x * 2;
        this.camera.position.y = r * Math.cos(this.orbit.phi) + this.mouse.y * 1.5;
        this.camera.position.z = r * Math.sin(this.orbit.phi) * Math.cos(this.orbit.theta);
        this.camera.lookAt(this.orbit.target);

        // ---- Rotate particle group ----
        this.particlesGroup.rotation.y += this.currentRotSpeed * 0.8;

        // ---- Rotate rings ----
        for (const ring of this.rings) {
            const s = ring.userData.speed * this.currentRingSpeedMult;
            if (ring.userData.axis === 'y') {
                ring.rotation.y += s * dt;
            } else {
                ring.rotation.x += s * dt;
                ring.rotation.z += s * dt * 0.3;
            }
            ring.material.opacity = (ring.userData.baseOpacity + Math.sin(this.time * 0.8 + ring.rotation.y) * 0.05) * this.currentLineOpacity / 0.35;
        }

        // Aperture float
        this.aperture.position.x = Math.sin(this.time * 0.3) * 0.3;
        this.aperture.position.y = Math.cos(this.time * 0.4) * 0.2;
        this.aperture.rotation.z = this.time * 0.05 * this.currentRingSpeedMult;
        this.aperture.material.opacity = 0.06;

        // ---- Core glow pulse — beats faster when thinking ----
        this.coreGlow.material.uniforms.uTime.value = this.time;
        this.coreGlow.material.uniforms.uColor.value.setHex(
            this.state === 'thinking' ? this.GOLD_BRIGHT : this.GOLD
        );
        const corePulse = 1.0 + Math.sin(this.time * this.targetCorePulseSpeed) * 0.12;
        this.coreGlow.scale.setScalar(corePulse);

        // ---- v3.2.0: State-specific visual effects ----

        // Memory retrieval flash — particles converge toward center
        if (this._triggerMemoryFlash) {
            this._memoryFlashTimer = 2.0; // 2 second effect
            this._triggerMemoryFlash = false;
        }
        if (this._memoryFlashTimer > 0) {
            this._memoryFlashTimer -= dt;
            const flashIntensity = this._memoryFlashTimer / 2.0;
            // Pulse the core brighter during retrieval
            this.coreGlow.scale.setScalar(corePulse * (1.0 + flashIntensity * 0.3));
        }

        // Delegation burst — energy radiates outward
        if (this._delegationBurst) {
            this._delegationBurstTimer = 1.5;
            this._delegationBurst = false;
        }
        if (this._delegationBurstTimer > 0) {
            this._delegationBurstTimer -= dt;
            const burstT = 1.0 - (this._delegationBurstTimer / 1.5);
            // Expand rings temporarily
            for (const ring of this.rings) {
                const expand = 1.0 + burstT * 0.15;
                ring.scale.setScalar(expand);
            }
        } else {
            for (const ring of this.rings) {
                ring.scale.setScalar(1.0);
            }
        }

        // Completion pulse — calm settling wave
        if (this._completionPulse) {
            this._completionPulseTimer = 3.0;
            this._completionPulse = false;
        }
        if (this._completionPulseTimer > 0) {
            this._completionPulseTimer -= dt;
            const settleT = this._completionPulseTimer / 3.0;
            // Gentle bloom pulse
            this.bloomPass.strength += settleT * 0.3;
        }

        // Ambient idle behavior — random micro-pulses when idle
        if (this.state === 'idle') {
            // Occasional tiny communication pulse
            if (Math.random() < 0.002) { // ~once every 8 seconds at 60fps
                this._spawnPulse();
            }
        }

        // ---- Particle shader time ----
        this.particles.material.uniforms.uTime.value = this.time;

        // ---- v3.2.0: Particle drift (inward for retrieve, outward for delegate) ----
        if (Math.abs(this._currentParticleDrift) > 0.0001) {
            const pos = this.nodePositions;
            const count = this.nodeCount;
            for (let i = 0; i < count; i++) {
                const x = pos[i * 3], y = pos[i * 3 + 1], z = pos[i * 3 + 2];
                const dist = Math.sqrt(x * x + y * y + z * z);
                if (dist > 0.1) {
                    // Normalize direction, apply drift
                    const nx = x / dist, ny = y / dist, nz = z / dist;
                    const drift = this._currentParticleDrift * (0.5 + Math.sin(i * 0.1 + this.time) * 0.5);
                    pos[i * 3]     += nx * drift;
                    pos[i * 3 + 1] += ny * drift;
                    pos[i * 3 + 2] += nz * drift;
                    // Keep within bounds
                    const newDist = Math.sqrt(pos[i*3]**2 + pos[i*3+1]**2 + pos[i*3+2]**2);
                    if (newDist > this.SPACE_RADIUS * 1.2) {
                        pos[i * 3]     *= this.SPACE_RADIUS * 1.1 / newDist;
                        pos[i * 3 + 1] *= this.SPACE_RADIUS * 1.1 / newDist;
                        pos[i * 3 + 2] *= this.SPACE_RADIUS * 1.1 / newDist;
                    }
                    if (newDist < 1.0) {
                        pos[i * 3]     *= 1.5 / newDist;
                        pos[i * 3 + 1] *= 1.5 / newDist;
                        pos[i * 3 + 2] *= 1.5 / newDist;
                    }
                }
            }
            this.particles.geometry.attributes.position.needsUpdate = true;
        }

        // ---- Constellation web opacity ----
        this.lines.material.opacity = this.currentLineOpacity;

        // ---- Neural pulse (more frequent when thinking) ----
        this._updatePulse(dt);

        // ---- Bloom intensity (lerp toward target) ----
        this.bloomPass.strength += (this.targetBloom - this.bloomPass.strength) * 0.03;

        // ---- Render with bloom ----
        this.composer.render();
    }

    /* ================================================================
       EVENTS
       ================================================================ */

    _onResize() {
        this.W = window.innerWidth;
        this.H = window.innerHeight;
        this.camera.aspect = this.W / this.H;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(this.W, this.H);
        this.composer.setSize(this.W, this.H);
    }

    _onMouseMove(e) {
        this.mouse.tx = (e.clientX / this.W - 0.5) * 2;
        this.mouse.ty = -(e.clientY / this.H - 0.5) * 2;
    }

    _onWheel(e) {
        e.preventDefault();
        this.orbit.radius = Math.max(14, Math.min(50, this.orbit.radius + e.deltaY * 0.02));
    }

    destroy() {
        this.stop();
        if (this.renderer) {
            this.renderer.dispose();
            if (this.renderer.domElement && this.renderer.domElement.parentNode) {
                this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
            }
        }
    }
}

window.Graph3D = Graph3D;
