# utils/helpers.py
# Funções auxiliares que podem ser usadas em vários lugares


# utils.py

from datetime import datetime, timedelta

# Função para formatar datas de forma amigável
def format_datetime(dt):
    return dt.strftime('%d/%m/%Y %H:%M:%S')

# Função para calcular o tempo restante para troca
def calculate_exchange_deadline(minutes=10):
    return format_datetime(datetime.now() + timedelta(minutes=minutes))

# Função para formatar o saldo do usuário com emojis
def format_balance(balance):
    return f"💰 Saldo: R$ {balance:.2f}"

# Função para formatar os pontos do usuário com emojis
def format_points(points):
    return f"💎 Pontos: {points:.2f}"


def format_card_info(product):
    return (
        f"💳 **{product[1]}** - R$ {product[2]:.2f}\n"
        f"**Número:** {product[4].split('|')[0]}\n"
        f"**Validade:** {product[4].split('|')[1]}/{product[4].split('|')[2]}\n"
        f"**CVV:** {product[4].split('|')[3]}\n"
        f"**Banco:** {product[6]}\n"
        f"**Bandeira:** {product[5]}\n"
        f"**País:** {product[3]}\n\n"
        f"**Titular:** {product[8]}\n"
        f"**CPF:** {product[9]}"
    )

