from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import re
import secrets
import unicodedata

app = Flask(__name__)
app.secret_key = 'DJA0229O8990SDJA92'  # Em produção: use uma chave aleatória forte

# ─── Caminhos dos arquivos de dados ───────────────────────────────────
BASE_DIR      = os.path.dirname(__file__)
USUARIOS_JSON = os.path.join(BASE_DIR, 'data', 'usuarios.json')
LIVROS_JSON   = os.path.join(BASE_DIR, 'data', 'livros.json')


def ler_usuarios():
    """Lê o arquivo usuarios.json e retorna uma lista de usuários."""
    if not os.path.exists(USUARIOS_JSON):
        return []
    with open(USUARIOS_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)

def salvar_usuarios(usuarios):
    """Salva a lista de usuários no arquivo usuarios.json."""
    os.makedirs(os.path.dirname(USUARIOS_JSON), exist_ok=True)
    with open(USUARIOS_JSON, 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=2)

def ler_livros():
    """Lê o arquivo livros.json e retorna a lista de livros."""
    if not os.path.exists(LIVROS_JSON):
        return []
    with open(LIVROS_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)

def buscar_usuario_por_email(email):
    """Retorna o usuário com o e-mail informado, ou None se não existir."""
    usuarios = ler_usuarios()
    for usuario in usuarios:
        if usuario['email'] == email:
            return usuario
    return None

def buscar_livro_por_id(livro_id):
    """Retorna o livro com o id informado, ou None se não existir."""
    for livro in ler_livros():
        if livro['id'] == livro_id:
            return livro
    return None


# ════════════════════════════════════════════════════════════════════════
#  DADOS FIXOS — categorias usadas em todas as páginas
# ════════════════════════════════════════════════════════════════════════

CATEGORIAS = [
    {'nome': 'Literatura',  'slug': 'literatura',  'emoji': 'fas fa-book'},
    {'nome': 'Ciências',    'slug': 'ciencias',    'emoji': 'fas fa-microscope'},
    {'nome': 'História',    'slug': 'historia',    'emoji': 'fas fa-university'},
    {'nome': 'Ficção',      'slug': 'ficcao',      'emoji': 'fas fa-book-open'},
    {'nome': 'Negócios',    'slug': 'negocios',    'emoji': 'fas fa-briefcase'},
    {'nome': 'Infantil',    'slug': 'infantil',    'emoji': 'fas fa-child'},
]

ESTADOS = (
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT',
    'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO',
    'RR', 'SC', 'SP', 'SE', 'TO',
)
FORMAS_PAGAMENTO = {'pix': 'Pix', 'cartao': 'Cartão', 'boleto': 'Boleto'}


def normalizar_texto_busca(texto):
    """Normaliza texto para buscas sem diferenciar maiúsculas ou acentos."""
    texto = unicodedata.normalize('NFD', texto.casefold())
    return ''.join(caractere for caractere in texto
                   if unicodedata.category(caractere) != 'Mn')


# ════════════════════════════════════════════════════════════════════════
#  CARRINHO — funções auxiliares
# ════════════════════════════════════════════════════════════════════════
# O carrinho fica salvo na sessão como um dicionário:
#   session['carrinho'] = {"1": 2, "7": 1}   → chave = id do livro (string), valor = quantidade

def obter_carrinho():
    """Retorna o dicionário do carrinho salvo na sessão (cria um vazio se não existir)."""
    return session.get('carrinho', {})

def salvar_carrinho(carrinho):
    """Salva o dicionário do carrinho de volta na sessão."""
    session['carrinho'] = carrinho
    session.modified = True

def montar_itens_carrinho():
    """Junta os dados do carrinho (id/quantidade) com os dados completos dos livros.
    Retorna a lista de itens e o valor total da compra."""
    carrinho = obter_carrinho()
    itens = []
    total = 0

    for livro_id_str, quantidade in carrinho.items():
        livro = buscar_livro_por_id(int(livro_id_str))
        if not livro:
            continue  # livro pode ter sido removido do catálogo
        subtotal = livro['preco'] * quantidade
        total += subtotal
        itens.append({
            'livro':     livro,
            'quantidade': quantidade,
            'subtotal':  subtotal,
        })

    return itens, total

@app.context_processor
def injetar_carrinho():
    """Deixa a quantidade total de itens do carrinho disponível em TODOS os templates,
    para mostrar o badge no ícone do carrinho na navbar."""
    carrinho = obter_carrinho()
    qtd_carrinho = sum(carrinho.values())
    return {'qtd_carrinho': qtd_carrinho}


# ════════════════════════════════════════════════════════════════════════
#  ROTA — Homepage  /
# ════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    livros = ler_livros()
    # Pega os 4 primeiros livros como destaques
    livros_destaque = livros[:4]
    return render_template('index.html',
                           livros_destaque=livros_destaque,
                           categorias=CATEGORIAS)


# ════════════════════════════════════════════════════════════════════════
#  ROTA — Cadastro  /cadastro
# ════════════════════════════════════════════════════════════════════════

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    # Se já estiver logado, manda direto para a loja
    if session.get('usuario'):
        return redirect(url_for('loja'))

    if request.method == 'POST':
        nome            = request.form.get('nome', '').strip()
        email           = request.form.get('email', '').strip().lower()
        senha           = request.form.get('senha', '')
        confirmar_senha = request.form.get('confirmar_senha', '')

        # ── Validações ──────────────────────────────────────────────
        if not nome or not email or not senha:
            flash('Preencha todos os campos.', 'erro')
            return render_template('cadastro.html')

        if len(senha) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'erro')
            return render_template('cadastro.html')

        if senha != confirmar_senha:
            flash('As senhas não coincidem.', 'erro')
            return render_template('cadastro.html')

        if buscar_usuario_por_email(email):
            flash('Este e-mail já está cadastrado. Tente fazer login.', 'erro')
            return render_template('cadastro.html')

        # ── Salvar novo usuário ──────────────────────────────────────
        novo_usuario = {
            'nome':  nome,
            'email': email,
            'senha': generate_password_hash(senha)  # nunca salva senha pura!
        }

        usuarios = ler_usuarios()
        usuarios.append(novo_usuario)
        salvar_usuarios(usuarios)

        flash(f'Conta criada com sucesso! Bem-vindo, {nome}.', 'sucesso')
        return redirect(url_for('login'))

    return render_template('cadastro.html')


# ════════════════════════════════════════════════════════════════════════
#  ROTA — Login  /login
# ════════════════════════════════════════════════════════════════════════

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Se já estiver logado, manda direto para a loja
    if session.get('usuario'):
        return redirect(url_for('loja'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')

        # ── Validações ──────────────────────────────────────────────
        if not email or not senha:
            flash('Preencha todos os campos.', 'erro')
            return render_template('login.html')

        usuario = buscar_usuario_por_email(email)

        # Verificação em dois passos: usuário existe + senha correta
        if not usuario or not check_password_hash(usuario['senha'], senha):
            flash('E-mail ou senha incorretos.', 'erro')
            return render_template('login.html')

        # ── Login bem-sucedido: salva na sessão ──────────────────────
        session['usuario'] = usuario['nome']
        session['email']   = usuario['email']

        flash(f'Seja bem-vindo, {usuario["nome"]}!', 'sucesso')
        return redirect(url_for('loja'))

    return render_template('login.html')


# ════════════════════════════════════════════════════════════════════════
#  ROTA — Logout  /logout
# ════════════════════════════════════════════════════════════════════════

@app.route('/logout')
def logout():
    nome = session.get('usuario', '')
    session.clear()  # também limpa o carrinho ao sair
    flash(f'Até logo, {nome}!', 'sucesso')
    return redirect(url_for('index'))


# ════════════════════════════════════════════════════════════════════════
#  ROTA — Loja  /loja  (protegida: só acessa se estiver logado)
# ════════════════════════════════════════════════════════════════════════

@app.route('/loja')
def loja():
    if not session.get('usuario'):
        flash('Faça login para acessar a loja.', 'erro')
        return redirect(url_for('login'))

    livros     = ler_livros()
    categoria  = request.args.get('categoria', '')
    busca      = request.args.get('q', '').strip()

    # Filtro por categoria via query string (?categoria=literatura)
    if categoria:
        livros = [l for l in livros if l.get('categoria') == categoria]
    if busca:
        termo = normalizar_texto_busca(busca)
        livros = [
            livro for livro in livros
            if termo in normalizar_texto_busca(livro.get('titulo', ''))
        ]

    return render_template('loja.html',
                           livros=livros,
                           categorias=CATEGORIAS,
                           busca=busca)


# ════════════════════════════════════════════════════════════════════════
#  ROTAS — Carrinho de compras  /carrinho
# ════════════════════════════════════════════════════════════════════════

@app.route('/carrinho')
def carrinho():
    if not session.get('usuario'):
        flash('Faça login para acessar o carrinho.', 'erro')
        return redirect(url_for('login'))

    itens, total = montar_itens_carrinho()
    return render_template('carrinho.html', itens=itens, total=total)


@app.route('/carrinho/adicionar/<int:livro_id>', methods=['POST'])
def adicionar_carrinho(livro_id):
    if not session.get('usuario'):
        flash('Faça login para adicionar livros ao carrinho.', 'erro')
        return redirect(url_for('login'))

    livro = buscar_livro_por_id(livro_id)
    if not livro:
        flash('Livro não encontrado.', 'erro')
        return redirect(url_for('loja'))

    carrinho = obter_carrinho()
    chave = str(livro_id)
    carrinho[chave] = carrinho.get(chave, 0) + 1
    salvar_carrinho(carrinho)

    flash(f'"{livro["titulo"]}" foi adicionado ao carrinho.', 'sucesso')
    return redirect(request.referrer or url_for('loja'))


@app.route('/carrinho/atualizar/<int:livro_id>', methods=['POST'])
def atualizar_carrinho(livro_id):
    if not session.get('usuario'):
        return redirect(url_for('login'))

    try:
        quantidade = int(request.form.get('quantidade', 1))
    except ValueError:
        quantidade = 1

    carrinho = obter_carrinho()
    chave = str(livro_id)

    if quantidade <= 0:
        carrinho.pop(chave, None)
    else:
        carrinho[chave] = quantidade

    salvar_carrinho(carrinho)
    return redirect(url_for('carrinho'))


@app.route('/carrinho/remover/<int:livro_id>', methods=['POST'])
def remover_carrinho(livro_id):
    if not session.get('usuario'):
        return redirect(url_for('login'))

    carrinho = obter_carrinho()
    carrinho.pop(str(livro_id), None)
    salvar_carrinho(carrinho)

    flash('Item removido do carrinho.', 'sucesso')
    return redirect(url_for('carrinho'))


@app.route('/carrinho/finalizar', methods=['GET', 'POST'])
@app.route('/checkout', methods=['GET', 'POST'])
def finalizar_compra():
    if not session.get('usuario'):
        flash('Faça login para finalizar a compra.', 'erro')
        return redirect(url_for('login'))

    itens, total = montar_itens_carrinho()
    if not itens:
        flash('Seu carrinho está vazio.', 'erro')
        return redirect(url_for('carrinho'))

    dados = session.get('checkout_dados', {})
    if request.method == 'GET':
        return render_template(
            'checkout.html',
            itens=itens,
            total=total,
            dados=dados,
            nome_usuario=session.get('usuario', ''),
            estados=ESTADOS,
            erros=[],
        )

    campos = ('nome', 'cep', 'rua', 'numero', 'complemento',
              'bairro', 'cidade', 'estado')
    dados = {campo: request.form.get(campo, '').strip() for campo in campos}
    dados['estado'] = dados['estado'].upper()
    dados['pagamento'] = request.form.get('pagamento', '').strip()

    erros = []
    obrigatorios = {
        'nome': ('Nome completo', 100),
        'rua': ('Rua', 120),
        'numero': ('Número', 20),
        'bairro': ('Bairro', 80),
        'cidade': ('Cidade', 80),
    }
    for campo, (rotulo, limite) in obrigatorios.items():
        if not dados[campo]:
            erros.append(f'Informe {rotulo.lower()}.')
        elif len(dados[campo]) > limite:
            erros.append(f'{rotulo} deve ter no máximo {limite} caracteres.')
    if len(dados['complemento']) > 100:
        erros.append('Complemento deve ter no máximo 100 caracteres.')

    cep = dados['cep'].replace('-', '').replace(' ', '')
    if not re.fullmatch(r'[0-9]{8}', cep):
        erros.append('Informe um CEP válido com 8 dígitos.')
    else:
        dados['cep'] = f'{cep[:5]}-{cep[5:]}'

    if dados['estado'] not in ESTADOS:
        erros.append('Selecione um estado válido.')
    if dados['pagamento'] not in FORMAS_PAGAMENTO:
        erros.append('Selecione uma forma de pagamento válida.')

    if erros:
        return render_template(
            'checkout.html',
            itens=itens,
            total=total,
            dados=dados,
            nome_usuario=session.get('usuario', ''),
            estados=ESTADOS,
            erros=erros,
        ), 400

    session['checkout_dados'] = dados
    return redirect(url_for('confirmar_endereco'))


@app.route('/checkout/confirmacao', methods=['GET'])
def confirmar_endereco():
    if not session.get('usuario'):
        flash('Faça login para finalizar a compra.', 'erro')
        return redirect(url_for('login'))

    dados = session.get('checkout_dados')
    itens, total = montar_itens_carrinho()
    if not dados or not itens:
        flash('Preencha os dados de entrega antes de confirmar o pedido.', 'erro')
        return redirect(url_for('finalizar_compra'))

    return render_template(
        'confirmar_endereco.html',
        dados=dados,
        itens=itens,
        total=total,
        pagamento_nome=FORMAS_PAGAMENTO[dados['pagamento']],
    )


@app.route('/checkout/confirmacao', methods=['POST'])
def confirmar_pedido():
    if not session.get('usuario'):
        flash('Faça login para finalizar a compra.', 'erro')
        return redirect(url_for('login'))

    dados = session.get('checkout_dados')
    itens, total = montar_itens_carrinho()
    if not dados or not itens:
        flash('Não foi possível confirmar o pedido. Confira seu carrinho e endereço.', 'erro')
        return redirect(url_for('carrinho'))

    session['ultimo_pedido'] = {
        'numero': secrets.token_hex(4).upper(),
        'total': total,
        'pagamento_nome': FORMAS_PAGAMENTO[dados['pagamento']],
        'endereco': {campo: dados[campo] for campo in (
            'nome', 'cep', 'rua', 'numero', 'complemento', 'bairro',
            'cidade', 'estado',
        )},
    }
    salvar_carrinho({})
    session.pop('checkout_dados', None)
    return redirect(url_for('pedido_concluido'))


@app.route('/pedido/confirmado')
def pedido_concluido():
    pedido = session.pop('ultimo_pedido', None)
    if not pedido:
        return redirect(url_for('loja'))
    return render_template('pedido_confirmado.html', pedido=pedido)


# ════════════════════════════════════════════════════════════════════════
#  INICIALIZAÇÃO
# ════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    app.run(debug=True)