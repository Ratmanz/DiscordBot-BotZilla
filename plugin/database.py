from discord.ext import commands
import json
import discord
import psycopg2
import csv
import re
from discord.errors import HTTPException


class Database:
    def __init__(self, bot):
        self.bot = bot
        self.tmp_config = json.loads(str(open('./options/config.js').read()))
        self.config = self.tmp_config['config']
        self.emojiUnicode = self.tmp_config['unicode']
        self.exchange = self.tmp_config['exchange']
        self.botzillaChannels = self.tmp_config['channels']
        self.owner_list = self.config['owner-id']
        self.database_settings = self.tmp_config['database']
        self.database_online = False
        self.database_export_location_users = './export/DBE_users.csv'
        self.database_import_location_users = './import/DBE_users.csv'
        self.database_export_location_music_channels = './export/DBE_music_channels.csv'
        self.database_import_location_music_channels = './import/DBE_music_channels.csv'
        self.database_export_location_blacklist = './export/DBE_blacklist.csv'
        self.database_import_location_blacklist = './import/DBE_blacklist.csv'
        self.database_export_musicque = './import/DBE_music_que.csv'
        self.database_import_musicque = './import/DBE_music_que.csv'
        self.client = discord.Client()
        self.music_channels = []
        self.reconnect_db_times = int(self.database_settings['reconnect_trys'])
        self.blacklist = []


        for i in range(self.reconnect_db_times):
            try:
                self.conn = psycopg2.connect("dbname='{}' user='{}' host='{}' port='{}' password={}".format(
                    self.database_settings['db_name'],
                    self.database_settings['user'],
                    self.database_settings['ip'],
                    self.database_settings['port'],
                    self.database_settings['password']
                ))
                self.cur = self.conn.cursor()
                self.cur.execute("select id from botzilla.music where type_channel = 'voice';")
                rows = self.cur.fetchall()
                self.cur.execute("ROLLBACK;")
                for row in rows:
                    for item in row:
                        self.music_channels.append(item)
                self.database_online = True
                break
            except:
                print('I am unable to connect to the Database')
            print('failed to connect with the database giving up...')

            # Blacklist
            try:
                self.cur.execute("SELECT ID from botzilla.blacklist;")
                rows = self.cur.fetchall()
                self.cur.execute("ROLLBACK;")
                for item in rows:
                    item = str(item).replace('(', '')
                    item = item.replace(',)', '')
                    self.blacklist.append(item)
            except Exception as e:
                print(f'Can\'t find database{e.args}')

    async def is_blacklisted(self, author_id):
        if author_id in self.blacklist:
            return

    @commands.command(pass_context=True, hidden=True)
    async def sql(self, ctx, *, query: str = None):
        """
        Acces database and run a query.
        use a query psql based.
        """
        if ctx.message.author.id not in self.owner_list:
            embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                                  description='You may not use this command :angry: only admins!',
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['warning'])
            return

        if not self.database_online:
            embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                                  description='Could not connect to database.',
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['error'])
            return

        if query is None:
            embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                                  description='You should know what you are doing.\n Especially with this command! :angry:',
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['warning'])
            return
        try:
            self.cur.execute('{}'.format(str(query)))
            result_cur = self.cur.fetchall()
            self.cur.execute("ROLLBACK;")
            if not result_cur:
                embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                                      description='No data found :cry:',
                                      colour=0xf20006)
                a = await self.bot.say(embed=embed)
                await self.bot.add_reaction(a, self.emojiUnicode['error'])
                return

            embed = discord.Embed(title='{}:'.format('SQL Succes'),
                                  description='```sql\n{}```'.format(result_cur),
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['succes'])
        except psycopg2.Error as e:
            if e.pgerror is None:
                embed = discord.Embed(title='{}:'.format('SQL Succes'),
                                      description='```sql\n{}```'.format(str(query)),
                                      colour=0xf20006)
                a = await self.bot.say(embed=embed)
                await self.bot.add_reaction(a, self.emojiUnicode['succes'])
                return
            embed = discord.Embed(title='{}:'.format('SQL Error'),
                                  description='```sql\n{}```\nROLLBACK query:\n```sql\n{}sql ROLLBACK;```'.format(
                                      e.pgerror, self.config['prefix']),
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['error'])
        except HTTPException as e:
            embed = discord.Embed(title='{}:'.format('Error'),
                                  description='Try to use `limit 10`. Output may be to big\n```Python\n{}```'.format(e.args),
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['error'])


    @commands.command(pass_context=True, hidden=True)
    async def get_users(self, ctx):
        """
        Update datebase with current active users
        """
        if ctx.message.author.id not in self.owner_list:
            embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                                  description='You may not use this command :angry: only admins!',
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['warning'])
            return

        if not self.database_online:
            embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                                  description='Could not connect to database.',
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['error'])
            return

        data_members = {"id" : "name"}
        for server in self.bot.servers:
            for member in server.members:
                data_members.update({member.id:member.name})

        for id_members, name_members in data_members.items():
            try:
                self.cur.execute('INSERT INTO botzilla.users (ID, name) VALUES ({}, \'{}\');'.format(
                    id_members, str(name_members)))
                self.cur.execute("ROLLBACK;")
            except Exception as e:
                print('Error gathering info user:\n```Python\n{}```'.format(e.args))
                continue
        embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                              description='Done with gathering user info!',
                              colour=0xf20006)
        a = await self.bot.say(embed=embed)
        await self.bot.add_reaction(a, self.emojiUnicode['succes'])


    @commands.command(pass_context=True, hidden=True)
    async def get_music(self, ctx):
        """
        Update datebase with current active music channels
        """
        if ctx.message.author.id not in self.owner_list:
            embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                                  description='You may not use this command :angry: only admins!',
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['warning'])
            return

        if not self.database_online:
            embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                                  description='Could not connect to database.',
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['error'])
            return

        data_channels = []
        for server in self.bot.servers:
            for channel in server.channels:
                if 'music' in str(channel).lower():
                    channel_type = str(channel.type)
                    print(channel_type)
                    data = [int(channel.id), str(channel.name), re.sub('\W+', '', str(server.name)), str(channel.type)]
                    data_channels.append(data)


        self.cur.execute('ROLLBACK;')
        for items in data_channels:
            try:
                self.cur.execute(
                    'INSERT INTO botzilla.music (ID, channel_name, server_name, type_channel) VALUES ({}, \'{}\', \'{}\', \'{}\');'.format(
                        items[0], items[1], items[2], items[3]
                    ))
                self.cur.execute("ROLLBACK;")
            except Exception as e:
                print('Error gathering info music channels:\n```Python\n{}```'.format(e.args))
                continue

        embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                              description='Done with gathering music channel info!',
                              colour=0xf20006)
        a = await self.bot.say(embed=embed)
        await self.bot.add_reaction(a, self.emojiUnicode['succes'])


    @commands.command(pass_context=True, hidden=True)
    async def dbexport(self, ctx):
        """
        Export database data to export folder
        """
        if ctx.message.author.id not in self.owner_list:
            embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                                  description='You may not use this command :angry: only admins!',
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['warning'])
            return


        if not self.database_online:
            embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                                  description='Could not connect to database.',
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['error'])
            return

        try:
            self.cur.execute("SELECT * from botzilla.users;")
            rows = self.cur.fetchall()
            self.cur.execute("ROLLBACK;")
            with open(self.database_export_location_users, 'w') as output:
                writer = csv.writer(output, lineterminator='\n')
                for val in rows:
                    writer.writerow([val])
        except Exception as e:
            embed = discord.Embed(title='{}:'.format('Error'),
                                  description='```Python\n{}\n```'.format(e.args),
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['error'])


        try:
            self.cur.execute("SELECT * from botzilla.music;")
            rows = self.cur.fetchall()
            self.cur.execute("ROLLBACK;")
            with open(self.database_export_location_music_channels, 'w') as output:
                writer = csv.writer(output, lineterminator='\n')
                for val in rows:
                    writer.writerow([val])
        except Exception as e:
            embed = discord.Embed(title='{}:'.format('Error'),
                                  description='```Python\n{}\n```'.format(e.args),
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['error'])


        try:
            self.cur.execute("SELECT * from botzilla.blacklist;")
            rows = self.cur.fetchall()
            self.cur.execute("ROLLBACK;")
            with open(self.database_export_location_blacklist, 'w') as output:
                writer = csv.writer(output, lineterminator='\n')
                for val in rows:
                    writer.writerow([val])
        except Exception as e:
            embed = discord.Embed(title='{}:'.format('Error'),
                                  description='```Python\n{}\n```'.format(e.args),
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['error'])


        try:
            self.cur.execute("SELECT * from botzilla.musicque;")
            rows = self.cur.fetchall()
            self.cur.execute("ROLLBACK;")
            with open(self.database_export_musicque, 'w') as output:
                writer = csv.writer(output, lineterminator='\n')
                for val in rows:
                    writer.writerow([val])
        except Exception as e:
            embed = discord.Embed(title='{}:'.format('Error'),
                                  description='```Python\n{}\n```'.format(e.args),
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['error'])


        embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                              description='Done!',
                              colour=0xf20006)
        a = await self.bot.say(embed=embed)
        await self.bot.add_reaction(a, self.emojiUnicode['succes'])


    @commands.command(pass_context=True, hidden=True)
    async def dbimport(self, ctx):
        """
        Import CSV data from import folder
        """
        if ctx.message.author.id not in self.owner_list:
            embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                                  description='You may not use this command :angry: only admins!',
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['warning'])
            return


        if not self.database_online:
            embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                                  description='Could not connect to database.',
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['error'])
            return

        try:
            with open(self.database_import_location_users, 'r') as file:
                reader = csv.reader(file, delimiter=',')
                for row in reader:
                    try:
                        row = str(row).replace('["', '')
                        row = str(row).replace('"]', '')
                        self.cur.execute("INSERT INTO botzilla.users (ID, name) VALUES{}".format(row))
                        self.cur.execute("ROLLBACK;")
                    except:
                        pass
        except Exception as e:
            embed = discord.Embed(title='{}:'.format('Error'),
                                  description='```Python\n{}\n```'.format(e.args),
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['error'])


        try:
            with open(self.database_import_location_blacklist, 'r') as file:
                reader = csv.reader(file, delimiter=',')
                for row in reader:
                    try:
                        row = str(row).replace('["', '')
                        row = str(row).replace('"]', '')
                        self.cur.execute("INSERT INTO botzilla.blacklist (ID, server_name, reason, total_votes) VALUES{};".format(row))
                        self.cur.execute("ROLLBACK;")
                    except:
                        pass

        except Exception as e:
            embed = discord.Embed(title='{}:'.format('Error'),
                                  description='```Python\n{}\n```'.format(e.args),
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['error'])


        try:
            with open(self.database_import_location_music_channels, 'r') as file:
                reader = csv.reader(file, delimiter=',')
                for row in reader:
                    try:
                        row = str(row).replace('["', '')
                        row = str(row).replace('"]', '')
                        self.cur.execute("INSERT INTO botzilla.music (ID, channel_name, server_name, type_channel) VALUES{}".format(row))
                        self.cur.execute("ROLLBACK;")
                    except:
                        pass
        except Exception as e:
            embed = discord.Embed(title='{}:'.format('Error'),
                                  description='```Python\n{}\n```'.format(e.args),
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['error'])


        embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                              description='Done!',
                              colour=0xf20006)
        a = await self.bot.say(embed=embed)
        await self.bot.add_reaction(a, self.emojiUnicode['succes'])


    @commands.command(pass_context=True, hidden=True)
    async def importmusic(self, ctx):
        """
        Import CSV data from import folder
        Imports music
        """
        if ctx.message.author.id not in self.owner_list:
            embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                                  description='You may not use this command :angry: only admins!',
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['warning'])
            return


        if not self.database_online:
            embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                                  description='Could not connect to database.',
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['error'])
            return


        try:
            with open(self.database_import_musicque, 'r') as file:
                reader = csv.reader(file, delimiter=',')
                for row in reader:
                    b = re.search(r'^(.*)', str(row)).group()
                    b = b.replace('[', '')
                    b = b.replace('"(', '')
                    b = b.replace(',)"', '')
                    row = b.replace(']', '')
                    try:
                        self.cur.execute("INSERT INTO botzilla.musicque(url) VALUES({});".format(row))
                        self.cur.execute("ROLLBACK;")
                    except Exception as e:
                        pass

                embed = discord.Embed(title='{}:'.format(ctx.message.author.name),
                                      description='Done!',
                                      colour=0xf20006)
                a = await self.bot.say(embed=embed)
                await self.bot.add_reaction(a, self.emojiUnicode['succes'])

        except Exception as e:
            embed = discord.Embed(title='{}:'.format('Error'),
                                  description='```Python\n{}```'.format(e.args),
                                  colour=0xf20006)
            a = await self.bot.say(embed=embed)
            await self.bot.add_reaction(a, self.emojiUnicode['error'])


def setup(bot):
    bot.add_cog(Database(bot))