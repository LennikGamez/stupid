from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import DataBase

class User(DataBase):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column()
    base_url: Mapped[str] = mapped_column()
    sync_dir: Mapped[str] = mapped_column()
