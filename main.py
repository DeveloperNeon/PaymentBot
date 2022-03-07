import string
import stripe
import discord
import time
import re
import logging
from config import *
from datetime import date, datetime
from discord.ui import Button, View
from discord.ext import commands

# Create intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Information for use
today = date.today()
trim = re.compile(r'[^\d.,]+')

# Payment information
stripe.api_key = Config.stripe_module['key']

# Create class for starting bot to allow for persistent views
class StartBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned_or(Config.prefix), intents=intents)
        self.persistent_views_added = False
    async def on_ready(self):
        print(f"We have logged in as {bot.user}")
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="For Invoices"), status="dnd")

bot = StartBot()

@bot.command(name="createInvoice", aliases=['createinvoice', 'invoice', 'pay'])
async def create_invoice(ctx, member: discord.Member, amount, *, product_name = ""):
    if ctx.author.get_role(Config.role):
        await ctx.message.delete()

        amount = int(trim.sub('',amount))
        url = await create_stripe_invoice(member, amount, product_name)
        await create_invoice_embed(member, url, amount)
        await create_invoice_log(member, amount, 'Stripe')
    else:
        await permission_denied(ctx)


# Function to show permission denied
async def permission_denied(ctx):
    await ctx.message.delete()

    embed = await embed_builder("Permission Denied", "You're not allowed to perform this action.")
    message = await ctx.send(embed=embed)
    time.sleep(5)
    await message.delete()

# Function for building embeds
async def embed_builder(title, description, fields = False, footer = True):
    if fields:
        embed = discord.Embed(title=title, description=f"{description}\n", color=discord.Color.from_rgb(18,95,217))
        for name,value in fields.items():
            embed.add_field(name=name, value=f"`{value}`", inline=False)
    else:
        embed = discord.Embed(title=title, description=description, color=discord.Color.from_rgb(18,95,217))
    if footer:
        embed.set_footer(text=f"© {Config.name} {today.strftime('%Y')} • {today.strftime('%m/%d/%Y')}")
    return embed

async def create_stripe_invoice(member: discord.Member, amount: int, product_name: string):
    customer = stripe.Customer.create(name=member.display_name, description = f"{member.display_name}#{member.discriminator}")
    product = stripe.InvoiceItem.create(currency = 'usd', customer = customer.id, amount = (amount * 100), description = product_name)
    invoice = stripe.Invoice.create(customer = customer.id)
    stripe.Invoice.finalize_invoice(invoice.id)
    redirect = stripe.Invoice.retrieve(invoice.id)

    return redirect.hosted_invoice_url

async def create_invoice_embed(member: discord.Member, url: string, amount: int):
    embed = await embed_builder("Invoice Created", f"Your invoice for the amount of ${amount} to {Config.name} has been created. Please click the button below to pay the invoice.")
    view = View()
    button = Button(label="Pay Invoice", style=discord.ButtonStyle.link, url=url)
    view.add_item(button)
    await member.send(embed=embed, view=view)

async def create_invoice_log(member: discord.Member, amount: int, method: string):
    log_channel = bot.get_channel(Config.log_channel)
    fields = {
        'Method': method,
        'User': member.mention,
        'Amount': amount,
    }
    embed = await embed_builder("Invoice Created", f"An invoice for the amount of ${amount} has been created for {member.mention}.", fields, True)
    await log_channel.send(embed=embed)

bot.run(Config.token)