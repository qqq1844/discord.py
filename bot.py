import discord  
from discord import app_commands  
from discord.ext import commands  
import os  
from datetime import datetime, timedelta  
from database_py import Database  
from config_py import Config  
import io  
  
OWNER_ID = '1416252754925584435'  
  
class LuarmorBot(commands.Bot):  
    def __init__(self):  
        intents = discord.Intents.default()  
        intents.message_content = True  
        intents.members = True  
        intents.guilds = True  
  
        super().__init__(command_prefix='/', intents=intents)  
        self.db = Database()  
        self.config = Config()  
  
    async def setup_hook(self):  
        await self.tree.sync()  
  
    def is_owner(self, user_id: str) -> bool:  
        return user_id == OWNER_ID or self.db.is_owner(user_id)  
  
    def has_manager_role(self, member: discord.Member) -> bool:  
        if self.is_owner(str(member.id)):  
            return True  
  
        panel_config = self.db.get_panel_config()  
        if not panel_config:  
            return any(role.name == 'Manager' for role in member.roles)  
        return any(role.id == int(panel_config['managerRoleId']) for role in member.roles)  
  
bot = LuarmorBot()  
  
@bot.event  
async def on_ready():  
    print(f'Bot logged in as {bot.user}')  
    bot.db.seed_demo_keys()  
    print('Demo keys created: DEMO-KEY-1 through DEMO-KEY-5')  
  
    print('\n=== Luarmor Bot Ready ===')  
    print('Available commands:')  
    print('  /generateapi - Generate API key for a user (Manager)')  
    print('  /login - Login with API key')  
    print('  /setpanel - Configure panel (Manager)')  
    print('  /ownerwl - Add/remove owners (Owner only)')  
    print('  /whitelist - Whitelist a user (Manager, requires login)')  
    print('  /blacklist - Blacklist a user (Manager, requires login)')  
    print('  /force-resethwid - Force reset HWID (Manager, requires login)')  
    print('  /createkey - Create a new key (Manager, requires login)')  
    print('  /genkeys - Generate multiple keys for a user (Manager, requires login)')  
    print('  /listkeys - List all keys (Manager, requires login)')  
    print('  /panel - Open user control panel (requires login)')  
    print('  /status - Check whitelist status (requires login)')  
    print('\nDemo keys available: DEMO-KEY-1 to DEMO-KEY-5')  
  
@bot.tree.command(name="generateapi", description="Generate an API key (Manager only)")  
@app_commands.describe(user="User to send the API key to")  
async def generateapi(interaction: discord.Interaction, user: discord.Member):  
    if not bot.has_manager_role(interaction.user):  
        await interaction.response.send_message('❌ You need the Manager role to use this command.', ephemeral=True)  
        return  
  
    result = bot.db.create_api_key(str(interaction.user.id), str(user.id))  
  
    try:  
        embed = discord.Embed(  
            title='🔑 Your API Key',  
            description=f"You've been given access to **{interaction.guild.name}**!\n\n**You must use this API key to access the bot.**",  
            color=0x0099ff  
        )  
        embed.add_field(name='API Key (50 characters)', value=f"```{result['apiKey']['apiKey']}```", inline=False)  
        embed.add_field(name='How to Login', value='Use `/login <apikey>` in the server to activate your access.\n\n**Without this API key, you cannot use any bot commands!**', inline=False)  
        embed.set_footer(text='Keep this key safe and do not share it!')  
        embed.timestamp = datetime.utcnow()  
  
        await user.send(embed=embed)  
  
        response_embed = discord.Embed(  
            title='✅ API Key Generated',  
            description=f"API key sent to **{user.name}** via DM!",  
            color=0x00ff00  
        )  
        response_embed.add_field(name='Key', value=f"`{result['apiKey']['apiKey']}`", inline=False)  
        response_embed.timestamp = datetime.utcnow()  
  
        await interaction.response.send_message(embed=response_embed, ephemeral=True)  
    except:  
        await interaction.response.send_message(  
            f"❌ Could not DM **{user.name}**. They may have DMs disabled.\n\nAPI Key: `{result['apiKey']['apiKey']}`",  
            ephemeral=True  
        )  
  
@bot.tree.command(name="login", description="Login with your API key")  
@app_commands.describe(apikey="Your API key")  
async def login(interaction: discord.Interaction, apikey: str):  
    result = bot.db.login_with_api_key(str(interaction.user.id), interaction.user.name, apikey)  
  
    if not result['success']:  
        await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)  
        return  
  
    embed = discord.Embed(  
        title='✅ Login Successful!',  
        description='You are now authenticated with your API key and can use all bot commands!',  
        color=0x00ff00  
    )  
    embed.add_field(name='Welcome!', value='Use `/panel` to access your control panel', inline=False)  
    embed.add_field(name='Your API Key', value=f"`{apikey}`", inline=False)  
    embed.timestamp = datetime.utcnow()  
  
    await interaction.response.send_message(embed=embed, ephemeral=True)  
  
@bot.tree.command(name="setpanel", description="Configure the panel (Manager only)")  
@app_commands.describe(  
    channel="Channel to place the panel in",  
    script="Script loadstring",  
    buyerrole="Buyer role",  
    managerrole="Manager role"  
)  
async def setpanel(interaction: discord.Interaction, channel: discord.TextChannel, script: str, buyerrole: discord.Role, managerrole: discord.Role):  
    if not bot.has_manager_role(interaction.user):  
        await interaction.response.send_message('❌ You need the Manager role to use this command.', ephemeral=True)  
        return  
  
    bot.db.set_panel_config(str(channel.id), script, str(buyerrole.id), str(managerrole.id))  
  
    view = discord.ui.View(timeout=None)  
    view.add_item(discord.ui.Button(label='Get Script', style=discord.ButtonStyle.success, emoji='📜', custom_id='get_script'))  
    view.add_item(discord.ui.Button(label='Reset HWID', style=discord.ButtonStyle.primary, emoji='🔄', custom_id='reset_hwid'))  
    view.add_item(discord.ui.Button(label='Get Role', style=discord.ButtonStyle.secondary, emoji='🎭', custom_id='get_role'))  
    view.add_item(discord.ui.Button(label='Redeem Key', style=discord.ButtonStyle.secondary, emoji='🔑', custom_id='redeem_key'))  
    view.add_item(discord.ui.Button(label='Get Stats', style=discord.ButtonStyle.secondary, emoji='📊', custom_id='get_stats'))  
    view.add_item(discord.ui.Button(label='Check Status', style=discord.ButtonStyle.secondary, emoji='ℹ️', custom_id='check_status'))  
  
    embed = discord.Embed(  
        title='🎮 Luarmor Control Panel',  
        description='Welcome! Use the buttons below to manage your access.',  
        color=0x0099ff  
    )  
    embed.add_field(name='📜 Get Script', value='Receive your script loader via DM', inline=True)  
    embed.add_field(name='🔄 Reset HWID', value='Reset your hardware ID', inline=True)  
    embed.add_field(name='🎭 Get Role', value='Claim your buyer role', inline=True)  
    embed.add_field(name='🔑 Redeem Key', value='Redeem a key for 24-hour access', inline=True)  
    embed.add_field(name='📊 Get Stats', value='View your statistics', inline=True)  
    embed.add_field(name='ℹ️ Check Status', value='Check your whitelist status', inline=True)  
    embed.set_footer(text='Make sure you are logged in before using the panel')  
    embed.timestamp = datetime.utcnow()  
  
    try:  
        msg = await channel.send(embed=embed, view=view)  
        bot.db.set_panel_message_id(str(msg.id))  
        await interaction.response.send_message(f'✅ Panel configured successfully in {channel.mention}!', ephemeral=True)  
    except:  
        await interaction.response.send_message('❌ Failed to create panel. Make sure I have permission to send messages in that channel.', ephemeral=True)  
  
@bot.tree.command(name="whitelist", description="Whitelist a user (Manager only)")  
@app_commands.describe(user="User to whitelist", days="Duration in days (default: 30)")  
async def whitelist(interaction: discord.Interaction, user: discord.Member, days: int = 30):  
    if not bot.has_manager_role(interaction.user):  
        await interaction.response.send_message('❌ You need the Manager role to use this command.', ephemeral=True)  
        return  
  
    if not bot.db.is_logged_in(str(interaction.user.id)) and not bot.is_owner(str(interaction.user.id)):  
        await interaction.response.send_message('🔒 **Authentication Required!**\n\nYou must login with your 50-character API key to use this bot.\n\nUse `/login <apikey>` with the API key you received.', ephemeral=True)  
        return  
  
    result = bot.db.whitelist_user(str(user.id), user.name, days)  
  
    if not result['success']:  
        await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)  
        return  
  
    panel_config = bot.db.get_panel_config()  
    panel_mention = f"<#{panel_config['channelId']}>" if panel_config else 'panel'  
  
    await interaction.response.send_message(f"<@{user.id}> you have been whitelisted! go to {panel_mention} to use script.")  
  
@bot.tree.command(name="blacklist", description="Blacklist a user (Manager only)")  
@app_commands.describe(user="User to blacklist", days="Duration in days (0 = permanent)", reason="Reason for blacklist")  
async def blacklist(interaction: discord.Interaction, user: discord.Member, days: int = 0, reason: str = "No reason provided"):  
    if not bot.has_manager_role(interaction.user):  
        await interaction.response.send_message('❌ You need the Manager role to use this command.', ephemeral=True)  
        return  
  
    if not bot.db.is_logged_in(str(interaction.user.id)) and not bot.is_owner(str(interaction.user.id)):  
        await interaction.response.send_message('🔒 **Authentication Required!**', ephemeral=True)  
        return  
  
    bot.db.blacklist_user(str(user.id), user.name, days, reason)  
  
    panel_config = bot.db.get_panel_config()  
    panel_mention = f"<#{panel_config['channelId']}>" if panel_config else 'panel'  
  
    await interaction.response.send_message(f"<@{user.id}> you have been blacklisted!⛔️ go to {panel_mention} click on stats to see the reason.")  
  
@bot.tree.command(name="force-resethwid", description="Force reset a user's HWID (Manager only)")  
@app_commands.describe(user="User to reset HWID for")  
async def force_resethwid(interaction: discord.Interaction, user: discord.Member):  
    if not bot.has_manager_role(interaction.user):  
        await interaction.response.send_message('❌ You need the Manager role to use this command.', ephemeral=True)  
        return  
  
    if not bot.db.is_logged_in(str(interaction.user.id)) and not bot.is_owner(str(interaction.user.id)):  
        await interaction.response.send_message('🔒 **Authentication Required!**', ephemeral=True)  
        return  
  
    result = bot.db.reset_hwid(str(user.id), interaction.user.name)  
  
    if not result['success']:  
        await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)  
        return  
  
    embed = discord.Embed(  
        title='✅ HWID Reset',  
        description=f"**{user.name}**'s HWID has been reset!",  
        color=0x00ff00  
    )  
    embed.timestamp = datetime.utcnow()  
  
    await interaction.response.send_message(embed=embed)  
  
@bot.tree.command(name="createkey", description="Create a new key (Manager only)")  
@app_commands.describe(code="Key code", days="Duration in days (default: 30)")  
async def createkey(interaction: discord.Interaction, code: str, days: int = 30):  
    if not bot.has_manager_role(interaction.user):  
        await interaction.response.send_message('❌ You need the Manager role to use this command.', ephemeral=True)  
        return  
  
    if not bot.db.is_logged_in(str(interaction.user.id)) and not bot.is_owner(str(interaction.user.id)):  
        await interaction.response.send_message('🔒 **Authentication Required!**', ephemeral=True)  
        return  
  
    result = bot.db.create_key(code, days, interaction.user.name)  
  
    if not result['success']:  
        await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)  
        return  
  
    embed = discord.Embed(title='✅ Key Created', color=0x00ff00)  
    embed.add_field(name='Code', value=f"`{code}`", inline=True)  
    embed.add_field(name='Duration', value=f"{days} days", inline=True)  
    embed.timestamp = datetime.utcnow()  
  
    await interaction.response.send_message(embed=embed, ephemeral=True)  
  
@bot.tree.command(name="genkeys", description="Generate multiple keys for a user (Manager only)")  
@app_commands.describe(user="User to send keys to", amount="Number of keys to generate (max 900)", days="Duration in days for each key (default: 30)")  
async def genkeys(interaction: discord.Interaction, user: discord.Member, amount: int, days: int = 30):  
    if not bot.has_manager_role(interaction.user):  
        await interaction.response.send_message('❌ You need the Manager role to use this command.', ephemeral=True)  
        return  
  
    if not bot.db.is_logged_in(str(interaction.user.id)) and not bot.is_owner(str(interaction.user.id)):  
        await interaction.response.send_message('🔒 **Authentication Required!**', ephemeral=True)  
        return  
  
    if amount > 900:  
        amount = 900  
    if amount < 1:  
        await interaction.response.send_message('❌ Amount must be at least 1.', ephemeral=True)  
        return  
  
    await interaction.response.defer(ephemeral=True)  
  
    import time  
    import random  
    import string  
  
    generated_keys = []  
    for i in range(amount):  
        key_code = f"KEY-{int(time.time() * 1000)}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"  
        result = bot.db.create_key(key_code, days, interaction.user.name)  
        if result['success']:  
            generated_keys.append(key_code)  
  
    keys_content = '\n'.join(generated_keys)  
  
    try:  
        await user.send(  
            f"🎁 **You have been rewarded free keys to the script!**\n\nYou received **{len(generated_keys)}** keys, each valid for **{days} days**.\n\nThe keys are attached as a text file below."  
        )  
  
        file = discord.File(io.BytesIO(keys_content.encode()), filename=f"keys-{user.name}-{int(time.time())}.txt")  
        await user.send(file=file)  
  
        await interaction.followup.send(  
            f"✅ Successfully generated and sent **{len(generated_keys)}** keys to **{user.name}** via DM!\n\nEach key is valid for **{days} days**."  
        )  
    except:  
        await interaction.followup.send(  
            f"❌ Could not DM **{user.name}**. They may have DMs disabled.\n\n**{len(generated_keys)}** keys were created but could not be delivered."  
        )  
  
@bot.tree.command(name="listkeys", description="List all keys (Manager only)")  
async def listkeys(interaction: discord.Interaction):  
    if not bot.has_manager_role(interaction.user):  
        await interaction.response.send_message('❌ You need the Manager role to use this command.', ephemeral=True)  
        return  
  
    if not bot.db.is_logged_in(str(interaction.user.id)) and not bot.is_owner(str(interaction.user.id)):  
        await interaction.response.send_message('🔒 **Authentication Required!**', ephemeral=True)  
        return  
  
    keys = bot.db.get_all_keys()  
  
    if not keys:  
        await interaction.response.send_message('📋 No keys found.', ephemeral=True)  
        return  
  
    key_list = []  
    for key in keys[:25]:  
        status_emoji = '✅' if key['status'] == 'redeemed' else ('❌' if key['status'] == 'expired' else '⏳')  
        key_list.append(f"{status_emoji} `{key['code']}` - {key['status']} ({key['duration']}d)")  
  
    embed = discord.Embed(  
        title='📋 Keys List',  
        description='\n'.join(key_list) if key_list else 'No keys',  
        color=0x0099ff  
    )  
    embed.set_footer(text=f"Showing {min(len(keys), 25)} of {len(keys)} keys")  
    embed.timestamp = datetime.utcnow()  
  
    await interaction.response.send_message(embed=embed, ephemeral=True)  
  
@bot.tree.command(name="panel", description="Open user control panel (requires login)")  
async def panel(interaction: discord.Interaction):  
    if not bot.db.is_logged_in(str(interaction.user.id)) and not bot.is_owner(str(interaction.user.id)):  
        await interaction.response.send_message('🔒 **Authentication Required!**', ephemeral=True)  
        return  
  
    user_data = bot.db.get_user(str(interaction.user.id))  
  
    if not user_data or not bot.db.is_user_active(str(interaction.user.id)):  
        await interaction.response.send_message('❌ You are not whitelisted. Please contact an administrator.', ephemeral=True)  
        return  
  
    view = discord.ui.View(timeout=None)  
    view.add_item(discord.ui.Button(label='Get Script', style=discord.ButtonStyle.success, emoji='📜', custom_id='get_script'))  
    view.add_item(discord.ui.Button(label='Reset HWID', style=discord.ButtonStyle.primary, emoji='🔄', custom_id='reset_hwid'))  
    view.add_item(discord.ui.Button(label='Get Role', style=discord.ButtonStyle.secondary, emoji='🎭', custom_id='get_role'))  
    view.add_item(discord.ui.Button(label='Redeem Key', style=discord.ButtonStyle.secondary, emoji='🔑', custom_id='redeem_key'))  
    view.add_item(discord.ui.Button(label='Get Stats', style=discord.ButtonStyle.secondary, emoji='📊', custom_id='get_stats'))  
    view.add_item(discord.ui.Button(label='Check Status', style=discord.ButtonStyle.secondary, emoji='ℹ️', custom_id='check_status'))  
  
    status_text = '✅ Active' if user_data['status'] == 'active' else '❌ Inactive'  
    expires_timestamp = int(user_data['expiresAt'] / 1000)  
  
    embed = discord.Embed(  
        title='🎮 User Control Panel',  
        description='Welcome to your Luarmor control panel!',  
        color=0x0099ff  
    )  
    embed.add_field(name='Status', value=status_text, inline=True)  
    embed.add_field(name='Expires', value=f"<t:{expires_timestamp}:R>", inline=True)  
    embed.add_field(name='HWID', value=user_data.get('hwid') or 'Not set', inline=True)  
    embed.timestamp = datetime.utcnow()  
  
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)  
  
@bot.tree.command(name="status", description="Check your whitelist status (requires login)")  
async def status(interaction: discord.Interaction):  
    if not bot.db.is_logged_in(str(interaction.user.id)) and not bot.is_owner(str(interaction.user.id)):  
        await interaction.response.send_message('🔒 **Authentication Required!**', ephemeral=True)  
        return  
  
    user_data = bot.db.get_user(str(interaction.user.id))  
  
    if not user_data:  
        await interaction.response.send_message('❌ You are not whitelisted.', ephemeral=True)  
        return  
  
    is_active = bot.db.is_user_active(str(interaction.user.id))  
    is_blacklisted = bot.db.is_blacklisted(str(interaction.user.id))  
  
    embed = discord.Embed(  
        title='📊 Whitelist Status',  
        color=0x00ff00 if is_active else 0xff0000  
    )  
    embed.add_field(name='Status', value='✅ Active' if is_active else '❌ Inactive', inline=True)  
    embed.add_field(name='Blacklisted', value='🚫 Yes' if is_blacklisted else '✅ No', inline=True)  
    embed.add_field(name='Expires', value=f"<t:{int(user_data['expiresAt'] / 1000)}:R>", inline=True)  
    embed.add_field(name='HWID', value=user_data.get('hwid') or 'Not set', inline=True)  
    embed.timestamp = datetime.utcnow()  
  
    await interaction.response.send_message(embed=embed, ephemeral=True)  
  
@bot.tree.command(name="ownerwl", description="Add or remove an owner (Owner only)")  
@app_commands.describe(user="User to add/remove as owner", action="Add or remove")  
@app_commands.choices(action=[  
    app_commands.Choice(name="Add", value="add"),  
    app_commands.Choice(name="Remove", value="remove")  
])  
async def ownerwl(interaction: discord.Interaction, user: discord.Member, action: app_commands.Choice[str]):  
    if not bot.is_owner(str(interaction.user.id)):  
        await interaction.response.send_message('❌ Only owners can use this command.', ephemeral=True)  
        return  
  
    if str(user.id) == OWNER_ID:  
        await interaction.response.send_message('❌ Cannot modify the primary owner.', ephemeral=True)  
        return  
  
    if action.value == 'add':  
        bot.db.add_owner(str(user.id), user.name, interaction.user.name)  
  
        embed = discord.Embed(  
            title='👑 Owner Added',  
            description=f"**{user.name}** has been added as an owner!",  
            color=0x00ff00  
        )  
        embed.add_field(name='Permissions', value='• Use all commands without API key\n• Add/remove other owners\n• Full bot access', inline=False)  
        embed.timestamp = datetime.utcnow()  
  
        await interaction.response.send_message(embed=embed)  
    else:  
        bot.db.remove_owner(str(user.id), user.name, interaction.user.name)  
  
        embed = discord.Embed(  
            title='👑 Owner Removed',  
            description=f"**{user.name}** has been removed as an owner.",  
            color=0xff0000  
        )  
        embed.timestamp = datetime.utcnow()  
  
        await interaction.response.send_message(embed=embed)  
  
@bot.event  
async def on_interaction(interaction: discord.Interaction):  
    if interaction.type == discord.InteractionType.component:  
        custom_id = interaction.data['custom_id']  
  
        user_id = str(interaction.user.id)  
        is_whitelisted = bot.db.get_user(user_id) and bot.db.is_user_active(user_id)  
        is_guest = not bot.db.is_logged_in(user_id) and not bot.is_owner(user_id)  
  
        if custom_id in ['get_script', 'get_role', 'get_stats', 'check_status', 'reset_hwid']:  
            if is_guest:  
                await interaction.response.send_message('🔒 **Authentication Required!**\n\nYou must login with your API key or redeem a key to use this function.', ephemeral=True)  
                return  
            if not is_whitelisted:  
                await interaction.response.send_message('❌ Your whitelist has expired or is inactive.', ephemeral=True)  
                return  
  
        if custom_id == 'get_script':  
            panel_config = bot.db.get_panel_config()  
            key_to_use = bot.db.get_key_for_user(user_id) or 'NO-KEY-ASSIGNED'  
  
            if panel_config and panel_config.get('scriptLoadstring'):  
                script_content = panel_config['scriptLoadstring'].replace('{{KEY}}', key_to_use)  
            else:  
                script_content = bot.config.SCRIPT_CONTENT.replace('{{KEY}}', key_to_use)  
  
            try:  
                file = discord.File(io.BytesIO(script_content.encode()), filename='loader.lua')  
                await interaction.user.send('📜 **Here\'s your script!**\n\nCopy and use the script below:', file=file)  
                await interaction.response.send_message('✅ Script sent to your DMs!', ephemeral=True)  
            except:  
                await interaction.response.send_message('❌ Could not send DM. Please enable DMs from server members.', ephemeral=True)  
  
        elif custom_id == 'reset_hwid':  
            if not bot.config.ENABLE_SELF_HWID_RESET:  
                await interaction.response.send_message('❌ Self-service HWID reset is disabled. Contact an administrator.', ephemeral=True)  
                return  
  
            result = bot.db.reset_hwid(user_id)  
  
            if not result['success']:  
                await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)  
                return  
  
            await interaction.response.send_message('✅ Your HWID has been reset successfully!', ephemeral=True)  
  
        elif custom_id == 'get_role':  
            panel_config = bot.db.get_panel_config()  
            if panel_config:  
                role = interaction.guild.get_role(int(panel_config['buyerRoleId']))  
                if role and role not in interaction.user.roles:  
                    await interaction.user.add_roles(role)  
                await interaction.response.send_message(f"✅ <@&{panel_config['buyerRoleId']}> role has been assigned to you!", ephemeral=True)  
            else:  
                buyer_role = discord.utils.get(interaction.guild.roles, name='Buyer')  
                if not buyer_role:  
                    buyer_role = await interaction.guild.create_role(name='Buyer', color=discord.Color.green())  
                if buyer_role not in interaction.user.roles:  
                    await interaction.user.add_roles(buyer_role)  
                await interaction.response.send_message('✅ Buyer role has been assigned to you!', ephemeral=True)  
  
        elif custom_id == 'redeem_key':  
            if bot.db.is_logged_in(user_id) or bot.is_owner(user_id):  
                await interaction.response.send_message('❌ You are already logged in. You cannot redeem another key.', ephemeral=True)  
                return  
            if bot.db.get_user(user_id):  
                await interaction.response.send_message('❌ You already have an active session. Please wait for it to expire or contact an admin.', ephemeral=True)  
                return  
  
            await interaction.response.send_modal(discord.ui.Modal(title="Redeem Key", custom_id="redeem_key_modal",  
                components=[  
                    discord.ui.InputText(label="Enter your key", placeholder="KEY-XXXX-XXXX", custom_id="key_input", style=discord.TextStyle.short)  
                ]  
            ))  
  
        elif custom_id == 'get_stats':  
            user_data = bot.db.get_user(user_id)  
            is_active = bot.db.is_user_active(user_id)  
            active_users = bot.db.get_all_active_users()  
            all_keys = bot.db.get_all_keys()  
            redeemed_keys = sum(1 for k in all_keys if k['status'] == 'redeemed')  
            blacklist_info = bot.db.get_blacklist_info(user_id)  
  
            stats_message = f"**📊 Your Statistics**\n\n"  
            stats_message += f"Your Status: {'✅ Active' if is_active else '❌ Inactive'}\n"  
            stats_message += f"Your HWID: {user_data.get('hwid') or 'Not set'}\n"  
            stats_message += f"Expires: <t:{int(user_data['expiresAt'] / 1000)}:R>\n"  
  
            if blacklist_info:  
                stats_message += f"\n⛔️ **BLACKLISTED**\n"  
                stats_message += f"Reason: {blacklist_info['reason']}\n"  
                if blacklist_info['permanent']:  
                    stats_message += "Duration: Permanent\n"  
                else:  
                    stats_message += f"Duration: Until <t:{int(blacklist_info['unblacklistAt'] / 1000)}:R>\n"  
  
            stats_message += f"\nTotal Active Users: {len(active_users)}\n"  
            stats_message += f"Total Keys: {len(all_keys)}\n"  
            stats_message += f"Redeemed Keys: {redeemed_keys}"  
  
            await interaction.response.send_message(stats_message, ephemeral=True)  
  
        elif custom_id == 'check_status':  
            user_data = bot.db.get_user(user_id)  
            is_active = bot.db.is_user_active(user_id)  
  
            embed = discord.Embed(  
                title='📊 Your Status',  
                color=0x00ff00 if is_active else 0xff0000  
            )  
            embed.add_field(name='Status', value='✅ Active' if is_active else '❌ Inactive', inline=True)  
            embed.add_field(name='Expires', value=f"<t:{int(user_data['expiresAt'] / 1000)}:R>", inline=True)  
            embed.add_field(name='HWID', value=user_data.get('hwid') or 'Not set', inline=True)  
            embed.timestamp = datetime.utcnow()  
  
            await interaction.response.send_message(embed=embed, ephemeral=True)  
  
    elif interaction.type == discord.InteractionType.modal_submit:  
        if interaction.data['custom_id'] == 'redeem_key_modal':  
            key = interaction.data['components'][0]['components'][0]['value']  
            user_id = str(interaction.user.id)  
  
            if bot.db.is_logged_in(user_id) or bot.is_owner(user_id):  
                await interaction.response.send_message('❌ You are already logged in. You cannot redeem another key.', ephemeral=True)  
                return  
            if bot.db.get_user(user_id):  
                await interaction.response.send_message('❌ You already have an active session. Please wait for it to expire or contact an admin.', ephemeral=True)  
                return  
  
            result = bot.db.redeem_key(user_id, interaction.user.name, key)  
  
            if not result['success']:  
                await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)  
                return  
  
            user_data = bot.db.get_user(user_id)  
            expires_timestamp = int(user_data['expiresAt'] / 1000)  
  
            embed = discord.Embed(  
                title='🔑 Key Redeemed Successfully!',  
                description='You have gained 24-hour access to the script!',  
                color=0x00ff00  
            )  
            embed.add_field(name='Expires', value=f"Your access will expire <t:{expires_timestamp}:R>", inline=False)  
            embed.set_footer(text='Enjoy using the script!')  
            embed.timestamp = datetime.utcnow()  
  
            await interaction.response.send_message(embed=embed, ephemeral=True)  
  
token = os.environ.get('DISCORD_BOT_TOKEN')  
if not token:  
    raise Exception('DISCORD_BOT_TOKEN not found in environment variables')  
  
bot.run(token)  
