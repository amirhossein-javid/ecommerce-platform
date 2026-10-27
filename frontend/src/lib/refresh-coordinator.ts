export function createRefreshCoordinator<T, Context = undefined>(
  rotate: (refresh: string, context: Context) => Promise<T>,
  keyFor: (refresh: string, context: Context) => string,
  retentionMs = 5_000,
) {
  const refreshes = new Map<string, Promise<T>>();

  return (refresh: string, context: Context) => {
    const key = keyFor(refresh, context);
    const current = refreshes.get(key);
    if (current) {
      return current;
    }

    const pending = rotate(refresh, context);
    refreshes.set(key, pending);
    const cleanup = () => {
      setTimeout(() => refreshes.delete(key), retentionMs);
    };
    void pending.then(cleanup, cleanup);
    return pending;
  };
}
