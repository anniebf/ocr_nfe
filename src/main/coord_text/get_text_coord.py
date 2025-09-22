import pdfplumber
import os

# CONFIGURAÇÃO
CAMINHO_PDF = r"C:\bf_ocr\src\resource\pdf\EMP 16 FL 1001001-2703074-NOTA FISCAL Nº 020.429.962 - Série 002 - OK.pdf"

# Regiões a serem extraídas
regioes = {
    "mais_a_cima": {"coordenadas": [(139.9, 4.1), (142.6, 46.2), (465.8, 42.1), (461.7, 6.8)],
                    "descricao": "Área mais acima"},
    "roteiro_tensao": {"coordenadas": [(43.5, 81.5), (40.7, 157.5), (319.1, 150.7), (306.9, 84.2)],
                       "descricao": "Roteiro e tensão"},
    "nota_fiscal_protocolo": {"coordenadas": [(422.4, 196.9), (423.7, 282.5), (559.5, 279.8), (559.5, 202.4)],
                              "descricao": "Nota fiscal e protocolo"},
    "nome_endereco": {"coordenadas": [(47.5, 158.9), (40.7, 243.1), (236.3, 160.3), (233.6, 244.5)],
                      "descricao": "Nome e endereço"},
    "codigo_cliente": {"coordenadas": [(236.3, 182.0), (237.7, 213.2), (331.4, 211.9), (334.1, 184.7)],
                       "descricao": "Código do cliente"},
    "ref_total_pagar": {"coordenadas": [(44.8, 260.7), (46.2, 285.2), (320.5, 282.5), (325.9, 252.6)],
                        "descricao": "Referência e total a pagar"},
    "tributos": {"coordenadas": [(444.1, 376.2), (563.6, 374.8), (445.4, 407.4), (566.3, 406.1)],
                 "descricao": "Tributos"},
}


def calcular_retangulo(coordenadas):
    """Converte coordenadas em um retângulo (x0, top, x1, bottom)"""
    x_coords = [coord[0] for coord in coordenadas]
    y_coords = [coord[1] for coord in coordenadas]
    return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))


def extrair_texto_pdfplumber(pdf_path, retangulo):
    """Extrai texto usando pdfplumber com tratamento melhor das quebras de linha"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pagina = pdf.pages[0]

            # Extrai texto dentro do retângulo
            texto_extraido = pagina.within_bbox(retangulo).extract_text()

            # Processa o texto para remover quebras de linha desnecessárias
            if texto_extraido:
                # Remove quebras de linha que não fazem sentido (baseado em algumas heurísticas)
                linhas = texto_extraido.split('\n')
                texto_processado = []

                for i, linha in enumerate(linhas):
                    linha = linha.strip()
                    if not linha:
                        continue

                    # Se a linha atual é muito curta e a próxima linha não começa com maiúscula/número,
                    # provavelmente é uma quebra indesejada
                    if (i < len(linhas) - 1 and len(linha) < 30 and
                            linha and not linha.endswith(('.', ':', ';')) and
                            linhas[i + 1].strip() and not linhas[i + 1].strip()[0].isupper() and
                            not linhas[i + 1].strip()[0].isdigit()):
                        texto_processado.append(linha + ' ' + linhas[i + 1].strip())
                        # Pula a próxima linha já que foi concatenada
                        linhas[i + 1] = ''
                    else:
                        texto_processado.append(linha)

                return '\n'.join(texto_processado)

            return texto_extraido or "Nenhum texto encontrado"

    except Exception as e:
        return f"Erro: {str(e)}"


def extrair_texto_com_layout(pdf_path, retangulo):
    """Alternativa: extrai texto mantendo informações de layout para melhor análise"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pagina = pdf.pages[0]

            # Extrai palavras com suas coordenadas
            palavras = pagina.within_bbox(retangulo).extract_words(
                x_tolerance=3,  # Tolerância para juntar palavras próximas
                y_tolerance=3,
                keep_blank_chars=False,
                use_text_flow=True  # Tenta seguir o fluxo natural do texto
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
                # Ordena palavras na linha por coordenada x
                palavras_na_linha = sorted(linhas[y], key=lambda x: x[0])
                linha_texto = ' '.join([palavra[1] for palavra in palavras_na_linha])
                texto_ordenado.append(linha_texto)

            return '\n'.join(texto_ordenado)

    except Exception as e:
        return f"Erro: {str(e)}"


def mostrar_texto_formatado(texto, titulo):
    """Exibe o texto de forma organizada"""
    print(f"\n{'=' * 80}")
    print(f"{titulo.upper()}")
    print(f"{'=' * 80}")

    if texto.startswith("Erro") or texto == "Nenhum texto encontrado":
        print(texto)
    else:
        linhas = texto.split('\n')
        for i, linha in enumerate(linhas):
            if linha.strip():  # Só mostra linhas não vazias
                print(f"{i + 1:2d}: {linha}")

    print(f"{'=' * 80}")


def main():
    print(f"Processando PDF: {os.path.basename(CAMINHO_PDF)}")
    print(f"{'=' * 80}")

    for nome, info in regioes.items():
        retangulo = calcular_retangulo(info["coordenadas"])

        # Tenta primeiro o método com layout melhorado
        texto = extrair_texto_com_layout(CAMINHO_PDF, retangulo)

        # Se não deu bom, tenta o método simples
        if texto == "Nenhum texto encontrado" or texto.startswith("Erro"):
            texto = extrair_texto_pdfplumber(CAMINHO_PDF, retangulo)

        mostrar_texto_formatado(texto, info["descricao"])


if __name__ == "__main__":
    main()