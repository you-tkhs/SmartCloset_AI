from pydantic import BaseModel


class UploadAcceptedResponse(BaseModel):
    item_id: str
    status: str
    failure_reason: str | None = None


class ItemStatusResponse(BaseModel):
    item_id: str
    status: str
    failure_reason: str | None = None
