from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Integer,
    String,
    Time,
)
from typing import Optional
from datetime import datetime


class Base(DeclarativeBase):
    pass


class AOCWinners(Base):
    __tablename__ = "aoc_winners"

    id: Mapped[int] = mapped_column(
        "id", Integer, primary_key=True, nullable=False, autoincrement=True
    )
    aoc_userid: Mapped[int] = mapped_column("aoc_userid", Integer, nullable=False)
    year: Mapped[int] = mapped_column("year", Integer, nullable=False)
    prize: Mapped[str] = mapped_column("prize", String, nullable=True)


class AOCRegistrations(Base):
    __tablename__ = "aoc_registrations"

    id: Mapped[int] = mapped_column(
        "id", Integer, primary_key=True, nullable=False, autoincrement=True
    )
    aoc_userid: Mapped[int] = mapped_column("aoc_userid", Integer, nullable=False)
    year: Mapped[int] = mapped_column("year", Integer, nullable=False)
    discord_userid: Mapped[int] = mapped_column(
        "discord_userid", BigInteger, nullable=False
    )


class MCWhitelist(Base):
    __tablename__ = "mc_whitelisted"

    mc_username: Mapped[str] = mapped_column(
        "mcuser", String, primary_key=True, nullable=False
    )
    discord_id: Mapped[str] = mapped_column("discordid", BigInteger, nullable=False)
    admin_whitelisted: Mapped[bool] = mapped_column("adminwl", Boolean)
    added_dt: Mapped[datetime] = mapped_column("added_dt", DateTime, nullable=False)


class Reminders(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column("id", BigInteger, primary_key=True, nullable=False)
    user_id: Mapped[int] = mapped_column("user_id", BigInteger, nullable=False)
    channel_id: Mapped[Optional[int]] = mapped_column(
        "channel_id", BigInteger, nullable=True
    )
    time_created: Mapped[int] = mapped_column("time_created", DateTime, nullable=False)
    message: Mapped[str] = mapped_column("message", String, nullable=False)
    time = mapped_column("time", Time, nullable=False)
    start_date = mapped_column("start_date", Date, nullable=False)
    end_date = mapped_column("end_date", Date, nullable=True)
    week_frequency: Mapped[Optional[int]] = mapped_column(
        "week_frequency", Integer, nullable=True
    )


class Starboard(Base):
    __tablename__ = "starboard"

    # composite key on recv, sent.

    # recv == null implies deleted recv message.
    # recv_location == null implies deleted recv channel. recv should also be null.
    # sent == null implies blacklisted recv message.
    recv: Mapped[Optional[int]] = mapped_column(
        "recv", BigInteger, primary_key=True, nullable=True
    )
    recv_location: Mapped[Optional[int]] = mapped_column(
        "recv_location", BigInteger, nullable=True, unique=False
    )
    sent: Mapped[Optional[int]] = mapped_column(
        "sent", BigInteger, primary_key=True, nullable=True, unique=True
    )


class YellingBans(Base):
    __tablename__ = "yellingbans"

    user_id: Mapped[int] = mapped_column(
        "user_id", BigInteger, primary_key=True, nullable=False
    )
    value: Mapped[int] = mapped_column("value", BigInteger, nullable=False)
