#!/bin/bash

# Erstelle config.json aus ENV-Variablen
cat <<EOF > /usr/share/nginx/html/config.json
{
    "ApiBaseUrl": "${API_HOST}:${API_PORT}",
    "LLMUrl": "${LLM_URL}"
}
EOF

# Starte Nginx im Vordergrund
exec nginx -g "daemon off;"
