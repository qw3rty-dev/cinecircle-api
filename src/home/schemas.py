from pydantic import BaseModel


class HomeResponse(BaseModel):
    name: str
    version: str
    description: str
    status: str
    documentation: str
