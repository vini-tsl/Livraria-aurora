"""
Rota de finalização de compra da Livraria Aurora.

Como usar: copie ESTE bloco para o seu app.py (depois de definir `app`,
`carregar_livros` / a leitura do livros.json e a função que monta os itens do
carrinho). Os nomes marcados com  # <-- ADAPTE  são os que você precisa
trocar pelos equivalentes que já existem no seu app.py.
"""
import re
import uuid
from flask import render_template, request, redirect, url_for, session, flash

ESTADOS = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA",
           "PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"]
FORMAS = {"pix": "Pix", "cartao": "Cartão de crédito", "boleto": "Boleto"}


@app.route("/finalizar-compra", methods=["GET", "POST"])
def finalizar_compra():
    if not session.get("usuario"):
        return redirect(url_for("login"))

    itens, total = montar_itens_carrinho()          # <-- ADAPTE: o mesmo que a rota /carrinho usa
    if not itens:
        flash("Seu carrinho está vazio.", "erro")
        return redirect(url_for("carrinho"))

    if request.method == "GET":
        return render_template("checkout.html", itens=itens, total=total, dados={},
                               estados=ESTADOS, nome_usuario=session["usuario"])

    # ── POST: validar ───────────────────────────────────────────────
    f = {k: request.form.get(k, "").strip() for k in
         ("nome", "cep", "rua", "numero", "complemento", "bairro", "cidade",
          "estado", "pagamento", "parcelas")}
    erros = []
    for campo, rotulo in (("nome", "nome"), ("rua", "rua"), ("numero", "número"),
                          ("bairro", "bairro"), ("cidade", "cidade")):
        if not f[campo]:
            erros.append(f"Informe o campo {rotulo}.")
    if not re.fullmatch(r"\d{5}-?\d{3}", f["cep"]):
        erros.append("CEP inválido.")
    if f["estado"] not in ESTADOS:
        erros.append("Selecione o estado.")
    if f["pagamento"] not in FORMAS:
        erros.append("Escolha uma forma de pagamento.")

    if erros:
        for e in erros:
            flash(e, "erro")
        return render_template("checkout.html", itens=itens, total=total, dados=f,
                               estados=ESTADOS, nome_usuario=session["usuario"])

    # ── Registrar pedido (simulado, sem gateway de pagamento) ───────
    pedido = {
        "numero": uuid.uuid4().hex[:8].upper(),
        "total": total,
        "pagamento_nome": FORMAS[f["pagamento"]],
        "endereco": f,
    }
    # <-- ADAPTE: aqui você pode salvar o pedido em data/pedidos.json, se quiser.
    session["carrinho"] = {}                        # <-- ADAPTE: chave que seu app usa para o carrinho
    return render_template("pedido_confirmado.html", pedido=pedido)
