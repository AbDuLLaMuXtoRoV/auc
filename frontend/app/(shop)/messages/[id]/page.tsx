import { notFound } from "next/navigation"

import { MessageThread } from "@/components/message/message-thread"

export default async function MessageThreadPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const conversationId = Number(id)
  if (!Number.isInteger(conversationId) || conversationId <= 0) notFound()

  return (
    <div className="mx-auto max-w-2xl px-4 py-6 sm:px-6">
      <MessageThread conversationId={conversationId} />
    </div>
  )
}
