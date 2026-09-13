# -*- coding: utf-8 -*-
"""
Trino Gateway Proxy com Integração DyraSQL Core
Este proxy intercepta queries e roteia automaticamente baseado na decisão do DyraSQL Core
"""

from fastapi import FastAPI, Request, Response, HTTPException

import httpx

import logging

import os

import re

import json

from urllib.parse import urljoin

from typing import Optional


app = FastAPI(title="Trino Gateway Proxy", version="1.0.0")


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


DYRASQL_CORE_URL = os.getenv('DYRASQL_CORE_URL', 'http://dyrasql-core:5000')

TRINO_GATEWAY_URL = os.getenv('TRINO_GATEWAY_URL', 'http://trino-gateway:8080')

CLUSTER_URLS = {

    'small': os.getenv('TRINO_SMALL_URL', 'http://trino-small:8080'),

    'medium': os.getenv('TRINO_MEDIUM_URL', 'http://trino-medium:8080'),

    'large': os.getenv('TRINO_LARGE_URL', 'http://trino-large:8080')

}

FALLBACK_CLUSTER = 'small'

TIMEOUT = int(os.getenv('ROUTING_TIMEOUT', '5'))


http_client = httpx.AsyncClient(timeout=TIMEOUT)


@app.get('/health')

async def health():

    """Health check endpoint"""

    return {

        'service': 'trino-gateway-proxy',

        'status': 'healthy',

        'dyrasql_core_url': DYRASQL_CORE_URL,

        'trino_gateway_url': TRINO_GATEWAY_URL

    }


@app.post('/v1/statement')

async def route_statement(request: Request):

    """
    Intercepta queries SQL e roteia baseado na decisão do DyraSQL Core
    """

    try:

                                                 
        query = (await request.body()).decode('utf-8')

        user = request.headers.get('X-Trino-User', 'admin')

        
        if not query or not query.strip():

            raise HTTPException(status_code=400, detail='Query SQL é obrigatória')

        
        query_normalized = query.strip().upper().rstrip(';').strip()

        is_keepalive = query_normalized in ['SELECT 1', 'SELECT 1 AS KEEPALIVE', 'SELECT 1 AS 1']

        
        if is_keepalive:

            logger.debug(f"Query de keep-alive detectada: {query}")

                                                                                       
            cluster_name = FALLBACK_CLUSTER

        else:

            logger.info(f"Query recebida de {user}: {query[:100]}...")

                                                                 
            cluster_name = await get_routing_decision(query)

            
            if not cluster_name:

                logger.warning(f"Não foi possível obter decisão do DyraSQL Core, usando fallback: {FALLBACK_CLUSTER}")

                cluster_name = FALLBACK_CLUSTER

        
        cluster_url = CLUSTER_URLS.get(cluster_name)

        if not cluster_url:

            logger.error(f"Cluster '{cluster_name}' não encontrado, usando fallback: {FALLBACK_CLUSTER}")

            cluster_url = CLUSTER_URLS[FALLBACK_CLUSTER]

        
        if not is_keepalive:

            logger.info(f"Roteando query para cluster: {cluster_name} ({cluster_url})")

        
        target_url = urljoin(cluster_url, '/v1/statement')

        
        headers = {

            'Content-Type': 'text/plain',

            'X-Trino-User': user

        }

        
        for header in ['X-Trino-Catalog', 'X-Trino-Schema', 'X-Trino-Source', 'X-Trino-Client-Info']:

            if header in request.headers:

                headers[header] = request.headers[header]

        
        request_headers = headers.copy()

        request_headers['Accept-Encoding'] = 'identity'                  

        
        async with httpx.AsyncClient(

            timeout=TIMEOUT, 

            follow_redirects=True

        ) as client:

            response = await client.post(

                target_url,

                content=query,

                headers=request_headers

            )

            
            response_content = response.content.decode('utf-8')

            
            for cluster_name_sub, cluster_url in CLUSTER_URLS.items():

                                                        
                pattern_next = re.escape(cluster_url) + r'(/v1/statement/[^\"]+)'

                replacement_next = r'http://localhost:8080\1'

                response_content = re.sub(pattern_next, replacement_next, response_content)

                
                pattern_info = re.escape(cluster_url) + r'(/ui/[^\"]+)'

                replacement_info = r'http://localhost:8080\1'

                response_content = re.sub(pattern_info, replacement_info, response_content)

            
            response_headers = {}

            for key, value in response.headers.items():

                                                                               
                if key.lower() not in ['connection', 'transfer-encoding', 'content-encoding', 'content-length']:

                    response_headers[key] = value

            
            content_type = response.headers.get('Content-Type', 'application/json')

            response_headers['Content-Type'] = content_type

            
            return Response(

                content=response_content.encode('utf-8'),

                status_code=response.status_code,

                headers=response_headers,

            )

        
    except httpx.TimeoutException:

        logger.error("Timeout ao rotear query")

        raise HTTPException(status_code=504, detail='Timeout ao executar query')

    except Exception as e:

        logger.error(f"Erro ao rotear query: {str(e)}", exc_info=True)

        raise HTTPException(status_code=500, detail=f'Erro ao rotear query: {str(e)}')


@app.get('/v1/info')

async def info():

    """Endpoint de info do Trino - retorna exatamente o que o Trino retorna"""

                                            
    try:

        async with httpx.AsyncClient(

            timeout=2,

            headers={'Accept-Encoding': 'identity'}                  

        ) as client:

            response = await client.get(f"{CLUSTER_URLS[FALLBACK_CLUSTER]}/v1/info")

                                                                         
            response_headers = {}

            for key, value in response.headers.items():

                if key.lower() not in ['connection', 'transfer-encoding', 'content-encoding']:

                    response_headers[key] = value

            
            response_content = response.content.decode('utf-8')

            for cluster_name_sub, cluster_url in CLUSTER_URLS.items():

                                             
                pattern = re.escape(cluster_url) + r'(/[^\"]+)'

                replacement = r'http://localhost:8080\1'

                response_content = re.sub(pattern, replacement, response_content)

            
            return Response(

                content=response_content.encode('utf-8'),

                status_code=response.status_code,

                headers=response_headers,

            )

    except Exception as e:

        logger.warning(f"Erro ao obter info do cluster, retornando fallback: {e}")

                                                                 
        import json

        fallback_data = {

            'nodeId': 'proxy',

            'state': 'ACTIVE',

            'environment': 'production'

        }

        return Response(

            content=json.dumps(fallback_data).encode('utf-8'),

            status_code=200,

            headers={'Content-Type': 'application/json'},

        )


@app.post('/loginType')

async def login_type_post():

    """Endpoint de tipo de login - retorna que não há autenticação necessária"""

    import json

    return Response(

        content=json.dumps({'supportedTypes': []}).encode('utf-8'),

        status_code=200,

        headers={'Content-Type': 'application/json'},

    )


@app.get('/loginType')

async def login_type_get():

    """Endpoint de tipo de login - retorna que não há autenticação necessária"""

    import json

    return Response(

        content=json.dumps({'supportedTypes': []}).encode('utf-8'),

        status_code=200,

        headers={'Content-Type': 'application/json'},

    )


@app.get('/v1/statement')

async def get_statement():

    """Endpoint GET /v1/statement - alguns clientes JDBC fazem GET antes de POST"""

                                                                 
    raise HTTPException(status_code=405, detail='Method not allowed. Use POST /v1/statement to execute queries.')


@app.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS'])

async def proxy_other(path: str, request: Request):

    """
    Proxy para outros endpoints do Trino (nextUri, queries de keep-alive, etc)
    Para UI do Trino, redireciona para o Trino Gateway
    """

                                                     
    logger.info(f"Proxy other - path: '{path}', method: {request.method}, path type: {type(path)}")

                                                      
    normalized_path = path.strip('/')

    if normalized_path == 'loginType':

                                                                                
        logger.info(f"Tratando /loginType - retornando resposta vazia")

        import json

        return Response(

            content=json.dumps({'supportedTypes': []}).encode('utf-8'),

            status_code=200,

            headers={'Content-Type': 'application/json'},

        )

    
    is_ui_request = (

        path == '' or 

        path == '/' or 

        path.startswith('ui/') or 

        path.startswith('assets/') or 

        path.startswith('vendor/') or

        path.endswith('.html') or

        path.endswith('.css') or

        path.endswith('.js') or

        path.endswith('.ico')

    )

    
    if is_ui_request and request.method == 'GET':

                                                                
        gateway_ui_url = f"{TRINO_GATEWAY_URL}/{path}" if path else f"{TRINO_GATEWAY_URL}/"

        logger.debug(f"Redirecionando requisição de UI para: {gateway_ui_url}")

        
        try:

            async with httpx.AsyncClient(

                timeout=5,

                follow_redirects=True,

                headers={'Accept-Encoding': 'identity'}

            ) as client:

                response = await client.get(gateway_ui_url, params=request.query_params)

                
                response_headers = {}

                for key, value in response.headers.items():

                    if key.lower() not in ['connection', 'transfer-encoding', 'content-encoding']:

                        response_headers[key] = value

                
                return Response(

                    content=response.content,

                    status_code=response.status_code,

                    headers=response_headers,

                )

        except Exception as e:

            logger.warning(f"Erro ao redirecionar UI para gateway, tentando cluster padrão: {e}")

                                                                
    try:

                                   
        if path.startswith('/'):

            target_url = f"{CLUSTER_URLS[FALLBACK_CLUSTER]}{path}"

        else:

            target_url = f"{CLUSTER_URLS[FALLBACK_CLUSTER]}/{path}" if path else f"{CLUSTER_URLS[FALLBACK_CLUSTER]}/"

        
        headers = {}

        for key, value in request.headers.items():

                                                         
            if key.lower() not in ['host', 'content-length', 'connection', 'transfer-encoding']:

                headers[key] = value

        
        body = await request.body() if request.method in ['POST', 'PUT'] else None

        
        async with httpx.AsyncClient(

            timeout=TIMEOUT, 

            follow_redirects=True,

            headers={'Accept-Encoding': 'identity'}                  

        ) as client:

            if request.method == 'GET':

                response = await client.get(target_url, headers=headers, params=request.query_params)

            elif request.method == 'POST':

                response = await client.post(target_url, content=body, headers=headers)

            elif request.method == 'PUT':

                response = await client.put(target_url, content=body, headers=headers)

            elif request.method == 'DELETE':

                response = await client.delete(target_url, headers=headers)

            elif request.method == 'HEAD':

                response = await client.head(target_url, headers=headers)

            elif request.method == 'OPTIONS':

                response = await client.options(target_url, headers=headers)

            else:

                raise HTTPException(status_code=405, detail='Method not allowed')

            
            response_headers = {}

            for key, value in response.headers.items():

                if key.lower() not in ['connection', 'transfer-encoding', 'content-encoding']:

                    response_headers[key] = value

            
            response_content = response.content.decode('utf-8')

            for cluster_name_sub, cluster_url in CLUSTER_URLS.items():

                                             
                pattern = re.escape(cluster_url) + r'(/[^\"]+)'

                replacement = r'http://localhost:8080\1'

                response_content = re.sub(pattern, replacement, response_content)

            
            return Response(

                content=response_content.encode('utf-8'),

                status_code=response.status_code,

                headers=response_headers,

            )

    except Exception as e:

        logger.error(f"Erro ao fazer proxy para {path}: {str(e)}", exc_info=True)

        raise HTTPException(status_code=500, detail=f'Erro ao fazer proxy: {str(e)}')


async def get_routing_decision(query: str) -> Optional[str]:

    """
    Chama o DyraSQL Core para obter decisão de roteamento
    """

    try:

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:

            response = await client.post(

                f"{DYRASQL_CORE_URL}/api/v1/route",

                json={'query': query}

            )

            
            if response.status_code == 200:

                data = response.json()

                cluster = data.get('cluster')

                score = data.get('score', 0)

                cached = data.get('cached', False)

                factors = data.get('factors', {})

                
                if cached:

                    logger.info(f"CACHE: DyraSQL Core decision (cached): cluster={cluster}, score={score:.3f}")

                else:

                    logger.info(f"NEW ANALYSIS: DyraSQL Core decision: cluster={cluster}, score={score:.3f}")

                    logger.info(f"   Factors: volume={factors.get('volume', 0):.3f}, complexity={factors.get('complexity', 0):.3f}, historical={factors.get('historical', 0):.3f}")

                logger.info(f"ROUTING: Query will be executed on cluster '{cluster}'")

                return cluster

            else:

                logger.warning(f"DyraSQL Core retornou status {response.status_code}: {response.text}")

                return None

                
    except httpx.TimeoutException:

        logger.warning("Timeout ao chamar DyraSQL Core")

        return None

    except Exception as e:

        logger.error(f"Erro ao chamar DyraSQL Core: {str(e)}", exc_info=True)

        return None


@app.on_event("startup")

async def startup_event():

    """Evento de inicialização"""

    logger.info(f"Iniciando Trino Gateway Proxy")

    logger.info(f"DyraSQL Core URL: {DYRASQL_CORE_URL}")

    logger.info(f"Trino Gateway URL: {TRINO_GATEWAY_URL}")


@app.on_event("shutdown")

async def shutdown_event():

    """Evento de encerramento"""

    await http_client.aclose()


if __name__ == '__main__':

    import uvicorn

    port = int(os.getenv('PORT', '8080'))

    uvicorn.run(app, host='0.0.0.0', port=port)

