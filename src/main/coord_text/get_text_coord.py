import fitz  # PyMuPDF
import os

# CONFIGURAÇÃO
CAMINHO_PDF = r"C:\bf_ocr\src\resource\pdf\EMP 22 FL 8B01001-2789122-NOTA FISCAL Nº 020.663.927 - Série 002 ok.pdf"

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
                        "descricao": "Referência e total a pagar"}
    #"tributos": {"coordenadas": [(444.1, 376.2), (563.6, 374.8), (445.4, 407.4), (566.3, 406.1)],
    #             "descricao": "Tributos"},
}


def calcular_retangulo(coordenadas):
    x_coords = [coord[0] for coord in coordenadas]
    y_coords = [coord[1] for coord in coordenadas]
    return fitz.Rect(min(x_coords), min(y_coords), max(x_coords), max(y_coords))


def extrair_texto(pdf_path, retangulo):
    try:
        doc = fitz.open(pdf_path)
        pagina = doc[0]
        texto = pagina.get_text("text", clip=retangulo).strip()
        doc.close()
        return texto
    except Exception as e:
        return f"Erro: {str(e)}"


def mostrar_tabela(texto, titulo):
    print(f"\n{'=' * 80}")
    print(f"TEXTO COMPLETO - {titulo.upper()}")
    print(f"{'=' * 80}")
    print(f"'{texto}'")
    print(f"{'=' * 80}")

    linhas = [linha.strip() for linha in texto.split('\n') if linha.strip()]

    for linha in linhas:
        if any(palavra in linha for palavra in ['KWH', 'KW', 'UN', 'R$', '%']):
            print(linha)
        elif len(linha) > 30 and any(c.isdigit() for c in linha):
            print(linha)


def main():
    for nome, info in regioes.items():
        retangulo = calcular_retangulo(info["coordenadas"])
        texto = extrair_texto(CAMINHO_PDF, retangulo)

        print(f"\n{info['descricao']}:")
        print("-" * 40)

        if texto and not texto.startswith("Erro"):
            if nome in ["itens_fatura", "tributos"]:
                # Mostra o texto completo para debug

                # Mostra também formatado
                print(f"\nTEXTO FORMATADO - {info['descricao'].upper()}:")
                print("-" * 50)
                linhas = [linha.strip() for linha in texto.split('\n') if linha.strip()]
                for i, linha in enumerate(linhas):
                    print(f"{i + 1:2d}: {linha}")
            else:
                print(texto)
        else:
            print("Nenhum texto encontrado ou erro na extração")


if __name__ == "__main__":
    main()