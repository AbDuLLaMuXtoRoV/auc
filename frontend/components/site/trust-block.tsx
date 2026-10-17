import {
  ShieldCheckIcon,
  TimerIcon,
  PercentIcon,
  GavelIcon,
  type LucideIcon,
} from "lucide-react"

/**
 * Ishonch bloki — marketing shiorlarisiz, aniq faktlar bilan.
 * Faktlar loyihaning haqiqiy qoidalaridan (CLAUDE.md / docs).
 */
const FACTS: { icon: LucideIcon; title: string; text: string }[] = [
  {
    icon: ShieldCheckIcon,
    title: "Escrow himoyasi",
    text: "Toʻlov bloklanadi. Xaridor tovarni olib kodni tasdiqlagach sotuvchiga oʻtadi.",
  },
  {
    icon: TimerIcon,
    title: "Majburiy deadline",
    text: "Har mahsulot auksioni 3, 5 yoki 7 kunda tugaydi — narx muzlab qolmaydi.",
  },
  {
    icon: PercentIcon,
    title: "Xaridor komissiyasi 8%",
    text: "Gʻolib taklifga qoʻshiladi va narx yonida oldindan koʻrsatiladi.",
  },
  {
    icon: GavelIcon,
    title: "Anti-sniping",
    text: "Oxirgi 2 daqiqada taklif kelsa, tugash vaqti 2 daqiqaga uzayadi.",
  },
]

function TrustBlock() {
  return (
    <section
      aria-labelledby="ishonch-sarlavha"
      className="mx-auto max-w-6xl px-4 pt-12 sm:px-6"
    >
      <h2 id="ishonch-sarlavha" className="sr-only">
        Nega Bazart
      </h2>
      <div className="grid gap-4 rounded-xl border border-border bg-card p-4 sm:p-6 md:grid-cols-4">
        {FACTS.map((f) => {
          const Icon = f.icon
          return (
            <div key={f.title} className="grid gap-2">
              <span className="grid size-9 place-items-center rounded-lg bg-muted text-foreground">
                <Icon className="size-5" aria-hidden="true" />
              </span>
              <h3 className="text-sm font-semibold text-foreground">
                {f.title}
              </h3>
              <p className="text-sm text-muted-foreground">{f.text}</p>
            </div>
          )
        })}
      </div>
    </section>
  )
}

export { TrustBlock }
