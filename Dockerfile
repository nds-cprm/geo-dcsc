FROM --platform=amd64 geonode/geonode-base:latest-ubuntu-24.04
RUN mkdir -p /usr/src/project

RUN apt-get update -y && apt-get install curl wget unzip gnupg2 locales -y

RUN sed -i -e 's/# C.UTF-8 UTF-8/C.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

WORKDIR /usr/src/project

COPY src/tasks.py \
    src/entrypoint.sh \
    src/requirements.txt \
    /usr/src/project/

COPY src/wait-for-databases.sh /usr/bin/wait-for-databases
RUN chmod +x /usr/bin/wait-for-databases
RUN chmod +x /usr/src/project/tasks.py \
    && chmod +x /usr/src/project/entrypoint.sh

COPY src/celery.sh /usr/bin/celery-commands
RUN chmod +x /usr/bin/celery-commands

COPY src/celery-cmd /usr/bin/celery-cmd
RUN chmod +x /usr/bin/celery-cmd

RUN python -m pip install -U pip setuptools wheel
RUN yes w | pip install --src /usr/src -r requirements.txt

# Segurança: o GeoNode 5.0.3.post1 fixa Pillow==12.1.1 (~60 CVEs no OSV, incl. heap overflow e RCE
# via Ghostscript). Substitui pelo Pillow 13 após instalar o GeoNode; o pip avisa do conflito com o
# pin, o que é esperado. Revisar/remover quando o GeoNode atualizar o pin.
RUN pip install --no-cache-dir "Pillow==13.0.0"

# Cliente PostgreSQL 17 (pg_dump/psql do backup do GeoNode): o pg_dump precisa ser da mesma
# versão do servidor (PostgreSQL 17 no dev) ou mais novo; também atende servidores mais antigos.
# O pg_wrapper (postgresql-client-common) usa a versão mais nova instalada.
# A imagem base bloqueia o repositório PGDG (/etc/apt/preferences.d/pgdg, Pin-Priority -1)
# exceto o client-15: libera aqui o client-17, a libpq5 (o client-17 exige libpq5 >= 17; a
# libpq.so.5 é compatível com a 16 do Ubuntu, usada pelo psycopg2/GDAL) e a libpq-dev (sem ela
# o apt remove libpq-dev/libgdal-dev em vez de atualizá-las). O autoremove fica sem -y de
# propósito: se algo inesperado for removido, o build falha em vez de apagar bibliotecas.
# Base 24.04 (Python 3.12): a 26.04 (Python 3.14) não instala o GeoNode 5.0.3 (lxml==5.2.1 e
# pylibmc==1.6.3 fixados sem wheel para 3.14).
# Fica após o pip install para não invalidar o cache das dependências.
RUN printf 'Package: postgresql-client-17 libpq5 libpq-dev\nPin: release o=apt.postgresql.org\nPin-Priority: 500\n' \
        > /etc/apt/preferences.d/pgdg-client-17 &&\
    apt-get update -y &&\
    apt-get install -y --no-install-recommends postgresql-client-17 &&\
    apt-get autoremove --purge &&\
    apt-get clean &&\
    rm -rf /var/lib/apt/lists/*

COPY src/ /usr/src/project/

# Pontos de montagem dos volumes compartilhados com grupo 0 e g=u: num volume novo, o primeiro
# container que o monta define, pelo copy-up, dono e permissões a partir deste diretório. O django
# sobe antes do geoserver e também monta o data dir do GeoServer, então precisa prepará-lo.
RUN mkdir -p /mnt/volumes/statics /geoserver_data/data /backup_restore /data &&\
    chgrp -R 0 /mnt/volumes/statics /geoserver_data/data /backup_restore /data &&\
    chmod -R g=u /mnt/volumes/statics /geoserver_data/data /backup_restore /data

# Atalho para o manage.py dentro do container (django/celery): geosdc-cli <comando>
# Instalado no bin do virtualenv (/usr/src/venv/bin, primeiro no PATH da imagem base).
# Fica após o pip install para não invalidar o cache das dependências.
COPY src/geosdc-cli /usr/src/venv/bin/geosdc-cli
RUN chmod +x /usr/src/venv/bin/geosdc-cli
# RUN yes w | pip install -e .

EXPOSE 8000
