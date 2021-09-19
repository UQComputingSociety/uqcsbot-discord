from uqcsbot import bot, Command
import requests
import json
from uqcsbot.utils.command_utils import UsageSyntaxException


@bot.on_command("wiki")
def handle_wiki(command: Command):
    """
    `!wiki <TOPIC>` - Returns a snippet of text from a relevent wikipedia entry.
    """
    if not command.has_arg():
        raise UsageSyntaxException()

    search_query = command.arg
    api_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&format=json&limit=2"

    http_response = requests.get(api_url, params={'search': search_query})
    if http_response.status_code != requests.codes.ok:
        bot.post_message(command.channel_id, "Problem fetching data")
        return

    _, title_list, snippet_list, url_list = json.loads(http_response.content)

    # If the results are empty let them know. Any list being empty signifies this.
    if len(title_list) == 0:
        bot.post_message(command.channel_id, "No Results Found.")
        return

    title, snippet, url = title_list[0], snippet_list[0], url_list[0]

    # Sometimes the first element is an empty string which is weird so we handle that rare case here
    if len(title) * len(snippet) * len(url) == 0:
        bot.post_message(command.channel_id, "Sorry, there was something funny about the result")
        return

    # Detect if there are multiple references to the query
    # if so, use the first reference (i.e. the second item in the lists).
    multiple_reference_instances = ("may refer to:", "may have several meanings:")
    if any(instance in snippet for instance in multiple_reference_instances):
        title, snippet, url = title_list[1], snippet_list[1], url_list[1]

    # The first url and title matches the first snippet containing any content
    message = f'{title}: {snippet}\nLink: {url}'
    bot.post_message(command.channel_id, message)
