"use client"

import * as React from "react"
import { useRouter, usePathname } from "next/navigation"
import { MessageSquarePlusIcon } from "lucide-react"
import { toast } from "sonner"

import { ApiError } from "@/lib/api/client"
import { useAuthStore } from "@/lib/store/auth"
import { listConversations, startConversation } from "@/lib/api/messages"
import { Button } from "@/components/ui/button"

/**
 * "Yozish" tugmasi — lot sahifasidan sotuvchi bilan suhbat boshlash uchun.
 *
 * Backend har POST'da YANGI suhbat yaratadi (dedup yo'q) — shuning uchun
 * avval mavjud suhbatni izlaymiz: shu item bo'yicha joriy foydalanuvchi
 * xaridor bo'lgan suhbat topilsa, o'shanga o'tamiz; aks holda yangi ochamiz.
 * Auth bo'lmasa — /login ga yo'naltiramiz.
 */
function MessageSellerButton({
  itemId,
  sellerId,
  className,
}: {
  itemId: number
  sellerId: number
  className?: string
}) {
  const router = useRouter()
  const pathname = usePathname()
  const authStatus = useAuthStore((s) => s.status)
  const userId = useAuthStore((s) => s.user?.id ?? null)

  const [busy, setBusy] = React.useState(false)

  // Sotuvchi o'z lotiga yoza olmaydi (backend ham 400 qaytaradi).
  const isOwnItem = userId != null && userId === sellerId

  function handleClick() {
    if (busy) return
    if (authStatus !== "authenticated") {
      router.push(`/login?next=${encodeURIComponent(pathname)}`)
      return
    }
    setBusy(true)
    listConversations()
      .then((conversations) => {
        const existing = conversations.find(
          (c) => c.item_id === itemId && c.buyer_id === userId
        )
        if (existing) return existing
        return startConversation(itemId, sellerId)
      })
      .then((conv) => {
        router.push(`/messages/${conv.id}`)
      })
      .catch((e) => {
        toast.error(
          e instanceof ApiError ? e.detail : "Suhbatni boshlab boʻlmadi."
        )
        setBusy(false)
      })
  }

  if (isOwnItem) return null

  return (
    <Button
      type="button"
      variant="outline"
      loading={busy}
      onClick={handleClick}
      className={className}
    >
      {!busy && <MessageSquarePlusIcon aria-hidden="true" />}
      Yozish
    </Button>
  )
}

export { MessageSellerButton }
