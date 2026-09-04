from pydantic import BaseModel


class NonceRequest(BaseModel):
    address: str


class NonceResponse(BaseModel):
    address: str
    message: str


class VerifyRequest(BaseModel):
    address: str
    signature: str


class SessionResponse(BaseModel):
    address: str
    token: str
