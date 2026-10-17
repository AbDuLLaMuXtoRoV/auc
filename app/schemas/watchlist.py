from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WatchlistCreate(BaseModel):
    auction_id: int


class WatchlistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    auction_id: int
    created_at: datetime
