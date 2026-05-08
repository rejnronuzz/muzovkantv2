import discord
from discord.ext import commands
from discord import app_commands

from cogs.player import get_player, fmt_duration

class Queue(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── /queue ────────────────────────────────
    @app_commands.command(name="queue", description="Показать очередь треков")
    async def queue(self, interaction: discord.Interaction):
        player = get_player(interaction.guild.id)
        embed = discord.Embed(title="📋 Очередь треков", color=0x5865F2)

        if player.current:
            duration = fmt_duration(player.current.duration) if player.current.duration else "—"
            embed.add_field(
                name="▶️ Музончик играет",
                value=f"**{player.current.title}** `{duration}`",
                inline=False
            )

        if player.queue:
            lines = []
            for i, url in enumerate(list(player.queue)[:10], 1):
                lines.append(f"`{i}.` {url}")
            if len(player.queue) > 10:
                lines.append(f"... и ещё {len(player.queue) - 10} треков")
            embed.add_field(
                name=f"В очереди ({len(player.queue)})",
                value="\n".join(lines),
                inline=False
            )
        else:
            embed.add_field(
                name="Очередь пуста",
                value="Добавь треки через `/play`",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    # ── /clear ────────────────────────────────
    @app_commands.command(name="clear", description="Очистить очередь треков")
    async def clear(self, interaction: discord.Interaction):
        player = get_player(interaction.guild.id)
        count = len(player.queue)
        player.queue.clear()
        await interaction.response.send_message(f"🗑️ Лэ брат вьебал ({count} треков назхуй).")

    # ── /remove ───────────────────────────────
    @app_commands.command(name="remove", description="Вьебать трек из очереди по номеру")
    @app_commands.describe(position="Номер трека в очереди")
    async def remove(self, interaction: discord.Interaction, position: int):
        player = get_player(interaction.guild.id)
        if not player.queue:
            return await interaction.response.send_message("Очередь пуста.")
        if not 1 <= position <= len(player.queue):
            return await interaction.response.send_message(f"❌ Укажи номер от 1 до {len(player.queue)}.")

        queue_list = list(player.queue)
        removed = queue_list.pop(position - 1)
        player.queue.clear()
        player.queue.extend(queue_list)
        await interaction.response.send_message(f"🗑️ Удалён трек `{position}`: {removed}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Queue(bot))