from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, Integer, String, Time

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
    __tablename__ = 'messages'

    id = Column("id", BigInteger, primary_key=True, nullable=False)
    type = Column("type", String, nullable=False)

class AOCWinner(Base):
    __tablename__ = 'aoc_winner'

    id = Column("id", BigInteger, primary_key=True, nullable=False)
    aoc_userid = Column("aoc_userid", Integer, nullable=False)
    year = Column("year", Integer, nullable=False)


class Reminders(Base):
    __tablename__ = 'reminders'

    id = Column("id", BigInteger, primary_key=True, nullable=False)
    user_id = Column("user_id", Integer, nullable=False)
    channel_id = Column("channel_id", Integer, nullable=True)
    time_created = Column("time_created", DateTime, nullable=False)
    message = Column("message", String, nullable=False)
    time = Column("time", Time, nullable=False)
    start_date = Column("start_date", Date, nullable=False)
    end_date = Column("end_date", Date, nullable=True)
    week_frequency = Column("week_frequency", Integer, nullable=True)
