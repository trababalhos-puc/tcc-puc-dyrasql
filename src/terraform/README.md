# Terraform - Provisionamento da Tabela DynamoDB

Este diretório contém os arquivos Terraform para criar a tabela DynamoDB necessária para o DyraSQL.

## Estrutura da Tabela

A tabela DynamoDB criada possui a seguinte estrutura:

- **Nome**: `dyrasql-history` (configurável)
- **Chave primária**: `fingerprint` (String) - Hash key
- **Atributos**:
  - `fingerprint` (String) - Chave primária, identificador único da consulta
  - `cluster` (String) - Cluster selecionado para execução
  - `score` (String) - Score calculado pelo algoritmo de decisão
  - `factors` (String) - JSON com os fatores utilizados no cálculo
  - `timestamp` (String) - Timestamp da decisão
  - `ttl` (Number) - Time To Live para expiração automática (24 horas)
  - `execution_time` (Number) - Tempo de execução (opcional, adicionado pós-execução)
  - `cost` (Number) - Custo da execução (opcional, adicionado pós-execução)
  - `success` (Boolean) - Indica se a execução foi bem-sucedida (opcional)

## Pré-requisitos

1. **Terraform instalado** (versão >= 1.0)
   ```bash
   terraform version
   ```

2. **AWS CLI configurado** com credenciais válidas
   ```bash
   aws configure
   ```

3. **Permissões IAM** necessárias:
   - `dynamodb:CreateTable`
   - `dynamodb:DescribeTable`
   - `dynamodb:PutItem`
   - `dynamodb:GetItem`
   - `dynamodb:UpdateItem`
   - `dynamodb:DeleteItem`
   - `dynamodb:Query`
   - `dynamodb:Scan`

## Uso

### 1. Configurar variáveis

Copie o arquivo de exemplo e ajuste os valores:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edite `terraform.tfvars` com seus valores:

```hcl
aws_region = "us-east-1"
dynamodb_table_name = "dyrasql-history"
environment = "dev"
enable_point_in_time_recovery = false
```

### 2. Inicializar Terraform

```bash
cd terraform
terraform init
```

### 3. Validar configuração

```bash
terraform validate
```

### 4. Ver plano de execução

```bash
terraform plan
```

### 5. Aplicar configuração

```bash
terraform apply
```

Confirme digitando `yes` quando solicitado.

### 6. Verificar outputs

Após a criação, os outputs serão exibidos:

```
Outputs:

dynamodb_table_name = "dyrasql-history"
dynamodb_table_arn = "arn:aws:dynamodb:us-east-1:123456789012:table/dyrasql-history"
dynamodb_table_id = "dyrasql-history"
```

### 7. Destruir recursos (se necessário)

```bash
terraform destroy
```

## Configurações

### Billing Mode

A tabela é criada com `PAY_PER_REQUEST` (on-demand), o que significa:
- Sem necessidade de provisionar capacidade
- Paga apenas pelo que usar
- Escala automaticamente
- Ideal para cargas de trabalho variáveis

### TTL (Time To Live)

O TTL está habilitado no atributo `ttl`:
- Itens expiram automaticamente após 24 horas
- Reduz custos de armazenamento
- Mantém apenas histórico recente

### Criptografia

A criptografia server-side está habilitada por padrão usando a chave gerenciada pela AWS (AWS KMS).

### Point-in-Time Recovery

O Point-in-Time Recovery está desabilitado por padrão. Para habilitar:

```hcl
enable_point_in_time_recovery = true
```

## Variáveis Disponíveis

| Variável | Descrição | Tipo | Padrão |
|----------|-----------|------|--------|
| `aws_region` | Região AWS | string | `us-east-1` |
| `dynamodb_table_name` | Nome da tabela | string | `dyrasql-history` |
| `environment` | Ambiente (dev/staging/prod) | string | `dev` |
| `enable_point_in_time_recovery` | Habilitar PITR | bool | `false` |
| `common_tags` | Tags comuns | map(string) | `{}` |

## Outputs

| Output | Descrição |
|--------|-----------|
| `dynamodb_table_name` | Nome da tabela criada |
| `dynamodb_table_arn` | ARN da tabela |
| `dynamodb_table_id` | ID da tabela |
| `dynamodb_table_stream_arn` | ARN do stream (se habilitado) |

## Integração com Docker Compose

Após criar a tabela, atualize o arquivo `.env` do docker-compose:

```env
DYNAMODB_TABLE=dyrasql-history
AWS_REGION=us-east-1
```

## Troubleshooting

### Erro: "Access Denied"

Verifique se suas credenciais AWS têm as permissões necessárias:

```bash
aws sts get-caller-identity
aws dynamodb list-tables
```

### Erro: "Table already exists"

Se a tabela já existe, você pode:
1. Importar a tabela existente: `terraform import aws_dynamodb_table.dyrasql_history dyrasql-history`
2. Ou usar um nome diferente: ajuste `dynamodb_table_name` no `terraform.tfvars`

### Erro: "Region not found"

Verifique se a região especificada está correta:

```bash
aws ec2 describe-regions --query 'Regions[].RegionName'
```

## Referências

- [Terraform AWS Provider - DynamoDB](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_table)
- [AWS DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)
- [DynamoDB TTL](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)

