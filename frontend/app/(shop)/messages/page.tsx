import { ConversationsView } from "@/components/message/conversations-view"

export const metadata = {
  title: "Xabarlar — Bazart",
}

export default function MessagesPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
      <ConversationsView />
    </div>
  )
}
