import unittest

from app import app


class LivrariaFluxosTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess['usuario'] = 'Leitora'
            sess['carrinho'] = {'1': 1}

    def test_busca_por_titulo_ignora_maiusculas_e_acentos(self):
        resposta = self.client.get('/loja?q=breve%20historia')

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b'Uma Breve Hist', resposta.data)
        self.assertNotIn(b'Dom Casmurro', resposta.data)

    def test_carrinho_exibe_imagem_da_capa(self):
        resposta = self.client.get('/carrinho')

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b'https://covers.openlibrary.org/b/id/647501-M.jpg', resposta.data)
        self.assertIn(b'<img', resposta.data)
        self.assertNotIn('📗'.encode(), resposta.data)

    def test_checkout_get_exibe_formulario_de_endereco(self):
        resposta = self.client.get('/checkout')

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b'action="/checkout"', resposta.data)
        self.assertIn(b'Endere\xc3\xa7o de entrega', resposta.data)

    def test_endereco_invalido_nao_avanca_checkout(self):
        resposta = self.client.post('/checkout', data={
            'nome': '',
            'cep': '123',
            'rua': 'Rua das Flores',
            'numero': '10',
            'bairro': 'Centro',
            'cidade': 'Curitiba',
            'estado': 'XX',
            'pagamento': 'dinheiro',
        })

        self.assertEqual(resposta.status_code, 400)
        self.assertIn(b'Nome completo', resposta.data)
        self.assertIn(b'CEP v', resposta.data)
        self.assertIn(b'estado v', resposta.data)
        self.assertIn(b'forma de pagamento v', resposta.data)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess['carrinho'], {'1': 1})
            self.assertNotIn('checkout_dados', sess)

    def test_endereco_validado_precisa_de_confirmacao_antes_de_finalizar(self):
        dados = {
            'nome': 'Leitora',
            'cep': '80000-000',
            'rua': 'Rua das Flores',
            'numero': '10',
            'complemento': 'Apto 2',
            'bairro': 'Centro',
            'cidade': 'Curitiba',
            'estado': 'PR',
            'pagamento': 'pix',
        }
        resposta = self.client.post('/checkout', data=dados)

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.headers['Location'], '/checkout/confirmacao')
        confirmacao = self.client.get('/checkout/confirmacao')
        self.assertEqual(confirmacao.status_code, 200)
        self.assertIn(b'Rua das Flores, 10', confirmacao.data)
        self.assertIn(b'Confirmar endere', confirmacao.data)

        resposta_final = self.client.post('/checkout/confirmacao')
        self.assertEqual(resposta_final.status_code, 302)
        pedido = self.client.get('/pedido/confirmado')
        self.assertEqual(pedido.status_code, 200)
        self.assertIn(b'CEP 80000-000', pedido.data)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess['carrinho'], {})
            self.assertNotIn('checkout_dados', sess)


if __name__ == '__main__':
    unittest.main()
