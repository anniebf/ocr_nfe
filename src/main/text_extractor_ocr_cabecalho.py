import os
import pytesseract
from pdf2image import convert_from_path
import re
import json

# Configurar o caminho do Tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Função para extrair informações
def extrair_informacoes_por_linha(texto: str) -> dict:
    dados = {
        "nome_titular": None,
        "cpf_cnpj_titular": None,
        "distribuidora_energia": None,
        "cnpj_distribuidora_energia": None,
        "cep": None,
        "cidade": None,
        "uf": None,
        "numero_nota_fiscal": None,
        "serie_nota_fiscal": None,
        "chave_acesso": None,
        "codigo_cliente": None,
        "tipo_nota_fiscal": None,
        "empresa_prestadora": None,
        "valor_total": None
    }

    linhas = texto.splitlines()

    for i, linha in enumerate(linhas):
        linha_limpa = linha.strip()

        # Nome e CPF/CNPJ do titular (aparece no bloco PAGADOR)
        if "PAGADOR" in linha_limpa.upper():
            if i + 1 < len(linhas):
                proxima = linhas[i + 1]
                nome = re.search(r"([A-ZÇÃÕÉÍÓÚÂÊÔ ]+)", proxima)
                cnpj = re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", proxima)
                if nome:
                    dados["nome_titular"] = nome.group(1).strip()
                if cnpj:
                    dados["cpf_cnpj_titular"] = cnpj.group(0)

        # Distribuidora + CNPJ
        if "ENERGISA" in linha_limpa.upper():
            dados["distribuidora_energia"] = linha_limpa
            cnpj = re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", linha_limpa)
            if cnpj:
                dados["cnpj_distribuidora_energia"] = cnpj.group(0)

        # CEP, cidade e UF
        if "CEP" in linha_limpa.upper():
            cep = re.search(r"\d{5}-\d{3}", linha_limpa)
            cidade_uf = re.search(r"([A-ZÇÃÕÉÍÓÚÂÊÔ ]+)\s*/\s*([A-Z]{2})", linha_limpa)
            if cep:
                dados["cep"] = cep.group(0)
            if cidade_uf:
                dados["cidade"] = cidade_uf.group(1).title().strip()
                dados["uf"] = cidade_uf.group(2)

        # Nota Fiscal
        if "NOTA FISCAL" in linha_limpa.upper():
            nf = re.search(r"([\d\.]+)", linha_limpa)
            serie = re.search(r"S[ée]rie[: ]+(\d+)", linha_limpa, re.IGNORECASE)
            if nf:
                dados["numero_nota_fiscal"] = nf.group(1)
            if serie:
                dados["serie_nota_fiscal"] = serie.group(1)

        # Chave de acesso
        if "chave de acesso" in linha_limpa.lower():
            chave = re.sub(r"\D", "", linha_limpa)  # só números
            if len(chave) >= 40:
                dados["chave_acesso"] = chave

        # Código do cliente / Matrícula
        if "MATRÍCULA" in linha_limpa.upper():
            codigo = re.search(r"([\d\-]+)", linha_limpa)
            if codigo:
                dados["codigo_cliente"] = codigo.group(1)

        # Valor total (procura TOTAL A PAGAR)
        if "TOTAL A PAGAR" in linha_limpa.upper() or "VALOR DO DOCUMENTO" in linha_limpa.upper():
            valor = re.search(r"R\$ ?([\d\.,]+)", linha_limpa)
            if valor:
                dados["valor_total"] = valor.group(1).replace(".", "").replace(",", ".")

    # fallback: se valor não foi achado, pega o último R$
    if not dados["valor_total"]:
        valores = re.findall(r"R\$ ?([\d\.,]+)", texto)
        if valores:
            dados["valor_total"] = valores[-1].replace(".", "").replace(",", ".")

    return dados


# Pasta com os PDFs
PASTA_PDFS = r"C:\bf_ocr\APRENDIZADO\pdf"
for arquivo in os.listdir(PASTA_PDFS):
    if arquivo.lower().endswith(".pdf"):
        caminho_pdf = os.path.join(PASTA_PDFS, arquivo)
        print(f"🔍 Processando: {arquivo}")
        print("-" * 50)

        try:
            imagens = convert_from_path(
                caminho_pdf, dpi=300, 
                poppler_path=r"C:\poppler-24.08.0\Library\bin"
            )
            texto_completo = ""

            for i, imagem in enumerate(imagens):
                print(f"📄 Página {i + 1}/{len(imagens)}...")
                texto = pytesseract.image_to_string(imagem, lang='por')
                texto_completo += texto + "\n"

            # Extrair os dados
            dados = extrair_informacoes(texto_completo)
            print(json.dumps(dados, ensure_ascii=False, indent=4))

        except Exception as e:
            print(f"❌ Erro ao processar {arquivo}: {e}")
