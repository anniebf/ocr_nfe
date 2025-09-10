import re
import pytesseract
import pdfplumber
import os

pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

PASTA_PDFS = r"C:\bf_ocr\src\resource\pdf"

def extrair_tributos_especificos(texto):
    """
    Retorna apenas as linhas que contenham PIS, COFINS ou ICMS,
    descartando descrições como Processo, Imunidade etc.
    """
    padrao = re.compile(
        r"^(?:.*\bPIS\b.*|.*\bCOFINS\b.*|.*\bICMS\b.*)$",
        re.IGNORECASE
    )

    linhas_filtradas = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if not padrao.search(linha):
            continue
        # descartar se tiver palavras extras indesejadas
        if any(p in linha.upper() for p in ["PROCESSO", "IMUNIDADE", "ISEN", "REV", "CONFORME"]):
            continue
        linhas_filtradas.append(linha)

    return linhas_filtradas


def processar_tributos(linhas, nome_pdf):
    """
    Processa as linhas de PIS, COFINS e ICMS em um dicionário estruturado,
    incluindo referência ao PDF de origem.
    """
    resultados = {}

    for linha in linhas:
        partes = linha.split()
        if "PIS" in linha.upper() and not "PIS/COFINS" in linha.upper():
            chave = "PIS"
            idx = partes.index("PIS")
        elif "COFINS" in linha.upper() and not "PIS/COFINS" in linha.upper():
            chave = "COFINS"
            idx = partes.index("COFINS")
        elif "ICMS" in linha.upper() and not "PROCESSO" in linha.upper():
            chave = "ICMS"
            idx = partes.index("ICMS")
        else:
            continue

        descricao = " ".join(partes[:idx + 1])
        valores = partes[idx + 1:]
        valores_filtrados = [v for v in valores if any(c.isdigit() for c in v.replace(",", "").replace(".", ""))]

        if len(valores_filtrados) >= 3:
            resultados[chave] = {
                "arquivo": nome_pdf,
                "base_calculo": valores_filtrados[0],
                "aliquota": valores_filtrados[1],
                "valor": valores_filtrados[2]
            }
        elif len(valores_filtrados) > 0:
            # Preencher com os valores disponíveis
            resultados[chave] = {
                "arquivo": nome_pdf,
                "base_calculo": valores_filtrados[0] if len(valores_filtrados) >= 1 else "indisponivel",
                "aliquota": valores_filtrados[1] if len(valores_filtrados) >= 2 else "indisponivel",
                "valor": valores_filtrados[2] if len(valores_filtrados) >= 3 else "indisponivel"
            }
        else:
            # Caso não tenha valores
            resultados[chave] = {
                "arquivo": nome_pdf,
                "base_calculo": "indisponivel",
                "aliquota": "indisponivel",
                "valor": "indisponivel"
            }

    return resultados


for arquivo in os.listdir(PASTA_PDFS):
    if arquivo.lower().endswith(".pdf"):
        caminho_pdf = os.path.join(PASTA_PDFS, arquivo)
        print(f"\n📄 Processando: {arquivo}")
        texto = ""

        with pdfplumber.open(caminho_pdf) as pdf:
            for pagina in pdf.pages:
                t = pagina.extract_text()
                if t:
                    texto += t + "\n"

        linhas_tributos = extrair_tributos_especificos(texto)

        print("\n✅ TRIBUTOS FILTRADOS:")
        #for linha in linhas_tributos:
            #print(linha)

        # Estruturar os dados
        resultado = processar_tributos(linhas_tributos, arquivo)

        print("\n📊 RESULTADO ESTRUTURADO:")
        for chave, valor in resultado.items():
            print(f"{chave}:")
            #print(f"  Arquivo: {valor['arquivo']}")
            print(f"  base de calculo: {valor['base_calculo']}")
            print(f"  aliquota: {valor['aliquota']}")
            print(f"  Valor: {valor['valor']}")
        print("=" * 80 + "\n")
