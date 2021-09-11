from argparse import ArgumentParser
from enum import Enum
from typing import Optional, Tuple

from slackblocks import Attachment, Color, SectionBlock
from sqlalchemy.exc import NoResultFound

from uqcsbot import bot, Command
from uqcsbot.models import Link
from uqcsbot.utils.command_utils import loading_status


class LinkScope(Enum):
    """
    Possible requested scopes for setting or retrieving a link.
    """
    CHANNEL = "channel"
    GLOBAL = "global"


class SetResult(Enum):
    """
    Possible outcomes of the set link operation.
    """
    NEEDS_OVERRIDE = "Link already exists, use `-f` to override"
    OVERRIDE_SUCCESS = "Successfully overrode link"
    NEW_LINK_SUCCESS = "Successfully added link"


def set_link_value(key: str, value: str, channel: str,
                   override: bool, link_scope: Optional[LinkScope] = None) -> Tuple[SetResult, str]:
    """
    Sets a corresponding value for a particular key. Keys are set to global by default but this can
    be overridden by passing the channel flag. Existing links can only be overridden if the
    override flag is passed.
    :param key: the lookup key for users to search the value by
    :param value: the value to associate with the key
    :param channel: the name of the channel the set operation was initiated in
    :param link_scope: defines the scope to set the link in, defaults to global if not provided
    :param override: required to be True if an association already exists and needs to be updated
    :return: a SetResult status and the value associated with the given key/channel combination
    """
    link_channel = channel if link_scope == LinkScope.CHANNEL else None
    session = bot.create_db_session()

    try:
        exists = session.query(Link).filter(Link.key == key,
                                            Link.channel == link_channel).one()
        if exists and not override:
            return SetResult.NEEDS_OVERRIDE, exists.value
        session.delete(exists)
        result = SetResult.OVERRIDE_SUCCESS
    except NoResultFound:
        result = SetResult.NEW_LINK_SUCCESS
    session.add(Link(key=key, channel=link_channel, value=value))
    session.commit()
    session.close()
    return result, value


def get_link_value(key: str,
                   channel: str,
                   link_scope: Optional[LinkScope] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Gets the value associated with a given key (and optionally channel). If a channel association
    exists, this is returned, otherwise a global association is returned. If no association exists
    then None is returned. The default behaviour can be overridden by passing the global flag to
    force retrieval of a global association when a channel association exists.
    :param key: the key to look up
    :param channel: the name of the channel the lookup request was made from
    :param link_scope: the requested scope to retrieve the link from (if supplied)
    :return: the associated value if an association exists, else None, and the source
    (global/channel) if any else None
    """
    session = bot.create_db_session()
    channel_match = session.query(Link).filter(Link.key == key,
                                               Link.channel == channel).one_or_none()
    global_match = session.query(Link).filter(Link.key == key,
                                              Link.channel == None).one_or_none()  # noqa: E711
    session.close()

    if link_scope == LinkScope.GLOBAL:
        return (global_match.value, "global") if global_match else (None, None)

    if link_scope == LinkScope.CHANNEL:
        return (channel_match.value, "channel") if channel_match else (None, None)

    if channel_match:
        return channel_match.value, "channel"

    if global_match:
        return global_match.value, "global"

    return None, None


@bot.on_command('link')
@loading_status
def handle_link(command: Command) -> None:
    """
    `!link [-c | -g] [-f] key [value [value ...]]` - Set and retrieve information in a key value
    store. Links can be set to be channel specific or global. Links are set as global by default,
    and channel specific links are retrieved by default unless overridden with the respective flag.
    """
    parser = ArgumentParser("!link", add_help=False)
    parser.add_argument("key", type=str, help="Lookup key")
    parser.add_argument("value", type=str, help="Value to associate with key", nargs="*")
    flag_group = parser.add_mutually_exclusive_group()
    flag_group.add_argument("-c", "--channel", action="store_true", dest="channel_flag",
                            help="Ensure a channel link is retrieved, or none is")
    flag_group.add_argument("-g", "--global", action="store_true", dest="global_flag",
                            help="Ignore channel link and force retrieval of global")
    parser.add_argument("-f", "--force-override", action="store_true", dest="override",
                        help="Must be passed if overriding a link")

    try:
        args = parser.parse_args(command.arg.split() if command.has_arg() else [])
    except SystemExit:
        # Incorrect Usage
        return bot.post_message(command.channel_id, "",
                                attachments=[Attachment(SectionBlock(str(parser.format_help())),
                                                        color=Color.YELLOW)._resolve()])

    channel = bot.channels.get(command.channel_id)
    if not channel:
        return bot.post_message(command.channel_id, "", attachments=[
            Attachment(SectionBlock("Cannot find channel name, please try again."),
                       color=Color.YELLOW)._resolve()
        ])

    channel_name = channel.name

    link_scope = LinkScope.CHANNEL if args.channel_flag else \
        LinkScope.GLOBAL if args.global_flag else None

    # Retrieve a link
    if not args.value:
        link_value, source = get_link_value(key=args.key,
                                            channel=channel_name,
                                            link_scope=link_scope)
        channel_text = f" in channel `{channel_name}`" if args.channel_flag else ""
        if link_value:
            source_text = source if source == 'global' else channel_name
            response = f"{args.key} ({source_text}): {link_value}"
        else:
            response = f"No link found for key: `{args.key}`" + channel_text
        color = Color.GREEN if link_value else Color.RED
        return bot.post_message(command.channel_id, "", attachments=[
            Attachment(SectionBlock(response), color=color)._resolve()
        ])

    # Set a link
    if args.key and args.value:
        result, current_value = set_link_value(key=args.key,
                                               channel=channel_name,
                                               value=" ".join(args.value),
                                               override=args.override,
                                               link_scope=link_scope)
        color = Color.YELLOW if result == SetResult.NEEDS_OVERRIDE else Color.GREEN
        scope = channel_name if args.channel_flag else 'global'
        response = f"{args.key} ({scope}): {current_value}"
        attachment = Attachment(SectionBlock(response), color=color)._resolve()
        bot.post_message(command.channel_id, f"{result.value}:", attachments=[attachment])
