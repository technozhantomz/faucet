# Tapin

`tapin` is a python-based faucet for PeerPlays.

## Usage
There are two APIs
* `'/api/v1/accounts', methods=['POST'], defaults={'referrer': None}` # This is the legacy API
* `'/api/v2/accounts', methods=['POST'], defaults={'referrer': None}` # This is the asynchronous API

v2 moves account creation to a rq worker process, so that a quck response is offered by the API.
This helps in managing peak loads, that is simultaneous account creations.
Depending on the transaction state, the following states are returned

1. init
2. run
3. acccount exists

## Installation

* `pip install -r requirements.txt` # to install dependencies

* edit `config.py` and provide private keys and settings
* `python manage.py install`

## Use virtual environment if required, to minimize libaray conflicts

## Usage

* `python work.py` # for starting worker 

* `python manage.py run` # for normal run
* `python manage.py start` # for debug

The faucet is then available at URL `http://localhost:5000`

## Test
* `python test_faucet.py`

## Nginx configuration

Run `uwsgi --ini wsgi.ini`

and use a configuration similar tothis

```
user peerplays;
worker_processes  4;

events {
    worker_connections  2048;
}

http {
    include       mime.types;
    default_type  application/octet-stream;
    access_log  /www/logs/access.log;
    error_log  /www/logs/error.log;
    log_not_found off;
    sendfile        on;
    keepalive_timeout  65;
    gzip  on;

    upstream websockets {
      server localhost:9090;
      server localhost:9091;
    }

    server {
        listen       80;
        if ($scheme != "https") {
                return 301 https://$host$request_uri;
        }

        listen       443 ssl;
        server_name  peerplays-wallet.com;
        ssl_certificate      /etc/nginx/ssl/peerplays-wallet.com.crt;
        ssl_certificate_key /etc/nginx/ssl/peerplays-wallet.com.key;
        ssl_session_cache    shared:SSL:1m;
        ssl_session_timeout  5m;
        ssl_ciphers  HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers  on;

        location ~ /ws/? {
            access_log on;
            proxy_pass http://websockets;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_next_upstream     error timeout invalid_header http_500;
            proxy_connect_timeout   2;
        }
        location ~ ^/[\w\d\.-]+\.(js|css|dat|png|json)$ {
            root /www/wallet;
            try_files $uri /wallet$uri =404;
        }
        location / {
            root /www/wallet;
        }
        location /api {
                include uwsgi_params;
                uwsgi_pass unix:/tmp/faucet.sock;
        }

    }
}
```
