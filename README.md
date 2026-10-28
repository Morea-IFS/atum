# atum

Sistema dos jogos interclasse do IFS (JIIFS): cadastro de eventos, times, jogadores e partidas, placar ao vivo e geração de certificados, crachás e adesivos em PDF.

- Django 5.1 + Channels (websocket para o placar), Python 3.11.5
- MySQL 8 e Redis 7
- Roda em Docker. A cada tag `v*`, o GitHub publica a imagem em `ghcr.io/morea-ifs/atum` e cria uma Release.

## 1. Situação atual

- Última versão publicada: [`v0.1.0`](https://github.com/Morea-IFS/atum/releases) (imagem `ghcr.io/morea-ifs/atum:0.1.0` e `:latest`).
- CI roda a cada push na `develop` e na `main` e em todo pull request.
- O deploy ainda não é automático: quem cuida do servidor puxa a imagem (seção 6) ou liga o deploy automático (seção 7).

## 2. Dependências

Só precisa de **Docker** com o plugin **Compose**. Nada de Python, MySQL ou Redis instalado na máquina: tudo roda em contêiner.

- Linux: https://docs.docker.com/engine/install/ (depois, `sudo usermod -aG docker $USER` e abrir o terminal de novo)
- Windows ou macOS: https://docs.docker.com/desktop/

Confira:

```bash
docker --version          # 24 ou mais novo
docker compose version    # v2 ou mais novo
```

Versões fixadas no projeto: Python 3.11.5 (`Dockerfile`), MySQL 8.4.3 e Redis 7.4.1 (`docker-compose.yml`), bibliotecas Python em `requirements.txt`.

## 3. Primeira vez na máquina

```bash
git clone https://github.com/Morea-IFS/atum.git
cd atum

# Baixa as imagens do MySQL e do Redis, monta a imagem do app e sobe os três contêineres.
# Na primeira vez demora alguns minutos (download + instalação das dependências).
docker compose up --build

# Em outro terminal: cria o usuário administrador
docker compose exec web python manage.py createsuperuser
```

Abra http://localhost:8000 (site) e http://localhost:8000/admin (painel). As migrations são aplicadas sozinhas quando o app sobe (`scripts/start.sh`).

O que o `docker compose up` sobe:

| Contêiner | Imagem | Porta no seu PC |
|---|---|---|
| `web` | montada do `Dockerfile` | 8000 |
| `db` | `mysql:8.4.3` | 3307 (para não colidir com um MySQL local na 3306) |
| `redis` | `redis:7.4.1-alpine` | só interna |

As variáveis de desenvolvimento (senhas `atum`/`atum`, `DEBUG=True` etc.) estão no próprio `docker-compose.yml`. Servem só para a sua máquina. O `.env.exemple` mostra as mesmas variáveis para quem rodar sem Docker.

## 4. Dia a dia

```bash
docker compose up            # sobe (sem --build: usa a imagem já montada)
docker compose up -d         # sobe em segundo plano
docker compose logs -f web   # acompanha o log do app
docker compose down          # para e remove os contêineres (mantém o banco)
docker compose down -v       # para e APAGA o banco e a mídia (volumes)

# Qualquer comando do Django roda dentro do contêiner web:
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py test
docker compose exec web python manage.py shell
```

Quando precisa de `--build` de novo: mudou o `requirements.txt`, o `Dockerfile` ou o `scripts/start.sh`. Mudança só em código Python ou template também exige rebuild, porque o código é copiado para dentro da imagem.

Para acessar o banco de fora (DBeaver, MySQL Workbench): host `127.0.0.1`, porta `3307`, banco `atum`, usuário `atum`, senha `atum`.

## 5. Testes e CI

O `manage.py test` ainda roda 0 testes (`app/tests.py` está vazio). O CI confere o resto.

`.github/workflows/ci.yml` roda em push na `develop` e na `main` e em todo pull request:

| Job | O que confere |
|---|---|
| `test` | instala as dependências, `manage.py check`, `makemigrations --check` (falha se alguém mudou um model sem gerar a migration), `migrate` e `test`, tudo contra um MySQL |
| `docker` | monta a imagem, sobe com MySQL e Redis e exige resposta 200 em `/admin/login/` e `/` |

Para fazer o mesmo localmente antes de abrir o PR:

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py makemigrations --check --dry-run
docker compose exec web python manage.py test
```

Há também o `main-cicd.yml`, pipeline de deploy antigo mantido pela equipe. Ele só reage à `main`.

## 6. Como publicar uma versão (CD)

Fluxo de branches: trabalho em `feature/*` → PR para `develop` → PR para `main` → tag na `main`. Push e merge **nunca** publicam nada; só a tag publica.

```bash
git fetch origin
git tag v0.1.1 origin/main      # marca o commit atual da main
git push origin v0.1.1          # este push dispara o release
```

O `.github/workflows/release.yml` então:

1. roda os mesmos testes do CI no commit da tag;
2. monta a imagem e publica `ghcr.io/morea-ifs/atum:0.1.1` e `ghcr.io/morea-ifs/atum:latest`;
3. cria a Release em https://github.com/Morea-IFS/atum/releases com as notas geradas dos PRs.

Regras:

- Numeração (SemVer): `v0.1.1` correção, `v0.2.0` funcionalidade nova, `v1.0.0` quando a equipe considerar estável.
- Tag com sufixo (`v0.2.0-rc1`) vira **pre-release** e **não** recebe `latest`. Use para testar antes da versão final.
- Uma tag não se reaproveita. Se o release falhar, corrija e crie a próxima (`-rc2`, `v0.1.2`).
- Acompanhe em https://github.com/Morea-IFS/atum/actions (workflow "Release").
- Nenhum secret precisa ser cadastrado: o workflow usa o `GITHUB_TOKEN` automático.

## 7. Rodar a imagem publicada (deploy)

Para quem cuida do servidor (AWS ou outro). O pipeline entrega a imagem; subir é daqui para a frente.

### 7.1 Puxar a imagem

```bash
docker pull ghcr.io/morea-ifs/atum:0.1.0     # ou :latest
```

Se o pacote estiver privado, antes: `docker login ghcr.io` com um token do GitHub de escopo `read:packages`.

### 7.2 O que a imagem precisa para subir

| Variável | Valor em produção |
|---|---|
| `SECRET_KEY` | chave longa e secreta do Django |
| `DEBUG` | `False` |
| `HOST` | domínios aceitos, separados por vírgula (ex.: `atum.ifs.edu.br`) |
| `ENVIRONMENT` | `PROD` |
| `DBTYPE` | `mysql` |
| `DBNAME`, `DBUSER`, `DBPASSWORD`, `DBHOST`, `DBPORT` | dados do MySQL |
| `REDIS_URL` | ex.: `redis://<host>:6379/0` (placar ao vivo) |

Guarde essas variáveis num cofre (AWS Secrets Manager, Parameter Store ou equivalente), nunca no repositório.

Além das variáveis:

- um **MySQL 8** e um **Redis 7** acessíveis pela imagem (RDS + ElastiCache, ou contêineres ao lado);
- a imagem escuta na porta **8000**; coloque atrás de um load balancer com HTTPS que aceite **websocket**;
- health check: `GET /admin/login/` → 200;
- um **volume em `/app/media`** (EFS, por exemplo): as fotos enviadas pelos usuários ficam fora da imagem e somem a cada reinício sem ele;
- na primeira subida, crie o superusuário: `python manage.py createsuperuser` dentro do contêiner.

As migrations rodam sozinhas a cada subida (`scripts/start.sh`).

### 7.3 Exemplo mínimo com Docker puro

```bash
docker run -d --name atum -p 8000:8000 \
  -e SECRET_KEY=... -e DEBUG=False -e HOST=atum.ifs.edu.br -e ENVIRONMENT=PROD \
  -e DBTYPE=mysql -e DBNAME=atum -e DBUSER=... -e DBPASSWORD=... -e DBHOST=... -e DBPORT=3306 \
  -e REDIS_URL=redis://...:6379/0 \
  -v atum-media:/app/media \
  ghcr.io/morea-ifs/atum:0.1.0
```

Para atualizar: troque a versão da imagem e reinicie. Para voltar atrás: aponte para a versão anterior, que continua no GHCR.

### 7.4 Deploy automático na AWS (opcional)

Hoje o `release.yml` termina ao criar a Release. Para a AWS atualizar sozinha a cada tag, acrescente um passo no fim do job `publish`. Exemplo para ECS:

```yaml
      - name: Deploy no ECS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE }}   # IAM role com permissão de ecs:UpdateService
          aws-region: us-east-1
      - run: >
          aws ecs update-service --cluster atum --service atum
          --force-new-deployment
```

O que isso exige do lado da AWS: um cluster e um serviço ECS já apontando para `ghcr.io/morea-ifs/atum:latest` (ou uma task definition atualizada pelo passo), uma IAM role que o GitHub possa assumir (OIDC) e o segredo `AWS_DEPLOY_ROLE` cadastrado em *Settings → Secrets* do repositório. Para EKS ou EC2 a ideia é a mesma: um passo final que manda o serviço puxar a imagem nova.

## 8. Estrutura do projeto

```
atum/
├── app/                     # o aplicativo Django
│   ├── models.py            # eventos, times, jogadores, partidas, pontos...
│   ├── views.py             # páginas públicas e de gerenciamento
│   ├── urls.py              # rotas
│   ├── signals.py           # ao salvar ponto/partida/etc., envia ao placar via websocket
│   ├── consumers.py         # websockets do placar (Channels)
│   ├── generators.py        # PDFs: certificados, crachás, adesivos, cronômetro
│   ├── decorators.py        # controle de acesso (termos, janela de inscrição)
│   ├── migrations/
│   ├── templates/
│   └── tests.py             # vazio por enquanto
├── interclasse/             # configuração do projeto Django (settings, urls, asgi)
├── static/                  # CSS, JS e imagens do site
├── media/defaults/          # imagens padrão (as enviadas pelos usuários ficam no volume)
├── fonts/                   # fontes usadas nos PDFs
├── scripts/start.sh         # migrate + gunicorn (ponto de entrada da imagem)
├── conf/                    # arquivos do deploy antigo (systemd)
├── .github/workflows/
│   ├── ci.yml               # testes e smoke test da imagem
│   ├── release.yml          # tag v* → imagem no GHCR + Release
│   └── main-cicd.yml        # pipeline antigo da equipe
├── Dockerfile
├── docker-compose.yml       # ambiente local: web + MySQL + Redis
├── .env.exemple             # variáveis, para rodar sem Docker
└── requirements.txt
```
