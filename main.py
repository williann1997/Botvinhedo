import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timezone
from dotenv import load_dotenv

# Carrega as variáveis do .env
load_dotenv()

# Variáveis de canal (substitua pelos IDs reais)
CANAL_COLETA = 123456789012345678
CANAL_MUNICAO = 123456789012345679
CANAL_MUNICAO_ADMIN = 123456789012345680

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Classe do modal de venda
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

# Select para entrega (presumo que você já tenha isso definido)
class EntregaSelect(discord.ui.Select):
    def __init__(self, modal: VendaMuniModal):
        self.modal = modal
        options = [
            discord.SelectOption(label="Sim", description="Entrega realizada com sucesso"),
            discord.SelectOption(label="Não", description="Entrega não realizada"),
        ]
        super().__init__(placeholder="Entrega foi realizada?", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.modal.entrega_opcao = self.values[0]
        await self.modal.enviar_registro_final(interaction)

# View com botão de venda
class VendaMuniView(discord.ui.View):
    @discord.ui.button(label="REGISTRAR VENDA DE MUNIÇÃO", style=discord.ButtonStyle.danger)
    async def vender(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VendaMuniModal())

# Exemplo de RegistroView
class RegistroView(discord.ui.View):
    @discord.ui.button(label="REGISTRAR COLETA", style=discord.ButtonStyle.success)
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Formulário de coleta ainda não implementado.", ephemeral=True)

# Task de ranking (exemplo vazio)
@tasks.loop(hours=24)
async def atualizar_ranking():
    print("Atualizando ranking...")

# Evento on_ready
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

    atualizar_ranking.start()

# Inicia o bot com o token do .env
bot.run(os.getenv("DISCORD_TOKEN"))
