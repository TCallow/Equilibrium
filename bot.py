import asyncio
import io
import os
import sqlite3
from datetime import datetime

import discord
from discord.ext import commands
from dotenv import load_dotenv

import xivresponses

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)
database = sqlite3.connect('events.db')
cursor = database.cursor()
database.execute('CREATE TABLE IF NOT EXISTS upcomingevents (server_id TEXT, event_name TEXT, event_date TEXT)')
database.execute('CREATE TABLE IF NOT EXISTS registeredplayers (player_name TEXT, world TEXT, user_id TEXT, '
                 'wins INTEGER, losses INTEGER, server_id TEXT)')


async def is_mod(member: discord.Member) -> bool:
    return member.guild_permissions.manage_messages


def run_discord_bot():
    token = os.getenv('DISCORD_TOKEN')

    @client.event
    async def on_ready():
        print(f'{client.user} is now running')
        activity = discord.Activity(name='to your commands!', type=discord.ActivityType.listening)
        await client.change_presence(activity=activity, status=discord.Status.online)

        try:
            synced = await client.tree.sync()
            print(f'Synced {len(synced)} commands')
        except Exception as e:
            print(f'Failed to sync commands: {e}')

    @client.tree.command(name='scrimdate', description='Sets the next date for scrims. Please use this format: '
                                                       'YYYY-MM-DD HH:MM')
    async def scrimdate(ctx, event_name: str, event_date: str):
        await ctx.response.defer(ephemeral=False)
        if not await is_mod(ctx.user):
            await ctx.followup.send('You do not have permission to use this command.')
            return
        cursor.execute('SELECT * FROM upcomingevents WHERE event_name = ? AND server_id = ?',
                       (event_name, ctx.guild.id))
        if cursor.fetchone() is not None:
            await ctx.followup.send('This event already exists.')
            return
        scheduled_date = datetime.strptime(event_date, '%Y-%m-%d %H:%M')
        current_date = datetime.now()
        time_delta = scheduled_date - current_date
        if time_delta.total_seconds() < 0:
            await ctx.followup.send('Please use a date in the future.')
            return
        database.execute(f'CREATE TABLE IF NOT EXISTS {event_name}_{ctx.guild.id} (user_id TEXT)')
        cursor.execute('INSERT INTO upcomingevents VALUES (?, ?, ?)', (ctx.guild.id, event_name, scheduled_date))
        database.commit()
        await ctx.followup.send(f'{event_name} is scheduled for {scheduled_date}')

    @client.tree.command(name='register', description='Registers your character in the database.')
    async def register(ctx, forename: str, surname: str, world: str):
        await ctx.response.defer(ephemeral=False)
        await asyncio.sleep(10)
        file = await xivresponses.fetch_character(forename, surname, world)
        if file:
            cursor.execute('SELECT * FROM registeredplayers WHERE player_name = ? AND world = ? AND user_id = ?',
                           (forename + ' ' + surname, world, ctx.user.id))
            if cursor.fetchone() is not None:
                await ctx.followup.send('You have already registered your character.')
                return
            cursor.execute('INSERT INTO registeredplayers VALUES (?, ?, ?, ?, ?, ?)',
                           (forename + ' ' + surname, world, ctx.user.id, 0, 0, ctx.guild.id))
            database.commit()
            image = discord.File(io.BytesIO(file), filename='character.png')
            embed = discord.Embed(title=f'{forename} {surname} of {world}',
                                  description='This character has been registered using your user ID.',
                                  color=discord.Color.green())
            file_url = f'attachment://character.png'
            embed.set_image(url=file_url)
            await ctx.followup.send(file=image, embed=embed)
        else:
            await ctx.followup.send('I couldn\'t find a character by that name, sorry!')

    @client.tree.command(name='unregister', description='Unregisters your character from the database.')
    async def unregister(ctx):
        await ctx.response.defer(ephemeral=False)
        cursor.execute('SELECT * FROM registeredplayers WHERE user_id = ?', (ctx.user.id,))
        if cursor.fetchone() is None:
            await ctx.followup.send('You have not registered your character.')
            return
        cursor.execute('DELETE FROM registeredplayers WHERE user_id = ?', (ctx.user.id,))
        database.commit()
        await ctx.followup.send('Your character has been unregistered.')

    @client.tree.command(name='player_list', description='Lists all registered player_list in this server.')
    async def players(ctx):
        await ctx.response.defer(ephemeral=False)
        cursor.execute('SELECT * FROM registeredplayers WHERE server_id = ?', (ctx.guild.id,))
        registered_players = cursor.fetchall()
        if len(registered_players) == 0:
            await ctx.followup.send('There are no registered player_list in this server.')
            return
        embed = discord.Embed(title='Registered Players', color=discord.Color.green())
        for player in registered_players:
            if player[3] == 0 and player[4] == 0:
                embed.add_field(name=player[0], value=f'Wins: {player[3]}\nLosses: {player[4]}\nWinrate: 0%')
            else:
                embed.add_field(name=player[0], value=f'Wins: {player[3]}\nLosses: {player[4]}\nWinrate: '
                                                      f'{round((player[3] / (player[3] + player[4])) * 100)}%',
                                inline=False)
        await ctx.followup.send(embed=embed)

    @client.tree.command(name='events', description='Lists all upcoming events in this server.')
    async def upcomingevents(ctx):
        await ctx.response.defer(ephemeral=False)
        cursor.execute('SELECT * FROM upcomingevents WHERE server_id = ?', (ctx.guild.id,))
        upcoming_events = cursor.fetchall()
        if len(upcoming_events) == 0:
            await ctx.followup.send('There are no upcoming events in this server.')
            return
        embed = discord.Embed(title='Upcoming Events', color=discord.Color.green())
        for event in upcoming_events:
            embed.add_field(name=event[1], value=event[2], inline=False)
        await ctx.followup.send(embed=embed)

    @client.tree.command(name='join', description='Joins an event.')
    async def join(ctx, event_name: str):
        await ctx.response.defer(ephemeral=False)
        cursor.execute('SELECT * FROM upcomingevents WHERE event_name = ? AND server_id = ?',
                       (event_name, ctx.guild.id))
        if cursor.fetchone() is None:
            await ctx.followup.send('This event does not exist.')
            return
        cursor.execute('SELECT * FROM registeredplayers WHERE user_id = ?', (ctx.user.id,))
        if cursor.fetchone() is None:
            await ctx.followup.send('You have not registered your character.')
            return
        cursor.execute(f'INSERT INTO {event_name}_{ctx.guild.id} VALUES (?)', (ctx.user.id,))
        database.commit()
        await ctx.followup.send('You have joined the event.')

    @client.tree.command(name='leave', description='Leaves an event.')
    async def leave(ctx, event_name: str):
        await ctx.response.defer(ephemeral=False)
        cursor.execute('SELECT * FROM upcomingevents WHERE event_name = ? AND server_id = ?',
                       (event_name, ctx.guild.id))
        if cursor.fetchone() is None:
            await ctx.followup.send('This event does not exist.')
            return
        cursor.execute(f'SELECT * FROM {event_name}_{ctx.guild.id} WHERE user_id = ?', (ctx.user.id,))
        if cursor.fetchone() is None:
            await ctx.followup.send('You have not joined this event.')
            return
        cursor.execute(f'DELETE FROM {event_name}_{ctx.guild.id} WHERE user_id = ?', (ctx.user.id,))
        database.commit()
        await ctx.followup.send('You have left the event.')

    @client.tree.command(name='eventattendees', description='Lists all character names and worlds attending an event.')
    async def eventattendees(ctx, event_name: str):
        await ctx.response.defer(ephemeral=False)
        cursor.execute('SELECT * FROM upcomingevents WHERE event_name = ? AND server_id = ?',
                       (event_name, ctx.guild.id))
        if cursor.fetchone() is None:
            await ctx.followup.send('This event does not exist.')
            return
        cursor.execute(f'SELECT * FROM {event_name}_{ctx.guild.id}')
        attendees = cursor.fetchall()
        if len(attendees) == 0:
            await ctx.followup.send('There are no attendees for this event.')
            return
        embed = discord.Embed(title=f'Attendees for {event_name}', color=discord.Color.green())
        for attendee in attendees:
            cursor.execute('SELECT * FROM registeredplayers WHERE user_id = ?', (attendee[0],))
            player = cursor.fetchone()
            embed.add_field(name=player[0], value=player[2], inline=False)
        await ctx.followup.send(embed=embed)

    @client.tree.command(name='createteams', description='Creates teams for the event.')
    async def createteams(ctx, event_name: str):
        await ctx.response.defer(ephemeral=False)
        try:
            cursor.execute(f'SELECT * FROM {event_name}_{ctx.guild.id}')
            player_ids = cursor.fetchall()
            player_ids = [player_id[0] for player_id in player_ids]

            player_list = []
            for player_id in player_ids:
                cursor.execute('SELECT player_name, wins, losses FROM registeredplayers WHERE user_id = ?', (player_id,))
                player_info = cursor.fetchone()
                if player_info:
                    player_list.append((player_id, player_info[0], player_info[1], player_info[2]))
            sorted_players = sorted(player_list, key=lambda x: x[3] / (x[2] + x[3]) if (x[2] + x[3]) > 0 else 0)
            team_a = sorted_players[:len(sorted_players) // 2]
            team_b = sorted_players[len(sorted_players) // 2:]

            embed = discord.Embed(title=f'Team Astra', color=discord.Color.blue())
            for player in team_a:
                if player[2] == 0 and player[3] == 0:
                    embed.add_field(name=player[1], value=f'Win rate: 0%', inline=False)
                else:
                    embed.add_field(name=player[1], value=f'Win rate: {round((player[2] / (player[2] + player[3])) * 100)}%', inline=False)

            await ctx.channel.send(embed=embed)

            embed = discord.Embed(title=f'Team Umbra', color=discord.Color.red())
            for player in team_b:
                if player[2] == 0 and player[3] == 0:
                    embed.add_field(name=player[1], value=f'Win rate: 0%', inline=False)
                else:
                    embed.add_field(name=player[1], value=f'Win rate: {round((player[2] / (player[2] + player[3])) * 100)}%', inline=False)

            await ctx.channel.send(embed=embed)
            await ctx.followup.send('Teams have been created.')
        except Exception as e:
            print(e)
            await ctx.followup.send('There was an error creating the teams.')

    client.run(token)
