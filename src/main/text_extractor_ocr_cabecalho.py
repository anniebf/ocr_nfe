from pdf2image import convert_from_path
import pytesseract
import pdfplumber
import re

# Configurar caminho do Tesseract no Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
#pages = convert_from_path(r"C:\bf_ocr\src\resource\pdf\EMP 16 FL 1001001-2703074-NOTA FISCAL Nº 020.429.962 - Série 002 - OK.pdf", dpi=300, first_page=1, last_page=1,poppler_path=r"C:\poppler-24.08.0\Library\bin")

# Converter somente a primeira página em imagem
arquivo = r"C:\bf_ocr\src\resource\pdf\EMP 16 FL 1008081-4668543-NOTA FISCAL Nº 021.096.025 - Série 002 OK.pdf"

with pdfplumber.open(arquivo) as pdf:
    page = pdf.pages[0]

    # palavras-chave que identificam o cabeçalho
    keywords = ["Preço", "unit", "R$"]

    y_positions = []

    for word in page.extract_words(x_tolerance=2, y_tolerance=2):
        if any(k in word["text"] for k in keywords):
            y_positions.append(word["top"])

    if y_positions:
        y_corte = min(y_positions)  # pegar a linha mais acima
        largura = page.width
        cropped = page.crop((0, 0, largura, y_corte))
        texto_filtrado = cropped.extract_text(x_tolerance=2, y_tolerance=2)
        print("📌 Texto apenas acima da linha:")
        #print(texto_filtrado)
        texto = texto_filtrado

        resultado = {}

        # 1️⃣ Nome do titular (linha que contém BOM FUTURO AGRICOLA LTDA)
        m = re.search(r'\n([A-Z &]+)\s*\d*\n', texto)
        resultado['nome_titular'] = m.group(1).strip() if m else None

        # 2️⃣ Distribuidora de energia (linha que contém ENERGISA ...)
        m = re.search(r'(ENERGISA [^\n]+)', texto)
        resultado['distribuidora_energia'] = m.group(1).strip() if m else None

        # 3️⃣ CNPJ da distribuidora (formato 00.000.000/0000-00)
        m = re.search(r'CNPJ (\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', texto)
        resultado['cnpj_distribuidora_energia'] = m.group(1) if m else None

        # 4️⃣ Número da nota fiscal (de "NOTA FISCAL Nº: 020.429.962")
        m = re.search(r'NOTA FISCAL Nº:\s*([\d\.]+)', texto)
        if m:
            resultado['numero_nota_fiscal'] = m.group(1).replace('.', '')  # remove pontos
        else:
            resultado['numero_nota_fiscal'] = None

        # 5️⃣ Série da nota fiscal
        m = re.search(r'Série:\s*(\d+)', texto)
        resultado['serie_nota_fiscal'] = m.group(1) if m else None

        # 6️⃣ Código do cliente (formato 6/2703074-1)
        m = re.search(r'RURAL (\d+/\d+-\d+)', texto)
        resultado['codigo_cliente'] = m.group(1) if m else None

        # 7️⃣ Data de emissão (formato dd/mm/yyyy)
        #m = re.search(r'DATA DE EMISSÃO:(\d{2}/\d{2}/\d{4})', texto)
        #resultado['data_emissao'] = m.group(1) if m else None

        # 8️⃣ Chave de acesso (somente números)
        m = re.search(r'chave de acesso:\s*([\d\s\n]+)', texto, re.IGNORECASE)
        if m:
            # remove espaços e quebras de linha
            chave = re.sub(r'\D', '', m.group(1))  # \D = qualquer coisa que não seja dígito
            resultado['chave_acesso'] = chave
        else:
            resultado['chave_acesso'] = None

        valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', texto)
        resultado['preco_total'] = valores[-1] if valores else None

        # ---------- resultado final ----------
        import json

        print(json.dumps(resultado, indent=4, ensure_ascii=False))
    else:
        print("⚠️ Nenhuma palavra-chave encontrada!")