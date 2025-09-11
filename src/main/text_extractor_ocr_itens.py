import os
import pytesseract
from pdf2image import convert_from_path
import re

# Configurar o caminho do Tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Pasta com os PDFs
PASTA_PDFS = r"C:\bf_ocr\src\resource\pdf"


def extrair_secao_tributos(texto):
    """Extrai a seção específica entre Tributo/Alíquota e ICMS"""

    # Padrão para capturar desde "Tributo" ou "Base de Alíquota" até "ICMS"
    padrao = r'(Tributo.*?Base de Alíquota.*?)(Consumo em kWh.*?Adic\. B\. Vermelha.*?)(?=ICMS|\Z)'

    resultado = re.search(padrao, texto, re.DOTALL | re.IGNORECASE)

    if resultado:
        # Retorna a seção completa com as linhas desejadas
        return resultado.group(2).strip()
    else:
        # Fallback: procurar as linhas específicas
        linhas = []

        padroes_linhas = [
            r'Consumo em kWh.*',
            r'Custo de Disponibilidade.*',
            r'Energia Atv Injetada.*',
            r'Adic\. B\..*',
            r'Ilum Pub.*',
        ]

        for padrao in padroes_linhas:
            match = re.search(padrao, texto)
            if match:
                linhas.append(match.group(0))

        return '\n'.join(linhas) if linhas else "Seção não encontrada"


def processar_texto(texto):
    linhas = texto.strip().split('\n')
    resultados = {}
    #print(linhas)
    for linha in linhas:
        linha = linha.strip()

        # sempre cortar no "Cálc" se existir
        linha_limpa = re.split(r'Cálc', linha)[0].strip()

        # Consumo
        if 'Consumo' in linha_limpa and 'KWH' in linha_limpa.upper():
            partes = linha_limpa.split()
            try:
                # normaliza para maiúsculo
                partes_upper = [p.upper() for p in partes]
                kwh_index = partes_upper.index('KWH')

                descricao = ' '.join(partes[:kwh_index + 1])
                valores = partes[kwh_index + 1:]
                valores_filtrados = [v for v in valores if re.search(r'[-]?\d+[.,]?\d*', v)]

                # pega o 3º valor numérico (índice 2)
                if len(valores_filtrados) >= 3:
                    valores_filtrados = [valores_filtrados[2]]

                resultados['Consumo'] = {
                    'descricao': descricao,
                    'valores': valores_filtrados
                }
            except:
                pass


        # Custo de Disponibilidade
        elif 'Custo' in linha_limpa and 'KWH' in linha_limpa:
            partes = linha_limpa.split()
            try:
                kwh_index = partes.index('KWH')
                descricao = ' '.join(partes[:kwh_index + 1])
                valores = partes[kwh_index + 1:]
                valores_filtrados = [v for v in valores if re.search(r'[-]?\d+[.,]?\d*', v)]

                if len(valores_filtrados) >= 3:
                    valores_filtrados = [valores_filtrados[2]]

                resultados['Custo de Disponibilidade'] = {
                    'descricao': descricao,
                    'valores': valores_filtrados
                }
            except:
                pass

        # Energia Injetada
        elif 'Injetada' in linha_limpa:
            partes = linha_limpa.split()
            try:
                idx_injetada = [i for i, p in enumerate(partes) if 'Injetada' in p]
                for idx in idx_injetada:
                    descricao = ' '.join(partes[:idx + 1])
                    try:
                        kwh_index = [p.upper() for p in partes[idx:]].index('KWH') + idx
                    except ValueError:
                        kwh_index = idx
                    valores = partes[kwh_index + 1:]
                    valores_filtrados = [v for v in valores if re.search(r'[-]?\d+[.,]?\d*', v)]

                    if len(valores_filtrados) >= 3:
                        valores_filtrados = [valores_filtrados[2]]

                    chave = f'Energia Injetada {len([k for k in resultados if "Energia Injetada" in k]) + 1}'
                    resultados[chave] = {
                        'descricao': descricao,
                        'valores': valores_filtrados
                    }
            except Exception as e:
                print(f"⚠️ Erro ao processar Energia Injetada: {e}")

        # Bandeira Vermelha
        elif 'Adic. B.' in linha_limpa:
            partes = linha_limpa.split()
            try:
                vermelha_index = partes.index('Vermelha')
                descricao = ' '.join(partes[:vermelha_index + 1])
                valores = partes[vermelha_index + 1:]
                valores_filtrados = [v for v in valores if re.search(r'[-]?\d+[.,]?\d*', v)]

                if valores_filtrados:
                    valores_filtrados = [valores_filtrados[0]]

                resultados['Bandeira Vermelha'] = {
                    'descricao': descricao,
                    'valores': valores_filtrados
                }
            except:
                pass

        # Iluminação Pública
        elif 'Ilum Pub' in linha_limpa:
            partes = linha_limpa.split()
            try:
                pub_index = partes.index('Pub')
                descricao = ' '.join(partes[:pub_index + 1])
                valores = partes[pub_index + 1:]
                valores_filtrados = [v for v in valores if re.search(r'[-]?\d+[.,]?\d*', v)]

                if valores_filtrados:
                    valores_filtrados = [valores_filtrados[0]]

                resultados['Iluminação Pública'] = {
                    'descricao': descricao,
                    'valores': valores_filtrados
                }
            except:
                pass

    return resultados



for arquivo in os.listdir(PASTA_PDFS):
    if arquivo.lower().endswith(".pdf"):
        caminho_pdf = os.path.join(PASTA_PDFS, arquivo)
        print(f"🔍 Processando: {arquivo}")
        print("-" * 50)

        try:
            imagens = convert_from_path(caminho_pdf, dpi=300, poppler_path=r"C:\poppler-24.08.0\Library\bin")
            texto_completo = ""

            for i, imagem in enumerate(imagens):
                print(f"📄 Página {i + 1}/{len(imagens)}...")
                texto = pytesseract.image_to_string(imagem, lang='por')
                texto_completo += texto + "\n"

            #print(texto_completo)
            secao_tributos = extrair_secao_tributos(texto_completo)

            print("\n✅ SEÇÃO DE TRIBUTOS EXTRAÍDA:")
            resultado = processar_texto(secao_tributos)

            for chave, valor in resultado.items():
                print(f"{chave}:")
                print(f"  Descrição: {valor['descricao']}")
                print(f"  Valores: {valor.get('valores', [])}")
                print()
            print("=" * 80 + "\n")

        except Exception as e:
            print(f"❌ Erro ao processar {arquivo}: {e}")
            print("=" * 80 + "\n")

print("🎉 Processamento concluído!")
