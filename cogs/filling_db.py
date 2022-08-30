import discord
from discord.ext import commands
import sqlite3
import json
import re

with open("cogs/jsons/settings.json") as json_file:
    data_dict = json.load(json_file)
    amount = data_dict["amount"]
    history_limit = data_dict["history_limit"]
    output_channel_id = data_dict["bookmark-list"]
    fetch_channel_id = data_dict["resource-sharing"]
    max_char = data_dict["max_char"]
    guild_id = data_dict["guild_id"]


class Filling_db(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)

    async def removing_pings(self, reaction_message):
        print("removing pings")
        split_message = reaction_message.content.split()
        user_id_list = []
        for e in split_message:
            if e.startswith("<@"):
                user_id_raw = re.findall("\<\@(.*?)\>", e)
                user_id = str(user_id_raw).strip("['']")
                user_id_new = re.sub('\D', '', user_id)
                user_id_list.append(user_id_new)

        user_name_list = []
        for r in user_id_list:
            user_name = await self.bot.fetch_user(r)
            user_name_list.append(str(user_name))

        for i in range(len(split_message)):
            if split_message[i].startswith("<@"):
                split_message[i] = user_name_list[0]
                del user_name_list[0]

        reaction_message.content = " ".join(str(g) for g in split_message)

        return reaction_message.content

    async def thumbnail(self, reaction_message):
        print("adding thumbnail")
        if reaction_message.attachments != []:
            a = 0
            for image in reaction_message.attachments:
                if a >= 1:
                    break
                if image.content_type == "image/png" or "image/jpg" or "image/jpeg":
                    reaction_message_image = image.url
                    return reaction_message_image
                a += 1

        return

    async def keyword_assignment(self, reaction_message):
        print("adding keywords")
        con = sqlite3.connect('words.db')
        cur = con.cursor()
        cur.execute(f"SELECT * FROM 'resource_sharing' ORDER BY freqs DESC")
        words = cur.fetchall()
        b = 0
        displayed_keywords = []
        for keywords in words:
            if b >= 3:
                break
            if keywords[0] in reaction_message.content:
                keyword = keywords[0]
                displayed_keywords.append(keyword)
                b += 1
        con.commit()
        con.close()

        return displayed_keywords

    async def fetch_messages(self, fetch_channel):
        con = sqlite3.connect('bookmarked-messages.db')
        cur = con.cursor()
        channel = await self.bot.fetch_channel(int(fetch_channel))
        async for reaction_message in channel.history(limit=int(history_limit)):
            for reaction in reaction_message.reactions:
                if reaction.emoji == "🔖":
                    reaction_amount = reaction.count
                    if reaction_amount >= int(amount):
                        reaction_message.content = await self.removing_pings(reaction_message)
                        reaction_message_image = await self.thumbnail(reaction_message)
                        displayed_keywords = await self.keyword_assignment(reaction_message)

                        if "[{" in reaction_message.content and "}]" in reaction_message.content:
                            reaction_message.content = re.findall('\[\{(.*?)\}\]', reaction_message.content)[0]
                            reaction_message.content = str(
                                reaction_message.content).strip("['']")
                            cur.execute('INSERT INTO bookmarked_messages (discord_user_id, bookmarks, message_id, content, link, created_at, attachments, keywords) VALUES (?,?,?,?,?,?,?,?)',(int(reaction_message.author.id), int(reaction_amount), int(reaction_message.id), "\n" + str(reaction_message.content), str(reaction_message.jump_url), str(reaction_message.created_at), str(reaction_message_image), str(displayed_keywords)))
                            con.commit()
                        elif reaction_message.attachments and len(reaction_message.content) == 0:
                            for naming in reaction_message.attachments:
                                reaction_message.content = naming.filename
                            cur.execute('INSERT INTO bookmarked_messages (discord_user_id, bookmarks, message_id, content, link, created_at, attachments, keywords) VALUES (?,?,?,?,?,?,?,?)', (int(reaction_message.author.id), int(reaction_amount), int(reaction_message.id), "\n" + str(reaction_message.content[:max_char]), str(reaction_message.jump_url), str(reaction_message.created_at), str(reaction_message_image), str(displayed_keywords)))
                            con.commit()
                        elif len(reaction_message.content) > max_char:
                            cur.execute('INSERT INTO bookmarked_messages (discord_user_id, bookmarks, message_id, content, link, created_at, attachments, keywords) VALUES (?,?,?,?,?,?,?,?)',(int(reaction_message.author.id), int(reaction.count), int(reaction_message.id), str(reaction_message.content), str(reaction_message.jump_url), str(reaction_message.created_at), str(reaction_message.attachments), str(displayed_keywords)))
                            con.commit()
                        else:
                            cur.execute('INSERT INTO bookmarked_messages (discord_user_id, bookmarks, message_id, content, link, created_at, attachments, keywords) VALUES (?,?,?,?,?,?,?,?)', (int(reaction_message.author.id), int(reaction_amount), int(reaction_message.id), "\n" + str(reaction_message.content[:max_char]), str(reaction_message.jump_url), str(reaction_message.created_at), str(reaction_message_image), str(displayed_keywords)))
                            con.commit()
        con.close()
        print("done fetching")
        
    @commands.command(hidden=True)
    async def fill_db(self, ctx, channel_name):
        all_text_channels = []
        for server in self.bot.guilds:
            for channel in server.channels:
                if str(channel.type) == 'text':
                    id = channel.id
                    all_text_channels.append(id)
        text_channels = (['<#{0}>'.format(i) for i in all_text_channels])
        try:
            if any(channel_name in s for s in text_channels):
                fetch_channel = channel_name.strip("<#>")
                await self.fetch_messages(fetch_channel)
        except:
            exit

def setup(bot):
    bot.add_cog(Filling_db(bot))
