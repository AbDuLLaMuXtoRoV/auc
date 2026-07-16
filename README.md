# Bazart API

FastAPI backend scaffold for a combined marketplace and auction platform inspired by
OfferUp and BidFTA. It uses Python 3.12+, SQLAlchemy 2.x, Alembic, PostgreSQL,
Pydantic v2, JWT authentication, bcrypt password hashing, pydantic-settings,
Uvicorn, Docker Compose, pytest, and Ruff.

The current implementation is intentionally an initial backend skeleton, not the full
production product. It includes clean module boundaries for authentication, roles,
user profiles, seller reputation fields, categories, listings, auctions, bids,
payments, orders, messaging, and admin views so future production work can grow from
stable foundations.

## Current modules

- Auth: registration, login, JWT access tokens, password hashing, current-user dependency, role helpers.
- Auth now includes refresh tokens, logout, password reset skeletons, and email verification skeletons.
- Users: profile fields, contact/location fields, seller reputation, active/verified/role flags.
- Categories: parent-child category tree.
- Listings/items: full CRUD-style operations, filters, owner/admin management, images, condition, category, reserve price, and status lifecycle fields.
- Auctions: auction creation, bid increment/reserve fields, winner fields, close/settlement service skeleton.
- Bids: bid creation through a service layer prepared for max bid/proxy bidding.
- Payments: payment method and payment transaction skeleton with mock provider abstraction; no real gateway integration yet.
- Orders: transaction records are created when a winning auction closes, with buyer/seller/admin views and status management.
- Messaging: buyer-seller conversations, message replies, participant-only access, and read state.
- Admin: admin-only moderation for users, items, auctions, bids, orders, and platform statistics.

## Initial auction rules

- Auctions can only be created for `draft` or `scheduled` items.
- Auctions created for a future `start_time` are `scheduled`.
- Scheduled auctions become `active` when `start_time` is reached and a bid is placed.
- Bids are accepted only while an auction is `active`.
- Bids are rejected after `end_time`.
- Bid amount must be at least `current_price + minimum_bid_increment`.
- Sellers cannot bid on their own auctions.
- The same user can bid multiple times, but each bid must still satisfy the increment rule.
- Each valid bid updates `current_price`, `winning_bid_id`, and `highest_bidder_id`.
- `close_auction` resolves the highest valid bidder and sets `winner_id`.
- If a reserve price exists and the highest bid is below it, the auction becomes `reserve_not_met`.
- Soft close is configured with `SOFT_CLOSE_WINDOW_SECONDS` and `SOFT_CLOSE_EXTENSION_SECONDS`.

## Project structure

```text
app/
  main.py
  core/
    config.py
    security.py
    dependencies.py
  db/
    session.py
    base.py
  models/
  schemas/
  api/
    v1/
      router.py
      endpoints/
  services/
  repositories/
tests/
  conftest.py
  test_admin.py
  test_auth.py
  test_auctions.py
  test_bids.py
  test_items.py
  test_messages.py
  test_orders.py
  test_payments.py
  test_users.py
  test_validation.py
```

## Included project files

- `pyproject.toml`: package metadata, dependencies, pytest config, and Ruff config.
- `.env.example`: local environment variable template.
- `Dockerfile`: FastAPI application container.
- `docker-compose.yml`: PostgreSQL and API services.
- `alembic.ini`: Alembic configuration.
- `alembic/env.py`: Alembic metadata wiring for SQLAlchemy models.
- `README.md`: setup and development instructions.

## Current API areas

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/forgot-password`
- `POST /api/v1/auth/reset-password`
- `POST /api/v1/auth/verification-token`
- `POST /api/v1/auth/verify-email`
- `GET /api/v1/auth/me`
- `GET /api/v1/users/me`
- `PATCH /api/v1/users/me`
- `POST /api/v1/categories`
- `GET /api/v1/categories`
- `POST /api/v1/items`
- `GET /api/v1/items`
- `GET /api/v1/items/{item_id}`
- `PATCH /api/v1/items/{item_id}`
- `DELETE /api/v1/items/{item_id}`
- `POST /api/v1/items/{item_id}/images`
- `POST /api/v1/auctions`
- `GET /api/v1/auctions`
- `GET /api/v1/auctions/{auction_id}`
- `PATCH /api/v1/auctions/{auction_id}/status`
- `POST /api/v1/auctions/{auction_id}/close`
- `POST /api/v1/auctions/{auction_id}/bids`
- `POST /api/v1/bids/{auction_id}`
- `POST /api/v1/payments/methods`
- `GET /api/v1/payments/methods`
- `POST /api/v1/payments/intents`
- `POST /api/v1/payments/{payment_id}/confirm-mock`
- `GET /api/v1/payments/orders/{order_id}`
- `GET /api/v1/orders/buyer`
- `GET /api/v1/orders/seller`
- `GET /api/v1/orders/admin`
- `GET /api/v1/orders/{order_id}`
- `PATCH /api/v1/orders/{order_id}/status`
- `POST /api/v1/messages/conversations`
- `GET /api/v1/messages/conversations`
- `GET /api/v1/messages/conversations/{conversation_id}`
- `POST /api/v1/messages/conversations/{conversation_id}/messages`
- `PATCH /api/v1/messages/messages/{message_id}/read`
- `GET /api/v1/admin/users`
- `POST /api/v1/admin/users/{user_id}/block`
- `POST /api/v1/admin/users/{user_id}/unblock`
- `PATCH /api/v1/admin/users/{user_id}/role`
- `GET /api/v1/admin/items`
- `POST /api/v1/admin/items/{item_id}/approve`
- `POST /api/v1/admin/items/{item_id}/reject`
- `GET /api/v1/admin/listings`
- `GET /api/v1/admin/auctions`
- `POST /api/v1/admin/auctions/{auction_id}/cancel`
- `GET /api/v1/admin/bids`
- `GET /api/v1/admin/orders`
- `GET /api/v1/admin/statistics`

## Admin

All admin endpoints use the `current_admin_user` dependency. List endpoints include pagination
with `skip` and `limit`, plus starter search/filter parameters such as `search`, `status`,
`role`, `seller_id`, `buyer_id`, `auction_id`, and `bidder_id` where relevant.

The statistics endpoint currently returns:

- `total_users`
- `total_active_auctions`
- `total_completed_orders`
- `total_sales_amount`

## Items and image uploads

List items with optional filters:

```bash
GET /api/v1/items?category_id=1&seller_id=2&status=draft&location=tashkent
```

`location` is a starter text-match filter. TODO: replace it with geo-distance search.

Delete uses a safe starter behavior: items are marked `cancelled` instead of being physically removed.
Only the item owner can update, cancel, or upload images for an item. Admin users can manage any item.

Upload an image:

```bash
POST /api/v1/items/{item_id}/images
Content-Type: multipart/form-data

file=<image file>
is_primary=true
```

Images are stored locally under `LOCAL_UPLOAD_DIR` and served from `PUBLIC_UPLOAD_URL_PREFIX`.
The storage logic is isolated in `StorageService` so it can later be replaced with S3 or another object store.

## Orders and transactions

When `close_auction` succeeds and `winner_id` exists, an order is created with:

- `auction_id`
- `item_id`
- `buyer_id`
- `seller_id`
- `final_price`
- `status`

Order statuses are `pending_payment`, `paid`, `pickup_pending`, `completed`, and `cancelled`.
Buyers can view their orders, sellers can view sales orders, and admins can view all orders.
Only an admin or the related seller can update order status.

## Payments

The payment module is gateway-ready but currently uses `MockPaymentProvider`.

Create a payment intent:

```bash
POST /api/v1/payments/intents
{
  "order_id": 1,
  "amount": "120.00",
  "currency": "UZS",
  "provider": "mock"
}
```

Confirm a mock payment:

```bash
POST /api/v1/payments/{payment_id}/confirm-mock
```

When a payment becomes `paid`, the related order status becomes `paid`.
Future providers such as Uzcard/Humo, Payme, Click, or another gateway should implement
`BasePaymentProvider` and be registered behind the provider selection function.

## Messaging

Buyers can start a conversation with the seller about an item:

```bash
POST /api/v1/messages/conversations
{
  "item_id": 1
}
```

Participants can list conversations, view conversation details with messages, send replies,
and mark received messages as read. Non-participants cannot view or send messages in a conversation.

## Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -e ".[dev]"
```

### 3. Set up the `.env` file

```bash
cp .env.example .env
```

For local development from your host machine, keep:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/bazart
```

Use a strong `SECRET_KEY` before deploying anywhere outside local development.

### 4. Start PostgreSQL with Docker Compose

```bash
docker compose up -d db
```

The database is exposed locally on port `5432`.

### 5. Run Alembic migrations

```bash
alembic upgrade head
```

To create a future migration after changing models:

```bash
alembic revision --autogenerate -m "describe change"
```

### 6. Start the FastAPI server with Uvicorn

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive docs are available at `http://localhost:8000/docs`.

## Docker API setup

To run both PostgreSQL and the API in Docker:

```bash
cp .env.example .env
docker compose up --build
docker compose exec api alembic upgrade head
```

## Useful commands

```bash
pytest
pytest tests/test_auth.py
pytest tests/test_validation.py
ruff check .
ruff format .
```

## Testing

Pytest is configured in `pyproject.toml`. The suite uses an in-memory SQLite test database
created in `tests/conftest.py`, with FastAPI's `get_db` dependency overridden for each test.

Shared test utilities include:

- `client`
- `db_session`
- `test_user`
- `test_seller`
- `test_admin`
- `register_user`
- `login_user`
- `auth_headers`
- `create_user`
- `create_item`
- `create_auction`
- `create_bid`

Run the full suite:

```bash
pytest
```

Run a focused module:

```bash
pytest tests/test_items.py
```
