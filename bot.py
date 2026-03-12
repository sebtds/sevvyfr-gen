
import os
import time
import discord
from discord import app_commands

TOKEN = os.getenv("TOKEN")

GUILD_ID = 1478979867088523425
OWNER_ID = 742144460552536106
ADMIN_ROLE_ID = 1478983511380725850
PREMIUM_ROLE_ID = 1481062565810536631  # replace later
PREMIUM_STOCK_FILE = "premium_stock.txt"

BLACKLIST_FILE = "blacklist.txt"
STOCK_FILE = "stock.txt"
FREE_COOLDOWN_SECONDS = 300
PREMIUM_COOLDOWN_SECONDS = 120
EMBED_THUMBNAIL = "https://i1.sndcdn.com/artworks-S9Zqk2YaTDjBEdlI-WxqcPw-t500x500.jpg"

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

def get_blacklist():
    try:
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            user_ids = set()
            for line in f.readlines():
                line = line.strip()
                if line and line.isdigit():
                    user_ids.add(int(line))
            return user_ids
    except FileNotFoundError:
        return set()

def save_blacklist(user_ids):
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(str(user_id) for user_id in user_ids))

blacklisted_users = get_blacklist()

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
    await interaction.response.defer(ephemeral=False)

    if interaction.user.id in blacklisted_users:
        embed = discord.Embed(
            title="Access Denied",
            description="You are blacklisted from using this bot.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.followup.send(embed=embed)
        return

    user_id = interaction.user.id
    now = time.time()
    stock_type = type.value
    key = (user_id, stock_type)

    cooldown_time = FREE_COOLDOWN_SECONDS if stock_type == "free" else PREMIUM_COOLDOWN_SECONDS

    if key in cooldowns:
        remaining = int(cooldown_time - (now - cooldowns[key]))
        if remaining > 0:
            embed = discord.Embed(
                title="Cooldown Active",
                description=f"You're on {stock_type} cooldown. Try again in {format_time(remaining)}.",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=EMBED_THUMBNAIL)
            embed.set_footer(text="Powered by @sevvyfr")
            await interaction.followup.send(embed=embed)
            return

    if stock_type == "free":
        stock = get_stock()

        if not stock:
            embed = discord.Embed(
                title="Out of Stock",
                description="Free stock is empty.",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=EMBED_THUMBNAIL)
            embed.set_footer(text="Powered by @sevvyfr")
            await interaction.followup.send(embed=embed)
            return

        item = stock.pop(0)
        save_stock(stock)

    else:
        if not isinstance(interaction.user, discord.Member) or not has_premium(interaction.user):
            embed = discord.Embed(
                title="Access Denied",
                description="You need the Premium role to use this.",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=EMBED_THUMBNAIL)
            embed.set_footer(text="Powered by @sevvyfr")
            await interaction.followup.send(embed=embed)
            return

        stock = get_premium_stock()

        if not stock:
            embed = discord.Embed(
                title="Out of Stock",
                description="Premium stock is empty.",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=EMBED_THUMBNAIL)
            embed.set_footer(text="Powered by @sevvyfr")
            await interaction.followup.send(embed=embed)
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
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.followup.send(embed=embed)

    except discord.Forbidden:
        embed = discord.Embed(
            title="DM Failed",
            description="I couldn't DM you. Turn on DMs and try again.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.followup.send(embed=embed)

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
        embed = discord.Embed(
            title="Access Denied",
            description="You are not allowed to use this command.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")

        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    new_items = [line.strip() for line in items.splitlines() if line.strip()]

    if not new_items:
        embed = discord.Embed(
            title="Restock Failed",
            description="No valid strings were provided.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")

        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if stock_type.value == "free":
        current_stock = get_stock()
        current_stock.extend(new_items)
        save_stock(current_stock)

        embed = discord.Embed(
            title="Free Stock Restocked",
            description=f"Added **{len(new_items)}** item(s) to FREE stock.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.add_field(name="Added", value=str(len(new_items)), inline=False)
        embed.add_field(name="Total Free Stock", value=str(len(current_stock)), inline=False)
        embed.set_footer(text="Powered by @sevvyfr")

        await interaction.response.send_message(embed=embed, ephemeral=False)

    elif stock_type.value == "premium":
        current_stock = get_premium_stock()
        current_stock.extend(new_items)
        save_premium_stock(current_stock)

        embed = discord.Embed(
            title="Premium Stock Restocked",
            description=f"Added **{len(new_items)}** item(s) to PREMIUM stock.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.add_field(name="Added", value=str(len(new_items)), inline=False)
        embed.add_field(name="Total Premium Stock", value=str(len(current_stock)), inline=False)
        embed.set_footer(text="Powered by @sevvyfr")

        await interaction.response.send_message(embed=embed, ephemeral=False)

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
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
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
    embed.set_thumbnail(url=EMBED_THUMBNAIL)
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
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
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
            title=stock_name,
            description="Stock is empty.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    text = "\n".join(stock_items)

    if len(text) <= 1900:
        embed = discord.Embed(
            title=stock_name,
            description=f"```{text}```",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.response.send_message(embed=embed, ephemeral=False)
    else:
        embed = discord.Embed(
            title=stock_name,
            description=f"Stock too long to show.\nTotal items: **{len(stock_items)}**",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.response.send_message(embed=embed, ephemeral=False)

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
    embed.set_thumbnail(url=EMBED_THUMBNAIL)
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
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
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
    embed.set_thumbnail(url=EMBED_THUMBNAIL)
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
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
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
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
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
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
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
    embed.set_thumbnail(url=EMBED_THUMBNAIL)
    embed.set_footer(text="Powered by @sevvyfr")

    await interaction.response.send_message(embed=embed, ephemeral=False)

@client.tree.command(
    name="help",
    description="Show all bot commands",
    guild=discord.Object(id=GUILD_ID)
)
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Bot Commands",
        description="List of available commands.",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=EMBED_THUMBNAIL)

    embed.add_field(
        name="Generator",
        value=(
            "`/gen` - Generate an account\n"
            "`/geninfo` - View stock and cooldown info"
        ),
        inline=False
    )

    embed.add_field(
        name="Stock",
        value=(
            "`/restock` - Add stock by text\n"
            "`/restockfile` - Add stock by .txt file\n"
            "`/stock` - View stock amounts\n"
            "`/stockview` - View all stock items\n"
            "`/clearstock` - Clear stock"
        ),
        inline=False
    )

    embed.add_field(
        name="Admin",
        value=(
            "`/setcooldown` - Change free or premium cooldown\n"
            "`/setstatus` - Change bot status text\n"
            "`/blacklist` - Blacklist a user\n"
            "`/unblacklist` - Remove a user from blacklist"
            "`/viewblacklist` - View blacklisted users\n"
            "`/clearblacklist` - Clear the blacklist\n"
            "`/removestock` - Remove items from stock\n"
            "`/resetcooldown` - Reset one user's cooldown\n"
            "`/clearcooldowns` - Clear all cooldowns\n"
            "`/botinfo` - View bot info\n"
            "`/removeduplicates` - Remove duplicate stock items\n"
        ),
        inline=False
    )

    embed.add_field(
        name="Other",
        value="`/help` - Show this message",
        inline=False
    )
    embed.set_thumbnail(url=EMBED_THUMBNAIL)
    embed.set_footer(text="Powered by @sevvyfr")
    await interaction.response.send_message(embed=embed, ephemeral=False)

@client.tree.command(
    name="setstatus",
    description="Change the bot status text",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(status_text="The text to show in the bot status")
async def setstatus(interaction: discord.Interaction, status_text: str):
    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = discord.Embed(
            title="Access Denied",
            description="You are not allowed to use this command.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    await client.change_presence(
        status=discord.Status.dnd,
        activity=discord.Game(name=status_text)
    )

    embed = discord.Embed(
        title="Status Updated",
        description=f"Bot status changed to:\n`{status_text}`",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=EMBED_THUMBNAIL)
    embed.set_footer(text="Powered by @sevvyfr")
    await interaction.response.send_message(embed=embed, ephemeral=False)
    
@client.tree.command(
    name="blacklist",
    description="Blacklist a user from using the generator",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(user="User to blacklist")
async def blacklist(interaction: discord.Interaction, user: discord.Member):
    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = discord.Embed(
            title="Access Denied",
            description="You are not allowed to use this command.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if user.id in blacklisted_users:
        embed = discord.Embed(
            title="Already Blacklisted",
            description=f"{user.mention} is already blacklisted.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    blacklisted_users.add(user.id)
    save_blacklist(blacklisted_users)

    embed = discord.Embed(
        title="User Blacklisted",
        description=f"{user.mention} has been blacklisted.",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=EMBED_THUMBNAIL)
    embed.set_footer(text="Powered by @sevvyfr")
    await interaction.response.send_message(embed=embed, ephemeral=False)

@client.tree.command(
    name="unblacklist",
    description="Remove a user from the blacklist",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(user="User to remove from blacklist")
async def unblacklist(interaction: discord.Interaction, user: discord.Member):
    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = discord.Embed(
            title="Access Denied",
            description="You are not allowed to use this command.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if user.id not in blacklisted_users:
        embed = discord.Embed(
            title="Not Blacklisted",
            description=f"{user.mention} is not blacklisted.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    blacklisted_users.remove(user.id)
    save_blacklist(blacklisted_users)

    embed = discord.Embed(
        title="User Unblacklisted",
        description=f"{user.mention} has been removed from the blacklist.",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=EMBED_THUMBNAIL)
    embed.set_footer(text="Powered by @sevvyfr")
    await interaction.response.send_message(embed=embed, ephemeral=False)

@client.tree.command(
    name="viewblacklist",
    description="View all blacklisted users",
    guild=discord.Object(id=GUILD_ID)
)
async def viewblacklist(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)

    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = discord.Embed(
            title="Access Denied",
            description="You are not allowed to use this command.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.followup.send(embed=embed)
        return

    if not blacklisted_users:
        embed = discord.Embed(
            title="Blacklist",
            description="No users are blacklisted.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.followup.send(embed=embed)
        return

    lines = []

    for user_id in blacklisted_users:
        member = interaction.guild.get_member(user_id)

        if member is None:
            try:
                member = await interaction.guild.fetch_member(user_id)
            except discord.NotFound:
                member = None
            except discord.Forbidden:
                member = None
            except discord.HTTPException:
                member = None

        if member:
            lines.append(f"{member.display_name} (@{member.name})")
        else:
            lines.append(f"Unknown User ({user_id})")

    text = "\n".join(lines)

    if len(text) > 1900:
        embed = discord.Embed(
            title="Blacklist",
            description=f"Too many users to show.\nTotal blacklisted: **{len(blacklisted_users)}**",
            color=discord.Color.red()
        )
    else:
        embed = discord.Embed(
            title="Blacklist",
            description=text,
            color=discord.Color.red()
        )

    embed.set_thumbnail(url=EMBED_THUMBNAIL)
    embed.set_footer(text="Powered by @sevvyfr")
    await interaction.followup.send(embed=embed)


@client.tree.command(
    name="clearblacklist",
    description="Clear the entire blacklist",
    guild=discord.Object(id=GUILD_ID)
)
async def clearblacklist(interaction: discord.Interaction):
    global blacklisted_users

    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = discord.Embed(
            title="Access Denied",
            description="You are not allowed to use this command.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    cleared_count = len(blacklisted_users)
    blacklisted_users.clear()
    save_blacklist(blacklisted_users)

    embed = discord.Embed(
        title="Blacklist Cleared",
        description=f"Cleared **{cleared_count}** blacklisted user(s).",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=EMBED_THUMBNAIL)
    embed.set_footer(text="Powered by @sevvyfr")
    await interaction.response.send_message(embed=embed, ephemeral=False)

@client.tree.command(
    name="removestock",
    description="Remove items from free or premium stock",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    stock_type="Choose which stock to remove from",
    amount="How many items to remove"
)
@app_commands.choices(stock_type=[
    app_commands.Choice(name="Free", value="free"),
    app_commands.Choice(name="Premium", value="premium")
])
async def removestock(
    interaction: discord.Interaction,
    stock_type: app_commands.Choice[str],
    amount: int
):
    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = discord.Embed(
            title="Access Denied",
            description="You are not allowed to use this command.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if amount <= 0:
        embed = discord.Embed(
            title="Invalid Amount",
            description="Amount must be greater than 0.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if stock_type.value == "free":
        stock = get_stock()

        if not stock:
            embed = discord.Embed(
                title="Free Stock",
                description="Free stock is already empty.",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=EMBED_THUMBNAIL)
            embed.set_footer(text="Powered by @sevvyfr")
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        removed_amount = min(amount, len(stock))
        stock = stock[removed_amount:]
        save_stock(stock)

        embed = discord.Embed(
            title="Free Stock Updated",
            description=f"Removed **{removed_amount}** item(s) from free stock.",
            color=discord.Color.red()
        )
        embed.add_field(name="Free Stock Left", value=str(len(stock)), inline=False)

    else:
        stock = get_premium_stock()

        if not stock:
            embed = discord.Embed(
                title="Premium Stock",
                description="Premium stock is already empty.",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=EMBED_THUMBNAIL)
            embed.set_footer(text="Powered by @sevvyfr")
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        removed_amount = min(amount, len(stock))
        stock = stock[removed_amount:]
        save_premium_stock(stock)

        embed = discord.Embed(
            title="Premium Stock Updated",
            description=f"Removed **{removed_amount}** item(s) from premium stock.",
            color=discord.Color.red()
        )
        embed.add_field(name="Premium Stock Left", value=str(len(stock)), inline=False)

    embed.set_thumbnail(url=EMBED_THUMBNAIL)
    embed.set_footer(text="Powered by @sevvyfr")
    await interaction.response.send_message(embed=embed, ephemeral=False)

@client.tree.command(
    name="clearcooldowns",
    description="Clear all active cooldowns",
    guild=discord.Object(id=GUILD_ID)
)
async def clearcooldowns(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = discord.Embed(
            title="Access Denied",
            description="You are not allowed to use this command.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    cleared_count = len(cooldowns)
    cooldowns.clear()

    embed = discord.Embed(
        title="Cooldowns Cleared",
        description=f"Cleared **{cleared_count}** active cooldown(s).",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=EMBED_THUMBNAIL)
    embed.set_footer(text="Powered by @sevvyfr")
    await interaction.response.send_message(embed=embed, ephemeral=False)
    
@client.tree.command(
    name="botinfo",
    description="View bot info, stock, cooldowns, and blacklist count",
    guild=discord.Object(id=GUILD_ID)
)
async def botinfo(interaction: discord.Interaction):
    free_stock = len(get_stock())
    premium_stock = len(get_premium_stock())
    blacklist_count = len(blacklisted_users)
    cooldown_count = len(cooldowns)
    ping_ms = round(client.latency * 1000)

    embed = discord.Embed(
        title="Bot Info",
        description="Current bot information.",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=EMBED_THUMBNAIL)
    embed.add_field(name="Ping", value=f"{ping_ms}ms", inline=False)
    embed.add_field(name="Free Stock", value=str(free_stock), inline=False)
    embed.add_field(name="Premium Stock", value=str(premium_stock), inline=False)
    embed.add_field(name="Free Cooldown", value=f"{FREE_COOLDOWN_SECONDS}s", inline=False)
    embed.add_field(name="Premium Cooldown", value=f"{PREMIUM_COOLDOWN_SECONDS}s", inline=False)
    embed.add_field(name="Active Cooldowns", value=str(cooldown_count), inline=False)
    embed.add_field(name="Blacklisted Users", value=str(blacklist_count), inline=False)
    embed.set_footer(text="Powered by @sevvyfr")

    await interaction.response.send_message(embed=embed, ephemeral=False)

@client.tree.command(
    name="removeduplicates",
    description="Remove duplicate items from free or premium stock",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(stock_type="Choose which stock to clean")
@app_commands.choices(stock_type=[
    app_commands.Choice(name="Free", value="free"),
    app_commands.Choice(name="Premium", value="premium")
])
async def removeduplicates(
    interaction: discord.Interaction,
    stock_type: app_commands.Choice[str]
):
    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = discord.Embed(
            title="Access Denied",
            description="You are not allowed to use this command.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(text="Powered by @sevvyfr")
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if stock_type.value == "free":
        stock = get_stock()
        original_count = len(stock)
        cleaned_stock = list(dict.fromkeys(stock))
        removed_count = original_count - len(cleaned_stock)
        save_stock(cleaned_stock)

        embed = discord.Embed(
            title="Free Stock Cleaned",
            description=f"Removed **{removed_count}** duplicate item(s).",
            color=discord.Color.red()
        )
        embed.add_field(name="Free Stock Left", value=str(len(cleaned_stock)), inline=False)

    else:
        stock = get_premium_stock()
        original_count = len(stock)
        cleaned_stock = list(dict.fromkeys(stock))
        removed_count = original_count - len(cleaned_stock)
        save_premium_stock(cleaned_stock)

        embed = discord.Embed(
            title="Premium Stock Cleaned",
            description=f"Removed **{removed_count}** duplicate item(s).",
            color=discord.Color.red()
        )
        embed.add_field(name="Premium Stock Left", value=str(len(cleaned_stock)), inline=False)

    embed.set_thumbnail(url=EMBED_THUMBNAIL)
    embed.set_footer(text="Powered by @sevvyfr")
    await interaction.response.send_message(embed=embed, ephemeral=False)

client.run(TOKEN)
