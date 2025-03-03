FROM python:3.11-buster

LABEL org.opencontainers.image.source=https://github.com/bihealth/sodar-server
LABEL org.opencontainers.image.authors="Mikko Nieminen <mikko.nieminen@bih-charite.de>"

ARG app_git_url=https://github.com/bihealth/sodar-server.git
ARG app_git_tag
ARG app_git_depth=1

ENV DEBIAN_FRONTEND noninteractive
ENV CUSTOM_STATIC_DIR /usr/src/app/local-static

## Add the wait script to the image
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.12.1/wait /usr/local/bin/wait
RUN chmod +x /usr/local/bin/wait

# Copy source code into Docker image
RUN mkdir -p /usr/src
RUN git clone --depth $app_git_depth --branch $app_git_tag $app_git_url /usr/src/app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y apt-utils gcc ldap-utils libldap2-dev libsasl2-dev \
        make postgresql-client wget

# Install Nodejs v18
RUN apt-get install -y ca-certificates curl gnupg && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
RUN echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_18.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list
RUN apt-get update && \
    apt-get install nodejs -y

# Install Python dependencies
RUN cd /usr/src/app && \
    pip install --no-cache-dir -r requirements/production.txt && \
    pip install --no-cache-dir -r requirements/local.txt

# Install npm dependencies
RUN cd /usr/src/app/samplesheets/vueapp && \
    mkdir -p /usr/src/app/samplesheets/vueapp/dist && \
    npm ci && \
    npm run build

# Download files from CDN
RUN mkdir -p /usr/src/app/local-static/local/css && \
    mkdir -p /usr/src/app/local-static/local/js && \
    cd /usr/src/app/local-static/local/css && \
    wget \
        https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/css/bootstrap.min.css \
        https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/css/bootstrap.min.css.map && \
    \
    cd /usr/src/app/local-static/local/js && \
    wget \
        https://code.jquery.com/jquery-3.5.1.min.js \
        https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/js/bootstrap.bundle.min.js \
        https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/js/bootstrap.bundle.min.js.map \
        https://cdnjs.cloudflare.com/ajax/libs/tether/1.4.4/js/tether.js \
        https://cdnjs.cloudflare.com/ajax/libs/shepherd/1.8.1/js/shepherd.min.js \
        https://cdnjs.cloudflare.com/ajax/libs/clipboard.js/2.0.0/clipboard.min.js \
        https://browser.sentry-cdn.com/7.15.0/bundle.tracing.min.js \
        https://browser.sentry-cdn.com/7.15.0/bundle.tracing.min.js.map

# Get icons
RUN cd /usr/src/app && \
    DJANGO_SECRET_KEY=for-build-only \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    DATABASE_URL=postgres://sodar:sodar@fake/sodar \
    python manage.py geticons

# Prepare static files
RUN cd /usr/src/app && \
    DJANGO_SECRET_KEY=for-build-only \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    DATABASE_URL=postgres://sodar:sodar@fake/sodar \
    python manage.py collectstatic --no-input

# Define the entry point
COPY docker-entrypoint.sh /usr/local/bin
RUN chmod +x /usr/local/bin/docker-entrypoint.sh && \
    ln -s /usr/local/bin/docker-entrypoint.sh / # backwards compat
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["wsgi"]
EXPOSE 8080/tcp
