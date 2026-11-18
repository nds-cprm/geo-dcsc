import logging

from django.http import HttpResponseServerError
from django.template.loader import render_to_string
from geonode.views import err500

from .context_processors import site_pages

logger = logging.getLogger(__name__)

# Página de reserva do erro 500 (sem banco, sem context processors) e, se até ela falhar, um HTML fixo.
FALLBACK_TEMPLATE = "geosdc/500_reserva.html"
LAST_RESORT_HTML = (
    '<!DOCTYPE html><html lang="pt-br"><head><meta charset="utf-8"><title>GeoSDC</title></head>'
    "<body><h1>GeoSDC</h1><p>Ocorreu um problema ao carregar esta página. "
    "Tente novamente em alguns minutos.</p></body></html>"
)


def handler500(request):
    """
    Página de erro 500. Tenta a página completa do GeoNode (geonode.views.err500, com o 500.html do
    projeto), que estende o geonode_base.html e roda os context processors: vários consultam o banco,
    então ela falha justamente quando o erro vem do banco fora do ar. Nesse caso, devolve a página de
    reserva, renderizada sem a requisição (sem context processors) e autocontida.
    """
    try:
        return err500(request)
    except Exception:
        logger.exception("Falha ao renderizar a página de erro 500 completa; usando a página de reserva")
    try:
        # site_pages só lê as settings: endereço da página "Fale conosco" no idioma da requisição
        html = render_to_string(FALLBACK_TEMPLATE, site_pages(request))
    except Exception:
        logger.exception("Falha ao renderizar a página de reserva do erro 500")
        html = LAST_RESORT_HTML
    return HttpResponseServerError(html)
