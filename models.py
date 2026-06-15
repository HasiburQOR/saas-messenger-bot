from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

from database import engine

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    # Relationships link this user to their page and products
    fb_page = relationship("FacebookPage", back_populates="user", uselist=False)
    products = relationship("Product", back_populates="user")


class FacebookPage(Base):
    __tablename__ = "facebook_pages"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    page_id = Column(String, unique=True, index=True)
    page_access_token = Column(Text)
    user = relationship("User", back_populates="fb_page")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    description = Column(Text)
    price = Column(String)
    user = relationship("User", back_populates="products")


# This line automatically creates the tables in PostgreSQL if they don't exist yet
Base.metadata.create_all(bind=engine)
