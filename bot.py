import os
import json
import time
import datetime

import discord
from discord import app_commands

TOKEN = os.getenv("TOKEN")

GUILD_ID = 1478979867088523425
OWNER_ID = 742144460552536106
ADMIN_ROLE_ID = 1478983511380725850
PREMIUM_ROLE_ID = 1481062565810536631
PREMIUM_STOCK_FILE = "premium_stock.txt"

BLACKLIST_FILE = "blacklist.txt"
STOCK_FILE = "stock.txt"
EMBED_SETTINGS_FILE = "embed_settings.json"
FREE_COOLDOWN_SECONDS = 300
PREMIUM_COOLDOWN_SECONDS = 120

DEFAULT_EMBED_THUMBNAIL = "https://i1.sndcdn.com/artworks-S9Zqk2YaTDjBEdlI-WxqcPw-t500x500.jpg"
DEFAULT_EMBED_COLOR = 0xED4245
DEFAULT_EMBED_FOOTER = "Powered by @sevvyfr"

EMBED_THUMBNAIL = DEFAULT_EMBED_THUMBNAIL
EMBED_COLOR = discord.Color(DEFAULT_EMBED_COLOR)
EMBED_FOOTER = DEFAULT_EMBED_FOOTER

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


def create_embed(title: str, description: str, style: str = "info") -> discord.Embed:
    styles = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "📌",
        "stock": "📦",
        "user": "👤",
        "admin": "🛠️",
        "cooldown": "⏳",
        "premium": "💎",
        "gen": "🎮",
        "settings": "⚙️",
        "blacklist": "🚫"
    }

    emoji = styles.get(style, "📌")

    embed = discord.Embed(
        title=f"{emoji} {title}",
        description=description,
        color=EMBED_COLOR,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_author(name="Sevvy Generator", icon_url=EMBED_THUMBNAIL)
    embed.set_thumbnail(url=EMBED_THUMBNAIL)
    embed.set_footer(text=EMBED_FOOTER)
    return embed


def get_stock():
    try:
        with open(STOCK_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        return []


def save_stock(lines):
    with open(STOCK_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def get_premium_stock():
    try:
        with open(PREMIUM_STOCK_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        return []


def save_premium_stock(lines):
    with open(PREMIUM_STOCK_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


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


def load_embed_settings():
    global EMBED_THUMBNAIL, EMBED_COLOR, EMBED_FOOTER

    try:
        with open(EMBED_SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        color_value = data.get("color", DEFAULT_EMBED_COLOR)
        footer_value = data.get("footer", DEFAULT_EMBED_FOOTER)
        thumbnail_value = data.get("thumbnail", DEFAULT_EMBED_THUMBNAIL)

        EMBED_COLOR = discord.Color(int(color_value))
        EMBED_FOOTER = str(footer_value)
        EMBED_THUMBNAIL = str(thumbnail_value)

    except (FileNotFoundError, json.JSONDecodeError, ValueError, TypeError):
        EMBED_COLOR = discord.Color(DEFAULT_EMBED_COLOR)
        EMBED_FOOTER = DEFAULT_EMBED_FOOTER
        EMBED_THUMBNAIL = DEFAULT_EMBED_THUMBNAIL


def save_embed_settings():
    with open(EMBED_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "color": EMBED_COLOR.value,
                "footer": EMBED_FOOTER,
                "thumbnail": EMBED_THUMBNAIL
            },
            f,
            indent=4
        )


def save_blacklist(user_ids):
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(str(user_id) for user_id in user_ids))


blacklisted_users = get_blacklist()
load_embed_settings()


def format_time(seconds):
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}m {secs}s"


def has_permission(member: discord.Member) -> bool:
    if member.id == OWNER_ID:
        return True
    return any(role.id == ADMIN_ROLE_ID for role in member.roles)


def has_premium(member: discord.Member) -> bool:
    return any(role.id == PREMIUM_ROLE_ID for role in member.roles)


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
        embed = create_embed(
            "Access Denied",
            "You are blacklisted from using this bot.",
            "blacklist"
        )
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
            embed = create_embed(
                "Cooldown Active",
                f"You're on {stock_type} cooldown. Try again in {format_time(remaining)}.",
                "cooldown"
            )
            await interaction.followup.send(embed=embed)
            return

    if stock_type == "free":
        stock = get_stock()

        if not stock:
            embed = create_embed(
                "Out of Stock",
                "Free stock is empty.",
                "stock"
            )
            await interaction.followup.send(embed=embed)
            return

        item = stock.pop(0)
        save_stock(stock)

    else:
        if not isinstance(interaction.user, discord.Member) or not has_premium(interaction.user):
            embed = create_embed(
                "Access Denied",
                "You need the Premium role to use this.",
                "premium"
            )
            await interaction.followup.send(embed=embed)
            return

        stock = get_premium_stock()

        if not stock:
            embed = create_embed(
                "Out of Stock",
                "Premium stock is empty.",
                "premium"
            )
            await interaction.followup.send(embed=embed)
            return

        item = stock.pop(0)
        save_premium_stock(stock)

    try:
        await interaction.user.send(f"Your generated R6 account:\n`{item}`")
        cooldowns[key] = now

        free_stock = len(get_stock())
        premium_stock = len(get_premium_stock())

        embed = create_embed(
            "Account Generated",
            f"Check your DMs for your {stock_type} account.",
            "gen"
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="🎟 Type", value=stock_type.title(), inline=True)
        embed.add_field(name="📦 Free Stock", value=str(free_stock), inline=True)
        embed.add_field(name="💎 Premium Stock", value=str(premium_stock), inline=True)
        embed.add_field(name="👤 Requested By", value=interaction.user.mention, inline=False)

        await interaction.followup.send(embed=embed)

    except discord.Forbidden:
        embed = create_embed(
            "DM Failed",
            "I couldn't DM you. Turn on DMs and try again.",
            "error"
        )
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
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    new_items = [line.strip() for line in items.splitlines() if line.strip()]

    if not new_items:
        embed = create_embed(
            "Restock Failed",
            "No valid strings were provided.",
            "warning"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if stock_type.value == "free":
        current_stock = get_stock()
        current_stock.extend(new_items)
        save_stock(current_stock)

        embed = create_embed(
            "Free Stock Restocked",
            f"Added **{len(new_items)}** item(s) to FREE stock.",
            "stock"
        )
        embed.add_field(name="📥 Added", value=str(len(new_items)), inline=False)
        embed.add_field(name="📦 Total Free Stock", value=str(len(current_stock)), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    else:
        current_stock = get_premium_stock()
        current_stock.extend(new_items)
        save_premium_stock(current_stock)

        embed = create_embed(
            "Premium Stock Restocked",
            f"Added **{len(new_items)}** item(s) to PREMIUM stock.",
            "premium"
        )
        embed.add_field(name="📥 Added", value=str(len(new_items)), inline=False)
        embed.add_field(name="💎 Total Premium Stock", value=str(len(current_stock)), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="stock",
    description="See how many accounts are left in stock",
    guild=discord.Object(id=GUILD_ID)
)
async def stock(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    free_amount = len(get_stock())
    premium_amount = len(get_premium_stock())

    embed = create_embed(
        "Stock Info",
        "Current stock amounts are below.",
        "stock"
    )
    embed.add_field(name="📦 Free Stock", value=str(free_amount), inline=False)
    embed.add_field(name="💎 Premium Stock", value=str(premium_amount), inline=False)

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
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if stock_type.value == "free":
        stock_items = get_stock()
        stock_name = "Free Stock"
        style = "stock"
    else:
        stock_items = get_premium_stock()
        stock_name = "Premium Stock"
        style = "premium"

    if not stock_items:
        embed = create_embed(
            stock_name,
            "Stock is empty.",
            style
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    text = "\n".join(stock_items)

    if len(text) <= 1900:
        embed = create_embed(
            stock_name,
            f"```{text}```",
            style
        )
    else:
        embed = create_embed(
            stock_name,
            f"Stock too long to show.\nTotal items: **{len(stock_items)}**",
            style
        )

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

    embed = create_embed(
        "Gen Info",
        "Your generator info.",
        "info"
    )
    embed.add_field(name="📦 Free Stock Left", value=str(free_stock_amount), inline=False)
    embed.add_field(name="💎 Premium Stock Left", value=str(premium_stock_amount), inline=False)
    embed.add_field(name="⏳ Free Cooldown", value=free_cooldown_text, inline=False)
    embed.add_field(name="⏳ Premium Cooldown", value=premium_cooldown_text, inline=False)

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
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if stock_type.value == "free":
        save_stock([])
        embed = create_embed(
            "Stock Cleared",
            "Free stock has been cleared.",
            "stock"
        )
    else:
        save_premium_stock([])
        embed = create_embed(
            "Stock Cleared",
            "Premium stock has been cleared.",
            "premium"
        )

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
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if not file.filename.endswith(".txt"):
        embed = create_embed(
            "Invalid File",
            "Only .txt files are allowed.",
            "warning"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    try:
        file_bytes = await file.read()
        content = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        embed = create_embed(
            "Invalid File",
            "That file is not valid UTF-8 text.",
            "warning"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return
    except Exception as e:
        embed = create_embed(
            "Read Failed",
            f"Failed to read file: {e}",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    new_items = [line.strip() for line in content.splitlines() if line.strip()]

    if not new_items:
        embed = create_embed(
            "Empty File",
            "The file is empty or has no valid lines.",
            "warning"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if stock_type.value == "free":
        current_stock = get_stock()
        current_stock.extend(new_items)
        save_stock(current_stock)

        embed = create_embed(
            "Free Stock Restocked",
            f"Added **{len(new_items)}** item(s) from `{file.filename}`.",
            "stock"
        )
        embed.add_field(name="📦 Total Free Stock", value=str(len(current_stock)), inline=False)
    else:
        current_stock = get_premium_stock()
        current_stock.extend(new_items)
        save_premium_stock(current_stock)

        embed = create_embed(
            "Premium Stock Restocked",
            f"Added **{len(new_items)}** item(s) from `{file.filename}`.",
            "premium"
        )
        embed.add_field(name="💎 Total Premium Stock", value=str(len(current_stock)), inline=False)

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
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if seconds < 0:
        embed = create_embed(
            "Invalid Cooldown",
            "Cooldown must be 0 or higher.",
            "warning"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if stock_type.value == "free":
        FREE_COOLDOWN_SECONDS = seconds
        message = f"Free cooldown is now **{FREE_COOLDOWN_SECONDS}** seconds."
    else:
        PREMIUM_COOLDOWN_SECONDS = seconds
        message = f"Premium cooldown is now **{PREMIUM_COOLDOWN_SECONDS}** seconds."

    embed = create_embed(
        "Cooldown Updated",
        message,
        "settings"
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="help",
    description="Show all bot commands",
    guild=discord.Object(id=GUILD_ID)
)
async def help_command(interaction: discord.Interaction):
    embed = create_embed(
        "Bot Commands",
        "List of available commands.",
        "info"
    )

    embed.add_field(
        name="🎮 Generator",
        value=(
            "`/gen` - Generate an account\n"
            "`/geninfo` - View stock and cooldown info"
        ),
        inline=False
    )

    embed.add_field(
        name="📦 Stock",
        value=(
            "`/restock` - Add stock by text\n"
            "`/restockfile` - Add stock by .txt file\n"
            "`/stock` - View stock amounts\n"
            "`/stockview` - View all stock items\n"
            "`/clearstock` - Clear stock\n"
            "`/removestock` - Remove items from stock\n"
            "`/removeitem` - Remove one exact item\n"
            "`/removeduplicates` - Remove duplicate stock items"
        ),
        inline=False
    )

    embed.add_field(
        name="🛠️ Admin",
        value=(
            "`/setcooldown` - Change free or premium cooldown\n"
            "`/resetcooldown` - Reset one user's cooldown\n"
            "`/clearcooldowns` - Clear all cooldowns\n"
            "`/setstatus` - Change bot status text\n"
            "`/blacklist` - Blacklist a user\n"
            "`/unblacklist` - Remove a user from blacklist\n"
            "`/viewblacklist` - View blacklisted users\n"
            "`/clearblacklist` - Clear the blacklist\n"
            "`/checkuser` - Check a user's status\n"
            "`/botinfo` - View bot info\n"
            "`/setembedcolor` - Change embed color\n"
            "`/setfooter` - Change footer text\n"
            "`/setthumbnail` - Change thumbnail"
        ),
        inline=False
    )

    embed.add_field(
        name="📌 Other",
        value="`/help` - Show this message",
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="setstatus",
    description="Change the bot status text",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(status_text="The text to show in the bot status")
async def setstatus(interaction: discord.Interaction, status_text: str):
    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    await client.change_presence(
        status=discord.Status.dnd,
        activity=discord.Game(name=status_text)
    )

    embed = create_embed(
        "Status Updated",
        f"Bot status changed to:\n`{status_text}`",
        "settings"
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="blacklist",
    description="Blacklist a user from using the generator",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(user="User to blacklist")
async def blacklist(interaction: discord.Interaction, user: discord.Member):
    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if user.id in blacklisted_users:
        embed = create_embed(
            "Already Blacklisted",
            f"{user.mention} is already blacklisted.",
            "blacklist"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    blacklisted_users.add(user.id)
    save_blacklist(blacklisted_users)

    embed = create_embed(
        "User Blacklisted",
        f"{user.mention} has been blacklisted.",
        "blacklist"
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="unblacklist",
    description="Remove a user from the blacklist",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(user="User to remove from blacklist")
async def unblacklist(interaction: discord.Interaction, user: discord.Member):
    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if user.id not in blacklisted_users:
        embed = create_embed(
            "Not Blacklisted",
            f"{user.mention} is not blacklisted.",
            "blacklist"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    blacklisted_users.remove(user.id)
    save_blacklist(blacklisted_users)

    embed = create_embed(
        "User Unblacklisted",
        f"{user.mention} has been removed from the blacklist.",
        "blacklist"
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="viewblacklist",
    description="View all blacklisted users",
    guild=discord.Object(id=GUILD_ID)
)
async def viewblacklist(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)

    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.followup.send(embed=embed)
        return

    if not blacklisted_users:
        embed = create_embed(
            "Blacklist",
            "No users are blacklisted.",
            "blacklist"
        )
        await interaction.followup.send(embed=embed)
        return

    lines = []

    for user_id in blacklisted_users:
        member = interaction.guild.get_member(user_id)

        if member is None:
            try:
                member = await interaction.guild.fetch_member(user_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                member = None

        if member:
            lines.append(f"{member.display_name} (@{member.name})")
        else:
            lines.append(f"Unknown User ({user_id})")

    text = "\n".join(lines)

    if len(text) > 1900:
        embed = create_embed(
            "Blacklist",
            f"Too many users to show.\nTotal blacklisted: **{len(blacklisted_users)}**",
            "blacklist"
        )
    else:
        embed = create_embed(
            "Blacklist",
            text,
            "blacklist"
        )

    await interaction.followup.send(embed=embed)


@client.tree.command(
    name="clearblacklist",
    description="Clear the entire blacklist",
    guild=discord.Object(id=GUILD_ID)
)
async def clearblacklist(interaction: discord.Interaction):
    global blacklisted_users

    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    cleared_count = len(blacklisted_users)
    blacklisted_users.clear()
    save_blacklist(blacklisted_users)

    embed = create_embed(
        "Blacklist Cleared",
        f"Cleared **{cleared_count}** blacklisted user(s).",
        "blacklist"
    )
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
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if amount <= 0:
        embed = create_embed(
            "Invalid Amount",
            "Amount must be greater than 0.",
            "warning"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if stock_type.value == "free":
        stock = get_stock()

        if not stock:
            embed = create_embed(
                "Free Stock",
                "Free stock is already empty.",
                "stock"
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        removed_amount = min(amount, len(stock))
        stock = stock[removed_amount:]
        save_stock(stock)

        embed = create_embed(
            "Free Stock Updated",
            f"Removed **{removed_amount}** item(s) from free stock.",
            "stock"
        )
        embed.add_field(name="📦 Free Stock Left", value=str(len(stock)), inline=False)

    else:
        stock = get_premium_stock()

        if not stock:
            embed = create_embed(
                "Premium Stock",
                "Premium stock is already empty.",
                "premium"
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        removed_amount = min(amount, len(stock))
        stock = stock[removed_amount:]
        save_premium_stock(stock)

        embed = create_embed(
            "Premium Stock Updated",
            f"Removed **{removed_amount}** item(s) from premium stock.",
            "premium"
        )
        embed.add_field(name="💎 Premium Stock Left", value=str(len(stock)), inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="resetcooldown",
    description="Reset a user's free or premium cooldown",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    user="User to reset cooldown for",
    stock_type="Which cooldown to reset"
)
@app_commands.choices(stock_type=[
    app_commands.Choice(name="Free", value="free"),
    app_commands.Choice(name="Premium", value="premium")
])
async def resetcooldown(
    interaction: discord.Interaction,
    user: discord.Member,
    stock_type: app_commands.Choice[str]
):
    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    key = (user.id, stock_type.value)

    if key in cooldowns:
        del cooldowns[key]
        message = f"Reset {stock_type.value} cooldown for {user.mention}."
    else:
        message = f"{user.mention} had no active {stock_type.value} cooldown."

    embed = create_embed(
        "Cooldown Reset",
        message,
        "cooldown"
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="clearcooldowns",
    description="Clear all active cooldowns",
    guild=discord.Object(id=GUILD_ID)
)
async def clearcooldowns(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    cleared_count = len(cooldowns)
    cooldowns.clear()

    embed = create_embed(
        "Cooldowns Cleared",
        f"Cleared **{cleared_count}** active cooldown(s).",
        "cooldown"
    )
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

    embed = create_embed(
        "Bot Info",
        "Current bot information.",
        "info"
    )
    embed.add_field(name="📡 Ping", value=f"{ping_ms}ms", inline=False)
    embed.add_field(name="📦 Free Stock", value=str(free_stock), inline=False)
    embed.add_field(name="💎 Premium Stock", value=str(premium_stock), inline=False)
    embed.add_field(name="⏳ Free Cooldown", value=f"{FREE_COOLDOWN_SECONDS}s", inline=False)
    embed.add_field(name="⏳ Premium Cooldown", value=f"{PREMIUM_COOLDOWN_SECONDS}s", inline=False)
    embed.add_field(name="🧠 Active Cooldowns", value=str(cooldown_count), inline=False)
    embed.add_field(name="🚫 Blacklisted Users", value=str(blacklist_count), inline=False)

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
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if stock_type.value == "free":
        stock = get_stock()
        original_count = len(stock)
        cleaned_stock = list(dict.fromkeys(stock))
        removed_count = original_count - len(cleaned_stock)
        save_stock(cleaned_stock)

        embed = create_embed(
            "Free Stock Cleaned",
            f"Removed **{removed_count}** duplicate item(s).",
            "stock"
        )
        embed.add_field(name="📦 Free Stock Left", value=str(len(cleaned_stock)), inline=False)

    else:
        stock = get_premium_stock()
        original_count = len(stock)
        cleaned_stock = list(dict.fromkeys(stock))
        removed_count = original_count - len(cleaned_stock)
        save_premium_stock(cleaned_stock)

        embed = create_embed(
            "Premium Stock Cleaned",
            f"Removed **{removed_count}** duplicate item(s).",
            "premium"
        )
        embed.add_field(name="💎 Premium Stock Left", value=str(len(cleaned_stock)), inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="checkuser",
    description="Check a user's premium, blacklist, and cooldown status",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(user="User to check")
async def checkuser(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(ephemeral=False)

    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.followup.send(embed=embed)
        return

    is_user_premium = has_premium(user)
    is_user_blacklisted = user.id in blacklisted_users
    free_remaining = get_cooldown_remaining(user.id, "free")
    premium_remaining = get_cooldown_remaining(user.id, "premium")

    free_text = f"{format_time(free_remaining)} remaining" if free_remaining > 0 else "Ready now"
    premium_text = f"{format_time(premium_remaining)} remaining" if premium_remaining > 0 else "Ready now"

    embed = create_embed(
        "User Info",
        f"Info for {user.mention}",
        "user"
    )
    embed.add_field(name="👤 Username", value=f"{user.display_name} (@{user.name})", inline=False)
    embed.add_field(name="💎 Premium", value="Yes" if is_user_premium else "No", inline=False)
    embed.add_field(name="🚫 Blacklisted", value="Yes" if is_user_blacklisted else "No", inline=False)
    embed.add_field(name="⏳ Free Cooldown", value=free_text, inline=False)
    embed.add_field(name="⏳ Premium Cooldown", value=premium_text, inline=False)

    await interaction.followup.send(embed=embed)


@client.tree.command(
    name="setthumbnail",
    description="Change the embed thumbnail URL",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(url="Direct image URL for the thumbnail")
async def setthumbnail(interaction: discord.Interaction, url: str):
    global EMBED_THUMBNAIL

    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if not (url.startswith("http://") or url.startswith("https://")):
        embed = create_embed(
            "Invalid URL",
            "Thumbnail URL must start with http:// or https://",
            "warning"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    EMBED_THUMBNAIL = url
    save_embed_settings()

    embed = create_embed(
        "Thumbnail Updated",
        "The embed thumbnail has been updated.",
        "settings"
    )
    embed.set_thumbnail(url=EMBED_THUMBNAIL)
    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="setfooter",
    description="Change the embed footer text",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(text="New footer text")
async def setfooter(interaction: discord.Interaction, text: str):
    global EMBED_FOOTER

    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    EMBED_FOOTER = text
    save_embed_settings()

    embed = create_embed(
        "Footer Updated",
        f"New footer:\n`{EMBED_FOOTER}`",
        "settings"
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="setembedcolor",
    description="Change the embed color using a hex code",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(hex_color="Example: #ff0000 or ff0000")
async def setembedcolor(interaction: discord.Interaction, hex_color: str):
    global EMBED_COLOR

    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    hex_color = hex_color.strip().replace("#", "")

    if len(hex_color) != 6:
        embed = create_embed(
            "Invalid Color",
            "Hex color must be 6 characters long.",
            "warning"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    try:
        color_value = int(hex_color, 16)
    except ValueError:
        embed = create_embed(
            "Invalid Color",
            "That is not a valid hex color.",
            "warning"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    EMBED_COLOR = discord.Color(color_value)
    save_embed_settings()

    embed = create_embed(
        "Embed Color Updated",
        f"New embed color set to `#{hex_color.lower()}`.",
        "settings"
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="removeitem",
    description="Remove one exact item from free or premium stock",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    stock_type="Choose which stock to remove from",
    item="The exact item to remove"
)
@app_commands.choices(stock_type=[
    app_commands.Choice(name="Free", value="free"),
    app_commands.Choice(name="Premium", value="premium")
])
async def removeitem(
    interaction: discord.Interaction,
    stock_type: app_commands.Choice[str],
    item: str
):
    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return

    if stock_type.value == "free":
        stock = get_stock()

        if item not in stock:
            embed = create_embed(
                "Item Not Found",
                "That item was not found in free stock.",
                "warning"
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        stock.remove(item)
        save_stock(stock)

        embed = create_embed(
            "Item Removed",
            "Removed item from free stock.",
            "stock"
        )
        embed.add_field(name="📦 Free Stock Left", value=str(len(stock)), inline=False)

    else:
        stock = get_premium_stock()

        if item not in stock:
            embed = create_embed(
                "Item Not Found",
                "That item was not found in premium stock.",
                "warning"
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        stock.remove(item)
        save_premium_stock(stock)

        embed = create_embed(
            "Item Removed",
            "Removed item from premium stock.",
            "premium"
        )
        embed.add_field(name="💎 Premium Stock Left", value=str(len(stock)), inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=False)

class AdminDashboardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
            embed = create_embed(
                "Access Denied",
                "You are not allowed to use this dashboard.",
                "error"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    def build_dashboard_embed(self):
        free_stock = len(get_stock())
        premium_stock = len(get_premium_stock())
        blacklist_count = len(blacklisted_users)
        cooldown_count = len(cooldowns)
        ping_ms = round(client.latency * 1000)

        embed = create_embed(
            "Admin Dashboard",
            "Manage the bot with the buttons below.",
            "admin"
        )
        embed.add_field(name="📡 Ping", value=f"{ping_ms}ms", inline=True)
        embed.add_field(name="📦 Free Stock", value=str(free_stock), inline=True)
        embed.add_field(name="💎 Premium Stock", value=str(premium_stock), inline=True)
        embed.add_field(name="🚫 Blacklisted", value=str(blacklist_count), inline=True)
        embed.add_field(name="⏳ Active Cooldowns", value=str(cooldown_count), inline=True)
        embed.add_field(name="👑 Owner", value=f"<@{OWNER_ID}>", inline=True)
        return embed

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.primary, emoji="🔄", row=0)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.build_dashboard_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Clear Cooldowns", style=discord.ButtonStyle.secondary, emoji="🧹", row=0)
    async def clear_cooldowns_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cleared_count = len(cooldowns)
        cooldowns.clear()

        embed = self.build_dashboard_embed()
        embed.description = f"Cleared **{cleared_count}** cooldown(s)."

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Stock", style=discord.ButtonStyle.secondary, emoji="📦", row=0)
    async def stock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        free_stock = len(get_stock())
        premium_stock = len(get_premium_stock())

        embed = create_embed(
            "Stock Overview",
            "Current stock amounts.",
            "stock"
        )
        embed.add_field(name="📦 Free Stock", value=str(free_stock), inline=True)
        embed.add_field(name="💎 Premium Stock", value=str(premium_stock), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Blacklist", style=discord.ButtonStyle.secondary, emoji="🚫", row=1)
    async def blacklist_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not blacklisted_users:
            embed = create_embed(
                "Blacklist",
                "No users are blacklisted.",
                "blacklist"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        lines = []
        for user_id in blacklisted_users:
            member = interaction.guild.get_member(user_id)
            if member is None:
                try:
                    member = await interaction.guild.fetch_member(user_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    member = None

            if member:
                lines.append(f"{member.display_name} (@{member.name})")
            else:
                lines.append(f"Unknown User ({user_id})")

        text = "\n".join(lines)

        if len(text) > 1900:
            embed = create_embed(
                "Blacklist",
                f"Too many users to show.\nTotal blacklisted: **{len(blacklisted_users)}**",
                "blacklist"
            )
        else:
            embed = create_embed(
                "Blacklist",
                text,
                "blacklist"
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Bot Info", style=discord.ButtonStyle.success, emoji="ℹ️", row=1)
    async def botinfo_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        free_stock = len(get_stock())
        premium_stock = len(get_premium_stock())
        blacklist_count = len(blacklisted_users)
        cooldown_count = len(cooldowns)
        ping_ms = round(client.latency * 1000)

        embed = create_embed(
            "Bot Info",
            "Current bot information.",
            "info"
        )
        embed.add_field(name="📡 Ping", value=f"{ping_ms}ms", inline=True)
        embed.add_field(name="📦 Free Stock", value=str(free_stock), inline=True)
        embed.add_field(name="💎 Premium Stock", value=str(premium_stock), inline=True)
        embed.add_field(name="⏳ Free Cooldown", value=f"{FREE_COOLDOWN_SECONDS}s", inline=True)
        embed.add_field(name="⏳ Premium Cooldown", value=f"{PREMIUM_COOLDOWN_SECONDS}s", inline=True)
        embed.add_field(name="🚫 Blacklisted", value=str(blacklist_count), inline=True)
        embed.add_field(name="🧠 Active Cooldowns", value=str(cooldown_count), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

@client.tree.command(
    name="admindashboard",
    description="Open the admin dashboard",
    guild=discord.Object(id=GUILD_ID)
)
async def admindashboard(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not has_permission(interaction.user):
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    view = AdminDashboardView()
    embed = view.build_dashboard_embed()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

client.run(TOKEN)
