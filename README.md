# UQCSbot

UQCSbot is our friendly chat bot used on the [UQCS Discord Server](https://discord.uqcs.org). For the UQCSbot used in our Slack team, see [UQCSbot-Slack](https://github.com/uqcomputing/uqcsbot-slack).

## Setup & Running Locally

UQCSbot uses [Poetry](https://python-poetry.org/) for dependency management. Once you have Poetry setup on your machine, you can setup and install dependencies by running:

```bash
poetry install
```

### Environment Variables

You'll need to define environment variables to be able to start the bot. The `.env.example` file contains a basis for what you can use as a `.env` file. You'll need to create an `.env` file with the required environment variables populated:

* `DISCORD_BOT_TOKEN` for the Discord provided bot token.
* `POSTGRES_URI_BOT` for the PostgreSQL connection string.

It is recommended that you acquire your own Discord bot token for testing, details can be found in the [Discord Developer Docs](https://discord.com/developers/docs/getting-started#creating-an-app). Requests can be made to committee for bot testing tokens, but will only be approved on a case by case basis.

More information for currently implemented environment variables can be found on [this wiki page](https://github.com/UQComputingSociety/uqcsbot-discord/wiki/Tokens-and-Environment-Variables).

### Running the Bot

Once you have a .env file, you can run the following command to start the bot:

```sh
poetry run botdev
```

To shutdown the bot, hit Ctrl+C

<details>
<summary><b>Alternative Instructions for Docker</b></summary>

UQCSbot is deployed using [Docker](https://docker.com). If you're familiar with it or want to fully simulate the production environment, you can follow these instructions instead.

If you're going to use Docker as your dev environment, make sure you have:
* [Docker](https://docs.docker.com/engine/install/)
* [Docker Compose](https://docs.docker.com/compose/install/)

To build and start Docker, you can run: (Note that depending on how Docker is configured, you may need to prepend `sudo`)
```
docker-compose up -d --build
```

To shut down the Docker environment, run:
```
docker-compose down
```
</details>

## Testing

Coming soon.

## Development Resources

If this is your first time working on an open source project, we're here to walk you through every step of the way.

If you're completely new to Git, check out [Atlassian's Git Tutorial site](https://www.atlassian.com/git).

<!-- If you're feeling ready to start working on the repository, check out this tutorial on forking and creating a pull request: ** TODO **  -->

If you're unsure what to work on, check out the [issues labelled good first issue](https://github.com/UQComputingSociety/uqcsbot-discord/labels/good%20first%20issue).

UQCSbot uses the open source [Discord.py project](https://github.com/Rapptz/discord.py), check out the docs at: <https://discordpy.readthedocs.io/>

If you want more information around working with Discord itself, check out the [Discord Developer Documentation](https://discord.com/developers/docs).

If you have any questions, reach out in the #bot-testing channel in the Discord!

## License

UQCSbot is licensed under the [MIT License](LICENSE).
