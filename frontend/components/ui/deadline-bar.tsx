"use client"

import * as React from "react"
import { TimerIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { Progress } from "@/components/ui/progress"

/**
 * "Muddat chizigʻi" — platformaning imzo elementi.
 *
 * Har auksion lotning rasm chetiga dokланadigan jonli countdown + o'lchagich.
 * Deadline yaqinlashgani sari kuchayadi: neytral -> amber -> qizil.
 * Faqat raqam yangilanadi (CSS animatsiya yo'q) — prefers-reduced-motion'ga mos.
 */

function pad(n: number): string {
  return n.toString().padStart(2, "0");
}

function format(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const mins = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (days >= 1) return `${days} kun ${pad(hours)}:${pad(mins)}`;
  return `${pad(hours)}:${pad(mins)}:${pad(secs)}`;
}

type Tone = {
  text: string;
  /** `Progress` indikatorining rangi — root'dan data-slot orqali beriladi. */
  fill: string;
};

function toneFor(minutesLeft: number): Tone {
  if (minutesLeft <= 30)
    return {
      text: "text-destructive",
      fill: "[&_[data-slot=progress-indicator]]:bg-destructive",
    };
  if (minutesLeft <= 360)
    return {
      text: "text-warning",
      fill: "[&_[data-slot=progress-indicator]]:bg-warning",
    };
  return {
    text: "text-muted-foreground",
    fill: "[&_[data-slot=progress-indicator]]:bg-muted-foreground",
  };
}

function DeadlineBar({
  endsAt,
  endsInMinutes,
  windowMinutes = 4320,
  inline = false,
  className,
}: {
  /** Haqiqiy tugash vaqti (ISO/Date) — backend auction.end_time. */
  endsAt?: string | number | Date;
  /** Muqobil: mount'dan boshlab qolgan daqiqa (namuna ma'lumot uchun). */
  endsInMinutes?: number;
  windowMinutes?: number;
  /** true — chip ko'rinishida (rasm chetiga emas). */
  inline?: boolean;
  className?: string;
}) {
  // Boshlang'ich qiymat deterministik (Date.now yo'q) — birinchi render xavfsiz.
  const [remaining, setRemaining] = React.useState(
    (endsInMinutes ?? windowMinutes) * 60_000
  );

  React.useEffect(() => {
    const end =
      endsAt != null
        ? new Date(endsAt).getTime()
        : Date.now() + (endsInMinutes ?? 0) * 60_000;
    const tick = () => setRemaining(Math.max(0, end - Date.now()));
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [endsAt, endsInMinutes]);

  const minutesLeft = remaining / 60_000;
  const tone = toneFor(minutesLeft);
  const pct = Math.max(
    0,
    Math.min(100, (remaining / (windowMinutes * 60_000)) * 100)
  );
  const ended = remaining <= 0;

  if (inline) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1 text-sm font-medium tabular-nums",
          tone.text,
          className
        )}
      >
        <TimerIcon className="size-4" aria-hidden="true" />
        {ended ? "Tugadi" : `${format(remaining)} qoldi`}
      </span>
    );
  }

  return (
    <div className={cn("absolute inset-x-0 bottom-0", className)}>
      {/* O'lchagich chizig'i — `ui/progress` (vengeanceui) ustida. */}
      <Progress
        value={pct}
        aria-label="Auksion muddati"
        className={cn("h-1 rounded-none bg-background/60", tone.fill)}
      />
      {/* Countdown matni. */}
      <div className="flex items-center gap-1 bg-background/85 px-2 py-1">
        <TimerIcon className={cn("size-3", tone.text)} aria-hidden="true" />
        <span className={cn("text-xs font-medium tabular-nums", tone.text)}>
          {ended ? "Tugadi" : format(remaining)}
        </span>
      </div>
    </div>
  );
}

export { DeadlineBar };
