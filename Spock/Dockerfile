# syntax=docker/dockerfile:1

############################################
## 1) Build & Publish the Blazor WASM app
############################################
ARG DOTNET_VERSION=8.0
FROM mcr.microsoft.com/dotnet/sdk:${DOTNET_VERSION} AS builder

WORKDIR /src

# SVN build args from TeamCity
ARG SVN_REVISION=unknown
ARG BUILD_URL=unknown

# Add DevExpress NuGet feed
RUN dotnet nuget add source https://nuget.devexpress.com/...

# Copy project and restore dependencies
COPY Spock.csproj ./
RUN dotnet restore "Spock.csproj"

# Copy all source code
COPY . .

# Publish the Blazor app
RUN dotnet publish "Spock.csproj" -c Release -o /app/publish --no-restore

# Create version.json using passed build args
RUN mkdir -p /src/wwwroot/generated && \
    echo "{\"revision\": \"${SVN_REVISION}\", \"uri\": \"${BUILD_URL}\"}" > /app/publish/wwwroot/generated/version.json

# Inject SVN_REVISION into index.html for cache busting
RUN sed -i "s/__REVISION__/${SVN_REVISION}/g" /app/publish/wwwroot/index.html

############################################
## 2) Final Image: Nginx to serve WASM
############################################
FROM nginx:alpine AS final

# Install bash for entrypoint script
RUN apk add --no-cache bash

# ENV for runtime configuration (optional defaults)
ENV API_HOST=http://localhost
ENV API_PORT=8000
ENV LLM_URL=http://localhost:8080

# Remove default nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy published Blazor WASM build
COPY --from=builder /app/publish/wwwroot /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose HTTP port
EXPOSE 80

# Use custom entrypoint to generate config and run nginx
CMD ["/entrypoint.sh"]
