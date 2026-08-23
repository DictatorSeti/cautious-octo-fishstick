import os
import sqlite3
import random
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks


# ============================================================
# CONFIGURATION
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")
TEST_GUILD_ID = os.getenv("TEST_GUILD_ID")
STAFF_ROLE = os.getenv("STAFF_ROLE", "Game Staff")
DATABASE_PATH = "/tmp/bus_game.db"

STARTING_MONEY = 5_000_000

TENDER_CHECK_SECONDS = 60
DRIVER_MARKET_HOURS = 6
BUS_TRANSFER_COST = 500


# ============================================================
# DATABASE
# ============================================================

from pathlib import Path
import sqlite3

def get_database_path():
    locations = [
        Path("/tmp/bus_game.db"),
        Path.cwd() / "bus_game.db",
        Path.home() / "bus_game.db",
    ]

    for path in locations:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            # Test that the directory is writable
            test_file = path.parent / ".write_test"
            test_file.touch(exist_ok=True)
            test_file.unlink()

            return path

        except (PermissionError, OSError):
            continue

    raise RuntimeError(
        "Could not find a writable directory for the SQLite database."
    )


DATABASE_PATH = get_database_path()

print(f"Using database: {DATABASE_PATH}")

conn = sqlite3.connect(
    str(DATABASE_PATH),
    check_same_thread=False,
    timeout=30
)

conn.row_factory = sqlite3.Row

conn.execute("PRAGMA foreign_keys = ON")
conn.execute("PRAGMA journal_mode = WAL")
# ============================================================
# GARAGES
# ============================================================

GARAGES = {
    "A": {
        "name": "Sutton Garage",
        "location": "Sutton",
        "capacity": 86,
        "buy": 1_800_000,
        "rent": 34_000,
    },
    "AC": {
        "name": "Willesden Garage",
        "location": "Brent",
        "capacity": 100,
        "buy": 2_400_000,
        "rent": 44_000,
    },
    "AD": {
        "name": "Palmers Green Garage",
        "location": "Enfield",
        "capacity": 81,
        "buy": 1_700_000,
        "rent": 32_000,
    },
    "AF": {
        "name": "Putney Garage",
        "location": "Wandsworth",
        "capacity": 94,
        "buy": 2_600_000,
        "rent": 47_000,
    },
    "AH": {
        "name": "Brentford Garage",
        "location": "Hounslow",
        "capacity": 96,
        "buy": 2_100_000,
        "rent": 38_000,
    },
    "BC": {
        "name": "Beddington Garage",
        "location": "Croydon",
        "capacity": 128,
        "buy": 2_800_000,
        "rent": 51_000,
    },
    "BK": {
        "name": "Barking Garage",
        "location": "Barking and Dagenham",
        "capacity": 105,
        "buy": 2_300_000,
        "rent": 42_000,
    },
    "BN": {
        "name": "Brixton Garage",
        "location": "Lambeth",
        "capacity": 94,
        "buy": 2_600_000,
        "rent": 47_000,
    },
    "BT": {
        "name": "Edgware Garage",
        "location": "Barnet",
        "capacity": 83,
        "buy": 1_800_000,
        "rent": 33_000,
    },
    "BW": {
        "name": "Bow Garage",
        "location": "Tower Hamlets",
        "capacity": 95,
        "buy": 2_300_000,
        "rent": 41_000,
    },
    "BX": {
        "name": "Bexleyheath Garage",
        "location": "Bexley",
        "capacity": 113,
        "buy": 2_400_000,
        "rent": 45_000,
    },
    "C": {
        "name": "Croydon Garage",
        "location": "Croydon",
        "capacity": 117,
        "buy": 2_500_000,
        "rent": 47_000,
    },
    "CP": {
        "name": "Canons Park Garage",
        "location": "Harrow",
        "capacity": 29,
        "buy": 600_000,
        "rent": 12_000,
    },
    "CT": {
        "name": "Clapton Garage",
        "location": "Hackney",
        "capacity": 79,
        "buy": 2_200_000,
        "rent": 39_000,
    },
    "DT": {
        "name": "Dartford Garage",
        "location": "Dartford",
        "capacity": 60,
        "buy": 1_000_000,
        "rent": 19_000,
    },
    "DS": {
        "name": "Henley Road Garage",
        "location": "Redbridge",
        "capacity": 142,
        "buy": 3_100_000,
        "rent": 57_000,
    },
    "DX": {
        "name": "Barking (North Street) Garage",
        "location": "Barking and Dagenham",
        "capacity": 45,
        "buy": 1_000_000,
        "rent": 18_000,
    },
    "E": {
        "name": "Enfield Garage",
        "location": "Enfield",
        "capacity": 122,
        "buy": 2_600_000,
        "rent": 49_000,
    },
    "EC": {
        "name": "Edmonton Garage",
        "location": "Enfield",
        "capacity": 25,
        "buy": 500_000,
        "rent": 10_000,
    },
    "EW": {
        "name": "Edgware Garage (Approach Rd)",
        "location": "Barnet",
        "capacity": 79,
        "buy": 1_700_000,
        "rent": 32_000,
    },
    "FW": {
        "name": "Fulwell Garage",
        "location": "Richmond upon Thames",
        "capacity": 124,
        "buy": 2_700_000,
        "rent": 50_000,
    },
    "G": {
        "name": "Greenford Garage",
        "location": "Ealing",
        "capacity": 85,
        "buy": 2_000_000,
        "rent": 37_000,
    },
    "GM": {
        "name": "Goat Road Garage",
        "location": "Newham",
        "capacity": 26,
        "buy": 600_000,
        "rent": 11_000,
    },
    "GW": {
        "name": "Armstrong Way Garage",
        "location": "Ealing",
        "capacity": 129,
        "buy": 3_100_000,
        "rent": 56_000,
    },
    "HD": {
        "name": "Harrow Weald Garage",
        "location": "Harrow",
        "capacity": 79,
        "buy": 1_700_000,
        "rent": 32_000,
    },
    "HK": {
        "name": "Ash Grove Garage",
        "location": "Hackney",
        "capacity": 108,
        "buy": 3_000_000,
        "rent": 53_000,
    },
    "HT": {
        "name": "Holloway Garage",
        "location": "Islington",
        "capacity": 157,
        "buy": 4_300_000,
        "rent": 78_000,
    },
    "DH": {
        "name": "Dawley Road Garage",
        "location": "Hillingdon",
        "capacity": 46,
        "buy": 1_000_000,
        "rent": 18_000,
    },
    "LI": {
        "name": "Lea Interchange Garage",
        "location": "Waltham Forest",
        "capacity": 143,
        "buy": 3_100_000,
        "rent": 57_000,
    },
    "MB": {
        "name": "Orpington Garage",
        "location": "Bromley",
        "capacity": 104,
        "buy": 2_200_000,
        "rent": 42_000,
    },
    "MG": {
        "name": "Morden Wharf Garage",
        "location": "Greenwich",
        "capacity": 88,
        "buy": 2_100_000,
        "rent": 38_000,
    },
    "N": {
        "name": "Norwood Garage",
        "location": "Lambeth",
        "capacity": 132,
        "buy": 3_600_000,
        "rent": 65_000,
    },
    "NP": {
        "name": "Northumberland Park Garage",
        "location": "Haringey",
        "capacity": 180,
        "buy": 4_300_000,
        "rent": 78_000,
    },
    "NS": {
        "name": "Romford Garage",
        "location": "Havering",
        "capacity": 88,
        "buy": 1_900_000,
        "rent": 35_000,
    },
    "NX": {
        "name": "New Cross Garage",
        "location": "Lewisham",
        "capacity": 100,
        "buy": 2_400_000,
        "rent": 44_000,
    },
    "PA": {
        "name": "Perivale West Garage",
        "location": "Ealing",
        "capacity": 60,
        "buy": 1_400_000,
        "rent": 26_000,
    },
    "PB": {
        "name": "Potters Bar Garage",
        "location": "Hertsmere",
        "capacity": 50,
        "buy": 800_000,
        "rent": 16_000,
    },
    "PD": {
        "name": "Plumstead Garage",
        "location": "Greenwich",
        "capacity": 80,
        "buy": 1_900_000,
        "rent": 35_000,
    },
    "PF": {
        "name": "Purfleet Garage",
        "location": "Thurrock",
        "capacity": 100,
        "buy": 1_700_000,
        "rent": 32_000,
    },
    "PM": {
        "name": "Peckham Garage",
        "location": "Southwark",
        "capacity": 120,
        "buy": 3_300_000,
        "rent": 59_000,
    },
    "Q": {
        "name": "Camberwell Garage",
        "location": "Southwark",
        "capacity": 199,
        "buy": 5_500_000,
        "rent": 99_000,
    },
    "QB": {
        "name": "Battersea Garage",
        "location": "Wandsworth",
        "capacity": 182,
        "buy": 5_000_000,
        "rent": 90_000,
    },
    "RA": {
        "name": "Waterloo Garage",
        "location": "Lambeth",
        "capacity": 36,
        "buy": 1_000_000,
        "rent": 18_000,
    },
    "RM": {
        "name": "Rainham Garage",
        "location": "Havering",
        "capacity": 90,
        "buy": 1_900_000,
        "rent": 36_000,
    },
    "RP": {
        "name": "Park Royal Garage",
        "location": "Brent",
        "capacity": 37,
        "buy": 900_000,
        "rent": 16_000,
    },
    "RR": {
        "name": "River Road Garage",
        "location": "Barking and Dagenham",
        "capacity": 209,
        "buy": 4_500_000,
        "rent": 84_000,
    },
    "S": {
        "name": "Shepherd's Bush Garage",
        "location": "Hammersmith and Fulham",
        "capacity": 94,
        "buy": 2_600_000,
        "rent": 47_000,
    },
    "SF": {
        "name": "Stamford Hill Garage",
        "location": "Hackney",
        "capacity": 74,
        "buy": 2_000_000,
        "rent": 37_000,
    },
    "SI": {
        "name": "Silvertown Garage",
        "location": "Newham",
        "capacity": 120,
        "buy": 2_900_000,
        "rent": 52_000,
    },
    "SM": {
        "name": "Sydenham Garage",
        "location": "Lewisham",
        "capacity": 45,
        "buy": 1_100_000,
        "rent": 20_000,
    },
    "SO": {
        "name": "Harrow Garage",
        "location": "Harrow",
        "capacity": 80,
        "buy": 1_700_000,
        "rent": 32_000,
    },
    "SW": {
        "name": "Stockwell Garage",
        "location": "Lambeth",
        "capacity": 158,
        "buy": 4_300_000,
        "rent": 78_000,
    },
    "T": {
        "name": "Leyton Garage",
        "location": "Waltham Forest",
        "capacity": 94,
        "buy": 2_000_000,
        "rent": 38_000,
    },
    "TB": {
        "name": "Bromley Garage",
        "location": "Bromley",
        "capacity": 83,
        "buy": 1_800_000,
        "rent": 33_000,
    },
    "TC": {
        "name": "Croydon (TC) Garage",
        "location": "Croydon",
        "capacity": 103,
        "buy": 2_200_000,
        "rent": 41_000,
    },
    "TF": {
        "name": "Twickenham Garage",
        "location": "Richmond upon Thames",
        "capacity": 129,
        "buy": 2_800_000,
        "rent": 52_000,
    },
    "TH": {
        "name": "Thornton Heath Garage",
        "location": "Croydon",
        "capacity": 78,
        "buy": 1_700_000,
        "rent": 31_000,
    },
    "TK": {
        "name": "Therapia Lane Garage",
        "location": "Sutton",
        "capacity": 50,
        "buy": 1_100_000,
        "rent": 20_000,
    },
    "TL": {
        "name": "Catford Garage",
        "location": "Lewisham",
        "capacity": 130,
        "buy": 3_100_000,
        "rent": 57_000,
    },
    "TV": {
        "name": "Tolworth Garage",
        "location": "Kingston upon Thames",
        "capacity": 77,
        "buy": 1_700_000,
        "rent": 31_000,
    },
    "UX": {
        "name": "Uxbridge Garage",
        "location": "Hillingdon",
        "capacity": 96,
        "buy": 2_100_000,
        "rent": 38_000,
    },
    "V": {
        "name": "Stamford Brook Garage",
        "location": "Hounslow",
        "capacity": 76,
        "buy": 1_600_000,
        "rent": 30_000,
    },
    "W": {
        "name": "Cricklewood Garage",
        "location": "Barnet",
        "capacity": 110,
        "buy": 2_400_000,
        "rent": 44_000,
    },
    "JE": {
        "name": "Wandsworth Garage",
        "location": "Wandsworth",
        "capacity": 80,
        "buy": 2_200_000,
        "rent": 40_000,
    },
    "WJ": {
        "name": "Willesden Junction Garage",
        "location": "Brent",
        "capacity": 70,
        "buy": 1_700_000,
        "rent": 30_000,
    },
    "WK": {
        "name": "Hounslow Heath Garage",
        "location": "Hounslow",
        "capacity": 90,
        "buy": 1_900_000,
        "rent": 36_000,
    },
    "WL": {
        "name": "Walworth Garage",
        "location": "Southwark",
        "capacity": 151,
        "buy": 4_200_000,
        "rent": 75_000,
    },
    "WN": {
        "name": "Wood Green Garage",
        "location": "Haringey",
        "capacity": 100,
        "buy": 2_400_000,
        "rent": 44_000,
    },
    "WS": {
        "name": "Hayes Garage",
        "location": "Hillingdon",
        "capacity": 80,
        "buy": 1_700_000,
        "rent": 32_000,
    },
    "X": {
        "name": "Westbourne Park Garage",
        "location": "Westminster",
        "capacity": 110,
        "buy": 3_000_000,
        "rent": 54_000,
    },
    "GY": {
        "name": "Grays Garage",
        "location": "Essex",
        "capacity": 57,
        "buy": 1_000_000,
        "rent": 18_000,
    },
    "HF": {
        "name": "Hatfield Garage",
        "location": "Hertfordshire",
        "capacity": 27,
        "buy": 500_000,
        "rent": 9_000,
    },
    "HH": {
        "name": "Hemel Hempstead Garage",
        "location": "Hertfordshire",
        "capacity": 90,
        "buy": 1_500_000,
        "rent": 28_000,
    },
    "CY": {
        "name": "Crawley Garage",
        "location": "West Sussex",
        "capacity": 80,
        "buy": 1_400_000,
        "rent": 25_000,
    },
    "KB": {
        "name": "Kangley Bridge Road Garage",
        "location": "Kent",
        "capacity": 34,
        "buy": 600_000,
        "rent": 11_000,
    },
}

# ============================================================
# BUS SHOP
# ============================================================

BUS_SHOP = {
    "Alexander Dennis Enviro200": 160_000,
    "Optare Solo SR": 130_000,
    "Optare Versa": 170_000,
    "Optare MetroCity": 200_000,
    "Wright StreetLite": 190_000,

    "Alexander Dennis Enviro400": 260_000,
    "Alexander Dennis Enviro400H": 310_000,
    "Wright Eclipse Gemini 2": 240_000,
    "Wright Eclipse Gemini 3": 300_000,
    "Volvo B5LH Wright Gemini 3": 350_000,
    "Volvo B5TL Wright Gemini 3": 320_000,
    "New Routemaster": 400_000,

    "Volvo B7TL Wright Gemini": 100_000,
    "Volvo B9TL Wright Gemini 2": 180_000,
    "Scania OmniCity DD": 150_000,
    "Dennis Dart SLF Plaxton Pointer": 60_000,
}


# ============================================================
# DRIVER MARKET
# ============================================================

FIRST_NAMES = [
    "James", "Oliver", "George", "Harry", "Noah",
    "Jack", "Charlie", "William", "Thomas", "Daniel",
    "Adam", "Ryan", "Michael", "David", "Alex",
]

LAST_NAMES = [
    "Smith", "Jones", "Williams", "Brown", "Taylor",
    "Davies", "Wilson", "Evans", "Thomas", "Roberts",
    "Johnson", "Walker", "Wright", "Thompson", "White",
]


# ============================================================
# HELPERS
# ============================================================

def get_operator(guild_id, owner_id):
    return conn.execute(
        """
        SELECT *
        FROM operators
        WHERE guild_id = ?
        AND owner_id = ?
        """,
        (guild_id, owner_id)
    ).fetchone()


def get_operator_code(guild_id, code):
    return conn.execute(
        """
        SELECT *
        FROM operators
        WHERE guild_id = ?
        AND UPPER(code) = UPPER(?)
        """,
        (guild_id, code)
    ).fetchone()


def require_operator(interaction):
    operator = get_operator(
        interaction.guild_id,
        interaction.user.id
    )

    if not operator:
        raise ValueError(
            "You do not own an operator. "
            "Use `/operator create` first."
        )

    return operator


def is_staff(interaction):
    if interaction.user.guild_permissions.administrator:
        return True

    return any(
        role.name.lower() == STAFF_ROLE.lower()
        for role in interaction.user.roles
    )


def add_transaction(
    guild_id,
    operator_id,
    amount,
    reason
):
    conn.execute(
        """
        UPDATE operators
        SET balance = balance + ?
        WHERE id = ?
        """,
        (amount, operator_id)
    )

    conn.execute(
        """
        INSERT INTO transactions
        (
            guild_id,
            operator_id,
            amount,
            reason,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            guild_id,
            operator_id,
            amount,
            reason,
            now().isoformat()
        )
    )

    conn.commit()


def get_garage_buses(garage_id):
    return conn.execute(
        """
        SELECT COUNT(*)
        FROM buses
        WHERE garage_id = ?
        """,
        (garage_id,)
    ).fetchone()[0]


def next_fleet_code(guild_id):
    count = conn.execute(
        """
        SELECT COUNT(*)
        FROM buses
        WHERE guild_id = ?
        """,
        (guild_id,)
    ).fetchone()[0]

    return f"BUS-{count + 1001:04d}"


def next_driver_code(guild_id):
    count = conn.execute(
        """
        SELECT COUNT(*)
        FROM drivers
        WHERE guild_id = ?
        """,
        (guild_id,)
    ).fetchone()[0]

    return f"DRV-{count + 1001:04d}"


async def post_to_channel(guild, channel_name, message):
    if not guild:
        return

    channel = discord.utils.get(
        guild.text_channels,
        name=channel_name
    )

    if channel:
        try:
            await channel.send(message)
        except discord.Forbidden:
            pass


# ============================================================
# BOT
# ============================================================

class BusGameBot(commands.Bot):

    async def setup_hook(self):

        self.tree.add_command(OperatorCommands())
        self.tree.add_command(GarageCommands())
        self.tree.add_command(BusCommands())
        self.tree.add_command(DriverCommands())
        self.tree.add_command(LoanCommands())
        self.tree.add_command(TenderCommands())
        self.tree.add_command(RouteCommands())
        self.tree.add_command(FinanceCommands())
        self.tree.add_command(MoneyCommands())

        if TEST_GUILD_ID:
            guild = discord.Object(
                id=int(TEST_GUILD_ID)
            )

            await self.tree.sync(guild=guild)

            print("Commands synced to test guild.")

        else:
            await self.tree.sync()
            print("Global commands synced.")

        if not check_tenders.is_running():
            check_tenders.start()

        if not weekly_finances.is_running():
            weekly_finances.start()

        if not refresh_driver_market.is_running():
            refresh_driver_market.start()

    async def on_ready(self):
        print(f"Logged in as {self.user}")


intents = discord.Intents.default()

bot = BusGameBot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# OPERATOR COMMANDS
# ============================================================

class OperatorCommands(app_commands.Group):

    def __init__(self):
        super().__init__(
            name="operator",
            description="Manage your bus operator"
        )

    @app_commands.command(
        name="create",
        description="Create your bus operator"
    )
    async def create(
        self,
        interaction: discord.Interaction,
        name: str,
        code: str
    ):

        if get_operator(
            interaction.guild_id,
            interaction.user.id
        ):
            return await interaction.response.send_message(
                "❌ You already own an operator.",
                ephemeral=True
            )

        code = code.upper().strip()

        if get_operator_code(
            interaction.guild_id,
            code
        ):
            return await interaction.response.send_message(
                "❌ That operator code is already taken.",
                ephemeral=True
            )

        conn.execute(
            """
            INSERT INTO operators
            (
                guild_id,
                owner_id,
                name,
                code,
                balance,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                interaction.guild_id,
                interaction.user.id,
                name,
                code,
                STARTING_MONEY,
                now().isoformat()
            )
        )

        conn.commit()

        operator = get_operator(
            interaction.guild_id,
            interaction.user.id
        )

        add_transaction(
            interaction.guild_id,
            operator["id"],
            STARTING_MONEY,
            "Starting capital"
        )

        await interaction.response.send_message(
            f"🏢 **{name} [{code}] created!**\n\n"
            f"💷 Starting capital: £{STARTING_MONEY:,}"
        )

    @app_commands.command(
        name="info",
        description="View operator information"
    )
    async def info(
        self,
        interaction: discord.Interaction,
        code: str | None = None
    ):

        if code:
            operator = get_operator_code(
                interaction.guild_id,
                code
            )
        else:
            operator = require_operator(interaction)

        if not operator:
            return await interaction.response.send_message(
                "❌ Operator not found.",
                ephemeral=True
            )

        buses = conn.execute(
            """
            SELECT COUNT(*)
            FROM buses
            WHERE operator_id = ?
            """,
            (operator["id"],)
        ).fetchone()[0]

        drivers = conn.execute(
            """
            SELECT COUNT(*)
            FROM drivers
            WHERE current_operator_id = ?
            """,
            (operator["id"],)
        ).fetchone()[0]

        garages = conn.execute(
            """
            SELECT COUNT(*)
            FROM garages
            WHERE operator_id = ?
            """,
            (operator["id"],)
        ).fetchone()[0]

        routes = conn.execute(
            """
            SELECT COUNT(*)
            FROM routes
            WHERE operator_id = ?
            """,
            (operator["id"],)
        ).fetchone()[0]

        embed = discord.Embed(
            title=f"🏢 {operator['name']} [{operator['code']}]"
        )

        embed.add_field(
            name="💷 Balance",
            value=f"£{operator['balance']:,}"
        )

        embed.add_field(
            name="🚌 Buses",
            value=str(buses)
        )

        embed.add_field(
            name="👤 Drivers",
            value=str(drivers)
        )

        embed.add_field(
            name="🏢 Garages",
            value=str(garages)
        )

        embed.add_field(
            name="🛣️ Routes",
            value=str(routes)
        )

        await interaction.response.send_message(
            embed=embed
        )


# ============================================================
# GARAGE COMMANDS
# ============================================================

class GarageCommands(app_commands.Group):

    def __init__(self):
        super().__init__(
            name="garage",
            description="Manage garages"
        )

    @app_commands.command(
        name="market",
        description="View available garages"
    )
    async def market(
        self,
        interaction: discord.Interaction
    ):

        lines = ["🏢 **GARAGE MARKET**"]

        for code, garage in GARAGES.items():
            taken = conn.execute(
                """
                SELECT 1
                FROM garages
                WHERE guild_id = ?
                AND UPPER(garage_code) = UPPER(?)
                """,
                (
                    interaction.guild_id,
                    code
                )
            ).fetchone()

            status = "🔴 Taken" if taken else "🟢 Available"

            lines.append(
                f"\n**{code} — {garage['name']}**\n"
                f"📍 {garage['location']}\n"
                f"🚌 Capacity: {garage['capacity']}\n"
                f"🔑 Rent: £{garage['rent']:,}/week\n"
                f"💷 Buy: £{garage['buy']:,}\n"
                f"{status}"
            )

        await interaction.response.send_message(
            "\n".join(lines)
        )

    @app_commands.command(
        name="info",
        description="View information about a garage"
    )
    async def info(
        self,
        interaction: discord.Interaction,
        garage: str
    ):

        code = garage.upper().strip()
        data = GARAGES.get(code)

        if not data:
            return await interaction.response.send_message(
                f"❌ Garage `{code}` was not found.",
                ephemeral=True
            )

        existing = conn.execute(
            """
            SELECT garages.*,
                   operators.name AS operator_name,
                   operators.code AS operator_code
            FROM garages
            JOIN operators
              ON operators.id = garages.operator_id
            WHERE garages.guild_id = ?
            AND UPPER(garages.garage_code) = UPPER(?)
            """,
            (
                interaction.guild_id,
                code
            )
        ).fetchone()

        if existing:
            used = get_garage_buses(existing["id"])

            status = (
                f"{existing['mode'].title()} by "
                f"{existing['operator_name']} "
                f"[{existing['operator_code']}]"
            )

            usage = (
                f"{used}/{existing['capacity']} buses"
            )
        else:
            status = "Available"
            usage = f"0/{data['capacity']} buses"

        embed = discord.Embed(
            title=f"🏢 {code} — {data['name']}"
        )

        embed.add_field(
            name="📍 Location",
            value=data["location"]
        )

        embed.add_field(
            name="🚌 Capacity",
            value=usage
        )

        embed.add_field(
            name="🔑 Estimated rent",
            value=f"£{data['rent']:,}/week"
        )

        embed.add_field(
            name="💷 Purchase price",
            value=f"£{data['buy']:,}"
        )

        embed.add_field(
            name="📄 Status",
            value=status,
            inline=False
        )

        await interaction.response.send_message(
            embed=embed
        )

    @app_commands.command(
        name="rent",
        description="Rent a garage using its code"
    )
    async def rent(
        self,
        interaction: discord.Interaction,
        garage: str
    ):

        operator = require_operator(interaction)

        code = garage.upper().strip()
        data = GARAGES.get(code)

        if not data:
            return await interaction.response.send_message(
                "❌ Garage not found.",
                ephemeral=True
            )

        already_taken = conn.execute(
            """
            SELECT 1
            FROM garages
            WHERE guild_id = ?
            AND UPPER(garage_code) = UPPER(?)
            """,
            (
                interaction.guild_id,
                code
            )
        ).fetchone()

        if already_taken:
            return await interaction.response.send_message(
                f"❌ Garage {code} is already occupied.",
                ephemeral=True
            )

        if operator["balance"] < data["rent"]:
            return await interaction.response.send_message(
                "❌ You cannot afford the first weekly rent payment.",
                ephemeral=True
            )

        conn.execute(
            """
            INSERT INTO garages
            (
                guild_id,
                operator_id,
                garage_code,
                name,
                location,
                capacity,
                mode,
                weekly_rent,
                purchase_price
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interaction.guild_id,
                operator["id"],
                code,
                data["name"],
                data["location"],
                data["capacity"],
                "rented",
                data["rent"],
                data["buy"]
            )
        )

        conn.commit()

        add_transaction(
            interaction.guild_id,
            operator["id"],
            -data["rent"],
            f"First rent payment for {code}"
        )

        await interaction.response.send_message(
            f"🔑 **Garage rented**\n\n"
            f"🏢 {code} — {data['name']}\n"
            f"📍 {data['location']}\n"
            f"🚌 Capacity: {data['capacity']}\n"
            f"💷 Weekly rent: £{data['rent']:,}"
        )

    @app_commands.command(
        name="buy",
        description="Buy a garage using its code"
    )
    async def buy(
        self,
        interaction: discord.Interaction,
        garage: str
    ):

        operator = require_operator(interaction)

        code = garage.upper().strip()
        data = GARAGES.get(code)

        if not data:
            return await interaction.response.send_message(
                "❌ Garage not found.",
                ephemeral=True
            )

        already_taken = conn.execute(
            """
            SELECT 1
            FROM garages
            WHERE guild_id = ?
            AND UPPER(garage_code) = UPPER(?)
            """,
            (
                interaction.guild_id,
                code
            )
        ).fetchone()

        if already_taken:
            return await interaction.response.send_message(
                "❌ This garage is already occupied.",
                ephemeral=True
            )

        if operator["balance"] < data["buy"]:
            return await interaction.response.send_message(
                f"❌ You need £{data['buy']:,}.",
                ephemeral=True
            )

        conn.execute(
            """
            INSERT INTO garages
            (
                guild_id,
                operator_id,
                garage_code,
                name,
                location,
                capacity,
                mode,
                weekly_rent,
                purchase_price
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interaction.guild_id,
                operator["id"],
                code,
                data["name"],
                data["location"],
                data["capacity"],
                "owned",
                0,
                data["buy"]
            )
        )

        conn.commit()

        add_transaction(
            interaction.guild_id,
            operator["id"],
            -data["buy"],
            f"Bought garage {code}"
        )

        await interaction.response.send_message(
            f"🏢 **Garage purchased**\n\n"
            f"{code} — {data['name']}\n"
            f"💷 Cost: £{data['buy']:,}"
        )

    @app_commands.command(
        name="list",
        description="View your garages"
    )
    async def list_garages(
        self,
        interaction: discord.Interaction
    ):

        operator = require_operator(interaction)

        garages = conn.execute(
            """
            SELECT *
            FROM garages
            WHERE operator_id = ?
            ORDER BY garage_code
            """,
            (operator["id"],)
        ).fetchall()

        if not garages:
            return await interaction.response.send_message(
                "You do not have any garages."
            )

        lines = ["🏢 **YOUR GARAGES**"]

        for garage in garages:
            used = get_garage_buses(garage["id"])

            lines.append(
                f"\n**{garage['garage_code']} — {garage['name']}**\n"
                f"📍 {garage['location']}\n"
                f"🚌 {used}/{garage['capacity']} buses\n"
                f"📄 {garage['mode'].title()}"
            )

        await interaction.response.send_message(
            "\n".join(lines)
        )


# ============================================================
# BUS COMMANDS
# ============================================================

class BusCommands(app_commands.Group):

    def __init__(self):
        super().__init__(
            name="bus",
            description="Manage your bus fleet"
        )

    @app_commands.command(
        name="shop",
        description="View buses for sale"
    )
    async def shop(
        self,
        interaction: discord.Interaction
    ):

        lines = ["🛒 **BUS SHOP**"]

        for model, price in BUS_SHOP.items():
            lines.append(
                f"🚌 **{model}** — £{price:,}"
            )

        await interaction.response.send_message(
            "\n".join(lines)
        )

    @app_commands.command(
        name="buy",
        description="Buy buses for one of your garages"
    )
    async def buy(
        self,
        interaction: discord.Interaction,
        model: str,
        quantity: app_commands.Range[int, 1, 50],
        garage: str
    ):

        operator = require_operator(interaction)

        model_name = next(
            (
                name for name in BUS_SHOP
                if name.lower() == model.lower()
            ),
            None
        )

        if not model_name:
            return await interaction.response.send_message(
                "❌ Bus model not found. Use `/bus shop`.",
                ephemeral=True
            )

        garage_code = garage.upper().strip()

        garage_row = conn.execute(
            """
            SELECT *
            FROM garages
            WHERE operator_id = ?
            AND UPPER(garage_code) = UPPER(?)
            """,
            (
                operator["id"],
                garage_code
            )
        ).fetchone()

        if not garage_row:
            return await interaction.response.send_message(
                f"❌ You do not own or rent Garage {garage_code}.",
                ephemeral=True
            )

        used = get_garage_buses(garage_row["id"])

        if used + quantity > garage_row["capacity"]:
            return await interaction.response.send_message(
                f"❌ Not enough space at {garage_code}.\n"
                f"Current: {used}/{garage_row['capacity']}",
                ephemeral=True
            )

        total_cost = BUS_SHOP[model_name] * quantity

        if operator["balance"] < total_cost:
            return await interaction.response.send_message(
                f"❌ You need £{total_cost:,}.",
                ephemeral=True
            )

        fleet_codes = []

        for _ in range(quantity):
            fleet_code = next_fleet_code(
                interaction.guild_id
            )

            conn.execute(
                """
                INSERT INTO buses
                (
                    guild_id,
                    fleet_code,
                    model,
                    operator_id,
                    garage_id,
                    purchase_price
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    interaction.guild_id,
                    fleet_code,
                    model_name,
                    operator["id"],
                    garage_row["id"],
                    BUS_SHOP[model_name]
                )
            )

            fleet_codes.append(fleet_code)

        conn.commit()

        add_transaction(
            interaction.guild_id,
            operator["id"],
            -total_cost,
            (
                f"Bought {quantity}x {model_name} "
                f"for Garage {garage_code}"
            )
        )

        await interaction.response.send_message(
            f"🚌 **Purchase complete**\n\n"
            f"Model: {model_name}\n"
            f"Quantity: {quantity}\n"
            f"Garage: {garage_code}\n"
            f"💷 Cost: £{total_cost:,}\n"
            f"Fleet numbers: {', '.join(fleet_codes)}"
        )

    @app_commands.command(
        name="transfer",
        description="Transfer a bus to another garage"
    )
    async def transfer(
        self,
        interaction: discord.Interaction,
        bus: str,
        garage: str
    ):

        operator = require_operator(interaction)

        bus_code = bus.upper().strip()
        garage_code = garage.upper().strip()

        bus_row = conn.execute(
            """
            SELECT *
            FROM buses
            WHERE guild_id = ?
            AND operator_id = ?
            AND UPPER(fleet_code) = UPPER(?)
            """,
            (
                interaction.guild_id,
                operator["id"],
                bus_code
            )
        ).fetchone()

        if not bus_row:
            return await interaction.response.send_message(
                "❌ You do not own that bus.",
                ephemeral=True
            )

        destination = conn.execute(
            """
            SELECT *
            FROM garages
            WHERE guild_id = ?
            AND operator_id = ?
            AND UPPER(garage_code) = UPPER(?)
            """,
            (
                interaction.guild_id,
                operator["id"],
                garage_code
            )
        ).fetchone()

        if not destination:
            return await interaction.response.send_message(
                f"❌ You do not own or rent Garage {garage_code}.",
                ephemeral=True
            )

        if bus_row["garage_id"] == destination["id"]:
            return await interaction.response.send_message(
                f"❌ That bus is already at {garage_code}.",
                ephemeral=True
            )

        used = get_garage_buses(destination["id"])

        if used >= destination["capacity"]:
            return await interaction.response.send_message(
                f"❌ Garage {garage_code} is full.",
                ephemeral=True
            )

        if operator["balance"] < BUS_TRANSFER_COST:
            return await interaction.response.send_message(
                "❌ You cannot afford the transfer cost.",
                ephemeral=True
            )

        old_code = "Unknown"

        if bus_row["garage_id"]:
            old_garage = conn.execute(
                """
                SELECT garage_code
                FROM garages
                WHERE id = ?
                """,
                (bus_row["garage_id"],)
            ).fetchone()

            if old_garage:
                old_code = old_garage["garage_code"]

        conn.execute(
            """
            UPDATE buses
            SET garage_id = ?,
                route_number = NULL,
                status = 'spare'
            WHERE id = ?
            """,
            (
                destination["id"],
                bus_row["id"]
            )
        )

        conn.commit()

        add_transaction(
            interaction.guild_id,
            operator["id"],
            -BUS_TRANSFER_COST,
            f"Transferred {bus_row['fleet_code']} "
            f"{old_code} -> {garage_code}"
        )

        await interaction.response.send_message(
            f"🔄 **BUS TRANSFER COMPLETE**\n\n"
            f"🚌 `{bus_row['fleet_code']}`\n"
            f"🚍 {bus_row['model']}\n"
            f"📍 {old_code} → {garage_code}\n"
            f"💷 Transfer cost: £{BUS_TRANSFER_COST:,}\n"
            f"📦 Status: Spare"
        )

    @app_commands.command(
        name="fleet",
        description="View your fleet"
    )
    async def fleet(
        self,
        interaction: discord.Interaction
    ):

        operator = require_operator(interaction)

        buses = conn.execute(
            """
            SELECT buses.*,
                   garages.garage_code
            FROM buses
            LEFT JOIN garages
              ON garages.id = buses.garage_id
            WHERE buses.operator_id = ?
            ORDER BY buses.fleet_code
            """,
            (operator["id"],)
        ).fetchall()

        if not buses:
            return await interaction.response.send_message(
                "Your fleet is empty."
            )

        lines = [
            f"🚌 **{operator['name']} FLEET ({len(buses)})**"
        ]

        for bus in buses[:50]:

            route = (
                bus["route_number"]
                if bus["route_number"]
                else "Spare"
            )

            garage = (
                bus["garage_code"]
                if bus["garage_code"]
                else "No garage"
            )

            lines.append(
                f"\n`{bus['fleet_code']}` — {bus['model']}\n"
                f"🏢 {garage}\n"
                f"🛣️ {route}\n"
                f"📊 {bus['status'].title()}"
            )

        await interaction.response.send_message(
            "\n".join(lines)
        )

    @app_commands.command(
        name="allocate",
        description="Allocate a bus to a route"
    )
    async def allocate(
        self,
        interaction: discord.Interaction,
        bus: str,
        route: str
    ):

        operator = require_operator(interaction)

        bus_row = conn.execute(
            """
            SELECT *
            FROM buses
            WHERE guild_id = ?
            AND operator_id = ?
            AND UPPER(fleet_code) = UPPER(?)
            """,
            (
                interaction.guild_id,
                operator["id"],
                bus
            )
        ).fetchone()

        if not bus_row:
            return await interaction.response.send_message(
                "❌ Bus not found.",
                ephemeral=True
            )

        route_row = conn.execute(
            """
            SELECT *
            FROM routes
            WHERE guild_id = ?
            AND operator_id = ?
            AND UPPER(route_number) = UPPER(?)
            """,
            (
                interaction.guild_id,
                operator["id"],
                route
            )
        ).fetchone()

        if not route_row:
            return await interaction.response.send_message(
                "❌ You do not own that route.",
                ephemeral=True
            )

        if not route_row["garage_id"]:
            return await interaction.response.send_message(
                "❌ Allocate the route to a garage first.",
                ephemeral=True
            )

        if bus_row["garage_id"] != route_row["garage_id"]:
            return await interaction.response.send_message(
                "❌ This bus is based at the wrong garage.",
                ephemeral=True
            )

        conn.execute(
            """
            UPDATE buses
            SET route_number = ?,
                status = 'allocated'
            WHERE id = ?
            """,
            (
                route.upper(),
                bus_row["id"]
            )
        )

        conn.commit()

        await interaction.response.send_message(
            f"✅ `{bus_row['fleet_code']}` allocated "
            f"to Route {route.upper()}."
        )


# ============================================================
# DRIVER COMMANDS
# ============================================================

class DriverCommands(app_commands.Group):

    def __init__(self):
        super().__init__(
            name="driver",
            description="Manage drivers"
        )

    @app_commands.command(
        name="market",
        description="View drivers currently available to hire"
    )
    async def market(
        self,
        interaction: discord.Interaction
    ):

        drivers = conn.execute(
            """
            SELECT *
            FROM driver_market
            WHERE guild_id = ?
            AND hired = 0
            AND expires_at > ?
            ORDER BY weekly_wage
            """,
            (
                interaction.guild_id,
                now().isoformat()
            )
        ).fetchall()

        if not drivers:
            return await interaction.response.send_message(
                "No drivers are currently available. "
                "The market will refresh soon."
            )

        lines = ["👤 **AVAILABLE DRIVERS**"]

        for driver in drivers:
            lines.append(
                f"\n**#{driver['id']} — {driver['name']}**\n"
                f"💷 £{driver['weekly_wage']:,}/week"
            )

        await interaction.response.send_message(
            "\n".join(lines)
        )

    @app_commands.command(
        name="hire",
        description="Hire a driver from the market"
    )
    async def hire(
        self,
        interaction: discord.Interaction,
        driver_id: int
    ):

        operator = require_operator(interaction)

        market_driver = conn.execute(
            """
            SELECT *
            FROM driver_market
            WHERE id = ?
            AND guild_id = ?
            AND hired = 0
            AND expires_at > ?
            """,
            (
                driver_id,
                interaction.guild_id,
                now().isoformat()
            )
        ).fetchone()

        if not market_driver:
            return await interaction.response.send_message(
                "❌ That driver is no longer available.",
                ephemeral=True
            )

        driver_code = next_driver_code(
            interaction.guild_id
        )

        conn.execute(
            """
            INSERT INTO drivers
            (
                guild_id,
                driver_code,
                name,
                home_operator_id,
                current_operator_id,
                weekly_wage
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                interaction.guild_id,
                driver_code,
                market_driver["name"],
                operator["id"],
                operator["id"],
                market_driver["weekly_wage"]
            )
        )

        conn.execute(
            """
            UPDATE driver_market
            SET hired = 1
            WHERE id = ?
            """,
            (driver_id,)
        )

        conn.commit()

        await interaction.response.send_message(
            f"👤 **DRIVER HIRED**\n\n"
            f"`{driver_code}` — {market_driver['name']}\n"
            f"💷 Weekly wage: £{market_driver['weekly_wage']:,}"
        )

    @app_commands.command(
        name="list",
        description="View your drivers"
    )
    async def list_drivers(
        self,
        interaction: discord.Interaction
    ):

        operator = require_operator(interaction)

        drivers = conn.execute(
            """
            SELECT *
            FROM drivers
            WHERE current_operator_id = ?
            ORDER BY driver_code
            """,
            (operator["id"],)
        ).fetchall()

        if not drivers:
            return await interaction.response.send_message(
                "You have no drivers."
            )

        lines = [
            f"👥 **YOUR DRIVERS ({len(drivers)})**"
        ]

        for driver in drivers[:50]:

            route = (
                driver["route_number"]
                if driver["route_number"]
                else "Spare"
            )

            lines.append(
                f"\n`{driver['driver_code']}` — {driver['name']}\n"
                f"🛣️ {route}\n"
                f"💷 £{driver['weekly_wage']:,}/week"
            )

        await interaction.response.send_message(
            "\n".join(lines)
        )

    @app_commands.command(
        name="allocate",
        description="Allocate a driver to a route"
    )
    async def allocate(
        self,
        interaction: discord.Interaction,
        driver: str,
        route: str
    ):

        operator = require_operator(interaction)

        driver_row = conn.execute(
            """
            SELECT *
            FROM drivers
            WHERE guild_id = ?
            AND current_operator_id = ?
            AND UPPER(driver_code) = UPPER(?)
            """,
            (
                interaction.guild_id,
                operator["id"],
                driver
            )
        ).fetchone()

        if not driver_row:
            return await interaction.response.send_message(
                "❌ Driver not found.",
                ephemeral=True
            )

        route_row = conn.execute(
            """
            SELECT *
            FROM routes
            WHERE guild_id = ?
            AND operator_id = ?
            AND UPPER(route_number) = UPPER(?)
            """,
            (
                interaction.guild_id,
                operator["id"],
                route
            )
        ).fetchone()

        if not route_row:
            return await interaction.response.send_message(
                "❌ Route not found.",
                ephemeral=True
            )

        conn.execute(
            """
            UPDATE drivers
            SET route_number = ?,
                status = 'allocated'
            WHERE id = ?
            """,
            (
                route.upper(),
                driver_row["id"]
            )
        )

        conn.commit()

        await interaction.response.send_message(
            f"✅ `{driver_row['driver_code']}` allocated "
            f"to Route {route.upper()}."
        )


# ============================================================
# LOANS
# ============================================================

class LoanCommands(app_commands.Group):

    def __init__(self):
        super().__init__(
            name="loan",
            description="Manage driver loans"
        )

    @app_commands.command(
        name="offer",
        description="Offer a driver to another operator"
    )
    async def offer(
        self,
        interaction: discord.Interaction,
        driver: str,
        operator_code: str,
        days: app_commands.Range[int, 1, 365]
    ):

        operator = require_operator(interaction)

        driver_row = conn.execute(
            """
            SELECT *
            FROM drivers
            WHERE guild_id = ?
            AND current_operator_id = ?
            AND home_operator_id = ?
            AND UPPER(driver_code) = UPPER(?)
            """,
            (
                interaction.guild_id,
                operator["id"],
                operator["id"],
                driver
            )
        ).fetchone()

        borrower = get_operator_code(
            interaction.guild_id,
            operator_code
        )

        if not driver_row or not borrower:
            return await interaction.response.send_message(
                "❌ Driver or operator not found.",
                ephemeral=True
            )

        if borrower["id"] == operator["id"]:
            return await interaction.response.send_message(
                "❌ You cannot loan a driver to yourself.",
                ephemeral=True
            )

        expiry = now() + timedelta(days=days)

        cursor = conn.execute(
            """
            INSERT INTO loans
            (
                guild_id,
                driver_id,
                lender_operator_id,
                borrower_operator_id,
                status,
                expires_at,
                created_at
            )
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                interaction.guild_id,
                driver_row["id"],
                operator["id"],
                borrower["id"],
                expiry.isoformat(),
                now().isoformat()
            )
        )

        conn.commit()

        await interaction.response.send_message(
            f"🤝 Loan offer **#{cursor.lastrowid}** sent to "
            f"{borrower['name']} [{borrower['code']}]."
        )

    @app_commands.command(
        name="pending",
        description="View pending loan offers"
    )
    async def pending(
        self,
        interaction: discord.Interaction
    ):

        operator = require_operator(interaction)

        loans = conn.execute(
            """
            SELECT loans.*,
                   drivers.driver_code,
                   drivers.name
            FROM loans
            JOIN drivers
              ON drivers.id = loans.driver_id
            WHERE loans.borrower_operator_id = ?
            AND loans.status = 'pending'
            """,
            (operator["id"],)
        ).fetchall()

        if not loans:
            return await interaction.response.send_message(
                "You have no pending loans."
            )

        lines = ["🤝 **PENDING LOANS**"]

        for loan in loans:
            lines.append(
                f"\n#{loan['id']} — "
                f"`{loan['driver_code']}` {loan['name']}"
            )

        await interaction.response.send_message(
            "\n".join(lines)
        )

    @app_commands.command(
        name="accept",
        description="Accept a driver loan"
    )
    async def accept(
        self,
        interaction: discord.Interaction,
        loan_id: int
    ):

        operator = require_operator(interaction)

        loan = conn.execute(
            """
            SELECT *
            FROM loans
            WHERE id = ?
            AND borrower_operator_id = ?
            AND status = 'pending'
            """,
            (
                loan_id,
                operator["id"]
            )
        ).fetchone()

        if not loan:
            return await interaction.response.send_message(
                "❌ Loan not found.",
                ephemeral=True
            )

        conn.execute(
            """
            UPDATE loans
            SET status = 'active'
            WHERE id = ?
            """,
            (loan_id,)
        )

        conn.execute(
            """
            UPDATE drivers
            SET current_operator_id = ?,
                route_number = NULL,
                status = 'spare'
            WHERE id = ?
            """,
            (
                operator["id"],
                loan["driver_id"]
            )
        )

        conn.commit()

        await interaction.response.send_message(
            "✅ Driver loan accepted."
        )


# ============================================================
# TENDERS
# ============================================================

class TenderCommands(app_commands.Group):

    def __init__(self):
        super().__init__(
            name="tender",
            description="Manage route tenders"
        )

    @app_commands.command(
        name="create",
        description="Create a route tender"
    )
    async def create(
        self,
        interaction: discord.Interaction,
        route: str,
        required_pvr: app_commands.Range[int, 1, 500],
        vehicle_type: str,
        weekly_income: app_commands.Range[int, 1, 100_000_000],
        contract_weeks: app_commands.Range[int, 1, 520],
        closes_in_hours: app_commands.Range[int, 1, 720]
    ):

        if not is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Game Staff only.",
                ephemeral=True
            )

        route = route.upper().strip()

        existing = conn.execute(
            """
            SELECT *
            FROM tenders
            WHERE guild_id = ?
            AND route_number = ?
            AND status = 'open'
            """,
            (
                interaction.guild_id,
                route
            )
        ).fetchone()

        if existing:
            return await interaction.response.send_message(
                "❌ That route already has an open tender.",
                ephemeral=True
            )

        close_time = now() + timedelta(
            hours=closes_in_hours
        )

        cursor = conn.execute(
            """
            INSERT INTO tenders
            (
                guild_id,
                route_number,
                required_pvr,
                vehicle_type,
                weekly_income,
                contract_weeks,
                close_at,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'open')
            """,
            (
                interaction.guild_id,
                route,
                required_pvr,
                vehicle_type,
                weekly_income,
                contract_weeks,
                close_time.isoformat()
            )
        )

        conn.commit()

        tender_id = cursor.lastrowid

        message = (
            f"📋 **NEW TENDER #{tender_id}**\n\n"
            f"🛣️ Route: **{route}**\n"
            f"🚌 PVR: **{required_pvr}**\n"
            f"🚍 Vehicle type: **{vehicle_type}**\n"
            f"💷 Weekly contract value: **£{weekly_income:,}**\n"
            f"📅 Contract length: **{contract_weeks} weeks**\n"
            f"⏰ Closes: <t:{int(close_time.timestamp())}:R>\n\n"
            f"Use `/tender bid` to bid."
        )

        await interaction.response.send_message(message)

        await post_to_channel(
            interaction.guild,
            "new-tenders",
            message
        )

    @app_commands.command(
        name="bid",
        description="Submit a bid on a tender"
    )
    async def bid(
        self,
        interaction: discord.Interaction,
        tender_id: int,
        amount: app_commands.Range[int, 1, 1_000_000_000],
        notes: str = ""
    ):

        operator = require_operator(interaction)

        tender = conn.execute(
            """
            SELECT *
            FROM tenders
            WHERE id = ?
            AND guild_id = ?
            AND status = 'open'
            """,
            (
                tender_id,
                interaction.guild_id
            )
        ).fetchone()

        if not tender:
            return await interaction.response.send_message(
                "❌ Tender not found or closed.",
                ephemeral=True
            )

        if datetime.fromisoformat(
            tender["close_at"]
        ) <= now():

            return await interaction.response.send_message(
                "❌ This tender has closed.",
                ephemeral=True
            )

        conn.execute(
            """
            INSERT INTO bids
            (
                tender_id,
                operator_id,
                amount,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(tender_id, operator_id)
            DO UPDATE SET
                amount = excluded.amount,
                notes = excluded.notes,
                created_at = excluded.created_at
            """,
            (
                tender_id,
                operator["id"],
                amount,
                notes,
                now().isoformat()
            )
        )

        conn.commit()

        await interaction.response.send_message(
            f"📨 Your bid for Tender #{tender_id} has been submitted.\n"
            f"💷 Bid: £{amount:,}",
            ephemeral=True
        )

    @app_commands.command(
        name="list",
        description="View open tenders"
    )
    async def list_tenders(
        self,
        interaction: discord.Interaction
    ):

        tenders = conn.execute(
            """
            SELECT *
            FROM tenders
            WHERE guild_id = ?
            AND status = 'open'
            ORDER BY close_at
            """,
            (interaction.guild_id,)
        ).fetchall()

        if not tenders:
            return await interaction.response.send_message(
                "There are no open tenders."
            )

        lines = ["📋 **OPEN TENDERS**"]

        for tender in tenders:
            close_time = datetime.fromisoformat(
                tender["close_at"]
            )

            lines.append(
                f"\n**#{tender['id']} — Route {tender['route_number']}**\n"
                f"🚌 PVR: {tender['required_pvr']}\n"
                f"🚍 {tender['vehicle_type']}\n"
                f"💷 £{tender['weekly_income']:,}/week\n"
                f"⏰ <t:{int(close_time.timestamp())}:R>"
            )

        await interaction.response.send_message(
            "\n".join(lines)
        )


# ============================================================
# ROUTES
# ============================================================

class RouteCommands(app_commands.Group):

    def __init__(self):
        super().__init__(
            name="route",
            description="Manage your won routes"
        )

    @app_commands.command(
        name="garage",
        description="Allocate a route to one of your garages"
    )
    async def garage(
        self,
        interaction: discord.Interaction,
        route: str,
        garage: str
    ):

        operator = require_operator(interaction)

        route_number = route.upper().strip()
        garage_code = garage.upper().strip()

        route_row = conn.execute(
            """
            SELECT *
            FROM routes
            WHERE guild_id = ?
            AND operator_id = ?
            AND UPPER(route_number) = UPPER(?)
            """,
            (
                interaction.guild_id,
                operator["id"],
                route_number
            )
        ).fetchone()

        if not route_row:
            return await interaction.response.send_message(
                "❌ You do not own that route.",
                ephemeral=True
            )

        garage_row = conn.execute(
            """
            SELECT *
            FROM garages
            WHERE guild_id = ?
            AND operator_id = ?
            AND UPPER(garage_code) = UPPER(?)
            """,
            (
                interaction.guild_id,
                operator["id"],
                garage_code
            )
        ).fetchone()

        if not garage_row:
            return await interaction.response.send_message(
                f"❌ You do not own or rent Garage {garage_code}.",
                ephemeral=True
            )

        conn.execute(
            """
            UPDATE routes
            SET garage_id = ?
            WHERE id = ?
            """,
            (
                garage_row["id"],
                route_row["id"]
            )
        )

        conn.commit()

        await interaction.response.send_message(
            f"🏢 Route {route_number} is now based at "
            f"{garage_code} — {garage_row['name']}."
        )

    @app_commands.command(
        name="list",
        description="View your routes"
    )
    async def list_routes(
        self,
        interaction: discord.Interaction
    ):

        operator = require_operator(interaction)

        routes = conn.execute(
            """
            SELECT routes.*,
                   garages.garage_code,
                   garages.name AS garage_name
            FROM routes
            LEFT JOIN garages
              ON garages.id = routes.garage_id
            WHERE routes.operator_id = ?
            ORDER BY routes.route_number
            """,
            (operator["id"],)
        ).fetchall()

        if not routes:
            return await interaction.response.send_message(
                "You have not won any routes."
            )

        lines = ["🛣️ **YOUR ROUTES**"]

        for route in routes:

            status = (
                "🟢 Operating"
                if route["active"]
                else "⚪ Not operating"
            )

            garage = (
                route["garage_code"]
                if route["garage_code"]
                else "Not allocated"
            )

            lines.append(
                f"\n**Route {route['route_number']}**\n"
                f"🏢 Garage: {garage}\n"
                f"🚌 PVR: {route['required_pvr']}\n"
                f"🚍 {route['vehicle_type']}\n"
                f"{status}"
            )

        await interaction.response.send_message(
            "\n".join(lines)
        )

    @app_commands.command(
        name="start",
        description="Start operating a route"
    )
    async def start(
        self,
        interaction: discord.Interaction,
        route: str
    ):

        operator = require_operator(interaction)

        route_number = route.upper().strip()

        route_row = conn.execute(
            """
            SELECT *
            FROM routes
            WHERE guild_id = ?
            AND operator_id = ?
            AND UPPER(route_number) = UPPER(?)
            """,
            (
                interaction.guild_id,
                operator["id"],
                route_number
            )
        ).fetchone()

        if not route_row:
            return await interaction.response.send_message(
                "❌ You do not own that route.",
                ephemeral=True
            )

        if not route_row["garage_id"]:
            return await interaction.response.send_message(
                "❌ Allocate the route to a garage first.",
                ephemeral=True
            )

        bus_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM buses
            WHERE operator_id = ?
            AND garage_id = ?
            AND route_number = ?
            """,
            (
                operator["id"],
                route_row["garage_id"],
                route_number
            )
        ).fetchone()[0]

        driver_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM drivers
            WHERE current_operator_id = ?
            AND route_number = ?
            """,
            (
                operator["id"],
                route_number
            )
        ).fetchone()[0]

        required = route_row["required_pvr"]

        if bus_count < required:
            return await interaction.response.send_message(
                f"❌ Route requires {required} buses, "
                f"but only {bus_count} are allocated.",
                ephemeral=True
            )

        if driver_count < required:
            return await interaction.response.send_message(
                f"❌ Route requires {required} drivers, "
                f"but only {driver_count} are allocated.",
                ephemeral=True
            )

        conn.execute(
            """
            UPDATE routes
            SET active = 1
            WHERE id = ?
            """,
            (route_row["id"],)
        )

        conn.commit()

        await interaction.response.send_message(
            f"🟢 Route {route_number} is now operating!"
        )


# ============================================================
# FINANCE
# ============================================================

class FinanceCommands(app_commands.Group):

    def __init__(self):
        super().__init__(
            name="finance",
            description="View operator finances"
        )

    @app_commands.command(
        name="balance",
        description="View your balance"
    )
    async def balance(
        self,
        interaction: discord.Interaction
    ):

        operator = require_operator(interaction)

        await interaction.response.send_message(
            f"💷 **{operator['name']} [{operator['code']}]**\n"
            f"Balance: **£{operator['balance']:,}**"
        )

    @app_commands.command(
        name="history",
        description="View recent transactions"
    )
    async def history(
        self,
        interaction: discord.Interaction
    ):

        operator = require_operator(interaction)

        transactions = conn.execute(
            """
            SELECT *
            FROM transactions
            WHERE operator_id = ?
            ORDER BY id DESC
            LIMIT 20
            """,
            (operator["id"],)
        ).fetchall()

        if not transactions:
            return await interaction.response.send_message(
                "No transactions found."
            )

        lines = ["📜 **RECENT TRANSACTIONS**"]

        for transaction in transactions:

            symbol = (
                "➕"
                if transaction["amount"] >= 0
                else "➖"
            )

            lines.append(
                f"{symbol} £{abs(transaction['amount']):,} "
                f"— {transaction['reason']}"
            )

        await interaction.response.send_message(
            "\n".join(lines)
        )


# ============================================================
# STAFF MONEY
# ============================================================

class MoneyCommands(app_commands.Group):

    def __init__(self):
        super().__init__(
            name="money",
            description="Staff money controls"
        )

    @app_commands.command(
        name="give",
        description="Give money to an operator"
    )
    async def give(
        self,
        interaction: discord.Interaction,
        operator_code: str,
        amount: app_commands.Range[
            int,
            1,
            1_000_000_000
        ]
    ):

        if not is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Game Staff only.",
                ephemeral=True
            )

        operator = get_operator_code(
            interaction.guild_id,
            operator_code
        )

        if not operator:
            return await interaction.response.send_message(
                "❌ Operator not found.",
                ephemeral=True
            )

        add_transaction(
            interaction.guild_id,
            operator["id"],
            amount,
            f"Money given by {interaction.user}"
        )

        await interaction.response.send_message(
            f"➕ Added £{amount:,} to "
            f"{operator['name']} [{operator['code']}]."
        )


# ============================================================
# AUTOMATIC TENDER CLOSING
# ============================================================

@tasks.loop(seconds=TENDER_CHECK_SECONDS)
async def check_tenders():

    expired = conn.execute(
        """
        SELECT *
        FROM tenders
        WHERE status = 'open'
        AND close_at <= ?
        """,
        (now().isoformat(),)
    ).fetchall()

    for tender in expired:

        bids = conn.execute(
            """
            SELECT bids.*,
                   operators.name AS operator_name,
                   operators.code AS operator_code
            FROM bids
            JOIN operators
              ON operators.id = bids.operator_id
            WHERE bids.tender_id = ?
            ORDER BY bids.amount ASC,
                     bids.created_at ASC
            """,
            (tender["id"],)
        ).fetchall()

        guild = bot.get_guild(
            tender["guild_id"]
        )

        if not bids:

            conn.execute(
                """
                UPDATE tenders
                SET status = 'cancelled'
                WHERE id = ?
                """,
                (tender["id"],)
            )

            conn.commit()

            await post_to_channel(
                guild,
                "tender-results",
                f"📋 **TENDER #{tender['id']} CLOSED**\n\n"
                f"Route {tender['route_number']} received no bids."
            )

            continue

        winner = bids[0]

        conn.execute(
            """
            UPDATE tenders
            SET status = 'awarded',
                winner_operator_id = ?
            WHERE id = ?
            """,
            (
                winner["operator_id"],
                tender["id"]
            )
        )

        conn.execute(
            """
            INSERT OR REPLACE INTO routes
            (
                guild_id,
                route_number,
                operator_id,
                garage_id,
                required_pvr,
                vehicle_type,
                weekly_income,
                active
            )
            VALUES (?, ?, ?, NULL, ?, ?, ?, 0)
            """,
            (
                tender["guild_id"],
                tender["route_number"],
                winner["operator_id"],
                tender["required_pvr"],
                tender["vehicle_type"],
                tender["weekly_income"]
            )
        )

        conn.commit()

        message = (
            f"🏆 **TENDER RESULT**\n\n"
            f"📋 Tender #{tender['id']}\n"
            f"🛣️ Route: {tender['route_number']}\n"
            f"🏢 Winner: {winner['operator_name']} "
            f"[{winner['operator_code']}]\n"
            f"💷 Winning bid: £{winner['amount']:,}\n"
            f"🚌 PVR: {tender['required_pvr']}\n\n"
            f"The operator must now allocate a garage, "
            f"buses and drivers."
        )

        await post_to_channel(
            guild,
            "tender-results",
            message
        )


@check_tenders.before_loop
async def before_check_tenders():
    await bot.wait_until_ready()


# ============================================================
# DRIVER MARKET REFRESH
# ============================================================

@tasks.loop(hours=DRIVER_MARKET_HOURS)
async def refresh_driver_market():

    for guild in bot.guilds:

        conn.execute(
            """
            UPDATE driver_market
            SET hired = 1
            WHERE guild_id = ?
            AND expires_at <= ?
            """,
            (
                guild.id,
                now().isoformat()
            )
        )

        available = conn.execute(
            """
            SELECT COUNT(*)
            FROM driver_market
            WHERE guild_id = ?
            AND hired = 0
            AND expires_at > ?
            """,
            (
                guild.id,
                now().isoformat()
            )
        ).fetchone()[0]

        needed = max(0, 10 - available)

        for _ in range(needed):

            name = (
                f"{random.choice(FIRST_NAMES)} "
                f"{random.choice(LAST_NAMES)}"
            )

            wage = random.randrange(
                650,
                1201,
                50
            )

            created = now()
            expires = created + timedelta(
                hours=DRIVER_MARKET_HOURS
            )

            conn.execute(
                """
                INSERT INTO driver_market
                (
                    guild_id,
                    name,
                    weekly_wage,
                    created_at,
                    expires_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    guild.id,
                    name,
                    wage,
                    created.isoformat(),
                    expires.isoformat()
                )
            )

        conn.commit()


@refresh_driver_market.before_loop
async def before_driver_market():
    await bot.wait_until_ready()


# ============================================================
# WEEKLY FINANCES
# ============================================================

@tasks.loop(hours=24)
async def weekly_finances():

    # Monday
    if now().weekday() != 0:
        return

    operators = conn.execute(
        """
        SELECT *
        FROM operators
        """
    ).fetchall()

    for operator in operators:

        routes = conn.execute(
            """
            SELECT *
            FROM routes
            WHERE operator_id = ?
            AND active = 1
            """,
            (operator["id"],)
        ).fetchall()

        income = sum(
            route["weekly_income"]
            for route in routes
        )

        wages = conn.execute(
            """
            SELECT COALESCE(
                SUM(weekly_wage),
                0
            )
            FROM drivers
            WHERE current_operator_id = ?
            """,
            (operator["id"],)
        ).fetchone()[0]

        rent = conn.execute(
            """
            SELECT COALESCE(
                SUM(weekly_rent),
                0
            )
            FROM garages
            WHERE operator_id = ?
            AND mode = 'rented'
            """,
            (operator["id"],)
        ).fetchone()[0]

        net = income - wages - rent

        add_transaction(
            operator["guild_id"],
            operator["id"],
            net,
            (
                f"Weekly operations: "
                f"Income £{income:,}, "
                f"Wages £{wages:,}, "
                f"Rent £{rent:,}"
            )
        )


@weekly_finances.before_loop
async def before_weekly_finances():
    await bot.wait_until_ready()


# ============================================================
# ERROR HANDLER
# ============================================================

@bot.tree.error
async def command_error(
    interaction: discord.Interaction,
    error
):

    if isinstance(error, ValueError):
        message = f"❌ {error}"

    elif isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):
        message = "❌ You do not have permission to use this command."

    elif isinstance(
        error,
        app_commands.errors.CommandOnCooldown
    ):
        message = "❌ This command is on cooldown."

    else:
        print(
            "COMMAND ERROR:",
            repr(error)
        )

        message = (
            "❌ Something went wrong while "
            "running that command."
        )

    if interaction.response.is_done():
        await interaction.followup.send(
            message,
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            message,
            ephemeral=True
        )


# ============================================================
# START
# ============================================================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is not set."
    )


bot.run(TOKEN)