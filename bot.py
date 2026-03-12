
import os
import time
import discord
from discord import app_commands

TOKEN = ""

GUILD_ID = 1478979867088523425
OWNER_ID = 742144460552536106
ADMIN_ROLE_ID = 1478983511380725850
PREMIUM_ROLE_ID = 1481062565810536631  # replace later
PREMIUM_STOCK_FILE = "premium_stock.txt"

STOCK_FILE = "stock.txt"
FREE_COOLDOWN_SECONDS = 300
PREMIUM_COOLDOWN_SECONDS = 120

cooldowns = {}


class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
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


def has_permission(member: discord.Member) -> bool:
    if member.id == OWNER_ID:
        return True
    return any(role.id == ADMIN_ROLE_ID for role in member.roles)


def get_cooldown_remaining(user_id: int, stock_type: str) -> int:
    key = (user_id, stock_type)

    if key not in cooldowns:
        return 0

    cooldown_time = FREE_COOLDOWN_SECONDS if stock_type == "free" else PREMIUM_COOLDOWN_SECONDS
    remaining = int(cooldown_time - (time.time() - cooldowns[key]))
    return max(0, remaining)


@client.event
async def on_ready():
    await client.change_presence(
        status=discord.Status.dnd,
        activity=discord.Game(name="discord.gg/sevvyfr")
    )
    print(f"Logged in as {client.user}")

def get_premium_stock():
    try:
        with open(PREMIUM_STOCK_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        return []


def save_premium_stock(lines):
    with open(PREMIUM_STOCK_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def has_premium(member: discord.Member) -> bool:
    return any(role.id == PREMIUM_ROLE_ID for role in member.roles)

@client.tree.command(
    name="gen",
    description="Generate an account",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(type="Choose stock type")
@app_commands.choices(type=[
    app_commands.Choice(name="Free", value="free"),
    app_commands.Choice(name="Premium", value="premium")
])
async def gen(interaction: discord.Interaction, type: app_commands.Choice[str]):

    user_id = interaction.user.id
    now = time.time()
    stock_type = type.value
    key = (user_id, stock_type)

    cooldown_time = FREE_COOLDOWN_SECONDS if stock_type == "free" else PREMIUM_COOLDOWN_SECONDS

    if key in cooldowns:
        remaining = int(cooldown_time - (now - cooldowns[key]))
        if remaining > 0:
            await interaction.response.send_message(
                f"You're on {stock_type} cooldown. Try again in {format_time(remaining)}.",
                ephemeral=False
            )
            return

    # FREE GEN
    if stock_type == "free":
        stock = get_stock()

        if not stock:
            await interaction.response.send_message("Free stock is empty.", ephemeral=False)
            return

        item = stock.pop(0)
        save_stock(stock)

    # PREMIUM GEN
    else:
        if not isinstance(interaction.user, discord.Member) or not has_premium(interaction.user):
            await interaction.response.send_message(
                "You need the Premium role to use this.",
                ephemeral=False
            )
            return

        stock = get_premium_stock()

        if not stock:
            await interaction.response.send_message("Premium stock is empty.", ephemeral=False)
            return

        item = stock.pop(0)
        save_premium_stock(stock)

    try:
        await interaction.user.send(f"Your generated R6 account:\n`{item}`")
        cooldowns[key] = now

        embed = discord.Embed(
            title="Account Generated",
            description=f"Check your DMs for your {stock_type} account.",
            color=discord.Color.red()
        )
        embed.set_footer(text="Powered by @sevvyfr")

        await interaction.response.send_message(embed=embed, ephemeral=False)

    except discord.Forbidden:
        await interaction.response.send_message(
            "I couldn't DM you. Turn on DMs and try again.",
            ephemeral=False
        )
        
@client.tree.command(
    name="restock",
    description="Add items to free or premium stock",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    stock_type="Choose which stock to add to",
    items="Paste items separated by new lines"
)
@app_commands.choices(stock_type=[
    app_commands.Choice(name="Free", value="free"),
    app_commands.Choice(name="Premium", value="premium")
])
async def restock(
    interaction: discord.Interaction,
    stock_type: app_commands.Choice[str],
    items: str
):
    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        await interaction.response.send_message(
            "You are not allowed to use this command.",
            ephemeral=False
        )
        return

    new_items = [line.strip() for line in items.splitlines() if line.strip()]

    if not new_items:
        await interaction.response.send_message(
            "No valid strings were provided.",
            ephemeral=False
        )
        return

    if stock_type.value == "free":
        current_stock = get_stock()
        current_stock.extend(new_items)
        save_stock(current_stock)

        await interaction.response.send_message(
            f"Added {len(new_items)} item(s) to FREE stock. Total free stock: {len(current_stock)}",
            ephemeral=False
        )

    elif stock_type.value == "premium":
        current_stock = get_premium_stock()
        current_stock.extend(new_items)
        save_premium_stock(current_stock)

        await interaction.response.send_message(
            f"Added {len(new_items)} item(s) to PREMIUM stock. Total premium stock: {len(current_stock)}",
            ephemeral=False
        )


@client.tree.command(
    name="stock",
    description="See how many accounts are left in stock",
    guild=discord.Object(id=GUILD_ID)
)
async def stock(interaction: discord.Interaction):

    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = discord.Embed(
            title="Access Denied",
            description="You are not allowed to use this command.",
            color=discord.Color.red()
        )
        embed.set_footer(text="Powered by @sevvyfr")

        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    free_amount = len(get_stock())
    premium_amount = len(get_premium_stock())

    embed = discord.Embed(
        title="Stock Info",
        description="Current stock amounts are below.",
        color=discord.Color.red()
    )
    embed.add_field(name="Free Stock", value=str(free_amount), inline=False)
    embed.add_field(name="Premium Stock", value=str(premium_amount), inline=False)
    embed.set_footer(text="Powered by @sevvyfr")

    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="stockview",
    description="View all free or premium stock items",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(stock_type="Choose which stock to view")
@app_commands.choices(stock_type=[
    app_commands.Choice(name="Free", value="free"),
    app_commands.Choice(name="Premium", value="premium")
])
async def stockview(
    interaction: discord.Interaction,
    stock_type: app_commands.Choice[str]
):

    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = discord.Embed(
            title="Access Denied",
            description="You are not allowed to use this command.",
            color=discord.Color.red()
        )
        embed.set_footer(text="Powered by @sevvyfr")

        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if stock_type.value == "free":
        stock_items = get_stock()
        stock_name = "Free Stock"
    else:
        stock_items = get_premium_stock()
        stock_name = "Premium Stock"

    if not stock_items:
        embed = discord.Embed(
            title=f"{stock_name}",
            description="Stock is empty.",
            color=discord.Color.red()
        )
        embed.set_footer(text="Powered by @sevvyfr")

        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    text = "\n".join(stock_items)

    if len(text) <= 1900:
        embed = discord.Embed(
            title=stock_name,
            description=f"
{text}
",
            color=discord.Color.red()
        )
        embed.set_footer(text="Powered by @sevvyfr")

        await interaction.response.send_message(embed=embed, ephemeral=False)
    else:
        embed = discord.Embed(
            title=stock_name,
            description=f"Stock too long to show.\nTotal items: **{len(stock_items)}**",
            color=discord.Color.red()
        )
        embed.set_footer(text="Powered by @sevvyfr")

        await interaction.response.send_message(embed=embed, ephemeral=False)

@client.tree.command(
    name="geninfo",
    description="View stock and cooldown info",
    guild=discord.Object(id=GUILD_ID)
)
@client.tree.command(
    name="geninfo",
    description="View stock and cooldown info",
    guild=discord.Object(id=GUILD_ID)
)
async def geninfo(interaction: discord.Interaction):

    free_stock_amount = len(get_stock())
    premium_stock_amount = len(get_premium_stock())

    free_remaining = get_cooldown_remaining(interaction.user.id, "free")
    premium_remaining = get_cooldown_remaining(interaction.user.id, "premium")

    free_cooldown_text = f"{format_time(free_remaining)} remaining" if free_remaining > 0 else "Ready now"
    premium_cooldown_text = f"{format_time(premium_remaining)} remaining" if premium_remaining > 0 else "Ready now"

    embed = discord.Embed(
        title="Gen Info",
        description="Your generator info.",
        color=discord.Color.red()
    )

    embed.add_field(name="Free Stock Left", value=str(free_stock_amount), inline=False)
    embed.add_field(name="Premium Stock Left", value=str(premium_stock_amount), inline=False)
    embed.add_field(name="Free Cooldown", value=free_cooldown_text, inline=False)
    embed.add_field(name="Premium Cooldown", value=premium_cooldown_text, inline=False)
    embed.set_footer(text="Powered by @sevvyfr")

    await interaction.response.send_message(embed=embed, ephemeral=False)

@client.tree.command(
    name="clearstock",
    description="Clear all items from stock",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(stock_type="Choose which stock to clear")
@app_commands.choices(stock_type=[
    app_commands.Choice(name="Free", value="free"),
    app_commands.Choice(name="Premium", value="premium")
])
async def clearstock(
    interaction: discord.Interaction,
    stock_type: app_commands.Choice[str]
):

    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = discord.Embed(
            title="Access Denied",
            description="You are not allowed to use this command.",
            color=discord.Color.red()
        )
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if stock_type.value == "free":
        save_stock([])
        embed = discord.Embed(
            title="Stock Cleared",
            description="Free stock has been cleared.",
            color=discord.Color.red()
        )
    else:
        save_premium_stock([])
        embed = discord.Embed(
            title="Stock Cleared",
            description="Premium stock has been cleared.",
            color=discord.Color.red()
        )

    embed.set_footer(text="Powered by @sevvyfr")
    await interaction.response.send_message(embed=embed, ephemeral=False)

@client.tree.command(
    name="restockfile",
    description="Add stock items from a .txt file",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    stock_type="Choose which stock to add to",
    file="Upload a .txt file with one item per line"
)
@app_commands.choices(stock_type=[
    app_commands.Choice(name="Free", value="free"),
    app_commands.Choice(name="Premium", value="premium")
])
async def restockfile(
    interaction: discord.Interaction,
    stock_type: app_commands.Choice[str],
    file: discord.Attachment
):
    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        await interaction.response.send_message(
            "You are not allowed to use this command.",
            ephemeral=False
        )
        return

    if not file.filename.endswith(".txt"):
        await interaction.response.send_message(
            "Only .txt files are allowed.",
            ephemeral=False
        )
        return

    try:
        file_bytes = await file.read()
        content = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        await interaction.response.send_message(
            "That file is not valid UTF-8 text.",
            ephemeral=False
        )
        return
    except Exception as e:
        await interaction.response.send_message(
            f"Failed to read file: {e}",
            ephemeral=False
        )
        return

    new_items = [line.strip() for line in content.splitlines() if line.strip()]

    if not new_items:
        await interaction.response.send_message(
            "The file is empty or has no valid lines.",
            ephemeral=False
        )
        return

    if stock_type.value == "free":
        current_stock = get_stock()
        current_stock.extend(new_items)
        save_stock(current_stock)

        embed = discord.Embed(
            title="Free Stock Restocked",
            description=f"Added **{len(new_items)}** item(s) from `{file.filename}`.",
            color=discord.Color.red()
        )
        embed.add_field(name="Total Free Stock", value=str(len(current_stock)), inline=False)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.response.send_message(embed=embed, ephemeral=False)

    else:
        current_stock = get_premium_stock()
        current_stock.extend(new_items)
        save_premium_stock(current_stock)

        embed = discord.Embed(
            title="Premium Stock Restocked",
            description=f"Added **{len(new_items)}** item(s) from `{file.filename}`.",
            color=discord.Color.red()
        )
        embed.add_field(name="Total Premium Stock", value=str(len(current_stock)), inline=False)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.response.send_message(embed=embed, ephemeral=False)

@client.tree.command(
    name="setcooldown",
    description="Change the free or premium cooldown in seconds",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    stock_type="Choose which cooldown to change",
    seconds="New cooldown in seconds"
)
@app_commands.choices(stock_type=[
    app_commands.Choice(name="Free", value="free"),
    app_commands.Choice(name="Premium", value="premium")
])
async def setcooldown(
    interaction: discord.Interaction,
    stock_type: app_commands.Choice[str],
    seconds: int
):
    global FREE_COOLDOWN_SECONDS, PREMIUM_COOLDOWN_SECONDS

    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = discord.Embed(
            title="Access Denied",
            description="You are not allowed to use this command.",
            color=discord.Color.red()
        )
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if seconds < 0:
        await interaction.response.send_message(
            "Cooldown must be 0 or higher.",
            ephemeral=False
        )
        return

    if stock_type.value == "free":
        FREE_COOLDOWN_SECONDS = seconds
        message = f"Free cooldown is now **{FREE_COOLDOWN_SECONDS}** seconds."
    else:
        PREMIUM_COOLDOWN_SECONDS = seconds
        message = f"Premium cooldown is now **{PREMIUM_COOLDOWN_SECONDS}** seconds."

    embed = discord.Embed(
        title="Cooldown Updated",
        description=message,
        color=discord.Color.red()
    )
    embed.set_footer(text="Powered by @sevvyfr")

    await interaction.response.send_message(embed=embed, ephemeral=False)

client.run(TOKEN)
