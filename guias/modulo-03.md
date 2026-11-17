# Módulo 3 — A primeira página com um gráfico

Nos blocos 3.4 a 3.7, você localizará os dados, abrirá a pasta do projeto e pedirá ao agente uma página com um gráfico.

## 3.4 — Arquivos, pastas e caminhos

O ZIP é o pacote que você baixa e extrai. A pasta `projeto-municipios` reúne os arquivos de trabalho. Dentro dela, `dados/municipios.csv` é o arquivo de dados. O agente criará `index.html` para mostrar o gráfico no navegador.

As pastas `.claude` e `.agents` também fazem parte do projeto e podem estar ocultas no gerenciador de arquivos. Mantenha-as: o tutor será apresentado no módulo 6.

## 3.5 — Abrir a pasta correta

Baixe o [pacote inicial](../pacotes/modulo-03-inicio.zip), extraia todos os arquivos e abra no aplicativo a pasta que contém `LEIA-ME.txt` e `dados`.

Envie este pedido ao agente:

```text
Liste os arquivos e as pastas na raiz deste projeto e dentro da pasta dados.
Confirme se você encontrou dados/municipios.csv e diga quantas linhas de municípios esse arquivo tem, sem contar o cabeçalho.
Por enquanto, apenas leia e descreva. Não crie nem altere arquivos.
```

**Checkpoint:** o agente encontra o CSV e informa 5.570 registros de municípios, sem contar o cabeçalho.

## 3.6 — Criar a página

Na mesma sessão, envie:

```text
Leia dados/municipios.csv e crie uma página chamada index.html com um gráfico de barras horizontais dos 10 municípios mais populosos dessa base.

Ordene do mais populoso para o menos populoso. Mostre o nome e a UF de cada município e a população em número de habitantes, com os valores legíveis em português.

Identifique no título que a população é de 2022 e cite o IBGE como fonte. Use os números do arquivo, sem inventar nem buscar outros dados.

A página precisa abrir diretamente no navegador, mesmo sem internet, sem instalar programas e sem iniciar um servidor. Guarde na própria página os dados necessários ao gráfico.

Preserve o arquivo CSV e as demais pastas do projeto. Ao terminar, diga qual arquivo criou e como eu posso abri-lo.
```

**Checkpoint:** abra `index.html` no navegador e confira se há dez barras, município e UF, valores, ano e fonte.

## 3.7 — Reconhecer o resultado

Envie:

```text
Liste os arquivos que você criou ou alterou para fazer o gráfico e explique, em uma frase para cada um, para que ele serve.
Mostre onde está index.html em relação à pasta dados e confirme se dados/municipios.csv foi preservado.
Por enquanto, apenas explique. Não altere mais nada.
```

**Checkpoint:** localize o HTML na pasta e abra-o novamente. O CSV é a fonte, e o HTML mostra o resultado. Se os dados mudarem depois, peça ao agente para atualizar a página.

## Se precisar retomar

- **Pasta errada:** abra a pasta que contém `LEIA-ME.txt` e `dados` antes de continuar.
- **Página vazia:** peça ao agente para corrigir a página para funcionar por abertura direta, sem servidor e sem internet, usando o CSV original.
- **Valores diferentes:** peça ao agente para conferir as dez barras contra o CSV, corrigir diferenças e preservar os dados originais.
- **Retomada no módulo seguinte:** use o [ponto de partida do módulo 4](../pacotes/modulo-04-inicio.zip). Ele contém uma página de referência preparada pelo professor.
