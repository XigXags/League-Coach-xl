"""Check the bot credential with Discord without joining a server or printing the token."""

import asyncio

import discord

from credentials import load_discord_token


async def main() -> None:
    token = load_discord_token()
    client = discord.Client(intents=discord.Intents.none())
    try:
        await client.login(token)
        application = await client.application_info()
        print(f"Bot: {client.user} (ID {client.user.id})")
        print(f"Application ID: {application.id}")
    except discord.LoginFailure:
        print("Discord rejected the bot token. Reset it in the Developer Portal and update the local file.")
        raise SystemExit(1) from None
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
