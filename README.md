# Introdução a Agentes de IA — Nivelamento

Materiais para acompanhar as atividades do curso do IDP.

## Comece pelo módulo 3

**[Baixar o projeto inicial do módulo 3 (.zip)](https://github.com/alexlopespereira/idp-nivelamento-agentes/raw/refs/heads/main/pacotes/modulo-03-inicio.zip)**

1. Baixe e extraia todos os arquivos do ZIP.
2. Localize a pasta `projeto-municipios`, que contém `LEIA-ME.txt` e a pasta `dados`.
3. Abra essa pasta no aplicativo do agente e acompanhe a aula.

O pacote inicial contém os dados, o tutor e a skill do painel no Power BI, sem o gráfico pronto. Você criará `index.html` na atividade. Para esses primeiros blocos, use o aplicativo do agente já instalado, uma conta conectada e um navegador. Python será instalado no módulo 4.

Consulte o [guia dos blocos 3.4 a 3.7](guias/modulo-03.md) para os pedidos ao agente e os checkpoints.

## Pacotes disponíveis

| Pacote | Quando usar |
|---|---|
| [Módulo 3: projeto inicial](https://github.com/alexlopespereira/idp-nivelamento-agentes/raw/refs/heads/main/pacotes/modulo-03-inicio.zip) | Para começar o projeto e criar o primeiro gráfico durante a aula. |
| [Módulo 4: ponto de partida](https://github.com/alexlopespereira/idp-nivelamento-agentes/raw/refs/heads/main/pacotes/modulo-04-inicio.zip) | Se precisar retomar o curso a partir do módulo 4, com a página de referência já incluída. |

O segundo pacote contém uma página preparada pelo professor para retomada. O objetivo da atividade do módulo 3 continua sendo produzir sua própria página com o agente.

## Dados, tutor e painel

A base reúne as 5.570 unidades de nível municipal do IBGE em 2022, incluindo Brasília e Fernando de Noronha. População e PIB são de 2022, e o IDEB da rede pública é de 2023. Campos vazios de IDEB não significam zero. Consulte as [fontes, unidades e limitações](projeto-base/dados/LEIA-ME.md).

As pastas `.claude` e `.agents` contêm o tutor, apresentado no módulo 6, e devem ser mantidas na pasta extraída.

## Painel no Power BI

As mesmas pastas trazem a skill `painel-powerbi`, usada no módulo 11. Você pede o painel ao agente; ele escreve uma especificação em `powerbi/painel.json` e um script gera o projeto do Power BI (`.pbip`) por código, sem arrastar visuais.

- [Instruções da skill](projeto-base/.claude/skills/painel-powerbi/SKILL.md)
- [Formato da especificação](projeto-base/.claude/skills/painel-powerbi/especificacao.md)
- [Exemplo com os dados do curso](projeto-base/.claude/skills/painel-powerbi/exemplos/municipios.json)

O script usa apenas o Python, instalado no módulo 4. Para abrir o painel, é preciso o Power BI Desktop, que só roda no Windows. No Mac, você gera o projeto e confere os números, mas não abre o painel.

## Organização

- `pacotes/`: arquivos ZIP para baixar.
- `projeto-base/`: arquivos que compõem o pacote inicial, disponíveis para consulta e versionamento.
- `guias/`: orientações das atividades.
- `SHA256SUMS`: hashes dos pacotes para conferência de integridade.

Os pacotes passam por uma validação automática de integridade, dados e conteúdo a cada pull request.
