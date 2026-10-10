import { Container } from "@/components/container";

export default function ReviewManagementLoading() {
  return (
    <Container className="py-8">
      <div role="status" className="animate-pulse rounded-[1.5rem] border border-gold/35 bg-surface p-10 text-center text-sm text-muted-foreground shadow-card">
        در حال آماده‌سازی مدیریت نظرها…
      </div>
    </Container>
  );
}
