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
