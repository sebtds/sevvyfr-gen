import time
import discord
from discord import app_commands

TOKEN = ""
GUILD_ID = 12345678901   # your server ID
OWNER_ID = "sevvyfr."   # your Discord user ID
STOCK_FILE = "stock.txt"
COOLDOWN_SECONDS = 300  # 5 minutes

cooldowns = {}


class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        await self.tree.sync(guild=guild)


client = MyClient()


def get_stock():
    try:
        with open(STOCK_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        return []


def save_stock(lines):
    with open(STOCK_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def format_time(seconds):
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}m {secs}s"


def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.tree.command(
    name="gen",
    description="Get one item from stock",
    guild=discord.Object(id=GUILD_ID)
)
async def gen(interaction: discord.Interaction):
    user_id = interaction.user.id
    now = time.time()

    if user_id in cooldowns:
        remaining = int(COOLDOWN_SECONDS - (now - cooldowns[user_id]))
        if remaining > 0:
            await interaction.response.send_message(
                f"You're on cooldown. Try again in {format_time(remaining)}.",
                ephemeral=True
            )
            return

    stock = get_stock()

    if not stock:
        await interaction.response.send_message("Out of stock.", ephemeral=True)
        return

    item = stock.pop(0)
    save_stock(stock)

    try:
        await interaction.user.send(f"Your generated string:\n`{item}`")
        cooldowns[user_id] = now
        await interaction.response.send_message("Check your DMs.", ephemeral=True)
    except discord.Forbidden:
        stock.insert(0, item)
        save_stock(stock)
        await interaction.response.send_message(
            "I couldn't DM you. Turn on DMs and try again.",
            ephemeral=True
        )


@client.tree.command(
    name="restock",
    description="Add strings to stock",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(items="Paste strings separated by new lines")
async def restock(interaction: discord.Interaction, items: str):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message(
            "You are not allowed to use this command.",
            ephemeral=True
        )
        return

    new_items = [line.strip() for line in items.splitlines() if line.strip()]
    if not new_items:
        await interaction.response.send_message(
            "No valid strings were provided.",
            ephemeral=True
        )
        return

    current_stock = get_stock()
    current_stock.extend(new_items)
    save_stock(current_stock)

    await interaction.response.send_message(
        f"Added {len(new_items)} item(s). Total stock: {len(current_stock)}",
        ephemeral=True
    )


@client.tree.command(
    name="stock",
    description="See how many items are left",
    guild=discord.Object(id=GUILD_ID)
)
async def stock(interaction: discord.Interaction):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message(
            "You are not allowed to use this command.",
            ephemeral=True
        )
        return

    amount = len(get_stock())
    await interaction.response.send_message(
        f"There are {amount} item(s) in stock.",
        ephemeral=True
    )


@client.tree.command(
    name="stockview",
    description="View all stock items",
    guild=discord.Object(id=GUILD_ID)
)
async def stockview(interaction: discord.Interaction):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message(
            "You are not allowed to use this command.",
            ephemeral=True
        )
        return

    stock_items = get_stock()

    if not stock_items:
        await interaction.response.send_message(
            "Stock is empty.",
            ephemeral=True
        )
        return

    # Discord message limit is 2000 chars, so split if needed
    text = "\n".join(stock_items)

    if len(text) <= 1900:
        await interaction.response.send_message(
            f"Current stock:\n```{text}```",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"Stock is too long to show in one message.\nTotal items: {len(stock_items)}",
            ephemeral=True
        )


client.run(TOKEN)
