import re

from django.conf import settings

GTM_REGEX = re.compile(r"^GTM-[A-Z0-9]{4,10}$")


def google_tag_manager(request):
    """GOOGLE_TAG_MANAGER_ID para o aviso de cookies; vazio quando o valor não tem o formato de um ID do GTM."""
    gtag = str(getattr(settings, "GOOGLE_TAG_MANAGER_ID", "") or "")
    return {"GOOGLE_TAG_MANAGER_ID": gtag if GTM_REGEX.match(gtag) else ""}


def _page_url(language, name):
    """Endereço de <name>_URLS para o idioma ("pt", "en"); sem correspondência, vale o <name>_URL."""
    urls = getattr(settings, f"{name}_URLS", {}) or {}
    return urls.get(language) or getattr(settings, f"{name}_URL", "")


def site_pages(request):
    """
    Endereços das páginas do site no idioma da requisição. Vazio, o link não aparece.
    - COOKIE_POLICY_URL: política de cookies, no aviso de cookies (geosdc/snippets/cookie_consent.html)
      e no rodapé (geonode-mapstore-client/snippets/footer.html);
    - CONTACT_PAGE_URL: página "Fale conosco", no rodapé.
    """
    language = (getattr(request, "LANGUAGE_CODE", "") or "").split("-")[0]
    return {
        "COOKIE_POLICY_URL": _page_url(language, "COOKIE_POLICY"),
        "CONTACT_PAGE_URL": _page_url(language, "CONTACT_PAGE"),
    }
