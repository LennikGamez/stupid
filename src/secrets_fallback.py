from sqlalchemy.orm import Mapped, mapped_column

from database import DataBase

class SecretsFallback(DataBase):
    __tablename__ = "secrets_fallback"

    id: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column()