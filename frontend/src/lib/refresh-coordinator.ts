export function createRefreshCoordinator<T>(
  rotate: (refresh: string) => Promise<T>,
  keyFor: (refresh: string) => string,
  retentionMs = 5_000,
) {
  const refreshes = new Map<string, Promise<T>>();

  return (refresh: string) => {
    const key = keyFor(refresh);
    const current = refreshes.get(key);
    if (current) {
      return current;
    }

    const pending = rotate(refresh);
    refreshes.set(key, pending);
    const cleanup = () => {
      setTimeout(() => refreshes.delete(key), retentionMs);
    };
    void pending.then(cleanup, cleanup);
    return pending;
  };
}
