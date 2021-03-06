import ovalia_auxiliary_protocol as oap
from discord.ext import tasks, commands
from os import path, makedirs, listdir
from importlib import reload
from random import randint
import requests as r
import DiscordUtils
import discord
import json
import re


class DND(commands.Cog, description="Stat generation, information on items, spells, and the like, and more, for Dungeons and Dragons 5th edition"):
    def __init__(self, bot):
        self.abacus = bot
        self.cog_name = "DND"
        self.data = oap.getJson("data")
        self.url = "https://www.dnd5eapi.co/api"

    # ==================================================
    # Unload event
    # ==================================================
    def cog_unload(self):
        oap.log(text="Unloaded", cog="DND", color="magenta")


    # ==================================================
    # General "get"/"lookup" command
    # ==================================================
    @commands.command(brief="", usage="", help="", aliases=["get"], enabled=False)
    async def lookup(self, ctx, category="categories", item="", *, other=""):
        server_data = oap.getJson(f"servers/{ctx.guild.id}")
        if server_data.get("delete_invocation") == True:
            await oap.tryDelete(ctx)

        # ==================================================
        # Get the 5e api website and all available categories
        # ==================================================
        request = r.get(url=self.url).json()
        categories = request.keys()


        # ==================================================
        # Argument error checking
        # ==================================================
        if category == "categories":
            embed = oap.makeEmbed(title="Available Categories", description=("- " + "\n- ".join(categories)), ctx=ctx)
            await ctx.send(embed=embed)
            return oap.log(text="Got available categories", cog="DND", color="magenta", ctx=ctx)
        
        if (category not in categories):
            embed = oap.makeEmbed(title="Whoops!", description="Please enter a valid category\n*(You can get valid categories with >>lookup categories)*", ctx=ctx)
            return await ctx.send(embed=embed)


        # ==================================================
        # If they want a whole category
        # (No specific item)
        # ==================================================
        if item == "":
            request = r.get(url=f"{self.url}/{category}").json()
            results = request.get("results")

            # ==================================================
            # Get all category info
            # Spit it into strings small enough for discord (if necesarry)
            # Paginate it (if necesarry)
            # Send output
            # ==================================================
            if len("- " + "\n- ".join([result.get("index") for result in results])) > 500:
                whole_string = "- " + "\n- ".join([result.get("index") for result in results])
                strings = [whole_string[:500] + "..."]
                for i in range(10):
                    _string = whole_string[500*(i+1):]
                    if len(_string) > 500:
                        strings.append("..." + _string[:500] + "...")
                        pass
                    else:
                        strings.append("..." + _string)
                        break
                
                embeds = []
                for string in strings:
                    embeds.append(oap.makeEmbed(title=f"Data From the {category.title()} Category", description=string, ctx=ctx))
                
                paginator = DiscordUtils.Pagination.CustomEmbedPaginator(ctx, remove_reactions=True, auto_footer=True)
                paginator.add_reaction('⏮️', "first")
                paginator.add_reaction('⏪', "back")
                paginator.add_reaction('🔐', "lock")
                paginator.add_reaction('⏩', "next")
                paginator.add_reaction('⏭️', "last")
                await paginator.run(embeds)
            else:
                embed = oap.makeEmbed(title=f"Data from the {category.title()} Category", description=("- " + "\n- ".join([result.get("index") for result in results])), ctx=ctx)
                await ctx.send(embed=embed)

            return oap.log(text=f"Got info from the {category} category", cog="DND", color="magenta", ctx=ctx)
    

        # ==================================================
        # Otherwise (they want a specific item)
        # ==================================================
        request = r.get(url=f"{self.url}/{category}").json()
        items = request.get("results")

        # ==================================================
        # Check if the item exists
        # ==================================================
        if item not in [item.get("index") for item in items]:
            embed = oap.makeEmbed(title="Whoops!", description="I couldnt find that item in that category", ctx=ctx)
            return await ctx.send(embed=embed)
        
        # ==================================================
        # Get the index of the item
        # Using the index, get the url of the item
        # ==================================================
        for number in range(len(items)): 
            if items[number].get("index") == item: 
                item_index = number
        request = r.get(url=f"https://www.dnd5eapi.co/{items[item_index].get('url')}").json()

        # ==================================================
        # If they specified something other than just the item
        # Iterate through what they requested
        # If something they requested is an array
        # Simplify it (or iterate through that until we find it)
        # ==================================================
        if other != "":
            for thing in other.split(" "):
                if isinstance(request, list):
                    for _item in request:
                        if _item.get(thing):
                            request = _item.get(thing)
                            break
                else:
                    request = request.get(thing)

        # ==================================================
        # If we never found their specific request, tell them
        # ==================================================
        if request == None:
            embed = oap.makeEmbed(title="Whoops!", description="I couldnt find that, try something else maybe?", ctx=ctx)
            return await ctx.send(embed=embed)

        # ==================================================
        # Formatting the request to JSON, if its an array
        # ==================================================
        if isinstance(request, list):
            request = json.loads("{\"" + other.split(" ")[-1] + "\": " + json.dumps(request) + "}")

        
        # ==================================================
        # If they *didnt* request something more specific than an item
        # ==================================================
        if other == "":
            formatted_category = re.sub(r'-', ' ', category).title()

            # ==================================================
            # Format the embed specifically for the information they requested
            # Yeah, this takes up a lot of space
            # ==================================================
            if category in ["conditions", "damage-types", "skills", "alignments"]:
                embed = oap.makeEmbed(title=f"Info on the {request.get('name')} {formatted_category[:-1] if formatted_category.endswith('s') else formatted_category}", description=("\n".join(request.get("desc")) if isinstance(request.get("desc"), list) else request.get("desc")), ctx=ctx)
            
            elif category == "ability-scores":
                embed = oap.makeEmbed(title=f"Info on the {request.get('full_name')} {formatted_category[:-1] if formatted_category.endswith('s') else formatted_category}", description="\n".join(request.get("desc")), ctx=ctx)
                embed.add_field(name="Skills", value="- " + "\n- ".join([f"{skill.get('name')} ({skill.get('url')[5:]})" for skill in request.get("skills")]), inline=True)
            
            elif category == "equipment-categories":
                whole_string = "- " + "\n- ".join([result.get("index") for result in request.get("equipment")])
                if len(whole_string) > 500:
                    strings = [whole_string[:500] + "..."]
                    for i in range(10):
                        _string = whole_string[500*(i+1):]
                        if len(_string) > 500:
                            strings.append("..." + _string[:500] + "...")
                            pass
                        else:
                            strings.append("..." + _string)
                            break

                    embeds = []
                    for string in strings:
                        embeds.append(oap.makeEmbed(title=f"Info on the {request.get('index')} Equipment Category", description=string, ctx=ctx))

                    paginator = DiscordUtils.Pagination.CustomEmbedPaginator(ctx, remove_reactions=True, auto_footer=True)
                    paginator.add_reaction('⏮️', "first")
                    paginator.add_reaction('⏪', "back")
                    paginator.add_reaction('🔐', "lock")
                    paginator.add_reaction('⏩', "next")
                    paginator.add_reaction('⏭️', "last")
                    await paginator.run(embeds)
                else:
                    embed = oap.makeEmbed(title=f"Info on the {request.get('name')} Equipment Category", description=whole_string, ctx=ctx)
            
            elif category == "equipment":
                equipment_category = request.get("equipment_category").get("name")
                embed = oap.makeEmbed(title=f"Info on the {request.get('name')} {formatted_category[:-1] if formatted_category.endswith('s') else formatted_category}", description="*(" + ", ".join([(request.get(key) if isinstance(request.get(key), str) else request.get(key).get("name")) for key, value in request.items() if key.endswith("_category")]) + ")*", ctx=ctx)
                embed.add_field(name="Cost", value=f"{request.get('cost').get('quantity')} {request.get('cost').get('unit')}", inline=True)
                if equipment_category == "Adventuring Gear":
                    embed.add_field(name="Weight", value=f"{request.get('weight')}", inline=True)
                if equipment_category == "Mounts and Vehicles":
                    vehicle_category = request.get("vehicle_category")
                    if vehicle_category == "Mounts and Other Animals":
                        embed.add_field(name="Speed", value=f"{request.get('speed').get('quantity')} {request.get('speed').get('unit')}")
                        embed.add_field(name="Capacity", value=f"{request.get('capacity')}")
                    
                    # FUCKING ADD SHIT HERE
                    # YEAH
                    # YEAH
                    # YEAH
                    # YEAH
                    # YEAH
                    # YEAH
            
            # ==================================================
            # Fallback (if i havent written formatting for the category they chose)
            # Just do general formatting
            # ==================================================
            else:
                embed = oap.makeEmbed(title=f"HERE HAVE A BUNCH OF SHITTY {'JSON' if (isinstance(request, dict)) else 'not json'} DATA LOL!!!!!!!!!!!!!", description="```json\n" + ((json.dumps(request, indent=2) if (isinstance(request, dict)) else request) if len(json.dumps(request, indent=2) if (isinstance(request, dict)) else request) < 2000 else (json.dumps(request, indent=2) if (isinstance(request, dict)) else request)[:2000]) + "```", ctx=ctx)
        
        # ==================================================
        # Otherwise (requested something more specific than just an item)
        # Just do general formatting
        # ==================================================
        else:
            embed = oap.makeEmbed(title=f"HERE HAVE A BUNCH OF SHITTY {'JSON' if (isinstance(request, dict)) else 'not json'} DATA LOL!!!!!!!!!!!!!", description="```json\n" + ((json.dumps(request, indent=2) if (isinstance(request, dict)) else request) if len(json.dumps(request, indent=2) if (isinstance(request, dict)) else request) < 2000 else (json.dumps(request, indent=2) if (isinstance(request, dict)) else request)[:2000]) + "```", ctx=ctx)

        # ==================================================
        # Send output and log to console
        # ==================================================
        await ctx.send(embed=embed)
        oap.log(text=f"Got info on the {item} item from the {category} category", cog="DND", color="magenta", ctx=ctx)


    # ==================================================
    # Rolling stats
    # ==================================================
    @commands.command(brief="Roll standard D&D 5E stats", usage="""\
        <wanted stats, most to least>", help="I can roll character stats for you!
        
        __**Random Assignment**__
        - By default, I'll just give you a list of numbers.
        - If you want them randomly assigned, just use "random"
        `>>roll_stats random`
        
        __**Ordered Assignment**__
        - If you want me to assign the stats in an order you want, list what you want, from highest to lowest.
        - You don't have to input all stats!
        - I'll randomly assign the ones you don't tell me.
        `>>roll_stats int, con, cha`
        `>>rs str, con, int, dex, cha, wis`\
        """, aliases=["rs"])
    async def roll_stats(self, ctx, *, _in=""):
        server_data = oap.getJson(f"servers/{ctx.guild.id}")
        if server_data.get("delete_invocation") == True:
            await oap.tryDelete(ctx)
    
        # ==================================================
        # Argument checking
        # Check if they want anything in order
        # Check if they want random stats or just numbers
        # Check if they entered valid stat names (if ordered)
        # Make the output dict
        # ==================================================
        stats = ["str", "dex", "con", "int", "wis", "cha"]
        ordered = False if _in == "" else True
        random = False
        if _in == "random":
            ordered = False
            random = True
        if ordered:
            for stat in _in.split(" "):
                if stat not in stats:
                    return await oap.give_error(
                        text=f"The stat \"{stat}\" isn't a valid stat!",
                        categories=stats,
                        category_title="Stats",
                        ctx=ctx
                    )
        
        stats = {
            "str": 0,
            "dex": 0,
            "con": 0,
            "int": 0,
            "wis": 0,
            "cha": 0
        }

        # ==================================================
        # Rolling the numbers
        # (4d6, drop the lowest, six times)
        # ==================================================
        rolls = []
        for i in range(6):
            _rolls = [randint(1, 6) for i in range(4)]
            _rolls.remove(min(_rolls))
            rolls.append(sum(_rolls))

        # ==================================================
        # If they wanted an ordered list
        # Assign rolls to the stats highest to lowest
        # If they didnt specify every stat
        # Randomly choose the ones they didnt specify
        # ==================================================
        if ordered:
            for stat in _in.split(" "):
                stats[stat] = max(rolls)
                rolls.remove(max(rolls))
            if len(rolls) > 0:
                for stat in ["con", "dex", "str", "wis", "int", "cha"]:
                    if stats[stat] == 0:
                        stats[stat] = max(rolls)
                        rolls.remove(max(rolls))

        # ==================================================
        # If they want random stats
        # Randomly assign the stats
        # ==================================================
        elif random:
            for i in stats:
                index = randint(0, len(rolls)-1)
                stats[i] = rolls[index]
                del rolls[index]

        # ==================================================
        # If they dont want an ordered list or random stats
        # Just give them the six numbers
        # ==================================================

        # ==================================================
        # Send output and log to console
        # ==================================================
        return await oap.give_output(
            embed_title=f"Rolled stats!",
            embed_description=(
                ", ".join(
                    [str(roll) for roll in rolls]
                )) if (not ordered and not random) 
                else (
                    "\n".join(
                        [f"{key.title()}: {value}" for key, value in stats.items()]
                    )),
            log_text=f"Rolled stats",
            cog=self.cog_name,
            ctx=ctx,
            data=server_data
        )


    # ==================================================
    # List skills
    # ==================================================
    @commands.command(brief="Get a list of all valid skills for >>roll", usage="", help="This just gives you a list of the abbreviated stats you can use with ``>>roll`.\n\n__**Examples**__\n`>>list_skills`")
    async def list_skills(self, ctx):
        server_data = oap.getJson(f"servers/{ctx.guild.id}")
        if server_data.get("delete_invocation") == True:
            await oap.tryDelete(ctx)
    
        # ==================================================
        # Send output
        # Log to console
        # ==================================================
        return await oap.give_output(
            embed_title=f"Here are all skills!",
            embed_description=
                "*- skill (abbreviation)*\n\n- " + 
                "\n- ".join([f"{value} ({key})" for key, value in oap.skills.items()]),
            log_text=f"Listed skills",
            cog=self.cog_name,
            ctx=ctx,
            data=server_data
        )


    # ==================================================
    # Import a character
    # ==================================================
    @commands.command(brief="Import a character from foundry", usage="[name]", help="Import a character from foundry by attaching the .json file to the message you send.\nExport a character from foundry by right clicking the actor and selecting \"Export Data\".\n\n__**Examples**__\n`>>import_character Dave`\n`>>import_char George`\n`>>ic Sophia`", aliases=["import_char", "ic"])
    async def import_character(self, ctx, name=""):    
        # ==================================================
        # Check for an input name
        # Check for attached json file
        # ==================================================
        if name == "":
            embed = oap.makeEmbed(title="Whoops!", description="Please input a name for the character", ctx=ctx)
            return await ctx.send(embed=embed)

        if len(ctx.message.attachments) == 0 or not ctx.message.attachments[0].filename.endswith(".json"):
            embed = oap.makeEmbed(title="Whoops!", description="Please attach a valid .json file", ctx=ctx)
            return await ctx.send(embed=embed)

        # ==================================================
        # If the author doesnt have a characters folder
        # Make it, then
        # Download the attached json
        # ==================================================
        if not path.exists(f"characters/{ctx.author.id}"):
            makedirs(f"characters/{ctx.author.id}")
        await ctx.message.attachments[0].save(f"characters/{ctx.author.id}/{name}.json")
    
        # ==================================================
        # Delete message
        # Send output
        # Log to console
        # ==================================================
        server_data = oap.getJson(f"servers/{ctx.guild.id}")
        if server_data.get("delete_invocation") == True:
            await oap.tryDelete(ctx)
        embed = oap.makeEmbed(title="Success!", description=f"The character \"{name}\" has been added", ctx=ctx)
        await ctx.send(embed=embed)
        oap.log(text="Added a character", cog="DND", color="magenta", ctx=ctx)


    # ==================================================
    # List characters
    # ==================================================
    @commands.command(brief="List all characters you have imported", usage="", help="I'll give you a list of all characters you've given me.\n\n__**Examples**__\n`>>characters`\n`>>chars`\n`>>chs`", aliases=["chars", "chs"])
    async def characters(self, ctx):
        server_data = oap.getJson(f"servers/{ctx.guild.id}")
        if server_data.get("delete_invocation") == True:
            await oap.tryDelete(ctx)
    
        # ==================================================
        # Check if the user has a characters folder
        # ==================================================
        if not path.exists(f"characters/{ctx.author.id}"):
            embed = oap.makeEmbed(title="Whoops!", description="You don't have any characters\nImport one from foundry with >>import_character", ctx=ctx)
            return await ctx.send(embed=embed)

        # ==================================================
        # Send output
        # Log to console
        # ==================================================    
        embed = oap.makeEmbed(title=f"{ctx.author.name}'s Characters", description="- " + "\n- ".join([file[:-5] for file in listdir(f"characters/{ctx.author.id}")]), ctx=ctx)
        await ctx.send(embed=embed)
        oap.log(text="Listed characters", cog="DND", color="magenta", ctx=ctx)


    # ==================================================
    # Character information
    # ==================================================
    @commands.command(brief="Get informaiton on a character you've imported", usage="", help="I'll give you information on a character you've imported.\n\n__**Examples**__\n`>>character Brooklyn`\n`>>char Avi`\n`>>ch Itova`", aliases=["char", "ch"])
    async def character(self, ctx, character="", specific_info=""):
        server_data = oap.getJson(f"servers/{ctx.guild.id}")
        if server_data.get("delete_invocation") == True:
            await oap.tryDelete(ctx)
    
        # ==================================================
        # Check if they supplied a character
        # Check if they have that character
        # ==================================================
        if character == "":
            embed = oap.makeEmbed(title="Whoops!", description="Please enter a characters name", ctx=ctx)
            return await ctx.send(embed=embed)

        if not path.exists(f"characters/{ctx.author.id}"):
            embed = oap.makeEmbed(title="Whoops!", description="You dont have any characters\nImport one from foundry with >>import_character", ctx=ctx)
            return await ctx.send(embed=embed)

        if not path.exists(f"characters/{ctx.author.id}/{character}.json"):
            embed = oap.makeEmbed(title="Whoops!", description="I couldn't find that character\nCheck capital letters, and make sure you spelled it right\nList your characters with >>characters", ctx=ctx)
            return await ctx.send(embed=embed)

        # ==================================================
        # Load the characters file
        # ==================================================
        if True:
            character = oap.getJson(f"characters/{ctx.author.id}/{character}")
            character_data = character["data"]
            abilities = character_data["abilities"]
            attributes = character_data["attributes"]
            details = character_data["details"]
            traits = character_data["traits"]
            currency = character_data["currency"]
            skills = character_data["skills"]
            spells = character_data["spells"]
            bonuses = character_data["bonuses"]
            resources = character_data["resources"]
            items = character["items"]
            linebreak = "\n"

            character_class = ""
            character_items = [""]
            character_spells = [""]
            for value in items:
                if value.get("type") == "class":
                    character_class = value.get("name")
                    character_level = value.get("data").get("levels")
                    character_subclass = value.get("data").get("subclass")
                if value.get("type") not in ["class", "feat", "spell"]:
                    character_items.append(value.get("name"))
                if value.get("type") == "spell":
                    character_spells.append(value.get("name"))

        # ==================================================
        # If they asked for details
        # ==================================================
        if specific_info == "details":
            embed = oap.makeEmbed(title=character.get("name"), description=f"""*Level {character_level} {details["race"]} {character_class}{f" ({character_subclass})" if character_subclass else ""}*

            **Alignment:** {details["alignment"]}

            **Trait:** {details["trait"]}
            **Ideal:** {details["ideal"]}
            **Bond:** {details["bond"]}
            **Flaw:** {details["flaw"]}
            """)

        # ==================================================
        # If they didnt give anything other than a name
        # Start formatting the embed
        # ==================================================
        else:
            movement = [((f"\n**{key}:** {value} ft.") if value and (key != "units") else "") for key, value in attributes["movement"].items()]
            movement = "\n".join(list(filter(lambda value: value != "", movement)))

            senses = [((f"\n**{key}:** {value} ft.") if value and (key != "units") not in [0, ""] else "") for key, value in attributes["senses"].items()]
            senses = "\n".join(list(filter(lambda value: value != "", senses)))

            embed = oap.makeEmbed(title=character.get('name'), description=f"""*Level {character_level} {details["race"]} {character_class}{f" ({character_subclass})" if character_subclass else ""}*

        **AC:** {attributes['ac']['value']}
        **HP:** {attributes['hp']['value']}/{attributes['hp']['max']}
        **Initiative:** {attributes['init']['value']} (+{attributes['init']['bonus']} bonus)

        __**Movement:**__ {movement}

        {f"__**Senses:**__ {senses}" if len(senses) > 1 else ""}
        """, ctx=ctx)

        # ==================================================
        # Send output
        # Log to console
        # ==================================================
        await ctx.send(embed=embed)
        oap.log(text=f"Got info on the {character['name']} character", cog="DND", color="magenta", ctx=ctx)


    # ==================================================
    # Generate a calendar
    # ==================================================
    @commands.command(brief="", usage="", help="", enabled=False)
    async def generate_calendar(self, ctx, *, args=""):
        server_data = oap.getJson(f"servers/{ctx.guild.id}")
        if server_data.get("delete_invocation") == True:
            await oap.tryDelete(ctx)
    
        # ==================================================
        # Arg checking and validation
        # ==================================================


        # ==================================================
        # Send output
        # Log to console
        # ==================================================
        embed = oap.makeEmbed(title="PLACEHOLDER", description="PLACEHOLDER", ctx=ctx)
        await ctx.send(embed=embed)
        oap.log(text="PLACEHOLDER", cog="PLACEHOLDER", color="PLACEHOLDER", ctx=ctx)


# ==================================================
# Cog setup
# ==================================================
def setup(bot):
    oap.log(text="Loaded", cog="DND", color="magenta")
    bot.add_cog(DND(bot))
    reload(oap)
