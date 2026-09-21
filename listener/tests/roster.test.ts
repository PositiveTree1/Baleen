import { streamEvents } from '../src/hypersync';

describe('server-owned roster at the ingestion boundary', () => {
  it('does not fetch or advance source blocks when the roster cannot be loaded', async () => {
    jest.useFakeTimers();
    const handlers: Record<string, () => void> = {};
    const on = jest.spyOn(process, 'on').mockImplementation(((name: string, handler: () => void) => {
      handlers[name] = handler; return process;
    }) as typeof process.on);
    const error = jest.spyOn(console, 'error').mockImplementation(() => {});
    const client = { getHeight: jest.fn(), get: jest.fn() };
    const consume = jest.fn();
    const roster = jest.fn().mockRejectedValue(new Error('HTTP 503'));
    try {
      const running = streamEvents(client, 100, consume, roster);
      await Promise.resolve(); await Promise.resolve();
      handlers.SIGTERM();
      await jest.runAllTimersAsync();
      await running;
      expect(roster).toHaveBeenCalledTimes(1);
      expect(client.getHeight).not.toHaveBeenCalled();
      expect(client.get).not.toHaveBeenCalled();
      expect(consume).not.toHaveBeenCalled();
    } finally { on.mockRestore(); error.mockRestore(); jest.useRealTimers(); }
  });
});
