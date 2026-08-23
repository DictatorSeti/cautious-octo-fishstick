import sqlite3
import discord
from discord import app_commands

DATABASE_PATH = "bus_game.db"


def setup_garages():
    conn = sqlite3.connect(DATABASE_PATH)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS garages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            location TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            price INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()


class GarageCommands(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="garage",
            description="Manage garages"
        )

    @app_commands.command(name="add", description="Add a garage to the market")
    @app_commands.describe(
        name="Garage name",
        location="Garage location",
        capacity="Maximum number of buses",
        price="Purchase price"
    )
    async def add_garage(
        self,
        interaction: discord.Interaction,
        name: str,
        location: str,
        capacity: int,
        price: int
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You do not have permission to add garages.",
                ephemeral=True
            )
            return

        conn = sqlite3.connect(DATABASE_PATH)

        try:
            conn.execute(
                """
                INSERT INTO garages (name, location, capacity, price)
                VALUES (?, ?, ?, ?)
                """,
                (name, location, capacity, price)
            )

            conn.commit()

            await interaction.response.send_message(
                f"🏢 **{name}** added to the garage market!\n"
                f"📍 **Location:** {location}\n"
                f"🚌 **Capacity:** {capacity}\n"
                f"💰 **Price:** £{price:,}"
            )

        except sqlite3.IntegrityError:
            await interaction.response.send_message(
                "❌ A garage with that name already exists.",
                ephemeral=True
            )

        finally:
            conn.close()

    @app_commands.command(name="list", description="View available garages")
    async def list_garages(self, interaction: discord.Interaction):
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name, location, capacity, price
            FROM garages
            ORDER BY price ASC
        """)

        garages = cursor.fetchall()
        conn.close()

        if not garages:
            await interaction.response.send_message(
                "🏢 There are currently no garages available."
            )
            return

        text = "## 🏢 Available Garages\n\n"

        for name, location, capacity, price in garages:
            text += (
                f"**{name}**\n"
                f"📍 {location}\n"
                f"🚌 Capacity: {capacity}\n"
                f"💰 £{price:,}\n\n"
            )

        await interaction.response.send_message(text)
