/**
 * Backend (FastAPI) sxemalariga mos TypeScript turlari.
 * MUHIM: pul maydonlari — TIYIN, JSON'da STRING ("6200050" = 62 000.50 so'm).
 * Formatlash: lib/format.ts -> formatTiyin().
 */

export type ItemCondition = "new" | "used" | "refurbished";

export type ItemStatus =
  | "draft"
  | "scheduled"
  | "pending"
  | "active"
  | "sold"
  | "cancelled";

export type AuctionStatus =
  | "scheduled"
  | "active"
  | "ended"
  | "cancelled"
  | "reserve_not_met";

export type BidStatus =
  | "valid"
  | "outbid"
  | "cancelled"
  /** Foydalanuvchi o'zi qaytarib oldi. */
  | "retracted"
  /** Admin bekor qildi (shill/firibgarlik). */
  | "invalidated";

export type UserRole = "user" | "seller" | "admin" | "superadmin";

export type OrderStatus =
  | "pending_payment"
  | "paid"
  | "pickup_pending"
  | "completed"
  | "cancelled";

export type PaymentStatus =
  | "pending"
  | "processing"
  | "paid"
  | "failed"
  | "refunded"
  | "held"
  | "released"
  | "cancelled_hold";

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  phone: string | null;
  bio: string | null;
  avatar_url: string | null;
  location: string | null;
  seller_rating: number;
  seller_rating_count: number;
  is_active: boolean;
  is_verified: boolean;
  role: UserRole;
  created_at: string;
  updated_at: string;
}

/** GET /users/me — faqat egaga qaytadigan kengaytirilgan profil (UserMeRead). */
export interface UserMe extends User {
  telegram_chat_id: string | null;
  preferred_language: "uz" | "ru";
  /** Telefon OTP bilan tasdiqlangan vaqt (null = tasdiqlanmagan). */
  phone_verified_at: string | null;
}

export interface Category {
  id: number;
  parent_id: number | null;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ItemImage {
  id: number;
  item_id: number;
  image_url: string;
  is_primary: boolean;
  created_at: string;
}

export interface Item {
  id: number;
  seller_id: number;
  title: string;
  description: string | null;
  category_id: number | null;
  images: string[];
  condition: ItemCondition;
  status: ItemStatus;
  location: string | null;
  item_location: string | null;
  year: number | null;
  equipment: string | null;
  defects: string | null;
  video_url: string | null;
  region_id: number | null;
  district_id: number | null;
  view_count: number;
  published_at: string | null;
  /** tiyin (string) */
  starting_price: string;
  /** Rezerv narx BORLIGI. Qiymatning o'zi javobda hech qachon kelmaydi. */
  has_reserve: boolean;
  item_images: ItemImage[];
  created_at: string;
  updated_at: string;
}

export interface Auction {
  id: number;
  item_id: number;
  seller_id: number;
  start_time: string;
  end_time: string;
  duration_days: number | null;
  status: AuctionStatus;
  /** tiyin (string) */
  starting_price: string;
  /** tiyin (string) — joriy narx */
  current_price: string;
  /** tiyin (string) — minimal qadam */
  minimum_bid_increment: string;
  /** tiyin (string) — server qabul qiladigan eng kichik keyingi taklif (qadam jadvali hisobga olingan). */
  minimum_next_bid: string;
  /** Rezerv narx BORLIGI. Qiymatning o'zi javobda hech qachon kelmaydi. */
  has_reserve: boolean;
  /** Rezerv qoplanganmi; rezerv yo'q bo'lsa null. */
  reserve_met: boolean | null;
  bid_count: number;
  unique_bidder_count: number;
  highest_bidder_id: number | null;
  winner_id: number | null;
  winning_bid_id: number | null;
  /** Anti-sniping uzaytirishdan oldingi tugash vaqti. */
  original_end_time: string | null;
  closed_at: string | null;
  /** RESERVE_NOT_MET bo'lganda sotuvchining "eng yuqori taklifga sotish" muddati. */
  second_chance_expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Bid {
  id: number;
  auction_id: number;
  bidder_id: number;
  /** tiyin (string) */
  amount: string;
  status: BidStatus;
  created_at: string;
  /** Maskalangan ism ("A***v") — bid tarixida to'liq ism ko'rsatilmaydi. */
  bidder_display: string;
  /** Faqat POST javobida: taklif joriy narxdan bir necha barobar yuqori (xato bo'lishi mumkin). */
  high_bid_warning: boolean;
}

export interface Order {
  id: number;
  auction_id: number;
  item_id: number;
  buyer_id: number;
  seller_id: number;
  /** tiyin (string) */
  final_price: string;
  status: OrderStatus;
  created_at: string;
  updated_at: string;
}

export interface AuthToken {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

/** Frontend tushunchasi: LOT = auksion + uning tovari (item). */
export interface Lot {
  auction: Auction;
  item: Item;
}

/** Admin panel statistikasi (GET /admin/statistics). total_sales_amount — tiyin (string). */
export interface AdminStats {
  total_users: number;
  total_active_auctions: number;
  total_completed_orders: number;
  /** tiyin (string) */
  total_sales_amount: string;
}
