# Imagem unica da plataforma DyraSQL (MinIO + Trino Gateway).
# Cada servico do docker compose usa esta mesma imagem com um comando diferente.
# Contexto de build: diretorio src/ (usa o codigo em vendor/, sem clonar nada).

FROM --platform=$BUILDPLATFORM golang:1.24-alpine@sha256:8bee1901f1e530bfb4a7850aa7a479d17ae3a18beb6e09064ed54cfd245b7191 AS minio-build
ARG TARGETOS
ARG TARGETARCH
WORKDIR /src
COPY vendor/minio/ /src/
RUN CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH go build -trimpath -o /out/minio .

FROM --platform=$BUILDPLATFORM eclipse-temurin:25-jdk@sha256:2d5d5e9b533342a565907c84f47a2ec298c40cde7b13a3ca85d4950fa456a641 AS gateway-build
WORKDIR /src
COPY vendor/trino-gateway/ /src/
RUN ./mvnw clean package -DskipTests -Dmaven.gitcommitid.skip=true -pl gateway-ha -am && \
    cp gateway-ha/target/gateway-ha-*-jar-with-dependencies.jar /out-gateway-ha.jar

FROM eclipse-temurin:25-jre@sha256:dbb43d81099eec91e0800226ed2296d03146ee7857165b95112372ad0d67e87f
LABEL maintainer="DyraSQL Project"
LABEL description="Plataforma DyraSQL com MinIO e Trino Gateway"
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY --from=minio-build /out/minio /usr/bin/minio
COPY --from=gateway-build /out-gateway-ha.jar /app/gateway-ha.jar
COPY platform/postgresql-42.7.1.jar /app/postgresql.jar
EXPOSE 9000 9001 8080 8081
CMD ["minio", "--help"]
