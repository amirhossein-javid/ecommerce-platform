type BrandLogoProps = {
  inverse?: boolean;
  compact?: boolean;
};

export function BrandMark({ className = "size-12" }: { className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 64 64" fill="none" className={className}>
      <path d="m32 3 8 5 9-1 5 8 7 5-2 9 2 9-7 5-5 8-9-1-8 5-8-5-9 1-5-8-7-5 2-9-2-9 7-5 5-8 9 1 8-5Z" fill="#E6C98A" />
      <path d="M32 9a23 23 0 1 0 0 46 23 23 0 0 0 0-46Z" fill="#173D5E" />
      <path d="M17 43V29c0-8.3 6.7-15 15-15s15 6.7 15 15v14h-7V30a8 8 0 0 0-16 0v13h-7Z" fill="#FFFDF8" />
      <path d="M32 17c5.2 0 9.7 3 11.8 7.4A15 15 0 0 0 19 35.7V43h5V30a8 8 0 0 1 8-8V17Z" fill="#0E8A86" />
      <path d="m32 25 2.1 4.9 5.2.4-4 3.4 1.2 5.1-4.5-2.7-4.5 2.7 1.2-5.1-4-3.4 5.2-.4L32 25Z" fill="#E6C98A" />
    </svg>
  );
}

export function BrandLogo({ inverse = false, compact = false }: BrandLogoProps) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <BrandMark className="size-11 shrink-0 sm:size-12" />
      {!compact ? (
        <span className="flex flex-col leading-none">
          <span className={`text-lg font-black tracking-tight sm:text-xl ${inverse ? "text-gold-light" : "text-primary"}`}>نقش‌جهان</span>
          <span className={`mt-1.5 hidden text-[0.56rem] font-bold tracking-[0.24em] sm:block ${inverse ? "text-white/55" : "text-muted-foreground"}`} dir="ltr">NAGHSH-E JAHAN</span>
        </span>
      ) : null}
    </span>
  );
}
