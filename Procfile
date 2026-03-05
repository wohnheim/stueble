frontend: cd packages/frontend && yarn run preview --host $HOST --port $FE_PORT 2>&1 | tee -a logs/frontend.log
database: postgres --unix_socket_directories="$PGHOST" 2>&1 | tee -a logs/database.log
backend: backend 2>&1 | tee -a logs/backend.log
webserver: nginx -c $NGINX_CONF 2>&1 | tee -a logs/webserver.log
