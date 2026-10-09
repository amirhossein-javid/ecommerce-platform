export type LoginCartMergeState =
  | "none"
  | "merged"
  | "pending"
  | "unavailable"
  | "authentication-failure";

export type CartMergeDecision = {
  state: LoginCartMergeState;
  clearGuestCookie: boolean;
  establishSession: boolean;
};

export function successfulCartMerge(): CartMergeDecision {
  return {
    state: "merged",
    clearGuestCookie: true,
    establishSession: true,
  };
}

export function classifyCartMergeFailure(status?: number): CartMergeDecision {
  if (status === 404) {
    return {
      state: "unavailable",
      clearGuestCookie: true,
      establishSession: true,
    };
  }
  if (status === 401 || status === 403) {
    return {
      state: "authentication-failure",
      clearGuestCookie: false,
      establishSession: false,
    };
  }
  return {
    state: "pending",
    clearGuestCookie: false,
    establishSession: true,
  };
}
