# Especificação do painel (`painel.json`)

Um único arquivo JSON descreve o painel inteiro: de onde vêm os dados, as medidas e as páginas com seus visuais. O gerador confere tudo antes de gravar e lista os problemas encontrados.

## Estrutura geral

```json
{
  "nome": "PainelMunicipios",
  "titulo": "Municípios: PIB por habitante e IDEB",
  "tabela": "Municipios",
  "csv": "../dados/municipios.csv",
  "separador": ",",
  "colunas": { "uf": "texto", "populacao": "inteiro", "ideb_anos_iniciais": "decimal" },
  "colunas_calculadas": [],
  "medidas": [],
  "paginas": []
}
```

| Campo | O que é |
|---|---|
| `nome` | Nome do arquivo `.pbip`. Letras sem acento, números e `_`, começando com letra. |
| `titulo` | Nome do painel, mostrado no Power BI. |
| `tabela` | Nome da tabela de dados no modelo. Mesmas regras de `nome`. É o nome usado no DAX. |
| `csv` | Caminho do CSV, **relativo à pasta do `painel.json`**. Codificação UTF-8. |
| `separador` | Separador de colunas do CSV. Padrão: vírgula. |
| `colunas` | Colunas do CSV usadas no painel, com o tipo: `"texto"`, `"inteiro"` ou `"decimal"`. As outras são ignoradas. Códigos (como o do IBGE) são `"texto"`. |
| `colunas_calculadas` | Opcional. Colunas novas, calculadas linha a linha em DAX. |
| `medidas` | Os números do painel, em DAX. Ao menos uma. |
| `paginas` | As páginas do painel, cada uma com seus visuais. |

Números no CSV usam ponto decimal e não têm separador de milhar. Campo vazio vira vazio no Power BI, nunca zero.

## Medidas

```json
{"nome": "PIB por habitante (R$)", "dax": "DIVIDE(SUM(Municipios[pib_mil_reais]) * 1000, SUM(Municipios[populacao]))", "formato": "#,0"}
```

Uma medida é uma fórmula que o Power BI recalcula para cada recorte: o país inteiro, uma UF, um município. Escreva-a em uma única linha.

| Para calcular | DAX |
|---|---|
| Quantas linhas | `COUNTROWS(Municipios)` |
| Soma | `SUM(Municipios[populacao])` |
| Média simples (ignora vazios) | `AVERAGE(Municipios[ideb_anos_iniciais])` |
| Razão entre somas | `DIVIDE(SUM(Municipios[a]), SUM(Municipios[b]))` |
| Quantos vazios | `COUNTROWS(FILTER(Municipios, ISBLANK(Municipios[coluna])))` |
| Usar outra medida | `[Nome da medida] * 100` |

`DIVIDE` devolve vazio quando o divisor é zero, em vez de erro. Uma razão entre somas é ponderada: o PIB por habitante de uma UF é o PIB da UF dividido pela população da UF, e não a média dos municípios.

Formatos comuns: `#,0` (inteiro com separador de milhar), `#,0.0` (uma casa), `0.0` (uma casa, sem milhar), `0.0%` (percentual de uma razão entre 0 e 1). O Power BI mostra vírgula ou ponto conforme o idioma do computador.

## Colunas calculadas

```json
{"nome": "municipio_uf", "dax": "Municipios[municipio] & \" - \" & Municipios[uf]", "tipo": "texto"}
```

Úteis para rótulos. No projeto do curso, há municípios com o mesmo nome em UFs diferentes, e um gráfico por `municipio` os juntaria numa barra só. Para somar ou contar, use medidas, não colunas calculadas.

## Páginas

```json
{
  "nome": "Visão geral",
  "titulo": "Municípios: PIB por habitante e IDEB",
  "subtitulo": "A pergunta que esta página responde.",
  "nota": "Fontes e anos dos dados. Ressalvas de leitura.",
  "visuais": []
}
```

`nome` é o texto da aba. `titulo`, `subtitulo` e `nota` são opcionais e viram caixas de texto fixas.

## Posição dos visuais

A página tem **1280 x 720 pixels**. Cada visual tem `"posicao": [x, y, largura, altura]`, contados a partir do canto superior esquerdo.

```
 0                                                        1280
 ┌──────────────────────────────────────────────────────────┐ 0
 │ título e subtítulo (se houver)                           │
 ├──────────────────────────────────────────────────────────┤ 96
 │                                                          │
 │ área dos visuais: de x 24 a 1256, de y 104 a 664         │
 │                                                          │
 ├──────────────────────────────────────────────────────────┤ 664
 │ nota de rodapé (se houver)                               │
 └──────────────────────────────────────────────────────────┘ 720
```

- Margem de 24 nas laterais e cerca de 16 entre visuais.
- Uma linha de cinco cartões: largura 236, x em 24, 273, 522, 771 e 1020, altura 96.
- Duas colunas iguais: largura 608, x em 24 e 648.
- O gerador recusa visuais sobrepostos, fora da página ou sobre o cabeçalho e a nota.

## Tipos de visual

Todos aceitam `titulo` (obrigatório, exceto em `texto`), `subtitulo` e `posicao`. Os campos se referem a colunas e medidas pelo nome.

| `tipo` | Para quê | Campos |
|---|---|---|
| `cartao` | Um número em destaque | `medida` |
| `barras` | Comparar categorias, barras deitadas | `categoria` (coluna), `valor` (medida); opcionais `serie` (coluna), `top` (número), `ordenar` (`"valor"` ou `"categoria"`) |
| `colunas` | Comparar categorias ou anos, barras em pé | os mesmos de `barras` |
| `linhas` | Evolução no tempo | `categoria` (coluna, como o ano), `valor` (medida ou lista de medidas); opcional `serie` |
| `dispersao` | Relação entre duas medidas | `detalhe` (coluna: cada ponto), `x` e `y` (medidas); opcionais `tamanho` (medida), `legenda` (coluna), `escala_log` (`true` para o eixo horizontal) |
| `tabela` | Os valores exatos | `campos`: lista de colunas e medidas |
| `segmentacao` | Filtro em lista suspensa | `campo` (coluna) |
| `texto` | Um texto fixo | `texto` (texto ou lista de parágrafos); opcional `tamanho_fonte`, como `"11pt"` |

`top` mostra só as N categorias com maior valor, como "15 municípios com maior PIB por habitante". Barras e colunas vêm ordenadas do maior para o menor valor, a menos que `ordenar` seja `"categoria"`.

Clicar em uma barra ou escolher um item na segmentação filtra os outros visuais da página.

## Mensagens de erro comuns

| Mensagem | O que fazer |
|---|---|
| A coluna 'x' não existe no CSV. Você quis dizer 'y'? | Corrija o nome em `colunas`. |
| A linha N do CSV tem '...' | A coluna não é do tipo declarado. Mude o tipo ou prepare um CSV limpo. |
| 'x' não é coluna nem medida | O visual cita um nome que não foi declarado. |
| 'valor' precisa ser uma medida | Crie uma medida, como `SUM(Tabela[coluna])`, e use-a no visual. |
| se sobrepõe a | Ajuste `posicao`. |
| Já existe um painel gerado | Use `--force` para gerar de novo. |
