#!/usr/bin/env python3
"""
Script para converter arquivos PDF em Markdown.

Este script utiliza PyMuPDF (fitz) para extrair texto de arquivos PDF
e convertê-lo para formato Markdown, preservando a estrutura e formatação.

Autor: Aristides Henrique Gonçalves da Cruz
Email: arihenriquedev@hotmail.com
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Erro: PyMuPDF não está instalado.")
    print("Execute: pip install PyMuPDF")
    sys.exit(1)


class PDFToMarkdownConverter:
    """Conversor de PDF para Markdown."""

    def __init__(self, preserve_formatting: bool = True, extract_images: bool = False):
        """
        Inicializa o conversor.

        Args:
            preserve_formatting: Se deve preservar formatação (negrito, itálico)
            extract_images: Se deve extrair imagens do PDF
        """
        self.preserve_formatting = preserve_formatting
        self.extract_images = extract_images
        self.extracted_images = []  # Lista para armazenar informações das imagens

    def _html_to_markdown(self, html_text: str) -> str:
        """
        Converte HTML básico para Markdown.

        Args:
            html_text: Texto HTML a ser convertido

        Returns:
            Texto em formato Markdown
        """
        import re

        # Remove tags HTML básicas e converte para Markdown
        text = html_text

        # Converte negrito
        text = re.sub(r"<b>(.*?)</b>", r"**\1**", text)
        text = re.sub(r"<strong>(.*?)</strong>", r"**\1**", text)

        # Converte itálico
        text = re.sub(r"<i>(.*?)</i>", r"*\1*", text)
        text = re.sub(r"<em>(.*?)</em>", r"*\1*", text)

        # Converte quebras de linha
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"<p>", "\n\n", text)
        text = re.sub(r"</p>", "\n", text)

        # Remove outras tags HTML
        text = re.sub(r"<[^>]+>", "", text)

        # Decodifica entidades HTML básicas
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")

        return text

    def _extract_images_from_page(
        self, page, page_num: int, output_dir: str
    ) -> List[dict]:
        """
        Extrai imagens de uma página específica do PDF.

        Args:
            page: Página do PDF (objeto fitz.Page)
            page_num: Número da página
            output_dir: Diretório para salvar as imagens

        Returns:
            Lista de dicionários com informações das imagens extraídas
        """
        images_info = []

        try:
            # Obtém lista de imagens na página
            image_list = page.get_images()
            drawings = page.get_drawings()

            # Se há desenhos mas não há imagens, renderiza a página como imagem
            if len(drawings) > 0 and len(image_list) == 0:
                print(
                    f"  📄 Página {page_num + 1} contém elementos gráficos - renderizando como imagem..."
                )

                # Renderiza a página como imagem com alta resolução
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom para melhor qualidade
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")

                # Define nome do arquivo
                img_filename = f"pagina_{page_num+1}.png"
                img_path = os.path.join(output_dir, img_filename)

                # Salva a imagem
                with open(img_path, "wb") as img_file:
                    img_file.write(img_data)

                # Armazena informações da imagem
                img_info = {
                    "filename": img_filename,
                    "path": img_path,
                    "page": page_num + 1,
                    "index": 1,
                    "size": len(img_data),
                    "type": "page_render",
                }
                images_info.append(img_info)

                print(f"  ✓ Página renderizada: {img_filename} ({len(img_data)} bytes)")
                pix = None  # Libera memória

            # Extrai imagens tradicionais se existirem
            for img_index, img in enumerate(image_list):
                # Obtém referência da imagem
                xref = img[0]

                # Extrai a imagem
                pix = fitz.Pixmap(page.parent, xref)

                # Converte para PNG se necessário
                if pix.n - pix.alpha < 4:  # GRAY ou RGB
                    img_data = pix.tobytes("png")
                    img_ext = "png"
                else:  # CMYK: converte para RGB primeiro
                    pix1 = fitz.Pixmap(fitz.csRGB, pix)
                    img_data = pix1.tobytes("png")
                    img_ext = "png"
                    pix1 = None

                # Define nome do arquivo
                img_filename = f"imagem_p{page_num+1}_{img_index+1}.{img_ext}"
                img_path = os.path.join(output_dir, img_filename)

                # Salva a imagem
                with open(img_path, "wb") as img_file:
                    img_file.write(img_data)

                # Armazena informações da imagem
                img_info = {
                    "filename": img_filename,
                    "path": img_path,
                    "page": page_num + 1,
                    "index": img_index + 1,
                    "size": len(img_data),
                    "type": "embedded_image",
                }
                images_info.append(img_info)

                print(f"  ✓ Imagem extraída: {img_filename} ({len(img_data)} bytes)")

                pix = None  # Libera memória

        except Exception as e:
            print(f"  ⚠ Erro ao extrair imagens da página {page_num + 1}: {e}")

        return images_info

    def extract_text_from_pdf(self, pdf_path: str, output_dir: str = None) -> List[str]:
        """
        Extrai texto de todas as páginas do PDF.

        Args:
            pdf_path: Caminho para o arquivo PDF
            output_dir: Diretório para salvar imagens (se extract_images=True)

        Returns:
            Lista de strings com o texto de cada página
        """
        try:
            doc = fitz.open(pdf_path)
            pages_text = []

            # Limpa lista de imagens extraídas
            self.extracted_images = []

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)

                # Extrai imagens se solicitado
                if self.extract_images and output_dir:
                    print(f"Extraindo imagens da página {page_num + 1}...")
                    page_images = self._extract_images_from_page(
                        page, page_num, output_dir
                    )
                    self.extracted_images.extend(page_images)

                if self.preserve_formatting:
                    # Extrai texto com formatação HTML e converte para Markdown
                    text = page.get_text("html")
                    # Converte HTML básico para Markdown
                    text = self._html_to_markdown(text)
                else:
                    # Extrai texto simples
                    text = page.get_text()

                pages_text.append(text)

            doc.close()
            return pages_text

        except Exception as e:
            print(f"Erro ao processar PDF: {e}")
            import traceback

            traceback.print_exc()
            return []

    def clean_markdown_text(self, text: str) -> str:
        """
        Limpa e melhora o texto Markdown extraído.

        Args:
            text: Texto Markdown bruto

        Returns:
            Texto Markdown limpo
        """
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            # Remove linhas vazias excessivas
            if line.strip() == "" and cleaned_lines and cleaned_lines[-1].strip() == "":
                continue

            # Remove espaços em branco no final
            line = line.rstrip()

            # Melhora formatação de títulos
            if line.startswith("#"):
                # Adiciona espaço após #
                line = line.replace("#", "# ", 1)

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _add_image_references_to_text(
        self, text: str, images_dir_name: str = None
    ) -> str:
        """
        Adiciona referências às imagens extraídas no texto Markdown.

        Args:
            text: Texto Markdown original
            images_dir_name: Nome do diretório das imagens para incluir no caminho

        Returns:
            Texto Markdown com referências às imagens
        """
        if not self.extracted_images:
            return text

        # Cria seção de imagens no final do texto
        images_section = "\n\n## Imagens Extraídas\n\n"

        for img_info in self.extracted_images:
            # Define o caminho da imagem (com pasta se especificada)
            if images_dir_name:
                image_path = f"{images_dir_name}/{img_info['filename']}"
            else:
                image_path = img_info["filename"]

            # Cria referência da imagem em Markdown
            if img_info.get("type") == "page_render":
                img_reference = (
                    f"![Página {img_info['page']} renderizada]"
                    f"({image_path})\n\n"
                    f"*Página {img_info['page']} renderizada como imagem "
                    f"({img_info['size']} bytes)*\n\n"
                )
            else:
                img_reference = (
                    f"![Imagem da página {img_info['page']} - {img_info['filename']}]"
                    f"({image_path})\n\n"
                    f"*Figura {img_info['index']} da página {img_info['page']} "
                    f"({img_info['size']} bytes)*\n\n"
                )
            images_section += img_reference

        return text + images_section

    def convert_pdf_to_markdown(
        self, pdf_path: str, output_path: Optional[str] = None
    ) -> bool:
        """
        Converte um arquivo PDF para Markdown.

        Args:
            pdf_path: Caminho para o arquivo PDF
            output_path: Caminho para o arquivo de saída (opcional)

        Returns:
            True se a conversão foi bem-sucedida, False caso contrário
        """
        if not os.path.exists(pdf_path):
            print(f"Erro: Arquivo PDF não encontrado: {pdf_path}")
            return False

        # Define o caminho de saída se não fornecido
        if output_path is None:
            pdf_file = Path(pdf_path)
            # Cria pasta referencias se não existir
            referencias_dir = Path("referencias")
            referencias_dir.mkdir(exist_ok=True)
            output_path = referencias_dir / f"{pdf_file.stem}.md"

        print(f"Convertendo: {pdf_path}")
        print(f"Saída: {output_path}")

        # Cria diretório para imagens se necessário
        images_dir = None
        if self.extract_images:
            # Usa o mesmo diretório do arquivo de saída
            output_file = Path(output_path)
            images_dir = output_file.parent / f"{output_file.stem}_imagens"
            images_dir.mkdir(exist_ok=True)
            print(f"Diretório de imagens: {images_dir}")

        # Extrai texto do PDF
        pages_text = self.extract_text_from_pdf(
            pdf_path, str(images_dir) if images_dir else None
        )

        if not pages_text:
            print("Erro: Não foi possível extrair texto do PDF")
            return False

        # Combina todas as páginas
        full_text = "\n\n---\n\n".join(pages_text)

        # Limpa o texto
        cleaned_text = self.clean_markdown_text(full_text)

        # Adiciona referências às imagens se foram extraídas
        if self.extract_images and self.extracted_images:
            images_dir_name = images_dir.name if images_dir else None
            cleaned_text = self._add_image_references_to_text(
                cleaned_text, images_dir_name
            )

        # Adiciona cabeçalho com metadados
        pdf_name = Path(pdf_path).stem
        datetime_str = (
            __import__("datetime").datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        )

        # Adiciona informação sobre imagens no cabeçalho se aplicável
        images_info = ""
        if self.extract_images and self.extracted_images:
            images_info = (
                f"\n> Imagens extraídas: {len(self.extracted_images)} arquivo(s)"
            )

        header = f"""# {pdf_name}

> Convertido automaticamente de PDF para Markdown
>
> Arquivo original: `{pdf_path}`
> Data de conversão: {datetime_str}{images_info}

---

"""

        final_text = header + cleaned_text

        # Salva o arquivo
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_text)

            success_msg = f"✓ Conversão concluída: {output_path}"
            if self.extract_images and self.extracted_images:
                success_msg += f" ({len(self.extracted_images)} imagens extraídas)"
            print(success_msg)
            return True

        except Exception as e:
            print(f"Erro ao salvar arquivo: {e}")
            return False


def main():
    """Função principal do script."""
    parser = argparse.ArgumentParser(
        description="Converte arquivos PDF para Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python pdf_to_markdown.py documento.pdf
  python pdf_to_markdown.py documento.pdf -o saida.md
  python pdf_to_markdown.py documento.pdf --no-formatting
  python pdf_to_markdown.py *.pdf  # Múltiplos arquivos
        """,
    )

    parser.add_argument("pdf_files", nargs="+", help="Arquivo(s) PDF para converter")

    parser.add_argument(
        "-o",
        "--output",
        help="Arquivo de saída (padrão: mesmo nome do PDF com extensão .md)",
    )

    parser.add_argument(
        "--no-formatting",
        action="store_true",
        help="Não preservar formatação (texto simples)",
    )

    parser.add_argument(
        "--extract-images",
        action="store_true",
        help="Extrair imagens (funcionalidade futura)",
    )

    args = parser.parse_args()

    # Cria o conversor
    converter = PDFToMarkdownConverter(
        preserve_formatting=not args.no_formatting,
        extract_images=args.extract_images,
    )

    # Processa cada arquivo PDF
    success_count = 0
    total_files = len(args.pdf_files)

    for pdf_file in args.pdf_files:
        print(f"\n[{success_count + 1}/{total_files}] Processando: {pdf_file}")

        if converter.convert_pdf_to_markdown(pdf_file, args.output):
            success_count += 1

        # Se foi especificado um arquivo de saída específico,
        # só processa o primeiro arquivo
        if args.output:
            break

    print(
        f"\n✓ Conversão concluída: {success_count}/{total_files} "
        f"arquivos processados com sucesso"
    )

    if success_count < total_files:
        sys.exit(1)


if __name__ == "__main__":
    main()
