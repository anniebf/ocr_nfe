# Document Extraction API - Contas de Energia

Automação RPA  para o processamento e lançamento de documentos de entrada de energia elétrica.

Este projeto tem como objetivo **extrair de forma automatizada informações de faturas de energia elétrica em PDF**, garantindo maior eficiência na integração desses dados em sistemas internos ou bancos de dados corporativos.

## Confguracoes do python 
-Versão do python: 3.12

## Funcionalidades

- **Extração de dados do cabeçalho da fatura**:
  - Nome do titular (ainda nao teminado)
  - Distribuidora de energia
  - CNPJ da distribuidora
  - Número e série da nota fiscal
  - Código do cliente
  - Data de emissão
  - Chave de acesso
  - Valor total da fatura
- **Extração detalhada dos itens da fatura**:
  - Consumo e custo
  - Energia injetada
  - Bandeiras tarifárias
  - Taxa de iluminacao publica
- **Extração dos Atributos**:
  - ICMS
  - CONFINS
  - PIS

- **Saída estruturada em JSON no prompt de comando**
  - Melhoria futura - retornar o json em uma pasta especifica

## Funcionalidades

- **iNTEGRACAO COM O BANCO PARA INSERÇÃO DOS INFROMACOES**
- ** **


├─ src/
│ ├─ main/
│ │ ├─ text_extractor_ocr_cabecalho.py      # Extrai cabeçalho da fatura
│ │ ├─ text_extractor_ocr_itens.py          # Extrai valores monetários
│ │ ├─ text_extractor_ocr_itens_atributos.py # Extrai atributos (ICMS, PIS, etc.)
│ │ └─ __init__.py                          # Tornar a pasta um módulo Python
│ │
│ ├─ resource/
│ │ ├─ pdf/   

## Estrutura do Projeto

