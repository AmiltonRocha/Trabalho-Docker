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
- Grava as URLs em `locust/posts.json` (o Locust usa o `post_url` de cada cenário)

Nos cenários 1 e 3 o Locust abre o HTML do post e baixa a imagem do `<img src>` dele, como um
navegador. Se o post vier sem imagem, a requisição é marcada como falha ("post sem <img>").

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

| Nível | Usuários | Significado |
|---|---|---|
| Leve | 10 | uso normal |
| Pesado | 350 | máquina já saturada (RPS para de crescer) |
| Extremo | 400 | acima da saturação |
| Máximo | 500 | carga máxima testada |

- Duração: 30s por teste + 20s de pausa antes de cada um, spawn rate 25/s → ~35 min no total
- A pausa evita que a carga de um teste pesado contamine o teste seguinte

```bash
chmod +x rodar_testes.sh
./rodar_testes.sh
```

Cada execução gera um CSV em `locust/resultados/` no padrão `cenario1_u10_i1_stats.csv`,
e o script grava também `conexoes_mysql.csv` com quantas conexões o MySQL **recusou por excesso**
em cada teste (é a causa dos erros HTTP 500 — ver Evidências).

Segunda matriz, com o MySQL aceitando mais conexões (para comprovar o gargalo):

```bash
MYSQL_MAX_CONNECTIONS=500 SAIDA=resultados_maxconn500 ./rodar_testes.sh
```

| Variável | Padrão | O que faz |
|---|---|---|
| `USUARIOS` | `10 350 400 500` | níveis de usuários |
| `INSTANCIAS` | `1 2 3` | quantidades de instâncias do WordPress |
| `RUN_TIME` | `30s` | duração de cada teste |
| `PAUSA` | `20` | segundos de descanso antes de cada teste |
| `SAIDA` | `resultados` | pasta dentro de `locust/` para os CSVs |
| `MYSQL_MAX_CONNECTIONS` | `151` | limite de conexões do MySQL (padrão do MySQL) |

Para testes mais rápidos (menos combinações e tempo menor):

```bash
USUARIOS="10 350" INSTANCIAS="1 2" RUN_TIME=30s ./rodar_testes.sh
```

> Deixe o notebook **na tomada** e sem suspender durante os testes: na bateria o
> processador fica mais lento e os tempos de resposta deixam de ser comparáveis.

---

## Passo 9 — Gerar os gráficos

```bash
pip3 install --user --break-system-packages matplotlib
```

Gráficos normais (por cenário):

```bash
python3 gerar_graficos.py
python3 gerar_graficos.py --pasta locust/resultados_maxconn500
```

Os gráficos ficam em `<pasta>/graficos/` (ex.: `locust/resultados/graficos/`):

- `cenarioN_usuarios_no_eixo_x.png` — eixo X = usuários, 1 linha por instância
- `cenarioN_instancias_no_eixo_x.png` — eixo X = instâncias (1, 2, 3), 1 linha por usuários

Cada figura traz 5 métricas: tempo médio de resposta (ms), **mediana (percentil 50%)**, **percentil 95% (P95)**, RPS e taxa de erro (%).

**Gráficos comparativos com legenda (zona segura vs zona de estouro):**

```bash
python3 gerar_graficos_comparacao.py --legenda "MySQL max_connections=151 (padrao)"
python3 gerar_graficos_comparacao.py --pasta locust/resultados_maxconn500 --legenda "MySQL max_connections=500"
```

Os gráficos ficam em `<pasta>/comparacao/`:

- `comparacao_cenarioN.png` — figura única com 5 subplots de **barras agrupadas** (as mesmas 5 métricas, 1 barra por instância) e legenda destacando:
  - **ZONA VERDE** (até 350 usuários) e **ZONA VERMELHA** (acima de 350), com o erro máximo real de cada zona calculado dos CSVs
  - barras **hachuradas** = execuções com falhas (o tempo delas inclui as respostas de erro, que voltam rápido)
  - o subtítulo mostra as CPUs/RAM do Docker (lidas do `docker info`) e o texto de `--legenda`

Nos gráficos dos cenários 1 e 3, tempo e RPS aparecem como **"(post + imagem)"**: cada visita faz
2 requisições (HTML + imagem), então esses valores não são comparáveis diretamente com o cenário 2.

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

# Evidências — Resultados dos Testes (22/10/2026)

> Duas matrizes completas de 36 execuções (3 cenários × 4 níveis × 3 instâncias), 30s cada, com 20s de pausa entre testes:
> - **Matriz A** — MySQL com o limite padrão de **151 conexões** → `locust/resultados/`
> - **Matriz B** — MySQL com **500 conexões** → `locust/resultados_maxconn500/`

## Ambiente

| Item | Valor |
|---|---|
| Máquina | Intel Core Ultra 9 185H (16 núcleos / 22 threads), 31,5 GB RAM, Windows 11 |
| Docker | Docker Desktop (WSL2): 22 CPUs / 15,4 GB RAM para os containers |
| Onde rodou | Locust, nginx, WordPress e MySQL **na mesma máquina** |
| Energia | Na tomada, sem suspensão durante os testes (conferido no log de energia do Windows) |
| Imagens | WordPress 5.4.2 (PHP 7.2/Apache), MySQL 5.7, nginx 1.19, Locust 1.2.3 |

## Resumo por nível de carga

| Usuários | Erro (A: 151 conexões) | Erro (B: 500 conexões) | Tempo médio (A) | Tempo médio (B) | RPS máx (A / B) |
|---|---|---|---|---|---|
| 10 | **0%** | **0%** | 87-606 ms* | 101-353 ms* | 10 / 10 |
| 350 | **0%** | **0%** | 134-538 ms | 230-517 ms | 243 / 226 |
| 400 | **0,05%** (28 falhas) | **0%** | 250-796 ms | 252-757 ms | 240 / 241 |
| 500 | **0,78%** (386 falhas) | **0%** | 354-1120 ms | 336-1078 ms | 249 / 253 |

\* Com 10 usuários há poucas requisições (~130-280 por teste), então o tempo varia muito entre execuções;
os valores mais altos aparecem logo depois de mudar a quantidade de instâncias (containers recém-iniciados, cache frio).

## Por que dá HTTP 500: o limite de conexões do MySQL

Na **Matriz A**, só 4 dos 36 testes tiveram falhas — e em todos o MySQL recusou conexões por excesso no mesmo teste:

| Teste | Falhas | Total | % | Conexões recusadas pelo MySQL | Pico de conexões |
|---|---|---|---|---|---|
| cenario2_u400_i3 | 28 | 2982 | 0,94% | 28 | 152 (limite) |
| cenario2_u500_i2 | 84 | 3341 | 2,51% | 96 | 152 (limite) |
| cenario2_u500_i3 | 37 | 3244 | 1,14% | 54 | 152 (limite) |
| cenario3_u500_i3 | 265 | 6454 | 4,11% | 265 | 152 (limite) |

Nos outros 32 testes: **0 conexões recusadas e 0 falhas** (dados em `locust/resultados/conexoes_mysql.csv`).

O motivo: cada instância do WordPress (Apache) atende até **150 requisições ao mesmo tempo**, cada uma com sua
conexão ao MySQL. O MySQL aceita **151** por padrão.

- **1 instância** → no máximo ~150 conexões → **nunca estoura** (0 falha em todos os 12 testes com 1 instância)
- **2-3 instâncias** → até 300-450 conexões disputando 151 vagas → as que sobram viram `HTTP 500`

Na **Matriz B** (500 conexões), com as mesmas cargas: **0 falhas e 0 conexões recusadas nos 36 testes**.
O pico chegou a **216 conexões** — acima do limite padrão, o que confirma que a Matriz A estouraria nesses testes.

## Mais instâncias não aumentaram a vazão

RPS médio nos níveis 350-500 (Matriz B, sem erros):

| Cenário | 1 instância | 2 instâncias | 3 instâncias |
|---|---|---|---|
| 1 (imagem 1MB, post + imagem) | 229 | 221 | 220 |
| 2 (texto 400KB) | 108 | 104 | 112 |
| 3 (imagem 300KB, post + imagem) | 239 | 236 | 230 |

A vazão fica praticamente igual com 1, 2 ou 3 instâncias, e quase não cresce de 350 para 500 usuários
(enquanto o tempo de resposta sobe). Ou seja, **com 350 usuários a máquina já está saturada**: como Locust,
nginx, WordPress e MySQL dividem as mesmas CPUs, mais containers do WordPress só dividem o mesmo processador.
Para o ganho do balanceamento aparecer, as instâncias precisariam estar em máquinas diferentes.

Referência: cada usuário espera de 1 a 3s entre visitas (média 2s). Com 350 usuários o ideal seria ~175 visitas/s
(~350 req/s nos cenários 1 e 3, que fazem 2 requisições por visita); o medido (~220-240 req/s e ~110 req/s no cenário 2)
fica bem abaixo disso — sinal de saturação.

## Conclusões

- **Até 350 usuários**: 0% de erro em todos os cenários e quantidades de instâncias.
- **400-500 usuários com 2-3 instâncias**: aparecem erros `HTTP 500` porque o total de conexões das instâncias passa do
  limite do MySQL (151). Com 1 instância não há erro em nenhum teste (no cenário 2 com 500 usuários o tempo médio
  chega a 0,9-1,1s).
- **Aumentar o `max_connections` do MySQL para 500 eliminou 100% dos erros** sem mudar a vazão: o banco compartilhado
  era o gargalo de erros, e a CPU da máquina única era o gargalo de desempenho.
- **Escalar só a camada web desloca o gargalo para o banco de dados.** Em produção, junto com mais instâncias do
  WordPress seria preciso ajustar o banco (limite de conexões, pool de conexões ou réplicas) e usar mais de uma máquina.
- O **cenário 2 (texto 400KB)** é o mais pesado para o servidor: ~110 req/s contra ~230 nos cenários com imagem,
  porque o PHP monta uma página de ~460KB a cada requisição, enquanto a imagem é um arquivo estático.

## Limitações

- Locust e servidor na mesma máquina: o próprio gerador de carga consome CPU que falta ao WordPress.
- O projeto fica numa pasta do OneDrive, montada no Docker Desktop (WSL2); o acesso a esses arquivos é mais lento
  que num Linux nativo, então os tempos absolutos são maiores que os de um servidor real.
- Nos testes com falhas, o tempo e o RPS incluem as respostas de erro (que voltam rápido); os gráficos marcam esses pontos.

## Gráficos gerados

Para cada matriz (`locust/resultados/` e `locust/resultados_maxconn500/`):

**Normais** (`graficos/`) — os dois estilos pedidos no enunciado:

| Arquivo | Conteúdo |
|---|---|
| `cenarioN_usuarios_no_eixo_x.png` | X = usuários (10/350/400/500), 1 linha por quantidade de instâncias |
| `cenarioN_instancias_no_eixo_x.png` | X = instâncias (1/2/3), 1 linha por quantidade de usuários |

**Comparativos com legenda** (`comparacao/`):

| Arquivo | Conteúdo |
|---|---|
| `comparacao_cenario1.png` | Zona verde (≤350) vs vermelha (400-500) — imagem 1MB |
| `comparacao_cenario2.png` | Zona verde vs vermelha — texto 400KB |
| `comparacao_cenario3.png` | Zona verde vs vermelha — imagem 300KB |

Comparar `locust/resultados/comparacao/` com `locust/resultados_maxconn500/comparacao/` mostra as barras
hachuradas (com falha) da Matriz A sumindo na Matriz B.

## Checklist final — Requisitos do enunciado

| Requisito | Evidência | Status |
|---|---|---|
| Locust no docker-compose do Trabalho 2 | `docker-compose.yml` (serviço `locust`, `ATTACKED_HOST=http://nginx:8080`) | ✓ |
| 3 cenários (imagem 1MB, texto 400KB, imagem 300KB) | `locustfile.py` + `criar_posts.py` | ✓ |
| WordPress multi-instância (1, 2, 3) | `docker-compose.yml` + `--scale` | ✓ |
| Balanceador Nginx | `nginx.conf` com `X-Upstream` | ✓ |
| ≥3 níveis de usuários e ≥3 de instâncias | 4 níveis (10/350/400/500) × 3 instâncias, 2 matrizes de 36 execuções | ✓ |
| Métricas: tempo, mediana, P95, RPS, erro | Gráficos em `graficos/` (X = usuários e X = instâncias) e `comparacao/` | ✓ |
| Script automático de testes | `rodar_testes.sh` | ✓ |
