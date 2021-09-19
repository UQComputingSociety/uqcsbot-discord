from uqcsbot import bot, Command


@bot.on_command("cookbook")
def handle_cookbook(command: Command):
    """
    `!cookbook` - Returns the URL of the UQCS student-compiled cookbook (pdf).
    """
    bot.post_message(command.channel_id, "It's A Cookbook!\n"
                     "https://github.com/UQComputingSociety/cookbook")
