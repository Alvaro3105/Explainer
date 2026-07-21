import unittest
from uuid import uuid4

from app import create_app


class ExplainerAppTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_root_endpoint(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('mensagem', response.get_json())

    def test_alunos_list_endpoint_supports_cors(self):
        response = self.client.get('/alunos')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_create_aluno_with_birth_date(self):
        email = f"{uuid4()}@teste.com"
        response = self.client.post('/alunos', json={
            'nome': 'Teste Cadastro',
            'email': email,
            'senha': '123456',
            'data_nascimento': '1998-03-15'
        })
        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertEqual(payload['email'], email)
        self.assertEqual(payload['data_nascimento'], '1998-03-15')


if __name__ == '__main__':
    unittest.main()
