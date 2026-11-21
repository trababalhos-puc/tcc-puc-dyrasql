# Roteiro do pitch - DyraSQL

Autor: Aristides Henrique Gonçalves da Cruz  
Orientador: Gustavo Luís Soares  
PUC Minas - Sistemas de Informação

Tempo planejado: **6 minutos**, com pausas breves e leitura natural. Grave os slides 1 a 12; os slides seguintes são apoio. O tempo é uma orientação para ensaio, não uma duração já medida de vídeo.

| Slide | Intervalo | Duração |
|---|---|---|
| 1. Apresentação | 0:00-0:20 | 20 s |
| 2. Contexto e motivação | 0:20-0:55 | 35 s |
| 3. Objetivo | 0:55-1:20 | 25 s |
| 4. Referencial teórico | 1:20-2:00 | 40 s |
| 5. Metodologia | 2:00-2:40 | 40 s |
| 6. Algoritmo | 2:40-3:15 | 35 s |
| 7. Decisões | 3:15-3:45 | 30 s |
| 8. API e cache | 3:45-4:15 | 30 s |
| 9. Testes | 4:15-4:45 | 30 s |
| 10. Limitações | 4:45-5:15 | 30 s |
| 11. Próximas atividades | 5:15-5:40 | 25 s |
| 12. Encerramento | 5:40-6:00 | 20 s |

## 1. Apresentação

Olá, eu sou Aristides Henrique Gonçalves da Cruz, aluno de Sistemas de Informação da PUC Minas. Este é o DyraSQL, meu trabalho de conclusão de curso, orientado pelo professor Gustavo Luís Soares. A proposta é realizar o roteamento dinâmico de consultas SQL com base em metadados de tabelas Apache Iceberg.

## 2. Contexto e motivação

Em um data lake, os dados podem ficar armazenados em uma camada de objetos, enquanto o processamento acontece em ambientes separados. Isso permite consultar o mesmo conjunto de dados com capacidades computacionais diferentes. Entretanto, as consultas também são diferentes: algumas leem poucos dados, enquanto outras exigem junções, agregações e maior processamento. Usar sempre o mesmo ambiente pode reservar capacidade excessiva para operações simples ou limitar operações complexas. A pesquisa investiga como selecionar essa capacidade antes da execução.

## 3. Objetivo

O objetivo é desenvolver um mecanismo de decisão que combine informações dos dados e da própria consulta SQL. Para isso, o trabalho organiza a extração de estimativas, define uma regra de pontuação e implementa um protótipo com três destinos: small, medium e large. A contribuição inclui uma lógica explícita, que pode ser inspecionada, configurada e verificada por testes.

## 4. Referencial teórico

O referencial reúne três tecnologias. O Apache Iceberg organiza as tabelas por meio de snapshots, manifestos e estatísticas. O Trino fornece execução SQL e o comando EXPLAIN TYPE IO, que apresenta os objetos acessados e estimativas do plano. Essas estimativas não são uma medição dos bytes físicos efetivamente lidos. O Trino Gateway oferece um ponto de entrada para múltiplos clusters. Como trabalho relacionado, Strausz e colaboradores investigam a seleção de engines com modelos de custo aprendidos. O DyraSQL adota uma regra de pontuação para capacidades distintas do mesmo motor.

## 5. Metodologia

A metodologia é aplicada, com desenvolvimento e verificação experimental de um protótipo. A consulta chega pelo cliente ou proxy e recebe uma identificação chamada fingerprint. O histórico é consultado para verificar se existe uma decisão reutilizável. Na ausência de cache, o fluxo analisa a estrutura SQL, solicita as informações de entrada e saída ao Trino e calcula a pontuação. A decisão pode ser registrada no PostgreSQL. Na arquitetura proposta, os ambientes Trino acessam um catálogo Iceberg e o armazenamento MinIO compartilhados. O diagrama representa esse desenho, não uma comprovação de que todos esses serviços estão ativos nesta coleta.

## 6. Algoritmo

O score combina três fatores: volume, com peso de cinquenta por cento; complexidade, com trinta por cento; e histórico, com vinte por cento. O volume considera tamanho e quantidade estimada de linhas. A complexidade considera operações e filtros da consulta. O histórico complementa a decisão quando disponível. Scores abaixo de zero vírgula três selecionam small. De zero vírgula três até zero vírgula sete, incluindo os limites, selecionam medium. Acima disso, selecionam large. Os pesos são configuráveis, mas não são aprendidos automaticamente nesta implementação.

## 7. Execução das decisões

Este print mostra a saída real do algoritmo executado localmente, com entradas controladas. Foram preparados três cenários para exercitar as três faixas. O exemplo intermediário usa um vírgula vinte e cinco gibibytes e dois milhões e meio de registros como valores de entrada. Ele produziu score aproximado de zero vírgula quarenta e quatro e selecionou medium. Os outros dois cenários selecionaram small e large. Isso demonstra o cálculo e a seleção, sem afirmar que esses volumes foram carregados em tabelas reais nesta execução.

## 8. API e cache

A aplicação FastAPI também foi exercitada por requisições em processo, usando o TestClient. O endpoint de saúde retornou HTTP duzentos. A primeira requisição de roteamento retornou medium, com cache falso. Na repetição, uma decisão controlada foi fornecida pelo histórico e a API retornou cache verdadeiro. É importante delimitar o teste: a aplicação foi executada, mas as respostas do Trino e do PostgreSQL foram simuladas. Portanto, este resultado verifica o fluxo da API, sem medir persistência real ou latência desses serviços.

## 9. Testes automatizados

Além das demonstrações, executei a suíte automatizada do projeto. Os quarenta e três testes focados em decisão, análise SQL e API passaram no Windows. A execução completa nesse ambiente encontrou falhas de codificação e de compatibilidade com scripts shell. Por isso, a suíte também foi executada no Ubuntu pelo WSL, com seu resultado preservado neste slide e nos logs. A cobertura representa as linhas exercitadas pelos testes; ela não é uma medida de precisão das decisões nem de ganho de desempenho.

## 10. Limitações

A principal limitação desta coleta foi a inicialização da infraestrutura integrada. O download das imagens MinIO foi negado pelo registro, interrompendo o Docker Compose. Assim, não apresento novas medições de execução distribuída, custo, consumo de memória ou tempo de EXPLAIN. As evidências disponíveis comprovam a execução local da lógica e da API com dependências controladas. Uma avaliação integrada continua necessária para quantificar desempenho e comparar o roteamento com um destino fixo.

## 11. Próximas atividades

Como o artigo já está finalizado, as próximas atividades para esta entrega são revisar os slides e as evidências com o orientador, ensaiar a apresentação e realizar a gravação entre cinco e sete minutos. Depois, o vídeo será publicado no YouTube como não listado, e seu endereço será informado em PDF. A submissão depende da autorização prévia do orientador. O cronograma é apresentado por etapas porque a data de entrega não foi informada nesta preparação.

## 12. Encerramento

O DyraSQL apresenta um protótipo de roteamento com critérios explícitos de volume, estrutura SQL e histórico. A coleta preserva testes, entradas e respostas para permitir a conferência dos resultados locais. Como continuidade técnica, fica a reprodução da infraestrutura e a avaliação de desempenho e custo em cargas controladas. Obrigado.

## Ensaio

Faça uma leitura cronometrada dos slides 1 a 12. Se ultrapassar 7 minutos, reduza as descrições dos slides 4 e 5 e comente apenas o resultado principal de cada print. Se ficar abaixo de 5 minutos, explique os fatores do exemplo intermediário no slide 7. Mantenha os qualificadores sobre dados controlados e serviços simulados.
