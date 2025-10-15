import pdfplumber
import re
import json
from typing import Dict, Any
from pathlib import Path
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

# CONFIGURAÇÃO
PASTA_PDFS = r"C:\bf_ocr\src\resource\pdf_fino"

# Regiões a serem extraídas
regioes = {
    "mais_a_cima": {
        "coordenadas": [
            (65.5, 5.6),
            (239.5, 5.6),
            (63.3, 45.2),
            (239.5, 40.7)
        ],
        "descricao": "Área mais acima do documento"
    },
    "roteiro_tensao": {
        "coordenadas": [
            (10.2, 48.6),
            (4.5, 74.6),
            (285.9, 75.7),
            (284.7, 48.6)
        ],
        "descricao": "Roteiro e tensão"
    },
    "nota_fiscal_protocolo": {
        "coordenadas": [
            (96.0, 169.5),
            (261.0, 167.2),
            (97.2, 245.2),
            (263.3, 241.8)
        ],
        "descricao": "Nota fiscal e protocolo"
    },
    "nome_endereco": {
        "coordenadas": [
            (4.0, 74.8),
            (3.0, 113.2),
            (170.8, 114.2),
            (176.9, 78.9)
        ],
        "descricao": "Nome e endereço"
    },
    "codigo_cliente": {
        "coordenadas": [
            (185.3, 87.0),
            (178.5, 110.7),
            (275.7, 108.5),
            (273.4, 84.7)
        ],
        "descricao": "Código do cliente"
    },
    "ref_total_pagar": {
        "coordenadas": [
            (15.8, 149.1),
            (14.7, 162.7),
            (274.6, 162.7),
            (275.7, 148.0)
        ],
        "descricao": "Referência e total a pagar"
    },
    "itens_fatura": {
        "coordenadas": [
            (3.4, 385.3),
            (3.4, 465.5),
            (288.1, 466.6),
            (287.0, 385.3)
        ],
        "descricao": "Itens da fatura"
    },
    "tributos": {
        "coordenadas": [
            (146.9, 497.1),
            (144.6, 527.6),
            (274.6, 524.3),
            (275.7, 500.5)
        ],
        "descricao": "Tributos"
    },
    "cnpj": {"coordenadas":
                 [(5.6, 690.3),
                  (207.9, 698.3),
                  (6.8, 700.5),
                  (206.8, 689.2)
            ],
            "descricao": "cnpj"}
}

# Área específica para extração do DISP
AREA_DISP = (11.3, 68.9, 282.5, 82.5)


def calcular_retangulo(coordenadas):
    """Converte coordenadas em um retângulo (x0, top, x1, bottom)"""
    if len(coordenadas) == 2:
        return (coordenadas[0][0], coordenadas[0][1], coordenadas[1][0], coordenadas[1][1])
    else:
        x_coords = [coord[0] for coord in coordenadas]
        y_coords = [coord[1] for coord in coordenadas]
        return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))


def extrair_texto_nas_coordenadas(pdf_path, retangulo):
    """Extrai texto mantendo informações de layout para melhor análise"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pagina = pdf.pages[0]

            palavras = pagina.within_bbox(retangulo).extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=False,
                use_text_flow=True
            )

            if not palavras:
                return "Nenhum texto encontrado"

            linhas = {}
            for palavra in palavras:
                y = round(palavra['top'])
                if y not in linhas:
                    linhas[y] = []
                linhas[y].append((palavra['x0'], palavra['text']))

            texto_ordenado = []
            for y in sorted(linhas.keys()):
                palavras_na_linha = sorted(linhas[y], key=lambda x: x[0])
                linha_texto = ' '.join([palavra[1] for palavra in palavras_na_linha])
                texto_ordenado.append(linha_texto)

            return '\n'.join(texto_ordenado)

    except Exception as e:
        return f"Erro: {str(e)}"


def extrair_texto_por_linhas(pdf_path, coordenadas, pagina=0):
    """Extrai texto por linhas de uma área específica do PDF"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pagina_pdf = pdf.pages[pagina]
            area = (
                coordenadas[0][0],
                coordenadas[0][1],
                coordenadas[1][0],
                coordenadas[1][1]
            )
            linhas = pagina_pdf.within_bbox(area).extract_text_lines()
            return linhas
    except Exception as e:
        print(f"Erro ao processar {pdf_path}: {e}")
        return []


def extrair_disp_especifico(pdf_path: str) -> str:
    """Extrai o valor DISP das coordenadas específicas fornecidas"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pagina = pdf.pages[0]

            # Extrai texto da área específica do DISP
            texto_disp = pagina.within_bbox(AREA_DISP).extract_text(
                x_tolerance=2,
                y_tolerance=2,
                layout=True,
                use_text_flow=True
            )

            print(f"DEBUG - Texto extraído da área DISP: '{texto_disp}'")

            if texto_disp:
                # Método mais direto: procura por "Disp:" seguido de número
                # O padrão agora é mais flexível para espaços e pontuação
                disp_match = re.search(r'Disp\s*[:]?\s*(\d{2,3})', texto_disp, re.IGNORECASE)

                if disp_match:
                    disp_value = disp_match.group(1)
                    print(f"DEBUG - DISP encontrado com regex: {disp_value}")
                    return disp_value

                # Fallback: procura qualquer número de 3 dígitos na área
                numeros = re.findall(r'\b\d{3}\b', texto_disp)
                if numeros:
                    print(f"DEBUG - Números de 3 dígitos encontrados: {numeros}")
                    # Pega o primeiro número (provavelmente o Disp)
                    return numeros[0]

            print("DEBUG - Nenhum valor DISP encontrado")
            return ""

    except Exception as e:
        print(f"Erro ao extrair DISP: {str(e)}")
        return ""


def extrair_valores_apos_unidade(texto, unidades):
    """Extrai valores após as unidades KWH, UN ou KW"""
    for unidade in unidades:
        padrao = rf".*?{unidade}(.*)"
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            parte_numerica = match.group(1).strip()
            return re.findall(r"-?\d{1,3}(?:\.\d{3})*(?:,\d+)?|-?\d+", parte_numerica)
    return []


def processar_tabela_itens(linhas, pdf_path):
    """Processa a tabela de itens da fatura"""
    itens = []

    if not linhas:
        return itens

    for linha in linhas:
        texto_linha = linha['text'].strip()

        if not re.search(r"\d", texto_linha):
            continue

        if texto_linha.upper().startswith("TOTAL:"):
            continue

        descricao, valores_str = extrair_descricao_valores(texto_linha)
        valores = re.findall(r"-?\d{1,3}(?:\.\d{3})*(?:,\d+)?|-?\d+", valores_str)

        item_data = {'descricao': descricao}

        if len(valores) >= 8:
            item_data.update({
                'quantidade': valores[0],
                'preco_unit_com_tributos': valores[1],
                'valor': valores[2],
                'pis_confins': valores[3],
                'base_calc_icms': valores[4],
                'porcent_icms': valores[5],
                'icms': valores[6],
                'tarifa_unit': valores[7]
            })
        elif len(valores) == 5:
            item_data.update({
                'valor': valores[0],
                'pis_confins': valores[1],
                'base_calc_icms': valores[2],
                'porcent_icms': valores[3],
                'icms': valores[4]
            })
        elif len(valores) == 1:
            item_data.update({
                'valor': valores[0]
            })
        elif valores:
            item_data.update({
                'valor': valores[0]
            })


        itens.append(item_data)

    return itens


def extrair_descricao_valores(texto_linha: str):
    """Extrai a descrição e os valores de uma linha da fatura"""
    unidades = ["KWH", "KW", "UN"]

    for un in unidades:
        if un in texto_linha:
            partes = texto_linha.split(un, 1)
            descricao = partes[0].strip()
            valores = partes[1].strip() if len(partes) > 1 else ""
            return descricao, valores

    m_data = re.search(r"\b\d{2}/\d{4}\b", texto_linha)
    if m_data:
        idx = m_data.end()
        resto = texto_linha[idx:]
        m_num = re.search(r"\d+", resto)
        if m_num:
            descricao = texto_linha[: idx + m_num.start()].strip()
            valores = resto[m_num.start():].strip()
            return descricao, valores

    m_num = re.search(r"\d+", texto_linha)
    if m_num:
        descricao = texto_linha[:m_num.start()].strip()
        valores = texto_linha[m_num.start():].strip()
        return descricao, valores

    return texto_linha.strip(), ""


def processar_area_mais_acima(texto: str) -> Dict[str, Any]:
    """Processa a área mais acima"""
    linhas = texto.split('\n')
    resultado = {}

    if len(linhas) >= 2:
        resultado["distribuidora_energia"] = linhas[1].strip()

    if len(linhas) >= 4:
        cep_match = re.search(r'\b\d{5}-?\d{3}\b', linhas[3])
        if cep_match:
            resultado["cep"] = cep_match.group()

    return resultado


def processar_roteiro_tensao(texto: str, pdf_path: str) -> Dict[str, Any]:
    """Processa roteiro e tensão com extração específica do DISP"""
    linhas = [linha.strip() for linha in texto.split('\n') if linha.strip()]
    resultado = {}

    # Extrai DISP da área específica
    resultado["disp"] = extrair_disp_especifico(pdf_path)

    primeira_linha_eh_roteiro = False
    if linhas:
        tem_padrao_roteiro = re.search(r'\b\d+\s*-\s*\d+\s*-\s*\d+\s*-\s*\d+\b', linhas[0])
        tem_palavra_roteiro = 'ROTEIRO:' in linhas[0].upper()
        primeira_linha_eh_roteiro = tem_padrao_roteiro or tem_palavra_roteiro

    if primeira_linha_eh_roteiro and len(linhas) >= 1:
        roteiro_match = re.search(r'ROTEIRO:\s*([\d\s\-]+)', linhas[0], re.IGNORECASE)
        if roteiro_match:
            resultado["roteiro"] = roteiro_match.group(1).strip()
        else:
            resultado["roteiro"] = linhas[0]

    elif len(linhas) >= 2:
        roteiro_match = re.search(r'ROTEIRO:\s*([\d\s\-]+)', linhas[1], re.IGNORECASE)
        if roteiro_match:
            resultado["roteiro"] = roteiro_match.group(1).strip()

    if len(linhas) >= 2:
        for i in range(min(3, len(linhas))):
            matricula_match = re.search(r'MATRÍCULA:\s*([\d\-]+)', linhas[i], re.IGNORECASE)
            if matricula_match:
                resultado["matricula"] = matricula_match.group(1).strip()
                break

    info_classificacao = {}
    texto_classificacao = ""

    for i, linha in enumerate(linhas):
        linha_upper = linha.upper()
        if (re.search(r'CLASSI[TF]', linha_upper) or
                re.search(r'TIPO.*FORNEC', linha_upper) or
                re.search(r'MTC-', linha_upper) or
                re.search(r'B[123]', linha_upper) or
                any(tipo in linha_upper for tipo in ['TRIFASICO', 'BIFASICO', 'MONOFASICO'])):

            texto_classificacao += ' ' + linha
            if len(linhas) > i + 2:
                texto_classificacao += ' ' + ' '.join(linhas[i + 1:i + 3])
            break

    if not texto_classificacao and len(linhas) >= 3:
        texto_classificacao = ' '.join(linhas[-3:])

    if texto_classificacao:
        texto_limpo = texto_classificacao

        texto_limpo = re.sub(r'Classitesgio', 'Classificação', texto_limpo, flags=re.IGNORECASE)
        texto_limpo = re.sub(r'‘ipa de Foracimenta', 'Tipo de Fornecimento', texto_limpo, flags=re.IGNORECASE)
        texto_limpo = re.sub(r'BEASICO', 'BIFASICO', texto_limpo, flags=re.IGNORECASE)
        texto_limpo = re.sub(r'TENBAO NOMMIAL', 'TENSÃO NOMINAL', texto_limpo, flags=re.IGNORECASE)

        ligacao_match = re.search(r'(TRIFASICO|MONOFASICO|BIFASICO)', texto_limpo, re.IGNORECASE)
        if ligacao_match:
            info_classificacao["ligacao"] = ligacao_match.group(1).upper()

        grupo_subgrupo_match = re.search(r'/\s*([A-Z]?)(\d+)', texto_limpo)
        if grupo_subgrupo_match:
            grupo = grupo_subgrupo_match.group(1) or 'B'
            numero = grupo_subgrupo_match.group(2)
            info_classificacao["grupo"] = grupo
            info_classificacao["subgrupo"] = f"{grupo}{numero}"

        if 'subgrupo' in info_classificacao:
            texto_sem_ligacao = texto_limpo
            if 'ligacao' in info_classificacao:
                texto_sem_ligacao = re.sub(info_classificacao["ligacao"], '', texto_sem_ligacao, flags=re.IGNORECASE)

            padrao_classe = re.search(
                rf'{info_classificacao["subgrupo"]}\s+([^/]+)',
                texto_sem_ligacao,
                re.IGNORECASE
            )
            if padrao_classe:
                classe = padrao_classe.group(1).strip()
                classe = re.sub(r'(Classificação|Tipo de Fornecimento):?\s*', '', classe, flags=re.IGNORECASE)
                classe = re.sub(r'/\s*$', '', classe).strip()
                palavras = re.split(r'[\s/]', classe)
                for palavra in palavras:
                    if palavra and palavra not in ['BIFASICO', 'TRIFASICO', 'MONOFASICO']:
                        info_classificacao["classe"] = palavra
                        break

        if info_classificacao:
            resultado["classificacao"] = info_classificacao

    return resultado


def processar_nota_fiscal_protocolo(texto: str) -> Dict[str, Any]:
    """Processa nota fiscal e protocolo"""
    linhas = texto.split('\n')
    resultado = {}

    if len(linhas) >= 1:
        nf_match = re.search(r'\b\d{3}\.\d{3}\.\d{3}\b', linhas[0])
        if nf_match:
            resultado["numero_nota_fiscal"] = nf_match.group()

    if len(linhas) >= 2:
        data_match = re.search(r'\b\d{2}/\d{2}/\d{4}\b', linhas[1])
        if data_match:
            resultado["data_emissao"] = data_match.group()

    if len(linhas) >= 6:
        chave_texto = ' '.join(linhas[5:7])
        chave_match = re.search(r'\b\d{44}\b', chave_texto.replace(' ', ''))
        if chave_match:
            resultado["chave_acesso"] = chave_match.group()

    return resultado


def processar_nome_endereco(texto: str) -> Dict[str, Any]:
    """Processa nome e endereço"""
    linhas = texto.split('\n')
    resultado = {}

    if len(linhas) >= 1:
        resultado["nome_titular"] = linhas[0].strip()

    if len(linhas) >= 2:
        endereco = []
        for i in range(1, min(4, len(linhas))):
            if i < len(linhas):
                endereco.append(linhas[i].strip())

        endereco_completo = ' '.join(endereco)
        resultado["endereco"] = endereco_completo

        # 🔍 Agora procura o CEP no endereço completo
        cep_match = re.search(r'CEP\s*(\d{5}-?\d{3})', endereco_completo)
        resultado["CEP"] = cep_match.group(1) if cep_match else None

    return resultado


def processar_codigo_cliente(texto: str) -> Dict[str, Any]:
    """Processa código do cliente"""
    linhas = texto.split('\n')
    resultado = {}
    #print(linhas)
    if len(linhas) >= 1:
        codigo_completo = re.search(r'[\d/]+-?\d*', linhas[0])
        if codigo_completo:
            resultado["codigo_cliente"] = codigo_completo.group()
        else:
            resultado["codigo_cliente"] = linhas[0].strip()

    return resultado


def processar_cnpj(texto: str) -> dict:
    resultado = {}
    linhas = texto.split('\n')
    match = re.search(r'CNPJ/CPF:\s*([\d.-/]+)', texto)
    if match:
        # Remove caracteres especiais, mantém só números
        numeros_limpos = re.sub(r'[^\d]', '', match.group(1))


    return numeros_limpos


def processar_ref_total_pagar(texto: str) -> Dict[str, Any]:
    """Processa referência e total a pagar"""
    linhas = texto.split('\n')
    resultado = {}

    if linhas:
        linha_principal = linhas[0]

        ref_match = re.search(r'([A-Za-zçÇ]+)\s*/\s*(\d{4})', linha_principal, re.IGNORECASE)
        if ref_match:
            resultado["mes_ano_referencia"] = f"{ref_match.group(1)}/{ref_match.group(2)}"

        vencimento_match = re.search(r'\b\d{2}/\d{2}/\d{4}\b', linha_principal)
        if vencimento_match:
            resultado["data_vencimento"] = vencimento_match.group()

        total_match = re.search(r'R\$\s*([\d.,]+)', linha_principal)
        if total_match:
            resultado["total_pagar"] = total_match.group(1)

    return resultado


def processar_tributos(texto: str) -> Dict[str, Any]:
    """Processa tributos"""
    linhas = texto.split('\n')
    resultado = {}

    if len(linhas) >= 2:
        pis_texto = ' '.join(linhas[0:2])
        pis_valores = re.findall(r'[\d.,]+', pis_texto)
        if len(pis_valores) >= 3:
            resultado["PIS"] = {
                "base_calculo": pis_valores[0],
                "aliquota": pis_valores[1],
                "valor": pis_valores[2]
            }

    if len(linhas) >= 3:
        cofins_valores = re.findall(r'[\d.,]+', linhas[2])
        if len(cofins_valores) >= 3:
            resultado["COFINS"] = {
                "base_calculo": cofins_valores[0],
                "aliquota": cofins_valores[1],
                "valor": cofins_valores[2]
            }

    if len(linhas) >= 4:
        icms_valores = re.findall(r'[\d.,]+', linhas[3])
        if len(icms_valores) >= 3:
            resultado["ICMS"] = {
                "base_calculo": icms_valores[0],
                "aliquota": icms_valores[1],
                "valor": icms_valores[2]
            }

    return resultado


def processar_tributos(texto: str) -> Dict[str, Any]:
    """Processa tributos"""
    linhas = texto.split('\n')
    resultado = {}

    if len(linhas) >= 2:
        pis_texto = ' '.join(linhas[0:2])
        pis_valores = re.findall(r'[\d.,]+', pis_texto)
        if len(pis_valores) >= 3:
            resultado["PIS"] = {
                "base_calculo": pis_valores[0],
                "aliquota": pis_valores[1],
                "valor": pis_valores[2]
            }

    if len(linhas) >= 3:
        cofins_valores = re.findall(r'[\d.,]+', linhas[2])
        if len(cofins_valores) >= 3:
            resultado["COFINS"] = {
                "base_calculo": cofins_valores[0],
                "aliquota": cofins_valores[1],
                "valor": cofins_valores[2]
            }

    if len(linhas) >= 4:
        icms_valores = re.findall(r'[\d.,]+', linhas[3])
        if len(icms_valores) >= 3:
            resultado["ICMS"] = {
                "base_calculo": icms_valores[0],
                "aliquota": icms_valores[1],
                "valor": icms_valores[2]
            }

    return resultado

def processar_regiao_parallel(nome, texto, resultado_parcial):
    """Processa uma região individual em thread"""
    try:
        if nome == "mais_a_cima":
            return "informacoes_superiores", processar_area_mais_acima(texto)
        elif nome == "roteiro_tensao":
            return "roteiro_tensao", processar_roteiro_tensao(texto)
        elif nome == "nota_fiscal_protocolo":
            return "nota_fiscal", processar_nota_fiscal_protocolo(texto)
        elif nome == "nome_endereco":
            return "cliente", processar_nome_endereco(texto)
        elif nome == "codigo_cliente":
            return "codigo_cliente", processar_codigo_cliente(texto)
        elif nome == "ref_total_pagar":
            return "pagamento", processar_ref_total_pagar(texto)
        elif nome == "tributos":
            return "tributos", processar_tributos(texto)
        elif nome == "cnpj":
            # CNPJ precisa esperar o cliente estar pronto
            nome_titular = resultado_parcial.get('cliente', {}).get('nome_titular', '')
            return "cnpj", processar_cnpj(texto, nome_titular)
    except Exception as e:
        return nome, {"erro": f"Erro no processamento: {str(e)}", "texto_bruto": texto}


def extrair_informacoes_json(pdf_path: str) -> Dict[str, Any]:
    """Extrai todas as informações e retorna como JSON com threading"""
    resultado_final = {}

    # Extrair todos os textos primeiro (fora das threads)
    textos_regioes = {}
    for nome, info in regioes.items():
        if nome == "tabela_itens":
            continue  # Tabela será processada separadamente

        retangulo = calcular_retangulo(info["coordenadas"])
        texto = extrair_texto_nas_coordenadas(pdf_path, retangulo)

        if texto.startswith("Erro") or texto == "Nenhum texto encontrado":
            resultado_final[nome] = {"erro": texto}
        else:
            textos_regioes[nome] = texto

    # Processar regiões independentes em paralelo
    regioes_independentes = ["mais_a_cima", "roteiro_tensao", "nota_fiscal_protocolo",
                             "nome_endereco", "codigo_cliente", "ref_total_pagar", "tributos"]

    # Dicionário temporário para resultados parciais (usado pelo CNPJ)
    resultado_parcial = resultado_final.copy()

    with ThreadPoolExecutor(max_workers=4) as executor:
        # Enviar todas as tarefas independentes para execução
        future_to_regiao = {}

        for nome in regioes_independentes:
            if nome in textos_regioes:  # Só processa se tem texto válido
                future = executor.submit(processar_regiao_parallel, nome, textos_regioes[nome], resultado_parcial)
                future_to_regiao[future] = nome

        # Coletar resultados conforme ficam prontos
        for future in concurrent.futures.as_completed(future_to_regiao):
            nome = future_to_regiao[future]
            try:
                chave, resultado = future.result()
                resultado_final[chave] = resultado
                resultado_parcial[chave] = resultado  # Atualiza parcial para o CNPJ
            except Exception as e:
                resultado_final[nome] = {"erro": str(e)}

    # Processar CNPJ (depende do cliente)
    if "cnpj" in textos_regioes and "cliente" in resultado_final:
        resultado_final["cnpj"] = processar_cnpj(textos_regioes["cnpj"])

    # PASSO 4: Processar tabela de itens (fora do threading por ser complexa)
    if "tabela_itens" in regioes:
        try:
            linhas = extrair_texto_por_linhas(pdf_path, regioes["tabela_itens"]["coordenadas"])
            resultado_final["itens_fatura"] = processar_tabela_itens(linhas, pdf_path)
        except Exception as e:
            resultado_final["itens_fatura"] = {"erro": f"Erro na tabela: {str(e)}"}

    return resultado_final

def main():
    caminho_pasta = Path(PASTA_PDFS)
    arquivos_pdf = list(caminho_pasta.glob("*.pdf"))

    if not arquivos_pdf:
        print(f"Nenhum arquivo PDF encontrado na pasta: {PASTA_PDFS}")
        return

    print(f"Encontrados {len(arquivos_pdf)} arquivos PDF para processar")
    print(f"{'=' * 80}")

    # Processa cada arquivo PDF
    for i, caminho_pdf in enumerate(arquivos_pdf, 1):
        print(f"Processando ({i}/{len(arquivos_pdf)}): {caminho_pdf.name}")

        try:
            # Extrai informações estruturadas
            dados_extraidos = extrair_informacoes_json(str(caminho_pdf))

            # Converte para JSON com formatação
            json_output = json.dumps(dados_extraidos, ensure_ascii=False, indent=2)

            # Salva em arquivo JSON
            nome_arquivo_saida = caminho_pdf.stem + "_dados.json"
            caminho_saida = caminho_pdf.parent / nome_arquivo_saida

            print(json_output)
            #with open(caminho_saida, 'w', encoding='utf-8') as f:
            #    f.write(json_output)

            #print(f"✓ Dados salvos em: {caminho_saida}")

        except Exception as e:
            print(f"✗ Erro ao processar {caminho_pdf.name}: {str(e)}")

        print("-" * 80)

    print("Processamento concluído!")


if __name__ == "__main__":
    main()