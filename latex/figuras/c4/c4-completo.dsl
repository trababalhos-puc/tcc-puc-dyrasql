workspace "DyraSQL" "Framework de roteamento dinamico baseado em metadados Iceberg" {

    model {
        analista = person "Analista de dados" "Executa consultas SQL"

        ambienteLocal = softwareSystem "Ambiente local" "Trino, MinIO, PostgreSQL e catalogo Iceberg" "External"

        sistemaRoteamento = softwareSystem "DyraSQL" "Framework de roteamento dinamico baseado em metadados Iceberg" {

            trinoGatewayProxy = container "Trino Gateway Proxy" "FastAPI" "Proxy de roteamento" "Gateway" {
                description "Intercepta consultas SQL e integra-se com DyraSQL Core"
            }

            trinoGateway = container "Trino Gateway" "Trino Gateway" "Balanceamento de carga" "Gateway" {
                description "Balanceador e roteamento de consultas"
            }

            dyraSQLCore = container "DyraSQL Core" "Python" "Analise e decisao" "Core" {
                description "Sistema de analise de consultas e decisao de roteamento"

                apiREST = component "API REST" "FastAPI" "API de roteamento"
                queryAnalyzer = component "Query Analyzer" "Python" "Analise de consultas"
                decisionEngine = component "Decision Engine" "Python" "Decisao de roteamento"
                historyManager = component "History Manager" "Python" "Gerenciamento de historico"
            }

            clusterSmall = container "Cluster Trino Small" "Trino" "Consultas leves" "ClusterSmall" {
                description "Cluster Small para consultas com Score menor que 0,3"
            }

            clusterMedium = container "Cluster Trino Medium" "Trino" "Consultas medias" "ClusterMedium" {
                description "Cluster Medium para consultas com Score 0,3 a 0,7"
            }

            clusterLarge = container "Cluster Trino Large" "Trino" "Consultas pesadas" "ClusterLarge" {
                description "Cluster Large para consultas com Score maior que 0,7"
            }

            postgres = container "PostgreSQL" "PostgreSQL" "Cache e historico" "Database" {
                description "Cache TTL 24h, historico de execucoes e metricas"
            }

            catalogoRest = container "Catalogo Iceberg REST" "Iceberg REST" "Catalogo de metadados" "Database" {
                description "Catalogo de metadados das tabelas Iceberg"
            }

            tabelasIceberg = container "Tabelas Apache Iceberg" "Apache Iceberg" "Dados e metadados" "DataLake" {
                description "Dados e metadados armazenados no MinIO"
            }
        }

        analista -> sistemaRoteamento "Executa consultas SQL"
        sistemaRoteamento -> ambienteLocal "Utiliza clusters e data lake local"
        sistemaRoteamento -> analista "Resultado da consulta"

        trinoGatewayProxy -> dyraSQLCore "1. Decisao"
        dyraSQLCore -> postgres "2. Cache"
        dyraSQLCore -> clusterSmall "3. EXPLAIN"
        clusterSmall -> catalogoRest "4. Metadados"
        dyraSQLCore -> trinoGatewayProxy "5. Score"
        trinoGatewayProxy -> trinoGateway "6. Balanceamento"
        trinoGatewayProxy -> clusterSmall "7a. Roteamento"
        trinoGatewayProxy -> clusterMedium "7b. Roteamento"
        trinoGatewayProxy -> clusterLarge "7c. Roteamento"
        clusterSmall -> tabelasIceberg "8. Dados"
        clusterMedium -> tabelasIceberg "8. Dados"
        clusterLarge -> tabelasIceberg "8. Dados"
        postgres -> dyraSQLCore "9. Historico"

        trinoGatewayProxy -> apiREST "1. Query"
        apiREST -> queryAnalyzer "2. Fingerprint"
        apiREST -> historyManager "3. Cache"
        historyManager -> postgres "4. TTL"
        queryAnalyzer -> clusterSmall "5. EXPLAIN"
        clusterSmall -> catalogoRest "6. Metadados"
        clusterSmall -> tabelasIceberg "7. Dados"
        queryAnalyzer -> decisionEngine "8. Dados"
        decisionEngine -> historyManager "9. Historico"
        decisionEngine -> apiREST "10. Decisao"
        apiREST -> trinoGatewayProxy "11. JSON"
        postgres -> decisionEngine "12. Aprendizado"
    }

    views {
        theme default

        systemContext sistemaRoteamento "ContextoDoSistema" {
            include *
            title "Contexto do Sistema"
            description "Analista executa consultas SQL no DyraSQL em ambiente local."
            autolayout lr
        }

        container sistemaRoteamento "ContainersDoSistema" {
            include sistemaRoteamento
            include trinoGatewayProxy
            include trinoGateway
            include dyraSQLCore
            include clusterSmall
            include clusterMedium
            include clusterLarge
            include postgres
            include catalogoRest
            include tabelasIceberg
            title "Containers do Sistema"
            description "Trino Gateway Proxy intercepta consultas, DyraSQL Core analisa e decide, clusters processam."
            autolayout tb
        }

        component dyraSQLCore "ComponentesRoteamento" {
            include dyraSQLCore
            include apiREST
            include queryAnalyzer
            include decisionEngine
            include historyManager
            include trinoGatewayProxy
            include clusterSmall
            include catalogoRest
            include tabelasIceberg
            include postgres
            title "Componentes do DyraSQL Core"
            description "Fluxo de interceptacao, analise, decisao e historico."
            autolayout tb
        }

        styles {
            element "Person" {
                shape Person
                fontSize 30
            }
            element "Software System" {
                fontSize 30
            }
            element "Container" {
                fontSize 30
            }
            element "Component" {
                fontSize 30
            }
            element "Database" {
                shape Cylinder
                fontSize 30
            }
            element "Gateway" {
                shape Pipe
                fontSize 30
            }
            element "Core" {
                shape Component
                fontSize 30
            }
            element "ClusterSmall" {
                shape Hexagon
                background #6cb6ff
                width 480
                fontSize 30
            }
            element "ClusterMedium" {
                shape Hexagon
                background #1168bd
                width 480
                fontSize 30
            }
            element "ClusterLarge" {
                shape Hexagon
                background #0b4884
                width 480
                fontSize 30
            }
            element "DataLake" {
                shape Folder
                fontSize 30
            }
            element "External" {
                background #999999
                color #ffffff
                border Dashed
                fontSize 30
            }
            relationship "Relationship" {
                fontSize 30
            }
        }
    }
}
