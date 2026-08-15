/**
 * JARVIS 3D Neural Core — Movie-Accurate Golden Neural Core
 * 
 * Visual Reference: Iron Man JARVIS interface
 * - Central golden core with intense glow/bloom
 * - Neural particle network with data pulses
 * - Holographic rotating rings with tick marks
 * - Constellation web of golden connections
 * - Breathing, pulsing core with state-driven animations
 * - Additive blending for true golden glow
 * - Post-processing bloom for cinematic quality
 */

class Graph3D {
    constructor(container, options = {}) {
        this.container = container;
        this.interactive = options.interactive !== false;
        this.W = window.innerWidth;
        this.H = window.innerHeight;
        this.time = 0;
        this.dt = 0;
        this.mouse = { x: 0, y: 0, tx: 0, ty: 0 };
        this.running = false;
        this._raf = null;
        this.state = 'idle';
        this._dragging = false;
        this._frameCount = 0;
        
        // --- Core Configuration ---
        this.NODE_COUNT = 500;              // More particles for density
        this.SPACE_RADIUS = 15;             // Larger field
        this.CONNECT_DIST = 4.5;            // Longer connections
        
        // --- State Targets (lerp'd) ---
        this.targetBloom = 2.5;
        this.targetRotSpeed = 0.0008;
        this.targetRingSpeedMult = 1.2;
        this.targetLineOpacity = 0.4;
        this.targetCorePulseSpeed = 2.0;
        this.targetMaxPulses = 2;
        this.targetPulseSpeedMult = 1.5;
        
        // Current (lerp'd) values
        this.currentRotSpeed = 0.0008;
        this.currentRingSpeedMult = 1.2;
        this.currentLineOpacity = 0.4;
        this.currentMaxPulses = 2;
        this.currentPulseSpeedMult = 1.5;
        
        // Color shift: 0 = pure gold, 0.3 = cyan-gold blend, 1 = full cyan
        this._targetColorShift = 0;
        this._currentColorShift = 0;
        
        // Particle drift
        this._targetParticleDrift = 0.0003;
        this._currentParticleDrift = 0.0003;
        
        // Ambient phases
        this._ambientPhase = 0;
        this._breathPhase = 0;
        this._memoryFlashTimer = 0;
        this._delegationBurstTimer = 0;
        this._completionPulseTimer = 0;
        
        // Event triggers
        this._expandNetwork = false;
        this._delegationBurst = false;
        this._memoryFlash = false;
        this._completionPulse = false;
        
        // Golden palette - TRUE GOLD
        this.GOLD = 0xffb800;        // True gold
        this.GOLD_BRIGHT = 0xffdd44;  // Bright gold
        this.GOLD_WARM = 0xff9900;    // Warm gold
        this.GOLD_DIM = 0xcc7700;     // Dim gold
        this.CYAN = 0x00ffff;         // Cyan for state shifts
        
        // Three.js objects
        this.renderer = null;
        this.scene = null;
        this.camera = null;
        this.composer = null;
        this.bloomPass = null;
        this.particles = null;
        this.particlesGroup = null;
        this.lines = null;
        this.ringGroup = null;
        this.rings = [];
        this.coreGlow = null;
        this.corePulseMesh = null;
        this.aperture = null;
        
        // Particle data
        this.NODE_COUNT = 500;
        this.nodePositions = null;
        this.nodePhases = null;
        this.nodeCount = 0;
        this.edgeCount = 0;
        this.linePositions = null;
        this.lineColors = null;
        this.maxEdges = 4000;
        
        // Pulse system
        this.pulsePool = [];
        this.pulsePoolSize = 20;
        this.activePulseCount = 0;
        
        // Ring data
        this.rings = [];
        
        // Orbit camera
        this.orbit = { theta: 0, phi: Math.PI / 2, radius: 30, target: new THREE.Vector3() };
        this.orbitDamping = { theta: 0, phi: 0 };
        
        // Interaction
        this._boundResize = () => this._onResize();
        this._boundMouseMove = (e) => this._onMouseMove(e);
        this._boundWheel = (e) => this._onWheel(e);
        this._boundMouseDown = () => { this._dragging = true; };
        this._boundMouseUp = () => { this._dragging = false; };
        this._boundDrag = (e) => {
            if (this._dragging) {
                this.orbitDamping.theta -= e.movementX * 0.005;
                this.orbitDamping.phi -= e.movementY * 0.005;
                this.orbitDamping.phi = Math.max(0.2, Math.min(Math.PI - 0.2, this.orbitDamping.phi));
            }
        };
    }

    // ================================================================
    // INIT
    // ================================================================
    init() {
        if (!this.container) {
            console.warn('Graph3D: container not found');
            return;
        }
        this.container.innerHTML = '';
        
        // ---- Renderer ----
        this.renderer = new THREE.WebGLRenderer({ 
            antialias: true, 
            alpha: false,
            powerPreference: "high-performance"
        });
        this.renderer.setSize(this.W, this.H);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.setClearColor(0x030508, 1);  // Deep space black
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.6;
        this.renderer.useLegacyLights = false;
        this.container.appendChild(this.renderer.domElement);
        
        // ---- Scene ----
        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.FogExp2(0x020306, 0.008);
        
        // ---- Camera ----
        this.camera = new THREE.PerspectiveCamera(55, this.W / this.H, 0.1, 300);
        this.camera.position.set(0, 0, 35);
        
        // ---- Post-processing (Bloom) ----
        this._setupBloom();
        
        // ---- Build Scene Objects ----
        this._createParticleNetwork();
        this._createConstellationWeb();
        this._createHolographicRings();
        this._createCoreGlow();
        this._createCorePulse();
        
        // ---- Events ----
        window.addEventListener('resize', this._boundResize);
        this._attachInteractionListeners();
        
    }

    _setupBloom() {
        // Full cinematic bloom pipeline
        const renderScene = new THREE.RenderPass(this.scene, this.camera);
        
        this.bloomPass = new THREE.UnrealBloomPass(
            new THREE.Vector2(this.W, this.H),
            2.5,    // strength - STRONG bloom
            0.15,   // radius - tighter
            0.02    // threshold - only brightest
        );
        
        this.composer = new THREE.EffectComposer(this.renderer);
        this.composer.addPass(renderScene);
        this.composer.addPass(this.bloomPass);
        
        // Bloom strength controlled by state
        this._bloomStrength = 2.5;
    }

    // ================================================================
    // PARTICLE NETWORK (Neural Nodes)
    // ================================================================
    _createParticleNetwork() {
        const count = this.NODE_COUNT;
        const positions = new Float32Array(count * 3);
        const colors = new Float32Array(count * 3);
        const sizes = new Float32Array(count);
        const phases = new Float32Array(count);
        const velocities = new Float32Array(count * 3);  // For drift animation
        const baseSizes = new Float32Array(count);

        for (let i = 0; i < count; i++) {
            // Fibonacci sphere distribution for even coverage
            const phi = Math.acos(2 * (i + 0.5) / count - 1);
            const theta = Math.PI * (1 + Math.sqrt(5)) * i;  // Golden angle
            
            const r = this.SPACE_RADIUS * (0.35 + Math.pow(Math.random(), 0.7) * 0.65);
            
            positions[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
            positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
            positions[i * 3 + 2] = r * Math.cos(phi);
            
            // Store base position for drift
            velocities[i * 3]     = positions[i * 3];
            velocities[i * 3 + 1] = positions[i * 3 + 1];
            velocities[i * 3 + 2] = positions[i * 3 + 2];
            
            // Golden color variation - more variation
            const t = Math.random();
            const color = new THREE.Color();
            if (t < 0.55) {
                color.setHex(this.GOLD);
            } else if (t < 0.85) {
                color.setHex(this.GOLD_BRIGHT);
            } else if (t < 0.95) {
                color.setHex(this.GOLD_WARM);
            } else {
                color.setHex(this.GOLD_DIM);
            }
            // Slight random brightness
            color.multiplyScalar(0.8 + Math.random() * 0.3);
            
            colors[i * 3]     = color.r;
            colors[i * 3 + 1] = color.g;
            colors[i * 3 + 2] = color.b;
            
            const baseSize = 1.8 + Math.random() * 3.5;
            sizes[i] = baseSize;
            baseSizes[i] = baseSize;
            
            phases[i] = Math.random() * Math.PI * 2;
        }

        this.nodePositions = positions;
        this.nodePhases = phases;
        this.nodeVelocities = velocities;
        this.nodeBaseSizes = baseSizes;
        this.nodeCount = count;

        // Glow texture - larger, softer
        const texCanvas = document.createElement('canvas');
        texCanvas.width = 128;
        texCanvas.height = 128;
        const ctx = texCanvas.getContext('2d');
        const gradient = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
        gradient.addColorStop(0, 'rgba(255,255,255,1)');
        gradient.addColorStop(0.1, 'rgba(255,255,220,0.95)');
        gradient.addColorStop(0.25, 'rgba(255,230,100,0.7)');
        gradient.addColorStop(0.5, 'rgba(255,180,0,0.3)');
        gradient.addColorStop(0.8, 'rgba(255,120,0,0.05)');
        gradient.addColorStop(1, 'rgba(255,100,0,0)');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 128, 128);
        const glowTexture = new THREE.CanvasTexture(texCanvas);
        glowTexture.wrapS = THREE.ClampToEdgeWrapping;
        glowTexture.wrapT = THREE.ClampToEdgeWrapping;

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
        geometry.setAttribute('baseSize', new THREE.BufferAttribute(baseSizes, 1));
        geometry.setAttribute('phase', new THREE.BufferAttribute(phases, 1));

        const material = new THREE.ShaderMaterial({
            uniforms: {
                uTime: { value: 0 },
                uTexture: { value: glowTexture },
                uColorShift: { value: 0 },
                uCorePulse: { value: 1.0 },
            },
            vertexShader: `
                attribute float size;
                attribute float baseSize;
                attribute vec3 color;
                attribute float phase;
                varying vec3 vColor;
                varying float vSize;
                varying float vPhase;
                uniform float uTime;
                uniform float uCorePulse;
                uniform float uColorShift;
                
                // 3D noise for organic movement
                float hash(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
                float noise(vec3 p) {
                    vec3 i = floor(p);
                    vec3 f = fract(p);
                    f = f * f * (3.0 - 2.0 * f);
                    return mix(mix(mix(hash(i + vec3(0,0,0)), hash(i + vec3(1,0,0)), f.x),
                                   mix(hash(i + vec3(0,1,0)), hash(i + vec3(1,1,0)), f.x), f.y),
                               mix(mix(hash(i + vec3(0,0,1)), hash(i + vec3(1,0,1)), f.x),
                                   mix(hash(i + vec3(0,1,1)), hash(i + vec3(1,1,1)), f.x), f.y), f.z);
                }
                
                void main() {
                    vColor = color;
                    vPhase = phase;
                    
                    // Ambient drift
                    float drift = noise(position * 0.5 + uTime * 0.02) * 0.3;
                    vec3 pos = position + normalize(position) * drift;
                    
                    // Core pulse affects nearby particles
                    float distToCore = length(pos);
                    float coreInfluence = smoothstep(2.0, 8.0, distToCore) * (1.0 - uCorePulse * 0.3);
                    
                    // Size breathing
                    float sizeMult = 1.0 + sin(uTime * 1.2 + phase) * 0.15;
                    sizeMult *= mix(1.0, uCorePulse, 0.4);
                    
                    vSize = baseSize * sizeMult * coreInfluence;
                    
                    // Color shift toward cyan during states
                    vec3 shiftedColor = mix(vColor, vec3(0.0, 1.0, 1.0), uColorShift * 0.5);
                    vColor = shiftedColor;
                    
                    vec4 mv = modelViewMatrix * vec4(pos, 1.0);
                    gl_PointSize = vSize * (300.0 / -mv.z);
                    gl_Position = projectionMatrix * mv;
                }
            `,
            fragmentShader: `
                uniform sampler2D uTexture;
                varying vec3 vColor;
                varying float vSize;
                varying float vPhase;
                
                void main() {
                    vec4 tex = texture2D(uTexture, gl_PointCoord);
                    
                    // Soft circular falloff
                    float dist = length(gl_PointCoord - 0.5) * 2.0;
                    float alpha = smoothstep(1.0, 0.0, dist) * tex.a;
                    
                    // Additive glow core
                    vec3 glow = vColor * (1.0 + sin(vPhase) * 0.2) * (1.0 + 0.5 * tex.r);
                    
                    gl_FragColor = vec4(glow * 1.5, alpha * 0.95);
                }
            `,
            transparent: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
            depthTest: true,
        });

        this.particles = new THREE.Points(geometry, material);
        this.particlesGroup = new THREE.Group();
        this.particlesGroup.add(this.particles);
        this.scene.add(this.particlesGroup);
    }

    // ================================================================
    // CONSTELLATION WEB (Golden Connections)
    // ================================================================
    _createConstellationWeb() {
        const maxEdges = this.maxEdges;
        const linePositions = new Float32Array(maxEdges * 6);
        const lineColors = new Float32Array(maxEdges * 6);
        const lineWidths = new Float32Array(maxEdges * 2);

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(lineColors, 3));
        geometry.setAttribute('width', new THREE.BufferAttribute(lineWidths, 1));

        const material = new THREE.LineBasicMaterial({
            vertexColors: true,
            transparent: true,
            opacity: 1.0,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
            depthTest: true,
        });

        this.lines = new THREE.LineSegments(geometry, material);
        this.lines.geometry.setDrawRange(0, 0);
        this.particlesGroup.add(this.lines);

        this.linePositions = linePositions;
        this.lineColors = lineColors;
        this.lineWidths = lineWidths;
    }

    _updateConstellationWeb() {
        const pos = this.nodePositions;
        const count = this.nodeCount;
        const maxDist = this.CONNECT_DIST;
        const maxEdges = this.maxEdges;
        const lp = this.linePositions;
        const lc = this.lineColors;
        const lw = this.lineWidths;
        let edgeIdx = 0;

        // Connect nearby particles - use spatial hashing for efficiency
        const step = Math.max(1, Math.floor(count / 250));
        
        for (let i = 0; i < count && edgeIdx < maxEdges; i += step) {
            const ax = pos[i * 3], ay = pos[i * 3 + 1], az = pos[i * 3 + 2];
            for (let j = i + 1; j < count && edgeIdx < maxEdges; j += 1) {
                const dx = pos[j * 3] - ax;
                const dy = pos[j * 3 + 1] - ay;
                const dz = pos[j * 3 + 2] - az;
                const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
                
                if (dist < maxDist) {
                    const idx = edgeIdx * 6;
                    const alpha = 1.0 - dist / maxDist;
                    const brightness = 0.12 + alpha * 0.7;
                    const width = 0.5 + alpha * 1.5;
                    
                    lp[idx]     = pos[i * 3];
                    lp[idx + 1] = pos[i * 3 + 1];
                    lp[idx + 2] = pos[i * 3 + 2];
                    lp[idx + 3] = pos[j * 3];
                    lp[idx + 4] = pos[j * 3 + 1];
                    lp[idx + 5] = pos[j * 3 + 2];
                    
                    // Golden gradient along line
                    const goldR = 1.0;
                    const goldG = 0.6 + alpha * 0.3;
                    const goldB = 0.0;
                    
                    lc[idx]     = goldR * brightness;
                    lc[idx + 1] = goldG * brightness;
                    lc[idx + 2] = goldB;
                    lc[idx + 3] = goldR * brightness;
                    lc[idx + 4] = goldG * brightness;
                    lc[idx + 5] = goldB;
                    
                    lw[edgeIdx * 2]     = width;
                    lw[edgeIdx * 2 + 1] = width;
                    
                    edgeIdx++;
                }
            }
        }

        this.lines.geometry.attributes.position.needsUpdate = true;
        this.lines.geometry.attributes.color.needsUpdate = true;
        this.lines.geometry.attributes.width.needsUpdate = true;
        this.lines.geometry.setDrawRange(0, edgeIdx * 2);
        this.edgeCount = edgeIdx;
    }

    // ================================================================
    // NEURAL PULSES (Data Packets)
    // ================================================================
    _createPulse() {
        this.pulsePool = [];
        this.pulsePoolSize = 30;
        
        const geo = new THREE.SphereGeometry(0.15, 10, 10);
        for (let i = 0; i < this.pulsePoolSize; i++) {
            const mat = new THREE.MeshBasicMaterial({
                color: this.GOLD_BRIGHT,
                transparent: true,
                opacity: 0,
                blending: THREE.AdditiveBlending,
                depthWrite: false,
            });
            const mesh = new THREE.Mesh(geo, mat);
            mesh.visible = false;
            mesh.scale.setScalar(0.5);
            this.particlesGroup.add(mesh);
            this.pulsePool.push({
                mesh,
                active: false,
                t: 0,
                speed: 0,
                src: new THREE.Vector3(),
                dst: new THREE.Vector3(),
                size: 0.5 + Math.random() * 0.5,
            });
        }
        this.activePulseCount = 0;
    }

    _spawnPulse() {
        if (this.edgeCount === 0) return;
        
        for (const p of this.pulsePool) {
            if (p.active) continue;
            const idx = Math.floor(Math.random() * this.edgeCount) * 6;
            const lp = this.linePositions;
            p.src.set(lp[idx], lp[idx + 1], lp[idx + 2]);
            p.dst.set(lp[idx + 3], lp[idx + 4], lp[idx + 5]);
            p.t = 0;
            p.speed = (1.8 + Math.random() * 2.5) * this.currentPulseSpeedMult;
            p.active = true;
            p.mesh.visible = true;
            p.mesh.material.opacity = 1;
            p.mesh.scale.setScalar(p.size);
            this.activePulseCount++;
            return;
        }
    }

    _updatePulse(dt) {
        // Spawn pulses to match target (max 30 attempts to prevent infinite loop)
        let _pulseSafety = 0;
        while (this.activePulseCount < Math.floor(this.currentMaxPulses) && this.edgeCount > 0 && _pulseSafety < 30) {
            this._spawnPulse();
            _pulseSafety++;
        }

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
                // Ease in/out with glow
                const alpha = p.t < 0.2 ? p.t / 0.2 : (1 - p.t) / 0.8;
                const scale = 0.6 + alpha * 1.0;
                p.mesh.material.opacity = alpha * 1.0;
                p.mesh.scale.setScalar(scale);
                // Color shift during travel
                const shift = Math.min(this._currentColorShift * 2, 1);
                p.mesh.material.color.setHex(
                    shift > 0.5 ? this.CYAN : this.GOLD_BRIGHT
                );
            }
        }
    }

    // ================================================================
    // HOLOGRAPHIC RINGS (The Iconic Spinning Rings)
    // ================================================================
    _createHolographicRings() {
        this.ringGroup = new THREE.Group();
        this.rings = [];

        const ringDefs = [
            // Inner ring - fast, tight
            { radius: 16, tube: 0.025, segments: 144, dash: 2.5, gap: 3, speed: 0.12, axis: 'y', color: this.GOLD, opacity: 0.6 },
            // Middle ring - medium, reverse
            { radius: 20, tube: 0.02, segments: 180, dash: 4, gap: 5, speed: -0.08, axis: 'x', color: this.GOLD_WARM, opacity: 0.5 },
            // Outer ring - slow, wide
            { radius: 25, tube: 0.015, segments: 220, dash: 3, gap: 7, speed: 0.05, axis: 'y', color: this.GOLD_DIM, opacity: 0.4 },
            // Focal ring - the "eye"
            { radius: 8, tube: 0.03, segments: 96, dash: 0, gap: 0, speed: 0.2, axis: 'z', color: this.GOLD_BRIGHT, opacity: 0.9 },
        ];

        for (const def of ringDefs) {
            if (def.dash > 0) {
                // Dashed ring
                const points = [];
                for (let i = 0; i <= def.segments; i++) {
                    const angle = (i / def.segments) * Math.PI * 2;
                    points.push(new THREE.Vector3(
                        Math.cos(angle) * def.radius,
                        Math.sin(angle) * def.radius,
                        0
                    ));
                }
                const geo = new THREE.BufferGeometry().setFromPoints(points);
                const mat = new THREE.LineDashedMaterial({
                    color: def.color,
                    dashSize: def.dash,
                    gapSize: def.gap,
                    transparent: true,
                    opacity: def.opacity,
                    blending: THREE.AdditiveBlending,
                    depthWrite: false,
                    linewidth: 2,
                });
                const ring = new THREE.Line(geo, mat);
                ring.computeLineDistances();
                ring.userData = { speed: def.speed, axis: def.axis, baseOpacity: def.opacity };
                
                // Rotate to correct axis
                if (def.axis === 'x') ring.rotation.x = Math.PI / 2;
                else if (def.axis === 'y') ring.rotation.y = Math.PI / 2;
                else if (def.axis === 'z') ring.rotation.z = Math.PI / 2;
                
                this.ringGroup.add(ring);
                this.rings.push(ring);
            } else {
                // Solid ring (aperture/focal)
                const geo = new THREE.RingGeometry(def.radius - 0.15, def.radius + 0.15, def.segments);
                const mat = new THREE.MeshBasicMaterial({
                    color: def.color,
                    transparent: true,
                    opacity: def.opacity * 0.3,
                    side: THREE.DoubleSide,
                    blending: THREE.AdditiveBlending,
                    depthWrite: false,
                });
                const ring = new THREE.Mesh(geo, mat);
                ring.userData = { speed: def.speed, axis: def.axis, baseOpacity: def.opacity * 0.3 };
                if (def.axis === 'x') ring.rotation.x = Math.PI / 2;
                else if (def.axis === 'y') ring.rotation.y = Math.PI / 2;
                else ring.rotation.z = Math.PI / 2;
                this.ringGroup.add(ring);
                this.rings.push(ring);
            }
        }

        // Aperture crosshair (the "eye")
        const apertureGeo = new THREE.RingGeometry(3.5, 4.5, 64);
        const apertureMat = new THREE.MeshBasicMaterial({
            color: this.GOLD,
            transparent: true,
            opacity: 0.2,
            side: THREE.DoubleSide,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        });
        this.aperture = new THREE.Mesh(apertureGeo, apertureMat);
        this.aperture.position.z = 0.8;
        this.ringGroup.add(this.aperture);

        // Crosshair lines
        const chMat = new THREE.LineBasicMaterial({
            color: this.GOLD_BRIGHT, transparent: true, opacity: 0.5,
            blending: THREE.AdditiveBlending, depthWrite: false,
        });
        const ch1 = new THREE.Line(new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(-6, 0, 0.8), new THREE.Vector3(6, 0, 0.8)
        ]), chMat);
        const ch2 = new THREE.Line(new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(0, -6, 0.8), new THREE.Vector3(0, 6, 0.8)
        ]), chMat);
        this.ringGroup.add(ch1, ch2);

        // Rotate rings initially
        this.ringGroup.rotation.x = 0.15;
        this.ringGroup.rotation.y = -0.1;
        this.scene.add(this.ringGroup);
    }

    // ================================================================
    // CORE GLOW (The Heart)
    // ================================================================
    _createCoreGlow() {
        const geo = new THREE.SphereGeometry(2.2, 48, 48);
        const mat = new THREE.ShaderMaterial({
            uniforms: {
                uTime: { value: 0 },
                uColor: { value: new THREE.Color(this.GOLD) },
                uPulse: { value: 1.0 },
            },
            vertexShader: `
                varying vec3 vNormal;
                varying vec3 vWorldPos;
                void main() {
                    vNormal = normalize(normalMatrix * normal);
                    vWorldPos = (modelMatrix * vec4(position, 1.0)).xyz;
                    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                }
            `,
            fragmentShader: `
                uniform float uTime;
                uniform vec3 uColor;
                uniform float uPulse;
                varying vec3 vNormal;
                varying vec3 vWorldPos;
                
                void main() {
                    // Fresnel effect - glow at edges
                    float facing = dot(vNormal, vec3(0.0, 0.0, 1.0));
                    float fresnel = pow(1.0 - max(facing, 0.0), 3.0);
                    
                    // Core pulse
                    float pulse = 1.0 + sin(uTime * 2.0) * 0.25;
                    pulse *= uPulse;
                    
                    // Distance from center for inner glow
                    float dist = length(vWorldPos);
                    float innerGlow = smoothstep(2.2, 1.0, dist) * 0.5;
                    
                    vec3 glow = uColor * (fresnel * 2.5 + innerGlow) * pulse;
                    
                    gl_FragColor = vec4(glow * 1.8, (fresnel * 0.9 + innerGlow * 0.4) * uPulse);
                }
            `,
            transparent: true,
            blending: THREE.AdditiveBlending,
            side: THREE.BackSide,
            depthWrite: false,
            depthTest: true,
        });

        this.coreGlow = new THREE.Mesh(geo, mat);
        this.coreGlow.scale.setScalar(1.0);
        this.scene.add(this.coreGlow);
    }

    // ================================================================
    // CORE PULSE (Central Burst)
    // ================================================================
    _createCorePulse() {
        const geo = new THREE.SphereGeometry(1.0, 32, 32);
        const mat = new THREE.ShaderMaterial({
            uniforms: {
                uTime: { value: 0 },
                uColor: { value: new THREE.Color(this.GOLD_BRIGHT) },
                uIntensity: { value: 1.0 },
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
                uniform float uIntensity;
                varying vec3 vNormal;
                
                void main() {
                    float facing = dot(vNormal, vec3(0.0, 0.0, 1.0));
                    float fresnel = pow(1.0 - max(facing, 0.0), 2.0);
                    
                    // Pulsing core
                    float pulse = 0.5 + 0.5 * sin(uTime * 3.0);
                    pulse = uIntensity * (0.7 + pulse * 0.5);
                    
                    // Central hot spot
                    float center = 1.0 - facing;
                    center = pow(center, 8.0) * uIntensity;
                    
                    vec3 glow = uColor * (fresnel * 1.5 + center * 3.0);
                    
                    gl_FragColor = vec4(glow * 2.0, (fresnel * 0.6 + center) * uIntensity);
                }
            `,
            transparent: true,
            blending: THREE.AdditiveBlending,
            side: THREE.FrontSide,
            depthWrite: false,
            depthTest: true,
        });

        this.corePulseMesh = new THREE.Mesh(geo, mat);
        this.corePulseMesh.scale.setScalar(1.5);
        this.scene.add(this.corePulseMesh);
    }

    // ================================================================
    // DATA LOADING
    // ================================================================
    async loadData() {
        try {
            const res = await fetch('/api/system/graph/data?limit=300');
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
            const phi = Math.acos(2 * (i / count) - 1);
            const theta = (i / count) * Math.PI * 2 * 1.618;
            const r = this.SPACE_RADIUS * (0.4 + Math.random() * 0.6);
            
            pos[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
            pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
            pos[i * 3 + 2] = r * Math.cos(phi);
            
            // Update velocity base
            this.nodeVelocities[i * 3]     = pos[i * 3];
            this.nodeVelocities[i * 3 + 1] = pos[i * 3 + 1];
            this.nodeVelocities[i * 3 + 2] = pos[i * 3 + 2];
        }
        this.particles.geometry.attributes.position.needsUpdate = true;
    }

    // ================================================================
    // STATE SYSTEM (The Brain)
    // ================================================================
    setState(newState) {
        if (this.state === newState) return;
        const oldState = this.state;
        this.state = newState;

        switch (newState) {
            case 'idle':
                this.targetBloom = 2.2;
                this.targetRotSpeed = 0.0008;
                this.targetRingSpeedMult = 1.0;
                this.targetLineOpacity = 0.35;
                this.targetCorePulseSpeed = 1.5;
                this.targetMaxPulses = 2;
                this.targetPulseSpeedMult = 1.2;
                this._targetColorShift = 0;
                this._targetParticleDrift = 0.0003;
                break;
            case 'listening':
                this.targetBloom = 2.8;
                this.targetRotSpeed = 0.0018;
                this.targetRingSpeedMult = 2.0;
                this.targetLineOpacity = 0.55;
                this.targetCorePulseSpeed = 3.0;
                this.targetMaxPulses = 4;
                this.targetPulseSpeedMult = 2.0;
                this._targetColorShift = 0.1;
                this._targetParticleDrift = 0.0006;
                break;
            case 'thinking':
                this.targetBloom = 3.5;
                this.targetRotSpeed = 0.0035;
                this.targetRingSpeedMult = 3.5;
                this.targetLineOpacity = 0.8;
                this.targetCorePulseSpeed = 5.0;
                this.targetMaxPulses = 10;
                this.targetPulseSpeedMult = 4.0;
                this._targetColorShift = 0.05;
                this._targetParticleDrift = 0.0015;
                break;
            case 'planning':
                this.targetBloom = 3.0;
                this.targetRotSpeed = 0.0025;
                this.targetRingSpeedMult = 2.8;
                this.targetLineOpacity = 0.7;
                this.targetCorePulseSpeed = 4.0;
                this.targetMaxPulses = 8;
                this.targetPulseSpeedMult = 3.5;
                this._targetColorShift = 0.1;
                this._targetParticleDrift = 0.001;
                this._expandNetwork = true;
                break;
            case 'delegating':
                this.targetBloom = 3.8;
                this.targetRotSpeed = 0.0045;
                this.targetRingSpeedMult = 4.5;
                this.targetLineOpacity = 0.9;
                this.targetCorePulseSpeed = 6.0;
                this.targetMaxPulses = 15;
                this.targetPulseSpeedMult = 5.0;
                this._targetColorShift = 0.15;
                this._targetParticleDrift = 0.002;
                this._delegationBurst = true;
                break;
            case 'working':
                this.targetBloom = 3.2;
                this.targetRotSpeed = 0.003;
                this.targetRingSpeedMult = 3.0;
                this.targetLineOpacity = 0.75;
                this.targetCorePulseSpeed = 4.5;
                this.targetMaxPulses = 10;
                this.targetPulseSpeedMult = 3.5;
                this._targetColorShift = 0.1;
                this._targetParticleDrift = 0.0012;
                break;
            case 'retrieving':
                this.targetBloom = 3.0;
                this.targetRotSpeed = 0.0012;
                this.targetRingSpeedMult = 2.0;
                this.targetLineOpacity = 0.7;
                this.targetCorePulseSpeed = 3.0;
                this.targetMaxPulses = 6;
                this.targetPulseSpeedMult = 2.5;
                this._targetColorShift = 0.35; // cyan-gold
                this._targetParticleDrift = -0.0015; // inward
                this._memoryFlash = true;
                break;
            case 'reviewing':
                this.targetBloom = 2.4;
                this.targetRotSpeed = 0.001;
                this.targetRingSpeedMult = 1.5;
                this.targetLineOpacity = 0.5;
                this.targetCorePulseSpeed = 2.5;
                this.targetMaxPulses = 4;
                this.targetPulseSpeedMult = 1.8;
                this._targetColorShift = 0.05;
                this._targetParticleDrift = 0.0004;
                break;
            case 'speaking':
                this.targetBloom = 2.8;
                this.targetRotSpeed = 0.002;
                this.targetRingSpeedMult = 2.2;
                this.targetLineOpacity = 0.6;
                this.targetCorePulseSpeed = 3.5;
                this.targetMaxPulses = 5;
                this.targetPulseSpeedMult = 2.5;
                this._targetColorShift = 0;
                this._targetParticleDrift = 0.0008;
                break;
            case 'complete':
                this.targetBloom = 2.5;
                this.targetRotSpeed = 0.0005;
                this.targetRingSpeedMult = 0.8;
                this.targetLineOpacity = 0.4;
                this.targetCorePulseSpeed = 1.2;
                this.targetMaxPulses = 2;
                this.targetPulseSpeedMult = 1.0;
                this._targetColorShift = 0;
                this._targetParticleDrift = 0.0001;
                this._completionPulse = true;
                break;
            case 'error':
                this.targetBloom = 3.0;
                this.targetRotSpeed = 0.002;
                this.targetRingSpeedMult = 2.0;
                this.targetLineOpacity = 0.6;
                this.targetCorePulseSpeed = 8.0;
                this.targetMaxPulses = 8;
                this.targetPulseSpeedMult = 3.0;
                this._targetColorShift = 0;
                this._targetParticleDrift = 0.001;
                // Flash red handled by color shift
                break;
        }

        // Emit event
        window.dispatchEvent(new CustomEvent('jarvis-state-change', {
            detail: { from: oldState, to: newState }
        }));
    }

    // ================================================================
    // RENDER LOOP
    // ================================================================
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
        this.dt = Math.min((now - this._lastTime) / 1000, 0.05);
        this._lastTime = now;
        this.time += this.dt;

        // ---- Smooth interpolation ----
        const lerp = 0.035;
        this.currentRotSpeed += (this.targetRotSpeed - this.currentRotSpeed) * lerp;
        this.currentRingSpeedMult += (this.targetRingSpeedMult - this.currentRingSpeedMult) * lerp;
        this.currentLineOpacity += (this.targetLineOpacity - this.currentLineOpacity) * lerp;
        this.currentMaxPulses += (this.targetMaxPulses - this.currentMaxPulses) * lerp;
        this.currentPulseSpeedMult += (this.targetPulseSpeedMult - this.currentPulseSpeedMult) * lerp;
        this._currentColorShift += ((this._targetColorShift || 0) - this._currentColorShift) * lerp;
        this._currentParticleDrift += ((this._targetParticleDrift || 0) - this._currentParticleDrift) * lerp;

        // ---- Bloom lerp ----
        if (this.bloomPass) {
            const bloomLerp = 0.05;
            this._bloomStrength += (this.targetBloom - this._bloomStrength) * bloomLerp;
            this.bloomPass.strength = this._bloomStrength;
        }

        // ---- Core pulse uniform ----
        if (this.coreGlow && this.coreGlow.material.uniforms) {
            const pulseLerp = 0.08;
            const currentPulse = this.coreGlow.material.uniforms.uPulse?.value || 1;
            const targetPulse = this.targetCorePulseSpeed / 2.0;
            this.coreGlow.material.uniforms.uPulse.value = currentPulse + (targetPulse - currentPulse) * pulseLerp;
            this.coreGlow.material.uniforms.uTime.value = this.time;
        }
        
        if (this.corePulseMesh && this.corePulseMesh.material.uniforms) {
            this.corePulseMesh.material.uniforms.uTime.value = this.time;
            this.corePulseMesh.material.uniforms.uIntensity.value = this.targetCorePulseSpeed / 4.0;
        }

        // ---- Color shift ----
        if (this.particles && this.particles.material.uniforms) {
            this.particles.material.uniforms.uColorShift.value = this._currentColorShift;
            this.particles.material.uniforms.uCorePulse.value = this.targetCorePulseSpeed / 4.0;
            this.particles.material.uniforms.uTime.value = this.time;
        }

        // ---- Core pulse mesh ----
        if (this.corePulseMesh) {
            const pulseScale = 1.0 + Math.sin(this.time * this.targetCorePulseSpeed) * 0.12;
            this.corePulseMesh.scale.setScalar(1.5 * pulseScale);
            this.corePulseMesh.rotation.y += this.dt * 0.3;
            this.corePulseMesh.rotation.x += this.dt * 0.15;
        }

        // ---- Core glow ----
        if (this.coreGlow) {
            this.coreGlow.rotation.y += this.dt * 0.08;
            this.coreGlow.rotation.x += this.dt * 0.04;
            const pulseScale = 1.0 + Math.sin(this.time * this.targetCorePulseSpeed) * 0.08;
            this.coreGlow.scale.setScalar(pulseScale);
        }

        // ---- Triggered events ----
        if (this._expandNetwork) {
            this._triggerNetworkExpansion();
            this._expandNetwork = false;
        }
        if (this._delegationBurst) {
            this._triggerDelegationBurst();
            this._delegationBurst = false;
        }
        if (this._memoryFlash) {
            this._triggerMemoryFlash();
            this._memoryFlash = false;
        }
        if (this._completionPulse) {
            this._triggerCompletionPulse();
            this._completionPulse = false;
        }

        // ---- Ambient breathing ----
        this._breathPhase += this.dt * 0.7;
        this._ambientPhase += this.dt;
        const breathScale = 1.0 + Math.sin(this._breathPhase) * 0.012;
        this.particlesGroup.scale.setScalar(breathScale);

        // ---- Particle animation ----
        this._animateParticles();
        
        // ---- Constellation web (update every 6 frames to save CPU) ----
        this._frameCount++;
        if (this._frameCount % 6 === 0) {
            this._updateConstellationWeb();
        }
        
        // ---- Pulses ----
        this._updatePulse(this.dt);
        
        // ---- Rings ----
        this._updateRings();

        // ---- Mouse parallax ----
        this.mouse.x += (this.mouse.tx - this.mouse.x) * 0.035;
        this.mouse.y += (this.mouse.ty - this.mouse.y) * 0.035;

        // ---- Camera orbit ----
        this.orbit.theta += (this.orbitDamping.theta - this.orbit.theta) * 0.05;
        this.orbit.phi += (this.orbitDamping.phi - this.orbit.phi) * 0.05;
        this.orbitDamping.theta += this.currentRotSpeed;

        const target = this.orbit.target;
        target.x += (this.mouse.x * 1.5 - target.x) * 0.02;
        target.y += (this.mouse.y * 1.5 - target.y) * 0.02;

        this.orbit.theta = (this.orbit.theta + this.currentRotSpeed) % (Math.PI * 2);
        
        this.camera.position.x = this.orbit.radius * Math.sin(this.orbit.phi) * Math.cos(this.orbit.theta) + target.x;
        this.camera.position.y = this.orbit.radius * Math.cos(this.orbit.phi) + target.y;
        this.camera.position.z = this.orbit.radius * Math.sin(this.orbit.phi) * Math.sin(this.orbit.theta) + target.z;
        this.camera.lookAt(target);

        // ---- Render ----
        if (this.composer) {
            this.composer.render();
        } else {
            this.renderer.render(this.scene, this.camera);
        }
    }

    _animateParticles() {
        const positions = this.nodePositions;
        const phases = this.nodePhases;
        const velocities = this.nodeVelocities;
        const baseSizes = this.nodeBaseSizes;
        const count = this.nodeCount;
        const drift = this._currentParticleDrift;
        
        for (let i = 0; i < count; i++) {
            // Organic drift using noise-like movement
            const phase = phases[i];
            const t = this.time + phase;
            
            // Multi-octave drift
            const dx = Math.sin(t * 0.7 + i * 0.01) * 0.02;
            const dy = Math.cos(t * 0.5 + i * 0.013) * 0.02;
            const dz = Math.sin(t * 0.9 + i * 0.007) * 0.02;
            
            // Apply drift toward/away from center
            const vx = velocities[i * 3];
            const vy = velocities[i * 3 + 1];
            const vz = velocities[i * 3 + 2];
            
            const dist = Math.sqrt(vx * vx + vy * vy + vz * vz);
            const dirX = vx / (dist || 1);
            const dirY = vy / (dist || 1);
            const dirZ = vz / (dist || 1);
            
            // Apply drift
            positions[i * 3]     += (dx + dirX * drift) * this.dt * 60;
            positions[i * 3 + 1] += (dy + dirY * drift) * this.dt * 60;
            positions[i * 3 + 2] += (dz + dirZ * drift) * this.dt * 60;
            
            // Boundary constraint - keep in sphere
            const newDist = Math.sqrt(
                positions[i * 3] ** 2 + 
                positions[i * 3 + 1] ** 2 + 
                positions[i * 3 + 2] ** 2
            );
            if (newDist > this.SPACE_RADIUS * 1.1) {
                const scale = (this.SPACE_RADIUS * 1.1) / newDist;
                positions[i * 3]     *= scale;
                positions[i * 3 + 1] *= scale;
                positions[i * 3 + 2] *= scale;
            }
        }
        
        this.particles.geometry.attributes.position.needsUpdate = true;
    }

    _updateRings() {
        for (const ring of this.rings) {
            const speed = ring.userData.speed * this.currentRingSpeedMult;
            const axis = ring.userData.axis;
            if (axis === 'x') ring.rotation.x += this.dt * speed;
            else if (axis === 'y') ring.rotation.y += this.dt * speed;
            else ring.rotation.z += this.dt * speed;
            
            if (ring.material && ring.material.opacity !== undefined) {
                const baseOp = ring.userData.baseOpacity || 0.3;
                ring.material.opacity = baseOp * (0.7 + 0.3 * Math.sin(this.time * 2));
            }
        }
        
        if (this.aperture) {
            this.aperture.rotation.z += this.dt * 0.4;
            this.aperture.material.opacity = 0.15 + 0.1 * Math.sin(this.time * 2);
        }
    }

    // ================================================================
    // SPECIAL EFFECTS
    // ================================================================
    _triggerNetworkExpansion() {
        // Emit new particles outward
        for (let i = 0; i < 50; i++) {
            setTimeout(() => {
                this._spawnPulse();
            }, i * 30);
        }
    }

    _triggerDelegationBurst() {
        // Massive pulse burst
        for (let i = 0; i < 20; i++) {
            setTimeout(() => this._spawnPulse(), i * 25);
        }
        // Flash rings
        for (const ring of this.rings) {
            ring.material.opacity = Math.min(1, (ring.userData.baseOpacity || 0.3) * 2.5);
            setTimeout(() => { ring.material.opacity = ring.userData.baseOpacity || 0.3; }, 300);
        }
    }

    _triggerMemoryFlash() {
        // Cyan flash - particles shift color
        const origColor = this.particles.material.uniforms.uColorShift.value;
        this.particles.material.uniforms.uColorShift.value = 0.6;
        setTimeout(() => {
            this.particles.material.uniforms.uColorShift.value = origColor;
        }, 500);
    }

    _triggerCompletionPulse() {
        // Golden wave from center
        for (let i = 0; i < 8; i++) {
            setTimeout(() => this._spawnPulse(), i * 50);
        }
        // Core glow burst
        if (this.coreGlow && this.coreGlow.material.uniforms) {
            this.coreGlow.material.uniforms.uPulse.value = 3.0;
            setTimeout(() => { this.coreGlow.material.uniforms.uPulse.value = 1.0; }, 600);
        }
    }

    // ================================================================
    // EVENTS
    // ================================================================
    _onResize() {
        this.W = window.innerWidth;
        this.H = window.innerHeight;
        this.camera.aspect = this.W / this.H;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(this.W, this.H);
        if (this.composer) this.composer.setSize(this.W, this.H);
    }

    _onMouseMove(e) {
        if (!this.interactive) return;
        this.mouse.tx = (e.clientX / this.W - 0.5) * 2;
        this.mouse.ty = -(e.clientY / this.H - 0.5) * 2;
    }

    _onWheel(e) {
        if (!this.interactive) return;
        e.preventDefault();
        this.orbit.radius = Math.max(16, Math.min(60, this.orbit.radius + e.deltaY * 0.015));
    }

    setInteractionEnabled(enabled) {
        if (this.interactive === enabled) return;
        this.interactive = enabled;
        if (!enabled) {
            this._detachInteractionListeners();
            this.mouse.tx = this.mouse.ty = 0;
            this.orbitDamping.theta = this.orbit.theta;
            this.orbitDamping.phi = this.orbit.phi;
            this._dragging = false;
        } else {
            this._attachInteractionListeners();
        }
    }

    _attachInteractionListeners() {
        if (!this.interactive || this._interactionBound) return;
        window.addEventListener('mousemove', this._boundMouseMove);
        this.container.addEventListener('wheel', this._boundWheel, { passive: false });
        this.container.addEventListener('mousedown', this._boundMouseDown);
        window.addEventListener('mouseup', this._boundMouseUp);
        window.addEventListener('mousemove', this._boundDrag);
        this._interactionBound = true;
    }

    _detachInteractionListeners() {
        if (!this._interactionBound) return;
        window.removeEventListener('mousemove', this._boundMouseMove);
        window.removeEventListener('mousemove', this._boundDrag);
        this.container.removeEventListener('wheel', this._boundWheel);
        this.container.removeEventListener('mousedown', this._boundMouseDown);
        window.removeEventListener('mouseup', this._boundMouseUp);
        this._interactionBound = false;
    }

    destroy() {
        this.stop();
        window.removeEventListener('resize', this._boundResize);
        this._detachInteractionListeners();

        if (this.scene) {
            this.scene.traverse(obj => {
                if (obj.geometry) obj.geometry.dispose();
                if (obj.material) {
                    if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose());
                    else obj.material.dispose();
                }
            });
        }
        if (this.composer) this.composer.dispose?.();
        if (this.bloomPass) this.bloomPass.dispose?.();
        if (this.renderer) {
            this.renderer.dispose();
            if (this.renderer.domElement?.parentNode) {
                this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
            }
        }
        this.scene = this.camera = this.renderer = this.composer = this.bloomPass = null;
        this.particles = this.lines = this.ringGroup = this.coreGlow = this.corePulseMesh = null;
    }
}

window.Graph3D = Graph3D;