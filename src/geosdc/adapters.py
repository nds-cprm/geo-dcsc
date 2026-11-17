from django.conf import settings

from geonode.people.adapters import LocalAccountAdapter


class AccountAdapter(LocalAccountAdapter):
    """Adaptador de contas do geosdc.

    O adaptador do GeoNode libera o cadastro, mesmo com ACCOUNT_OPEN_SIGNUP=False, para quem
    chega por um convite aceito (e-mail verificado na sessão), e qualquer usuário logado pode
    enviar convites. Aqui o cadastro segue só o ACCOUNT_OPEN_SIGNUP: com o cadastro fechado,
    toda conta é criada por um administrador.
    """

    def is_open_for_signup(self, request):
        return getattr(settings, "ACCOUNT_OPEN_SIGNUP", True)
