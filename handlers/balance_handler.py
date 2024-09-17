from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext
from utils.database import get_user_balance, search_products, update_user_balance
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_purchase(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()

    balance, points = get_user_balance(user_id)
    logger.info(f"Callback data received: {query.data}")  # Debugging info

    if query.data == 'cc_full':
        logger.info("User selected 'CC Full'")
        await query.edit_message_text(
            text=f"💳 Comprar Full (Com dados do titular)\n\n"
                 f"⚠️ Compre apenas se você estiver de acordo com as regras:\n\n"
                 f"⏳ PRAZO PARA TROCAS É DE 10 MINUTOS.\n"
                 f"📌 TESTEM A CC NESSE LINK: https://pay.google.com/gp/w/u/0/home/paymentmethods\n"
                 f"📌 ENVIAR O VIDEO DO TESTE PARA O SUPORTE: (@suporte_galvanni).\n"
                 f"📌 MESMO MATERIAL ACOMPANHANDO CPF, NÃO GARANTIMOS OS DADOS BATER 100% DOS CASOS.\n"
                 f"📌 NÃO FAZEMOS ESTORNO DE PIX.\n"
                 f"📌 Não será aceito nenhum teste como prova a não ser do GOOGLE PAY.\n"
                 f"📌 Em hipótese alguma será feito troca fora do prazo de 10 minutos da compra, favor não insistir ou será BLOQUEADO.\n\n"
                 f"- Escolha abaixo o produto que deseja comprar.\n\n"
                 f"🏦 Carteira:\n"
                 f" ├ ID: {user_id}\n"
                 f" ├💰 Saldo: R$ {balance:.2f}\n"
                 f" └💎 Pontos: {points:.2f}\n",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Unitária", callback_data='cc_unitaria')],
                [
                    InlineKeyboardButton("🏦 Pesquisar banco", callback_data='search_full_bank'),
                    InlineKeyboardButton("💳 Pesquisar bin", callback_data='search_full_bin')
                ],
                [
                    InlineKeyboardButton("🏴 Pesquisar bandeira", callback_data='search_full_vendor'),
                    InlineKeyboardButton("📑 Pesquisar level", callback_data='search_full_level')
                ],
                [
                    InlineKeyboardButton("🌍 Pesquisar país", callback_data='search_full_country')
                ],
                [InlineKeyboardButton("⬅️ Voltar", callback_data='back')]
            ])
        )

    elif query.data.startswith('search_full'):
        search_type = query.data.split('_')[-1]
        logger.info(f"User selected search: {search_type}")
        
        # Salvar o tipo de pesquisa no contexto e enviar o comando para a caixa de mensagem do usuário
        context.user_data['search_type'] = search_type
        await update.message.reply_text(f"@{context.bot.username} search_full {search_type} ")
    
    elif query.data == 'cc_unitaria':
        logger.info(f"Handling 'cc_unitaria' for user {user_id}")
        keyboard = [
            [InlineKeyboardButton("AMEX | R$100", callback_data='comprar_amex')],
            [InlineKeyboardButton("BLACK | R$100", callback_data='comprar_black')],
            [InlineKeyboardButton("BUSINESS | R$100", callback_data='comprar_business')],
            [InlineKeyboardButton("PLATINUM | R$100", callback_data='comprar_platinum')],
            [InlineKeyboardButton("GOLD | R$100", callback_data='comprar_gold')],
            [InlineKeyboardButton("STANDARD | R$100", callback_data='comprar_standard')],
            [InlineKeyboardButton("CLASSIC | R$100", callback_data='comprar_classic')],
            [InlineKeyboardButton("CORPORATE | R$100", callback_data='comprar_corporate')],
            [InlineKeyboardButton("⬅️ Voltar", callback_data='cc_full')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        logger.info("Displaying CC Unitária options")
        await query.edit_message_text("Escolha o tipo de CC para compra:", reply_markup=reply_markup)

    elif query.data.startswith('comprar_'):
        card_type = query.data.split('_')[1].upper()
        balance, _ = get_user_balance(user_id)
        price = 100.00  # Preço fixo para cada tipo de CC

        if balance >= price:
            new_balance = balance - price
            update_user_balance(user_id, new_balance, 0.0)
            product = search_products(card_type)
            if product and len(product) > 0:
                await query.edit_message_text(
                    text=f"✅ Compra realizada com sucesso!\n\n"
                         f"Detalhes do produto:\n"
                         f"💳 {product[0][3]}\n"
                         f"Banco: {product[0][6]}\n"
                         f"Titular: {product[0][8]}\n\n"
                         f"Seu novo saldo é: R$ {new_balance:.2f}"
                )
            else:
                await query.edit_message_text("❌ Cartão indiponivel no momento.")
        else:
            await query.edit_message_text("❌ Saldo insuficiente para completar a compra. Faça uma recarga digitando:/pix 20, 30")
    
    else:
        logger.warning(f"Unhandled callback data: {query.data}")

async def handle_search_result(update: Update, context: CallbackContext):
    search_type = context.user_data.get('search_type')
    filter_value = update.message.text.strip()
    
    # Realiza a busca no banco de dados com base no tipo de pesquisa
    products = search_products(filter_value)
    
    if not products:
        await update.message.reply_text("❌ Nenhum produto encontrado.")
        return
    
    # Criação da mensagem com os resultados encontrados
    message = f"🔍 {len(products)} CC(s) foram encontrados\n\n"
    message += "Escolha uma das opções abaixo:\n\n"
    
    for product in products:
             message = (
    f"💳 **{product[1]}** - R$ {product[2]:.2f}\n\n"  # Gold level and price
    f"💳 *Produto:*\n"
    f"*País:* 🇧🇷Brasil\n"
    f"*Número:* {product[4][:6]}********\n"
    f"*Validade:* {product[4][13:]}\n"
    f"*CVV:* ***\n"
    f"*Bandeira:* {product[5]}\n"
    f"*Banco:* {product[6]}\n\n"
    f"**Dados do Titular:**\n"
    f"Nome: {product[8][:5]}***** ***\n"
    f"CPF: {product[9][:3]}********\n\n"
    f"**Dados auxiliares:**\n"
    f"Nome: {product[10][:7]}***** *****\n"
    f"CPF: {product[11][:3]}********\n\n"
)
    
    await update.message.reply_text(message)
