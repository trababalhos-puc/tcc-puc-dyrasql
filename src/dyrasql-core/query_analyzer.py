#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Query Analyzer - Analisa consultas SQL e extrai informações relevantes
Usa EXPLAIN (TYPE IO) do Trino para obter informações precisas sobre I/O e custos
"""


import re

import hashlib

import logging

import json

import os

import requests

import sqlglot
from sqlglot import exp

from typing import Dict, List, Optional, Any
from datetime import datetime


logger = logging.getLogger(__name__)


class QueryAnalyzer:

    """Analisa consultas SQL e extrai metadados relevantes usando EXPLAIN (TYPE IO)"""

    
    def __init__(self):

        """Inicializa o analisador com configuração do Trino"""

                                                      
        self.trino_url = os.getenv('TRINO_URL', 'http://trino-small:8080')

        self.trino_user = os.getenv('TRINO_USER', 'admin')
        
        # Diretório para salvar os EXPLAIN
        self.save_explains = os.getenv('SAVE_EXPLAINS', 'true').lower() == 'true'
        self.explains_dir = os.getenv('EXPLAINS_DIR', '/app/explains')
        if self.save_explains:
            os.makedirs(self.explains_dir, exist_ok=True)

        # Colunas de particionamento conhecidas, usadas para classificar
        # filtros do WHERE como particionados ou não-particionados
        self.partition_columns = frozenset(
            col.strip().lower()
            for col in os.getenv('PARTITION_COLUMNS', 'date').split(',')
            if col.strip()
        )

    
    def generate_fingerprint(self, query):

        """
        Gera um fingerprint único para a consulta SQL
        Remove espaços, normaliza e cria hash
        """

                                                                             
        normalized = re.sub(r'\s+', ' ', query.strip().lower())

        
        normalized = re.sub(r"'[^']*'", "'?'", normalized)

        normalized = re.sub(r'\d+', '?', normalized)

        
        fingerprint = hashlib.sha256(normalized.encode()).hexdigest()

        
        return fingerprint

    
    def _normalize_query_with_catalog(self, query: str) -> str:
        """
        Normaliza a query adicionando o catálogo 'iceberg' quando não estiver presente
        Exemplo: 'select * from schema.table' -> 'select * from iceberg.schema.table'
        """
        # Padrão para encontrar referências de tabelas: FROM/JOIN schema.table ou apenas table
        # Não modifica se já tiver catálogo especificado (catalog.schema.table)
        
        # Lista de palavras-chave SQL que podem preceder nomes de tabelas
        table_keywords = ['from', 'join', 'inner join', 'left join', 'right join', 'full join', 
                         'cross join', 'left outer join', 'right outer join', 'full outer join']
        
        query_normalized = query
        modified = False
        
        for keyword in table_keywords:
            # Padrão: keyword + espaço + (opcionalmente catalog.) + schema.table ou apenas table
            # Não captura se já tiver catalog.schema.table
            pattern = rf'\b{re.escape(keyword)}\s+([a-zA-Z_][a-zA-Z0-9_]*\.)?([a-zA-Z_][a-zA-Z0-9_]*\.)?([a-zA-Z_][a-zA-Z0-9_]*)'
            
            def replace_table(match):
                nonlocal modified
                full_match = match.group(0)
                part1 = match.group(1)  # Primeira parte (pode ser catalog. ou None)
                part2 = match.group(2)  # Segunda parte (pode ser schema. ou None)
                part3 = match.group(3)  # Nome da tabela
                
                # Se já tem 2 pontos (catalog.schema.table), não modifica
                if part1 and part2:
                    return full_match
                
                # Se tem apenas 1 ponto (schema.table), adiciona iceberg.
                if part2 and not part1:
                    modified = True
                    return f"{keyword} iceberg.{part2}{part3}"
                
                # Se não tem pontos (apenas table), não modifica (pode ser alias ou função)
                # Mas se está após FROM/JOIN, provavelmente é uma tabela
                if not part1 and not part2:
                    # Verifica se não é uma função ou subquery
                    if part3.lower() not in ['select', 'values', 'unnest', 'table']:
                        # Não modifica automaticamente - pode ser alias ou tabela sem schema
                        # Deixamos o Trino resolver isso
                        return full_match
                
                return full_match
            
            query_normalized = re.sub(pattern, replace_table, query_normalized, flags=re.IGNORECASE)
        
        # Se não houve modificação, tenta uma abordagem mais simples:
        # Procura por padrões FROM schema.table ou JOIN schema.table e adiciona iceberg.
        if not modified:
            # Padrão mais simples: FROM/JOIN seguido de schema.table (sem catalog)
            simple_pattern = r'\b(from|join|inner\s+join|left\s+join|right\s+join|full\s+join|cross\s+join)\s+([a-zA-Z_][a-zA-Z0-9_]+)\.([a-zA-Z_][a-zA-Z0-9_]+)'
            
            def add_catalog(match):
                nonlocal modified
                keyword = match.group(1)
                schema = match.group(2)
                table = match.group(3)
                
                # Verifica se schema não é 'iceberg' (já tem catálogo)
                if schema.lower() != 'iceberg':
                    modified = True
                    return f"{keyword} iceberg.{schema}.{table}"
                return match.group(0)
            
            query_normalized = re.sub(simple_pattern, add_catalog, query_normalized, flags=re.IGNORECASE)
        
        if modified:
            logger.info(f"Query normalizada com catálogo iceberg: {query[:100]}... -> {query_normalized[:100]}...")
        
        return query_normalized

    
    def _save_explain(self, query: str, explain_result: Dict[str, Any], parsed_result: Optional[Dict[str, Any]] = None, normalized_query: Optional[str] = None):
        """
        Salva o resultado do EXPLAIN em um arquivo JSON para análise posterior
        """
        if not self.save_explains:
            return
            
        try:
            fingerprint = self.generate_fingerprint(query)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            
            # Nome do arquivo: timestamp_fingerprint_short.json
            filename = f"{timestamp}_{fingerprint[:16]}.json"
            filepath = os.path.join(self.explains_dir, filename)
            
            # Estrutura completa do EXPLAIN salvo
            explain_data = {
                'timestamp': datetime.now().isoformat(),
                'fingerprint': fingerprint,
                'query': query,
                'normalized_query': normalized_query if normalized_query else query,
                'explain_query': f"EXPLAIN (TYPE IO) {normalized_query if normalized_query else query}",
                'raw_explain': explain_result.get('raw', {}),
                'result_complete': explain_result.get('result_complete'),
                'error': explain_result.get('error'),
                'error_details': explain_result.get('error_details'),
                'explain_json_str': explain_result.get('explain_json_str'),
                'parsed_result': parsed_result,
                'summary': {
                    'total_tables': len(parsed_result.get('tables', {})) if parsed_result else 0,
                    'total_size_bytes': parsed_result.get('total_size_bytes', 0) if parsed_result else 0,
                    'total_size_gb': (parsed_result.get('total_size_bytes', 0) / (1024**3)) if parsed_result else 0,
                    'total_rows': parsed_result.get('total_rows', 0) if parsed_result else 0,
                    'total_cpu_cost': parsed_result.get('total_cpu_cost', 0) if parsed_result else 0,
                },
                'tables': parsed_result.get('tables', {}) if parsed_result else {}
            }
            
            # Garante que o diretório existe
            os.makedirs(self.explains_dir, exist_ok=True)
            
            # Salva o arquivo JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(explain_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"EXPLAIN salvo em: {filepath}")
            if parsed_result:
                logger.info(f"  Resumo: {explain_data['summary']['total_tables']} tabelas, "
                           f"{explain_data['summary']['total_size_gb']:.2f} GB, "
                           f"{explain_data['summary']['total_rows']:,.0f} linhas")
            else:
                logger.info(f"  EXPLAIN salvo com erro: {explain_result.get('error', 'Unknown error')}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar EXPLAIN: {str(e)}", exc_info=True)

    
    def _execute_trino_query(self, query: str) -> Optional[Dict[str, Any]]:

        """
        Executa uma query no Trino via API REST e retorna o resultado completo
        """

        try:

                             
            response = requests.post(

                f"{self.trino_url}/v1/statement",

                headers={

                    "Content-Type": "text/plain",

                    "X-Trino-User": self.trino_user

                },

                data=query,

                timeout=60                                                  

            )

            
            if response.status_code != 200:

                error_info = {
                    'status_code': response.status_code,
                    'response_text': response.text,
                    'error': f'HTTP {response.status_code}'
                }
                logger.error(f"Erro ao executar query no Trino: {response.status_code} - {response.text}")

                return error_info

            
            result = response.json()

            
            if 'error' in result:

                error_msg = result['error'].get('message', str(result['error']))
                logger.error(f"Erro na query: {error_msg}")

                # Retorna o resultado com erro para que possamos salvá-lo
                return {
                    'error': error_msg,
                    'error_details': result.get('error'),
                    'result': result
                }

            
            next_uri = result.get('nextUri')

            all_data = []

            
            if 'data' in result and result['data']:

                all_data.extend(result['data'])

            
            while next_uri:

                next_response = requests.get(

                    next_uri,

                    headers={"X-Trino-User": self.trino_user},

                    timeout=60                                                  

                )

                
                if next_response.status_code != 200:

                    logger.error(f"Erro ao obter próximos resultados: {next_response.status_code}")

                    break

                
                next_result = next_response.json()

                
                if 'data' in next_result:

                    all_data.extend(next_result['data'])

                
                if next_result.get('stats', {}).get('state') == 'FINISHED':

                    break

                
                next_uri = next_result.get('nextUri')

            
            return {

                'columns': result.get('columns', []),

                'data': all_data,

                'stats': result.get('stats', {})

            }

            
        except Exception as e:

            logger.error(f"Erro ao executar query no Trino: {str(e)}", exc_info=True)

            return None

    
    def _parse_explain_io(self, explain_result: Dict[str, Any]) -> Dict[str, Any]:

        """
        Parseia o resultado do EXPLAIN (TYPE IO) para extrair informações sobre tabelas, filtros e custos
        
        Estrutura do JSON retornado pelo Trino:
        {
          "inputTableColumnInfos": [{
            "table": {
              "catalog": "iceberg",
              "schemaTable": {
                "schema": "prod_db_transient_ref",
                "table": "transient_caf_executions"
              }
            },
            "constraint": {
              "none": false,
              "columnConstraints": [{
                "columnName": "date",
                "type": "timestamp(6)",
                "domain": {
                  "ranges": [...]
                }
              }]
            },
            "estimate": {
              "outputRowCount": 1150371.0,
              "outputSizeInBytes": 3.3055640450000005E9,
              "cpuCost": 3.3055640450000005E9,
              "maxMemory": 0.0,
              "networkCost": 0.0
            }
          }],
          "estimate": {...}
        }
        """

        tables_info = {}

        total_size_bytes = 0

        total_rows = 0

        total_cpu_cost = 0

        
        input_tables = explain_result.get('inputTableColumnInfos', [])

        for table_info in input_tables:

                                                                                
            table_obj = table_info.get('table', {})

            catalog = table_obj.get('catalog', '')

            
            schema_table = table_obj.get('schemaTable', {})

            schema = schema_table.get('schema', '')

            table = schema_table.get('table', '')

            
            if not catalog:

                catalog = table_info.get('catalog', '')

            if not schema:

                schema = table_info.get('schema', '')

            if not table:

                table = table_info.get('table', '')

            
            if catalog and schema and table:

                full_table_name = f"{catalog}.{schema}.{table}"

                
                estimate = table_info.get('estimate', {})

                
                def safe_float(value):

                    if value == "NaN" or value is None:

                        return 0.0

                    try:

                        return float(value)

                    except (ValueError, TypeError):

                        return 0.0

                
                estimated_size_bytes = safe_float(estimate.get('outputSizeInBytes', 0))

                estimated_rows = safe_float(estimate.get('outputRowCount', 0))

                cpu_cost = safe_float(estimate.get('cpuCost', 0))

                
                constraints = table_info.get('constraint', {})

                column_constraints = constraints.get('columnConstraints', [])

                
                filters = []

                for constraint in column_constraints:

                    column_name = constraint.get('columnName', '')

                    domain = constraint.get('domain', {})

                    ranges = domain.get('ranges', [])

                    
                    for range_obj in ranges:

                        low = range_obj.get('low', {})

                        high = range_obj.get('high', {})

                        
                        filter_info = {

                            'column': column_name,

                            'low_value': low.get('value'),

                            'low_bound': low.get('bound'),

                            'high_value': high.get('value'),

                            'high_bound': high.get('bound')

                        }

                        filters.append(filter_info)

                
                tables_info[full_table_name] = {

                    'catalog': catalog,

                    'schema': schema,

                    'table': table,

                    'estimated_size_bytes': estimated_size_bytes,

                    'estimated_rows': estimated_rows,

                    'cpu_cost': cpu_cost,

                    'filters': filters,

                    'column_constraints': column_constraints

                }

                
                total_size_bytes += estimated_size_bytes

                total_rows += estimated_rows

                total_cpu_cost += cpu_cost

                
                logger.info(f"Tabela: {full_table_name}")

                logger.info(f"  Tamanho estimado: {estimated_size_bytes:,.0f} bytes ({estimated_size_bytes / (1024**3):.2f} GB)")

                logger.info(f"  Linhas estimadas: {estimated_rows:,.0f}")

                logger.info(f"  Custo CPU: {cpu_cost:,.0f}")

                if filters:

                    logger.info(f"  Filtros aplicados: {len(filters)}")

        
        return {

            'tables': tables_info,

            'total_size_bytes': total_size_bytes,

            'total_rows': total_rows,

            'total_cpu_cost': total_cpu_cost,

            'raw': explain_result

        }

    
    def explain_io(self, query: str) -> Optional[Dict[str, Any]]:

        """
        Executa EXPLAIN (TYPE IO) na query e retorna informações sobre I/O e custos
        Normaliza a query adicionando o catálogo 'iceberg' quando necessário
        """

        # Normaliza a query adicionando o catálogo iceberg se necessário
        normalized_query = self._normalize_query_with_catalog(query)
        
        explain_query = f"EXPLAIN (TYPE IO) {normalized_query}"

        
        logger.info(f"Executando EXPLAIN (TYPE IO): {explain_query[:100]}...")

        
        result = self._execute_trino_query(explain_query)

        
        # Verifica se há erro no resultado
        if result and result.get('error'):
            logger.warning(f"EXPLAIN (TYPE IO) retornou erro: {result.get('error')}")
            logger.info(f"Result completo com erro: {result}")
            logger.info(f"Tentando salvar EXPLAIN com erro...")
            
            # Salva o EXPLAIN com informações de erro
            self._save_explain(query, {
                'raw': result.get('result', {}),
                'error': result.get('error'),
                'error_details': result.get('error_details'),
                'result_complete': result
            }, None, normalized_query)

            return None
        
        # Verifica se não há dados
        if not result or not result.get('data'):
            logger.warning("EXPLAIN (TYPE IO) não retornou dados")
            logger.info(f"Result completo: {result}")
            logger.info(f"Tentando salvar EXPLAIN sem dados...")
            
            # Salva o EXPLAIN mesmo sem dados para análise, incluindo o resultado completo
            self._save_explain(query, {
                'raw': result if result else {},
                'error': 'No data returned',
                'result_complete': result
            }, None, normalized_query)

            return None

        
        try:

            explain_json_str = result['data'][0][0] if result['data'] else None

            if explain_json_str:

                                                          
                explain_json_str = explain_json_str.replace('\\n', ' ').replace('\n', ' ')

                                
                explain_json = json.loads(explain_json_str)

                logger.debug(f"EXPLAIN parseado com sucesso: {len(explain_json.get('inputTableColumnInfos', []))} tabelas encontradas")
                logger.info(f"Salvando EXPLAIN parseado com {len(explain_json.get('inputTableColumnInfos', []))} tabelas...")

                parsed_result = self._parse_explain_io(explain_json)
                
                # Salva o EXPLAIN para análise posterior, incluindo o resultado completo original
                logger.info(f"Chamando _save_explain com parsed_result: {parsed_result is not None}")
                self._save_explain(query, {
                    'raw': explain_json,
                    'result_complete': result,  # Salva o resultado completo original
                    'explain_json_str': explain_json_str  # Salva a string JSON original também
                }, parsed_result, normalized_query)
                
                return parsed_result
            else:
                # Salva o EXPLAIN mesmo sem dados válidos, incluindo o resultado completo
                logger.warning(f"explain_json_str está vazio. Result completo: {result}")
                self._save_explain(query, {
                    'raw': {},
                    'result_complete': result,
                    'error': 'Empty explain_json_str'
                }, None, normalized_query)

        except (json.JSONDecodeError, IndexError, KeyError) as e:

            logger.error(f"Erro ao parsear resultado do EXPLAIN: {str(e)}")

            logger.error(f"String recebida: {explain_json_str[:200] if explain_json_str else 'None'}...")
            
            # Salva o EXPLAIN mesmo com erro para análise
            self._save_explain(query, {'raw': {}, 'error': str(e), 'explain_json_str': explain_json_str[:500] if explain_json_str else None}, None, normalized_query)

            return None

        
        return None

    
    def analyze_query_io(self, query: str) -> Dict[str, Any]:

        """
        Analisa a query usando EXPLAIN (TYPE IO) e retorna informações detalhadas sobre I/O e custos
        O EXPLAIN já fornece todas as informações necessárias: tamanho, linhas, custos e filtros aplicados
        """

                                            
        logger.info("Executando EXPLAIN (TYPE IO) no Trino...")

        explain_result = self.explain_io(query)

        
        if not explain_result:

            logger.error("Não foi possível obter resultado do EXPLAIN (TYPE IO)")

            return {

                'tables': {},

                'total_size_bytes': 0,

                'total_rows': 0,

                'total_cpu_cost': 0,

                'where_clause': None,

                'explain_result': {}

            }

        
        where_clause = self._extract_where_clause(query)

        
        tables_metadata = {}

        
        for table_name, table_info in explain_result.get('tables', {}).items():

            tables_metadata[table_name] = {

                'table': table_name,

                'file_count': 0,                                                   

                'total_size_bytes': table_info.get('estimated_size_bytes', 0),

                'total_records': int(table_info.get('estimated_rows', 0)),

                'cpu_cost': table_info.get('cpu_cost', 0),

                'filters': table_info.get('filters', []),

                'io_analysis': table_info

            }

        
        total_size = explain_result.get('total_size_bytes', 0)

        total_rows = explain_result.get('total_rows', 0)

        total_cpu_cost = explain_result.get('total_cpu_cost', 0)

        
        logger.info(f"Análise de I/O concluída: {len(tables_metadata)} tabelas, {total_size:,.0f} bytes ({total_size / (1024**3):.2f} GB), {total_rows:,.0f} linhas")

        
        return {

            'tables': tables_metadata,

            'total_size_bytes': total_size,

            'total_rows': total_rows,

            'total_cpu_cost': total_cpu_cost,

            'where_clause': where_clause,

            'explain_result': explain_result

        }

    
    def _extract_where_clause(self, query: str) -> Optional[str]:

        """
        Extrai a cláusula WHERE da query original (para referência)
        """

        query_lower = query.lower()

        where_match = re.search(r'\bwhere\s+(.+?)(?:\s+group\s+by|\s+order\s+by|\s+limit|$)', query_lower, re.IGNORECASE | re.DOTALL)

        
        if where_match:

                                                                                   
            where_start = query_lower.find('where')

            if where_start != -1:

                                                    
                remaining = query[where_start + 5:]                         

                                                  
                for keyword in ['group by', 'order by', 'limit']:

                    keyword_pos = remaining.lower().find(keyword)

                    if keyword_pos != -1:

                        remaining = remaining[:keyword_pos]

                return remaining.strip()

        
        return None

    
    def extract_tables(self, query):

        """
        Extrai nomes de tabelas da consulta SQL (método legado, mantido para compatibilidade)
        """

        explain_result = self.explain_io(query)

        
        if explain_result and explain_result.get('tables'):

            return list(explain_result['tables'].keys())

        
        tables = []

        patterns = [

            r'from\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)',

            r'join\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)',

        ]

        
        query_lower = query.lower()

        for pattern in patterns:

            matches = re.finditer(pattern, query_lower, re.IGNORECASE)

            for match in matches:

                table = match.group(1)

                table = table.split()[0]

                if table not in tables:

                    tables.append(table)

        
        return tables

    
    def analyze_complexity(self, query):

        """
        Analisa a complexidade estrutural da consulta SQL a partir da AST
        gerada pelo sqlglot, em vez de expressões regulares sobre o texto.

        As agregações são contabilizadas apenas na lista de projeção do
        SELECT principal (ignorando reocorrências em HAVING ou em
        subconsultas), e os filtros do WHERE de nível superior são
        agrupados pelas colunas referenciadas, de modo que múltiplas
        condições sobre a mesma coluna (ex.: um intervalo de datas) sejam
        contadas como um único filtro.
        """

        try:
            tree = sqlglot.parse_one(query, dialect="trino")
        except Exception as e:
            logger.warning(f"Falha ao parsear a consulta com sqlglot: {str(e)}")
            return {
                'joins': 0,
                'aggregations': 0,
                'subqueries': 0,
                'partitioned_filters': 0,
                'non_partitioned_filters': 0
            }

        joins = len(list(tree.find_all(exp.Join)))

        aggregations = sum(
            len(list(projection.find_all(exp.AggFunc)))
            for projection in tree.expressions
        )

        subqueries = len(list(tree.find_all(exp.Subquery)))

        partitioned_filters = 0
        non_partitioned_filters = 0

        top_where = tree.args.get('where')
        if top_where is not None:

            def flatten_and(node):
                if isinstance(node, exp.And):
                    return flatten_and(node.this) + flatten_and(node.expression)
                return [node]

            condition_groups = {}
            for condition in flatten_and(top_where.this):
                columns = frozenset(col.name for col in condition.find_all(exp.Column))
                condition_groups.setdefault(columns, []).append(condition)

            for columns in condition_groups:
                if columns & self.partition_columns:
                    partitioned_filters += 1
                else:
                    non_partitioned_filters += 1

        complexity = {

            'joins': joins,

            'aggregations': aggregations,

            'subqueries': subqueries,

            'partitioned_filters': partitioned_filters,

            'non_partitioned_filters': non_partitioned_filters

        }


        logger.debug(f"Complexidade analisada: {complexity}")

        return complexity

