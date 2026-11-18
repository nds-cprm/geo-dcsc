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

# Do not remove handler500 import. It is required to re-export
# the custom error page handler for the GeoNode project
# related issue: https://github.com/GeoNode/geonode-project/issues/570
from geonode.urls import urlpatterns, handler500, sitemaps  # noqa
from django.conf import settings
from django.contrib import admin
from django.contrib.flatpages.sitemaps import FlatPageSitemap
from django.urls import include, path

# Login do admin com reCAPTCHA (mesma flag do login e do cadastro do GeoNode)
if settings.RECAPTCHA_ENABLED:
    from geosdc.forms import AdminReCaptchaAuthenticationForm

    admin.site.login_form = AdminReCaptchaAuthenticationForm
    admin.site.login_template = "admin/login_recaptcha.html"

"""
# You can register your own urlpatterns here
urlpatterns = [
    url(r'^/?$',
        homepage,
        name='home'),
 ] + urlpatterns
"""

# Flatpages (editor no admin, pelo geonode-flatpages-editor), fora do prefixo de idioma: cada idioma
# é uma página separada (ex.: /pages/politica-de-cookies/ e /pages/cookie-policy/)
sitemaps.update(page=FlatPageSitemap)
urlpatterns += [
    path("pages/", include("django.contrib.flatpages.urls")),
]
