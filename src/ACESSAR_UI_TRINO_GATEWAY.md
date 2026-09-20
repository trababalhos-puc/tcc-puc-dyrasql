# Como Acessar a UI do Trino Gateway

## URLs de Acesso

### Interface Web (UI)
- **URL:** http://localhost:8085
- **Descrição:** Interface web do Trino Gateway para visualizar queries, backends e estatísticas

### API Administrativa
- **URL:** http://localhost:8084
- **Descrição:** API REST para gerenciamento e monitoramento

## Endpoints Úteis da API

### Listar Backends Ativos
```bash
curl http://localhost:8084/gateway/backend/active
```

### Listar Todos os Backends
```bash
curl http://localhost:8084/gateway/backend/all
```

### Health Check
```bash
curl http://localhost:8084/healthcheck
```

### Informações do Gateway
```bash
curl http://localhost:8084/entity?entityType=GATEWAY_BACKEND
```

## O que Você Pode Ver na UI

1. **Queries Executadas**: Lista de queries executadas através do gateway
2. **Backends**: Status e informações dos clusters Trino configurados
3. **Estatísticas**: Métricas de uso e performance
4. **Roteamento**: Visualização de como as queries são roteadas

## Verificando Roteamento dos Clusters

### Via API
```bash
# Ver backends e seus status
curl http://localhost:8084/gateway/backend/active | python3 -m json.tool
```

### Via UI
1. Acesse http://localhost:8085
2. Navegue até a seção "Backends" ou "Clusters"
3. Veja o status de cada backend (HEALTHY, UNHEALTHY, etc.)
4. Verifique estatísticas de uso de cada cluster

## Notas Importantes

- O Trino Gateway está na porta **8085** (application port)
- A porta **8084** é para APIs administrativas
- O proxy inteligente (trino-gateway-proxy) está na porta **8080** e intercepta queries antes do gateway
- Para ver o roteamento dinâmico do DyraSQL Core, verifique os logs do `dyrasql-core`:
  ```bash
  docker compose logs -f dyrasql-core | grep ROUTING
  ```

