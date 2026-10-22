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
http://localhost:8080
```

Faça a instalação de 5 minutos (igual ao Trabalho 1). Usuário e senha que você escolher.

> O nginx usa a porta **8080** no host (`8080:8080` no `docker-compose.yml`, mesma porta dentro e fora do container) para não
> conflitar com outro servidor web na porta 80 (ex.: Apache do XAMPP).

---

## Passo 4 — Criar os 3 posts de teste automaticamente

```bash
python3 criar_posts.py --host http://localhost:8080 --user SEU_USUARIO --password 'SUA_SENHA'
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
- **Host**: `http://nginx:8080` (já vem preenchido)

Escolha a **tag** do cenário em *Edit load test → Load test tags* (cenario1, cenario2 ou cenario3) e clique **Start**.

---

## Passo 6 — Testar pelo terminal (headless) um cenário

```bash
docker compose exec -T locust locust -f /locust/locustfile.py --host=http://nginx:8080 --headless -u 10 -r 10 --run-time 30s --tags cenario1 --csv /locust/resultados/manual_cenario1_u10_i1 --only-summary
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
for i in 1 2 3; do curl -sI http://localhost:8080/ | grep -i x-upstream; done
```

---

## Passo 8 — Rodar TODA a matriz de testes automático

Matriz: 3 cenários × 4 níveis de carga × 3 instâncias (1, 2, 3) = **36 execuções**

| Nível | Usuários | Significado | Resultado |
|---|---|---|---|
| Leve | 10 | uso normal | 0% erro |
| Pesado | 350 | limite da máquina (7,5GB RAM) | ~0% erro |
| Extremo | 400 | zona de estouro | até ~3% erro no cenário 2 (HTTP 500) |
| Máximo | 500 | estouro total | até ~17% erro no cenário 2 (HTTP 500) |

- Duração: 30s por teste, spawn rate 25/s → ~25 min no total

```bash
chmod +x rodar_testes.sh
./rodar_testes.sh
```

Cada execução gera um CSV em `locust/resultados/` no padrão:
`cenario1_u10_i1_stats.csv`

Para testes mais rápidos (menos combinações e tempo menor):

```bash
USUARIOS="10 350" INSTANCIAS="1 2" RUN_TIME=30s ./rodar_testes.sh
```

---

## Passo 9 — Gerar os gráficos

```bash
pip3 install --user --break-system-packages matplotlib
```

Gráficos normais (por cenário):

```bash
python3 gerar_graficos.py
```

Os gráficos ficam em `locust/resultados/graficos/`:

- `cenarioN_usuarios_no_eixo_x.png` — eixo X = usuários, 1 linha por instância
- `cenarioN_instancias_no_eixo_x.png` — eixo X = instâncias (1, 2, 3), 1 linha por usuários

Cada figura traz 5 métricas: tempo médio de resposta (ms), **mediana (percentil 50%)**, **percentil 95% (P95)**, RPS e taxa de erro (%).

**Gráficos comparativos com legenda (zona segura vs zona de estouro):**

```bash
python3 gerar_graficos_comparacao.py
```

Os gráficos ficam em `locust/resultados/comparacao/`:

- `comparacao_cenarioN.png` — figura única com 5 subplots de **barras agrupadas** (as mesmas 5 métricas, 1 barra por instância) e legenda destacando:
  - **ZONA VERDE** (até 350 usuários): ~0% de erro, sistema estável
  - **ZONA VERMELHA** (400 e 500 usuários): cenário 2 com ~3% de erro em 400 e ~17% em 500 (HTTP 500), sistema saturado

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
python3 criar_posts.py --host http://localhost:8080 --user SEU_USUARIO --password 'SUA_SENHA'
```

---

## Comandos extras — Limpar resultados antigos

```bash
rm -rf locust/resultados/*
```

---

# Evidências — Resultados dos Testes (18/10/2026)

> Matriz completa: 36 execuções (3 cenários × 4 níveis × 3 instâncias), 30s cada.

## Resumo por nível de carga

| Nível | Usuários | Testes | Erro | Tempo médio | RPS máx | Situação |
|---|---|---|---|---|---|---|
| Leve | 10 | 9 | **0%** | 11-55ms | ~10 | Estável |
| Pesado | 350 | 9 | **0,02%*** | 16-720ms | ~272 | No limite |
| Extremo | 400 | 9 | **0,27%**** | 26-846ms | ~295 | Saturado no cenário 2 (HTTP 500) |
| Máximo | 500 | 9 | **1,57%***** | 33-1014ms | ~332 | Estouro no cenário 2 (HTTP 500) |

\* Só o cenario2 com 3 instâncias teve 12 falhas em 2906 requisições (0,41%) — os outros 8 testes de 350 ficaram com 0%.

\*\* Só o cenario2 com 2 e 3 instâncias teve falhas (162 em 59634 requisições no total do nível) — os outros 7 testes de 400 ficaram com 0%.

\*\*\* Só o cenario2 com 2 e 3 instâncias teve falhas (1166 em 74418 requisições no total do nível) — os outros 7 testes de 500 ficaram com 0%.

## Detalhe das falhas

| Teste | Falhas | Total | % |
|---|---|---|---|
| cenario2_u350_i3 | 12 | 2906 | 0,41% |
| cenario2_u400_i2 | 93 | 2963 | 3,14% |
| cenario2_u400_i3 | 69 | 3004 | 2,30% |
| cenario2_u500_i2 | 563 | 3476 | 16,20% |
| cenario2_u500_i3 | 603 | 3482 | 17,32% |

Todos os erros são `HTTP 500` do WordPress — MySQL e PHP saturam acima de ~350 usuários simultâneos.

## Conclusão da máquina (12 CPU / 7,5GB RAM)

- **Até 350 usuários**: sistema aguenta praticamente sem erro (zona segura)
- **400 usuários**: 2-3% de erro no cenário mais pesado (texto 400KB) — **zona de estouro**
- **500 usuários**: 16-17% de erro no cenário 2 com 2 e 3 instâncias — **estouro total**. Com 1 instância não houve erro, mas o tempo médio passou de 1 segundo (1014ms)
- Cenários com imagem (1MB/300KB) aguentaram 500 usuários com 0 erro — o gargalo é o cenário de texto (HTML pesado + PHP renderizando)
- No cenário 2, mais instâncias do WordPress **não** reduziram os erros (com 500 usuários até aumentaram): o gargalo é a máquina única (CPU/RAM e MySQL compartilhados), não o número de containers

## Gráficos gerados

**Normais** (`locust/resultados/graficos/`) — os dois estilos pedidos no enunciado (usuários no eixo X e instâncias no eixo X):

| Arquivo | Conteúdo |
|---|---|
| `cenario1_usuarios_no_eixo_x.png` | Cenário 1 (imagem 1MB), X = usuários (10/350/400/500) |
| `cenario1_instancias_no_eixo_x.png` | Cenário 1, X = instâncias (1/2/3) |
| `cenario2_usuarios_no_eixo_x.png` | Cenário 2 (texto 400KB), X = usuários |
| `cenario2_instancias_no_eixo_x.png` | Cenário 2, X = instâncias |
| `cenario3_usuarios_no_eixo_x.png` | Cenário 3 (imagem 300KB), X = usuários |
| `cenario3_instancias_no_eixo_x.png` | Cenário 3, X = instâncias |

**Comparativos com legenda** (`locust/resultados/comparacao/`):

| Arquivo | Conteúdo |
|---|---|
| `comparacao_cenario1.png` | Zona verde (≤350) vs vermelha (400-500) — imagem 1MB |
| `comparacao_cenario2.png` | Zona verde vs vermelha — texto 400KB (mostra o estouro) |
| `comparacao_cenario3.png` | Zona verde vs vermelha — imagem 300KB |

## Checklist final — Requisitos do enunciado

| Requisito | Evidência | Status |
|---|---|---|
| 3 cenários (imagem 1MB, texto 400KB, imagem 300KB) | `locustfile.py` + `criar_posts.py` | ✓ |
| WordPress multi-instância (1, 2, 3) | `docker-compose.yml` + `--scale` | ✓ |
| Balanceador Nginx | `nginx.conf` com `X-Upstream` | ✓ |
| Testes de carga com Locust | 36 execuções, CSVs em `resultados/` | ✓ |
| Métricas: tempo, mediana, P95, RPS, erro | Gráficos em `graficos/` (X = usuários e X = instâncias) e `comparacao/` | ✓ |
| Script automático de testes | `rodar_testes.sh` | ✓ |
