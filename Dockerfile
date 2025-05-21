FROM nginx:alpine

# Crear directorio para el sitio web y establecer permisos
RUN mkdir -p /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html && \
    chown -R nginx:nginx /usr/share/nginx/html

# Copiar archivos del sitio web al directorio de Nginx
COPY --chown=nginx:nginx . /usr/share/nginx/html

# Crear directorio para configuraciones de Nginx y establecer permisos
RUN mkdir -p /etc/nginx/conf.d && \
    chmod -R 755 /etc/nginx/conf.d

# Exponer puertos
EXPOSE 80 443

# Asegurarse de que el script de entrada tenga permisos de ejecución
RUN chmod +x /docker-entrypoint.sh

# Comando para iniciar Nginx
CMD ["nginx", "-g", "daemon off;"]
