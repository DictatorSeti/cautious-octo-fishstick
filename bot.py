import os
import sqlite3
import asyncio
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands


# ============================================================
# CONFIGURATION
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

# Railway persistent volume path if available, otherwise current folder
DATABASE_PATH = os.getenv("DATABASE_PATH", "bus_game.db")

# Use a specific guild for instant slash-command syncing.
# Put your Discord server ID in Railway variables if you want this.
GUILD_ID = os.getenv("GUILD_ID")


# ============================================================
# DATABASE
# ============================================================

db_dir = os.path.dirname(DATABASE_PATH)

if db_dir:
    os.makedirs(db_dir, exist_ok=True)

conn = sqlite3.connect(
    DATABASE_PATH,
    check_same_thread=False
)

conn.row_factory = sqlite3.Row
cursor = conn.cursor()


def setup_database():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            owner_id TEXT UNIQUE NOT NULL,
            balance INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route TEXT NOT NULL,
            required_pvr INTEGER NOT NULL,
            vehicle_type TEXT NOT NULL,
            tender_price INTEGER NOT NULL,
            contract_years INTEGER NOT NULL,
            closes_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            winner_operator_id INTEGER,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tender_bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id INTEGER NOT NULL,
            operator_id INTEGER NOT NULL,
            bid_price INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(tender_id, operator_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id INTEGER UNIQUE NOT NULL,
            route TEXT NOT NULL,
            operator_id INTEGER NOT NULL,
            tender_price INTEGER NOT NULL,
            required_pvr INTEGER NOT NULL,
            vehicle_type TEXT NOT NULL,
            starts_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
        )
    """)

    conn.commit()


setup_database()


# ============================================================
# HELPERS
# ============================================================

def now():
    return datetime.now(timezone.utc)


def format_money(amount):
    return f"£{amount:,.0f}"


def get_operator_by_owner(user_id):
    return cursor.execute(
        "SELECT * FROM operators WHERE owner_id = ?",
        (str(user_id),)
    ).fetchone()


def get_operator_by_id(operator_id):
    return cursor.execute(
        "SELECT * FROM operators WHERE id = ?",
        (operator_id,)
    ).fetchone()


def get_tender(tender_id):
    return cursor.execute(
        "SELECT * FROM tenders WHERE id = ?",
        (tender_id,)
    ).fetchone()


async def send_error(interaction, message):
    if interaction.response.is_done():
        await interaction.followup.send(
            f"❌ {message}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ {message}",
            ephemeral=True
        )


# ============================================================
# DISCORD BOT
# ============================================================

class BusBot(discord.Client):

    def __init__(self):
        intents = discord.Intents.default()

        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
        self.tender_checker_started = False

    async def setup_hook(self):

        # Start automatic tender checker
        if not self.tender_checker_started:
            self.tender_checker_started = True
            self.loop.create_task(check_expired_tenders())

        # Fast guild sync if GUILD_ID is set
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))

            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

            print(f"Synced commands to guild {GUILD_ID}")

        else:
            await self.tree.sync()
            print("Synced global commands")


bot = BusBot()


# ============================================================
# OPERATOR COMMANDS
# ============================================================

operator_group = app_commands.Group(
    name="operator",
    description="Manage your bus operator"
)


@operator_group.command(
    name="create",
    description="Create your bus operator"
)
@app_commands.describe(
    name="The name of your bus operator"
)
async def operator_create(
    interaction: discord.Interaction,
    name: str
):

    existing = get_operator_by_owner(interaction.user.id)

    if existing:
        await send_error(
            interaction,
            "You already own an operator."
        )
        return

    try:

        cursor.execute("""
            INSERT INTO operators (
                name,
                owner_id,
                balance,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            name,
            str(interaction.user.id),
            0,
            now().isoformat()
        ))

        conn.commit()

    except sqlite3.IntegrityError:

        await send_error(
            interaction,
            "That operator name is already taken."
        )
        return

    embed = discord.Embed(
        title="🏢 Operator Created",
        description=f"Welcome to **{name}**!"
    )

    embed.add_field(
        name="💰 Starting Balance",
        value=format_money(0)
    )

    embed.add_field(
        name="👤 Owner",
        value=interaction.user.mention
    )

    await interaction.response.send_message(
        embed=embed
    )


@operator_group.command(
    name="info",
    description="View operator information"
)
async def operator_info(
    interaction: discord.Interaction
):

    operator = get_operator_by_owner(interaction.user.id)

    if not operator:
        await send_error(
            interaction,
            "You do not own an operator. Use `/operator create` first."
        )
        return

    active_contracts = cursor.execute("""
        SELECT COUNT(*)
        FROM contracts
        WHERE operator_id = ?
        AND status = 'active'
    """, (
        operator["id"],
    )).fetchone()[0]

    embed = discord.Embed(
        title=f"🏢 {operator['name']}"
    )

    embed.add_field(
        name="💰 Balance",
        value=format_money(operator["balance"])
    )

    embed.add_field(
        name="🚌 Active Contracts",
        value=str(active_contracts)
    )

    embed.add_field(
        name="🆔 Operator ID",
        value=str(operator["id"])
    )

    await interaction.response.send_message(
        embed=embed
    )


@operator_group.command(
    name="balance",
    description="View your operator balance"
)
async def operator_balance(
    interaction: discord.Interaction
):

    operator = get_operator_by_owner(interaction.user.id)

    if not operator:
        await send_error(
            interaction,
            "You do not own an operator."
        )
        return

    await interaction.response.send_message(
        f"💰 **{operator['name']}** currently has "
        f"**{format_money(operator['balance'])}**."
    )


# ============================================================
# TENDER COMMANDS
# ============================================================

tender_group = app_commands.Group(
    name="tender",
    description="Manage bus route tenders"
)


@tender_group.command(
    name="create",
    description="Create a new route tender"
)
@app_commands.describe(
    route="Route number, for example 92, 341 or N341",
    required_pvr="Number of buses required",
    vehicle_type="Required vehicle type",
    tender_price="Maximum value of the tender in pounds",
    contract_years="Length of contract in years",
    closes_in_hours="How many hours until bidding closes"
)
async def tender_create(
    interaction: discord.Interaction,
    route: str,
    required_pvr: app_commands.Range[int, 1, 500],
    vehicle_type: str,
    tender_price: app_commands.Range[int, 1, 1000000000],
    contract_years: app_commands.Range[int, 1, 20],
    closes_in_hours: app_commands.Range[int, 1, 8760]
):

    # You can replace this with an admin role check later
    closes_at = now() + timedelta(
        hours=closes_in_hours
    )

    cursor.execute("""
        INSERT INTO tenders (
            route,
            required_pvr,
            vehicle_type,
            tender_price,
            contract_years,
            closes_at,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 'open', ?)
    """, (
        route.upper(),
        required_pvr,
        vehicle_type,
        tender_price,
        contract_years,
        closes_at.isoformat(),
        now().isoformat()
    ))

    tender_id = cursor.lastrowid

    conn.commit()

    embed = discord.Embed(
        title=f"📋 NEW TENDER — Route {route.upper()}",
        description=f"**Tender #{tender_id} is now open for bidding.**"
    )

    embed.add_field(
        name="🚌 Required PVR",
        value=str(required_pvr),
        inline=True
    )

    embed.add_field(
        name="🚍 Vehicle Type",
        value=vehicle_type,
        inline=True
    )

    embed.add_field(
        name="💷 Maximum Tender Value",
        value=format_money(tender_price),
        inline=False
    )

    embed.add_field(
        name="📅 Contract Length",
        value=f"{contract_years} years",
        inline=True
    )

    embed.add_field(
        name="⏰ Closes",
        value=f"<t:{int(closes_at.timestamp())}:R>",
        inline=True
    )

    embed.set_footer(
        text=f"Tender ID: {tender_id}"
    )

    await interaction.response.send_message(
        embed=embed
    )


@tender_group.command(
    name="list",
    description="View all open tenders"
)
async def tender_list(
    interaction: discord.Interaction
):

    tenders = cursor.execute("""
        SELECT *
        FROM tenders
        WHERE status = 'open'
        ORDER BY closes_at ASC
    """).fetchall()

    if not tenders:
        await interaction.response.send_message(
            "📭 There are currently no open tenders."
        )
        return

    lines = []

    for tender in tenders:

        closes_at = datetime.fromisoformat(
            tender["closes_at"]
        )

        lines.append(
            f"**#{tender['id']} — Route {tender['route']}**\n"
            f"PVR: `{tender['required_pvr']}` | "
            f"{tender['vehicle_type']}\n"
            f"Max value: **{format_money(tender['tender_price'])}** | "
            f"Closes <t:{int(closes_at.timestamp())}:R>"
        )

    embed = discord.Embed(
        title="📋 Open Tenders",
        description="\n\n".join(lines)
    )

    await interaction.response.send_message(
        embed=embed
    )


@tender_group.command(
    name="info",
    description="View detailed information about a tender"
)
@app_commands.describe(
    tender_id="The tender ID"
)
async def tender_info(
    interaction: discord.Interaction,
    tender_id: int
):

    tender = get_tender(tender_id)

    if not tender:
        await send_error(
            interaction,
            "Tender not found."
        )
        return

    bid_count = cursor.execute("""
        SELECT COUNT(*)
        FROM tender_bids
        WHERE tender_id = ?
    """, (
        tender_id,
    )).fetchone()[0]

    closes_at = datetime.fromisoformat(
        tender["closes_at"]
    )

    embed = discord.Embed(
        title=f"📋 Tender #{tender['id']} — Route {tender['route']}"
    )

    embed.add_field(
        name="Status",
        value=tender["status"].upper()
    )

    embed.add_field(
        name="Required PVR",
        value=str(tender["required_pvr"])
    )

    embed.add_field(
        name="Vehicle Type",
        value=tender["vehicle_type"]
    )

    embed.add_field(
        name="Maximum Tender Value",
        value=format_money(tender["tender_price"])
    )

    embed.add_field(
        name="Contract Length",
        value=f"{tender['contract_years']} years"
    )

    embed.add_field(
        name="Bids Received",
        value=str(bid_count)
    )

    if tender["status"] == "open":

        embed.add_field(
            name="Closes",
            value=f"<t:{int(closes_at.timestamp())}:F>"
        )

    if tender["winner_operator_id"]:

        winner = get_operator_by_id(
            tender["winner_operator_id"]
        )

        if winner:
            embed.add_field(
                name="Winner",
                value=winner["name"]
            )

    await interaction.response.send_message(
        embed=embed
    )


@tender_group.command(
    name="bid",
    description="Submit or update your tender bid"
)
@app_commands.describe(
    tender_id="The tender ID you want to bid on",
    price="The amount your operator is bidding"
)
async def tender_bid(
    interaction: discord.Interaction,
    tender_id: int,
    price: app_commands.Range[int, 1, 1000000000]
):

    operator = get_operator_by_owner(
        interaction.user.id
    )

    if not operator:
        await send_error(
            interaction,
            "Create an operator before bidding."
        )
        return

    tender = get_tender(tender_id)

    if not tender:
        await send_error(
            interaction,
            "Tender not found."
        )
        return

    if tender["status"] != "open":
        await send_error(
            interaction,
            "This tender is no longer open."
        )
        return

    closes_at = datetime.fromisoformat(
        tender["closes_at"]
    )

    if now() >= closes_at:
        await close_tender(tender_id)

        await send_error(
            interaction,
            "This tender has just closed."
        )
        return

    if price > tender["tender_price"]:
        await send_error(
            interaction,
            f"Your bid cannot be higher than the maximum "
            f"tender value of {format_money(tender['tender_price'])}."
        )
        return

    existing_bid = cursor.execute("""
        SELECT *
        FROM tender_bids
        WHERE tender_id = ?
        AND operator_id = ?
    """, (
        tender_id,
        operator["id"]
    )).fetchone()

    if existing_bid:

        cursor.execute("""
            UPDATE tender_bids
            SET bid_price = ?,
                created_at = ?
            WHERE id = ?
        """, (
            price,
            now().isoformat(),
            existing_bid["id"]
        ))

        message = "✏️ Your bid has been updated."

    else:

        cursor.execute("""
            INSERT INTO tender_bids (
                tender_id,
                operator_id,
                bid_price,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            tender_id,
            operator["id"],
            price,
            now().isoformat()
        ))

        message = "📨 Your bid has been submitted."

    conn.commit()

    await interaction.response.send_message(
        f"{message}\n\n"
        f"**Route:** {tender['route']}\n"
        f"**Your bid:** {format_money(price)}"
    )


@tender_group.command(
    name="my_bids",
    description="View all your tender bids"
)
async def tender_my_bids(
    interaction: discord.Interaction
):

    operator = get_operator_by_owner(
        interaction.user.id
    )

    if not operator:
        await send_error(
            interaction,
            "You do not own an operator."
        )
        return

    bids = cursor.execute("""
        SELECT
            tender_bids.bid_price,
            tenders.id AS tender_id,
            tenders.route,
            tenders.status
        FROM tender_bids
        JOIN tenders
            ON tenders.id = tender_bids.tender_id
        WHERE tender_bids.operator_id = ?
        ORDER BY tender_bids.created_at DESC
    """, (
        operator["id"],
    )).fetchall()

    if not bids:
        await interaction.response.send_message(
            "📭 You have not submitted any bids."
        )
        return

    lines = []

    for bid in bids:

        lines.append(
            f"**#{bid['tender_id']} — Route {bid['route']}**\n"
            f"Your bid: {format_money(bid['bid_price'])}\n"
            f"Status: `{bid['status'].upper()}`"
        )

    embed = discord.Embed(
        title=f"📨 {operator['name']} — Tender Bids",
        description="\n\n".join(lines)
    )

    await interaction.response.send_message(
        embed=embed
    )


@tender_group.command(
    name="close",
    description="Manually close and award a tender"
)
@app_commands.describe(
    tender_id="The tender ID to close"
)
async def tender_close(
    interaction: discord.Interaction,
    tender_id: int
):

    tender = get_tender(tender_id)

    if not tender:
        await send_error(
            interaction,
            "Tender not found."
        )
        return

    if tender["status"] != "open":
        await send_error(
            interaction,
            "This tender has already closed."
        )
        return

    result = await close_tender(tender_id)

    await interaction.response.send_message(
        result
    )


# ============================================================
# TENDER AWARD SYSTEM
# ============================================================

async def close_tender(tender_id):

    tender = get_tender(tender_id)

    if not tender or tender["status"] != "open":
        return "❌ Tender could not be closed."

    # Lowest valid bid wins
    winning_bid = cursor.execute("""
        SELECT *
        FROM tender_bids
        WHERE tender_id = ?
        ORDER BY bid_price ASC, created_at ASC
        LIMIT 1
    """, (
        tender_id,
    )).fetchone()

    if not winning_bid:

        cursor.execute("""
            UPDATE tenders
            SET status = 'closed'
            WHERE id = ?
        """, (
            tender_id,
        ))

        conn.commit()

        return (
            f"📋 **Tender #{tender_id} — Route {tender['route']}**\n"
            f"The tender closed with no bids."
        )

    winner = get_operator_by_id(
        winning_bid["operator_id"]
    )

    winning_price = winning_bid["bid_price"]

    start_date = now()

    expiry_date = start_date + timedelta(
        days=365 * tender["contract_years"]
    )

    # Award tender
    cursor.execute("""
        UPDATE tenders
        SET status = 'awarded',
            winner_operator_id = ?
        WHERE id = ?
    """, (
        winner["id"],
        tender_id
    ))

    # Add the WINNING CONTRACT VALUE to the operator
    cursor.execute("""
        UPDATE operators
        SET balance = balance + ?
        WHERE id = ?
    """, (
        winning_price,
        winner["id"]
    ))

    # Create contract
    cursor.execute("""
        INSERT OR REPLACE INTO contracts (
            tender_id,
            route,
            operator_id,
            tender_price,
            required_pvr,
            vehicle_type,
            starts_at,
            expires_at,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
    """, (
        tender_id,
        tender["route"],
        winner["id"],
        winning_price,
        tender["required_pvr"],
        tender["vehicle_type"],
        start_date.isoformat(),
        expiry_date.isoformat()
    ))

    conn.commit()

    return (
        f"🏆 **TENDER AWARDED!**\n\n"
        f"**Route:** {tender['route']}\n"
        f"**Winner:** {winner['name']}\n"
        f"**Contract Value:** {format_money(winning_price)}\n"
        f"**Contract Length:** {tender['contract_years']} years\n"
        f"**Required PVR:** {tender['required_pvr']}\n"
        f"**Vehicle Type:** {tender['vehicle_type']}\n\n"
        f"💰 **{format_money(winning_price)} has been added "
        f"to {winner['name']}'s balance.**"
    )


# ============================================================
# AUTOMATIC TENDER CHECKER
# ============================================================

async def check_expired_tenders():

    await bot.wait_until_ready()

    while not bot.is_closed():

        try:

            open_tenders = cursor.execute("""
                SELECT *
                FROM tenders
                WHERE status = 'open'
            """).fetchall()

            for tender in open_tenders:

                closes_at = datetime.fromisoformat(
                    tender["closes_at"]
                )

                if now() >= closes_at:

                    result = await close_tender(
                        tender["id"]
                    )

                    print(result)

        except Exception as error:

            print(
                f"Tender checker error: {error}"
            )

        await asyncio.sleep(60)


# ============================================================
# ACTIVE CONTRACTS
# ============================================================

contract_group = app_commands.Group(
    name="contract",
    description="View your awarded contracts"
)


@contract_group.command(
    name="list",
    description="View your active contracts"
)
async def contract_list(
    interaction: discord.Interaction
):

    operator = get_operator_by_owner(
        interaction.user.id
    )

    if not operator:
        await send_error(
            interaction,
            "You do not own an operator."
        )
        return

    contracts = cursor.execute("""
        SELECT *
        FROM contracts
        WHERE operator_id = ?
        AND status = 'active'
        ORDER BY expires_at ASC
    """, (
        operator["id"],
    )).fetchall()

    if not contracts:

        await interaction.response.send_message(
            "📭 Your operator has no active contracts."
        )
        return

    lines = []

    for contract in contracts:

        expiry = datetime.fromisoformat(
            contract["expires_at"]
        )

        lines.append(
            f"**Route {contract['route']}**\n"
            f"PVR: `{contract['required_pvr']}` | "
            f"{contract['vehicle_type']}\n"
            f"Contract value: **{format_money(contract['tender_price'])}**\n"
            f"Expires: <t:{int(expiry.timestamp())}:D>"
        )

    embed = discord.Embed(
        title=f"🚌 {operator['name']} — Active Contracts",
        description="\n\n".join(lines)
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# REGISTER COMMAND GROUPS
# ============================================================

bot.tree.add_command(operator_group)
bot.tree.add_command(tender_group)
bot.tree.add_command(contract_group)


# ============================================================
# EVENTS
# ============================================================

@bot.event
async def on_ready():

    print("====================================")
    print(f"Logged in as {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print(f"Database: {DATABASE_PATH}")
    print("====================================")


# ============================================================
# START BOT
# ============================================================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN environment variable is not set."
    )

bot.run(TOKEN)
