let
  /* Inputs */

  pkgs = import <nixpkgs> { };
  inherit (pkgs) lib;

  pyproject-nix = import (builtins.fetchGit {
    url = "https://github.com/pyproject-nix/pyproject.nix.git";
  }) {
    inherit lib;
  };

  uv2nix = import (builtins.fetchGit {
    url = "https://github.com/pyproject-nix/uv2nix.git";
  }) {
    inherit pyproject-nix lib;
  };

  pyproject-build-systems = import (builtins.fetchGit {
    url = "https://github.com/pyproject-nix/build-system-pkgs.git";
  }) {
    inherit pyproject-nix uv2nix lib;
  };

  /* Hardcoded Ports (Development) */

  webserverPort = 3010;
  frontendPort = 3011;
  backendPort = 3012;
  websocketPort = 3013;
  databasePort = 3014;

  /* Python */

  workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

  overlay = workspace.mkPyprojectOverlay { sourcePreference = "wheel"; };

  zbarOverlay = final: prev: {
    pyzbar = prev.pyzbar.overrideAttrs (old: {
      buildInputs = (old.buildInputs or []) ++ [ pkgs.zbar ];

      postInstall = (old.postInstall or "") + ''
        substituteInPlace $out/${pkgs.python3.sitePackages}/pyzbar/zbar_library.py \
          --replace-fail "find_library('zbar')" '"${lib.getLib pkgs.zbar}/lib/libzbar${pkgs.stdenv.hostPlatform.extensions.sharedLibrary}"'
      '';
    });
  };

  pythonSet = (pkgs.callPackage pyproject-nix.build.packages {
    python = pkgs.python3;
  }).overrideScope (
    lib.composeManyExtensions [
      pyproject-build-systems.wheel
      overlay
      zbarOverlay
    ]);

  packageSet = pythonSet.overrideScope (
    final: prev: {
      backend = prev.backend.overrideAttrs (old: {
        src = lib.fileset.toSource rec {
          root = ./.;

          fileset = lib.fileset.unions [
            (root + "/pyproject.toml")
            (root + "/packages/backend")
          ];
        };
      });
    });

  /* Nginx */

  recommendedProxyConfig = pkgs.writeText "nginx-recommended-proxy_set_header-headers.conf" ''
    proxy_set_header        Host $host;
    proxy_set_header        X-Real-IP $remote_addr;
    proxy_set_header        X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header        X-Forwarded-Proto $scheme;
    proxy_set_header        X-Forwarded-Host $host;
    proxy_set_header        X-Forwarded-Server $hostname;
  '';

  nginxConf = ''
    error_log /dev/stdout info;
    daemon off;

    events {}

    http {
      # Mime types
      include ${pkgs.mailcap}/etc/nginx/mime.types;
      types_hash_max_size 2688;

      include ${pkgs.nginx}/conf/fastcgi.conf;
      include ${pkgs.nginx}/conf/uwsgi_params;

      default_type application/octet-stream;

      # Optimisation
      sendfile on;
      tcp_nopush on;
      tcp_nodelay on;
      keepalive_timeout 65;

      # Proxy
      proxy_redirect          off;
      proxy_connect_timeout   60s;
      proxy_send_timeout      60s;
      proxy_read_timeout      60s;
      proxy_http_version      1.1;
      proxy_set_header        "Connection" "";
      proxy_set_header        Host $host;
      proxy_set_header        X-Real-IP $remote_addr;
      proxy_set_header        X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header        X-Forwarded-Proto $scheme;
      proxy_set_header        X-Forwarded-Host $host;
      proxy_set_header        X-Forwarded-Server $host;    

      # Gzip
      gzip on;
      gzip_static on;
      gzip_vary on;
      gzip_comp_level 5;
      gzip_min_length 256;
      gzip_proxied expired no-cache no-store private auth;
      gzip_types application/atom+xml application/geo+json application/javascript application/json application/ld+json application/manifest+json application/rdf+xml application/vnd.ms-fontobject application/wasm application/x-rss+xml application/x-web-app-manifest+json application/xhtml+xml application/xliff+xml application/xml font/collection font/otf font/ttf image/bmp image/svg+xml image/vnd.microsoft.icon text/cache-manifest text/calendar text/css text/csv text/javascript text/markdown text/plain text/vcard text/vnd.rim.location.xloc text/vtt text/x-component text/xml;

      # WebSocket Proxy
      map $http_upgrade $connection_upgrade {
        default upgrade;
        ""      close;
      }

      client_max_body_size 10m;
      server_tokens off;
      access_log /dev/stdout;
      absolute_redirect off;

      server {
        listen 0.0.0.0:${lib.toString webserverPort};
        listen [::0]:${lib.toString webserverPort};
        server_name stueble.localhost;

        location / {
          proxy_pass http://localhost:${lib.toString frontendPort};
          include ${recommendedProxyConfig};
        }

        location /api/ {
          proxy_pass http://localhost:${lib.toString backendPort}/;
          include ${recommendedProxyConfig};
        }

        location /api/websocket {
          proxy_pass http://localhost:${lib.toString websocketPort};
          proxy_http_version 1.1;
          proxy_set_header Upgrade $http_upgrade;
          proxy_set_header Connection $connection_upgrade;
          include ${recommendedProxyConfig};
        }
      }
    }
  '';
in {
  # Backend production package
  backend = packageSet.mkVirtualEnv "backend-env" workspace.deps.default;

  # Development shell (doesn't contain source code)
  shell = let
    sourceOverlay = final: prev: {
      backend = prev.backend.overrideAttrs (old: {
        src = pkgs.runCommand "backend-stub-src" {} ''
          mkdir -p $out/packages/backend

          cp ${./pyproject.toml} $out/pyproject.toml
          touch $out/packages/backend/__init__.py
        '';
      });
    };

    editableOverlay = workspace.mkEditablePyprojectOverlay {
      root = "$REPO_ROOT";
    };

    editableSet = pythonSet.overrideScope (
      lib.composeManyExtensions [
        sourceOverlay
        editableOverlay
      ]);

    virtualenv = editableSet.mkVirtualEnv "backend-env" workspace.deps.all;
  in pkgs.mkShell {
    packages = [
      pkgs.overmind
      pkgs.postgresql_18
      pkgs.nginx

      virtualenv
      pkgs.uv
    ];

    env = {
      OVERMIND_NO_PORT = "1";

      PGDATABASE = "stueble_data";
      PGPORT = lib.toString databasePort;
      HOST = "127.0.0.1";
      PORT = lib.toString backendPort;
      WS_PORT = lib.toString websocketPort;
      FE_PORT = lib.toString frontendPort;

      NGINX_CONF = "${pkgs.writeText "nginx.conf" nginxConf}";

      UV_NO_SYNC = "1";
      UV_PYTHON = editableSet.python.interpreter;
      UV_PYTHON_DOWNLOADS = "never";
    };

    shellHook = ''
      unset PYTHONPATH
      export REPO_ROOT=$(git rev-parse --show-toplevel)

      export PGDATA="$PWD/pg_data"
      export PGHOST="$PWD"

      if [ -e .overmind.sock ]; then
          if overmind status 1>/dev/null; then
              echo $(($(cat .OVERMIND_REF_COUNT) + 1)) > .OVERMIND_REF_COUNT
              SKIP_OVERMIND=1
          else
              rm -f .overmind.sock
          fi
      fi

      if [ -e .env ]; then
          set -a
          . .env
          set +a
      fi

      if [ ! -d pg_data ]; then 
          CREATE_SCHEMA=1
          initdb 1>/dev/null
      fi

      mkdir -p logs

      if [ "$CREATE_SCHEMA" == "1" ]; then
          pg_ctl -s -l logs/database.log -o "--unix_socket_directories='$PGHOST'" start

          createdb 1>/dev/null
          psql -q -f packages/data/create_tables.sql
          psql -q -f packages/data/triggers.sql

          psql -q -c "INSERT INTO users (user_role, room, residence, first_name, last_name, password_hash, email, user_name, verified) VALUES ('admin', 0, 'altbau', 'Super', 'Admin', '$ADMIN_PASSWORD', '$EMAIL_ADDRESS', 'admin', 't');"

          pg_ctl -s stop
      fi

      trap "if [ ! -e .OVERMIND_REF_COUNT ] || [ \"\$(cat .OVERMIND_REF_COUNT)\" == '1' ]; then rm -f .OVERMIND_REF_COUNT; test -e '$PWD/.overmind.sock' && overmind quit --socket '$PWD/.overmind.sock'; else echo \$((\$(cat .OVERMIND_REF_COUNT) - 1)) > .OVERMIND_REF_COUNT; fi" EXIT
      if [ "$SKIP_OVERMIND" != "1" ]; then
          overmind start -D && echo "1" > .OVERMIND_REF_COUNT
      fi
    '';
  };
}
