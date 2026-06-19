from fpdf import FPDF

# Inicializar el objeto PDF
pdf = FPDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=15)

# Configurar la fuente (fpdf usa fuentes estándar por defecto)
pdf.set_font("Arial", size=11)

# Nombre de tu archivo de origen
archivo_txt = "PT_JoaquinContreras.txt"

# Leer el archivo de texto y escribirlo en el PDF
with open(archivo_txt, "r", encoding="utf-8") as file:
    for linea in file:
        # multi_cell asegura que el texto se ajuste a los márgenes
        # encode/decode ayuda a evitar errores con caracteres latinos (tildes, ñ) en fpdf
        texto_limpio = linea.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 8, txt=texto_limpio)

# Exportar el resultado
pdf.output("PT_JoaquinContreras_Restaurado.pdf")
print("¡Archivo PDF generado con éxito!")