from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, BigInteger, Boolean

Base = declarative_base()

class Channel(Base):
    __tablename__ = 'channels'

    id = Column("id", BigInteger, primary_key=True, nullable=False)
    name = Column("name", String, nullable=False)
    joinable = Column("joinable", Boolean)

    def __repr__(self):
        return f"Channel({self.id}, {self.name}, {self.joinable})"
