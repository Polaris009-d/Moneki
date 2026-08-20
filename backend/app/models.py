"""SQLAlchemy 数据模型（与 init_db.py 建库保持一致）。"""
from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Store(Base):
    __tablename__ = "stores"

    store_id: Mapped[str] = mapped_column(String, primary_key=True)
    store_name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    district: Mapped[str] = mapped_column(String)


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String, primary_key=True)
    product_name: Mapped[str] = mapped_column(String)
    product_category: Mapped[str] = mapped_column(String)
    unit_price: Mapped[float] = mapped_column(Float)


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String, index=True)
    date: Mapped[str] = mapped_column(String, index=True)
    store_id: Mapped[str] = mapped_column(String, index=True)
    product_id: Mapped[str] = mapped_column(String, index=True)
    qty: Mapped[float] = mapped_column(Float)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    payment: Mapped[str] = mapped_column(String)
