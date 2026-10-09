import { getCurrentCustomer } from "@/lib/auth-session";
import { privateAuthJson } from "@/lib/auth-route";

export async function GET() {
  const customer = await getCurrentCustomer();
  return privateAuthJson({ authenticated: customer !== null, customer });
}
