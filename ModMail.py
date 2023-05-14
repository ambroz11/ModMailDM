import discord
from discord.ext import commands
import pymongo
from datetime import datetime
from webserver import keep_alive
import os

intents = discord.Intents.all()
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix="!", intents=intents)

guild_id = SERVER ID HERE
category_id = CATEGORY WHERE IT WILL OPEN TICKETS
# if you want for replit it's set, if you want for other hosts replace os.environ.get("TOKEN") with your token
token = os.environ.get("TOKEN")
server_id = SERVER ID HERE

open_tickets = {}

# Replace the connection string and database name with your own
client = pymongo.MongoClient(
  "<CONNECTION STRING>"
)
db = client["<DATABASE>"]
tickets_collection = db["<COLLECTIONS"]


@bot.event
async def on_ready():
  print(f"{bot.user} has connected to Discord!")
  activity = discord.Streaming(name="DM for Support",
                               url="https://www.twitch.tv/yourchannel")
  await bot.change_presence(status=discord.Status.online, activity=activity)


@bot.event
async def on_message(message):
  if message.author.bot:
    return

  if isinstance(message.channel, discord.DMChannel):
    if message.author.id in open_tickets:
      ticket_channel = bot.get_channel(open_tickets[message.author.id])
      if ticket_channel is not None:
        embed = discord.Embed(title=f"Message from {message.author}",
                              description=message.content,
                              color=0x03fcf0)
        await ticket_channel.send(embed=embed)
    else:
      guild = bot.get_guild(guild_id)
      category = guild.get_channel(category_id)
      overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True),
        guild.roles[0]: discord.PermissionOverwrite(
          read_messages=True)  # Allow @everyone to read messages
      }
      ticket_channel = await category.create_text_channel(
        f"ticket-{message.author.id}", overwrites=overwrites)
      open_tickets[message.author.id] = ticket_channel.id
      embed = discord.Embed(title=f"New ticket from {message.author}",
                            description=message.content,
                            color=0x03fcf0)
      await ticket_channel.send(embed=embed)

  elif message.guild and message.guild.id == server_id:
    await bot.process_commands(message)


@bot.command(name="commands")
async def commands(ctx):
  if ctx.guild.id == server_id:
    embed = discord.Embed(title="Bot Commands", color=0x00ff00)
    embed.add_field(name="!r", value="Reply to a user's ticket", inline=False)
    embed.add_field(name="!close", value="Close a user's ticket", inline=False)
    embed.add_field(name="!contact",
                    value="Contact a user and create a ticket",
                    inline=False)
    await ctx.send(embed=embed)


@bot.command(name="r")
async def r(ctx, *, message: str):
  if ctx.guild.id == server_id:
    user_id = ctx.channel.name.split("-")[1]
    user = bot.get_user(int(user_id))
    if user:
      ticket_channel = bot.get_channel(open_tickets[int(user_id)])
      embed = discord.Embed(title="Support:",
                            description=message,
                            color=0xff0011)
      await ticket_channel.send(embed=embed)
      await user.send(embed=embed)
    else:
      await ctx.send("User not found")


@bot.command(name="close")
async def close(ctx):
  if ctx.guild.id == server_id:
    user_id = int(ctx.channel.name.split("-")[1])
    if user_id in open_tickets:
      ticket_channel = bot.get_channel(open_tickets[user_id])
      messages = [
        message async for message in ticket_channel.history(limit=None)
      ]
      # Replace with the correct channel ID
      log_channel = bot.get_channel(<INSERT LOGS CHANNEL ID>)
      log_embed = discord.Embed(
        title="Ticket Created",
        description=
        f"Information\nUser: {user_id}\nTicket Channel: {ticket_channel.name}\nDate: {datetime.now().strftime('%A, %B %d %Y')}\n{datetime.now().strftime('%m/%d/%Y %I:%M %p')}\nMessages:\n",
        color=0xff00)
      for message in reversed(messages):
        for embed in message.embeds:
          log_embed.add_field(name=f"{embed.title} ({embed.url})",
                              value=embed.description,
                              inline=False)
      await log_channel.send(embed=log_embed)
      await ticket_channel.delete()
      del open_tickets[user_id]
      await ctx.send(f"Ticket for {user_id} closed")

      # Store the ticket information in the MongoDB database
      ticket_data = {
        "user_id":
        user_id,
        "messages": [message.content for message in messages],
        "embedded_messages": [
          embed.to_dict() for message in messages for embed in message.embeds
          if message.embeds
        ],
        "ticket_channel_name":
        ticket_channel.name,
        "date":
        datetime.now()
      }

      tickets_collection.insert_one(ticket_data)
    else:
      await ctx.send("No open ticket for this user")


@bot.command(name="contact")
async def contact(ctx, user_id: int, *, message: str):
  if ctx.guild.id == server_id:
    user = bot.get_user(user_id)
    if user:
      guild = bot.get_guild(guild_id)
      category = guild.get_channel(category_id)
      overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True),
        guild.roles[0]: discord.PermissionOverwrite(
          read_messages=True)  # Allow @everyone to read messages
      }
      ticket_channel = await category.create_text_channel(
        f"ticket-{user_id}", overwrites=overwrites)
      open_tickets[user_id] = ticket_channel.id
      embed = discord.Embed(title=f"New ticket from {user}",
                            description=message,
                            color=0xff0011)
      await ticket_channel.send(embed=embed)
      await ctx.send(f"Ticket created for {user.mention}")
      dm_embed = discord.Embed(title="Support:",
                               description=message,
                               color=0x03fcf0)
      await user.send(embed=dm_embed)

      # Store the ticket information in the MongoDB database
      ticket_data = {
        "user_id": user_id,
        "message": message,
        "ticket_channel_name": ticket_channel.name,
        "date": datetime.now()
      }
      tickets_collection.insert_one(ticket_data)
    else:
      await ctx.send("User not found")


keep_alive()
bot.run(token)
