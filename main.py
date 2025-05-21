import os
import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone
from collections import defaultdict

# IDs dos canais e servidor
GUILD_ID = 1373298275700047963
CANAL_COLETA = 1373300281730924624
CANAL_COLETA_ADMIN = 1374559903414227155
CANAL_RANKING = 1374656368979480617
CANAL_MUNICAO = 1373305755465158677
CANAL_MUNICAO_ADMIN = 1374613709770723440

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

registros_coleta = []

# Modal para registro de coleta
class RegistroModal(discord.ui.Modal, title="Registrar Coleta"):
    nome = discord.ui.TextInput(label="Seu Nome", required=True)
    discord_id = discord.ui.TextInput(label="Seu ID", required=True)
    caixas = discord.ui.TextInput(label="Quantidade de Caixas", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qtd = int(self.caixas.value)
            data = {
                "nome": self.nome.value,
                "id": self.discord_id.value,
                "caixas": qtd,
                "timestamp": datetime.now(timezone.utc),
                "user": interaction.user
            }
            registros_coleta.append(data)

            embed = discord.Embed(
                title="Nova Coleta Registrada",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Nome", value=self.nome.value, inline=False)
            embed.add_field(name="ID", value=self.discord_id.value, inline=True)
            embed.add_field(name="Caixas", value=str(qtd), inline=True)
            embed.set_footer(text=f"Registrado por {interaction.user}", icon_url=interaction.user.display_avatar.url)

            canal = bot.get_channel(CANAL_COLETA_ADMIN)
            if canal:
                await canal.send(embed=embed)

            await interaction.response.send_message("Coleta registrada com sucesso!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Erro: quantidade inválida.", ephemeral=True)

class RegistroView(discord.ui.View):
    @discord.ui.button(label="REGISTRAR COLETA", style=discord.ButtonStyle.success)
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RegistroModal())

@tasks.loop(minutes=30)
async def atualizar_ranking():
    hoje = datetime.now(timezone.utc).date()
    contagem = defaultdict(int)
    for r in registros_coleta:
        if r["timestamp"].date() == hoje:
            contagem[r["nome"]] += r["caixas"]

    ranking = sorted(contagem.items(), key=lambda x: x[1], reverse=True)
    texto = "\n".join([f"**{i+1}. {nome}** — {caixas} caixas" for i, (nome, caixas) in enumerate(ranking)]) or "Nenhum registro hoje."

    embed = discord.Embed(
        title="**Ranking Diário de Coletas**",
        description=texto,
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )
    canal = bot.get_channel(CANAL_RANKING)
    if canal:
        await canal.purge(limit=3)
        await canal.send(embed=embed)

# Venda de munições
class EntregaSelect(discord.ui.Select):
    def __init__(self, modal):
        self.modal = modal
        options = [
            discord.SelectOption(label="Sim", description="Entrega realizada"),
            discord.SelectOption(label="Não", description="Entrega pendente")
        ]
        super().__init__(placeholder="Entrega realizada?", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        self.modal.entrega_opcao = self.values[0]
        await self.modal.enviar_registro_final(interaction)

class VendaMuniModal(discord.ui.Modal, title="Registrar Venda de Munição"):

    def __init__(self):
        super().__init__()
        self.entrega_opcao = None
        self.nome_vendedor = discord.ui.TextInput(label="Nome do Vendedor", required=True)
        self.id_vendedor = discord.ui.TextInput(label="ID do Vendedor", required=True)
        self.descricao = discord.ui.TextInput(label="Descrição da Venda", style=discord.TextStyle.paragraph, required=True)
        self.valor_total = discord.ui.TextInput(label="Valor Total da Venda (R$)", required=True)
        self.add_item(self.nome_vendedor)
        self.add_item(self.id_vendedor)
        self.add_item(self.descricao)
        self.add_item(self.valor_total)

    async def on_submit(self, interaction: discord.Interaction):
        select = EntregaSelect(self)
        view = discord.ui.View()
        view.add_item(select)
        await interaction.response.send_message("Selecione se a entrega foi realizada:", view=view, ephemeral=True)

    async def enviar_registro_final(self, interaction: discord.Interaction):
        try:
            valor = float(self.valor_total.value.replace(",", "."))
            canal = bot.get_channel(CANAL_MUNICAO_ADMIN)
            embed = discord.Embed(
                title="Venda de Munição Registrada",
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Nome do Vendedor", value=self.nome_vendedor.value, inline=True)
            embed.add_field(name="ID do Vendedor", value=self.id_vendedor.value, inline=True)
            embed.add_field(name="Descrição", value=self.descricao.value, inline=False)
            embed.add_field(name="Entrega Realizada", value=self.entrega_opcao, inline=True)
            embed.add_field(name="Valor Total", value=f"R$ {valor:.2f}", inline=True)
            embed.set_footer(text=f"Registrado por {interaction.user}", icon_url=interaction.user.display_avatar.url)

            if canal:
                await canal.send(embed=embed)
            await interaction.followup.send("Venda registrada com sucesso!", ephemeral=True)

        except ValueError:
            await interaction.followup.send("Erro: Valor inválido.", ephemeral=True)

class VendaMuniView(discord.ui.View):
    @discord.ui.button(label="REGISTRAR VENDA DE MUNIÇÃO", style=discord.ButtonStyle.danger)
    async def vender(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VendaMuniModal())

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    canal_coleta = bot.get_channel(CANAL_COLETA)
    canal_muni = bot.get_channel(CANAL_MUNICAO)

    if canal_coleta:
        embed = discord.Embed(
            title="**REGISTRO DE COLETAS**",
            description="Clique no botão abaixo para registrar sua coleta.",
            color=discord.Color.green()
        )
        await canal_coleta.purge(limit=5)
        await canal_coleta.send(embed=embed, view=RegistroView())

    if canal_muni:
        embed = discord.Embed(
            title="**VENDA DE MUNIÇÕES**",
            description="Clique no botão abaixo para registrar uma venda.",
            color=discord.Color.dark_red()
        )
        await canal_muni.purge(limit=5)
        await canal_muni.send(embed=embed, view=VendaMuniView())

@bot.event
async def on_ready():
 
   print(f'Bot conectado como {bot.user}')
   atualizar_ranking.start()

import os

bot.run(os.getenv("DISCORD_TOKEN"))
