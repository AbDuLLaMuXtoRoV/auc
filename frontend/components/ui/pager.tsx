"use client"

import * as React from "react"

import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"

/**
 * Boshqariladigan sahifalash: joriy sahifa, umumiy sahifalar soni va
 * o'zgarish hodisasi. Chekka sahifalarda "oldingi/keyingi" o'chiriladi.
 */
function Pager({
  page,
  totalPages,
  onPageChange,
  className,
}: {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
  className?: string
}) {
  if (totalPages <= 1) return null

  const go = (target: number) => (e: React.MouseEvent) => {
    e.preventDefault()
    const next = Math.min(Math.max(target, 1), totalPages)
    if (next !== page) onPageChange(next)
  }

  // Sahifa raqamlari: birinchi, oxirgi, joriy ± 1, orasida ellipsis.
  const pages: (number | "ellipsis")[] = []
  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || Math.abs(i - page) <= 1) {
      pages.push(i)
    } else if (pages[pages.length - 1] !== "ellipsis") {
      pages.push("ellipsis")
    }
  }

  const atStart = page <= 1
  const atEnd = page >= totalPages

  return (
    <Pagination className={className}>
      <PaginationContent>
        <PaginationItem>
          <PaginationPrevious
            href="#"
            text="Oldingi"
            aria-disabled={atStart}
            tabIndex={atStart ? -1 : undefined}
            className={atStart ? "pointer-events-none opacity-50" : undefined}
            onClick={go(page - 1)}
          />
        </PaginationItem>

        {pages.map((p, i) =>
          p === "ellipsis" ? (
            <PaginationItem key={`e${i}`}>
              <PaginationEllipsis />
            </PaginationItem>
          ) : (
            <PaginationItem key={p}>
              <PaginationLink
                href="#"
                isActive={p === page}
                aria-label={`${p}-sahifa`}
                onClick={go(p)}
              >
                {p}
              </PaginationLink>
            </PaginationItem>
          )
        )}

        <PaginationItem>
          <PaginationNext
            href="#"
            text="Keyingi"
            aria-disabled={atEnd}
            tabIndex={atEnd ? -1 : undefined}
            className={atEnd ? "pointer-events-none opacity-50" : undefined}
            onClick={go(page + 1)}
          />
        </PaginationItem>
      </PaginationContent>
    </Pagination>
  )
}

export { Pager }
