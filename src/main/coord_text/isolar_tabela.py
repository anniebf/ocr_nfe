import fitz  # PyMuPDF
import pandas as pd
import pytesseract
from PIL import Image
import cv2
import numpy as np
import io
import matplotlib.pyplot as plt
from pytesseract import Output
import os
import tabula  # Import correto para tabula


def extract_high_quality_table(pdf_path, coordinates, page_number=0, dpi=300):
    """
    Extrai tabela de PDF com alta resolução usando OCR
    """
    try:
        # Abrir PDF
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_number)

        # Criar matriz de transformação para alta resolução
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)

        # Definir área de extração
        rect = fitz.Rect(coordinates[0][0], coordinates[0][1],
                         coordinates[1][0], coordinates[1][1])

        # Renderizar a área específica com alta resolução
        pix = page.get_pixmap(matrix=mat, clip=rect)
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))

        # Converter para OpenCV format
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        # Pré-processamento de imagem para melhor OCR
        processed_img = preprocess_image(img_cv)

        # Usar Tesseract OCR
        custom_config = r'--oem 3 --psm 6'
        ocr_data = pytesseract.image_to_data(processed_img, config=custom_config, output_type=Output.DICT, lang='por')

        # Processar resultados do OCR
        table_data = process_ocr_results(ocr_data, img.shape[1])

        return table_data

    except Exception as e:
        print(f"Erro na extração OCR: {e}")
        return pd.DataFrame()


def preprocess_image(img):
    """
    Pré-processa a imagem para melhorar a qualidade do OCR
    """
    # Converter para escala de cinza
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Aplicar filtro para reduzir ruído
    denoised = cv2.fastNlMeansDenoising(gray)

    # Aumentar contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast_enhanced = clahe.apply(denoised)

    # Binarização adaptativa
    binary = cv2.adaptiveThreshold(contrast_enhanced, 255,
                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)

    return binary


def process_ocr_results(ocr_data, image_width):
    """
    Processa os resultados do OCR e organiza em estrutura tabular
    """
    n_boxes = len(ocr_data['text'])
    rows = {}

    for i in range(n_boxes):
        if int(ocr_data['conf'][i]) > 50:  # Confiança mínima de 50%
            text = ocr_data['text'][i].strip()
            if text:
                x = ocr_data['left'][i]
                y = ocr_data['top'][i]
                w = ocr_data['width'][i]
                h = ocr_data['height'][i]

                # Determinar a coluna baseada na posição x
                col_position = int(x / (image_width / 15))  # Divide em 15 colunas

                # Determinar a linha baseada na posição y
                row_key = y // (h * 1.2)  # Agrupa por linhas

                if row_key not in rows:
                    rows[row_key] = {}

                # Adicionar texto à coluna apropriada
                if col_position not in rows[row_key]:
                    rows[row_key][col_position] = text
                else:
                    rows[row_key][col_position] += " " + text

    # Converter para DataFrame
    if rows:
        sorted_rows = sorted(rows.items())
        table_rows = []

        for row_key, columns in sorted_rows:
            sorted_cols = sorted(columns.items())
            row_data = [col_text for _, col_text in sorted_cols]
            table_rows.append(row_data)

        df = pd.DataFrame(table_rows)
        return df

    return pd.DataFrame()


def alternative_tabula_extraction(pdf_path, coordinates, page_number=0):
    """
    Método alternativo usando Tabula com alta resolução - CORRIGIDO
    """
    try:
        # Converter coordenadas para formato Tabula [y1, x1, y2, x2]
        area = [
            coordinates[0][1],  # top (y1)
            coordinates[0][0],  # left (x1)
            coordinates[1][1],  # bottom (y2)
            coordinates[1][0]  # right (x2)
        ]

        print(f"Extraindo com Tabula na área: {area}")

        # Extrair tabela com Tabula - MÉTODO CORRETO
        tables = tabula.read_pdf(
            pdf_path,
            pages=page_number + 1,
            area=[area],
            multiple_tables=True,
            guess=False,
            lattice=True  # Para tabelas com linhas
        )

        if tables:
            print(f"Tabula encontrou {len(tables)} tabela(s)")
            return tables[0]
        else:
            print("Tabula não encontrou tabelas na área especificada")
            return pd.DataFrame()

    except Exception as e:
        print(f"Erro no Tabula: {e}")
        return pd.DataFrame()


def visualize_extraction_area(pdf_path, coordinates, page_number=0, dpi=150):
    """
    Visualiza a área de extração
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_number)

        # Renderizar com boa resolução para visualização
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)

        # Renderizar página completa
        pix_full = page.get_pixmap(matrix=mat)
        img_full_data = pix_full.tobytes("png")
        img_full = Image.open(io.BytesIO(img_full_data))

        # Converter coordenadas
        scale = zoom
        x0, y0 = int(coordinates[0][0] * scale), int(coordinates[0][1] * scale)
        x1, y1 = int(coordinates[1][0] * scale), int(coordinates[1][1] * scale)

        # Desenhar retângulo
        img_array = np.array(img_full)
        cv2.rectangle(img_array, (x0, y0), (x1, y1), (255, 0, 0), 3)

        plt.figure(figsize=(12, 15))
        plt.imshow(img_array)
        plt.title("Área de Extração (vermelho)")
        plt.axis('off')
        plt.show()

    except Exception as e:
        print(f"Erro na visualização: {e}")


# Exemplo de uso
if __name__ == "__main__":
    # Configurações
    pdf_path =  r"C:\bf_ocr\src\resource\pdf\EMP 16 FL 1001001-2703074-NOTA FISCAL Nº 020.429.962 - Série 002 - OK.pdf"  # Substitua pelo seu arquivo
    coordenadas = [(32.6, 347.7), (445.4, 457.7)]
    pagina = 0
    dpi = 400

    # Verificar se arquivo existe
    if not os.path.exists(pdf_path):
        print(f"Arquivo {pdf_path} não encontrado!")
        print("Por favor, verifique o caminho do arquivo.")
    else:
        print(f"Processando arquivo: {pdf_path}")

        # Visualizar área de extração
        print("Visualizando área de extração...")
        visualize_extraction_area(pdf_path, coordenadas, pagina, dpi=150)

        # Extrair tabela com OCR
        print("Extraindo tabela com OCR de alta qualidade...")
        tabela_ocr = extract_high_quality_table(pdf_path, coordenadas, pagina, dpi)

        if not tabela_ocr.empty:
            print("Tabela extraída com OCR:")
            print(tabela_ocr)
            csv_path_ocr = "tabela_alta_qualidade_ocr.csv"
            tabela_ocr.to_csv(csv_path_ocr, index=False, encoding='utf-8-sig')
            print(f"Salvo como: {os.path.abspath(csv_path_ocr)}")
        else:
            print("OCR não conseguiu extrair a tabela.")

        # Método alternativo com Tabula
        print("Tentando extração com Tabula...")
        tabela_tabula = alternative_tabula_extraction(pdf_path, coordenadas, pagina)

        if not tabela_tabula.empty:
            print("Tabela extraída com Tabula:")
            print(tabela_tabula)
            csv_path_tabula = "tabela_tabula.csv"
            tabela_tabula.to_csv(csv_path_tabula, index=False, encoding='utf-8-sig')
            print(f"Salvo como: {os.path.abspath(csv_path_tabula)}")
        else:
            print("Tabula também não conseguiu extrair a tabela.")

        # Mostrar onde os arquivos foram salvos
        print("\n" + "=" * 50)
        print("Arquivos salvos no diretório:")
        print(f"Diretório atual: {os.getcwd()}")

        # Listar arquivos CSV
        csv_files = [f for f in os.listdir() if f.endswith('.csv')]
        if csv_files:
            print("Arquivos CSV encontrados:")
            for file in csv_files:
                print(f"- {os.path.abspath(file)}")
        else:
            print("Nenhum arquivo CSV foi criado.")