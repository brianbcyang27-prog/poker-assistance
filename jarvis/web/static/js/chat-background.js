/**
 * Chat Background — golden core for the chat workspace.
 * Non-draggable, pointer-events disabled, reduced particles.
 */

class ChatBackground {
    constructor(container) {
        this.container = container;
        this.graph = null;
    }

    start() {
        if (this.graph) return;

        this.graph = new Graph3D(this.container);
        this.graph.NODE_COUNT = 150;
        this.graph.SPACE_RADIUS = 10;
        this.graph.CONNECT_DIST = 3.0;
        this.graph.init();
        this.graph.loadData();

        // Make background: non-interactive, subtle opacity
        const canvas = this.graph.renderer.domElement;
        canvas.style.pointerEvents = 'none';
        canvas.style.opacity = '0.25';
        canvas.style.position = 'absolute';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.zIndex = '0';

        // Disable mouse interaction
        this.graph._mouseDown = () => {};
        this.graph._mouseUp = () => {};
        this.graph._onMouseMove = () => {};

        this.graph.start();
    }

    stop() {
        if (this.graph) {
            this.graph.stop();
            this.graph = null;
        }
    }
}
