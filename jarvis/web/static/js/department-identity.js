/**
 * Department Identity — v3.2.0
 *
 * Each King gets a unique visual identity:
 *   Engineering: blue/geometric (sharp angles, grid patterns)
 *   Research: purple/organic (flowing, radial growth)
 *   Personal: green/calm (smooth, breathing)
 *   System: orange/angular (mechanical, rotating)
 *
 * These appear as department badges and influence
 * the Three.js core rendering when tasks are delegated.
 */

const DEPARTMENTS = {
    engineering: {
        name: 'Engineering',
        color: '#0088ff',
        colorAlt: '#00aaff',
        icon: '\u2699',   // gear
        shape: 'hexagon',
        pattern: 'grid',
        motto: 'Build & Execute',
    },
    research: {
        name: 'Research',
        color: '#8844ff',
        colorAlt: '#aa66ff',
        icon: '\U0001f52d', // telescope
        shape: 'circle',
        pattern: 'radial',
        motto: 'Discover & Analyze',
    },
    personal: {
        name: 'Personal',
        color: '#00cc66',
        colorAlt: '#33dd88',
        icon: '\U0001f3e0', // house
        shape: 'rounded',
        pattern: 'breathing',
        motto: 'Organize & Assist',
    },
    system: {
        name: 'System',
        color: '#ff8800',
        colorAlt: '#ffaa33',
        icon: '\u2699', // gear (same but different color)
        shape: 'angular',
        pattern: 'mechanical',
        motto: 'Maintain & Optimize',
    },
};

class DepartmentIdentity {
    constructor() {
        this.badgeContainer = document.getElementById('department-badges');
        this._active = null;
        this._animFrame = null;
    }

    /**
     * Create department badge HTML
     */
    renderBadge(department) {
        const dept = DEPARTMENTS[department];
        if (!dept) return '';

        return `
            <div class="dept-badge dept-${department}" data-dept="${department}"
                 style="--dept-color: ${dept.color}; --dept-alt: ${dept.colorAlt};">
                <div class="dept-icon">${dept.icon}</div>
                <div class="dept-name">${dept.name}</div>
                <div class="dept-motto">${dept.motto}</div>
            </div>
        `;
    }

    /**
     * Render all department badges
     */
    renderAll() {
        if (!this.badgeContainer) return;
        this.badgeContainer.innerHTML = Object.keys(DEPARTMENTS)
            .map(d => this.renderBadge(d)).join('');
    }

    /**
     * Highlight active department during delegation
     */
    setActive(department) {
        this._active = department;
        if (this.badgeContainer) {
            const badges = this.badgeContainer.querySelectorAll('.dept-badge');
            badges.forEach(b => {
                b.classList.toggle('active', b.dataset.dept === department);
            });
        }
    }

    /**
     * Get department color for Three.js state changes
     */
    getColor(department) {
        return DEPARTMENTS[department]?.color || '#00f0ff';
    }

    /**
     * Map king ID to department
     */
    getDepartment(kingId) {
        const map = {
            'king-1': 'engineering',
            'king-2': 'research',
            'king-3': 'personal',
            'king-4': 'system',
        };
        return map[kingId] || 'engineering';
    }

    /**
     * Get shape SVG for department
     */
    getShape(department, size = 40) {
        const dept = DEPARTMENTS[department];
        if (!dept) return '';

        const cx = size / 2;
        const cy = size / 2;
        const r = size / 2 - 2;

        switch (dept.shape) {
            case 'hexagon': {
                const pts = [];
                for (let i = 0; i < 6; i++) {
                    const angle = (Math.PI / 3) * i - Math.PI / 2;
                    pts.push(`${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`);
                }
                return `<svg width="${size}" height="${size}"><polygon points="${pts.join(' ')}" fill="none" stroke="${dept.color}" stroke-width="2"/></svg>`;
            }
            case 'circle':
                return `<svg width="${size}" height="${size}"><circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${dept.color}" stroke-width="2"/></svg>`;
            case 'rounded':
                return `<svg width="${size}" height="${size}"><rect x="2" y="2" width="${size - 4}" height="${size - 4}" rx="${r / 2}" fill="none" stroke="${dept.color}" stroke-width="2"/></svg>`;
            case 'angular':
                return `<svg width="${size}" height="${size}"><polygon points="${cx},${2} ${size - 2},${cy} ${cx},${size - 2} 2,${cy}" fill="none" stroke="${dept.color}" stroke-width="2"/></svg>`;
            default:
                return '';
        }
    }
}

// Export
window.DepartmentIdentity = DepartmentIdentity;
window.DEPARTMENTS = DEPARTMENTS;
