#!/usr/bin/env bash
# ============================================================
# Trabalho AV2 - Computação Distribuída
# Instalação e Configuração do WordPress utilizando Docker
# Script validado passo a passo
# ============================================================
set -e

echo "=== PASSO 1: Verificar instalação do Docker ==="
docker --version
docker compose version
systemctl is-active docker || service docker status
docker run --rm hello-world

echo
echo "=== PASSO 2: Configurar e iniciar o MySQL ==="
docker pull mysql:5.7
docker images

docker run -d \
  -p 3306:3306 \
  --name wordpress-db \
  -e MYSQL_ROOT_PASSWORD=r00t \
  -e MYSQL_DATABASE=wordpress \
  -e MYSQL_USER=usr-wordpress \
  -e MYSQL_PASSWORD=pwd-wordpress \
  mysql:5.7

echo "Aguardando o MySQL ficar pronto..."
until docker exec wordpress-db mysql -uusr-wordpress -ppwd-wordpress \
      -e "USE wordpress;" 2>/dev/null; do
  sleep 2
done
echo "MySQL pronto!"
docker ps --filter name=wordpress-db

echo
echo "=== PASSO 3: Configurar e iniciar o WordPress ==="
docker run -d \
  -p 8080:80 \
  --name wordpress \
  --link wordpress-db:mysql \
  -e WORDPRESS_DB_HOST=wordpress-db:3306 \
  -e WORDPRESS_DB_USER=usr-wordpress \
  -e WORDPRESS_DB_PASSWORD=pwd-wordpress \
  -e WORDPRESS_DB_NAME=wordpress \
  wordpress

sleep 10
docker ps

echo
echo "=== Validação final ==="
curl -s -o /dev/null -w "HTTP %{http_code} -> %{url_effective}\n" -L http://localhost:8080
echo "Acesse no navegador: http://localhost:8080 (tela de instalação do WordPress)"
