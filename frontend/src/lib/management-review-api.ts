import "server-only";

import {
  isManagedReview,
  isManagedReviewPage,
  isStoreReply,
  type ManagedReview,
  type ManagedReviewPage,
  type ManagedReviewStatus,
  type StoreReply,
} from "@/lib/management-review-contract";

const MANAGEMENT_PATH = "/api/v1/management/reviews/";

export class ManagementReviewApiError extends Error {
  constructor(
    public readonly status?: number,
    public readonly payload?: unknown,
  ) {
    super("The review management API request failed.");
    this.name = "ManagementReviewApiError";
  }
}

function getApiOrigin() {
  const value = process.env.DJANGO_API_URL;
  if (!value) throw new ManagementReviewApiError();
  try {
    return new URL(value);
  } catch {
    throw new ManagementReviewApiError();
  }
}

async function parsePayload(response: Response) {
  try {
    return (await response.json()) as unknown;
  } catch {
    return undefined;
  }
}

async function requestManagement(path: string, access: string, init: RequestInit) {
  let response: Response;
  try {
    response = await fetch(new URL(path, getApiOrigin()), {
      ...init,
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${access}`,
        ...init.headers,
      },
      cache: "no-store",
    });
  } catch {
    throw new ManagementReviewApiError();
  }
  if (!response.ok) {
    throw new ManagementReviewApiError(response.status, await parsePayload(response));
  }
  return response;
}

export async function fetchManagedReviews(
  access: string,
  query = "",
): Promise<ManagedReviewPage> {
  const response = await requestManagement(`${MANAGEMENT_PATH}${query}`, access, {
    method: "GET",
  });
  const payload = await parsePayload(response);
  if (!isManagedReviewPage(payload)) throw new ManagementReviewApiError();
  return payload;
}

export async function moderateManagedReview(
  access: string,
  id: number,
  reviewStatus: Extract<ManagedReviewStatus, "APPROVED" | "REJECTED">,
): Promise<ManagedReview> {
  const response = await requestManagement(
    `${MANAGEMENT_PATH}${id}/moderate/`,
    access,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: reviewStatus }),
    },
  );
  const payload = await parsePayload(response);
  if (!isManagedReview(payload)) throw new ManagementReviewApiError();
  return payload;
}

export async function saveManagedReply(
  access: string,
  id: number,
  comment: string,
  exists: boolean,
): Promise<StoreReply> {
  const response = await requestManagement(`${MANAGEMENT_PATH}${id}/reply/`, access, {
    method: exists ? "PATCH" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comment }),
  });
  const payload = await parsePayload(response);
  if (!isStoreReply(payload)) throw new ManagementReviewApiError();
  return payload;
}

export async function deleteManagedReply(access: string, id: number) {
  await requestManagement(`${MANAGEMENT_PATH}${id}/reply/`, access, {
    method: "DELETE",
  });
}
