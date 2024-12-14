import discord
from discord.ext import commands, tasks
import random
import asyncio
from datetime import datetime
import json
import logging
import os
from typing import Optional
from pathlib import Path

# Advanced logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Config handler
class Config:
    @staticmethod
    def load_config():
        with open('config.json') as f:
            return json.load(f)

    @staticmethod
    def save_config(config):
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)

# Custom bot class with enhanced features
class AdvancedBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix=self.get_prefix, intents=intents)
        self.config = Config.load_config()
        self.initial_extensions = [
            'cogs.moderation',
            'cogs.fun',
            'cogs.economy',
            'cogs.leveling'
        ]
        self.uptime = datetime.utcnow()
        
    async def get_prefix(self, message):
        if not message.guild:
            return '!'
        
        guild_id = str(message.guild.id)
        return self.config.get('prefixes', {}).get(guild_id, '!')

    async def setup_hook(self):
        for ext in self.initial_extensions:
            try:
                await self.load_extension(ext)
                logger.info(f'Loaded extension: {ext}')
            except Exception as e:
                logger.error(f'Failed to load extension {ext}: {e}')

bot = AdvancedBot()

# Error Handler
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        suggestion = get_closest_command(ctx.invoked_with, [cmd.name for cmd in bot.commands])
        if suggestion:
            await ctx.send(f"Command not found. Did you mean `{ctx.prefix}{suggestion}`?")
        return
    
    error_embed = discord.Embed(
        title="Error",
        description=str(error),
        color=discord.Color.red()
    )
    await ctx.send(embed=error_embed)
    logger.error(f'Error in {ctx.command}: {error}')

# Leveling System
class LevelingSystem:
    def __init__(self):
        self.levels = {}
        
    def calculate_xp(self, message):
        return len(message.content) // 2

    async def add_xp(self, user_id, xp):
        if user_id not in self.levels:
            self.levels[user_id] = {'xp': 0, 'level': 1}
        
        self.levels[user_id]['xp'] += xp
        return await self.check_level_up(user_id)

    async def check_level_up(self, user_id):
        xp = self.levels[user_id]['xp']
        lvl = self.levels[user_id]['level']
        
        if xp >= lvl * 100:
            self.levels[user_id]['level'] += 1
            return True
        return False

leveling = LevelingSystem()

# Event Handlers
@bot.event
async def on_ready():
    logger.info(f'{bot.user} is online and ready!')
    change_status.start()
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f'{len(bot.guilds)} servers | !help'
        )
    )

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Add XP
    if not message.content.startswith(await bot.get_prefix(message)):
        xp_gained = leveling.calculate_xp(message)
        leveled_up = await leveling.add_xp(message.author.id, xp_gained)
        
        if leveled_up:
            level_embed = discord.Embed(
                title="Level Up! 🎉",
                description=f"{message.author.mention} has reached level {leveling.levels[message.author.id]['level']}!",
                color=discord.Color.gold()
            )
            await message.channel.send(embed=level_embed)

    await bot.process_commands(message)

# Advanced Commands
@bot.command()
async def stats(ctx):
    embed = discord.Embed(
        title="Bot Statistics",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    uptime = datetime.utcnow() - bot.uptime
    embed.add_field(name="Uptime", value=str(uptime).split('.')[0])
    embed.add_field(name="Servers", value=len(bot.guilds))
    embed.add_field(name="Users", value=len(set(bot.get_all_members())))
    embed.add_field(name="Commands", value=len(bot.commands))
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms")
    
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def setprefix(ctx, new_prefix: str):
    guild_id = str(ctx.guild.id)
    bot.config['prefixes'][guild_id] = new_prefix
    Config.save_config(bot.config)
    
    embed = discord.Embed(
        title="Prefix Updated",
        description=f"New prefix set to: `{new_prefix}`",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# Create necessary directories and files
def setup_files():
    # Create cogs directory
    Path("cogs").mkdir(exist_ok=True)
    
    # Create default config if it doesn't exist
    if not os.path.exists('config.json'):
        default_config = {
            "token": "YOUR_TOKEN_HERE",
            "prefixes": {},
            "welcome_channel": None,
            "log_channel": None
        }
        with open('config.json', 'w') as f:
            json.dump(default_config, f, indent=4)

if __name__ == "__main__":
    setup_files()
    config = Config.load_config()
    bot.run(config['token'])
