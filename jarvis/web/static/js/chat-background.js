/**
 * Chat Background — miniature golden core for the chat workspace.
 * Non-draggable, reduced particle count, subtle opacity.
 */

class ChatBackground {
    constructor(container) {
        this.container = container;
        this.graph = null;
    }

    start() {
        if (this.graph) return;

        const canvas = document.createElement('canvas');
        canvas.id = 'chat-core-canvas';
        canvas.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;opacity:0.15;z-index:0;';
        this.container.prepend(canvas);

        this.graph = new Graph3D(this.container);
        this.graph.NODE_COUNT = 120;
        this.graph.SPACE_RADIUS = 10;
        this.graph.CONNECT_DIST = 3.0;
        this.graph.init();
        this.graph.loadData();

        this.graph.container = canvas;
        this.graph.renderer.domElement.style.pointerEvents = 'none';
        this.graph.renderer.domElement.style.opacity = '0.15';
        this.graph.renderer.domElement.style.position = 'absolute';
        this.graph.renderer.domElement.style.top = '0';
        this.graph.renderer.domElement.style.left = '0';
        this.graph.renderer.domElement.style.zIndex = '0';

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
