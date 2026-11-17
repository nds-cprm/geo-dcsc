FROM --platform=amd64 geonode/geonode-base:latest-ubuntu-24.04
RUN mkdir -p /usr/src/project

RUN apt-get update -y && apt-get install curl wget unzip gnupg2 locales -y

RUN sed -i -e 's/# C.UTF-8 UTF-8/C.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

WORKDIR /usr/src/project

# Só o requirements.txt antes do pip install: o restante do src/ (tasks.py, entrypoint.sh...) vem no
# COPY src/ abaixo, sem invalidar o cache das dependências a cada mudança nos scripts.
COPY src/requirements.txt /usr/src/project/

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

# --chmod no COPY: permissão definida na própria camada, sem um RUN chmod que duplicaria os arquivos.
COPY --chmod=755 src/wait-for-databases.sh /usr/bin/wait-for-databases
COPY --chmod=755 src/celery.sh /usr/bin/celery-commands
COPY --chmod=755 src/celery-cmd /usr/bin/celery-cmd
# Sem root (qualquer UID do grupo 0, como o UID aleatório do OpenShift): o COPY preserva as permissões
# do host, que podem não dar leitura a "outros" (ex.: entrypoint.sh 700). --chmod=755 deixa código e
# scripts legíveis/executáveis por qualquer UID, sem escrita. O modo numérico vale igual para arquivos
# e diretórios, então todo arquivo ganha o bit de execução (inofensivo: o diretório é somente leitura
# em runtime); o modo simbólico (a+rX,go-w) não é aceito pelo Podman/Buildah. Evita um RUN chmod -R,
# que duplicaria todo o src/ numa camada nova.
COPY --chmod=755 src/ /usr/src/project/

# Bytecode do projeto pré-compilado, porque em runtime o /usr/src/project é somente leitura.
RUN python -m compileall -q /usr/src/project/geosdc

# HOME no /tmp, exclusivo de cada container (tmpfs no compose): .override_env do entrypoint, fixtures
# geradas e estado do celery beat. O que é compartilhado entre containers fica em /tmp/geonode (volume).
# /var/log (logs do uWSGI, Celery e invoke) gravável por qualquer UID do grupo 0; tmpfs no compose.
ENV HOME=/tmp
RUN chgrp 0 /var/log && chmod g=u /var/log

# Pontos de montagem dos volumes compartilhados com grupo 0 e g=u: num volume novo, o primeiro
# container que o monta define, pelo copy-up, dono e permissões a partir deste diretório. O django
# sobe antes do geoserver e também monta o data dir do GeoServer, então precisa prepará-lo.
# /tmp/geonode: TMPDIR (temporários do Python), em disco e não no tmpfs do /tmp.
RUN mkdir -p /mnt/volumes/statics /geoserver_data/data /backup_restore /data /tmp/geonode &&\
    chgrp -R 0 /mnt/volumes/statics /geoserver_data/data /backup_restore /data /tmp/geonode &&\
    chmod -R g=u /mnt/volumes/statics /geoserver_data/data /backup_restore /data /tmp/geonode

# Temporários do Python (tempfile: uploads do Django, arquivos que o GeoNode gera e copia para os
# assets/mídia) em /tmp/geonode, volume em disco compartilhado entre django e celery: não ocupam
# memória e, copiados para os volumes, não levam o rótulo SELinux privado do tmpfs deste container.
ENV TMPDIR=/tmp/geonode

# Atalho para o manage.py dentro do container (django/celery): geosdc-cli <comando>
# Instalado no bin do virtualenv (/usr/src/venv/bin, primeiro no PATH da imagem base).
# Fica após o pip install para não invalidar o cache das dependências.
COPY --chmod=755 src/geosdc-cli /usr/src/venv/bin/geosdc-cli
# RUN yes w | pip install -e .

EXPOSE 8000
