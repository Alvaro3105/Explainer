class ErroDeNegocio(Exception):
    """Erro previsto de um caso de uso (dado inválido, recurso de outra conta...).

    O Service levanta; o Controller transforma em resposta HTTP com o status indicado.
    """

    def __init__(self, mensagem, status=400, extra=None, cabecalhos=None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status
        self.extra = extra or {}
        self.cabecalhos = cabecalhos or {}
