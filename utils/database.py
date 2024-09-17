import psycopg2
import os
import urllib.parse as urlparse
from psycopg2 import sql
import logging

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurando os detalhes da conexão ao banco de dados
DATABASE_CONFIG = {
    'dbname': 'galvanni_store_db',
    'user': 'postgres',
    'password': 'P@ulo123',
    'host': 'localhost',
    'port': '5432'
}

def get_connection():
    """Estabelece uma conexão segura com o banco de dados usando DATABASE_CONFIG."""
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

def execute_query(query, params=None):
    """Executa uma query no banco de dados e retorna os resultados."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                
                 # Diferenciar entre queries que retornam resultados e as que não retornam
                if cursor.description:  # cursor.description é None para queries que não retornam dados
                    results = cursor.fetchall()
                else:
                    results = []
                
                conn.commit()
                return results
    except Exception as e:
        logger.error(f"Erro ao executar query: {e}")
        return []

def init_db():
    """Inicializa as tabelas no banco de dados."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    balance REAL DEFAULT 0.0,
                    points REAL DEFAULT 0.0
                );
                ''')
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    level TEXT NOT NULL,
                    price REAL NOT NULL,
                    country TEXT NOT NULL,
                    card TEXT NOT NULL,
                    vendor TEXT NOT NULL,
                    bank TEXT NOT NULL,
                    formatted TEXT NOT NULL,
                    holder_name TEXT NOT NULL,
                    holder_cpf TEXT NOT NULL,
                    aux_name TEXT NOT NULL,
                    aux_cpf TEXT NOT NULL
                );
                ''')
                conn.commit()
                logger.info("Tabelas inicializadas com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {e}")

def add_or_update_user(user_id, balance=0.0, points=0.0):
    """Adiciona ou atualiza um usuário no banco de dados."""
    query = """
    INSERT INTO users (id, balance, points) 
    VALUES (%s, %s, %s) 
    ON CONFLICT (id) 
    DO UPDATE SET balance = EXCLUDED.balance, points = EXCLUDED.points
    """
    execute_query(query, (user_id, balance, points))

def get_user_balance(user_id):
    """Obtém o saldo e pontos de um usuário."""
    query = "SELECT balance, points FROM users WHERE id=%s"
    results = execute_query(query, (user_id,))
    if results:
        return results[0]
    return 0.0, 0.0

def update_user_balance(user_id, balance, points):
    """Atualiza o saldo de um usuário."""
    query = "UPDATE users SET balance=%s, points=%s WHERE id=%s"
    execute_query(query, (balance, points, user_id))

def add_product(product_data):
    """Adiciona um produto ao banco de dados."""
    query = '''
    INSERT INTO products 
    (level, price, country, card, vendor, bank, formatted, holder_name, holder_cpf, aux_name, aux_cpf) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    '''
    execute_query(query, (
        product_data['level'], product_data['price'], product_data['country'], 
        product_data['card'], product_data['vendor'], product_data['bank'], 
        product_data['formatted'], product_data['holder_name'], 
        product_data['holder_cpf'], product_data['aux_name'], 
        product_data['aux_cpf']
    ))

def search_products(search_value):
    """Busca produtos no banco de dados com base em um valor de pesquisa."""
    logger.info(f"Buscando por: {search_value}")
    query = """
    SELECT * FROM products 
    WHERE card LIKE %s 
    OR level LIKE %s 
    OR vendor LIKE %s 
    OR bank LIKE %s
    """
    params = [f'%{search_value}%', f'%{search_value}%', f'%{search_value}%', f'%{search_value}%']
    results = execute_query(query, params)
    logger.info(f"Resultados encontrados: {len(results)}")
    return results

def search_products_by_bin_or_keyword(value):
    """Busca produtos no banco de dados com base na BIN ou palavra-chave."""
    logger.info(f"Buscando por: {value}")
    query = """
    SELECT * FROM products 
    WHERE card LIKE %s 
    OR level LIKE %s 
    OR vendor LIKE %s 
    OR bank LIKE %s
    """
    params = [f'%{value}%', f'%{value}%', f'%{value}%', f'%{value}%']
    results = execute_query(query, params)
    logger.info(f"Resultados encontrados: {len(results)}")
    return results

def search_products_by_criteria(column, value):
    """Busca produtos no banco de dados com base em um critério específico."""
    logger.info(f"Realizando busca na coluna '{column}' com o valor '{value}'")
    query = sql.SQL("SELECT * FROM products WHERE {} LIKE %s").format(sql.Identifier(column))
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # Convertendo a query composta em uma string SQL válida
                query_str = query.as_string(conn)
                cursor.execute(query_str, [f'%{value}%'])
                results = cursor.fetchall()
                logger.info(f"Número de resultados encontrados: {len(results)}")  # Adicionando log para verificar os resultados
                conn.commit()
                return results
    except Exception as e:
        logger.error(f"Erro ao executar a busca: {e}")
        return []
    

def add_suporte_galvanni_store_user():
    """Adiciona ou atualiza o saldo de um usuário específico."""
    suporte_galvanni_id = 7500387613  # Use o ID real do usuário
    add_or_update_user(suporte_galvanni_id, balance=1000.0)

def insert_initial_products():
    """Insere produtos iniciais no banco de dados, incluindo as novas BINs."""
    products = [
        # Adicionando 5 cartões com BIN 453211
       {
            'level': 'GOLD',
            'price': 50,
            'country': 'BRAZIL',
            'card': '5415550650252044|06|2032|916',
            'vendor': 'MASTERCARD',
            'bank': 'BANCO ITAU',
            'formatted': '541555******2044',
            'holder_name': 'Nilson Braz Videl',
            'holder_cpf': '16042751204',
            'aux_name': 'João Silva',
            'aux_cpf': '12345678900'
        },
        {
            'level': 'PLATINUM',
            'price': 70,
            'country': 'BRAZIL',
            'card': '4705982055831498|01|2032|935',
            'vendor': 'VISA',
            'bank': 'BANCO ITAU',
            'formatted': '470598******1498',
            'holder_name': 'Sergio Egidio Witt',
            'holder_cpf': '17536855087',
            'aux_name': 'Maria Oliveira',
            'aux_cpf': '09876543211'
        },
        {
            'level': 'PLATINUM',
            'price': 70,
            'country': 'BRAZIL',
            'card': '4705981693830730|06|2030|517',
            'vendor': 'VISA',
            'bank': 'BANCO ITAU',
            'formatted': '470598******0730',
            'holder_name': 'Adilson De Lara Lima',
            'holder_cpf': '87692872953',
            'aux_name': 'Carlos Souza',
            'aux_cpf': '32165498700'
        },
        {
            'level': 'CLASSIC',
            'price': 30,
            'country': 'BRAZIL',
            'card': '4901441272764018|02|2031|147',
            'vendor': 'VISA',
            'bank': 'BANCO ITAU',
            'formatted': '490144******4018',
            'holder_name': 'Edson Marcos Colina Firmo',
            'holder_cpf': '58606696668',
            'aux_name': 'Beatriz Santos',
            'aux_cpf': '65432198709'
        },
        {
            'level': 'PLATINUM',
            'price': 70,
            'country': 'BRAZIL',
            'card': '4532117187423190|09|2031|760',
            'vendor': 'VISA',
            'bank': 'BANCO BRADESCO',
            'formatted': '453211******3190',
            'holder_name': 'Moises Ramal De Deus',
            'holder_cpf': '27397815553',
            'aux_name': 'Lucas Almeida',
            'aux_cpf': '11122233344'
        },
        {
            'level': 'PLATINUM',
            'price': 70,
            'country': 'BRAZIL',
            'card': '4532117173690018|07|2028|400',
            'vendor': 'VISA',
            'bank': 'BANCO BRADESCO',
            'formatted': '453211******0018',
            'holder_name': 'Ronaldo Barros',
            'holder_cpf': '33830428715',
            'aux_name': 'Fernanda Silva',
            'aux_cpf': '22233344455'
        },
        {
            'level': 'PLATINUM',
            'price': 70,
            'country': 'BRAZIL',
            'card': '4532117188192331|05|2032|568',
            'vendor': 'VISA',
            'bank': 'BANCO BRADESCO',
            'formatted': '453211******2331',
            'holder_name': 'Roberto Lopes',
            'holder_cpf': '73540927891',
            'aux_name': 'Paula Oliveira',
            'aux_cpf': '33344455566'
        }
    ]
    for product in products:
        add_product(product)

if __name__ == '__main__':
    init_db()
    insert_initial_products()
    add_suporte_galvanni_store_user()
