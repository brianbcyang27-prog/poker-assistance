/**
 * WebSocketManager tests
 */
describe('WebSocketManager', () => {
    let ws;

    beforeEach(() => {
        ws = new WebSocketManager();
    });

    afterEach(() => {
        ws.close();
    });

    test('initializes with correct defaults', () => {
        expect(ws._ws).toBeNull();
        expect(ws._listeners).toBeInstanceOf(Map);
        expect(ws.connected).toBe(false);
    });

    test('on/off registers and unregisters listeners', () => {
        const callback = jest.fn();
        const unsubscribe = ws.on('test', callback);

        expect(ws._listeners.get('test').has(callback)).toBe(true);

        unsubscribe();
        expect(ws._listeners.get('test').has(callback)).toBe(false);
    });

    test('off removes listener', () => {
        const callback = jest.fn();
        ws.on('test', callback);
        ws.off('test', callback);

        expect(ws._listeners.get('test').has(callback)).toBe(false);
    });

    test('_emit calls all listeners for event', () => {
        const cb1 = jest.fn();
        const cb2 = jest.fn();
        ws.on('test', cb1);
        ws.on('test', cb2);

        ws._emit('test', { data: 123 });

        expect(cb1).toHaveBeenCalledWith({ data: 123 });
        expect(cb2).toHaveBeenCalledWith({ data: 123 });
    });

    test('_emit handles listener errors gracefully', () => {
        const badCallback = () => { throw new Error('test'); };
        const goodCallback = jest.fn();
        ws.on('test', badCallback);
        ws.on('test', goodCallback);

        expect(() => ws._emit('test')).not.toThrow();
        expect(goodCallback).toHaveBeenCalled();
    });

    test('close sets intentionalClose flag', () => {
        ws._intentionalClose = false;
        ws.close();
        expect(ws._intentionalClose).toBe(true);
    });

    test('connected returns false when no socket', () => {
        expect(ws.connected).toBe(false);
    });
});
