# geosdc: GeoNode da Defesa Civil de Santa Catarina

Instância [GeoNode](https://geonode.org/) da **Defesa Civil de Santa Catarina**, derivada do template oficial [geonode-project](https://github.com/GeoNode/geonode-project). O projeto é um app Django (`geosdc`) que estende o GeoNode por *override*: configurações, templates, traduções pt-BR, fixtures e identidade visual do governo de SC. O pacote GeoNode instalado nunca é alterado.

## Sumário

- [Principais características](#principais-características)
- [Arquitetura](#arquitetura)
- [Instalação](#instalação)
- [Operação do dia a dia](#operação-do-dia-a-dia)
- [Backup e restore](#backup-e-restore)
- [Testes](#testes)
- [Desenvolvimento](#desenvolvimento)
- [Execução sem root e com filesystem somente leitura](#execução-sem-root-e-com-filesystem-somente-leitura)

## Principais características

- **GeoNode 5.0.3** (`geonode==5.0.3.post1`) com `django-geonode-mapstore-client` 5.0.3 e GeoServer 2.28. As dependências Python ficam em [src/requirements.txt](src/requirements.txt).
- **Interface em português:** traduções pt-BR do MapStore em [src/geosdc/static/mapstore/](src/geosdc/static/mapstore/). A lista de idiomas vem da variável `LANGUAGES` do `.env`, o que contorna o bloqueio de idiomas do MapStore.
- **Identidade visual do governo de SC:** rodapé, favicon, CSS e tema próprios em [src/geosdc/templates/](src/geosdc/templates/) e [src/geosdc/static/](src/geosdc/static/).
- **Páginas institucionais** com `django.contrib.flatpages`, editadas no admin com o [geonode-flatpages-editor](https://github.com/nds-cprm/geonode-flatpages-editor) (TinyMCE, HTML sanitizado e upload de imagens) e servidas em `/pages/`.
- **Login social com Google** via `django-allauth`. Há um rascunho comentado para OpenID Connect / gov.br em [src/geosdc/settings.py](src/geosdc/settings.py).
- **Fixtures do projeto** (licença e regiões) em [src/geosdc/fixtures/](src/geosdc/fixtures/), carregadas no primeiro boot.
- **Stack completa em containers** (Docker ou Podman), com overrides por ambiente: desenvolvimento, homologação e produção. Em homologação e produção o banco PostgreSQL é externo.
- **Containers sem root e somente leitura** para django, celery e geoserver, compatíveis com UID arbitrário (OpenShift). Veja a [seção final](#execução-sem-root-e-com-filesystem-somente-leitura).
- **Suíte de testes do GeoNode** executável numa stack descartável com o script [geosdc-tests](geosdc-tests).

## Arquitetura

O [docker-compose.yml](docker-compose.yml) define a stack. Todos os serviços leem o `.env`.

| Serviço | Container | Papel |
|---|---|---|
| `django` | `django4geosdc` | GeoNode/geosdc servido por uWSGI (porta 8000) |
| `celery` | `celery4geosdc` | Mesma imagem do django: workers (fila padrão e `harvesting`) e beat |
| `geonode` | `nginx4geosdc` | Nginx: proxy reverso para django e geoserver, estáticos e mídia |
| `geoserver` | `geoserver4geosdc` | Serviços OGC (WMS, WFS, WCS, GWC) |
| `db` | `db4geosdc` | PostGIS com os bancos `geosdc` e `geosdc_data` (só em dev) |
| `redis` | `redis4geosdc` | Broker e backend de resultados do Celery |
| `memcached` | `memcached4geosdc` | Cache |
| `letsencrypt` | `letsencrypt4geosdc` | Certificados TLS |

Os nomes dos containers seguem `<serviço>4${COMPOSE_PROJECT_NAME}`.

A imagem do django é construída pelo [Dockerfile](Dockerfile) da raiz, a partir do `geonode-base`. As imagens de nginx, geoserver, postgis e letsencrypt vêm do submódulo [docker/](docker/) ([nds-cprm/geonode-docker](https://github.com/nds-cprm/geonode-docker), branch `geosdc`). As versões das imagens base ficam no `.env`, nas variáveis `*_BASE_IMAGE_VERSION`, e também servem de tag das imagens geradas.

Overrides por ambiente, usados junto com o compose base:

| Arquivo | Ambiente | Diferenças |
|---|---|---|
| [docker-compose-dev.yml](docker-compose-dev.yml) | desenvolvimento | publica no host as portas 8000 (django), 8080 (geoserver) e 5432 (db) |
| [docker-compose-hml.yml](docker-compose-hml.yml) | homologação | banco externo: desliga o `db` e aponta o hostname `db` para o servidor PostgreSQL (`extra_hosts`) |
| [docker-compose-prod.yml](docker-compose-prod.yml) | produção | idem homologação |

## Instalação

### Requisitos

- Docker com o plugin `docker compose`, ou Podman com `podman compose`.
- Git, para clonar o projeto com o submódulo.
- Python 3, só para gerar o `.env` com o `create-envfile.py`.
- Em homologação e produção: um servidor PostgreSQL/PostGIS acessível pelos containers.

### 1. Clonar o repositório

```bash
git clone --recurse-submodules https://github.com/nds-cprm/geo-dcsc.git geosdc
cd geosdc
```

Se o projeto já foi clonado sem o submódulo, rode `git submodule update --init`.

### 2. Criar o arquivo de ambiente

O `.env` é gerado a partir do [.env.sample](.env.sample). As senhas omitidas são geradas aleatoriamente.

```bash
python create-envfile.py --hostname geo.exemplo.sc.gov.br --https --email admin@exemplo.sc.gov.br --env_type prod
```

Opções úteis (veja `python create-envfile.py --help`):

| Opção | Descrição |
|---|---|
| `--hostname` | nome público do servidor (padrão `localhost`) |
| `--https` | ativa HTTPS; exige `--email`, usado pelo Let's Encrypt |
| `--env_type` | `prod`, `test` ou `dev` (define `DEBUG`) |
| `--geonodepwd`, `--geoserverpwd` | senhas dos administradores do GeoNode e do GeoServer |
| `--pgpwd`, `--dbpwd`, `--geodbpwd` | senhas do PostgreSQL, do banco do GeoNode e do banco de dados geográficos |
| `--clientid`, `--clientsecret` | credenciais OAuth2 entre GeoNode e GeoServer |
| `-f arquivo.json` | lê os parâmetros de um JSON (a linha de comando tem prioridade) |

Depois de gerar, revise o arquivo. Ajuste pelo menos:

- `DOCKER_ENV`: `dev`, `hml` ou `prod`. Ele define qual override o `./geosdc` usa.
- `LANGUAGE_CODE` e `LANGUAGES`, por exemplo `LANGUAGE_CODE=pt-br`.
- Em homologação e produção: `DATABASE_HOST`, `DATABASE_URL` e `GEODATABASE_URL` apontando para o banco externo, e o IP do servidor em `extra_hosts` no `docker-compose-hml.yml` ou no `docker-compose-prod.yml`.
- E-mail (`DJANGO_EMAIL_*`) e chaves de API (`GOOGLE_API_KEY` etc.).

> [!WARNING]
> O `.env` e as variantes `.env.dev`, `.env.hml` e `.env.prod` contêm credenciais. Eles estão no `.gitignore` e não devem ser commitados nem compartilhados.

O `./geosdc` também aceita manter um arquivo por ambiente (`.env.dev`, `.env.hml`, `.env.prod`). Sem `.env` no diretório, ele cria o link `.env -> .env.<amb>` de acordo com o `DOCKER_ENV` do shell. Um `.env` existente nunca é alterado.

### 3. Construir as imagens e subir a stack

O script [geosdc](geosdc) é um atalho para `docker compose -f docker-compose.yml -f docker-compose-<amb>.yml`. Ele escolhe o override pelo `DOCKER_ENV` e usa o Docker quando o daemon responde. Se o daemon não responde, usa o Podman. Para forçar o engine, defina `CONTAINER_ENGINE=docker` ou `CONTAINER_ENGINE=podman`.

```bash
./geosdc build
./geosdc up -d
./geosdc logs -f django
```

O primeiro boot demora alguns minutos. Nele o container django:

1. calcula as URLs e as configurações derivadas do `.env`;
2. aplica as migrações dos bancos `default` e `datastore`;
3. carrega as fixtures, inclusive as do projeto, e cria o administrador;
4. coleta os estáticos e inicia o uWSGI.

O GeoServer popula o próprio data dir no primeiro boot.

Ao final, acesse `https://<hostname>/` (ou `http://localhost/` em dev) e entre com `ADMIN_USERNAME`/`ADMIN_PASSWORD` do `.env`. O GeoServer fica em `/geoserver/`.

As fixtures e o administrador só são carregados enquanto não existir o arquivo `/mnt/volumes/statics/geonode_init.lock`. Para recarregá-los, defina `FORCE_REINIT=true` no `.env` e reinicie o django. Depois, volte a variável para `false`.

### Atualizações

```bash
git pull
git submodule update --init      # atualiza o submódulo para o ponteiro commitado
./geosdc build
./geosdc up -d
```

As migrações rodam automaticamente na subida do django. Mudanças no `requirements.txt` exigem rebuild da imagem.

## Operação do dia a dia

```bash
./geosdc ps                                  # estado dos serviços
./geosdc logs -f django celery               # logs
./geosdc restart django                      # reinicia um serviço
./geosdc stop                                # para a stack, sem remover nada
./geosdc down                                # remove os containers e mantém os volumes

# manage.py dentro do container (o geosdc-cli carrega o ambiente calculado no boot)
./geosdc exec django geosdc-cli showmigrations
./geosdc exec django geosdc-cli shell
./geosdc exec -T django geosdc-cli dumpdata people.Profile --indent 2 > profiles.json   # -T em pipes e redirecionamentos
```

> [!CAUTION]
> `./geosdc down -v` apaga os volumes: banco de dev, data dir do GeoServer, mídia e backups.

## Backup e restore

Os scripts ficam em [src/geosdc/br/](src/geosdc/br/) e usam os comandos `backup` e `restore` do GeoNode. A configuração do que entra no backup está em [settings_docker.ini](src/geosdc/br/settings_docker.ini). Os arquivos são gravados no volume `backup-restore`, montado em `/backup_restore` nos containers django e geoserver.

O backup inclui os dados do GeoNode (fixtures dos apps), a mídia e os assets, o data dir do GeoServer e os dados geográficos do banco `geosdc_data`.

### Gerar um backup

```bash
./geosdc exec django sh /usr/src/project/geosdc/br/backup.sh
```

O script cria em `/backup_restore/` um `.zip` e o `.md5` correspondente, e mostra o checksum no final. Para usar outra pasta, passe o nome dela como argumento. O caminho é relativo à raiz do container, e o padrão é `backup_restore`.

Para copiar o backup para fora do servidor:

```bash
./geosdc exec django ls -lt /backup_restore/
./geosdc cp django:/backup_restore/<arquivo>.zip ./
./geosdc cp django:/backup_restore/<arquivo>.md5 ./
```

### Restaurar um backup

O `restore.sh` restaura o backup **mais recente** em `/backup_restore/` e precisa de duas variáveis:

- `SOURCE_URL`: endereço do servidor que gerou o backup (ex.: `geo.sdc.sc.gov.br`);
- `TARGET_URL`: endereço do servidor que recebe o restore. O script troca as URLs do servidor de origem por este endereço.

```bash
# 1. Coloque o .zip e o .md5 do backup no volume (se vierem de outro servidor)
./geosdc cp ./<arquivo>.zip django:/backup_restore/
./geosdc cp ./<arquivo>.md5 django:/backup_restore/

# 2. Rode o restore
./geosdc exec -e SOURCE_URL=geo.origem.sc.gov.br -e TARGET_URL=geo.destino.sc.gov.br \
    django sh /usr/src/project/geosdc/br/restore.sh
```

O restore executa estas etapas:

1. faz um backup de segurança da instância atual em `/backup_restore/<uuid>/` e confere o checksum;
2. confere o `.md5` do backup a restaurar e executa o `restore` do GeoNode;
3. troca as URLs (`migrate_baseurl`), recria as tile layers do GWC e atualiza os metadados das camadas;
4. corrige as referências de workspace nos estilos do GeoServer e recarrega o catálogo;
5. limpa o memcached.

Se algo der errado, o backup de segurança do passo 1 permite voltar ao estado anterior.

> [!NOTE]
> - o app `resource` entra no backup (`fixtures/resource.json`), porque a fixture `upload` depende dele. O modelo do GeoNode 5.0.3 não o inclui. Backups gerados antes dessa mudança não têm o arquivo, e o restore deles para com `No fixture named 'resource' found`. Para restaurar um desses, crie um `resource.json` contendo só `[]` na pasta `fixtures` do zip e gere o `.md5` de novo;
> - limitação em aberto: depois do backup ou do restore, o GeoWebCache pode ficar sem catálogo de tile layers, e o `create_tile_layers` do passo 3 acusa erro. Nesse caso, reinicie o GeoServer e rode `./geosdc exec django geosdc-cli create_tile_layers -f`.

### Backup do banco em homologação e produção

Em homologação e produção o PostgreSQL é externo, e o backup do banco como um todo (`pg_dump`, snapshots) é responsabilidade da administração desse servidor. O backup do GeoNode descrito acima não substitui esse backup.

## Testes

O projeto não tem testes próprios. O script [geosdc-tests](geosdc-tests) executa a suíte automatizada do **GeoNode** contra as imagens do projeto, dividida em grupos como na CI do GeoNode 5.0.x. Ele sobe uma stack descartável e isolada, chamada `<COMPOSE_PROJECT_NAME>test`, sem nginx e sem portas publicadas. A stack de trabalho não é afetada.

Antes, construa as imagens com `./geosdc build`.

```bash
./geosdc-tests --help                       # ajuda completa
./geosdc-tests --list                       # lista os grupos
./geosdc-tests smoke                        # um grupo
./geosdc-tests main upload                  # vários grupos
./geosdc-tests --lang pt smoke              # com o idioma pt (padrão: en-us)
./geosdc-tests                              # todos os grupos
```

| Grupo | Conteúdo |
|---|---|
| `smoke` | testes rápidos: smoke, REST API, busca, utilitários, cabeçalhos |
| `main` | testes dos apps do GeoNode (exceto security, geoserver e upload) |
| `security` | permissões e segurança |
| `gis_backend` | integração com o GeoServer |
| `rest_apis` | APIs REST (api, base, layers, maps, documents, geoapps) |
| `csw` | catálogo CSW |
| `upload` | importação de dados |

Opções principais:

| Opção | Efeito |
|---|---|
| `--lang CODE` | `LANGUAGE_CODE` dos testes; padrão `en-us` (e não o do `.env`), pois vários testes do GeoNode comparam textos em inglês |
| `-f`, `--failfast` | para cada grupo no primeiro teste com falha |
| `--relaxed` | roda django, celery e geoserver como root e com filesystem gravável, para separar falhas causadas pela execução sem root |
| `-k`, `--keep` | mantém a stack de testes no final, para inspeção |
| `--down` | remove uma stack de testes mantida, com os volumes |

Os logs ficam em `~/.cache/geosdc-tests/logs/<data-hora>/`: um `<grupo>.log` por grupo e o `compose-up.log` da subida. O código de saída é 0 só se todos os grupos passarem. A variável `BOOT_TIMEOUT` (padrão 3600 s) limita a espera pela subida da stack.

### Lint

```bash
flake8 src/      # configuração em .flake8 (max-line-length 200)
```

## Desenvolvimento

- Use `DOCKER_ENV=dev`. O django fica em `http://localhost:8000`, o GeoServer em `http://localhost:8080/geoserver` e o PostGIS em `localhost:5432`.
- **Hot reload:** descomente o bind `./src:/usr/src/project` no `x-common-django` do [docker-compose.yml](docker-compose.yml). O uWSGI recarrega ao tocar em `src/geosdc/wsgi.py`. O `py-autoreload` do [src/uwsgi.ini](src/uwsgi.ini) também funciona, mas não deve ficar ativo em produção.
- **Personalizações** sempre por override em [src/geosdc/](src/geosdc/):
  - `settings.py`: configurações;
  - `templates/`: templates;
  - `static/`: CSS, imagens e traduções;
  - `fixtures/`: um novo `.json` nessa pasta é carregado no primeiro boot ou com `FORCE_REINIT=true`.
- **Atualização do GeoNode:** acompanhe as tags `5.0.x` do [geonode-project](https://github.com/GeoNode/geonode-project) e porte as diferenças manualmente (`git diff <tag_atual> <tag_nova>` no upstream).
- **Submódulo `docker/`:** para trazer as novidades do branch `geosdc`, rode `git submodule update --remote docker` e commite o novo ponteiro.
- Comentários, commits e documentação do projeto são em português.

## Execução sem root e com filesystem somente leitura

Os containers `django`, `celery` e `geoserver` rodam sem root (`user: "1001:0"` no [docker-compose.yml](docker-compose.yml)) e com `read_only: true`. Qualquer UID do grupo 0 funciona, como o UID aleatório do OpenShift. Graváveis ficam só os volumes e os tmpfs.

| Caminho | Tipo | Uso |
|---|---|---|
| `/tmp` | tmpfs, exclusivo de cada container | `HOME` (`.override_env` do entrypoint), fixtures geradas no boot, estado e pid do Celery beat; no GeoServer, também o log da JVM |
| `/tmp/geonode` | volume `tmp`, compartilhado entre django e celery | `TMPDIR` da imagem: temporários do Python, incluindo os dos uploads do Django, em disco para não ocupar memória |
| `/var/log` | tmpfs (django/celery) | logs do uWSGI, Celery e invoke |
| `/usr/local/tomcat/{logs,temp,work}` | tmpfs (geoserver) | diretórios de trabalho do Tomcat |
| `/mnt/volumes/statics`, `/geoserver_data/data`, `/backup_restore`, `/data` | volumes compartilhados | estáticos, mídia e assets, data dir do GeoServer, backups |

Convenções nas imagens:

- **Grupo 0 com `g=u`:** os pontos de montagem são criados no build com grupo 0 e permissão de grupo igual à do dono. Num volume novo, o primeiro container que o monta define dono e permissões a partir desse diretório (copy-up).
- **`umask 0002`:** nos entrypoints, no `geosdc-cli` e no Tomcat (`UMASK=0002`). Assim, os arquivos criados nos volumes compartilhados já nascem com escrita do grupo 0, e os outros containers continuam gravando neles.
- **Código somente leitura:** o `COPY src/` preserva as permissões do host. Por isso o Dockerfile aplica `chmod -R a+rX,go-w` em `/usr/src/project`, para o código ser legível e os scripts executáveis por qualquer UID, sem escrita.
- **`python -m compileall`:** gera no build os `.pyc` do app `geosdc` (o GeoNode e as dependências já vêm compilados pelo `pip install`). Em runtime o `/usr/src/project` é somente leitura, e o Python não consegue gravar o `__pycache__`. Ele não falha por isso, mas recompila o código em memória a cada processo, e o uWSGI e o Celery sobem e reciclam vários workers. O `.dockerignore` exclui os `__pycache__` do host, então a imagem só leva os `.pyc` gerados no build.
- **Sem cron do sistema:** o `service cron` exigia root e só tinha os jobs do `e2scrub`. As tarefas periódicas ficam no cron do uWSGI ([src/uwsgi.ini](src/uwsgi.ini)) e no Celery beat.

Para rodar os testes do GeoNode nesse modo, use o `./geosdc-tests` (veja [Testes](#testes)). A opção `--relaxed` roda como root e com filesystem gravável, para comparar.

Os containers são pensados para subir do zero. Volumes criados antes dessa configuração, com arquivos de root sem escrita do grupo, precisam de um `chgrp -R 0` e de um `chmod -R g=u` uma única vez, ou precisam ser recriados.
