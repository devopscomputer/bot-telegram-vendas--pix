import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import CallbackContext
from utils.database import get_user_balance, update_user_balance, search_products_by_criteria
from uuid import uuid4
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Função start para iniciar a interação com o bot
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

    # Enviar mensagem de boas-vindas
    await update.message.reply_text(
        text=(
            f"👋 Olá, *{update.effective_user.first_name}*!\n\n"
            f"Bem-vindo ao Galvanni Store Bot.\n"
            f"Aqui você pode comprar cartões de crédito de diferentes níveis.\n\n"
            f"💼 Sua Carteira:\n"
            f"💰 Saldo: R$ {balance:.2f}\n"
            f"💎 Pontos: {points:.2f}"
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Comprar CC", callback_data='purchase')],
            [InlineKeyboardButton("👤Minha conta", callback_data='account')],
            [InlineKeyboardButton("💰 Adicionar saldo", callback_data='add_balance')],
            [InlineKeyboardButton("⬅️ Voltar", callback_data='purchase')]
        ])
    )

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
                    InlineKeyboardButton("🏦 Pesquisar banco", switch_inline_query_current_chat='search_full_bank'),
                    InlineKeyboardButton("🔐Pesquisar bin", switch_inline_query_current_chat="search_full_bin"),
                ],
                [
                    InlineKeyboardButton("🏴 Pesquisar bandeira", switch_inline_query_current_chat='search_full_vendor'),
                    InlineKeyboardButton("🔰 Pesquisar level", switch_inline_query_current_chat='search_full_level')
                ],
                [InlineKeyboardButton("🌍 Pesquisar país", switch_inline_query_current_chat='search_full_country')],
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

    elif query.data.startswith('purchase_'):
        _, product_id, product_price = query.data.split('_')
        product_price = float(product_price)
        
        balance, _ = get_user_balance(user_id)

        if balance >= product_price:
            new_balance = balance - product_price
            update_user_balance(user_id, new_balance, 0.0)
            
            # Buscando o produto pelo ID para entregar após o débito
            product = search_products_by_criteria('id', product_id)
            if product:
                selected_product = product[0]
                current_time = datetime.now()
                formatted_time = current_time.strftime("%d/%m/%Y %H:%M:%S")
                
                # Formatação das partes do cartão e dados do titular
                card_info = selected_product[4].split('|')
                formatted_card_number = f"{card_info[0][:6]}******{card_info[0][-4:]}"
                formatted_cvv = "***"
                formatted_holder_cpf = f"{selected_product[9][:3]}******{selected_product[9][-2:]}"
                formatted_aux_cpf = f"{selected_product[11][:3]}******{selected_product[11][-2:]}"
                formatted_holder_name = f"{selected_product[8].split()[0]} {selected_product[8].split()[-1][:3]}*****"
                formatted_aux_name = f"{selected_product[10].split()[0]} {selected_product[10].split()[-1][:3]}*****"

                product_details = (
                    f"✅ *Compra efetuada!*\n"
                    f"- *{selected_product[1]}*\n"
                    f"- *Preço:* R$ {product_price:.2f}\n"
                    f"- *Novo Saldo:* R$ {new_balance:.2f}\n"
                    f"- *Pontos recebidos:* 8.0\n\n"
                    f"💳 *Produto:*\n"
                    f"*País:* 🇧🇷 {selected_product[3]}\n"
                    f"*Número:* `{formatted_card_number}`\n"
                    f"*Validade:* `{card_info[1]}/{card_info[2]}`\n"
                    f"*CVV:* `{formatted_cvv}`\n"
                    f"*Bandeira:* {selected_product[6]}\n"
                    f"*Banco:* {selected_product[7]}\n\n"
                    f"*Dados do Titular:*\n"
                    f"*Nome:* {formatted_holder_name}\n"
                    f"*CPF:* `{formatted_holder_cpf}`\n\n"
                    f"*Dados Auxiliares:*\n"
                    f"*Nome:* {formatted_aux_name}\n"
                    f"*CPF:* `{formatted_aux_cpf}`\n\n"
                    f"Você tem 10 minutos para trocar se alguma CC não estiver live.\n"
                    f"⏳ *Tempo máximo de troca* {formatted_time}."
                )

                await query.edit_message_text(product_details, parse_mode='Markdown')
            else:
                await query.edit_message_text("❌ Produto não encontrado após a compra.")
        else:
            await query.edit_message_text("❌ Saldo insuficiente para completar a compra. Faça uma recarga digitando: /pix 20, 30")
    elif query.data == 'add_balance':
        await query.edit_message_text(
            text=(
                "💰 Para adicionar saldo, por favor, envie um PIX usando o comando:\n\n"
                "/pix <valor>\n\n"
                "Por exemplo, para adicionar R$20, envie:\n"
                "`/pix 20`"
            ),
            parse_mode='Markdown'
        )
    else:
        logger.warning(f"Unhandled callback data: {query.data}")
