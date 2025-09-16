import pdfplumber
import numpy as np
import re
import json


""" -PASSO A PASSO-
 - Recorta o pdf apenas na parte que nao é da cor branca
 - Leitura da parte seleceionada
 - Regex procura as palavras chaves
 - Retorna o json
 
"""


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
    m = re.search(r'NOTA FISCAL N[°º]\s*([\d\.]+)', texto)
    resultado['numero_nota_fiscal'] = m.group(1).replace('.', '') if m else None

    # 5️⃣ Série da nota fiscal
    m = re.search(r'SÉRIE\s*[:]\s*(\d+)', texto)
    resultado['serie_nota_fiscal'] = m.group(1) if m else None

    # 6️⃣ Código do cliente
    # m = re.search(r'RURAL (\d+/\d+-\d+)', texto)
    # resultado['codigo_cliente'] = m.group(1) if m else None

    # 7️⃣ Data de emissão
    m = re.search(r'DATA EMISSÂO/APRESENTAÇÂO:[:\s]*(\d{2}/\d{2}/\d{4})', texto)
    resultado['data_emissao'] = m.group(1) if m else None

    # 8️⃣ Chave de acesso
    m = re.search(r'Chave de Acesso\s*\n([\d\s]+)', texto, re.IGNORECASE)
    if m:
        chave = re.sub(r'\D', '', m.group(1))  # remove tudo que não é dígito
        resultado['chave_acesso'] = chave
    else:
        resultado['chave_acesso'] = None

    # 9️⃣ Preço total (último valor monetário)
    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', texto)
    resultado['preco_total'] = valores[-1] if valores else None

    # 12️⃣ Disp
    m = re.search(r'DISP.:\s*(\d+)', texto, re.IGNORECASE)
    resultado['disp'] = m.group(1) if m else None



    # 13️⃣ Número do cliente (antes de "NOTA FISCAL Nº")
    matches = re.findall(r'\b\d/\d{6}-\d\b', texto)

    if not matches:
        # Tentativa alternativa: procurar números antes de "- RURAL"
        matches = re.findall(r'\b(\d+/\d+-\d+)\b\s', texto, re.IGNORECASE)
        print(matches)

    numero_cliente = matches[1] if matches else None
    resultado['numero_cliente'] = numero_cliente



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

    consumo_match = re.search(r'Consumo.*?kWh\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)', texto, re.IGNORECASE)
    if consumo_match:
        resultado['Consumo'] = {
            'descricao': 'Consumo em kWh',
            'valores': consumo_match.group(3)
        }

    bandeiras = re.finditer(r'Adic\. B\. Vermelha.*?([\d.,]+)', texto, re.IGNORECASE)

    for i, match in enumerate(bandeiras, 1):
        valor = match.group(1)

        chave = f'Bandeira_Vermelha_{i}'
        resultado[chave] = {
            'descricao': 'Adic. B. Vermelha',
            'valores': valor
        }

    return resultado


def bbox_colorido(page, branco_threshold=250):
    """
    Retorna a menor caixa (bbox) contendo qualquer pixel não branco/colorido.
    branco_threshold: valor acima do qual é considerado branco (0-255)
    """
    # Gerar imagem da página
    im = page.to_image(resolution=150).original.convert("RGB")
    arr = np.array(im)

    # Criar máscara de pixels coloridos (não brancos)
    mask = np.any(arr < branco_threshold, axis=2)  # True se R/G/B < threshold

    coords = np.argwhere(mask)
    if coords.size == 0:
        return None  # nada colorido na página

    # Obter limites
    top, left = coords.min(axis=0)
    bottom, right = coords.max(axis=0)

    # Converter coordenadas da imagem para coordenadas do PDF
    # page.height / imagem altura, page.width / imagem largura
    img_height, img_width = arr.shape[:2]
    x0 = left * page.width / img_width
    x1 = right * page.width / img_width
    y0 = top * page.height / img_height
    y1 = bottom * page.height / img_height

    return (x0, y0, x1, y1)

# --- Uso ---
with pdfplumber.open(
        r"/src/resource/pdf_fino/EMP 16 FL 1008081 - 4668543 -NOTA FISCAL Nº 044.606.418 - Série 001 OK.pdf") as pdf:
    page = pdf.pages[0]

    bbox = bbox_colorido(page)
    if bbox:
        print("PAGINA RECORTADA - ", bbox)
        recorte = page.crop(bbox)
        texto = recorte.extract_text()
        print("Texto extraído:")
        #print(texto)

        resultado = extrair_dados_texto(texto)
        print(json.dumps(resultado, indent=4, ensure_ascii=False))
        print("\n" + "=" * 80 + "\n")

        # Visualizar
        im_vis = page.to_image(resolution=150)
        im_vis.draw_rect(bbox, stroke="red", stroke_width=3)
        #im_vis.show()
    else:
        print("Página sem conteúdo colorido.")
