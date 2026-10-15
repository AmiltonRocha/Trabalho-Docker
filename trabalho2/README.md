# Trabalho 2 — WordPress Multi-instância com Nginx e Docker Compose

> Copie e cole cada bloco no terminal, na ordem.

---

## Passo 1 — Entrar na pasta do projeto

```bash
cd "/home/amilton/Documentos/Trabalho AV2 Computação distribuida Docker/trabalho2"
```

---

## Passo 2 — Subir os 5 containers (Nginx + 3 WordPress + MySQL)

```bash
docker compose up -d
```

---

## Passo 3 — Verificar se os 5 containers estão rodando

```bash
docker ps
```

Deve listar: `nginx`, `wordpress1`, `wordpress2`, `wordpress3`, `mysql`.

---

## Passo 4 — Aguardar o WordPress ficar pronto

```bash
sleep 20
```

---

## Passo 5 — Testar o balanceamento de carga (execute várias vezes)

```bash
curl -I http://localhost/
```

Observe o cabeçalho `X-Upstream` alternando entre 3 IPs diferentes (um de cada WordPress).

Teste automático (6 requisições seguidas):

```bash
for i in 1 2 3 4 5 6; do curl -sI http://localhost/ | grep -i x-upstream; done
```

---

## Passo 6 — Confirmar que o WordPress responde

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" -L http://localhost/
```

Deve retornar `HTTP 200`.

---

## Passo 7 — Abrir no navegador

```
http://localhost
```

ou

```
http://127.0.0.1
```

Para ver o X-Upstream no navegador: F12 → aba **Rede** → recarregue a página → clique na requisição → cabeçalhos de resposta.

---

## Passo 8 — Ver os arquivos do WordPress na pasta compartilhada com o host

```bash
ls html
```

---

## Passo 9 (extra) — Adicionar mais workers (instâncias WordPress)

Para adicionar mais um worker, são **2 arquivos** que precisam mudar + 1 comando.

**1.** No `docker-compose.yml`, copie um bloco `wordpress` e mude o nome (ex: `wordpress4`):

```yaml
  wordpress4:
    image: wordpress:5.4.2-php7.2-apache
    container_name: wordpress4
    restart: always
    depends_on:
      - mysql
    environment:
      WORDPRESS_DB_HOST: mysql:3306
      WORDPRESS_DB_USER: usr-wordpress
      WORDPRESS_DB_PASSWORD: pwd-wordpress
      WORDPRESS_DB_NAME: wordpress
    volumes:
      - ./html:/var/www/html
    networks:
      - wpnet
```

**2.** No `nginx.conf`, adicione no `upstream`:

```nginx
    upstream wordpress_cluster {
        server wordpress1:80;
        server wordpress2:80;
        server wordpress3:80;
        server wordpress4:80;   # novo
    }
```

**3.** Subir e recarregar o nginx:

```bash
docker compose up -d
```

```bash
docker compose restart nginx
```

O `docker compose up -d` **não derruba** os containers que já estão rodando — ele só cria o novo. MySQL e os outros workers continuam de pé.

> **Importante:** o `restart nginx` é obrigatório — ele faz o nginx ler o `nginx.conf` atualizado e enxergar o `wordpress4`. Sem isso o novo worker não recebe tráfego.

---

## Passo 10 (extra) — Remover um worker

É o contrário de adicionar:

**1.** Apague o bloco do worker no `docker-compose.yml` (ex: `wordpress4`)

**2.** Apague a linha correspondente no `nginx.conf` (ex: `server wordpress4:80;`)

**3.** Subir e recarregar o nginx:

```bash
docker compose up -d
```

```bash
docker compose restart nginx
```

> **Importante:** sem o `restart nginx`, o nginx continua enviando metade das requisições para o worker removido (erro **502**).

---

## Comandos extras — Parar e remover os containers do Trabalho 2

Parar os 5 containers:

```bash
docker compose down
```

Parar e apagar também os volumes (banco de dados):

```bash
docker compose down -v
```

---

## Comandos extras — Remover containers antigos do Trabalho 1 (se ainda existirem)

```bash
docker rm -f wordpress wordpress-db
```

Verificar todos os containers:

```bash
docker ps -a
```

---

# Evidências — Logs da Execução (prova de que funciona)

> Saídas reais dos comandos executados em 15/10/2026. Copie os comandos e compare com seus resultados.

---

## Evidência 1 — Subida dos containers (`docker compose up -d`)

```
[+] Running 6/6
 ✔ Network trabalho2_wpnet  Created                                        0.0s
 ✔ Container mysql          Started                                        0.2s
 ✔ Container wordpress3     Started                                        0.3s
 ✔ Container wordpress2     Started                                        0.3s
 ✔ Container wordpress1     Started                                        0.3s
 ✔ Container nginx          Started                                        0.3s
```

Comando para reproduzir:

```bash
docker compose up -d
```

---

## Evidência 2 — Os 5 containers rodando (`docker ps`)

**Comando:**

```bash
docker ps
```

**Saída:**

```
NAMES        IMAGE                           STATUS          PORTS
nginx        nginx:1.19.0                    Up 31 minutes   0.0.0.0:80->80/tcp, [::]:80->80/tcp
wordpress2   wordpress:5.4.2-php7.2-apache   Up 31 minutes   80/tcp
wordpress1   wordpress:5.4.2-php7.2-apache   Up 31 minutes   80/tcp
wordpress3   wordpress:5.4.2-php7.2-apache   Up 31 minutes   80/tcp
mysql        mysql:5.7                       Up 31 minutes   3306/tcp, 33060/tcp
```

✓ 5 containers (nginx + 3 wordpress + mysql) com as imagens exigidas no enunciado.

---

## Evidência 3 — Balanceamento de carga (`curl -I`)

**Comando (execute várias vezes):**

```bash
curl -I http://localhost/
```

**Saída — 6 requisições seguidas, o X-Upstream alterna entre os 3 IPs do WordPress:**

```
HTTP/1.1 200 OK
X-Upstream: 172.18.0.4:80     <- wordpress2

HTTP/1.1 200 OK
X-Upstream: 172.18.0.3:80     <- wordpress3

HTTP/1.1 200 OK
X-Upstream: 172.18.0.5:80     <- wordpress1

HTTP/1.1 200 OK
X-Upstream: 172.18.0.4:80     <- wordpress2

HTTP/1.1 200 OK
X-Upstream: 172.18.0.3:80     <- wordpress3

HTTP/1.1 200 OK
X-Upstream: 172.18.0.5:80     <- wordpress1
```

**Mapeamento IP -> container (confirme com este comando):**

```bash
for c in wordpress1 wordpress2 wordpress3; do echo "$c: $(docker inspect $c -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')"; done
```

```
wordpress1: 172.18.0.5
wordpress2: 172.18.0.4
wordpress3: 172.18.0.3
```

> Obs: os IPs podem mudar se os containers forem recriados — use o comando acima para verificar os atuais.

**Teste automático (uma linha):**

```bash
for i in 1 2 3 4 5 6; do curl -sI http://localhost/ | grep -i x-upstream; done
```

✓ O cabeçalho assume os **3 endereços de IP** dos containers WordPress, conforme exige o enunciado.

---

## Evidência 4 — Isolamento de portas (WP e MySQL não expostos)

**Comando:**

```bash
docker ps --format '{{.Names}}: {{.Ports}}'
```

**Saída:**

```
nginx: 0.0.0.0:80->80/tcp, [::]:80->80/tcp
wordpress2: 80/tcp
wordpress1: 80/tcp
wordpress3: 80/tcp
mysql: 3306/tcp, 33060/tcp
```

✓ Apenas o **Nginx** tem porta exposta para a máquina hospedeira (80).
✓ WordPress e MySQL só têm portas **internas** na rede Docker (sem `0.0.0.0`).

---

## Evidência 5 — Site respondendo (HTTP 200)

**Comando:**

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" -L http://localhost/
```

**Saída:**

```
HTTP 200
```

✓ Site acessível em `http://localhost` (e também `http://127.0.0.1`).

---

## Evidência 6 — Busca do WordPress via balanceador

**Comando:**

```bash
curl -sL "http://localhost/?s=balanceador" | grep -oE '<a href="http://localhost/[^"]*">[^<]*</a>'
curl -sI "http://localhost/?s=docker" | grep -i x-upstream
```

**Saída:**

```
<a href="http://localhost/2026/10/15/links-uteis-sobre-docker-e-balanceamento/">Links Uteis sobre Docker e Balanceamento</a>
...
<a href="http://localhost/2026/10/13/ola-mundo/">Olá, mundo!</a>

X-Upstream: 172.18.0.5:80
```

✓ A busca encontra os posts (banco compartilhado pelas 3 instâncias) e a requisição passa pelo Nginx (X-Upstream presente).

---

## Checklist final — Requisitos do enunciado

| Requisito | Evidência | Status |
|---|---|---|
| 5 containers (Nginx + 3 WP + MySQL) | Evidência 2 | ✓ |
| Imagens `nginx:1.19.0`, `wordpress:5.4.2-php7.2-apache`, `mysql:5.7` | Evidência 2 | ✓ |
| Balanceador com `X-Upstream` alternando 3 IPs | Evidência 3 | ✓ |
| WP/MySQL inacessíveis direto do host | Evidência 4 | ✓ |
| Só porta 80 do Nginx exposta | Evidência 4 | ✓ |
| Site respondendo | Evidência 5 | ✓ |
| Compartilhamento de `/var/www/html` + `/usr/share/nginx/html` | Passo 8 do README (`ls html`) | ✓ |
