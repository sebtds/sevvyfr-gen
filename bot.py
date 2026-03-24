import os
import json
import time
import datetime
from typing import Any

import discord
from discord import app_commands

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN environment variable is missing.")

DATA_DIR = "/data"
os.makedirs(DATA_DIR, exist_ok=True)

OWNER_ID = 742144460552536106

BLACKLIST_FILE = f"{DATA_DIR}/blacklist.txt"
STOCK_FILE = f"{DATA_DIR}/stock.txt"
PREMIUM_STOCK_FILE = f"{DATA_DIR}/premium_stock.txt"
EMBED_SETTINGS_FILE = f"{DATA_DIR}/embed_settings.json"
SERVER_CONFIG_FILE = f"{DATA_DIR}/server_config.json"

FREE_COOLDOWN_SECONDS = 300
PREMIUM_COOLDOWN_SECONDS = 120

DEFAULT_EMBED_THUMBNAIL = "https://i1.sndcdn.com/artworks-S9Zqk2YaTDjBEdlI-WxqcPw-t500x500.jpg"
DEFAULT_EMBED_COLOR = 0xED4245
DEFAULT_EMBED_FOOTER = "Powered by @sevvyfr"

EMBED_THUMBNAIL = DEFAULT_EMBED_THUMBNAIL
EMBED_COLOR = discord.Color(DEFAULT_EMBED_COLOR)
EMBED_FOOTER = DEFAULT_EMBED_FOOTER

cooldowns: dict[tuple[int, str], float] = {}


class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()


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


def load_json_file(path: str, default: Any):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json_file(path: str, data: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_server_configs() -> dict[str, dict[str, Any]]:
    return load_json_file(SERVER_CONFIG_FILE, {})


def save_server_configs(data: dict[str, dict[str, Any]]):
    save_json_file(SERVER_CONFIG_FILE, data)


def get_guild_config(guild_id: int) -> dict[str, Any]:
    configs = load_server_configs()
    return configs.get(str(guild_id), {})


def update_guild_config(guild_id: int, **kwargs):
    configs = load_server_configs()
    guild_id_str = str(guild_id)

    if guild_id_str not in configs:
        configs[guild_id_str] = {}

    configs[guild_id_str].update(kwargs)
    save_server_configs(configs)


def get_log_channel_id(guild_id: int):
    return get_guild_config(guild_id).get("log_channel_id")


def get_gen_channel_id(guild_id: int):
    return get_guild_config(guild_id).get("gen_channel_id")


async def send_log(guild: discord.Guild, title: str, description: str, style: str = "info"):
    channel_id = get_log_channel_id(guild.id)
    if not channel_id:
        return

    channel = guild.get_channel(channel_id)
    if channel is None:
        try:
            channel = await guild.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return

    if not isinstance(channel, discord.TextChannel):
        return

    try:
        await channel.send(embed=create_embed(title, description, style))
    except discord.HTTPException:
        pass


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


def save_blacklist(user_ids):
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(str(user_id) for user_id in sorted(user_ids)))


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


def ensure_default_files():
    if not os.path.exists(STOCK_FILE):
        save_stock([])
    if not os.path.exists(PREMIUM_STOCK_FILE):
        save_premium_stock([])
    if not os.path.exists(BLACKLIST_FILE):
        save_blacklist(set())
    if not os.path.exists(EMBED_SETTINGS_FILE):
        save_embed_settings()
    if not os.path.exists(SERVER_CONFIG_FILE):
        save_server_configs({})


def format_time(seconds):
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}m {secs}s"


def has_permission(member: discord.Member) -> bool:
    if member.id == OWNER_ID:
        return True

    config = get_guild_config(member.guild.id)
    admin_role_ids = config.get("admin_role_ids", [])

    if not admin_role_ids:
        return member.guild_permissions.administrator

    return any(role.id in admin_role_ids for role in member.roles)


def has_premium(member: discord.Member) -> bool:
    config = get_guild_config(member.guild.id)
    premium_role_ids = config.get("premium_role_ids", [])

    if not premium_role_ids:
        return False

    return any(role.id in premium_role_ids for role in member.roles)


def clean_new_items(existing_stock, new_items):
    existing_set = set(existing_stock)
    cleaned = []
    skipped_duplicates = 0

    for item in new_items:
        if item in existing_set:
            skipped_duplicates += 1
            continue

        existing_set.add(item)
        cleaned.append(item)

    return cleaned, skipped_duplicates


def get_cooldown_remaining(user_id: int, stock_type: str) -> int:
    key = (user_id, stock_type)

    if key not in cooldowns:
        return 0

    cooldown_time = FREE_COOLDOWN_SECONDS if stock_type == "free" else PREMIUM_COOLDOWN_SECONDS
    remaining = int(cooldown_time - (time.time() - cooldowns[key]))
    return max(0, remaining)


blacklisted_users = get_blacklist()
ensure_default_files()
load_embed_settings()


@client.event
async def on_ready():
    await client.change_presence(
        status=discord.Status.dnd,
        activity=discord.Game(name="discord.gg/sevvyfr")
    )
    print(f"Logged in as {client.user}")


@client.event
async def on_guild_join(guild: discord.Guild):
    me = guild.me
    if me is None:
        return

    for channel in guild.text_channels:
        if channel.permissions_for(me).send_messages:
            try:
                await channel.send(
                    embed=create_embed(
                        "Thanks for Adding Me",
                        "Run `/setup` to configure admin role, premium role, log channel, and gen channel.",
                        "info"
                    )
                )
            except discord.HTTPException:
                pass
            break


@client.tree.command(
    name="gen",
    description="Generate an account"
)
@app_commands.describe(type="Choose stock type")
@app_commands.choices(type=[
    app_commands.Choice(name="Free", value="free"),
    app_commands.Choice(name="Premium", value="premium")
])
async def gen(interaction: discord.Interaction, type: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=False)

    # blacklist check
    if interaction.user.id in blacklisted_users:
        embed = create_embed(
            "Access Denied",
            "You are blacklisted from using this bot.",
            "blacklist"
        )
        await interaction.followup.send(embed=embed)
        return

    # channel lock check
    if interaction.guild:
        gen_channel_id = get_gen_channel_id(interaction.guild.id)
        if gen_channel_id and interaction.channel_id != gen_channel_id:
            embed = create_embed(
                "Wrong Channel",
                f"Use this command in <#{gen_channel_id}>.",
                "warning"
            )
            await interaction.followup.send(embed=embed)
            return

    user_id = interaction.user.id
    now = time.time()
    stock_type = type.value
    key = (user_id, stock_type)

    cooldown_time = FREE_COOLDOWN_SECONDS if stock_type == "free" else PREMIUM_COOLDOWN_SECONDS

    # cooldown check
    if key in cooldowns:
        remaining = int(cooldown_time - (now - cooldowns[key]))
        if remaining > 0:
            embed = create_embed(
                "Cooldown Active",
                f"Try again in {format_time(remaining)}.",
                "cooldown"
            )
            await interaction.followup.send(embed=embed)
            return

    # get stock
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
                "You need premium access.",
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

    # send DM
    try:
        dm_embed = create_embed(
            "Your Generated Account",
            f"`{item}`",
            "gen"
        )

        dm_embed.add_field(
            name="🔎 Check Skins",
            value="(https://siegeskins.dev)",
            inline=False
        )

        await interaction.user.send(embed=dm_embed)

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
        embed.add_field(name="👤 User", value=interaction.user.mention, inline=False)

        await interaction.followup.send(embed=embed)

        # log
        if interaction.guild:
            await send_log(
                interaction.guild,
                "Account Generated",
                f"{interaction.user.mention} generated a **{stock_type}** account.",
                "gen"
            )

    except discord.Forbidden:
        embed = create_embed(
            "DM Failed",
            "Turn on DMs and try again.",
            "error"
        )
        await interaction.followup.send(embed=embed)


@client.tree.command(
    name="restock",
    description="Add items to free or premium stock"
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
        cleaned_items, skipped_duplicates = clean_new_items(current_stock, new_items)
        current_stock.extend(cleaned_items)
        save_stock(current_stock)

        embed = create_embed(
            "Free Stock Restocked",
            f"Added **{len(cleaned_items)}** item(s) to FREE stock.",
            "stock"
        )
        embed.add_field(name="📥 Added", value=str(len(cleaned_items)), inline=True)
        embed.add_field(name="♻️ Skipped Duplicates", value=str(skipped_duplicates), inline=True)
        embed.add_field(name="📦 Total Free Stock", value=str(len(current_stock)), inline=False)

    else:
        current_stock = get_premium_stock()
        cleaned_items, skipped_duplicates = clean_new_items(current_stock, new_items)
        current_stock.extend(cleaned_items)
        save_premium_stock(current_stock)

        embed = create_embed(
            "Premium Stock Restocked",
            f"Added **{len(cleaned_items)}** item(s) to PREMIUM stock.",
            "premium"
        )
        embed.add_field(name="📥 Added", value=str(len(cleaned_items)), inline=True)
        embed.add_field(name="♻️ Skipped Duplicates", value=str(skipped_duplicates), inline=True)
        embed.add_field(name="💎 Total Premium Stock", value=str(len(current_stock)), inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=False)

    if interaction.guild:
        await send_log(
            interaction.guild,
            "Stock Restocked",
            f"{interaction.user.mention} added **{len(cleaned_items)}** item(s) to **{stock_type.value}** stock.",
            "stock"
        )


@client.tree.command(
    name="stock",
    description="See how many accounts are left in stock"
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
    description="View all free or premium stock items"
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
    description="View stock and cooldown info"
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
    description="Clear all items from stock"
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

    if interaction.guild:
        await send_log(
            interaction.guild,
            "Stock Cleared",
            f"{interaction.user.mention} cleared **{stock_type.value}** stock.",
            "stock"
        )


@client.tree.command(
    name="restockfile",
    description="Add stock items from a .txt file"
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
        cleaned_items, skipped_duplicates = clean_new_items(current_stock, new_items)
        current_stock.extend(cleaned_items)
        save_stock(current_stock)

        embed = create_embed(
            "Free Stock Restocked",
            f"Added **{len(cleaned_items)}** item(s) from `{file.filename}`.",
            "stock"
        )
        embed.add_field(name="📥 Added", value=str(len(cleaned_items)), inline=True)
        embed.add_field(name="♻️ Skipped Duplicates", value=str(skipped_duplicates), inline=True)
        embed.add_field(name="📦 Total Free Stock", value=str(len(current_stock)), inline=False)

    else:
        current_stock = get_premium_stock()
        cleaned_items, skipped_duplicates = clean_new_items(current_stock, new_items)
        current_stock.extend(cleaned_items)
        save_premium_stock(current_stock)

        embed = create_embed(
            "Premium Stock Restocked",
            f"Added **{len(cleaned_items)}** item(s) from `{file.filename}`.",
            "premium"
        )
        embed.add_field(name="📥 Added", value=str(len(cleaned_items)), inline=True)
        embed.add_field(name="♻️ Skipped Duplicates", value=str(skipped_duplicates), inline=True)
        embed.add_field(name="💎 Total Premium Stock", value=str(len(current_stock)), inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=False)

    if interaction.guild:
        await send_log(
            interaction.guild,
            "Stock File Restocked",
            f"{interaction.user.mention} added **{len(cleaned_items)}** item(s) to **{stock_type.value}** stock from `{file.filename}`.",
            "stock"
        )


@client.tree.command(
    name="setcooldown",
    description="Change the free or premium cooldown in seconds"
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
    description="Show all bot commands"
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
            "`/setup` - Set up the bot for this server\n"
            "`/viewsetup` - View this server's setup\n"
            "`/addadminrole` - Add another admin role\n"
            "`/addpremiumrole` - Add another premium role\n"
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
            "`/setthumbnail` - Change thumbnail\n"
            "`/admindashboard` - Open admin dashboard"
        ),
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="setstatus",
    description="Change the bot status text"
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
    description="Blacklist a user from using the generator"
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

    if interaction.guild:
        await send_log(
            interaction.guild,
            "User Blacklisted",
            f"{interaction.user.mention} blacklisted {user.mention}.",
            "blacklist"
        )


@client.tree.command(
    name="unblacklist",
    description="Remove a user from the blacklist"
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
    description="View all blacklisted users"
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

    if not interaction.guild:
        embed = create_embed(
            "Blacklist",
            "\n".join(str(user_id) for user_id in blacklisted_users),
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
    description="Clear the entire blacklist"
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
    description="Remove items from free or premium stock"
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
        stock_data = get_stock()

        if not stock_data:
            embed = create_embed(
                "Free Stock",
                "Free stock is already empty.",
                "stock"
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        removed_amount = min(amount, len(stock_data))
        stock_data = stock_data[removed_amount:]
        save_stock(stock_data)

        embed = create_embed(
            "Free Stock Updated",
            f"Removed **{removed_amount}** item(s) from free stock.",
            "stock"
        )
        embed.add_field(name="📦 Free Stock Left", value=str(len(stock_data)), inline=False)

    else:
        stock_data = get_premium_stock()

        if not stock_data:
            embed = create_embed(
                "Premium Stock",
                "Premium stock is already empty.",
                "premium"
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        removed_amount = min(amount, len(stock_data))
        stock_data = stock_data[removed_amount:]
        save_premium_stock(stock_data)

        embed = create_embed(
            "Premium Stock Updated",
            f"Removed **{removed_amount}** item(s) from premium stock.",
            "premium"
        )
        embed.add_field(name="💎 Premium Stock Left", value=str(len(stock_data)), inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="resetcooldown",
    description="Reset a user's free or premium cooldown"
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
    description="Clear all active cooldowns"
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
    description="View bot info, stock, cooldowns, and blacklist count"
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
    embed.add_field(name="📡 Ping", value=f"{ping_ms}ms", inline=True)
    embed.add_field(name="📦 Free Stock", value=str(free_stock), inline=True)
    embed.add_field(name="💎 Premium Stock", value=str(premium_stock), inline=True)
    embed.add_field(name="⏳ Free Cooldown", value=f"{FREE_COOLDOWN_SECONDS}s", inline=True)
    embed.add_field(name="⏳ Premium Cooldown", value=f"{PREMIUM_COOLDOWN_SECONDS}s", inline=True)
    embed.add_field(name="🚫 Blacklisted", value=str(blacklist_count), inline=True)
    embed.add_field(name="🧠 Active Cooldowns", value=str(cooldown_count), inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="removeduplicates",
    description="Remove duplicate items from free or premium stock"
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
        stock_data = get_stock()
        original_count = len(stock_data)
        cleaned_stock = list(dict.fromkeys(stock_data))
        removed_count = original_count - len(cleaned_stock)
        save_stock(cleaned_stock)

        embed = create_embed(
            "Free Stock Cleaned",
            f"Removed **{removed_count}** duplicate item(s).",
            "stock"
        )
        embed.add_field(name="📦 Free Stock Left", value=str(len(cleaned_stock)), inline=False)

    else:
        stock_data = get_premium_stock()
        original_count = len(stock_data)
        cleaned_stock = list(dict.fromkeys(stock_data))
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
    description="Check a user's premium, blacklist, and cooldown status"
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
    description="Change the embed thumbnail URL"
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
    description="Change the embed footer text"
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
    description="Change the embed color using a hex code"
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
    description="Remove one exact item from free or premium stock"
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
        stock_data = get_stock()

        if item not in stock_data:
            embed = create_embed(
                "Item Not Found",
                "That item was not found in free stock.",
                "warning"
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        stock_data.remove(item)
        save_stock(stock_data)

        embed = create_embed(
            "Item Removed",
            "Removed item from free stock.",
            "stock"
        )
        embed.add_field(name="📦 Free Stock Left", value=str(len(stock_data)), inline=False)

    else:
        stock_data = get_premium_stock()

        if item not in stock_data:
            embed = create_embed(
                "Item Not Found",
                "That item was not found in premium stock.",
                "warning"
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        stock_data.remove(item)
        save_premium_stock(stock_data)

        embed = create_embed(
            "Item Removed",
            "Removed item from premium stock.",
            "premium"
        )
        embed.add_field(name="💎 Premium Stock Left", value=str(len(stock_data)), inline=False)

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

        await interaction.response.send_message(embed=embed, ephemeral=False)

    @discord.ui.button(label="Blacklist", style=discord.ButtonStyle.secondary, emoji="🚫", row=1)
    async def blacklist_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not blacklisted_users:
            embed = create_embed(
                "Blacklist",
                "No users are blacklisted.",
                "blacklist"
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        if not interaction.guild:
            embed = create_embed(
                "Blacklist",
                "\n".join(str(user_id) for user_id in blacklisted_users),
                "blacklist"
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
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

        await interaction.response.send_message(embed=embed, ephemeral=False)

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

        await interaction.response.send_message(embed=embed, ephemeral=False)





@client.tree.command(
    name="setup",
    description="Set up the bot for this server"
)
@app_commands.describe(
    admin_role="Role that can manage the bot",
    premium_role="Role that can use premium stock",
    log_channel="Channel for bot logs",
    gen_channel="Channel where /gen should be used"
)
async def setup(
    interaction: discord.Interaction,
    admin_role: discord.Role,
    premium_role: discord.Role,
    log_channel: discord.TextChannel,
    gen_channel: discord.TextChannel
):
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        embed = create_embed(
            "Server Only",
            "This command can only be used in a server.",
            "warning"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if interaction.user.id != OWNER_ID and not interaction.user.guild_permissions.administrator:
        embed = create_embed(
            "Access Denied",
            "You must be a server administrator to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    update_guild_config(
        interaction.guild.id,
        admin_role_ids=[admin_role.id],
        premium_role_ids=[premium_role.id],
        log_channel_id=log_channel.id,
        gen_channel_id=gen_channel.id
    )

    embed = create_embed(
        "Setup Complete",
        f"Saved configuration for **{interaction.guild.name}**.",
        "settings"
    )
    embed.add_field(name="🛠 Admin Role", value=admin_role.mention, inline=False)
    embed.add_field(name="💎 Premium Role", value=premium_role.mention, inline=False)
    embed.add_field(name="📝 Log Channel", value=log_channel.mention, inline=False)
    embed.add_field(name="🎮 Gen Channel", value=gen_channel.mention, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=False)

    await send_log(
        interaction.guild,
        "Server Setup Updated",
        f"Configured by {interaction.user.mention}",
        "settings"
    )


@client.tree.command(
    name="viewsetup",
    description="View this server's bot setup"
)
async def viewsetup(interaction: discord.Interaction):
    if not interaction.guild:
        embed = create_embed(
            "Server Only",
            "This command can only be used in a server.",
            "warning"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    config = get_guild_config(interaction.guild.id)

    admin_role_ids = config.get("admin_role_ids", [])
    premium_role_ids = config.get("premium_role_ids", [])
    log_channel_id = config.get("log_channel_id")
    gen_channel_id = config.get("gen_channel_id")

    admin_roles = [interaction.guild.get_role(role_id) for role_id in admin_role_ids]
    premium_roles = [interaction.guild.get_role(role_id) for role_id in premium_role_ids]
    log_channel = interaction.guild.get_channel(log_channel_id) if log_channel_id else None
    gen_channel = interaction.guild.get_channel(gen_channel_id) if gen_channel_id else None

    embed = create_embed(
        "Server Setup",
        f"Current setup for **{interaction.guild.name}**.",
        "settings"
    )
    embed.add_field(
        name="🛠 Admin Roles",
        value="\n".join(role.mention for role in admin_roles if role) if any(admin_roles) else "Not set",
        inline=False
    )
    embed.add_field(
        name="💎 Premium Roles",
        value="\n".join(role.mention for role in premium_roles if role) if any(premium_roles) else "Not set",
        inline=False
    )
    embed.add_field(
        name="📝 Log Channel",
        value=log_channel.mention if log_channel else "Not set",
        inline=False
    )
    embed.add_field(
        name="🎮 Gen Channel",
        value=gen_channel.mention if gen_channel else "Not set",
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="addadminrole",
    description="Add another admin role for this server"
)
@app_commands.describe(role="Role to add as an admin role")
async def addadminrole(interaction: discord.Interaction, role: discord.Role):
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return

    if interaction.user.id != OWNER_ID and not interaction.user.guild_permissions.administrator:
        embed = create_embed(
            "Access Denied",
            "You must be a server administrator to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    config = get_guild_config(interaction.guild.id)
    admin_role_ids = config.get("admin_role_ids", [])

    if role.id in admin_role_ids:
        embed = create_embed(
            "Already Added",
            f"{role.mention} is already an admin role.",
            "warning"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    admin_role_ids.append(role.id)
    update_guild_config(interaction.guild.id, admin_role_ids=admin_role_ids)

    embed = create_embed(
        "Admin Role Added",
        f"{role.mention} can now manage the bot.",
        "settings"
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.tree.command(
    name="addpremiumrole",
    description="Add another premium role for this server"
)
@app_commands.describe(role="Role to add as a premium role")
async def addpremiumrole(interaction: discord.Interaction, role: discord.Role):
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return

    if not has_permission(interaction.user):
        embed = create_embed(
            "Access Denied",
            "You are not allowed to use this command.",
            "error"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    config = get_guild_config(interaction.guild.id)
    premium_role_ids = config.get("premium_role_ids", [])

    if role.id in premium_role_ids:
        embed = create_embed(
            "Already Added",
            f"{role.mention} is already a premium role.",
            "warning"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    premium_role_ids.append(role.id)
    update_guild_config(interaction.guild.id, premium_role_ids=premium_role_ids)

    embed = create_embed(
        "Premium Role Added",
        f"{role.mention} can now use premium stock.",
        "settings"
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)

@client.tree.command(
    name="admindashboard",
    description="Open the admin dashboard"
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
    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)


@client.tree.command(name="exportstock", description="Download stock as file")
async def exportstock(interaction: discord.Interaction):
    if not has_permission(interaction.user):
        return

    file = discord.File(STOCK_FILE, filename="stock.txt")
    await interaction.response.send_message(file=file)

client.run(TOKEN)
