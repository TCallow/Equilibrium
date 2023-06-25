# Equilibrium
A Discord bot for FFXIV's Crystalline Conflict mode focusing on randomizing and autobalancing teams based on their cumulative winrate so that theoretically each team has a 50% chance of winning the match. I hope to refine the formula and algorithm as development continues.

# Commands
I will list all commands included with this bot as well as explanations of what it does for transparency.

- /register and /unregister
All players will start by using /register. This commands adds them into the database. This database will hold the player's discord ID as well as server ID (The server where this user registered), character name, world, wins, and losses. Wins and Losses always start at 0. It is also where information about upcoming scrims/events is stored and retrieved, but this will be explained later. If a player does /unregister they will no longer be tracked in the database meaning they will be unable to join upcoming scrims/events to be auto sorted into teams.

- /players
  This command will search through the database for all registered players in the current server and return a list of them as a discord embed including their wins, losses, and winrates.

- /scrimdate
  Moderators/Admins of the server will use this command to create events/scrims. You will need to enter a name for the event, as well as a date. Names must not include spaces currently, this will be fixed in the future. You will need to use this format for it to be a valid date: YYYY-MM-DD HH:MM. For example, if you wanted to create a scrim for June 26 2023 at 2 pm, you would enter: /scrimdate nameofevent 2023-06-26 14:00. This will create a new table in the database for this event and discord server. You will need to remember this scrim/event name to join it. 
