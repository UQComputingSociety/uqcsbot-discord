import datetime as dt
import discord
from discord import app_commands
from discord.ext import commands
from functools import partial
import logging
from typing import List, NamedTuple, Optional, Union

from uqcsbot.bot import UQCSBot
from uqcsbot.models import Reminders


USER_REMINDER_LIMIT = 10

REMINDME_MESSAGE_TITLE = "RemindMe: Reminder"
REMINDME_ERROR_TITLE = "RemindMe: Error"
REMINDME_ADDED_TITLE = "RemindMe: Reminder Added"
REMINDME_REMOVED_TITLE = "RemindMe: Reminder Removed"
REMINDME_LIST_TITLE = "RemindMe: List Reminders"

REMINDER_MESSAGE = "Reminder set by <@{}>:\n> {}"
REMINDER_NOT_FOUND_ERR = "Reminder id not found."
REMINDER_LIMIT_REACHED_ERR = f"You've reached the maximum number of active reminders ({USER_REMINDER_LIMIT})."
DATETIME_VALID_FORMAT_ERR = "Dates and times should conform to a valid ISO 8601 format."
DATETIME_IN_PAST_ERR = "Datetime can't be in the past."
STARTEND_DATE_IN_PAST_ERR = "Start or end date can't be in the past."
END_DATE_BEFORE_START_ERR = "End date can't be before the start date."
NEGATIVE_WEEK_FREQUENCY_ERR = "Week frequency must be non-negative."

REMOVE_REMINDERS_FOOTER = "You can remove active reminders with /remindme remove."
LIST_REMINDERS_FOOTER = "You can view your active reminders with /remindme list."

DISPLAY_DATE_FORMAT = '%A %d %b %Y'
DISPLAY_DAY_NAME_FORMAT = '%A'
DISPLAY_TIME_FORMAT = '%-I:%M %p'


class Reminder(NamedTuple):
    id: int
    user_id: int
    channel_id: int | None  # None => send reminder in DMs
    time_created: dt.datetime
    message: str
    time: dt.time
    start_date: dt.date
    end_date: dt.date | None  # None => non-ending
    week_frequency: int | None  # 0 => daily, None => one-time

    def __str__(self):
        id = self.id
        message = self.message
        time = self.time.strftime(DISPLAY_TIME_FORMAT)
        start_date = self.start_date.strftime(DISPLAY_DATE_FORMAT)

        if self.week_frequency == None:  # one-time reminders
            return f"Reminder with id {id} set for {start_date} at {time}:\n> {message}"

        if self.week_frequency == 0:
            day = "daily"
            frequency = ""
        else:  # convert day to word; Monday, Tuesday, etc.
            day = self.start_date.strftime(DISPLAY_DAY_NAME_FORMAT) + "s" 
            frequency = (", repeating every week" if self.week_frequency == 1 else
                         f", repeating every {self.week_frequency} weeks")

        if self.end_date == None:  # recurring reminders (non-ending)
            return (f"Reminder with id {id} set for {day} at {time} starting {start_date}{frequency}:\n> {message}")
        # recurring reminders (ending on self.end_date)
        end_date = self.end_date.strftime(DISPLAY_DATE_FORMAT)
        return (f"Reminder with id {id} set for {day} at {time} starting {start_date} and "
                f"ending {end_date}{frequency}:\n> {message}")
    
    def removed_str(self):
        return f"Reminder with id {self.id} removed:\n> {self.message}"

def _error_embed(description: str, footer: str = "") -> discord.Embed:
    """ Returns a formatted Error embed with the given description and an optional footer """
    embed = discord.Embed(title=REMINDME_ERROR_TITLE, description=description, color=discord.Color.red())
    if footer != "":
        embed.set_footer(text=footer)
    return embed

def _add_reminder_embed(reminder: Reminder, footer: str = "") -> discord.Embed:
    """ Returns a formatted Reminder Added embed with the given Reminder and an optional footer """
    embed = discord.Embed(title=REMINDME_ADDED_TITLE, description=str(reminder))
    if footer != "":
        embed.set_footer(text=footer)
    return embed

def _remove_reminder_embed(reminder: Reminder, footer: str = "") -> discord.Embed:
    """ Returns a formatted Reminder Removed embed with the given Reminder and an optional footer """
    embed = discord.Embed(title=REMINDME_REMOVED_TITLE, description=reminder.removed_str())
    if footer != "":
        embed.set_footer(text=footer)
    return embed

def _list_reminders_embed(reminders: List[Reminder], footer: str = "") -> discord.Embed:
    """ Returns a formatted List Reminders embed with a list of Reminders and an optional footer """
    if len(reminders) == 0:
        description = "You don't currently have any active reminders."
    else:
        description = (f"You currently have {len(reminders)} active reminder(s).\n\n" +
                        "\n\n".join([str(reminder) for reminder in reminders]))
    embed = discord.Embed(title=REMINDME_LIST_TITLE, description=description)
    if footer != "":
        embed.set_footer(text=footer)
    return embed


class RemindMe(commands.Cog):
    remindme_group = app_commands.Group(name="remindme", description="Reminder commands")

    def __init__(self, bot: UQCSBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """ Schedule all pre-existing reminders once bot is ready """
        for reminder in self._get_all_reminders():
            self._schedule_reminder(reminder)
        logging.info(f"All pre-existing reminders scheduled")

    def _add_reminder_to_db(self, reminder: Reminder):
        """ Adds the given Reminder to the Reminders table in the database """
        db_session = self.bot.create_db_session()
        db_session.add(Reminders(
            id=reminder.id,
            user_id=reminder.user_id,
            channel_id=reminder.channel_id,
            time_created=reminder.time_created,
            message=reminder.message,
            time=reminder.time,
            start_date=reminder.start_date,
            end_date=reminder.end_date,
            week_frequency=reminder.week_frequency
        ))
        db_session.commit()
        db_session.close()

    def _remove_reminder_from_db(self, reminder_id: int) -> Reminder:
        """ Removes the reminder with id `reminder_id` from the Reminders table in the database """
        db_session = self.bot.create_db_session()
        reminder_query = db_session.query(Reminders).filter(Reminders.id == reminder_id).one()
        removed_reminder = Reminder(
            reminder_query.id,
            reminder_query.user_id,
            reminder_query.channel_id,
            reminder_query.time_created,
            reminder_query.message,
            reminder_query.time,
            reminder_query.start_date,
            reminder_query.end_date,
            reminder_query.week_frequency
        )
        db_session.delete(reminder_query)
        db_session.commit()
        db_session.close()

        return removed_reminder

    def _get_all_reminders(self) -> List[Reminder]:
        """ Returns all the active reminders in the database in creation order """
        db_session = self.bot.create_db_session()
        reminders_query = db_session.query(Reminders)
        db_session.close()

        return [Reminder(
            reminder.id,
            reminder.user_id,
            reminder.channel_id,
            reminder.time_created,
            reminder.message,
            reminder.time,
            reminder.start_date,
            reminder.end_date,
            reminder.week_frequency
        ) for reminder in sorted(reminders_query, key=lambda reminder: reminder.time_created)]

    def _get_user_reminders(self, user_id: int) -> List[Reminder]:
        """ Returns all the active reminders belonging to the user with id `user_id` in creation order """
        return list(filter(lambda reminder: reminder.user_id == user_id, self._get_all_reminders()))
    
    def _get_unused_reminder_id(self) -> int:
        """ Returns a reminder id that is not currently in use """
        reminders = self._get_all_reminders()
        reminder_ids = [reminder.id for reminder in reminders]
        i = 1
        while (id := i) in reminder_ids:
            i += 1
        return id

    def _reached_reminder_limit(self, user: Union[discord.User, discord.Member]) -> bool:
        """ Returns whether the given user has reached the maximum reminder limit. """
        # a slight caveat is that if a user sends a command to the bot in DMs, it won't be able to
        # check for admin perms, so the reminder limit will be enforced
        if isinstance(user, discord.Member) and user.guild_permissions.administrator:
            return False
        return len(self._get_user_reminders(user.id)) >= USER_REMINDER_LIMIT

    def _schedule_reminder(self, reminder: Reminder):
        """ Schedules the reminder to be sent at its specified time (or its next recurring time) """
        today = dt.date.today()
        time = reminder.time
        start_date = reminder.start_date
        start_datetime = dt.datetime.combine(reminder.start_date, time)
        end_datetime = dt.datetime.combine(reminder.end_date, time) if reminder.end_date != None else None

        # if reminder datetime is in the past (bot downtime or something went wrong etc.), send a reminder now
        if ((reminder.week_frequency == None and start_datetime < dt.datetime.now()) or
            reminder.week_frequency != None and end_datetime != None and end_datetime < dt.datetime.now()):
            self.bot.schedule_task(partial(self._process_reminder, reminder), misfire_grace_time=None)

        # otherwise, reminder datetime is in the future so we can schedule it
        if reminder.week_frequency == None or start_datetime > dt.datetime.now():
            # one-time reminder OR first occurrence of recurring reminder, so schedule for start_date
            return self.bot.schedule_task(
                partial(self._process_reminder, reminder),
                trigger="cron", timezone="Australia/Brisbane", misfire_grace_time=None,
                year=start_date.year, month=start_date.month, day=start_date.day,
                hour=time.hour, minute=time.minute, second=time.second
            )

        # non-first occurrence of recurring reminder, schedule next occurrence based on week_frequency
        if reminder.week_frequency == 0:
            # daily reminder, schedule for today or tomorrow depending on time
            if time > dt.datetime.now().time():
                year, month, day = today.year, today.month, today.day
            else:
                tomorrow = today + dt.timedelta(days=1)
                year, month, day = tomorrow.year, tomorrow.month, tomorrow.day
        else:
            # schedule for next available datetime
            next_date = start_date
            if time <= dt.datetime.now().time():
                # find next available datetime after today
                while next_date <= today:
                    next_date += dt.timedelta(days = 7 * reminder.week_frequency)
            else:
                # find next available datetime after yesterday
                while next_date < today:
                    next_date += dt.timedelta(days = 7 * reminder.week_frequency)
            year, month, day = next_date.year, next_date.month, next_date.day

        # check selected datetime is not past end_date; if so, this reminder is done
        datetime = dt.datetime.combine(dt.date(year, month, day), time)
        if end_datetime != None and datetime > end_datetime:
            return self._remove_reminder_from_db(reminder.id)

        self.bot.schedule_task(
            partial(self._process_reminder, reminder),
            trigger="cron", timezone="Australia/Brisbane", misfire_grace_time=None,
            year=year, month=month, day=day, hour=time.hour, minute=time.minute, second=time.second
        )

    async def _process_reminder(self, reminder: Reminder):
        """
        Sends the given reminder, and schedules any future reminders if it is recurring and hasn't
        ended yet. Otherwise, removes the reminder from the database.
        """
        if (user := self.bot.get_user(reminder.user_id)) != None:
            ctx = None
            if reminder.channel_id == None:  # send in DMs
                ctx = user
            elif isinstance(channel := self.bot.get_channel(reminder.channel_id), discord.TextChannel):
                # send in server channel, if it is a text channel
                ctx = channel

            if ctx != None:
                if isinstance(user, discord.Member) and user.guild_permissions.administrator:
                    allowed_mentions = discord.AllowedMentions.all()
                else:
                    allowed_mentions = discord.AllowedMentions(users=[user])
                await ctx.send(REMINDER_MESSAGE.format(reminder.user_id, reminder.message), allowed_mentions=allowed_mentions)
            else:
                logging.warning(f"Reminder couldn't be sent to channel with id {reminder.channel_id}; not a text channel")
        else:
            logging.warning(f"User with id {reminder.user_id} couldn't be found")

        if reminder.week_frequency == None:  # one-time reminder, remove from db
            self._remove_reminder_from_db(reminder.id)
        else:  # recurring reminder
            # check if we need to schedule reminder again
            if reminder.end_date == None or reminder.end_date > dt.date.today():
                self._schedule_reminder(reminder)
            else:
                self._remove_reminder_from_db(reminder.id)

    @remindme_group.command(name="add")
    @app_commands.describe(
        message="Reminder message",
        time="Time to send reminder in a valid ISO 8601 format, e.g. HH:MM",
        date="Date to send reminder in a valid ISO 8601 format, e.g. YYYY-MM-DD; defaults to today",
    )
    async def add_reminder(self, interaction: discord.Interaction, message: str, date: Optional[str], time: str):
        """ Sets a one-time reminder """
        if self._reached_reminder_limit(interaction.user):
            embed = _error_embed(REMINDER_LIMIT_REACHED_ERR, REMOVE_REMINDERS_FOOTER)
            return await interaction.response.send_message(embed=embed)

        # check datetime is valid
        try:
            check_time = dt.time.fromisoformat(time)
            check_date = dt.date.fromisoformat(date) if date else dt.date.today()
            check_datetime = dt.datetime.combine(check_date, check_time)
        except ValueError:
            embed = _error_embed(DATETIME_VALID_FORMAT_ERR)
            return await interaction.response.send_message(embed=embed)

        if check_datetime < dt.datetime.now():
            embed = _error_embed(DATETIME_IN_PAST_ERR)
            return await interaction.response.send_message(embed=embed)

        # add reminder to db and schedule
        reminder = Reminder(
            self._get_unused_reminder_id(),
            interaction.user.id,
            interaction.channel_id,
            dt.datetime.now(),
            message,
            check_time,
            check_date,
            check_date,
            None)
        self._add_reminder_to_db(reminder)
        self._schedule_reminder(reminder)

        embed = _add_reminder_embed(reminder, LIST_REMINDERS_FOOTER)
        await interaction.response.send_message(embed=embed)

    @remindme_group.command(name="addrecurring")
    @app_commands.describe(
        message="Reminder message",
        time="Time of day in a valid ISO 8601 format, e.g. HH:MM",
        week_frequency="Reminder every `week_frequency` week(s), set to 0 for daily reminders; defaults to 1 (weekly)",
        start_date="Date to start reminders in a valid ISO 8601 format, e.g. YYYY-MM-DD; defaults to today",
        end_date="Date to stop reminders in a valid ISO 8601 format, e.g. YYYY-MM-DD; defaults to no end date"
    )
    async def add_recurring_reminder(self, interaction: discord.Interaction, message: str, time: str,
                                     week_frequency: Optional[int], start_date: Optional[str], end_date: Optional[str]):
        """ Sets a new recurring reminder """
        if self._reached_reminder_limit(interaction.user):
            embed = _error_embed(REMINDER_LIMIT_REACHED_ERR, REMOVE_REMINDERS_FOOTER)
            return await interaction.response.send_message(embed=embed)

        # check datetime is valid
        try:
            check_time = dt.time.fromisoformat(time)
            check_start_date = dt.date.fromisoformat(start_date) if start_date else dt.date.today()
            check_end_date = dt.date.fromisoformat(end_date) if end_date else None
        except ValueError:
            embed = _error_embed(DATETIME_VALID_FORMAT_ERR)
            return await interaction.response.send_message(embed=embed)

        if (check_start_date < dt.date.today() or
            (check_end_date != None and dt.datetime.combine(check_end_date, check_time) < dt.datetime.now())):
            embed = _error_embed(STARTEND_DATE_IN_PAST_ERR)
            return await interaction.response.send_message(embed=embed)

        if check_end_date != None and check_end_date < check_start_date:
            embed = _error_embed(END_DATE_BEFORE_START_ERR)
            return await interaction.response.send_message(embed=embed)

        if (week_frequency := week_frequency if week_frequency != None else 1) < 0:
            embed = _error_embed(NEGATIVE_WEEK_FREQUENCY_ERR)
            return await interaction.response.send_message(embed=embed)

        # add reminder to db and schedule
        reminder = Reminder(
            self._get_unused_reminder_id(),
            interaction.user.id,
            interaction.channel_id,
            dt.datetime.now(),
            message,
            check_time,
            check_start_date,
            check_end_date,
            week_frequency)
        self._add_reminder_to_db(reminder)
        self._schedule_reminder(reminder)

        embed = _add_reminder_embed(reminder, LIST_REMINDERS_FOOTER)
        await interaction.response.send_message(embed=embed)

    @remindme_group.command(name="remove")
    @app_commands.describe(reminder_id="Reminder id")
    async def remove_reminder(self, interaction: discord.Interaction, reminder_id: int):
        """ Removes an active reminder """
        reminders = self._get_user_reminders(interaction.user.id)
        reminder_ids = [reminder.id for reminder in reminders]

        if reminder_id not in reminder_ids:
            embed = _error_embed(REMINDER_NOT_FOUND_ERR, LIST_REMINDERS_FOOTER)
            return await interaction.response.send_message(embed=embed)

        removed_reminder = self._remove_reminder_from_db(reminder_id)
        embed = _remove_reminder_embed(removed_reminder)
        await interaction.response.send_message(embed=embed)

    @remindme_group.command(name="list")
    async def list_reminders(self, interaction: discord.Interaction):
        """ Lists all your active reminders """
        reminders = self._get_user_reminders(interaction.user.id)
        embed = _list_reminders_embed(reminders)
        await interaction.response.send_message(embed=embed)

async def setup(bot: UQCSBot):
    await bot.add_cog(RemindMe(bot))
