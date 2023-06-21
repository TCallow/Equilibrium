import io
import os
import asyncio
import aiohttp
from datetime import datetime, timedelta


async def fetch_character(forename, surname, world):
    url = f'https://xiv-character-cards.drakon.cloud/characters/name/{world}/{forename} {surname}.png'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                if response.headers['Content-Type'] == 'image/png':
                    data = await response.read()
                    if data:
                        return data
            return None
