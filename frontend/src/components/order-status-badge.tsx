import type { OrderStatus } from "@/lib/checkout-contract";
import { ORDER_STATUS_LABELS, orderStatusTone } from "@/lib/order-policy";

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  const tone = orderStatusTone(status);
  const classes =
    tone === "success"
      ? "bg-success-soft text-success"
      : tone === "destructive"
        ? "bg-destructive-soft text-destructive"
        : "bg-primary-soft text-primary";
  return <span className={`inline-flex rounded-full px-3 py-1 text-xs font-extrabold ${classes}`}>{ORDER_STATUS_LABELS[status]}</span>;
}

