import pypdf
from pathlib import Path

def extract_pdf_to_txt(pdf_path: Path, txt_path: Path):
    reader = pypdf.PdfReader(pdf_path)
    with open(txt_path, "w", encoding="utf-8") as f:
        # Extraer solo las primeras 15 páginas y las últimas 15 páginas para entender la estructura
        total = len(reader.pages)
        f.write(f"=== PDF METADATA ===\nNumber of pages: {total}\n\n")
        
        f.write("=== FIRST 15 PAGES ===\n")
        for idx in range(min(15, total)):
            f.write(f"\n--- PAGE {idx + 1} ---\n")
            f.write(reader.pages[idx].extract_text() or "")
            
        if total > 15:
            f.write("\n\n=== LAST 15 PAGES ===\n")
            start = max(15, total - 15)
            for idx in range(start, total):
                f.write(f"\n--- PAGE {idx + 1} ---\n")
                f.write(reader.pages[idx].extract_text() or "")
            
    print(f"Extracted preview of {pdf_path} to {txt_path}")

if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parents[2]
    pdf = root_dir / "Proyecto de Titulo - EJEMPLO PILAR Y NICHOLAS.pdf"
    txt = root_dir / "thesis_carrasco_rivera_summary.txt" # Reusamos este txt para no crear nuevos
    extract_pdf_to_txt(pdf, txt)
