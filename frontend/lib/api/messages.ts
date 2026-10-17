/**
 * Xabarlar (xaridor ↔ sotuvchi) API moduli.
 *
 * Turlarni shu yerda lokal e'lon qilamiz — backend Pydantic sxemalariga
 * (`app/schemas/message.py`) aniq mos:
 *   - ConversationRead: id, buyer_id, seller_id, item_id, created_at, updated_at
 *   - MessageRead: id, conversation_id, sender_id, body, is_read, created_at
 *   - ConversationDetailRead = ConversationRead + messages: MessageRead[]
 */
import { apiFetch } from "@/lib/api/client"

export interface Conversation {
  id: number
  buyer_id: number
  seller_id: number
  /** item o'chirilgan bo'lsa null bo'lishi mumkin. */
  item_id: number | null
  created_at: string
  updated_at: string
}

export interface Message {
  id: number
  conversation_id: number
  sender_id: number
  body: string
  is_read: boolean
  created_at: string
}

export interface ConversationDetail extends Conversation {
  messages: Message[]
}

/**
 * Suhbat boshlash. Backend `ConversationCreate` — item_id majburiy,
 * seller_id ixtiyoriy (berilmasa item egasidan olinadi). Joriy foydalanuvchi
 * xaridor sifatida yoziladi; u item egasi bo'lsa backend 400 qaytaradi.
 */
export function startConversation(
  itemId: number,
  sellerId?: number
): Promise<Conversation> {
  return apiFetch<Conversation>("/messages/conversations", {
    body: { item_id: itemId, ...(sellerId != null ? { seller_id: sellerId } : {}) },
  })
}

/** Joriy foydalanuvchining barcha suhbatlari (xaridor yoki sotuvchi sifatida). */
export function listConversations(): Promise<Conversation[]> {
  return apiFetch<Conversation[]>("/messages/conversations")
}

/** Bitta suhbat — xabarlari bilan (ConversationDetailRead). */
export function getConversation(conversationId: number): Promise<ConversationDetail> {
  return apiFetch<ConversationDetail>(`/messages/conversations/${conversationId}`)
}

/** Suhbatga xabar yuborish. Backend `MessageCreate.body` — 1..5000 belgi. */
export function sendMessage(conversationId: number, body: string): Promise<Message> {
  return apiFetch<Message>(`/messages/conversations/${conversationId}/messages`, {
    body: { body },
  })
}

/**
 * Boshqa tomon xabarini o'qilgan deb belgilash. Backend o'z xabaringizni
 * o'qilgan deb belgilashga yo'l qo'ymaydi (400).
 */
export function markMessageRead(messageId: number): Promise<Message> {
  return apiFetch<Message>(`/messages/messages/${messageId}/read`, { method: "PATCH" })
}
