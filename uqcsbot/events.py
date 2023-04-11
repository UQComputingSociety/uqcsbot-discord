import logging
from calendar import day_abbr, month_abbr, month_name
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

import discord
from discord import app_commands
import requests
from dateutil.rrule import rrulestr
from discord.ext import commands
from icalendar import Calendar
from pytz import timezone, utc

from uqcsbot.bot import UQCSBot

UQCS_CALENDAR_URL = "https://calendar.google.com/calendar/ical/" \
                    "q3n3pce86072n9knt3pt65fhio%40group.calendar.google.com/public/basic.ics"
# EXTERNAL_CALENDAR_URL = "https://calendar.google.com/calendar/ical/" \
#                         "72abf01afvsl3bjd9oq2g1avgg%40group.calendar.google.com/public/basic.ics"
# Testing calendar: "https://calendar.google.com/calendar/ical/7djv171v2mdr4dmufq612j6uj4%40group.calendar.google.com/public/basic.ics"

MONTH_NUMBER = {month.lower(): index for index, month in enumerate(month_abbr)}

MAX_RECURRING_EVENTS = 3
BRISBANE_TZ = timezone('Australia/Brisbane')

class EventFilter(object):
    def __init__(self, full=False, weeks=None, cap=None, month=None, is_valid=True):
        self.is_valid = is_valid
        self._full = full
        self._weeks = weeks
        self._cap = cap
        self._month = month

    @classmethod
    def from_argument(cls, args: Tuple):
        if len(args) == 0:
            return cls(weeks=2)
        else:
            if 'full' in args or 'all' in args:
                return cls(full=True)
            elif 'weeks' in args:
                i = args.index('weeks') + 1
                return cls(weeks=int(args[i]))
            else:
                # No valid input
                return cls(weeks=2)

    def filter_events(self, events: List['Event'], start_time: datetime):
        if self._weeks is not None:
            end_time = start_time + timedelta(weeks=self._weeks)
            return [e for e in events if e.start < end_time]
        if self._month is not None:
            return [e for e in events if e.start.month == self._month]
        elif self._cap is not None:
            return events[:self._cap]
        return events

    def get_header(self):
        if self._full:
            return "List of *all* upcoming events:"
        elif self._weeks is not None:
            return f"Events in the next *{self._weeks} weeks*:"
        elif self._month is not None:
            return f"Events in *{month_name[self._month]}*:"
        else:
            return f"The *next {self._cap} events*:"

    def get_no_result_msg(self):
        if self._weeks is not None:
            return f"There don't appear to be any events in the next *{self._weeks}* weeks"
        elif self._month is not None:
            return f"There don't appear to be any events in *{month_name[self._month]}*"
        else:
            return "There don't appear to be any upcoming events..."

class Event(object):
    def __init__(self, start: datetime, end: datetime,
                 location: str, summary: str, recurring: bool,
                 link: Optional[str], source: Optional[str] = None):
        self.start = start
        self.end = end
        self.location = location
        self.summary = summary
        self.recurring = recurring
        self.link = link
        self.source = source

    @classmethod
    def encode_text(cls, text: str) -> str:
        """
        Encodes user-specified text so that it is not interpreted as command characters
        by Slack. Implementation as required by: https://api.slack.com/docs/message-formatting
        Note that this encoding process does not stop injection of text effects (bolding,
        underlining, etc.), or a malicious user breaking the text formatting in the events
        command. It should, however, prevent <, & and > being misinterpreted and including
        links where they should not.
        --
        :param text: The text to encode
        :return: The encoded text
        """
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @classmethod
    def from_cal_event(cls, cal_event, source: str = "UQCS", recurrence_dt: datetime = None):
        """
        Converts an ical event to an Event

        :param cal_event: event to convert
        :param source: the calendar the event was sourced from
        :param recurrence_dt: if this is a one off event then None
                                else the date of this instance of a recurring event
        """
        if recurrence_dt:
            start = recurrence_dt
            end = recurrence_dt + (cal_event.get('DTEND').dt - cal_event.get('DTSTART').dt)

        else:
            start = cal_event.get('dtstart').dt
            end = cal_event.get('dtend').dt
            # ical 'dt' properties are parsed as a 'DDD' (datetime, date, duration) type.
            # The below code converts a date to a datetime, where time is set to midnight.
            if isinstance(start, date) and not isinstance(start, datetime):
                start = datetime.combine(start, datetime.min.time()).astimezone(utc)
            if isinstance(end, date) and not isinstance(end, datetime):
                end = datetime.combine(end, datetime.max.time()).astimezone(utc)
        location = cal_event.get('location', 'TBA')
        summary = cal_event.get('summary')
        return cls(start, end, location,
                   f"{'[External] ' if source == 'external' else ''}{summary}",
                   recurrence_dt is not None, None, source)

    def get_title(self):
        # TODO: fix for case with link
        return Event.encode_text(("[Recurring] " if self.recurring else "") + self.summary)

    def get_time_loc(self):
        d1 = self.start.astimezone(BRISBANE_TZ)
        d2 = self.end.astimezone(BRISBANE_TZ)

        start_str = (f"{day_abbr[d1.weekday()].upper()}"
                     + f" {month_abbr[d1.month].upper()} {d1.day} {d1.hour}:{d1.minute:02}")
        if (d1.month, d1.day) != (d2.month, d2.day):
            end_str = (f"{day_abbr[d2.weekday()].upper()}"
                       + f" {month_abbr[d2.month].upper()} {d2.day} {d2.hour}:{d2.minute:02}")
        else:
            end_str = f"{d2.hour}:{d2.minute:02}"

        # Encode user-provided text to prevent certain characters
        # being interpreted as slack commands.
        location_str = Event.encode_text(self.location)
        return f"**{start_str} - {end_str}** {'*(' + location_str + ')*' if location_str else ''}"

class Events(commands.Cog):
    """
        Display events 
    """
    CHANNEL_NAME = "events"

    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self.bot.schedule_task(self.scheduled_message, trigger='cron', hour=9, day_of_week="mon", timezone='Australia/Brisbane')

    async def scheduled_message(self):
        channel = discord.utils.get(self.bot.uqcs_server.channels, name=self.CHANNEL_NAME)
        if channel is not None:
            await self.send_events(channel)
        else:
            logging.warning(f"Could not find required channel #{self.CHANNEL_NAME}")

    @classmethod
    def _get_current_time(cls):
        """
        Returns the current date and time
        This function exists purely so it can be mocked for testing
        """
        return datetime.now(tz=BRISBANE_TZ).astimezone(utc)


    def _handle_calendar(self, calendar) -> List[Event]:
        """
        Returns a list of events from a calendar
        """
        events = []
        current_time = self._get_current_time()
        # subcomponents are how icalendar returns the list of things in the calendar
        for component in calendar.subcomponents:
            # we are only interested in ones with the name VEVENT as they
            # are events
            if component.name != 'VEVENT':
                continue
            elif component.get('RRULE') is not None:
                # If the until date exists, update it to UTC
                if component['RRULE'].get('UNTIL') is not None:
                    until = datetime.combine(component['RRULE']['UNTIL'][0], datetime.min.time()) \
                                .astimezone(utc)
                    component['RRULE']['UNTIL'] = [until]
                rule = rrulestr('\n'.join([
                        line for line in component.content_lines()
                        if line.startswith('RRULE')
                        or line.startswith('EXDATE')
                    ]), dtstart=component.get('DTSTART').dt)
                rule = [dt for dt in list(rule) if dt > current_time]
                for dt in rule[:MAX_RECURRING_EVENTS]:
                    dt = dt.replace(tzinfo=BRISBANE_TZ)
                    event = Event.from_cal_event(component, recurrence_dt=dt)
                    events.append(event)
            else:
                # we convert it to our own event class
                event = Event.from_cal_event(component)
                # then we want to filter out any events that are not after the current time
                if event.start > current_time:
                    events.append(event)

        return events

    async def send_events(self, channel: discord.abc.Messageable, interaction: discord.Interaction = None, *args):
        current_time = self._get_current_time()
        event_filter = EventFilter.from_argument(args)
        events = []

        uqcs_calendar = Calendar.from_ical(self._get_calendar_file())
        events += self._handle_calendar(uqcs_calendar)

        # then we apply our event filter as generated earlier
        events = event_filter.filter_events(events, current_time)
        # then, we sort the events by date
        events = sorted(events, key=lambda event_: event_.start)

        if not events:
            message_text = f"_{event_filter.get_no_result_msg()}_\n" \
                           f"For a full list of events, visit: " \
                           f"https://uqcs.org/events " 
            if interaction == None:
                await channel.send(message_text)
            else:
                await interaction.response.send_message(message_text)
        else:
            message_text = f"{event_filter.get_header()}"
            if interaction == None:
                await channel.send(message_text)
            else:
                await interaction.response.send_message(message_text)

            for event in events:
                colour = discord.Colour.from_rgb(82, 151, 209)
     
                embed = discord.Embed()
                embed.colour = colour
                embed.title = f"{event.get_title()}"
                embed.description = f"{event.get_time_loc()}"
                await channel.send(embed=embed)

    @app_commands.command()
    @app_commands.describe(weeks="Number of weeks to return, defaults to 2")
    async def events(self, interaction: discord.Interaction, weeks: int = 2):
        """ Shows the upcoming UQCS events for the next 2 weeks. """
        await self.send_events(interaction.channel, interaction, "weeks", weeks)

    @app_commands.command()
    async def allevents(self, interaction: discord.Interaction):
        """ Shows all upcoming UQCS events. """
        await self.send_events(interaction.channel, interaction, "full")

    @classmethod
    def _get_calendar_file(cls) -> bytes:
        """
        Loads the UQCS or External Events calender .ics file from Google Calendar.
        This method is mocked by unit tests.
        :return: The returned ics calendar file, as a stream
        """
        http_response = requests.get(UQCS_CALENDAR_URL)
        return http_response.content

async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))

