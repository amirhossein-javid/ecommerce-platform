import type { ReactNode } from "react";

type StorefrontPageHeaderProps = {
  eyebrow: string;
  title: ReactNode;
  description: string;
  trailing?: ReactNode;
};

export function StorefrontPageHeader({
  eyebrow,
  title,
  description,
  trailing,
}: StorefrontPageHeaderProps) {
  return (
    <header className="naghsh-pattern relative isolate mb-7 overflow-hidden rounded-[1.5rem] px-5 py-9 text-center text-white sm:mb-9 sm:px-10 sm:py-12">
      <div className="absolute inset-0 -z-10 bg-lapis-dark/82" />
      <p className="flex items-center justify-center gap-3 text-xs font-black text-gold-light sm:text-sm">
        <span className="size-2 rotate-45 bg-gold" aria-hidden="true" />
        {eyebrow}
        <span className="size-2 rotate-45 bg-gold" aria-hidden="true" />
      </p>
      <h1 className="mx-auto mt-3 max-w-4xl text-3xl font-black leading-[1.45] tracking-tight text-white sm:text-4xl">
        {title}
      </h1>
      <p className="mx-auto mt-3 max-w-2xl text-sm leading-7 text-white/72 sm:text-base sm:leading-8">
        {description}
      </p>
      {trailing ? <div className="mt-5 flex justify-center">{trailing}</div> : null}
    </header>
  );
}
