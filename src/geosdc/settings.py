# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2017 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

# Django settings for the GeoNode project.
import os
import ast
import glob
import importlib.util

# Load more settings from a file called local_settings.py if it exists
try:
    from geosdc.local_settings import *
#    from geonode.local_settings import *
except ImportError:
    from geonode.settings import *

#
# General Django development settings
#
PROJECT_NAME = "geosdc"

# add trailing slash to site url. geoserver url will be relative to this
if not SITEURL.endswith("/"):
    SITEURL = "{}/".format(SITEURL)

SITENAME = os.getenv("SITENAME", "geosdc")

# Defines the directory that contains the settings file as the LOCAL_ROOT
# It is used for relative settings elsewhere.
LOCAL_ROOT = os.path.abspath(os.path.dirname(__file__))

WSGI_APPLICATION = "{}.wsgi.application".format(PROJECT_NAME)

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "en")

# Contornar bloqueio de idiomas do Mapstore/Geonode
# geonode.settings lines 1551-1565
LANGUAGES = ast.literal_eval(os.environ["LANGUAGES"]) if os.getenv("LANGUAGES") else MAPSTORE_DEFAULT_LANGUAGES

if PROJECT_NAME not in INSTALLED_APPS:
    INSTALLED_APPS += (PROJECT_NAME,)

# Location of url mappings
ROOT_URLCONF = os.getenv("ROOT_URLCONF", "{}.urls".format(PROJECT_NAME))

# Additional directories which hold static files
# - Give priority to local geonode-project ones
STATICFILES_DIRS = [
    os.path.join(LOCAL_ROOT, "static"),
] + STATICFILES_DIRS

# Location of locale files
LOCALE_PATHS = (os.path.join(LOCAL_ROOT, "locale"),) + LOCALE_PATHS

TEMPLATES[0]["DIRS"].insert(0, os.path.join(LOCAL_ROOT, "templates"))
loaders = TEMPLATES[0]["OPTIONS"].get("loaders") or [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]
# loaders.insert(0, 'apptemplates.Loader')
TEMPLATES[0]["OPTIONS"]["loaders"] = loaders
TEMPLATES[0].pop("APP_DIRS", None)


PROJECT_FIXTURES = [
    # List project-related fixture files here, in the order they should be loaded.
]

# Social Accounts
INSTALLED_APPS += (
    'allauth.socialaccount.providers.google',
    # 'allauth.socialaccount.providers.openid_connect',
)

# Cadastro: com ACCOUNT_OPEN_SIGNUP=False (env), nem convites abrem o cadastro (ver geosdc/adapters.py).
# O login social segue o ACCOUNT_OPEN_SOCIALSIGNUP (env), pelo adaptador social do GeoNode.
ACCOUNT_ADAPTER = "geosdc.adapters.AccountAdapter"
INVITATIONS_ADAPTER = ACCOUNT_ADAPTER

# Mescla com a configuração do GeoNode (mantém o geonode_openid_connect, reservado para um futuro
# OIDC como o gov.br: SOCIALACCOUNT_PROVIDERS[SOCIALACCOUNT_OIDC_PROVIDER] = {...}). O Google usa
# o provider nativo do allauth.
SOCIALACCOUNT_PROVIDERS.update({
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
        'FETCH_USERINFO' : True
    },
    # 'openid_connect': {
    #     # "SCOPE": [
    #     #     "openid",
    #     #     "email",
    #     #     "phone",
    #     #     "profile",
    #     #     # "govbr_empresa",
    #     #     # "govbr_confiabilidades"
    #     # ],
    #     "OAUTH_PKCE_ENABLED": True,
    # },
})

# SOCIALACCOUNT_PROFILE_EXTRACTORS = {
#     "govbr": "geosdc.account.profileextractors.GovBRExtractor"
# }

# Flatpages (páginas institucionais em /pages/<url>/) com o editor geonode-flatpages-editor, que
# substitui o admin delas e por isso vem depois de django.contrib.flatpages. As tabelas django_flatpage*
# já existem nos bancos. O sites/SITE_ID vem do GeoNode.
if "django.contrib.flatpages" not in INSTALLED_APPS:
    INSTALLED_APPS += ("django.contrib.flatpages",)
INSTALLED_APPS += ("geonode_flatpages_editor",)

# Limpeza diária (3h) das imagens órfãs das flatpages pelo Celery beat (tarefa do
# geonode-flatpages-editor >= 0.2.0; ver o README do pacote). Só agenda se a tarefa existir: com a
# 0.1.0, o beat mandaria todo dia uma tarefa que o worker não conhece.
if importlib.util.find_spec("geonode_flatpages_editor.tasks"):
    from celery.schedules import crontab

    CELERY_BEAT_SCHEDULE["flatpages-cleanup-images"] = {
        "task": "geonode_flatpages_editor.cleanup_orphan_images",
        "schedule": crontab(hour=3, minute=0),
    }

# Project Fixtures
PROJECT_FIXTURES = glob.glob(os.path.join(LOCAL_ROOT, "fixtures", "*.json"))

# Tesauros do projeto (RDF/SKOS), carregados na inicialização com "thesaurus load --action update"
# (task fixtures do tasks.py); o identificador de cada um vem do nome do arquivo
PROJECT_THESAURI = sorted(glob.glob(os.path.join(LOCAL_ROOT, "thesauri", "*.rdf")))

# Trava do envio da fila de notificações (pinax, task send_queued_notifications do Celery, usada com
# ASYNC_SIGNALS=True): sem isto, o arquivo de trava é criado no diretório atual (/usr/src/project),
# que é somente leitura. /tmp é o tmpfs do container: a trava some num restart, sem ficar presa.
NOTIFICATION_LOCK_LOCATION = "/tmp/send_notices"

# Aviso de cookies (LGPD) e Google Tag Manager (geosdc/snippets/cookie_consent.html): o GTM só é
# carregado depois do aceite. O ID precisa ter o formato GTM-XXXX; vazio, nada é carregado.
GOOGLE_TAG_MANAGER_ID = os.getenv("GOOGLE_TAG_MANAGER_ID", "")
# Política de cookies, por idioma da interface (pt, en): flatpages da fixture geosdc-flatpages-cookies.json;
# definida e vazia na env, o link não aparece no aviso nem no rodapé
COOKIE_POLICY_URL = os.getenv("COOKIE_POLICY_URL", "/pages/politica-de-cookies/")
COOKIE_POLICY_URLS = {
    "pt": COOKIE_POLICY_URL,
    "en": os.getenv("COOKIE_POLICY_URL_EN", "/pages/cookie-policy/"),
}
# Página "Fale conosco" (contato e endereço da Defesa Civil), por idioma da interface: flatpages da
# fixture geosdc-flatpages-fale-conosco.json; definida e vazia na env, o link não aparece no rodapé
CONTACT_PAGE_URL = os.getenv("CONTACT_PAGE_URL", "/pages/fale-conosco/")
CONTACT_PAGE_URLS = {
    "pt": CONTACT_PAGE_URL,
    "en": os.getenv("CONTACT_PAGE_URL_EN", "/pages/contact-us/"),
}
TEMPLATES[0]["OPTIONS"]["context_processors"] += [
    "geosdc.context_processors.google_tag_manager",
    "geosdc.context_processors.site_pages",
]
