# Document Extraction API

RPA PARA AUTOMACAO DO LANCAMENTOS DOS DOCUMENTOS DE ENTRADA DA ENERGIA.

## Funcionalidades
- Extração de dados das contas de energia em pdf

## Instalação

1. Clone o repositório:
   ```bash
   git clone <repo-url>
   cd image-extractor
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt

## Estrutura do Projeto
- `text_extractor_ocr_cabecalho.py` — extrai o cabeçalho da conta de luz
- `text_extractor_ocr_itens.py` — extrai os itens da fatura, e retorna somente o valor deles
- `text_extractor_ocr_itens.py` — extrai os atributos e as 3 colunas deles


