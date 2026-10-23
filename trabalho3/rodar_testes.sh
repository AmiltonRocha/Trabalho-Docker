#!/usr/bin/env bash
# ============================================================
# Trabalho 3 - Executa a matriz completa de testes de carga
#   instancias (1,2,3) x cenarios (1,2,3) x usuarios (10,350,400,500)
# CSVs sao gravados em locust/$SAIDA/ (padrao: locust/resultados/)
#
# Variaveis (opcionais):
#   USUARIOS="10 350 400 500"  INSTANCIAS="1 2 3"  RUN_TIME=30s  SPAWN_RATE=25
#   PAUSA=20                   segundos de descanso antes de cada teste, para
#                              a carga do teste anterior nao contaminar o proximo
#   SAIDA=resultados           pasta dentro de locust/ para os CSVs
#   MYSQL_MAX_CONNECTIONS=151  limite de conexoes do MySQL (padrao do MySQL)
#
# Ex.: segunda matriz com o MySQL aceitando mais conexoes:
#   MYSQL_MAX_CONNECTIONS=500 SAIDA=resultados_maxconn500 ./rodar_testes.sh
#
# Alem dos CSVs do Locust, grava $SAIDA/conexoes_mysql.csv com quantas
# conexoes o MySQL recusou por excesso em cada teste (causa dos HTTP 500).
#
# IMPORTANTE: usa `docker compose exec` (e NAO `docker compose run`),
# pois `compose run` re-sincroniza a escala e REMOVE os containers
# extras criados com --scale wordpress=N.
# ============================================================
set -e
cd "$(dirname "$0")"

# Git Bash (Windows) converte /locust/... em caminho do Windows antes de
# chamar o docker; isto desliga a conversao (sem efeito no Linux)
export MSYS_NO_PATHCONV=1

USUARIOS=(${USUARIOS:-10 350 400 500})
INSTANCIAS=(${INSTANCIAS:-1 2 3})
CENARIOS=(cenario1 cenario2 cenario3)
RUN_TIME=${RUN_TIME:-30s}
SPAWN_RATE=${SPAWN_RATE:-25}
PAUSA=${PAUSA:-20}
SAIDA=${SAIDA:-resultados}
# lido pelo docker-compose.yml (command do mysql)
export MYSQL_MAX_CONNECTIONS=${MYSQL_MAX_CONNECTIONS:-151}

mkdir -p "locust/${SAIDA}"

mysql_cmd() {
  docker compose exec -T mysql mysql -uroot -pr00t -N -e "$1" 2>/dev/null
}

mysql_status() {
  mysql_cmd "SHOW GLOBAL STATUS LIKE '$1'" | awk '{print $2}'
}

# garante todos os servicos de base no ar (recria o mysql se o limite mudou)
docker compose up -d
until mysql_cmd "SELECT 1" >/dev/null; do sleep 2; done
echo "MySQL max_connections = $(mysql_cmd "SELECT @@max_connections")"
echo "cenario,usuarios,instancias,conexoes_recusadas,max_conexoes_usadas" > "locust/${SAIDA}/conexoes_mysql.csv"

for inst in "${INSTANCIAS[@]}"; do
  echo "=========================== Instancias do WordPress: $inst ==========================="
  docker compose up -d --scale "wordpress=$inst"
  # reinicia o nginx para re-resolver os IPs das instancias no DNS
  docker compose restart nginx
  sleep 10

  # confirma o balanceamento (X-Upstream deve alternar)
  echo "Teste rapido do balanceamento:"
  for i in 1 2 3; do
    curl -sI http://localhost:8080/ | grep -i x-upstream || true
  done

  for cen in "${CENARIOS[@]}"; do
    for usr in "${USUARIOS[@]}"; do
      nome="${cen}_u${usr}_i${inst}"
      echo "---- ${cen} | usuarios=${usr} | instancias=${inst} | duracao=${RUN_TIME} ----"
      sleep "${PAUSA}"
      mysql_cmd "FLUSH STATUS" || true
      recusadas_antes=$(mysql_status Connection_errors_max_connections)

      # o CSV e escrito dentro do container e copiado no final: gravar
      # direto na pasta compartilhada falhava no Windows (OSError 22)
      docker compose exec -T locust locust \
        -f /locust/locustfile.py --host=http://nginx:8080 \
        --headless -u "${usr}" -r "${SPAWN_RATE}" --run-time "${RUN_TIME}" \
        --tags "${cen}" --csv "/tmp/${nome}" --only-summary || true
      docker compose exec -T locust sh -c "cp /tmp/${nome}_*.csv /locust/${SAIDA}/ && rm -f /tmp/${nome}_*.csv"

      recusadas=$(( $(mysql_status Connection_errors_max_connections) - recusadas_antes ))
      echo "${cen},${usr},${inst},${recusadas},$(mysql_status Max_used_connections)" >> "locust/${SAIDA}/conexoes_mysql.csv"
      echo "MySQL: ${recusadas} conexoes recusadas por excesso"
    done
  done
done

echo
echo "==== Todos os testes concluidos! ===="
echo "Proximos passos:"
echo "  python3 gerar_graficos.py --pasta locust/${SAIDA}"
echo "  python3 gerar_graficos_comparacao.py --pasta locust/${SAIDA}"
