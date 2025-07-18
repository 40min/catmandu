from pydantic import BaseModel


class Settings(BaseModel):
    cattackles_dir: str = "cattackles"
