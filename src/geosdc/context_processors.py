import re

from django.conf import settings

GTM_REGEX = re.compile(r"^GTM-[A-Z0-9]{4,10}$")


def google_tag_manager(request):
    """GOOGLE_TAG_MANAGER_ID para o aviso de cookies; vazio quando o valor não tem o formato de um ID do GTM."""
    gtag = str(getattr(settings, "GOOGLE_TAG_MANAGER_ID", "") or "")
    return {"GOOGLE_TAG_MANAGER_ID": gtag if GTM_REGEX.match(gtag) else ""}


def site_pages(request):
    """
    Endereço da política de cookies no idioma da requisição, usado no aviso de cookies
    (geosdc/snippets/cookie_consent.html) e no rodapé (geonode-mapstore-client/snippets/footer.html).
    COOKIE_POLICY_URLS mapeia o idioma ("pt", "en") para o endereço; sem correspondência, vale o
    COOKIE_POLICY_URL. Vazio, o link não aparece.
    """
    language = (getattr(request, "LANGUAGE_CODE", "") or "").split("-")[0]
    urls = getattr(settings, "COOKIE_POLICY_URLS", {}) or {}
    return {"COOKIE_POLICY_URL": urls.get(language) or getattr(settings, "COOKIE_POLICY_URL", "")}
