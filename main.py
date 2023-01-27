# _-_ encoding: utf-8 _-_
import disnake
from datetime import time
from disnake.ext import commands
import asyncio
import json
from re import A
from unicodedata import name
from disnake import Client
from pyqiwip2p import QiwiP2P

qiwi_auth = ""#https://qiwi.com/p2p-admin/transfers/api
token = ""#https://discord.com/developers/applications
guildid = 884982510013022248
logid = 985527720899395584
bot = commands.Bot(command_prefix=commands.when_mentioned_or(">"), intents=disnake.Intents.all(), help_command=None)
p2p = QiwiP2P(qiwi_auth)

@bot.event
async def on_dropdown(interaction):
    for option in interaction.component.options:
        if option.label == interaction.values[0]:
            if option.description == "Отсуствует":
                await interaction.response.send_message("Товара нет в наличии", ephemeral=True)
            else:
                bill = p2p.bill(lifetime=360, comment=f"Покупка {option.label}", amount=int(option.description))
                with open("database.json", "r", encoding = "utf-8") as f:
                    data1 = str(f.read())
                    data2 = json.loads(data1) 
                with open("database.json", "w", encoding = "utf-8") as write_file:
                    try:
                        data2["qiwi"].append({
                            "name": option.label,
                            "bill_id": bill.bill_id,
                            "author": int(interaction.author.id),
                            "expires": int(360 * 60),
                            "paid": "False"
                        })
                    except Exception as e:
                        print(e)
                        data2["qiwi"].append({
                            "name": interaction.component.options[0].label,
                            "bill_id": bill.bill_id,
                            "author": int(interaction.author.id),
                            "expires": int(360 * 60),
                            "paid": "False"
                        })
                    json.dump(data2, write_file, indent=4)
                    await interaction.response.send_message(content=f"Ссылка на оплату товара {interaction.component.options[0].label}: {bill.pay_url}")

@bot.command()
async def tovar(ctx: commands.Context):
    with open("last_tovar_msg_id", "r", encoding = "utf-8") as f:
        last_tovar_msg_id = str(f.read())
    with open("database.json", "r", encoding = "utf-8") as f:
        data = str(f.read())
    records = json.loads(data)
    view = disnake.ui.View() 
    list = []
    for value in records["slots"]:
        if value['availability'] != "False":
            list.append(disnake.SelectOption(label=value['name'], description=f"**{str(value['price'])}**", emoji="✅"))
        else:
            list.append(disnake.SelectOption(label=value['name'], description="**Отсуствует**", emoji="❌"))
    select = disnake.ui.Select(
        placeholder="Выберите товар для покупки",
        min_values=1,
        max_values=1,
        options=list
    )
    view.add_item(item=select)
    embed=disnake.Embed(title="Товары")
    for value in records["slots"]:
        embed.add_field(name=value['name'], value=f"{value['description']} Цена: {str(value['price'])}", inline=False)
    embed.set_footer(text="Все товары можно купить по меню ниже")
    embed.color = disnake.Color.blurple()
    if last_tovar_msg_id == "":
        msg1 = await ctx.send(embed=embed, view=view)
        with open("last_tovar_msg_id", "w", encoding = "utf-8") as f:
            f.write(str(msg1.id))
    else:
        try:
            for channel in ctx.guild.text_channels:
                msg = await channel.fetch_message(last_tovar_msg_id)
                if msg:
                    await msg.edit(content = "", embed = embed, view = view)
                    break
        except Exception as e:
            print(e)

@bot.command()
async def add(ctx):
    mes = await ctx.send("Напишите название товара")
    name = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
    await name.delete()
    await mes.edit(content="Напишите описание товара")
    description = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
    await description.delete()
    await mes.edit(content="Напишите цену товара")
    price = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
    await price.delete()
    await mes.edit(content="Напишите наличие товара `True/False`")
    availability = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
    await availability.delete()
    await mes.edit(content=add_item_to_db(name.content, description.content, price.content, availability.content))

@bot.command()
async def edit(ctx):
    mes = await ctx.send("Напишите название товара")
    name = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
    await name.delete()
    await mes.edit(content="Напишите цену товара\n`None` если не нужно изменять")
    price = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
    await price.delete()
    await mes.edit(content="Напишите наличие товара `True/False` \n`None` если не нужно изменять")
    availability = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
    await availability.delete()
    await mes.edit(content=edit_item_in_db(name.content, price.content, availability.content))

@bot.command()
async def delete(ctx):
    mes = await ctx.send("Напишите название товара для удаления")
    name = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
    await name.delete()
    await mes.edit(content=remove_item_from_db(name.content))

@bot.command()
async def help(ctx):
    embed=disnake.Embed(title="Команды")
    embed.description = "После любого изменения товаров пропишите >tovar для изменения embed сообщения. Оно само не меняется потому что я тупой и мне лень че-то придумывать"
    embed.color = disnake.Color.blurple()
    embed.add_field(name=">tovar", value="Показывает список товаров", inline=False)
    embed.add_field(name=">add", value="Добавляет товар в список", inline=False)
    embed.add_field(name=">edit", value="Редактирует товар в списке", inline=False)
    embed.add_field(name=">delete", value="Удаляет товар из списка", inline=False)
    embed.add_field(name=">help", value="Показывает список команд", inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print("Бот запущен")
    bot.loop.create_task(check_bills())

async def check_bills():
    while True:
        with open("database.json", "r", encoding = "utf-8") as f:
            data = str(f.read())
            records = json.loads(data)
        for value in records["qiwi"]:
            if value['paid'] != "PAID":
                if str(p2p.check(value['bill_id']).status) == "PAID":
                    value['paid'] == "True"
                    with open("database.json", "w", encoding = "utf-8") as write_file:
                        json.dump(records, write_file, indent=4)
                    guild = bot.get_guild(guildid)
                    try:
                        await guild.fetch_member(int(value['author'])).send(f"Спасибо за покупку {value['name']}. Скоро администратор свяжется с вами. Не закрывайте личные сообщения до выдачи товара.")
                    except:
                        await guild.fetch_channel(logid).send(f"Не смог написать {value['author']}. Скорее всего закрыты личные сообщения")
                    await guild.fetch_channel(logid).send(f"Пользователь {value['author']} оплатил товар {value['name']}")
        await asyncio.sleep(.2)
        await asyncio.sleep(40)

def edit_item_in_db(name, price, availability):
    with open("database.json", "r", encoding = "utf-8") as f:
        data = str(f.read())
        records = json.loads(data)
        for row in records['slots']:
            if row['name'] == name:
                if price != "None":
                    row['price'] = price
                if availability != "None":
                    row['availability'] = availability
                with open("database.json", "w", encoding = "utf-8") as write_file:
                    json.dump(records, write_file, indent=4)
                return "Товар изменен"
        return "Товар не найден"


def remove_item_from_db(name):
    with open("database.json", "r", encoding = "utf-8") as f:
        data = str(f.read())
        records = json.loads(data)
    for row in records['slots']:
        if row['name'] == name:
            indx = records['slots'].index(row)
            del records['slots'][indx]
            with open("database.json", "w", encoding = "utf-8") as write_file:
                json.dump(records, write_file, indent=4)
            return "Товар удален"
    return "Товар не найден"

def add_item_to_db(name: str = None, description: str = None, price: str = None, availability: str = None):
    if name is None:
        return "Не указано название товара"
    if description is None:
        return "Не указано описание товара"
    if price is None:
        return "Не указана цена товара"
    if availability is None:
        return "Не указано наличие товара"
    if availability != "False" and availability != "True":
        return "Неверно указано наличие товара. Указывайте в виде `True/False`!!!"
    price if price.isdigit() else "Неверно указана цена товара. Указывайте в виде числа!!!"
    with open("database.json", "r", encoding = "utf-8") as f:
        data1 = str(f.read())
        data2 = json.loads(data1) 
    with open("database.json", "w", encoding = "utf-8") as write_file:
        data2["slots"].append({
            "name": name,
            "description": description,
            "price": price,
            "availability": availability
            })
        json.dump(data2, write_file, indent=4)
    return "Товар с названием `" + name + "`, описанием `" + description + "`, ценой `" + str(price) + "` и наличием `" + str(availability) + "` добавлен в базу данных"

bot.run(token)
