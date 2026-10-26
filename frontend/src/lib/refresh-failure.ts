// Only a definitive rejection by the JWT endpoint invalidates a session.
// Other responses, including malformed success bodies, may follow rotation.
export class RefreshFailure extends Error {
  readonly status: 401 | 429 | 503;
  readonly retryAfter?: string;

  constructor(status?: number, retryAfter?: string | null) {
    super("Session refresh failed.");
    this.name = "RefreshFailure";
    this.status = status === 401 || status === 429 ? status : 503;
    if (
      this.status === 429 && retryAfter &&
      (/^\d+$/.test(retryAfter) ||
        (!Number.isNaN(Date.parse(retryAfter)) &&
          new Date(retryAfter).toUTCString() === retryAfter))
    ) {
      this.retryAfter = retryAfter;
    }
  }
}
