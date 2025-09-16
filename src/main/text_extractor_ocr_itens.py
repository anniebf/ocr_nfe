import os
import pytesseract
from pdf2image import convert_from_path
import re

""" Terceiro codigo para pegar os itens dos pdfs de conta de energia
    Pegando somente os valores e descricao dos itens que foram passados pelo analista 
"""

##
##USANDO PYTESSERACT E PLOPPLERS PARA LER OS PDFS
##

# Configuraçoes padrao
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
PASTA_PDFS = r"C:\bf_ocr\src\resource\pdf"

def extrair_secao_tributos(texto):
    """Extrai a seção específica entre Tributo/Alíquota e ICMS"""

    # Padrão para capturar desde "Tributo" ou "Base de Alíquota" até "ICMS"
    # Tarifa e unit os valres nao foram encontrados no lumber
    padrao = r'(Tributo.*?Base de Alíquota.*?)(Consumo em kWh.*?Adic\. B\. Vermelha.*?)(?=ICMS|\Z)'
    resultado = re.search(padrao, texto, re.DOTALL | re.IGNORECASE)

    #re.IGNORECASE = caracteriza . como quebra de linha
    #re.DOTALL = nao diferencia maiuscula de minuscula

    if resultado:
        #retorna somente as linhas com
        #Consumo
        #Custos
        #Energia injetada
        #adional da bandeira
        #Taxa de iluminacao publica

        return resultado.group(2).strip()
    else:
        # Fallback: procurar as linhas específicas
        linhas = []

        #Padroes para a procura no itens
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
    """Extrai as informacoes importantes de cada linha capturada"""

    #limpa linhas e cria as substrings
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
                # coloca maiusculo para reducao de erros
                partes_upper = [p.upper() for p in partes]
                kwh_index = partes_upper.index('KWH')

                descricao = ' '.join(partes[:kwh_index + 1])
                valores = partes[kwh_index + 1:]
                valores_filtrados = [v for v in valores if re.search(r'[-]?\d+[.,]?\d*', v)]

                # valor do consumo com indice 2
                # Itens
                if len(valores_filtrados) >= 3:
                    valor_consumo = [valores_filtrados[2]]


                    """ Outras colunas dos itens da fatura que nao foram usadas"""
                    #quantidade_consumo = valores_filtrados[0]
                    #preco_unidade = valores_filtrados[1]
                    #pis_confins = valores_filtrados[3]
                    #base = valores_filtrados[4]
                    #aliquota = valores_filtrados[5]
                    #icms = valores_filtrados[6]
                    #tarifa = valores_filtrados[7]

                    #print('quantidade_consumo: '+quantidade_consumo)
                    #print('preco_unidade: '+preco_unidade)
                    #print('pis_confins: '+pis_confins)
                    #print('base: '+base)
                    #print('aliquota: '+aliquota)
                    #print('icms: '+icms)
                    #print('tarifa: '+tarifa)

                resultados['Consumo'] = {
                    'descricao': descricao,
                    'valores': valor_consumo,
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
            print(partes)
            try:
                #Cria uma lista de indices onde a palavra "Injetada" aparece na linha
                idx_injetada = [i for i, p in enumerate(partes) if 'KwWH' in p or 'KWH' in p]
                for idx in idx_injetada:
                    #Cria a descrição do item, pegando todas as palavras desde o início da linha até a palavra "Injetada"
                    descricao = ' '.join(partes[:idx + 1])
                    try:
                        #encontra o índice da palavra "KWH" após a palavra "Injetada"
                        kwh_index = [p.upper() for p in partes[idx:]].index('KWH') + idx
                    except ValueError:
                        kwh_index = idx
                    #Pega todos os elementos da lista após o índice de "KWH"
                    valores = partes[kwh_index + 1:]
                    #print(valores)
                    try:
                        # Procura especificamente por "KwWH" (case insensitive)
                        # Usando 'KWWH' ou variações similares
                        kw_index = next(i for i, v in enumerate(valores) if v.upper() in ['KWWH', 'KWH', 'KWW'])
                    except StopIteration:
                        kw_index = -1

                    # Filtra a lista para manter somente strings que contenham números
                    if kw_index >= 0:
                        # Pega apenas os valores a partir de "KwWH" + 1
                        valores_apos_kw = valores[kw_index + 1:]
                        # Filtra apenas valores numéricos (mais restritivo)
                        valores_filtrados = [v for v in valores_apos_kw if re.search(r'^[-]?\d+[.,]?\d*[.,]?\d*$', v)]
                    else:
                        # Fallback: filtra todos os valores numéricos (abordagem original)
                        valores_filtrados = [v for v in valores if re.search(r'^[-]?\d+[.,]?\d*[.,]?\d*$', v)]
                    print(valores_filtrados)
                    if len(valores_filtrados) >= 3:
                        #Filtra somente o Valor da energia no indice 2 (coluna Valor)
                        valores_filtrados = [valores_filtrados[2]]

                    #Cria uma chave que armazena o docionario com os resultados e quantos itens existem no dicionario
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
                #Armazena o índice da palavra "Vermelha"
                vermelha_index = partes.index('Vermelha')

                #descrição da taxa pegando todas as palavras até a palavra "Vermelha"
                descricao = ' '.join(partes[:vermelha_index + 1])

                #Pega todos os elementos que vêm após "Vermelha"
                valores = partes[vermelha_index + 1:]

                #Filtra a lista para manter somente strings que contenham números
                valores_filtrados = [v for v in valores if re.search(r'[-]?\d+[.,]?\d*', v)]

                if valores_filtrados:
                    #filtra somente o valor da taxa da bandeira indice 0
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
    #pega todos os arquivos que tenham a extensao pdf
    if arquivo.lower().endswith(".pdf"):
        caminho_pdf = os.path.join(PASTA_PDFS, arquivo)
        print(f"🔍 Processando: {arquivo}")
        print("-" * 50)

        try:
            #converte o pdf em imagem
            imagens = convert_from_path(caminho_pdf, dpi=300, poppler_path=r"C:\poppler-24.08.0\Library\bin")
            texto_completo = ""

            for i, imagem in enumerate(imagens):
                print(f"📄 Página {i + 1}/{len(imagens)}...")
                #identifica a texto como portugues
                texto = pytesseract.image_to_string(imagem, lang='por')
                texto_completo += texto + "\n"

            #print(texto_completo)
            secao_tributos = extrair_secao_tributos(texto_completo)

            print("\n✅ SEÇÃO DE TRIBUTOS EXTRAÍDA:")
            resultado = processar_texto(secao_tributos)

            #Retorna o valor e descricao de cada chave encontrada no regex
            for chave, valor in resultado.items():
                print(f"{chave}:")
                print(f"  Descrição: {valor['descricao']}")
                print(f"  Valor: {valor.get('valores', [])}")
                print()
            print("=" * 80 + "\n")

        except Exception as e:
            print(f"❌ Erro ao processar {arquivo}: {e}")
            print("=" * 80 + "\n")

print("🎉 Processamento concluído!")
