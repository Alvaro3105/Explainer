class ErroDeNegocio(Exception):

    def __init__(self, mensagem, status=400, extra=None, cabecalhos=None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status
        self.extra = extra or {}
        self.cabecalhos = cabecalhos or {}
