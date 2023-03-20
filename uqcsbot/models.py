from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, BigInteger, Boolean, Integer

Base = declarative_base()

class Channel(Base):
    __tablename__ = 'channels'

    id = Column("id", BigInteger, primary_key=True, nullable=False)
    name = Column("name", String, nullable=False)
    joinable = Column("joinable", Boolean)
    emoji = Column("emoji", String, nullable=False)

    def __repr__(self):
        return f"Channel({self.id}, {self.name}, {self.joinable}, {self.emoji})"

class Message(Base):
    __tablename__= 'messages'

    id = Column("id", BigInteger, primary_key=True, nullable=False)
    type = Column("type", String, nullable=False)

class AOCWinner(Base):
    __tablename__ = 'aoc_winner'

    id = Column("id", BigInteger, primary_key=True, nullable=False)
    aoc_userid = Column("aoc_userid", Integer, nullable=False)
    year = Column("year", Integer, nullable=False)

class Starboard(Base):
    __tablename__ = 'starboard'

    recv = Column("recv", BigInteger, primary_key=True, nullable=False)
    recv_location = Column("recv_location", BigInteger, nullable=True, unique=False)
    sent = Column("sent", BigInteger, nullable=True, unique=True)