import httpx
import uvicorn
from fastapi import FastAPI, UploadFile, Depends, Header, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import os
import logging
from logging.handlers import TimedRotatingFileHandler

from src_moreno.model.schemas import DocumentTypesResponse, ExtractionResponse, UriExtractionRequest
from src_moreno.repository.database import SessionLocal, engine
from src_moreno.model.models import Base, DocumentExtraction
from src_moreno.controller.extraction_controller import process_document_extraction, get_document_types_info

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'app.log')

file_handler = TimedRotatingFileHandler(LOG_FILE, when='D', interval=60, backupCount=6, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s')
file_handler.setFormatter(file_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(file_formatter)

logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])
logger = logging.getLogger("api_logger")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Document Extraction API",
    description="API para extração de dados de documentos usando GPT",
    version="2.0.0"
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def validate_openai_key(x_openai_key: str = Header(..., alias="X-OpenAI-Key")) -> str:
    """
    Valida a chave OpenAI fornecida no header da requisição.

    Args:
        x_openai_key (str): Chave OpenAI fornecida no header X-OpenAI-Key

    Returns:
        str: Chave OpenAI validada

    Raises:
        HTTPException: Se a chave for inválida ou não fornecida

    Note:
        A chave deve começar com 'sk-' para ser considerada válida
    """
    if not x_openai_key or not x_openai_key.startswith('sk-'):
        raise HTTPException(
            status_code=401,
            detail="Chave OpenAI inválida. Forneça uma chave válida no header X-OpenAI-Key"
        )
    return x_openai_key

@app.get("/")
async def root():
    """
    Endpoint raiz que retorna informações básicas sobre a API.

    Returns:
        dict: Informações sobre a API, versão e endpoints disponíveis
    """
    return {
        "message": "Document Extraction API",
        "version": "2.0.0",
        "endpoints": {
            "extract": "POST /extract - Extrai dados de arquivo enviado",
            "extract_uri": "POST /extract-uri - Extrai dados de arquivo via URI",
            "document_types": "GET /document-types - Lista tipos de documentos disponíveis"
        }
    }

@app.get("/document-types", response_model=DocumentTypesResponse)
async def get_document_types():
    """
    Lista todos os tipos de documentos disponíveis e seus campos.

    Returns:
        DocumentTypesResponse: Informações detalhadas sobre os tipos de documentos,
                              incluindo campos esperados, tipos de dados e descrições

    Example:
        GET /document-types

        Response:
        {
            "available_types": {
                "identidade": {
                    "name": "identidade",
                    "description": "Documento de identidade (RG, CNH, Passaporte)",
                    "fields": [...]
                }
            },
            "total_types": 6
        }
    """
    return get_document_types_info()

@app.post("/extract", response_model=ExtractionResponse)
async def extract_document(
    file: UploadFile,
    document_type: Optional[str] = Form(None, description="Tipo do documento (opcional)"),
    openai_key: str = Depends(validate_openai_key),
    db: Session = Depends(get_db)
):
    """
    Extrai dados de um documento (imagem ou PDF)

    - **file**: Arquivo a ser processado (imagem ou PDF)
    - **document_type**: Tipo do documento (opcional). Se não informado, será detectado automaticamente
    - **X-OpenAI-Key**: Chave da API OpenAI (obrigatório no header)

    Tipos de documento disponíveis:
    - identidade: RG, CNH, Passaporte
    - cartao_cnpj: Cartão CNPJ da Receita Federal
    - certidao_nascimento: Certidão de Nascimento
    - generico: Detecção automática do tipo
    """

    file_data = await file.read()

    if len(file_data) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    # Log da operação (sem expor a chave)
    logger.info(f"Processando extração - arquivo: {file.filename}, tipo: {document_type or 'auto'}, tamanho: {len(file_data)} bytes")

    result = process_document_extraction(
        file_data=file_data,
        filename=file.filename,
        document_type=document_type,
        openai_api_key=openai_key,
        db=db
    )

    logger.info(f"Extração concluída - ID: {result['id']}, tokens: {result['tokens']['total']}, custo: ${result['cost_usd']:.4f}")

    return result

@app.post("/extract-uri", response_model=ExtractionResponse)
async def extract_from_uri(
    request: UriExtractionRequest,
    openai_key: str = Depends(validate_openai_key),
    db: Session = Depends(get_db)
):
    """
    Extrai dados de um documento através de uma URI

    - **image_uri**: URL da imagem a ser processada
    - **document_type**: Tipo do documento (opcional). Se não informado, será detectado automaticamente
    - **X-OpenAI-Key**: Chave da API OpenAI (obrigatório no header)
    """

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(request.image_uri)
            resp.raise_for_status()
            file_data = resp.content
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"Erro ao baixar arquivo da URI: {e.response.status_code}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Erro de conexão ao baixar arquivo: {str(e)}")

    if len(file_data) == 0:
        raise HTTPException(status_code=400, detail="Arquivo baixado está vazio")

    # Extrair nome do arquivo da URI para detecção de tipo
    filename = request.image_uri.split('/')[-1].split('?')[0] if '/' in request.image_uri else None

    logger.info(f"Processando extração via URI - URL: {request.image_uri}, tipo: {request.document_type or 'auto'}, tamanho: {len(file_data)} bytes")

    result = process_document_extraction(
        file_data=file_data,
        filename=filename,
        document_type=request.document_type,
        openai_api_key=openai_key,
        db=db
    )

    logger.info(f"Extração via URI concluída - ID: {result['id']}, tokens: {result['tokens']['total']}, custo: ${result['cost_usd']:.4f}")

    return result

@app.get("/extractions/{extraction_id}")
async def get_extraction(extraction_id: int, db: Session = Depends(get_db)):
    """Busca uma extração específica pelo ID"""
    extraction = db.query(DocumentExtraction).filter(DocumentExtraction.id == extraction_id).first()

    if not extraction:
        raise HTTPException(status_code=404, detail="Extração não encontrada")

    return {
        "id": extraction.id,
        "document_type": extraction.document_type,
        "file_type": extraction.file_type,
        "file_size_bytes": extraction.file_size_bytes,
        "extracted_data": extraction.extracted_data,
        "tokens": {
            "prompt": extraction.prompt_tokens,
            "completion": extraction.completion_tokens,
            "total": extraction.total_tokens
        },
        "cost_usd": extraction.cost_usd,
        "cost_brl": extraction.cost_brl,
        "openai_key_hash": extraction.openai_key_hash,
        "created_at": extraction.created_at
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP Error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Erro interno: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Erro interno do servidor", "status_code": 500}
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5556, reload=True)