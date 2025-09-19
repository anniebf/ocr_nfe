import pdfplumber
import os
import re
import json
import pandas as pd
from typing import Dict, Any, List, Tuple
from pathlib import Path

# CONFIGURAÇÃO
PASTA_PDFS = r"C:\bf_ocr\src\resource\pdf"
ARQUIVO_EXCEL_SAIDA = r"C:\bf_ocr\src\resource\pdf\faturas_processadas_botzin.xlsx"

# Regiões a serem extraídas
regioes = {
    "mais_a_cima": {"coordenadas": [(139.9, 4.1), (142.6, 46.2), (465.8, 42.1), (461.7, 6.8)],
                    "descricao": "Área mais acima"},
    "roteiro_tensao": {"coordenadas": [(43.5, 81.5), (40.7, 157.5), (319.1, 150.7), (306.9, 84.2)],
                       "descricao": "Roteiro e tensão"},
    "nota_fiscal_protocolo": {"coordenadas": [(422.4, 196.9), (423.7, 282.5), (559.5, 279.8), (559.5, 202.4)],
                              "descricao": "Nota fiscal e protocolo"},
    "nome_endereco": {"coordenadas": [(42.1, 160.3), (44.8, 201.0), (232.2, 196.9), (229.5, 163.0)],
                      "descricao": "Nome e endereço"},
    "codigo_cliente": {"coordenadas": [(236.3, 182.0), (237.7, 213.2), (331.4, 211.9), (334.1, 184.7)],
                       "descricao": "Código do cliente"},
    "ref_total_pagar": {"coordenadas": [(44.8, 260.7), (46.2, 285.2), (320.5, 282.5), (325.9, 252.6)],
                        "descricao": "Referência e total a pagar"},
    "tributos": {"coordenadas": [(444.1, 376.2), (563.6, 374.8), (445.4, 407.4), (566.3, 406.1)],
                 "descricao": "Tributos"},
    "tabela_itens": {"coordenadas": [(21.7, 361.2), (444.1, 571.7)],
                     "descricao": "Tabela de itens da fatura"}
}


def calcular_retangulo(coordenadas):
    """Converte coordenadas em um retângulo (x0, top, x1, bottom)"""
    if len(coordenadas) == 2:  # Para a tabela de itens com formato diferente
        return (coordenadas[0][0], coordenadas[0][1], coordenadas[1][0], coordenadas[1][1])
    else:  # Para as outras regiões com 4 coordenadas
        x_coords = [coord[0] for coord in coordenadas]
        y_coords = [coord[1] for coord in coordenadas]
        return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))


def extrair_texto_com_layout(pdf_path, retangulo):
    """Extrai texto mantendo informações de layout para melhor análise"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pagina = pdf.pages[0]

            # Extrai palavras com suas coordenadas
            palavras = pagina.within_bbox(retangulo).extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=False,
                use_text_flow=True
            )

            if not palavras:
                return "Nenhum texto encontrado"

            # Agrupa palavras por linha baseado na coordenada y
            linhas = {}
            for palavra in palavras:
                y = round(palavra['top'])
                if y not in linhas:
                    linhas[y] = []
                linhas[y].append((palavra['x0'], palavra['text']))

            # Ordena as linhas e constrói o texto
            texto_ordenado = []
            for y in sorted(linhas.keys()):
                palavras_na_linha = sorted(linhas[y], key=lambda x: x[0])
                linha_texto = ' '.join([palavra[1] for palavra in palavras_na_linha])
                texto_ordenado.append(linha_texto)

            return '\n'.join(texto_ordenado)

    except Exception as e:
        return f"Erro: {str(e)}"


def extrair_texto_por_linhas(pdf_path, coordenadas, pagina=0):
    """Extrai texto por linhas de uma área específica do PDF (para tabela de itens)"""
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
    """Processa a tabela de itens da fatura aplicando regras unificadas para descrição"""
    itens = []

    if not linhas:
        return itens

    for linha in linhas:
        texto_linha = linha['text'].strip()

        # Ignorar linhas sem números
        if not re.search(r"\d", texto_linha):
            continue

        # Ignorar linhas que começam com TOTAL:
        if texto_linha.upper().startswith("TOTAL:"):
            continue

        descricao, valores_str = extrair_descricao_valores(texto_linha)

        # Extrair valores numéricos
        valores = re.findall(r"-?\d{1,3}(?:\.\d{3})*(?:,\d+)?|-?\d+", valores_str)

        item_data = {'descricao': descricao}

        # Preencher os valores nas colunas corretas
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
            # Para outros casos, colocar o primeiro valor na coluna 'valor'
            item_data.update({
                'valor': valores[0]
            })

        itens.append(item_data)

    return itens


def extrair_descricao_valores(texto_linha: str):
    """
    Extrai a descrição e os valores de uma linha da fatura
    seguindo as regras:
      1. Se tiver unidade (KWH, KW, UN) → descrição vai até a unidade
      2. Se tiver data (xx/xxxx) → descrição vai até o primeiro número após a data
      3. Se não tiver data/unidade, mas tiver número → descrição vai até o primeiro número
      4. Caso contrário, descrição = linha inteira
    """
    unidades = ["KWH", "KW", "UN"]

    # Caso 1 → linha contém unidade
    for un in unidades:
        if un in texto_linha:
            partes = texto_linha.split(un, 1)
            descricao = partes[0].strip()
            valores = partes[1].strip() if len(partes) > 1 else ""
            return descricao, valores

    # Caso 2 → contém data (xx/xxxx)
    m_data = re.search(r"\b\d{2}/\d{4}\b", texto_linha)
    if m_data:
        # pega a parte até logo depois da data
        idx = m_data.end()
        resto = texto_linha[idx:]
        m_num = re.search(r"\d+", resto)
        if m_num:
            descricao = texto_linha[: idx + m_num.start()].strip()
            valores = resto[m_num.start():].strip()
            return descricao, valores

    # Caso 3 → não tem data/unidade, mas tem número
    m_num = re.search(r"\d+", texto_linha)
    if m_num:
        descricao = texto_linha[:m_num.start()].strip()
        valores = texto_linha[m_num.start():].strip()
        return descricao, valores

    # Caso 4 → fallback
    return texto_linha.strip(), ""


def processar_area_mais_acima(texto: str) -> Dict[str, Any]:
    """Processa a área mais acima"""
    linhas = texto.split('\n')
    resultado = {}

    if len(linhas) >= 2:
        resultado["distribuidora_energia"] = linhas[1].strip()

    if len(linhas) >= 4:
        # Extrai apenas o CEP (números de contato não serão usados)
        cep_match = re.search(r'\b\d{5}-?\d{3}\b', linhas[3])
        if cep_match:
            resultado["cep"] = cep_match.group()

    return resultado


def processar_roteiro_tensao(texto: str) -> Dict[str, Any]:
    """Processa roteiro e tensão"""
    linhas = texto.split('\n')
    resultado = {}

    if len(linhas) >= 1:
        # Pega somente os números do roteiro
        roteiro_numeros = re.search(r'\b\d+\b', linhas[0])
        if roteiro_numeros:
            resultado["roteiro"] = roteiro_numeros.group()
        else:
            resultado["roteiro"] = linhas[0].strip()

    if len(linhas) >= 2:
        # Extrai matrícula (normalmente números)
        matricula_match = re.search(r'\b\d+\b', linhas[1])
        if matricula_match:
            resultado["matricula"] = matricula_match.group()

    if len(linhas) >= 4:
        classificacao = []
        for i in range(3, min(6, len(linhas))):  # linhas 4, 5 e 6 (índices 3, 4, 5)
            if i < len(linhas):
                classificacao.append(linhas[i].strip())
        texto_classificacao = ' '.join(classificacao)

        # Extrai informações específicas da classificação
        info_classificacao = {}

        # Extrai ligação (palavra após "LIGAÇÃO:")
        ligacao_match = re.search(r'LIGAÇÃO:\s*([^/]+)', texto_classificacao, re.IGNORECASE)
        if ligacao_match:
            info_classificacao["ligacao"] = ligacao_match.group(1).strip()

        # Extrai grupo (primeira letra após o primeiro /)
        grupo_match = re.search(r'/\s*([A-Za-z])', texto_classificacao)
        if grupo_match:
            info_classificacao["grupo"] = grupo_match.group(1)

        # Extrai subgrupo (3 caracteres após o /)
        subgrupo_match = re.search(r'/\s*([A-Za-z0-9]{3})', texto_classificacao)
        if subgrupo_match:
            info_classificacao["subgrupo"] = subgrupo_match.group(1)

        # Extrai classe (palavra após o grupo)
        if 'subgrupo' in info_classificacao:
            classe_match = re.search(rf'{info_classificacao["subgrupo"]}\s+([^/]+)', texto_classificacao)
            if classe_match:
                info_classificacao["classe"] = classe_match.group(1).strip()

        resultado["classificacao"] = info_classificacao

    if len(linhas) >= 7:
        disp_match = re.search(r'DISP\s*[:]?\s*(\d+)', linhas[6], re.IGNORECASE)
        if disp_match:
            resultado["disp"] = disp_match.group(1)
        else:
            resultado["disp"] = ""

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
        resultado["endereco"] = ' '.join(endereco)

    return resultado


def processar_codigo_cliente(texto: str) -> Dict[str, Any]:
    """Processa código do cliente"""
    linhas = texto.split('\n')
    resultado = {}

    if len(linhas) >= 1:
        codigo_completo = re.search(r'[\d/]+', linhas[0])
        if codigo_completo:
            resultado["codigo_cliente"] = codigo_completo.group()
        else:
            resultado["codigo_cliente"] = linhas[0].strip()

    return resultado


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


def extrair_informacoes_json(pdf_path: str) -> Dict[str, Any]:
    """Extrai todas as informações e retorna como JSON"""
    resultado_final = {}

    for nome, info in regioes.items():
        retangulo = calcular_retangulo(info["coordenadas"])

        if nome == "tabela_itens":
            linhas = extrair_texto_por_linhas(pdf_path, info["coordenadas"])
            resultado_final["itens_fatura"] = processar_tabela_itens(linhas, pdf_path)
            continue

        texto = extrair_texto_com_layout(pdf_path, retangulo)

        if texto.startswith("Erro") or texto == "Nenhum texto encontrado":
            resultado_final[nome] = {"erro": texto}
            continue

        try:
            if nome == "mais_a_cima":
                resultado_final["informacoes_superiores"] = processar_area_mais_acima(texto)
            elif nome == "roteiro_tensao":
                resultado_final["roteiro_tensao"] = processar_roteiro_tensao(texto)
            elif nome == "nota_fiscal_protocolo":
                resultado_final["nota_fiscal"] = processar_nota_fiscal_protocolo(texto)
            elif nome == "nome_endereco":
                resultado_final["cliente"] = processar_nome_endereco(texto)
            elif nome == "codigo_cliente":
                resultado_final["codigo_cliente"] = processar_codigo_cliente(texto)
            elif nome == "ref_total_pagar":
                resultado_final["pagamento"] = processar_ref_total_pagar(texto)
            elif nome == "tributos":
                resultado_final["tributos"] = processar_tributos(texto)

        except Exception as e:
            resultado_final[nome] = {"erro": f"Erro no processamento: {str(e)}", "texto_bruto": texto}

    return resultado_final


def criar_dataframe_consolidado(dados_todos_pdfs: List[Tuple[str, Dict[str, Any]]]) -> pd.DataFrame:
    """Cria um DataFrame consolidado com todos os dados dos PDFs"""
    linhas_consolidadas = []

    for caminho_pdf, dados in dados_todos_pdfs:
        linha = {}

        # Informações básicas do arquivo
        linha['caminho_arquivo'] = str(caminho_pdf)
        linha['nome_arquivo'] = caminho_pdf.name

        # Informações gerais
        info_gerais = dados.get('informacoes_superiores', {})
        linha.update({f'{k}': v for k, v in info_gerais.items()})

        # Roteiro e tensão
        roteiro = dados.get('roteiro_tensao', {})
        linha.update({f'{k}': v for k, v in roteiro.items() if k != 'classificacao'})

        classificacao = roteiro.get('classificacao', {})
        linha.update({f'{k}': v for k, v in classificacao.items()})

        # Nota fiscal
        nota_fiscal = dados.get('nota_fiscal', {})
        linha.update({f'nota_fiscal_{k}': v for k, v in nota_fiscal.items()})

        # Cliente
        cliente = dados.get('cliente', {})
        linha.update({f'{k}': v for k, v in cliente.items()})

        # Código do cliente
        codigo_cliente = dados.get('codigo_cliente', {})
        linha.update({f'{k}': v for k, v in codigo_cliente.items()})

        # Pagamento
        pagamento = dados.get('pagamento', {})
        linha.update({f'{k}': v for k, v in pagamento.items()})

        # Tributos (colunas separadas para PIS, COFINS, ICMS)
        tributos = dados.get('tributos', {})
        for tributo, valores in tributos.items():
            if isinstance(valores, dict):
                for chave, valor in valores.items():
                    linha[f'tributo_{tributo.lower()}_{chave}'] = valor

        # Itens da fatura (cada item em colunas separadas)
        itens = dados.get('itens_fatura', [])
        for i, item in enumerate(itens):
            for chave, valor in item.items():
                linha[f'{chave}'] = valor

        linhas_consolidadas.append(linha)

    return pd.DataFrame(linhas_consolidadas)



def main():
    caminho_pasta = Path(PASTA_PDFS)
    arquivos_pdf = list(caminho_pasta.glob("*.pdf"))

    if not arquivos_pdf:
        print(f"Nenhum arquivo PDF encontrado na pasta: {PASTA_PDFS}")
        return

    print(f"Encontrados {len(arquivos_pdf)} arquivos PDF para processar")
    print(f"{'=' * 80}")

    dados_todos_pdfs = []

    # Processa cada arquivo PDF
    for i, caminho_pdf in enumerate(arquivos_pdf, 1):
        print(f"Processando ({i}/{len(arquivos_pdf)}): {caminho_pdf.name}")


        # Extrai informações estruturadas
        dados_extraidos = extrair_informacoes_json(caminho_pdf)

        # Converte para JSON com formatação
        json_output = json.dumps(dados_extraidos, ensure_ascii=False, indent=2)

        print("DADOS EXTRAÍDOS (JSON):")
        print(json_output)

        # Salva em arquivo (opcional)
        #nome_arquivo_saida = os.path.splitext(os.path.basename(CAMINHO_PDF))[0] + "_dados.json"
        #caminho_saida = os.path.join(os.path.dirname(CAMINHO_PDF), nome_arquivo_saida)

        #with open(caminho_saida, 'w', encoding='utf-8') as f:
        #    f.write(json_output)

        #print(f"\nDados salvos em: {caminho_saida}")


if __name__ == "__main__":
    main()