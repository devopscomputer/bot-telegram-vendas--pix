import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, filters, MessageHandler, InlineQueryHandler
from uuid import uuid4
from datetime import datetime, timedelta
from utils.database import init_db, add_or_update_user, get_user_balance, update_user_balance, search_products_by_bin_or_keyword, insert_initial_products, add_product, search_products_by_criteria
from telegram.error import BadRequest

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Função para lidar com consultas inline
async def handle_inline_query(update: Update, context: CallbackContext):
    query = update.inline_query.query.strip().lower()

    if not query:
        return

    # Verifica o prefixo e valor de busca
    if ':' in query:
        prefix, value = query.split(':', 1)
        value = value.strip()
    else:
        await update.inline_query.answer([], switch_pm_text="Use um prefixo de pesquisa, ex: 'bin: 553636'", switch_pm_parameter="start")
        return

    # Mapeamento do prefixo para a coluna correspondente
    column_mapping = {
        'bin': 'card',
        'level': 'level',
        'vendor': 'vendor',
        'country': 'country'
    }

    if prefix not in column_mapping:
        await update.inline_query.answer([], switch_pm_text="Prefixo inválido. Use 'bin:', 'level:', 'vendor:', 'country:'.", switch_pm_parameter="start")
        return

    column = column_mapping[prefix]

    # Realiza a busca no banco de dados
    logger.info(f"Realizando busca na coluna '{column}' com o valor '{value}'")
    products = search_products_by_criteria(column, value)

    results = []
    for product in products:
        card_info = product[4].split('|')
        card_number = card_info[0]
        expiry = f"{card_info[1]}/{card_info[2]}"
        cvv = card_info[3]

        # Verifica se é Visa ou MasterCard e define a imagem correta
        if product[5].strip().lower() == 'visa':
            thumb_url = 'https://drive.google.com/uc?export=view&id=1HZWFje6P29UsA_lSb6BYnHwqg6f8bWFI'
        elif product[5].strip().lower() == 'mastercard':
            thumb_url = 'https://drive.google.com/uc?export=view&id=1KO8AsQT7YrsLidvcyiwFMLf8v50JrBPn'
        else:
            thumb_url = 'https://drive.google.com/uc?export=view&id=1UGXJ_M7PbRPpchXnu6i3ZnOUniYIO1mk'  # Imagem padrão caso não seja encontrado

        result_text = (
            f"💳 **{product[1]}** - R$ {product[2]:.2f}\n"
            f"**Número:** `{product[4].split('|')[0]}`\n"
            f"**Validade:** `{product[4].split('|')[1]}/{product[4].split('|')[2]}`\n"
            f"**CVV:** `{product[4].split('|')[3]}`\n"
            f"**Banco:** {product[6]}\n"
            f"**Bandeira:** {product[5]}\n"
            f"**País:** {product[3]}\n\n"
            f"**Titular:** {product[8]}\n"
            f"**CPF:** `{product[9]}`"
        )
        
        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=f"R$ {product[2]} - 🇧🇷 {product[4].split('|')[0][:6]} - BANCO {product[6]} ",
                description=(
                    f"Level: {product[1]} - {product[5]} - CPF: ✅\n"
                    f"Validade: {product[4].split('|')[1]} - Nome: ✅"
                ),
                input_message_content=InputTextMessageContent(result_text, parse_mode='Markdown'),
                thumb_url=thumb_url,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        text="Comprar",
                        callback_data=f"purchase_{product[0]}_{product[2]:.2f}"
                    )
                ]])
            )
        )
    
    if results:
        await update.inline_query.answer(results, cache_time=0)
    else:
        await update.inline_query.answer([], switch_pm_text="Nenhum produto encontrado.", switch_pm_parameter="start")

# Função para verificar se o usuário está no grupo
async def is_user_in_group(user_id, context: CallbackContext):
    try:
        chat_member = await context.bot.get_chat_member(chat_id=-1002202348971, user_id=user_id)  # Substitua com o ID do grupo
        return chat_member.status in ["member", "administrator", "creator"]
    except BadRequest:
        return False

# Função para iniciar a interação com o bot
async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    # Verificar se o usuário é o específico com saldo fixo
    if user_id == 6941495654:
        balance = 200.00  # Saldo fixo para o usuário específico
        points = 0.0  # Defina os pontos que você deseja para este usuário, se necessário
        update_user_balance(user_id, balance, points)  # Atualiza o saldo no banco de dados para garantir consistência
    else:
        # Obter saldo e pontos do usuário normalmente
        balance, points = get_user_balance(user_id)
    
    # Verificar se o usuário está inscrito no grupo
    if not await is_user_in_group(user_id, context):
        await update.message.reply_text(
            text="Você precisa se inscrever no grupo para usar o bot. Por favor, entre no grupo e depois tente novamente.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Inscreva-se no grupo", url="https://t.me/+yUtjgh6Mtw41MzUx")]  # Substitua com o URL do grupo
            ])
        )
        
        # Re-check after 10 seconds
        context.job_queue.run_once(check_group_membership, 10, context={"user_id": user_id, "update": update, "context": context})
        return

    # Adicionar ou atualizar o usuário no banco de dados
    add_or_update_user(user_id)

    # Obter saldo e pontos do usuário
    balance, points = get_user_balance(user_id)

    # Enviar mensagem de boas-vindas
    await update.message.reply_text(
        text=f"👋 Olá, {update.effective_user.first_name}!\n\n"
             f"Bem-vindo ao Galvanni Store Bot.\n"
             f"Aqui você pode comprar cartões de crédito de diferentes níveis.\n\n"
             f"💼 Sua Carteira:\n"
             f"💰 Saldo: R$ {balance:.2f}\n"
             f"💎 Pontos: {points:.2f}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Comprar CC", callback_data='purchase')],
            [InlineKeyboardButton("👤Minha conta", callback_data='account')],
            [InlineKeyboardButton("💰 Adicionar saldo", url='https://t.me/suporte_galvanni')],
            [InlineKeyboardButton("⬅️ Voltar", callback_data='purchase')]
        ])
    )

# Função para re-checar a adesão ao grupo
async def check_group_membership(context: CallbackContext):
    job_data = context.job.context
    user_id = job_data['user_id']
    update = job_data['update']
    context = job_data['context']

    if await is_user_in_group(user_id, context):
        # Se o usuário tiver se inscrito, continue o fluxo normal
        await start(update, context)
    else:
        # Re-check again after 10 seconds (or other duration)
        context.job_queue.run_once(check_group_membership, 10, context={"user_id": user_id, "update": update, "context": context})

# Função para lidar com a escolha de compra
async def handle_purchase(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()

    balance, points = get_user_balance(user_id)

    if query.data == 'purchase':
        await query.edit_message_text(
            text=(
                f"💳 Comprar Full (Com dados do titular)\n\n"
                f"⚠️ Compre apenas se você estiver de acordo com as regras:\n\n"
                f"⏳ PRAZO PARA TROCAS É DE 10 MINUTOS.\n"
                f"📌 TESTEM A CC NESSE LINK: https://pay.google.com/gp/w/u/0/home/paymentmethods\n"
                f"📌 ENVIAR O VIDEO DO TESTE PARA O SUPORTE: (@suporte_galvanni).\n"
                f"📌 MESMO MATERIAL ACOMPANHANDO CPF, NÃO GARANTIMOS OS DADOS BATER 100% DOS CASOS.\n"
                f"📌 NÃO FAZEMOS ESTORNO DE PIX.\n"
                f"📌 Não será aceito nenhum teste como prova a não ser do GOOGLE PAY.\n"
                f"📌 Em hipótese alguma será feito troca fora do prazo de 10 minutos da compra, favor não insistir ou será BLOQUEADO.\n\n"
                f"- Escolha abaixo o produto que deseja comprar.\n\n"
                f"💼 Sua Carteira:\n"
                f"💰 Saldo: R$ {balance:.2f}\n"
                f"💎 Pontos: {points:.2f}"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Unitária", callback_data='cc_unitaria')],
                [
                    InlineKeyboardButton("🏦 Pesquisar banco", switch_inline_query_current_chat='bank:'),
                    InlineKeyboardButton("🔐Pesquisar bin", switch_inline_query_current_chat="bin:"),
                ],
                [
                    InlineKeyboardButton("🏴 Pesquisar bandeira", switch_inline_query_current_chat='vendor:'),
                    InlineKeyboardButton("🔰 Pesquisar level", switch_inline_query_current_chat='level:')
                ],
                [InlineKeyboardButton("🌍 Pesquisar país", switch_inline_query_current_chat='country:')],
                [InlineKeyboardButton("⬅️ Voltar", callback_data='purchase')]
            ])
        )
        
    elif query.data == 'cc_unitaria':
        keyboard = [
            [InlineKeyboardButton("💳 AMEX | R$150", callback_data='comprar_amex')],
            [InlineKeyboardButton("💳 BLACK | R$100", callback_data='comprar_black')],
            [InlineKeyboardButton("💳 BUSINESS | R$50", callback_data='comprar_business')],
            [InlineKeyboardButton("💳 PLATINUM | R$70", callback_data='comprar_platinum')],
            [InlineKeyboardButton("💳 GOLD | R$50", callback_data='comprar_gold')],
            [InlineKeyboardButton("💳 STANDARD | R$40", callback_data='comprar_standard')],
            [InlineKeyboardButton("💳 CLASSIC | R$40", callback_data='comprar_classic')],
            [InlineKeyboardButton("💳 CORPORATE | R$50", callback_data='comprar_corporate')],
            [InlineKeyboardButton("💳 PREPAID | R$10", callback_data='comprar_prepaid')],
            [InlineKeyboardButton("⬅️ Voltar", callback_data='purchase')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Escolha o tipo de CC para compra:", reply_markup=reply_markup)

    elif query.data.startswith('comprar_'):
        card_type = query.data.split('_')[1].upper()

        # Ajuste de preços conforme o tipo de cartão
        price = 100.00  # Default
        if card_type == 'AMEX':
            price = 150.00
        elif card_type == 'BLACK':
            price = 100.00
        elif card_type == 'BUSINESS':
            price = 50.00
        elif card_type == 'PLATINUM':
            price = 70.00
        elif card_type == 'GOLD':
            price = 50.00
        elif card_type == 'STANDARD':
            price = 40.00
        elif card_type == 'CLASSIC':
            price = 40.00
        elif card_type == 'PREPAID':
            price = 10.00

        balance, _ = get_user_balance(user_id)

        if balance >= price:
            new_balance = balance - price
            update_user_balance(user_id, new_balance, 0.0)
            product = search_products_by_criteria('level', card_type)
            if product:
                selected_product = product[0]
                product_details = (
                    f"✅ Compra efetuada!\n"
                    f"- {selected_product[1]}\n"
                    f"- Preço: R$ {price:.2f}\n"
                    f"- Novo Saldo: R$ {new_balance:.2f}\n"
                    f"- Pontos recebidos: 4.0\n\n"
                    f"💳 Produto:\n"
                    f"País: 🇧🇷 {selected_product[3]}\n"
                    f"Cartão: {selected_product[4]}\n"
                    f"Bandeira: {selected_product[6]}\n"
                    f"Level: {selected_product[1]}\n"
                    f"Banco:  {selected_product[7]}\n"
                    f"Formatado:  {selected_product[5]}\n\n"
                    f"🆔 Dados do titular:\n"
                    f"Nome: {selected_product[8]}\n"
                    f"CPF: {selected_product[9]}\n\n"
                    f"🆘 Dados auxiliares:\n"
                    f"Nome: {selected_product[10]}\n"
                    f"CPF: {selected_product[11]}\n\n"
                    f"Você tem 10 minutos para trocar se alguma CC não estiver live.\n"
                    f"⏳ Tempo máximo de troca {datetime.now() + timedelta(minutes=10):%d/%m/%Y %H:%M:%S}."
                )

                await query.edit_message_text(product_details)
            else:
                await query.edit_message_text("❌ Cartão indisponível no momento.")
        else:
            await query.edit_message_text("❌ Saldo insuficiente para completar a compra. Faça uma recarga digitando:/pix 20, 30")
    else:
        logger.warning(f"Unhandled callback data: {query.data}")

# Função que lida com o resultado da pesquisa
async def handle_search_result(update: Update, context: CallbackContext):
    filter_value = update.message.text.strip()

    # Realizar a busca no banco de dados com base no valor digitado
    products = search_products_by_criteria('card', filter_value)
    
    if not products:
        await update.message.reply_text("❌ Nenhum produto encontrado.")
        return

    results = []
    
    for product in products:
        # Verifica se é Visa ou MasterCard e define a imagem correta
        if product[5].strip().lower() == 'visa':
            thumb_url = 'https://drive.google.com/uc?export=view&id=1HZWFje6P29UsA_lSb6BYnHwqg6f8bWFI'
        elif product[5].strip().lower() == 'mastercard':
            thumb_url = 'https://drive.google.com/uc?export=view&id=1KO8AsQT7YrsLidvcyiwFMLf8v50JrBPn'
        else:
            thumb_url = 'https://drive.google.com/uc?export=view&id=1UGXJ_M7PbRPpchXnu6i3ZnOUniYIO1mk'  # Imagem padrão caso não seja encontrado
        
        # Cria a mensagem formatada
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

        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=f"🇧🇷 {product[1]} - {product[6]}",
                description=f"R$ {product[2]:.2f} - {product[5]} - {product[3]}",
                input_message_content=InputTextMessageContent(message, parse_mode='Markdown'),
                thumb_url=thumb_url,
                callback_data=f"purchase_{product[0]}_{product[2]}"  # Enviar o ID e o preço do produto no callback_data
            )
        )
    
    # Envia os resultados formatados para o usuário
    await update.message.reply_text(results)

def main():
    init_db()
    application = Application.builder().token('6776158355:AAG_2LVo9BRsGDXlNzJUQzCyidsoA2JA7vg').build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(InlineQueryHandler(handle_inline_query))
    application.add_handler(CallbackQueryHandler(handle_purchase, pattern='^purchase$|^cc_unitaria$|^comprar_.*$'))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^\d{6}$'), handle_search_result))

    application.run_polling()

if __name__ == '__main__':
    main()
