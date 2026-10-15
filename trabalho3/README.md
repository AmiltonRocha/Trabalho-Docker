# Trabalho 3 — Testes de Carga no WordPress com Locust e Docker Compose

> Copie e cole cada bloco no terminal, na ordem. Baseado no Trabalho 2 + Locust.

---

## Passo 1 — Entrar na pasta do projeto

```bash
cd "/home/amilton/Documentos/Trabalho AV2 Computação distribuida Docker/trabalho3"
```

---

## Passo 2 — Subir o ambiente (comece com 1 instância para instalar)

```bash
docker compose up -d --scale wordpress=1
```

---

## Passo 3 — Instalar o WordPress no navegador

```
http://localhost
```

Faça a instalação de 5 minutos (igual ao Trabalho 1). Usuário e senha que você escolher.

---

## Passo 4 — Criar os 3 posts de teste automaticamente

```bash
python3 criar_posts.py --host http://localhost --user SEU_USUARIO --password 'SUA_SENHA'
```

Esse comando:
- Gera os conteúdos em `cenarios/` (imagem 1MB, texto 400KB, imagem 300KB)
- Sobe as imagens e cria os 3 posts no WordPress
- Grava as URLs em `locust/posts.json` (o Locust usa essas URLs)

---

## Passo 5 — Subir o Locust (interface web)

```bash
docker compose up -d
```

Abra no navegador:

```
http://localhost:8089
```

Preencha:
- **Number of users**: ex. 10
- **Spawn rate**: ex. 10
- **Host**: `http://nginx` (já vem preenchido)

Escolha a **tag** do cenário em *Edit load test → Load test tags* (cenario1, cenario2 ou cenario3) e clique **Start**.

---

## Passo 6 — Testar pelo terminal (headless) um cenário

```bash
docker compose exec -T locust locust -f /locust/locustfile.py --host=http://nginx --headless -u 10 -r 10 --run-time 30s --tags cenario1 --csv /locust/resultados/manual_cenario1_u10_i1 --only-summary
```

> **Atenção:** use `docker compose exec` (e não `docker compose run`) para os testes.
> O `compose run` re-sincroniza a escala do projeto e **remove** os containers extras
> criados com `--scale wordpress=N`, derrubando o teste de múltiplas instâncias.

---

## Passo 7 — Variar instâncias do WordPress (1, 2 ou 3)

```bash
docker compose up -d --scale wordpress=2
docker compose restart nginx
```

Sempre reinicie o nginx depois de mudar a escala (para re-resolver os IPs).

Verifique o balanceamento:

```bash
for i in 1 2 3; do curl -sI http://localhost/ | grep -i x-upstream; done
```

---

## Passo 8 — Rodar TODA a matriz de testes automático

Matriz: 3 cenários × 3 usuários (10, 100, 1000) × 3 instâncias (1, 2, 3) = **27 execuções**

```bash
chmod +x rodar_testes.sh
./rodar_testes.sh
```

Cada execução gera um CSV em `locust/resultados/` no padrão:
`cenario1_u10_i1_stats.csv`

Para testes mais rápidos (menos combinações e tempo menor):

```bash
USUARIOS="10 50" INSTANCIAS="1 2" RUN_TIME=30s ./rodar_testes.sh
```

---

## Passo 9 — Gerar os gráficos

```bash
pip3 install --user --break-system-packages matplotlib
```

```bash
python3 gerar_graficos.py
```

Os gráficos ficam em `locust/resultados/graficos/`:

- `cenarioN_usuarios_no_eixo_x.png` — eixo X = usuários, 1 linha por instância
- `cenarioN_instancias_no_eixo_x.png` — eixo X = instâncias, 1 linha por usuários

Cada figura traz 3 métricas: tempo médio de resposta (ms), RPS e taxa de erro (%).

---

## Referência — Variáveis do Locust (via `-e` ou `environment:`)

| Variável | Descrição | Padrão |
|---|---|---|
| `ATTACKED_HOST` | URL alvo (obrigatório) | — |
| `LOCUST_FILE` | Script usado nos testes | `locustfile.py` |
| `LOCUST_OPTS` | Opções extras do locust | vazio (web UI) |

---

## Comandos extras — Parar tudo

```bash
docker compose down
```

Apagar também os volumes (banco de dados):

```bash
docker compose down -v
```

---

## Comandos extras — Refazer os posts de teste

Apague os posts antigos no WordPress (ou crie de novo) e rode:

```bash
python3 criar_posts.py --host http://localhost --user SEU_USUARIO --password 'SUA_SENHA'
```

---

## Comandos extras — Limpar resultados antigos

```bash
rm -rf locust/resultados/*
```
