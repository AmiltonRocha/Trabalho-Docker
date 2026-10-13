# Instalação e Configuração do WordPress com Docker — Comandos

> Copie e cole cada bloco no terminal, na ordem.

---

## Passo 1 — Verificar se o Docker está instalado e rodando

```bash
docker --version
```

```bash
systemctl is-active docker
```

---

## Passo 2 — Testar o Docker com a imagem de exemplo

```bash
docker run --rm hello-world
```

---

## Passo 3 — Baixar a imagem do MySQL 5.7

```bash
docker pull mysql:5.7
```

---

## Passo 4 — Listar as imagens baixadas

```bash
docker images
```

---

## Passo 5 — Criar e iniciar o container do MySQL

```bash
docker run -d \
  -p 3306:3306 \
  --name wordpress-db \
  -e MYSQL_ROOT_PASSWORD=r00t \
  -e MYSQL_DATABASE=wordpress \
  -e MYSQL_USER=usr-wordpress \
  -e MYSQL_PASSWORD=pwd-wordpress \
  mysql:5.7
```

---

## Passo 6 — Verificar se o container do MySQL está rodando

```bash
docker ps
```

---

## Passo 7 — Aguardar o MySQL ficar pronto e testar o acesso ao banco

```bash
docker logs wordpress-db | grep "ready for connections"
```

```bash
docker exec wordpress-db mysql -uusr-wordpress -ppwd-wordpress -e "SHOW DATABASES;"
```

---

## Passo 8 — Criar e iniciar o container do WordPress

```bash
docker run -d \
  -p 8080:80 \
  --name wordpress \
  --link wordpress-db:mysql \
  -e WORDPRESS_DB_HOST=wordpress-db:3306 \
  -e WORDPRESS_DB_USER=usr-wordpress \
  -e WORDPRESS_DB_PASSWORD=pwd-wordpress \
  -e WORDPRESS_DB_NAME=wordpress \
  wordpress
```

---

## Passo 9 — Verificar se os dois containers estão rodando

```bash
docker ps
```

---

## Passo 10 — Testar se o WordPress responde na porta 8080

```bash
curl -I http://localhost:8080
```

---

## Passo 11 — Abrir a instalação do WordPress no navegador

```
http://localhost:8080
```

ou

```
http://127.0.0.1:8080
```

---

## Passo 12 (extra) — Adicionar um terceiro container: phpMyAdmin

```bash
docker run -d -p 8081:80 --name phpmyadmin --link wordpress-db:mysql -e PMA_HOST=wordpress-db -e PMA_PORT=3306 phpmyadmin/phpmyadmin
```

```bash
docker ps
```

Acesse no navegador: `http://localhost:8081` (servidor: `mysql`, usuário: `usr-wordpress`, senha: `pwd-wordpress`)

---

## Passo 13 (extra) — Entender o comando `docker run` (para criar mais containers)

Para adicionar mais containers, é só repetir o `docker run` com um nome diferente:

```bash
docker run -d --name NOME -p PORTA_MAQUINA:PORTA_DO_CONTAINER --link OUTRO_CONTAINER:alias IMAGEM
```

O que cada parte faz:

| Parte | O que faz |
|---|---|
| `docker run` | Cria **e** inicia o container |
| `-d` | Roda em segundo plano (background) |
| `--name` | Nome do container (o que você inventa, precisa ser único) |
| `-p 8080:80` | Porta da **máquina**:porta do **container** (a da direita é fixa, é a porta que o programa usa lá dentro) |
| `--link` | Só quando o container precisa **conversar** com outro. Formato: `--link nome_do_container:alias`. Dentro do container, o outro será acessível pelo nome do alias |
| última palavra | Nome da imagem (ex: `redis:alpine`, `wordpress`) |

Exemplos — 5 containers extras que você pode adicionar:

```bash
docker run -d --name adminer -p 8082:8080 --link wordpress-db:mysql adminer
```

```bash
docker run -d --name redis -p 6379:6379 redis:alpine
```

```bash
docker run -d --name mailhog -p 8025:8025 -p 1025:1025 mailhog/mailhog
```

```bash
docker run -d --name portainer -p 9000:9000 -v /var/run/docker.sock:/var/run/docker.sock portainer/portainer-ce:latest
```

```bash
docker run -d --name whoami -p 8083:80 traefik/whoami
```

Confirme todos:

```bash
docker ps
```

Regras: um `docker run` = um container, nome único, portas diferentes na máquina. `--link` só quem precisa falar com o banco (ex: `adminer`). Redis, mailhog, portainer e whoami não precisam.

---

## Comandos extras — Remover os containers

Parar e remover os 3 containers de uma vez:

```bash
docker rm -f wordpress phpmyadmin wordpress-db
```

Remover um container só (exemplo: phpMyAdmin):

```bash
docker rm -f phpmyadmin
```

Verificar se foram removidos:

```bash
docker ps -a
```
# Trabalho-Docker
