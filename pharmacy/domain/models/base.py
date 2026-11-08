"""Shared SQLAlchemy declarative base for all supported database engines."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Common metadata registry used to create schema on any SQLAlchemy backend."""

