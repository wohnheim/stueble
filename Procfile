frontend: cd packages/frontend && yarn run preview --host $HOST --port $FE_PORT 2>&1 | tee -a ../../logs/frontend.log
database: postgres --unix_socket_directories="$PGHOST" 2>&1 | tee -a logs/database.log
backend: PYTHONUNBUFFERED=1 backend 2>&1 | tee -a logs/backend.log
backend-go: cd packages/backend-go && stdbuf -o0 -e0 go run . 2>&1 | tee -a ../../logs/backend-go.log
webserver: nginx -c $NGINX_CONF 2>&1 | tee -a logs/webserver.log
