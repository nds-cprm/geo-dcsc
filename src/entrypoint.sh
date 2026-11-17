#!/bin/bash

# Exit script in case of error
set -e

# Sem root (qualquer UID do grupo 0, como o UID aleatório do OpenShift): arquivos criados nos volumes
# compartilhados (estáticos, mídia, data dir do GeoServer, backups) nascem com escrita do grupo 0 (g=u),
# para o geoserver e os demais containers continuarem gravando neles.
umask 0002

# Estado do entrypoint (.override_env) em $HOME (/tmp na imagem, exclusivo de cada container). Se o
# runtime redefinir o HOME para um diretório sem escrita, usa /tmp.
if [ ! -w "${HOME:-/nonexistent}" ]; then
    HOME=/tmp
fi
export HOME

INVOKE_LOG_STDOUT=${INVOKE_LOG_STDOUT:-FALSE}
invoke () {
    if [ "$INVOKE_LOG_STDOUT" = 'true' ] || [ "$INVOKE_LOG_STDOUT" = 'True' ]
    then
        /usr/local/bin/invoke $@
    else
        /usr/local/bin/invoke $@ > /var/log/invoke.log 2>&1
    fi
    echo "$@ tasks done"
}

# Removido: "service cron restart" exige root, e o cron da imagem só tem os jobs do e2scrub (sem uso em
# container). Tarefas periódicas ficam no cron do uWSGI (uwsgi.ini) e no Celery beat.

echo $"\n\n\n"
echo "-----------------------------------------------------"
echo "STARTING DJANGO ENTRYPOINT $(date)"
echo "-----------------------------------------------------"

invoke update

if [ -f "$HOME/.bashrc" ]; then
    source "$HOME/.bashrc"
fi
source "$HOME/.override_env"

echo DOCKER_API_VERSION=$DOCKER_API_VERSION
echo POSTGRES_USER=$POSTGRES_USER
# Comentados: imprimem segredos no log (senha e URLs de banco com credenciais embutidas)
# echo POSTGRES_PASSWORD=$POSTGRES_PASSWORD
# echo DATABASE_URL=$DATABASE_URL
# echo GEODATABASE_URL=$GEODATABASE_URL
echo SITEURL=$SITEURL
echo ALLOWED_HOSTS=$ALLOWED_HOSTS
echo GEOSERVER_PUBLIC_LOCATION=$GEOSERVER_PUBLIC_LOCATION

# invoke waitfordbs

cmd="$@"

if [ "${IS_CELERY}" = "true" ]  || [ "${IS_CELERY}" = "True" ]
then
    echo "Executing Celery server $cmd for Production"
else

    invoke migrations
    invoke prepare

    if [ "${FORCE_REINIT}" = "true" ]  || [ "${FORCE_REINIT}" = "True" ] || [ ! -e "/mnt/volumes/statics/geonode_init.lock" ]; then
        invoke fixtures
        invoke initialized
        invoke updateadmin
    fi

    invoke statics

    echo "Executing UWSGI server $cmd for Production"
fi

echo "-----------------------------------------------------"
echo "FINISHED DJANGO ENTRYPOINT --------------------------"
echo "-----------------------------------------------------"

# Run the CMD
echo "got command $cmd"
exec $cmd
