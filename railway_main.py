import os
import discord
from discord.ext import commands
import requests
import re
from flask import Flask
from threading import Thread

# Configuration
TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
KIT_API_KEY = os.environ.get('KIT_API_KEY')
KIT_FORM_ID = os.environ.get('KIT_FORM_ID', '7859903')

if not TOKEN:
    print("❌ DISCORD_BOT_TOKEN manquant dans les variables d'environnement")
    exit()

if not KIT_API_KEY:
    print("❌ KIT_API_KEY manquant dans les variables d'environnement")
    exit()

KIT_API_URL = f'https://api.convertkit.com/v3/forms/{KIT_FORM_ID}/subscribe'

# Configuration du bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def is_valid_email(email):
    """Vérifie si l'email est valide"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Modal pour saisir l'email
class EmailModal(discord.ui.Modal, title='🎁 Accéder à la valeur gratuite'):
    def __init__(self):
        super().__init__()

    email = discord.ui.TextInput(
        label='📧 Ton adresse email',
        placeholder='exemple@gmail.com',
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        user_email = self.email.value.strip()
        
        # Vérification du format email
        if not is_valid_email(user_email):
            embed = discord.Embed(
                title="❌ Email invalide",
                description="Assure-toi que ton email est au bon format :\n`exemple@domaine.com`",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Préparation de la requête vers Kit
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "email": user_email,
            "first_name": str(interaction.user).split('#')[0],
            "api_key": KIT_API_KEY,
            "fields": {
                "discord_username": str(interaction.user),
                "discord_server": interaction.guild.name,
                "source": "Discord Bot Modal"
            }
        }
        
        try:
            # Envoi vers Kit
            response = requests.post(KIT_API_URL, headers=headers, json=data, timeout=10)
            
            if response.status_code in [200, 201]:
                # Succès - Attribution du rôle
                role = discord.utils.get(interaction.guild.roles, name="Valeur-gratuit")
                if role:
                    await interaction.user.add_roles(role)
                    role_msg = f"\n🎯 Rôle **{role.name}** attribué !"
                else:
                    role_msg = "\n⚠️ Rôle non trouvé (crée un rôle 'Valeur-gratuit')"
                
                embed = discord.Embed(
                    title="✅ Accès débloqué !",
                    description=f"Ton email `{user_email}` a bien été enregistré !{role_msg}\n\n🎉 Tu as maintenant accès aux valeurs gratuites !",
                    color=0x00ff00
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Log dans la console
                print(f"✅ Email ajouté: {user_email} par {interaction.user} ({interaction.guild.name})")
                
            else:
                embed = discord.Embed(
                    title="❌ Erreur d'enregistrement",
                    description="Une erreur est survenue. Contacte un admin si ça persiste.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                print(f"❌ Erreur Kit {response.status_code}: {response.text}")
                
        except requests.exceptions.Timeout:
            embed = discord.Embed(
                title="⏱️ Timeout",
                description="La requête a pris trop de temps. Réessaie dans quelques secondes.",
                color=0xffa500
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur technique",
                description="Une erreur inattendue s'est produite. Contacte un admin.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(f"❌ Erreur: {e}")

# Vue avec le bouton permanent
class AccessView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Bouton permanent

    @discord.ui.button(label='🎁 Accéder à la valeur gratuite', style=discord.ButtonStyle.success, custom_id='access_button')
    async def access_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Vérifier si l'utilisateur a déjà le rôle
        role = discord.utils.get(interaction.guild.roles, name="Valeur-gratuit")
        if role and role in interaction.user.roles:
            embed = discord.Embed(
                title="✅ Accès déjà débloqué !",
                description="Tu as déjà accès aux valeurs gratuites !",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Ouvrir la modal
        await interaction.response.send_modal(EmailModal())

@bot.event
async def on_ready():
    print(f'✅ Bot connecté en tant que {bot.user}')
    print(f'🔗 Bot présent sur {len(bot.guilds)} serveur(s)')
    
    # Ajouter la vue persistante pour les boutons
    bot.add_view(AccessView())
    print("🔄 Vue persistante ajoutée")
    
    # Synchroniser les commandes slash
    try:
        synced = await bot.tree.sync()
        print(f"🔄 {len(synced)} commande(s) slash synchronisée(s)")
    except Exception as e:
        print(f"❌ Erreur sync commandes: {e}")

@bot.command(name='setup')
@commands.has_permissions(administrator=True)
async def setup_access_message(ctx):
    """Commande pour créer le message avec bouton (admins seulement)"""
    
    embed = discord.Embed(
        title="🎁 Accéder à la valeur gratuite",
        description="Clique sur le bouton ci-dessous pour débloquer l'accès à toute notre valeur gratuite !\n\n📧 **Il te suffit de renseigner ton email**\n✅ **Tu recevras automatiquement l'accès**",
        color=0x000000  # Noir pour la barre de côté
    )
    embed.add_field(
        name="ℹ️ Information", 
        value="• 100% gratuit, il suffit de mettre ton email\n• Accès direct au salon avec les valeurs gratuites", 
        inline=False
    )
    embed.set_footer(text="Clique sur le bouton vert ci-dessous pour commencer")
    
    view = AccessView()
    await ctx.send(embed=embed, view=view)
    
    # Supprimer la commande pour garder le salon propre
    await ctx.message.delete()

@bot.command(name='test')
async def test_bot(ctx):
    """Commande de test simple"""
    await ctx.send("🤖 Bot fonctionnel !")

@bot.command(name='stats')
@commands.has_permissions(administrator=True)
async def stats(ctx):
    """Statistiques du bot (admins seulement)"""
    role = discord.utils.get(ctx.guild.roles, name="Valeur-gratuit")
    premium_count = len(role.members) if role else 0
    
    embed = discord.Embed(
        title="📊 Statistiques du bot",
        description=f"🔗 Serveurs: {len(bot.guilds)}\n👥 Utilisateurs: {len(bot.users)}\n✅ Membres avec valeur gratuite: {premium_count}",
        color=0x0099ff
    )
    await ctx.send(embed=embed)

# Gestion d'erreurs pour les commandes
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu n'as pas les permissions pour cette commande.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore les commandes inexistantes
    else:
        print(f"Erreur commande: {error}")

# Keep-alive pour Railway (optionnel)
app = Flask('')

@app.route('/')
def home():
    return "Bot Discord actif sur Railway !"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Lancement du bot
if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)