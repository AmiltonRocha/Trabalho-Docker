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

**3.** Subir:

```bash
docker compose up -d
```

O `docker compose up -d` **não derruba** os containers que já estão rodando — ele só cria o novo. MySQL e os outros workers continuam de pé.

---

## Passo 10 (extra) — Remover um worker

É o contrário de adicionar:

**1.** Apague o bloco do worker no `docker-compose.yml` (ex: `wordpress4`)

**2.** Apague a linha correspondente no `nginx.conf` (ex: `server wordpress4:80;`)

**3.** Subir:

```bash
docker compose up -d
```

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
