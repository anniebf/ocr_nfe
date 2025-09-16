import os
import pdfplumber
import re

PASTA_PDFS = r"C:\bf_ocr\src\resource\pdf"


def extrair_secao_tributos(texto):
    """Extrai a seção específica de tributos capturando linhas completas"""
    # Padrão para capturar todas as linhas relevantes até o final da seção
    padrao = r'(Consumo em kWh.*?)(?=Total|\n\n|\Z)'
    resultado = re.search(padrao, texto, re.DOTALL | re.IGNORECASE)

    if resultado:
        return resultado.group(1).strip()
    else:
        # Fallback: procurar todas as linhas relevantes individualmente
        linhas_relevantes = []
        padroes = [
            r'Consumo em kWh.*?[\d.,-]+.*?[\d.,-]+.*?[\d.,-]+',
            r'PIS.*?[\d.,-]+.*?[\d.,-]+.*?[\d.,-]+',
            r'COFINS.*?[\d.,-]+.*?[\d.,-]+.*?[\d.,-]+',
            r'ICMS.*?[\d.,-]+.*?[\d.,-]+.*?[\d.,-]+',
            r'Energia Atv Injetada.*?[\d.,-]+.*?[\d.,-]+.*?[\d.,-]+.*?[\d.,-]+.*?[\d.,-]+.*?[\d.,-]+',
            r'Adic\. B\. Vermelha.*?[\d.,-]+.*?[\d.,-]+.*?[\d.,-]+.*?[\d.,-]+'
        ]

        for padrao in padroes:
            matches = re.findall(padrao, texto, re.IGNORECASE)
            linhas_relevantes.extend(matches)

        return '\n'.join(linhas_relevantes) if linhas_relevantes else texto


def processar_texto(texto):
    """Extrai as informações importantes do texto de forma estruturada"""

    resultados = {}

    # Processar CONSUMO
    consumo_match = re.search(r'Consumo.*?kWh\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)', texto, re.IGNORECASE)
    if consumo_match:
        resultados['Consumo'] = {
            'descricao': 'Consumo em kWh',
            'valores': [consumo_match.group(2)]
        }

    # Processar PIS
    pis_match = re.search(r'PIS\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)', texto, re.IGNORECASE)
    if pis_match:
        resultados['PIS'] = {
            'descricao': 'PIS',
            "valores":{
            "base_calculo": pis_match.group(1),
            "aliquota": pis_match.group(2),
            'valor': pis_match.group(3)
            }
        }

    # Processar COFINS
    cofins_match = re.search(r'COFINS\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)', texto, re.IGNORECASE)
    if cofins_match:
        resultados['COFINS'] = {
            'descricao': 'COFINS',
            "valores":{
            "base_calculo": pis_match.group(1),
            "aliquota": pis_match.group(2),
            'valor': pis_match.group(3)
            }
        }

    # Processar ICMS
    icms_match = re.search(r'ICMS\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)', texto, re.IGNORECASE)
    if icms_match:
        resultados['ICMS'] = {
            'descricao': 'ICMS',
            "valores":{
            "base_calculo": pis_match.group(1),
            "aliquota": pis_match.group(2),
            'valor': pis_match.group(3)
            }
        }

    energias_injetadas = re.finditer(r'(Energia Atv Injetada.*?)(mPT|Ponta)\s+[\d.,]+\s+(-?[\d.,]+)', texto,
                                     re.IGNORECASE)

    for i, match in enumerate(energias_injetadas, 1):
        descricao = match.group(1).strip()
        valor = match.group(3)  # Terceiro grupo de captura (-4.800,04 ou -1.299,49)

        chave = f'Energia_Injetada_{i}'
        resultados[chave] = {
            'descricao': descricao,
            'valores': [valor]
        }

    # Processar BANDEIRA VERMELHA
    bandeiras = re.finditer(r'Adic\. B\. Vermelha.*?([\d.,]+)', texto, re.IGNORECASE)

    for i, match in enumerate(bandeiras, 1):
        valor = match.group(1)

        chave = f'Bandeira_Vermelha_{i}'
        resultados[chave] = {
            'descricao': 'Adic. B. Vermelha',
            'valores': [valor]
        }

    return resultados


# Processamento dos arquivos
for arquivo in os.listdir(PASTA_PDFS):
    if arquivo.lower().endswith(".pdf"):
        caminho_pdf = os.path.join(PASTA_PDFS, arquivo)
        print(f"\n📄 Processando: {arquivo}")
        texto_completo = ""

        with pdfplumber.open(caminho_pdf) as pdf:
            for pagina in pdf.pages:
                t = pagina.extract_text()
                if t:
                    texto_completo += t + "\n"

            #print("Texto completo extraído:")
            #print(texto_completo[:1000] + "..." if len(texto_completo) > 1000 else texto_completo)
            #print("\n" + "=" * 80)

            secao_tributos = extrair_secao_tributos(texto_completo)
            #print(f"\n✅ SEÇÃO DE TRIBUTOS EXTRAÍDA:")
            #print(f"Conteúdo: {secao_tributos}")

            resultado = processar_texto(secao_tributos)

            for chave, valor in resultado.items():
                print(f"{chave}:")
                print(f"  Descrição: {valor['descricao']}")
                print(f"  Valores: {valor.get('valores', [])}")
                print()

            print("=" * 80 + "\n")

print("🎉 Processamento concluído!")