import discord
from discord.ext import commands
from discord import app_commands
import asyncio

from cogs.player import (
    YTDLSource, get_player,
    now_playing_embed, fmt_duration
)

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Внутренний метод: следующий трек ──────
    async def play_next(self, guild: discord.Guild, channel: discord.TextChannel):
        player = get_player(guild.id)
        vc: discord.VoiceClient = guild.voice_client

        if not vc:
            return

        # Повтор текущего трека
        if player.loop and player.current:
            try:
                source = await YTDLSource.from_url(player.current.url, loop=self.bot.loop)
                source.volume = player.volume
                player.current = source
                vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(
                    self.play_next(guild, channel), self.bot.loop))
                await channel.send(embed=now_playing_embed(source))
            except Exception as e:
                await channel.send(f"❌ Ошибка повтора: {e}")
            return

        if player.queue:
            url = player.queue.popleft()
            try:
                source = await YTDLSource.from_url(url, loop=self.bot.loop)
            except Exception as e:
                await channel.send(f"❌ Ошибка воспроизведения: {e}")
                return
            source.volume = player.volume
            player.current = source
            vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(
                self.play_next(guild, channel), self.bot.loop))
            await channel.send(embed=now_playing_embed(source))
        else:
            player.current = None
            await channel.send("✅ Очередь закончилась.")

    # ── /play ─────────────────────────────────
    @app_commands.command(name="play", description="Воспроизвести трек по названию или ссылке")
    @app_commands.describe(query="Название песни или YouTube ссылка")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        if not interaction.user.voice:
            return await interaction.followup.send("❌ Сначала зайди в голосовой канал!")

        vc: discord.VoiceClient = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()
        elif interaction.user.voice.channel != vc.channel:
            await vc.move_to(interaction.user.voice.channel)

        player = get_player(interaction.guild.id)

        try:
            source = await YTDLSource.from_url(query, loop=self.bot.loop)
        except Exception as e:
            return await interaction.followup.send(f"❌ Не удалось найти трек: {e}")

        source.volume = player.volume

        if vc.is_playing() or vc.is_paused():
            player.queue.append(source.url)
            embed = discord.Embed(
                title="📥 Добавлено в очередь",
                description=f"**{source.title}**",
                color=0x5865F2
            )
            embed.add_field(name="Позиция", value=str(len(player.queue)))
            return await interaction.followup.send(embed=embed)

        player.current = source
        vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(
            self.play_next(interaction.guild, interaction.channel), self.bot.loop))
        await interaction.followup.send(embed=now_playing_embed(source))

    # ── /skip ─────────────────────────────────
    @app_commands.command(name="skip", description="Пропустить текущий трек")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("⏭️ Трек пропущен.")
        else:
            await interaction.response.send_message("❌ Ничего не играет.")

    # ── /pause ────────────────────────────────
    @app_commands.command(name="pause", description="Пауза / продолжить")
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Пауза.")
        elif vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Продолжаю.")
        else:
            await interaction.response.send_message("❌ Ничего не играет.")

    # ── /stop ─────────────────────────────────
    @app_commands.command(name="stop", description="Остановить музыку и очистить очередь")
    async def stop(self, interaction: discord.Interaction):
        player = get_player(interaction.guild.id)
        player.queue.clear()
        player.current = None
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
            await vc.disconnect()
        await interaction.response.send_message("⏹️ Остановлено, очередь очищена.")

    # ── /loop ─────────────────────────────────
    @app_commands.command(name="loop", description="Включить/выключить повтор трека")
    async def loop(self, interaction: discord.Interaction):
        player = get_player(interaction.guild.id)
        player.loop = not player.loop
        status = "включён 🔁" if player.loop else "выключен ➡️"
        await interaction.response.send_message(f"Повтор {status}")

    # ── /nowplaying ───────────────────────────
    @app_commands.command(name="nowplaying", description="Текущий трек")
    async def nowplaying(self, interaction: discord.Interaction):
        player = get_player(interaction.guild.id)
        if player.current:
            await interaction.response.send_message(embed=now_playing_embed(player.current))
        else:
            await interaction.response.send_message("❌ Ничего не играет.")

    # ── /volume ───────────────────────────────
    @app_commands.command(name="volume", description="Громкость от 1 до 100")
    @app_commands.describe(level="Уровень громкости (1–100)")
    async def volume(self, interaction: discord.Interaction, level: int):
        if not 1 <= level <= 100:
            return await interaction.response.send_message("❌ Укажи значение от 1 до 100.")
        player = get_player(interaction.guild.id)
        player.volume = level / 100
        vc = interaction.guild.voice_client
        if vc and vc.source:
            vc.source.volume = player.volume
        await interaction.response.send_message(f"🔊 Громкость: **{level}%**")

    # ── /leave ────────────────────────────────
    @app_commands.command(name="leave", description="Выгнать бота из канала")
    async def leave(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("👋 Отключился.")
        else:
            await interaction.response.send_message("❌ Я не в канале.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))