import os
import json
import pytesseract
from pdf2image import convert_from_path
from openai import OpenAI
import base64
import pdfplumber
import fitz  # PyMuPDF

pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
key = base64.b64decode('')
# Configure sua chave da OpenAI
client = OpenAI(api_key='')

PASTA_PDFS = r"C:\bf_ocr\src\resource\pdf"

PROMPT_TEMPLATE = """
Você é um sistema de OCR inteligente.
Extraia os dados do comprovante de endereço.

Campos a extrair:
- nome_titular
- cpf_cnpj_titular
- distribuidora_energia
- cnpj_distribuidora_energia
- cep
- cidade
- uf
- numero_nota_fiscal
- serie_nota_fiscal
- chave_acesso
- tipo_nota_fiscal
- codigo_do_cliente
- numero_nota_fiscal
- empresa_prestadora
- data_vencimento
- data_emissao
- valor_total

Verifique se alguma grandeza está com a leitura em 0 e caso ocorra informe qual é a grandeza que não está zerada no campo grandeza.
Pegue somente o valor da grandeza que não está zerada.
Pegue o codigo do cliente sem formatar aas informacoes.
Campos ausentes devem ser null.
Retorne apenas no formato JSON puro.
"""

def extrair_texto_pdf(pdf_path):
    texto = ""
    with pdfplumber.open(pdf_path) as pdf:
        for pagina in pdf.pages:
            t = pagina.extract_text()
            if t:
                texto += t + "\n"
    #print(texto)
    return texto

resultados = []

for arquivo in os.listdir(PASTA_PDFS):

    if arquivo.lower().endswith(".pdf"):
        caminho_pdf = os.path.join(PASTA_PDFS, arquivo)
        print(f"Processando: {arquivo}")

        texto_pdf = extrair_texto_pdf(caminho_pdf)

        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "Você é um assistente que converte comprovantes PDF em JSON estruturado."},
                    {"role": "user", "content": f"{PROMPT_TEMPLATE}\n\nTexto do PDF:\n{texto_pdf}"}
                ],
                temperature=0,
            )

            json_texto = response.choices[0].message.content.strip()
            print(json_texto)
            dados = json.loads(json_texto)
            resultados.append({"arquivo": arquivo, "dados": dados})

        except Exception as e:
            print(f"Erro ao processar {arquivo}: {e}")

# Salva em JSON final
with open("../../APRENDIZADO/tests/resultados_comprovantes.json", "w", encoding="utf-8") as f:
    json.dump(resultados, f, ensure_ascii=False, indent=4)

print("Processamento concluído! Arquivo 'resultados_comprovantes.json' gerado.")
