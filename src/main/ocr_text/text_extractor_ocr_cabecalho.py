
import pdfplumber
import re
import json
import os


# Configurar caminho do Tesseract no Windows
##
##USANDO PDFPLUMBER PARA LER OS PDFS
##

##O cabeçalho funciona para pegar as informacacoes dos refaturados
##
##

def corrigir_caracteres_duplicados(texto):
    """
    Corrige textos com caracteres duplicados como 'EERRAAII MMAAGGGGII' → 'ERAI MAGGI'
    Remove caracteres duplicados consecutivos
    """
    if not texto:
        return texto

    palavras = texto.split()
    palavras_corrigidas = []

    for palavra in palavras:
        # Remove caracteres duplicados consecutivos
        palavra_corrigida = ''
        i = 0
        while i < len(palavra):
            # Se houver pelo menos 2 caracteres iguais consecutivos, mantém apenas um
            if i + 1 < len(palavra) and palavra[i] == palavra[i + 1]:
                palavra_corrigida += palavra[i]
                i += 2  # Pula os dois caracteres iguais
            else:
                palavra_corrigida += palavra[i]
                i += 1
        palavras_corrigidas.append(palavra_corrigida)

    return ' '.join(palavras_corrigidas)


def extrair_dados_texto(texto):
    """
    Função para extrair todos os dados do texto usando regex
    Retorna um dicionário com todos os campos extraídos
    """
    resultado = {}

    # 1️⃣ Nome do titular - COM CORREÇÃO DE CARACTERES DUPLICADOS
    m = re.search(r'\n([A-Z\s&\.]+)\s*\d*\n', texto)
    if m:
        nome_cru = m.group(1).strip()
        # Corrige caracteres duplicados
        nome_corrigido = corrigir_caracteres_duplicados(nome_cru)
        resultado['nome_titular'] = nome_corrigido
    else:
        resultado['nome_titular'] = None

    # 2️⃣ Distribuidora de energia
    m = re.search(r'(ENERGISA [^\n]+)', texto)
    resultado['distribuidora_energia'] = m.group(1).strip() if m else None

    # 3️⃣ CNPJ da distribuidora
    m = re.search(r'CNPJ (\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', texto)
    resultado['cnpj_distribuidora_energia'] = m.group(1) if m else None

    # 4️⃣ Número da nota fiscal
    m = re.search(r'NOTA FISCAL Nº:\s*([\d\.]+)', texto)
    resultado['numero_nota_fiscal'] = m.group(1).replace('.', '') if m else None

    # 5️⃣ Série da nota fiscal
    m = re.search(r'Série:\s*(\d+)', texto)
    resultado['serie_nota_fiscal'] = m.group(1) if m else None

    # 6️⃣ Código do cliente
    # m = re.search(r'RURAL (\d+/\d+-\d+)', texto)
    # resultado['codigo_cliente'] = m.group(1) if m else None

    # 7️⃣ Data de emissão
    m = re.search(r'DATA DE EMISSÃO[:\s]*(\d{2}/\d{2}/\d{4})', texto)
    resultado['data_emissao'] = m.group(1) if m else None

    # 8️⃣ Chave de acesso
    m = re.search(r'chave de acesso:\s*([\d\s]+)', texto, re.IGNORECASE)
    if m:
        chave = re.sub(r'\D', '', m.group(1))  # remove tudo que não é dígito
        resultado['chave_acesso'] = chave
    else:
        resultado['chave_acesso'] = None

    # 9️⃣ Preço total (último valor monetário)
    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', texto)
    resultado['preco_total'] = valores[-1] if valores else None

    # 🔟 Ligação
    m = re.search(r'LIGAÇÃO:\s*([^\n]+)', texto, re.IGNORECASE)
    resultado['ligacao'] = m.group(1).strip() if m else None

    # 12️⃣ Disp
    m = re.search(r'DISP:\s*(\d+)', texto, re.IGNORECASE)
    resultado['disp'] = m.group(1) if m else None

    # 13️⃣ Número do cliente (antes de "NOTA FISCAL Nº")
    m = re.search(r'(\d+/[\d-]+)\s*NOTA FISCAL Nº:', texto)
    resultado['numero_cliente'] = m.group(1) if m else None

    m = re.search(r'Classificação:\s*([^\n]+)', texto)
    classificacao = m.group(1).strip() if m else None

    grupo, subgrupo, classe = None, None, ""
    if classificacao:
        partes = classificacao.split("/")
        if len(partes) > 1:
            subgrupo = partes[1].split()[0].strip()
            grupo = subgrupo[0] if subgrupo else None  # pega só a primeira letra
            if len(partes[1].split()) > 1:
                classe = " ".join(partes[1].split()[1:]).strip()
    resultado["classificacao"] = {
        "grupo": grupo,
        "subgrupo": subgrupo,
        "classe": classe
    }

    return resultado


# Definir a pasta onde estão os PDFs
PASTA_PDFS = r"C:\bf_ocr\src\resource\pdf"

# Processar cada arquivo PDF na pasta
for arquivo in os.listdir(PASTA_PDFS):
    # Pega todos os arquivos que tenham a extensao pdf
    if arquivo.lower().endswith(".pdf"):
        caminho_pdf = os.path.join(PASTA_PDFS, arquivo)
        print(f"🔍 Processando: {arquivo}")
        print("-" * 50)

        try:
            with pdfplumber.open(caminho_pdf) as pdf:
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
                    texto = texto_filtrado or ""

                    #print(texto)
                    # Chama a função única para extrair todos os dados
                    resultado = extrair_dados_texto(texto)

                    # ---------- resultado final ----------
                    print(json.dumps(resultado, indent=4, ensure_ascii=False))
                    print("\n" + "=" * 80 + "\n")

                else:
                    print("⚠️ Nenhuma palavra-chave encontrada!")

        except Exception as e:
            print(f"❌ Erro ao processar {arquivo}: {str(e)}")
            print("\n" + "=" * 80 + "\n")