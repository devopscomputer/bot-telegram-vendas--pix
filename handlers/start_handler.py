from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.database import get_user_balance

async def start(update, context):
    user_id = update.message.from_user.id
    balance, points = get_user_balance(user_id)

    keyboard = [
        [InlineKeyboardButton("💳 Compra CC", callback_data='compra_cc')],
        [InlineKeyboardButton("🏦 Minha conta", callback_data='minha_conta')],
        [InlineKeyboardButton("⚙️ Dono", callback_data='dono')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"💳 Bem-vindo à central de vendas e gerenciamento de produtos da @GalvanniStoreBot.\n\n"
                                    f"🏦 Carteira:\n"
                                    f" ├ ID: {user_id}\n"
                                    f" ├💰 Saldo: R$ {balance:.2f}\n"
                                    f" └💎 Pontos: {points:.2f}",
                                    reply_markup=reply_markup)
