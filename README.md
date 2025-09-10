# Document Extraction API

API para extração de dados estruturados de documentos brasileiros (imagens e PDFs) usando modelos GPT da OpenAI.

## Funcionalidades
- Extração de dados de documentos: RG, CNH, Passaporte, Cartão CNPJ, Certidões, Comprovantes de Endereço, entre outros.
- Suporte a imagens (JPG, PNG, GIF, BMP, TIFF, WebP) e PDFs.
- Chave OpenAI dinâmica via header (`X-OpenAI-Key`).
- Tracking de custos e uso por chave.
- Campos padronizados e prompts otimizados por tipo de documento.

## Instalação

1. Clone o repositório:
   ```bash
   git clone <repo-url>
   cd image-extractor
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure as variáveis de ambiente (opcional, padrão: PostgreSQL local):
   - `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

## Execução

```bash
uvicorn main:app --host 0.0.0.0 --port 5556 --reload
```

Acesse: [http://localhost:5556/docs](http://localhost:5556/docs) para a documentação interativa.

## Exemplos de Uso

### Extração via arquivo
```bash
curl -X POST "http://localhost:5556/extract" \
     -H "X-OpenAI-Key: sk-sua-chave-aqui" \
     -F "file=@documento.jpg" \
     -F "document_type=identidade"
```

### Extração via URI
```bash
curl -X POST "http://localhost:5556/extract-uri" \
     -H "X-OpenAI-Key: sk-sua-chave-aqui" \
     -H "Content-Type: application/json" \
     -d '{"image_uri": "https://exemplo.com/doc.jpg", "document_type": "cartao_cnpj"}'
```

### Listar tipos de documentos suportados
```bash
curl http://localhost:5556/document-types
```

## Endpoints Principais
- `POST /extract` — Extrai dados de um arquivo enviado.
- `POST /extract-uri` — Extrai dados de um arquivo via URL.
- `GET /document-types` — Lista tipos de documentos suportados.
- `GET /extractions/{id}` — Busca extração salva por ID.

## Banco de Dados
- Utiliza PostgreSQL (configurável via `.env`).
- Tabela principal: `document_extractions`.

## Estrutura do Projeto
- `main.py` — API FastAPI.
- `controller/` — Lógica de controle e orquestração.
- `service/` — Serviços de extração e integração com OpenAI.
- `model/` — Modelos ORM e schemas Pydantic.
- `config/` — Configuração de tipos de documentos.
- `repository/` — Conexão com banco de dados.
- `utils/` — Utilitários e logger.

## Observações
- É necessário possuir uma chave OpenAI válida (começando com `sk-`).
- O custo da extração é calculado e retornado na resposta.
- Logs são salvos em `logs/app.log`.

## Licença
MIT

