import {
  createOwnProductReview,
  deleteOwnProductReview,
  fetchOwnProductReview,
} from "@/lib/review-api";
import { normalizeReviewSlug, parseReviewInput } from "@/lib/review-contract";
import { reviewResponse, reviewRouteError } from "@/lib/review-route";
import { withAuthenticatedSession } from "@/lib/authenticated-request";
import {
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";

type RouteContext = { params: Promise<{ slug: string }> };

async function getSlug(context: RouteContext) {
  return normalizeReviewSlug((await context.params).slug);
}

export async function GET(_request: Request, context: RouteContext) {
  const slug = await getSlug(context);
  if (!slug) return reviewResponse({ error: "شناسهٔ محصول معتبر نیست." }, undefined, 404);
  try {
    const result = await withAuthenticatedSession((access) =>
      fetchOwnProductReview(access, slug),
    );
    return reviewResponse({ review: result.value }, result.rotatedTokens);
  } catch (error) {
    return reviewRouteError(error, "get");
  }
}

export async function POST(request: Request, context: RouteContext) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return reviewResponse({ error: "درخواست غیرمجاز است." }, undefined, 403);
  }
  if (!hasJsonContentType(request.headers)) {
    return reviewResponse({ error: "اطلاعات نظر معتبر نیست." }, undefined, 400);
  }
  const slug = await getSlug(context);
  if (!slug) return reviewResponse({ error: "شناسهٔ محصول معتبر نیست." }, undefined, 404);

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return reviewResponse({ error: "اطلاعات نظر معتبر نیست." }, undefined, 400);
  }
  const input = parseReviewInput(payload);
  if (!input) {
    return reviewResponse(
      { error: "امتیاز و متن نظر را کامل و صحیح وارد کنید." },
      undefined,
      400,
    );
  }
  try {
    const result = await withAuthenticatedSession((access) =>
      createOwnProductReview(access, slug, input),
    );
    return reviewResponse({ review: result.value }, result.rotatedTokens, 201);
  } catch (error) {
    return reviewRouteError(error, "create");
  }
}

export async function DELETE(request: Request, context: RouteContext) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return reviewResponse({ error: "درخواست غیرمجاز است." }, undefined, 403);
  }
  const slug = await getSlug(context);
  if (!slug) return reviewResponse({ error: "شناسهٔ محصول معتبر نیست." }, undefined, 404);
  try {
    const result = await withAuthenticatedSession((access) =>
      deleteOwnProductReview(access, slug),
    );
    return reviewResponse({ deleted: true }, result.rotatedTokens);
  } catch (error) {
    return reviewRouteError(error, "delete");
  }
}
