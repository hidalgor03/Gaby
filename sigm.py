import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import HexColor, black
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from PIL import Image
import os

# ========================= CONFIG STREAMLIT =========================
st.set_page_config(
    page_title="Generador de Certificados - Codelco Gabriela Mistral",
    layout="centered"
)

st.title("🎓 Generador de Certificados - Codelco Gabriela Mistral")

# ========================= PARÁMETROS BASE =========================
PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)   
MARGEN = 50

# Colores mejorados
NARANJO_DEF = "#E76227"        
TEXTO_SEC_DEF = "#4A4A4A"
GRIS_CLARO = "#E8E8E8"

# Textos fijos 
TITULO_PRINCIPAL_DEF = "DIPLOMA"
FRASE_OTORGA_DEF = "Se otorga el presente certificado a:"
FRASE_CURSO_DEF = "Por haber completado satisfactoriamente el curso:"

# ========================= SIDEBAR: AJUSTES =========================
with st.sidebar:
    st.header("⚙️ Ajustes del diseño")

    # Colores
    col_color1, col_color2 = st.columns(2)
    with col_color1:
        color_naranjo_hex = st.color_picker("Color principal", NARANJO_DEF)
    with col_color2:
        color_texto_hex = st.color_picker("Color secundario", TEXTO_SEC_DEF)

    # Tipos/tamaños base
    tam_titulo = st.slider("Tamaño título", 28, 52, 38, 1)
    tam_otorga = st.slider("Tamaño 'Se otorga…'", 12, 24, 15, 1)
    tam_nombre = st.slider("Tamaño NOMBRE", 24, 48, 34, 1)
    tam_frase_curso = st.slider("Tamaño 'Por haber completado…'", 12, 24, 15, 1)
    tam_curso = st.slider("Tamaño TÍTULO DEL CURSO", 16, 32, 22, 1)

    # Posiciones (eje Y; X centrado para textos)
    y_titulo = st.number_input("Y Título", value=int(PAGE_HEIGHT-100), step=5)
    y_otorga = st.number_input("Y 'Se otorga…'", value=int(PAGE_HEIGHT-165), step=5)
    y_nombre = st.number_input("Y Nombre", value=int(PAGE_HEIGHT-215), step=5)
    y_frase_curso = st.number_input("Y 'Por haber completado…'", value=int(PAGE_HEIGHT-280), step=5)
    y_curso = st.number_input("Y Curso (línea 1)", value=int(PAGE_HEIGHT-320), step=5)
    interlineado_curso = st.slider("Interlineado curso (pts)", 18, 40, 26, 1)

    # Logo
    st.subheader("🖼️ Logo")
    logo_x = st.number_input("Logo X", value=int(230), step=5)
    logo_y = st.number_input("Logo Y", value=int(40), step=5)
    logo_ancho_max = st.number_input("Logo ancho máx", value=400, step=5)
    logo_alto_max = st.number_input("Logo alto máx", value=400, step=5)

    # Decoración
    st.subheader("🧩 Decoración")
    mostrar_borde = st.checkbox("Mostrar borde decorativo", value=True)
    grosor_borde = st.slider("Grosor borde (pts)", 1, 5, 2, 1)
    distancia_borde = st.slider("Distancia del borde (pts)", 15, 40, 25, 1)

    mostrar_lineas = st.checkbox("Líneas decorativas", value=False)
    grosor_linea = st.slider("Grosor líneas (pts)", 1, 4, 2, 1)

    # Guías
    mostrar_guias = st.checkbox("Mostrar guías de margen/centro", value=False)

# ========================= INPUTS PRINCIPALES =========================
col1, col2 = st.columns(2)
with col1:
    nombre = st.text_input("Nombre del/la participante", value="")
with col2:
    curso = st.text_input("Título del curso", value="")

# Información adicional
col3, col4 = st.columns(2)
with col3:
    fecha = st.text_input("Fecha (opcional)", value="")


# Textos editables del template
with st.expander("📝 Textos del template"):
    titulo_principal = st.text_input("Título principal", value=TITULO_PRINCIPAL_DEF)
    frase_otorga = st.text_input("Frase de otorgamiento", value=FRASE_OTORGA_DEF)
    frase_curso = st.text_input("Frase del curso", value=FRASE_CURSO_DEF)

# Logo (archivo local por defecto + opción de subir)
logo_subido = st.file_uploader("Subir logo (PNG/JPG) — opcional", type=["png", "jpg", "jpeg"])
ruta_logo_local = "logo_codelco_gm.png"

# ========================= FUNCIONES AUXILIARES =========================
def draw_centered_string(c, text, y, font_name="Helvetica", font_size=16, color=black, y_offset=0):
    """Versión mejorada que acepta offset vertical."""
    c.setFont(font_name, font_size)
    c.setFillColor(color)
    text_width = pdfmetrics.stringWidth(text, font_name, font_size)
    x = (PAGE_WIDTH - text_width) / 2
    c.drawString(x, y + y_offset, text)

def draw_right_aligned_string(c, text, x_right, y, font_name="Helvetica", font_size=12, color=black):
    c.setFont(font_name, font_size)
    c.setFillColor(color)
    text_width = pdfmetrics.stringWidth(text, font_name, font_size)
    c.drawString(x_right - text_width, y, text)

def fit_font_size(text, max_width, base_size, min_size=12, font_name="Helvetica-Bold"):
    """Reduce el tamaño de fuente hasta que quepa en max_width."""
    size = base_size
    while size >= min_size:
        if pdfmetrics.stringWidth(text, font_name, size) <= max_width:
            return size
        size -= 1
    return min_size

def wrap_text(text, max_width, font_name="Helvetica", font_size=16):
    """Divide el texto en líneas sin superar max_width."""
    words = text.split()
    lines, current = [], []
    for w in words:
        test = " ".join(current + [w]) if current else w
        if pdfmetrics.stringWidth(test, font_name, font_size) <= max_width:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    return lines

def draw_image_fit(c, pil_img, x, y, max_w, max_h):
    """Dibuja imagen manteniendo proporción para encajar en el rectángulo."""
    iw, ih = pil_img.size
    ratio = min(max_w / iw, max_h / ih)
    w, h = iw * ratio, ih * ratio
    c.drawImage(ImageReader(pil_img), x, y, width=w, height=h, mask='auto')

def draw_decorative_border(c, color, width, distance):
    """Dibuja un borde decorativo doble alrededor del certificado."""
    c.setStrokeColor(color)
    c.setLineWidth(width)

    # Borde exterior
    c.rect(distance, distance, PAGE_WIDTH - 2*distance, PAGE_HEIGHT - 2*distance)

    # Borde interior (más delgado)
    c.setLineWidth(width * 0.5)
    inner_dist = distance + 6
    c.rect(inner_dist, inner_dist, PAGE_WIDTH - 2*inner_dist, PAGE_HEIGHT - 2*inner_dist)

def draw_decorative_lines(c, y_pos, color, width):
    """Dibuja líneas decorativas horizontales."""
    c.setStrokeColor(color)
    c.setLineWidth(width)

    # Líneas a los lados del contenido
    line_length = 80
    center_gap = 120

    x_left = (PAGE_WIDTH - center_gap) / 2 - line_length
    x_right = (PAGE_WIDTH + center_gap) / 2

    c.line(x_left, y_pos, x_left + line_length, y_pos)
    c.line(x_right, y_pos, x_right + line_length, y_pos)

def generar_pdf(nombre, curso, fecha_texto, logo_bytes=None):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))

    color_naranjo = HexColor(color_naranjo_hex)
    color_texto = HexColor(color_texto_hex)
    color_gris = HexColor(GRIS_CLARO)

    # ====== BORDE DECORATIVO ======
    if mostrar_borde:
        draw_decorative_border(c, color_naranjo, grosor_borde, distancia_borde)

    # ====== GUÍAS (opcional) ======
    if mostrar_guias:
        c.setStrokeColor(HexColor("#cccccc"))
        c.setLineWidth(0.5)
        c.line(MARGEN, 0, MARGEN, PAGE_HEIGHT)
        c.line(PAGE_WIDTH - MARGEN, 0, PAGE_WIDTH - MARGEN, PAGE_HEIGHT)
        c.line(0, MARGEN, PAGE_WIDTH, MARGEN)
        c.line(0, PAGE_HEIGHT - MARGEN, PAGE_WIDTH, PAGE_HEIGHT - MARGEN)
        c.setStrokeColor(HexColor("#bbbbbb"))
        c.line(PAGE_WIDTH/2, 0, PAGE_WIDTH/2, PAGE_HEIGHT)

    # ====== LOGO ======
    try:
        pil_logo = None
        if logo_bytes is not None:
            pil_logo = Image.open(BytesIO(logo_bytes.read()))
        elif os.path.exists(ruta_logo_local):
            pil_logo = Image.open(ruta_logo_local)

        if pil_logo is not None:
            draw_image_fit(c, pil_logo, logo_x, logo_y, logo_ancho_max, logo_alto_max)
    except Exception as e:
        print("No se pudo colocar el logo:", e)

    # ====== TÍTULO ======
    draw_centered_string(c, titulo_principal, y_titulo, "Helvetica-Bold", tam_titulo, color_naranjo)

    # Líneas decorativas bajo el título
    if mostrar_lineas:
        draw_decorative_lines(c, y_titulo - 18, color_naranjo, grosor_linea)

    # ====== FRASE OTORGA ======
    draw_centered_string(c, frase_otorga, y_otorga, "Helvetica", tam_otorga, color_texto)

    # ====== NOMBRE (auto-escala) ======
    nombre_texto = nombre.strip().upper() if nombre else "NOMBRE DEL/DE LA PARTICIPANTE"
    max_ancho_texto = PAGE_WIDTH - (MARGEN * 3)
    tam_nombre_fit = fit_font_size(nombre_texto, max_ancho_texto, tam_nombre, min_size=18, font_name="Helvetica-Bold")
    draw_centered_string(c, nombre_texto, y_nombre, "Helvetica-Bold", tam_nombre_fit, color_naranjo)

    # Línea sutil bajo el nombre
    c.setStrokeColor(color_gris)
    c.setLineWidth(1)
    line_width = min(pdfmetrics.stringWidth(nombre_texto, "Helvetica-Bold", tam_nombre_fit) + 40, PAGE_WIDTH - MARGEN * 3)
    x_start = (PAGE_WIDTH - line_width) / 2
    c.line(x_start, y_nombre - 8, x_start + line_width, y_nombre - 8)

    # ====== FRASE CURSO ======
    draw_centered_string(c, frase_curso, y_frase_curso, "Helvetica", tam_frase_curso, color_texto)

    # ====== TÍTULO DEL CURSO (con wrap) ======
    curso_texto = curso.strip() if curso else "TÍTULO DEL CURSO"
    lineas_curso = wrap_text(curso_texto, max_ancho_texto, "Helvetica-Bold", tam_curso)
    y_actual = y_curso
    for linea in lineas_curso:
        draw_centered_string(c, linea, y_actual, "Helvetica-Bold", tam_curso, HexColor("#2C2C2C"))
        y_actual -= interlineado_curso

    # ====== FECHA Y LUGAR (en la parte inferior) ======
    y_footer = 90

    if fecha_texto:
        if mostrar_lineas:
            # Línea decorativa superior al footer
            draw_decorative_lines(c, y_footer + 35, color_gris, 1)

        col_width = PAGE_WIDTH / 2

        if fecha_texto:
            # Fecha a la izquierda
            x_fecha = col_width / 2
            draw_centered_string(c, "Fecha", x_fecha, "Helvetica-Bold", 11, color_texto)
            draw_centered_string(c, fecha_texto, x_fecha, "Helvetica", 10, HexColor("#666666"), y_offset=-15)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ========================= BOTÓN DE GENERACIÓN =========================
if st.button("📄 Generar certificado", type="primary"):
    if not nombre or not curso:
        st.warning("⚠️ Completa **Nombre** y **Título del curso** para generar el certificado.")
    else:
        logo_stream = None
        if logo_subido is not None:
            data = logo_subido.read()
            logo_stream = BytesIO(data)

        pdf_bytes = generar_pdf(nombre, curso, fecha, logo_bytes=logo_stream)

        st.success("✅ Certificado generado correctamente.")
        st.download_button(
            label="⬇️ Descargar PDF",
            data=pdf_bytes,
            file_name=f"Certificado_{nombre.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )

st.caption("💡 Ajusta posiciones y tamaños en la barra lateral para personalizar el diseño.")