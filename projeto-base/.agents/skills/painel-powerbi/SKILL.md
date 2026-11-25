---
name: painel-powerbi
description: Monta um painel do Power BI Desktop (projeto .pbip) a partir de um CSV, gerando os arquivos por código a partir de uma especificação em JSON, sem clicar e arrastar. Use quando o aluno pedir um painel ou dashboard no Power BI, um arquivo .pbip, ou quiser apresentar os dados do projeto no Power BI.
argument-hint: "[pergunta que o painel deve responder]"
---

# Painel no Power BI, gerado por código

Você está ajudando um aluno do curso "Introdução a Agentes de IA — Nivelamento" a montar um painel no Power BI Desktop. O aluno não tem formação em TI. O projeto dele está nesta pasta, com os dados em `dados/`.

## O método

O painel não é montado com cliques no Power BI. Ele é descrito em um arquivo de texto, `powerbi/painel.json`, e um script gera a partir dele o projeto do Power BI (`.pbip`): o modelo de dados, em arquivos TMDL, e as páginas, em arquivos JSON. Para mudar o painel, muda-se a especificação e gera-se de novo.

Explique isso ao aluno uma vez, em poucas palavras, porque é o que o método ensina:

- **Dá para repetir.** A mesma especificação gera sempre os mesmos arquivos. Se os dados forem atualizados, basta gerar de novo.
- **Dá para revisar.** A especificação é curta e legível. O aluno confere o que pediu sem abrir o Power BI.
- **Dá para versionar.** A especificação e o projeto gerado são texto e entram no Git como qualquer outro arquivo.
- **É o tipo de trabalho em que o agente é bom:** escrever texto estruturado e conferir. Arrastar campos com o mouse não é.

## Limites

- **Não altere os dados originais.** Se o CSV precisar de ajuste (uma coluna a mais, um filtro), escreva um script em `powerbi/` que gera um CSV novo em `powerbi/`, e aponte a especificação para ele.
- **Não edite à mão os arquivos gerados** em `powerbi/pbip/`. Eles são sobrescritos na próxima geração.
- **Não invente números.** Tudo o que o painel mostra sai do CSV, por meio de medidas.
- **Grave só em `powerbi/`.** Não instale o Power BI nem mude configurações do computador. Se faltar algo, diga ao aluno o que instalar.

## Passo 1: o público e a pergunta

Antes de escrever qualquer coisa, entenda para quem é o painel e que pergunta ele responde. Se o aluno não disse, pergunte, **uma pergunta por mensagem**:

1. Quem vai ler o painel? (um gestor, um colega da área, o público em geral)
2. Que pergunta essa pessoa quer responder?
3. Quais são os três a cinco números que ela precisa ver primeiro?

Com isso, proponha em texto, antes de gerar, o desenho do painel: as páginas, os números em destaque e os gráficos, cada um com a pergunta que responde. Espere o aluno concordar.

## Passo 2: os dados

Leia a documentação dos dados (no projeto do curso, `dados/LEIA-ME.md`) e o cabeçalho do CSV. Confira:

- uma linha por unidade (município, órgão, mês), sem linhas de total;
- números com ponto decimal e sem separador de milhar;
- o significado de campos vazios. No projeto do curso, IDEB vazio é ausência de dado, não zero. A medida tem de tratar o vazio como vazio.

## Passo 3: a especificação

Escreva `powerbi/painel.json`. O formato completo, os tipos de visual e as regras de posição estão em `especificacao.md`, nesta pasta. Leia esse arquivo antes de escrever.

Para o projeto dos municípios, `exemplos/municipios.json` é um painel completo e testado sobre PIB por habitante e IDEB. Use-o como ponto de partida, mas adapte-o à pergunta do aluno. O exemplo responde a uma pergunta; o aluno pode ter outra.

Regras que evitam os erros mais comuns:

- Todo número no painel vem de uma **medida** em DAX, com nome legível e formato. Não use colunas numéricas diretamente nos visuais.
- Médias simples de municípios não são médias ponderadas pela população. Diga qual é no subtítulo do visual.
- Todo visual tem título. Em gráficos, o subtítulo diz o recorte ou a ressalva.
- Cada página tem uma nota de rodapé com as fontes e os anos dos dados.

## Passo 4: gerar

A partir da pasta do projeto, confira primeiro sem gravar:

```
python .claude/skills/painel-powerbi/scripts/gerar_pbip.py powerbi/painel.json --dry-run
```

No Codex, o mesmo script está em `.agents/skills/painel-powerbi/scripts/gerar_pbip.py`. Se `python` não for reconhecido, tente `python3` e depois `py`. O script usa só a biblioteca padrão do Python.

Se a especificação tiver problemas, o script lista todos de uma vez, em português. Corrija e rode de novo. Quando passar, gere:

```
python .claude/skills/painel-powerbi/scripts/gerar_pbip.py powerbi/painel.json
```

O projeto fica em `powerbi/pbip/`. Para gerar de novo depois de uma mudança, acrescente `--force`. Os arquivos que o aluno criou nessa pasta são preservados. Se o pacote `jsonschema` estiver instalado e houver internet, `--validar-esquemas` confere também com os esquemas oficiais da Microsoft. É opcional.

## Passo 5: conferir os números por outro caminho

O painel calcula com DAX, dentro do Power BI. Para saber se as medidas estão certas, calcule os mesmos números por outro caminho: um script Python curto que lê o CSV com o módulo `csv` e calcula cada número em destaque. Grave os valores esperados em `powerbi/conferencia.md`, um por linha, com a regra usada.

O aluno compara esse arquivo com o que aparece no Power BI. Se um número não bater, a medida ou a conferência está errada, e é preciso descobrir qual antes de seguir.

## Passo 6: abrir no Power BI Desktop

O Power BI Desktop é gratuito, está na Microsoft Store e **só roda no Windows**.

1. Abra o arquivo `powerbi/pbip/<nome>.pbip` com dois cliques.
2. Na primeira abertura, o painel aparece vazio. Clique em **Atualizar** (Refresh), na faixa de opções Página Inicial, ou em **Atualizar agora** no aviso amarelo. Os dados são lidos do CSV.
3. Se o Power BI recusar o arquivo, ative em Arquivo > Opções e configurações > Opções > Recursos de visualização: "Opção de salvar o projeto do Power BI (.pbip)" e "Armazenar relatórios usando o formato PBIR". Reinicie o Power BI.

O caminho do CSV fica gravado no projeto como caminho completo. Se a pasta do projeto mudar de lugar, ou de computador, gere de novo.

No Mac, o aluno pode gerar o projeto e conferir os números, mas precisa de um computador com Windows para abrir o painel. Lá, ele copia a pasta inteira e gera de novo, para atualizar o caminho do CSV.

## Passo 7: mudar o painel

Toda mudança passa pela especificação: o aluno pede, você altera `powerbi/painel.json` e gera de novo com `--force`. Feche o Power BI antes de gerar, ou use o aviso "Aplicar alterações externas" que ele mostra.

Mudanças feitas com o mouse no Power BI são perdidas na próxima geração. Se o aluno quiser um ajuste que a especificação não oferece, explique o limite. Para descobrir como o Power BI grava um ajuste, faça-o no Desktop, salve e compare o `visual.json` salvo com o gerado. Isso serve para estudar, não para manter o painel.

## Passo 8: versionar

Se o projeto usa Git, os arquivos a versionar são `powerbi/painel.json`, `powerbi/conferencia.md`, os scripts em `powerbi/` e a pasta `powerbi/pbip/`. O gerador cria o `.gitignore` que deixa de fora o cache local do Power BI.

## Resposta ao aluno

Ao terminar, diga em poucas linhas:

- o que o painel mostra e para quem;
- onde está o arquivo para abrir;
- os números de `conferencia.md` que ele deve encontrar na tela;
- como pedir uma mudança: dizendo o que quer ver, não onde clicar.

Frases curtas e palavras comuns. Quando um termo técnico for inevitável (medida, DAX, TMDL), explique-o na mesma frase.
