# Front: se compila con Vite y se sirve con nginx
FROM node:22-alpine AS compilacion

WORKDIR /app/front

COPY front/package.json front/package-lock.json ./
RUN npm ci

COPY front/ ./
COPY docs/auditoria/ /app/docs/auditoria/
COPY simulador2/*.py /app/simulador2/
COPY README.md Levantamiento_de_requrimientos_Cap1COSBUS.md /app/
RUN npm run build


FROM nginx:1.27-alpine

COPY front/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=compilacion /app/front/dist /usr/share/nginx/html

EXPOSE 80
