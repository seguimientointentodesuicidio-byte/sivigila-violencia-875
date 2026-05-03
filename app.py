"""
SIVIGILA - Vigilancia Violencia de Género e Intrafamiliar | Valle del Cauca
Evento 875 - SIN componente sexual (solo Física, Psicológica, Negligencia y Abandono)
Secretaría Departamental de Salud del Valle del Cauca

Aplicativo web hermano del SIVIGILA 356 (Conducta Suicida).
Stack: Streamlit + Google Sheets (gspread) + Plotly
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import hashlib
import io
import time

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

st.set_page_config(
    page_title="SIVIGILA - Violencia 875 | Valle del Cauca",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

COLOR_AZUL_OSCURO = "#1B3A5C"
COLOR_AZUL_MEDIO = "#2E6B9E"
COLOR_BLANCO = "#FFFFFF"
COLOR_GRIS_CLARO = "#F0F2F6"
COLOR_ROJO_ALERTA = "#D32F2F"
COLOR_AMARILLO_ALERTA = "#F9A825"

st.markdown(f"""
<style>
    .main-header {{
        background: linear-gradient(135deg, {COLOR_AZUL_OSCURO}, {COLOR_AZUL_MEDIO});
        color: white;
        padding: 1.2rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        text-align: center;
    }}
    .main-header h1 {{ font-size: 1.6rem; margin: 0; font-weight: 700; }}
    .main-header p {{ font-size: 0.9rem; margin: 0.3rem 0 0 0; opacity: 0.9; }}

    .kpi-card {{
        background: white;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid {COLOR_AZUL_OSCURO};
    }}
    .kpi-card .kpi-value {{
        font-size: 2.2rem;
        font-weight: 800;
        color: {COLOR_AZUL_OSCURO};
        line-height: 1.1;
    }}
    .kpi-card .kpi-label {{
        font-size: 0.8rem;
        color: #666;
        margin-top: 0.3rem;
        font-weight: 500;
    }}
    .kpi-card-danger {{ border-left-color: {COLOR_ROJO_ALERTA}; }}
    .kpi-card-danger .kpi-value {{ color: {COLOR_ROJO_ALERTA}; }}
    .kpi-card-warning {{ border-left-color: {COLOR_AMARILLO_ALERTA}; }}
    .kpi-card-warning .kpi-value {{ color: {COLOR_AMARILLO_ALERTA}; }}

    .alerta-roja {{
        background: #FFEBEE;
        border-left: 4px solid {COLOR_ROJO_ALERTA};
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.5rem;
    }}
    .alerta-amarilla {{
        background: #FFF8E1;
        border-left: 4px solid {COLOR_AMARILLO_ALERTA};
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.5rem;
    }}

    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {COLOR_AZUL_OSCURO} 0%, #0D2137 100%);
    }}
    [data-testid="stSidebar"] * {{ color: white !important; }}

    .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
    .stTabs [data-baseweb="tab"] {{
        background: {COLOR_GRIS_CLARO};
        border-radius: 8px 8px 0 0;
        padding: 0.5rem 1.5rem;
    }}

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)

# ============================================================
# LISTAS DE DATOS (Constantes)
# ============================================================

MUNICIPIOS_VALLE = [
    "ALCALA", "ANDALUCIA", "ANSERMANUEVO", "ARGELIA", "BOLIVAR",
    "BUENAVENTURA", "BUGA", "BUGALAGRANDE", "CAICEDONIA", "CALI",
    "CALIMA-DARIEN", "CANDELARIA", "CARTAGO", "DAGUA", "EL AGUILA",
    "EL CAIRO", "EL CERRITO", "EL DOVIO", "FLORIDA", "GINEBRA",
    "GUACARI", "JAMUNDI", "LA CUMBRE", "LA UNION", "LA VICTORIA",
    "OBANDO", "PALMIRA", "PRADERA", "RESTREPO", "RIOFRIO",
    "ROLDANILLO", "SAN PEDRO", "SEVILLA", "TORO", "TRUJILLO",
    "TULUA", "ULLOA", "VERSALLES", "VIJES", "YOTOCO", "YUMBO", "ZARZAL"
]

EPS_LISTA = [
    "ALIANSALUD", "ANAS WAYUU EPSI", "ASMET SALUD",
    "ASOCIACIÓN INDÍGENA DEL CAUCA EPSI", "CAJACOPI ATLÁNTICO",
    "CAPITAL SALUD", "CAPRESOCA", "COMFACHOCÓ", "COMFAORIENTE",
    "COMFENALCO VALLE", "COMPENSAR", "COOSALUD",
    "DUSAKAWI EPSI", "EMSSANAR",
    "EPM (EMPRESAS PÚBLICAS DE MEDELLÍN)", "EPS FAMILIAR DE COLOMBIA",
    "FAMISANAR", "FONDO PASIVO SOCIAL FERROCARRILES",
    "MALLAMAS EPSI", "MUTUAL SER", "NUEVA EPS",
    "PIJAOS SALUD EPSI", "SALUD MÍA", "SALUD TOTAL",
    "SANITAS", "SAVIA SALUD",
    "SOS (SERVICIO OCCIDENTAL DE SALUD)", "SURA",
    "OTRA (especificar)"
]

CURSOS_VIDA = [
    "Primera infancia (0-5 años)",
    "Infancia (6-11 años)",
    "Adolescencia (12-17 años)",
    "Juventud (18-28 años)",
    "Adultez (29-59 años)",
    "Vejez (60+ años)"
]

TIPOS_DOCUMENTO = ["RC", "TI", "CC", "CE", "PA", "MS", "AS", "PE", "CN", "CD", "SC", "DE", "PT"]

ESTADOS_CASO = [
    "ACTIVO", "CERRADO", "EN SEGUIMIENTO",
    "REMITIDO A OTRA EPS", "FALLECIDO", "SIN CONTACTO"
]

# Esquema reducido (33 columnas) - alineado con ficha SIVIGILA 875 pura
COLUMNAS_DATOS = [
    "id", "fecha_digitacion", "funcionario_reporta",
    "eps_reporta", "semana_epidemiologica", "antec_violencia",
    "nombres", "apellidos", "tipo_documento", "numero_documento",
    "edad", "sexo", "curso_vida", "municipio_residencia",
    "fecha_evento", "upgd_atencion", "municipio_atencion", "fecha_atencion",
    "atencion_salud_mental", "fecha_salud_mental",
    "remision_proteccion", "reporte_autoridades",
    "seguimiento_1", "seguimiento_2", "seguimiento_3",
    "ruta_atencion_integral", "asiste_servicios", "num_seguimientos_realizados",
    "abandono_proceso", "reincidencia_nuevo_evento", "estado_caso", "observaciones",
    "ultima_modificacion_por", "ultima_modificacion_fecha"
]


def calcular_curso_vida(edad):
    """Calcula el curso de vida a partir de la edad."""
    try:
        edad = int(edad) if edad else 0
    except (ValueError, TypeError):
        edad = 0
    if edad <= 5:
        return "Primera infancia (0-5 años)"
    elif edad <= 11:
        return "Infancia (6-11 años)"
    elif edad <= 17:
        return "Adolescencia (12-17 años)"
    elif edad <= 28:
        return "Juventud (18-28 años)"
    elif edad <= 59:
        return "Adultez (29-59 años)"
    else:
        return "Vejez (60+ años)"


# ============================================================
# FUNCIONES DE CONEXIÓN A GOOGLE SHEETS
# ============================================================

def obtener_conexion_gsheets():
    """Conecta a Google Sheets usando las credenciales en st.secrets."""
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(st.secrets["spreadsheet_id"])
        return spreadsheet
    except Exception as e:
        st.error(f"❌ Error al conectar con Google Sheets: {str(e)}")
        return None


def obtener_hoja_datos(spreadsheet):
    """Retorna la hoja 'DATOS' (la crea si no existe)."""
    try:
        return spreadsheet.worksheet("DATOS")
    except gspread.exceptions.WorksheetNotFound:
        hoja = spreadsheet.add_worksheet(title="DATOS", rows=2000, cols=len(COLUMNAS_DATOS))
        hoja.append_row(COLUMNAS_DATOS, table_range="A1")
        return hoja


def obtener_hoja_usuarios(spreadsheet):
    """Retorna la hoja 'USUARIOS' (la crea si no existe)."""
    try:
        return spreadsheet.worksheet("USUARIOS")
    except gspread.exceptions.WorksheetNotFound:
        hoja = spreadsheet.add_worksheet(title="USUARIOS", rows=100, cols=5)
        hoja.append_row(["usuario", "password_hash", "nombre_completo", "rol", "eps_asignada"])
        return hoja


# ============================================================
# FUNCIONES DE DATOS (CRUD)
# ============================================================

def cargar_datos(spreadsheet, forzar=False):
    """Carga todos los registros de la hoja DATOS como DataFrame, con caché manual."""
    ahora = time.time()
    cache_key = "_datos_cache"
    cache_time_key = "_datos_cache_time"

    if not forzar and cache_key in st.session_state:
        if ahora - st.session_state.get(cache_time_key, 0) < 60:
            return st.session_state[cache_key]

    try:
        hoja = obtener_hoja_datos(spreadsheet)
        all_values = hoja.get_all_values()
        if len(all_values) > 1:
            num_cols = len(COLUMNAS_DATOS)
            datos = [(row + [''] * num_cols)[:num_cols] for row in all_values[1:]]
            df = pd.DataFrame(datos, columns=COLUMNAS_DATOS)
            df = df[df.apply(lambda row: any(str(v).strip() != '' for v in row), axis=1)]
        else:
            df = pd.DataFrame(columns=COLUMNAS_DATOS)
        st.session_state[cache_key] = df
        st.session_state[cache_time_key] = ahora
        return df
    except Exception as e:
        st.error(f"❌ Error al cargar datos: {str(e)}")
        return pd.DataFrame(columns=COLUMNAS_DATOS)


def col_num_a_letra(n):
    """Convierte número de columna (1-indexado) a letra(s) de Excel."""
    resultado = ""
    while n > 0:
        n, residuo = divmod(n - 1, 26)
        resultado = chr(65 + residuo) + resultado
    return resultado


def generar_id():
    """Genera un ID único basado en timestamp."""
    return f"VG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{int(time.time()*1000) % 10000}"


def guardar_registro(spreadsheet, datos_dict):
    """Guarda un nuevo registro en la hoja DATOS."""
    try:
        hoja = obtener_hoja_datos(spreadsheet)
        datos_dict["id"] = generar_id()
        datos_dict["fecha_digitacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        datos_dict["ultima_modificacion_por"] = datos_dict.get("funcionario_reporta", "")
        datos_dict["ultima_modificacion_fecha"] = datos_dict["fecha_digitacion"]

        fila = [str(datos_dict.get(col, "")) for col in COLUMNAS_DATOS]
        hoja.append_row(fila, value_input_option="USER_ENTERED", table_range="A1")

        if "_datos_cache_time" in st.session_state:
            st.session_state["_datos_cache_time"] = 0

        return True, datos_dict["id"]
    except Exception as e:
        return False, str(e)


def actualizar_registro(spreadsheet, id_registro, datos_dict, usuario_modifica):
    """Actualiza un registro existente buscando por ID."""
    try:
        hoja = obtener_hoja_datos(spreadsheet)
        celdas_col_a = hoja.col_values(1)
        fila_num = None
        for i, valor in enumerate(celdas_col_a):
            if valor.strip() == str(id_registro).strip():
                fila_num = i + 1
                break

        if fila_num is None:
            return False, "Registro no encontrado."

        datos_dict["ultima_modificacion_por"] = usuario_modifica
        datos_dict["ultima_modificacion_fecha"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        fila = [str(datos_dict.get(col, "")) for col in COLUMNAS_DATOS]
        rango = f"A{fila_num}:{col_num_a_letra(len(COLUMNAS_DATOS))}{fila_num}"
        hoja.update(rango, [fila], value_input_option="USER_ENTERED")

        if "_datos_cache_time" in st.session_state:
            st.session_state["_datos_cache_time"] = 0

        return True, "Actualizado correctamente."
    except Exception as e:
        return False, str(e)


def buscar_por_documento(df, numero_doc):
    """Busca pacientes por número de documento."""
    if df.empty:
        return pd.DataFrame()
    numero_doc = str(numero_doc).strip()
    return df[df["numero_documento"].astype(str).str.strip() == numero_doc]


# ============================================================
# FUNCIONES DE AUTENTICACIÓN
# ============================================================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def verificar_credenciales(spreadsheet, usuario, password):
    try:
        hoja = obtener_hoja_usuarios(spreadsheet)
        registros = hoja.get_all_records()
        password_hash = hash_password(password)

        for reg in registros:
            if (reg.get("usuario", "").strip().lower() == usuario.strip().lower()
                    and reg.get("password_hash", "").strip() == password_hash):
                return True, {
                    "usuario": reg["usuario"],
                    "nombre_completo": reg.get("nombre_completo", usuario),
                    "rol": reg.get("rol", "EPS").upper(),
                    "eps_asignada": reg.get("eps_asignada", "")
                }
        return False, None
    except Exception as e:
        st.error(f"Error de autenticación: {str(e)}")
        return False, None


def crear_usuario(spreadsheet, usuario, password, nombre_completo, rol, eps_asignada):
    try:
        hoja = obtener_hoja_usuarios(spreadsheet)
        registros = hoja.get_all_records()
        for reg in registros:
            if reg.get("usuario", "").strip().lower() == usuario.strip().lower():
                return False, "El usuario ya existe."
        password_hash = hash_password(password)
        hoja.append_row([usuario, password_hash, nombre_completo, rol, eps_asignada])
        return True, "Usuario creado exitosamente."
    except Exception as e:
        return False, str(e)


def filtrar_por_rol(df):
    if st.session_state.get("rol") == "SECRETARÍA":
        return df
    eps_usuario = st.session_state.get("eps_asignada", "")
    if eps_usuario and not df.empty:
        return df[df["eps_reporta"] == eps_usuario]
    return df


# ============================================================
# LOGIN
# ============================================================

def mostrar_login():
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("Imagen1.png", width=250)
        except Exception:
            st.markdown(f"""
            <div style="text-align:center; padding:1rem;">
                <h2 style="color:{COLOR_AZUL_OSCURO};">🛡️ Gobernación del Valle del Cauca</h2>
                <p style="color:#666;">Secretaría Departamental de Salud</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="text-align:center; margin-bottom:1.5rem;">
            <h3 style="color:{COLOR_AZUL_OSCURO}; margin-bottom:0.2rem;">
                SIVIGILA - Violencia de Género e Intrafamiliar
            </h3>
            <p style="color:#888; font-size:0.85rem;">Evento 875 | Valle del Cauca</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            usuario = st.text_input("👤 Usuario", placeholder="Ingrese su usuario")
            password = st.text_input("🔒 Contraseña", type="password", placeholder="Ingrese su contraseña")
            submitted = st.form_submit_button("🔑 Ingresar", use_container_width=True)
            if submitted:
                if not usuario or not password:
                    st.error("⚠️ Ingrese usuario y contraseña.")
                else:
                    spreadsheet = obtener_conexion_gsheets()
                    if spreadsheet:
                        valido, datos_usuario = verificar_credenciales(spreadsheet, usuario, password)
                        if valido:
                            st.session_state["autenticado"] = True
                            st.session_state["usuario"] = datos_usuario["usuario"]
                            st.session_state["nombre_completo"] = datos_usuario["nombre_completo"]
                            st.session_state["rol"] = datos_usuario["rol"]
                            st.session_state["eps_asignada"] = datos_usuario["eps_asignada"]
                            st.rerun()
                        else:
                            st.error("❌ Credenciales incorrectas.")

        st.markdown("""
        <div style="text-align:center; margin-top:2rem; color:#aaa; font-size:0.75rem;">
            <p>Sistema de vigilancia epidemiológica - Uso institucional exclusivo</p>
            <p>Secretaría Departamental de Salud | Gobernación del Valle del Cauca</p>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# SIDEBAR
# ============================================================

def mostrar_sidebar():
    with st.sidebar:
        try:
            st.image("Imagen1.png", width=200)
        except Exception:
            st.markdown("### 🛡️ Gobernación del Valle del Cauca")

        st.markdown("---")
        st.markdown(f"**👤 {st.session_state.get('nombre_completo', '')}**")
        st.markdown(f"🏷️ Rol: **{st.session_state.get('rol', '')}**")
        if st.session_state.get("rol") == "EPS":
            st.markdown(f"🏥 EPS: **{st.session_state.get('eps_asignada', '')}**")
        st.markdown("---")

        opciones = [
            "📊 Tablero de Control",
            "📝 Registrar Nuevo Caso",
            "✏️ Editar / Actualizar Caso",
            "📥 Exportar Datos"
        ]
        if st.session_state.get("rol") == "SECRETARÍA":
            opciones.append("📂 Carga Masiva")
            opciones.append("⚙️ Gestionar Usuarios")

        # Si hay redirección desde duplicado, forzar página de edición
        idx_default = 0
        if st.session_state.get("_ir_a_edicion"):
            idx_default = opciones.index("✏️ Editar / Actualizar Caso")

        pagina = st.radio("Navegación", opciones, label_visibility="collapsed", index=idx_default)

        st.markdown("---")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        st.markdown("""
        <div style="position:fixed; bottom:10px; font-size:0.7rem; opacity:0.6;">
            SIVIGILA Evento 875<br>Valle del Cauca v2.0
        </div>
        """, unsafe_allow_html=True)

        return pagina


# ============================================================
# MÓDULO 1: REGISTRAR NUEVO CASO
# ============================================================

def modulo_formulario(spreadsheet):
    """Formulario de registro de nuevos casos (esquema reducido)."""
    st.markdown("""
    <div class="main-header">
        <h1>📝 Registro de Nuevo Caso - Violencia de Género e Intrafamiliar</h1>
        <p>Evento 875 SIVIGILA | Seguimiento de casos</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("formulario_nuevo_caso", clear_on_submit=False):
        # ---- Identificación del Caso ----
        st.markdown("#### 🏷️ Identificación del Caso")
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.get("rol") == "EPS":
                eps_seleccionada = st.session_state.get("eps_asignada", "")
                st.text_input("EPS/EAPB que reporta *", value=eps_seleccionada, disabled=True)
            else:
                eps_seleccionada = st.selectbox("EPS/EAPB que reporta *", options=[""] + EPS_LISTA)
            semana_epi = st.number_input("Semana epidemiológica *", min_value=1, max_value=53, value=1, step=1)
        with col2:
            antec_violencia = st.selectbox("¿Antecedente de violencia previa?",
                                           options=["", "NO", "SI", "SIN INFORMACIÓN"])

        eps_otra = ""
        if st.session_state.get("rol") != "EPS" and eps_seleccionada == "OTRA (especificar)":
            eps_otra = st.text_input("Especifique la EPS:").upper()

        st.markdown("---")

        # ---- Datos de la Víctima ----
        st.markdown("#### 👤 Datos de la Víctima")
        col1, col2 = st.columns(2)
        with col1:
            nombres = st.text_input("Nombres *", placeholder="NOMBRES DE LA VÍCTIMA")
            tipo_doc = st.selectbox("Tipo de documento *", options=[""] + TIPOS_DOCUMENTO)
            edad = st.number_input("Edad *", min_value=0, max_value=120, value=0, step=1)
        with col2:
            apellidos = st.text_input("Apellidos *", placeholder="APELLIDOS DE LA VÍCTIMA")
            numero_doc = st.text_input("Número de documento *", placeholder="Solo números")
            sexo = st.selectbox("Sexo *", options=["", "Masculino", "Femenino", "Indeterminado"])

        col1, col2 = st.columns(2)
        with col1:
            municipio_residencia = st.selectbox("Municipio de residencia *", options=[""] + MUNICIPIOS_VALLE)
        with col2:
            curso_vida = calcular_curso_vida(edad)
            st.text_input("Curso de vida (automático)", value=curso_vida, disabled=True)

        if edad > 0 and edad < 14:
            st.error("🚨 **CASO PRIORITARIO** - Menor de 14 años. Reporte obligatorio a ICBF y Fiscalía.")

        st.markdown("---")

        # ---- Notificación y Atención Inicial ----
        st.markdown("#### 📋 Notificación y Atención Inicial")
        col1, col2 = st.columns(2)
        with col1:
            fecha_evento = st.date_input("Fecha del evento *", value=None)
            upgd_atencion = st.text_input("Entidad de la atención (UPGD / IPS)")
        with col2:
            municipio_atencion = st.selectbox("Municipio de la atención", options=[""] + MUNICIPIOS_VALLE)
            fecha_atencion = st.date_input("Fecha de la atención", value=None)

        st.markdown("---")

        # ---- Atención Integral en Salud ----
        st.markdown("#### 🧠 Atención Integral en Salud")
        sino_na = ["", "NO", "SI", "NO APLICA"]
        col1, col2 = st.columns(2)
        with col1:
            atencion_sm = st.selectbox("Atención por Salud Mental", options=sino_na)
            fecha_sm = st.date_input("Fecha atención Salud Mental", value=None)
        with col2:
            remision_proteccion = st.selectbox("Remisión a protección (ICBF, Comisaría)", options=sino_na)
            reporte_autoridades = st.selectbox("Reporte a autoridades (Fiscalía, Policía, URI, CTI)",
                                               options=sino_na)

        st.markdown("---")

        # ---- Seguimientos ----
        st.markdown("#### 📞 Seguimientos")
        seguimiento_1 = st.text_input("Seguimiento 1", placeholder="Ej: 13/03/2026 PSICOLOGÍA")
        seguimiento_2 = st.text_input("Seguimiento 2", placeholder="Ej: 20/03/2026 TRABAJO SOCIAL")
        seguimiento_3 = st.text_input("Seguimiento 3", placeholder="Ej: 27/03/2026 PSIQUIATRÍA")

        st.markdown("---")

        # ---- Estado del Caso ----
        st.markdown("#### 📊 Estado del Caso y Trazabilidad")
        col1, col2 = st.columns(2)
        with col1:
            ruta_atencion = st.selectbox("¿En ruta de atención integral?",
                                         options=["", "SI", "NO", "EN PROCESO"])
            asiste_servicios = st.selectbox("¿Asiste a los servicios?",
                                            options=["", "SI", "NO", "SIN CONTACTO"])
            num_seguimientos = st.number_input("Número de seguimientos realizados",
                                               min_value=0, max_value=50, value=0)
        with col2:
            abandono_proceso = st.selectbox("¿Abandonó el proceso?",
                                            options=["", "NO", "SI", "SIN INFORMACIÓN"])
            reincidencia = st.selectbox("¿Reincidencia / nuevo evento?",
                                        options=["", "NO", "SI", "SIN INFORMACIÓN"])
            estado_caso = st.selectbox("Estado del caso *", options=[""] + ESTADOS_CASO)

        observaciones = st.text_area("Observaciones",
                                     placeholder="Bitácora de gestión: llamadas, notas, derivaciones...",
                                     height=120)

        st.text_input("Funcionario que reporta",
                      value=st.session_state.get("nombre_completo", ""), disabled=True)
        st.markdown(f"📅 **Fecha de digitación:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        submitted = st.form_submit_button("💾 Guardar Registro",
                                          use_container_width=True, type="primary")

        if submitted:
            errores = []
            eps_final = eps_seleccionada if eps_seleccionada != "OTRA (especificar)" else eps_otra
            if st.session_state.get("rol") == "EPS":
                eps_final = st.session_state.get("eps_asignada", "")

            if not eps_final:
                errores.append("EPS/EAPB es obligatorio.")
            if not nombres.strip():
                errores.append("Nombres es obligatorio.")
            if not apellidos.strip():
                errores.append("Apellidos es obligatorio.")
            if not tipo_doc:
                errores.append("Tipo de documento es obligatorio.")
            if not numero_doc.strip():
                errores.append("Número de documento es obligatorio.")
            if not sexo:
                errores.append("Sexo es obligatorio.")
            if not municipio_residencia:
                errores.append("Municipio de residencia es obligatorio.")
            if not fecha_evento:
                errores.append("Fecha del evento es obligatoria.")
            if not estado_caso:
                errores.append("Estado del caso es obligatorio.")
            if edad == 0:
                errores.append("Verifique que la edad sea correcta (actualmente es 0).")

            if errores:
                for err in errores:
                    st.error(f"⚠️ {err}")
            else:
                df_check = cargar_datos(spreadsheet, forzar=True)
                df_check_rol = filtrar_por_rol(df_check)
                duplicados = buscar_por_documento(df_check_rol, numero_doc)

                if not duplicados.empty:
                    st.session_state["_duplicado_doc"] = numero_doc.strip()
                    st.session_state["_duplicado_ids"] = duplicados["id"].tolist()
                    st.warning(f"⚠️ Ya existe(n) **{len(duplicados)}** registro(s) con el documento "
                               f"**{numero_doc}**. Use el botón abajo para ir directo al módulo de edición.")
                    cols_mostrar = ["nombres", "apellidos", "numero_documento", "eps_reporta",
                                    "estado_caso", "fecha_evento"]
                    cols_disp = [c for c in cols_mostrar if c in duplicados.columns]
                    st.dataframe(duplicados[cols_disp], use_container_width=True, hide_index=True)
                else:
                    datos = {
                        "eps_reporta": eps_final,
                        "semana_epidemiologica": str(semana_epi),
                        "antec_violencia": antec_violencia,
                        "nombres": nombres.upper().strip(),
                        "apellidos": apellidos.upper().strip(),
                        "tipo_documento": tipo_doc,
                        "numero_documento": numero_doc.strip(),
                        "edad": str(edad),
                        "sexo": sexo,
                        "curso_vida": calcular_curso_vida(edad),
                        "municipio_residencia": municipio_residencia,
                        "fecha_evento": str(fecha_evento) if fecha_evento else "",
                        "upgd_atencion": upgd_atencion,
                        "municipio_atencion": municipio_atencion,
                        "fecha_atencion": str(fecha_atencion) if fecha_atencion else "",
                        "atencion_salud_mental": atencion_sm,
                        "fecha_salud_mental": str(fecha_sm) if fecha_sm else "",
                        "remision_proteccion": remision_proteccion,
                        "reporte_autoridades": reporte_autoridades,
                        "seguimiento_1": seguimiento_1,
                        "seguimiento_2": seguimiento_2,
                        "seguimiento_3": seguimiento_3,
                        "ruta_atencion_integral": ruta_atencion,
                        "asiste_servicios": asiste_servicios,
                        "num_seguimientos_realizados": str(num_seguimientos),
                        "abandono_proceso": abandono_proceso,
                        "reincidencia_nuevo_evento": reincidencia,
                        "estado_caso": estado_caso,
                        "observaciones": observaciones,
                        "funcionario_reporta": st.session_state.get("nombre_completo", ""),
                    }

                    with st.spinner("Guardando registro..."):
                        exito, resultado = guardar_registro(spreadsheet, datos)

                    if exito:
                        st.success(f"✅ Registro guardado para **{nombres.upper()} {apellidos.upper()}** "
                                   f"(ID: {resultado})")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ Error al guardar: {resultado}")

    # Botón fuera del formulario para ir a edición si hubo duplicado
    if st.session_state.get("_duplicado_doc"):
        if st.button("✏️ Ir a editar este caso", type="primary", use_container_width=True):
            st.session_state["_ir_a_edicion"] = True
            st.session_state["_edit_doc_busqueda"] = st.session_state["_duplicado_doc"]
            st.session_state.pop("_duplicado_doc", None)
            st.session_state.pop("_duplicado_ids", None)
            st.rerun()


# ============================================================
# MÓDULO 2: TABLERO DE CONTROL
# ============================================================

def modulo_dashboard(spreadsheet):
    st.markdown("""
    <div class="main-header">
        <h1>📊 Tablero de Control - Violencia de Género e Intrafamiliar</h1>
        <p>Evento 875 SIVIGILA | Secretaría Departamental de Salud | Valle del Cauca</p>
    </div>
    """, unsafe_allow_html=True)

    df = cargar_datos(spreadsheet, forzar=False)
    df = filtrar_por_rol(df)

    if df.empty:
        st.info("📭 No hay datos registrados aún.")
        return

    df["edad"] = pd.to_numeric(df["edad"], errors="coerce").fillna(0).astype(int)
    df["num_seguimientos_realizados"] = pd.to_numeric(
        df["num_seguimientos_realizados"], errors="coerce").fillna(0).astype(int)
    df["semana_epidemiologica"] = pd.to_numeric(
        df["semana_epidemiologica"], errors="coerce").fillna(0).astype(int)

    # --- Filtros ---
    with st.expander("🔽 Filtros", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filtro_eps = st.multiselect("EPS", options=sorted(df["eps_reporta"].unique().tolist()))
        with col2:
            filtro_municipio = st.multiselect("Municipio de residencia",
                                              options=sorted(df["municipio_residencia"].unique().tolist()))
        with col3:
            filtro_curso = st.multiselect("Curso de vida",
                                          options=sorted(df["curso_vida"].unique().tolist()))
        with col4:
            filtro_estado = st.multiselect("Estado del caso",
                                           options=sorted(df["estado_caso"].unique().tolist()))

        col1, col2 = st.columns(2)
        with col1:
            filtro_sexo = st.multiselect("Sexo de la víctima",
                                         options=sorted(df["sexo"].unique().tolist()))
        with col2:
            try:
                fechas_validas = pd.to_datetime(df["fecha_evento"], errors="coerce").dropna()
                if not fechas_validas.empty:
                    fecha_min = fechas_validas.min().date()
                    fecha_max = fechas_validas.max().date()
                    filtro_fecha = st.date_input("Rango de fechas del evento",
                                                 value=(fecha_min, fecha_max),
                                                 min_value=fecha_min, max_value=fecha_max)
                else:
                    filtro_fecha = None
            except Exception:
                filtro_fecha = None

    df_f = df.copy()
    if filtro_eps:
        df_f = df_f[df_f["eps_reporta"].isin(filtro_eps)]
    if filtro_municipio:
        df_f = df_f[df_f["municipio_residencia"].isin(filtro_municipio)]
    if filtro_curso:
        df_f = df_f[df_f["curso_vida"].isin(filtro_curso)]
    if filtro_estado:
        df_f = df_f[df_f["estado_caso"].isin(filtro_estado)]
    if filtro_sexo:
        df_f = df_f[df_f["sexo"].isin(filtro_sexo)]
    if filtro_fecha and isinstance(filtro_fecha, tuple) and len(filtro_fecha) == 2:
        df_f["_fec"] = pd.to_datetime(df_f["fecha_evento"], errors="coerce")
        df_f = df_f[(df_f["_fec"] >= pd.Timestamp(filtro_fecha[0])) &
                    (df_f["_fec"] <= pd.Timestamp(filtro_fecha[1]))]
        df_f = df_f.drop(columns=["_fec"], errors="ignore")

    # --- KPIs ---
    total = len(df_f)
    menores_18 = len(df_f[df_f["edad"] < 18])
    menores_14 = len(df_f[df_f["edad"] < 14])
    pct_m18 = (menores_18 / total * 100) if total else 0
    mujeres = len(df_f[df_f["sexo"] == "Femenino"])
    pct_muj = (mujeres / total * 100) if total else 0
    reincidentes = len(df_f[df_f["antec_violencia"].str.upper() == "SI"])
    pct_rein = (reincidentes / total * 100) if total else 0
    activos_sin_seg = len(df_f[(df_f["estado_caso"].str.upper() == "ACTIVO") &
                               (df_f["num_seguimientos_realizados"] == 0)])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-value">{total}</div>
        <div class="kpi-label">Total Casos Registrados</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="kpi-card kpi-card-warning"><div class="kpi-value">{menores_18}
        <small style="font-size:0.5em;">({pct_m18:.1f}%)</small></div>
        <div class="kpi-label">⚠️ Menores de 18 años</div></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-value">{mujeres}
        <small style="font-size:0.5em;">({pct_muj:.1f}%)</small></div>
        <div class="kpi-label">Casos en mujeres</div></div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="kpi-card kpi-card-danger"><div class="kpi-value">{reincidentes}
        <small style="font-size:0.5em;">({pct_rein:.1f}%)</small></div>
        <div class="kpi-label">🚨 Reincidentes (violencia previa)</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="kpi-card kpi-card-danger"><div class="kpi-value">{activos_sin_seg}</div>
        <div class="kpi-label">🚨 Activos sin seguimiento</div></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="kpi-card kpi-card-danger"><div class="kpi-value">{menores_14}</div>
        <div class="kpi-label">🚨 Menores de 14 años</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Distribución", "📈 Tendencias", "🧠 Atenciones", "🚨 Alertas"])

    # ---- TAB 1: Distribución ----
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            df_mun = df_f["municipio_residencia"].value_counts().reset_index()
            df_mun.columns = ["Municipio", "Casos"]
            df_mun = df_mun.sort_values("Casos", ascending=True)
            fig = px.bar(df_mun, x="Casos", y="Municipio", orientation="h",
                         title="Casos por Municipio de Residencia",
                         color="Casos", color_continuous_scale="Reds", text="Casos")
            fig.update_traces(textposition="outside")
            fig.update_layout(height=max(400, len(df_mun) * 28),
                              showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            df_eps = df_f["eps_reporta"].value_counts().reset_index()
            df_eps.columns = ["EPS", "Casos"]
            fig = px.bar(df_eps, x="EPS", y="Casos",
                         title="Casos por EPS",
                         color="Casos", color_continuous_scale="Blues", text="Casos")
            fig.update_traces(textposition="outside")
            fig.update_layout(xaxis_tickangle=-45, height=400,
                              showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            df_sexo = df_f["sexo"].value_counts().reset_index()
            df_sexo.columns = ["Sexo", "Casos"]
            fig = px.pie(df_sexo, values="Casos", names="Sexo",
                         title="Distribución por Sexo de la Víctima",
                         color_discrete_sequence=["#D32F2F", "#1565C0", "#9E9E9E"], hole=0.4)
            fig.update_traces(textinfo="percent+value")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            df_curso = df_f["curso_vida"].value_counts().reset_index()
            df_curso.columns = ["Curso de Vida", "Casos"]
            df_curso["_orden"] = df_curso["Curso de Vida"].apply(
                lambda x: CURSOS_VIDA.index(x) if x in CURSOS_VIDA else 99)
            df_curso = df_curso.sort_values("_orden").drop(columns="_orden")
            fig = px.pie(df_curso, values="Casos", names="Curso de Vida",
                         title="Distribución por Curso de Vida",
                         category_orders={"Curso de Vida": CURSOS_VIDA},
                         color_discrete_sequence=["#0D2137", "#1B3A5C", "#2E6B9E",
                                                  "#4A90C4", "#7FB3D8", "#B5D4E9"], hole=0.4)
            fig.update_traces(textinfo="percent+value", sort=False)
            st.plotly_chart(fig, use_container_width=True)

        df_estado = df_f["estado_caso"].value_counts().reset_index()
        df_estado.columns = ["Estado", "Casos"]
        fig = px.bar(df_estado, x="Estado", y="Casos",
                     title="Distribución por Estado del Caso",
                     color="Estado", text="Casos",
                     color_discrete_map={
                         "ACTIVO": "#F9A825", "CERRADO": "#4CAF50",
                         "EN SEGUIMIENTO": "#2196F3", "FALLECIDO": "#D32F2F",
                         "SIN CONTACTO": "#9E9E9E", "REMITIDO A OTRA EPS": "#FF9800"
                     })
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # ---- TAB 2: Tendencias ----
    with tab2:
        df_sem = df_f.groupby("semana_epidemiologica").size().reset_index(name="Casos")
        df_sem = df_sem.sort_values("semana_epidemiologica")
        df_sem = df_sem[df_sem["semana_epidemiologica"] > 0]
        if not df_sem.empty:
            fig = px.line(df_sem, x="semana_epidemiologica", y="Casos",
                          title="Tendencia de Casos por Semana Epidemiológica",
                          markers=True, text="Casos")
            fig.update_traces(textposition="top center",
                              line_color=COLOR_AZUL_OSCURO, marker_color=COLOR_ROJO_ALERTA)
            fig.update_layout(xaxis_title="Semana Epidemiológica", yaxis_title="Número de Casos")
            st.plotly_chart(fig, use_container_width=True)

        df_cv_estado = df_f.groupby(["curso_vida", "estado_caso"]).size().reset_index(name="Casos")
        if not df_cv_estado.empty:
            fig = px.bar(df_cv_estado, x="curso_vida", y="Casos", color="estado_caso",
                         title="Estado del Caso por Curso de Vida",
                         barmode="group", text="Casos",
                         category_orders={"curso_vida": CURSOS_VIDA})
            fig.update_traces(textposition="outside")
            fig.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)

    # ---- TAB 3: Atenciones ----
    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            df_sm = df_f["atencion_salud_mental"].value_counts().reset_index()
            df_sm.columns = ["Atención", "Casos"]
            fig = px.bar(df_sm, x="Atención", y="Casos",
                         title="Atención por Salud Mental",
                         color="Casos", color_continuous_scale="Blues", text="Casos")
            fig.update_traces(textposition="outside")
            fig.update_layout(showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            df_rp = df_f["remision_proteccion"].value_counts().reset_index()
            df_rp.columns = ["Remisión", "Casos"]
            fig = px.bar(df_rp, x="Remisión", y="Casos",
                         title="Remisión a protección (ICBF, Comisaría)",
                         color="Casos", color_continuous_scale="Oranges", text="Casos")
            fig.update_traces(textposition="outside")
            fig.update_layout(showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            df_ra = df_f["reporte_autoridades"].value_counts().reset_index()
            df_ra.columns = ["Reporte", "Casos"]
            fig = px.bar(df_ra, x="Reporte", y="Casos",
                         title="Reporte a autoridades (Fiscalía/Policía)",
                         color="Casos", color_continuous_scale="Reds", text="Casos")
            fig.update_traces(textposition="outside")
            fig.update_layout(showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            df_as = df_f["asiste_servicios"].value_counts().reset_index()
            df_as.columns = ["Asistencia", "Casos"]
            fig = px.bar(df_as, x="Asistencia", y="Casos",
                         title="¿Asiste a los servicios?",
                         color="Casos", color_continuous_scale="Blues", text="Casos")
            fig.update_traces(textposition="outside")
            fig.update_layout(showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

        df_ab = df_f["abandono_proceso"].value_counts().reset_index()
        df_ab.columns = ["Abandono", "Casos"]
        fig = px.bar(df_ab, x="Abandono", y="Casos",
                     title="¿Abandonó el proceso?",
                     color="Casos", color_continuous_scale="Reds", text="Casos")
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # ---- TAB 4: Alertas ----
    with tab4:
        st.markdown("""<div class="alerta-roja"><strong>🚨 ALERTA ROJA — Reincidentes (violencia previa)</strong></div>""",
                    unsafe_allow_html=True)
        df_r = df_f[df_f["antec_violencia"].str.upper() == "SI"]
        if not df_r.empty:
            cols = ["numero_documento", "nombres", "apellidos", "edad",
                    "municipio_residencia", "eps_reporta", "estado_caso"]
            cols_d = [c for c in cols if c in df_r.columns]
            st.dataframe(df_r[cols_d], use_container_width=True, hide_index=True)
        else:
            st.info("No hay reincidentes con los filtros actuales.")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""<div class="alerta-roja"><strong>🚨 ALERTA ROJA — Menores de 14 años (reporte obligatorio a ICBF y Fiscalía)</strong></div>""",
                    unsafe_allow_html=True)
        df_m = df_f[df_f["edad"] < 14]
        if not df_m.empty:
            cols = ["numero_documento", "nombres", "apellidos", "edad", "sexo",
                    "eps_reporta", "reporte_autoridades", "remision_proteccion", "estado_caso"]
            cols_d = [c for c in cols if c in df_m.columns]
            st.dataframe(df_m[cols_d], use_container_width=True, hide_index=True)
        else:
            st.info("No hay casos en menores de 14 años con los filtros actuales.")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""<div class="alerta-amarilla"><strong>⚠️ ALERTA — Activos sin seguimiento o sin contacto</strong></div>""",
                    unsafe_allow_html=True)
        df_ss = df_f[
            ((df_f["estado_caso"].str.upper() == "ACTIVO") & (df_f["num_seguimientos_realizados"] == 0)) |
            (df_f["asiste_servicios"].str.upper().isin(["NO", "SIN CONTACTO"]))
        ]
        if not df_ss.empty:
            cols = ["numero_documento", "nombres", "apellidos", "municipio_residencia",
                    "asiste_servicios", "num_seguimientos_realizados", "eps_reporta", "estado_caso"]
            cols_d = [c for c in cols if c in df_ss.columns]
            st.dataframe(df_ss[cols_d], use_container_width=True, hide_index=True)
        else:
            st.info("No hay casos sin seguimiento con los filtros actuales.")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""<div class="alerta-amarilla"><strong>⚠️ ALERTA — Pacientes que abandonaron el proceso</strong></div>""",
                    unsafe_allow_html=True)
        df_a = df_f[df_f["abandono_proceso"].str.upper() == "SI"]
        if not df_a.empty:
            cols = ["numero_documento", "nombres", "apellidos", "municipio_residencia",
                    "eps_reporta", "estado_caso"]
            cols_d = [c for c in cols if c in df_a.columns]
            st.dataframe(df_a[cols_d], use_container_width=True, hide_index=True)
        else:
            st.info("No hay pacientes con abandono del proceso.")


# ============================================================
# MÓDULO 3: EDITAR / ACTUALIZAR CASO
# ============================================================

def parse_date_safe(val):
    try:
        if val and str(val).strip() and str(val).strip() != "None":
            return pd.to_datetime(val).date()
    except Exception:
        pass
    return None


def modulo_edicion(spreadsheet):
    st.markdown("""
    <div class="main-header">
        <h1>✏️ Editar / Actualizar Caso</h1>
        <p>Busque un registro y actualice la información de seguimiento</p>
    </div>
    """, unsafe_allow_html=True)

    df = cargar_datos(spreadsheet, forzar=True)
    df = filtrar_por_rol(df)

    if df.empty:
        st.info("📭 No hay registros disponibles para editar.")
        return

    # Si viene redirigido desde duplicado, prellenar búsqueda
    busq_doc_default = st.session_state.pop("_edit_doc_busqueda", "")
    if st.session_state.get("_ir_a_edicion"):
        st.session_state.pop("_ir_a_edicion", None)

    st.markdown("#### 🔍 Buscar Registro")
    col1, col2 = st.columns([2, 2])
    with col1:
        busq_doc = st.text_input("Buscar por número de documento",
                                 value=busq_doc_default, key="edit_busq_doc")
    with col2:
        busq_nombre = st.text_input("Buscar por nombre o apellido", key="edit_busq_nombre")

    df_r = df.copy()
    if busq_doc:
        df_r = df_r[df_r["numero_documento"].astype(str).str.contains(busq_doc, na=False)]
    if busq_nombre:
        bu = busq_nombre.upper()
        df_r = df_r[
            df_r["nombres"].astype(str).str.upper().str.contains(bu, na=False) |
            df_r["apellidos"].astype(str).str.upper().str.contains(bu, na=False)
        ]

    if df_r.empty:
        st.warning("No se encontraron registros con los criterios de búsqueda.")
        return

    st.markdown(f"**{len(df_r)} registro(s) encontrado(s)**")
    cols_t = ["id", "nombres", "apellidos", "numero_documento", "eps_reporta",
              "edad", "municipio_residencia", "estado_caso", "fecha_evento"]
    cols_d = [c for c in cols_t if c in df_r.columns]
    st.dataframe(df_r[cols_d], use_container_width=True, hide_index=True)

    ids = df_r["id"].tolist()
    if not ids:
        return

    st.markdown("---")
    id_sel = st.selectbox("Seleccione el ID del registro a editar:", options=ids)

    if id_sel:
        registro = df_r[df_r["id"] == id_sel].iloc[0].to_dict()

        st.markdown(f"#### Editando: **{registro.get('nombres', '')} {registro.get('apellidos', '')}** "
                    f"(Doc: {registro.get('numero_documento', '')})")

        with st.form("formulario_edicion"):
            # Identificación
            st.markdown("##### 🏷️ Identificación")
            col1, col2 = st.columns(2)
            with col1:
                eps_e = st.selectbox("EPS/EAPB", options=EPS_LISTA,
                                     index=EPS_LISTA.index(registro.get("eps_reporta", ""))
                                     if registro.get("eps_reporta", "") in EPS_LISTA else 0)
                semana_e = st.number_input("Semana epidemiológica", min_value=1, max_value=53,
                                           value=int(registro.get("semana_epidemiologica") or 1))
            with col2:
                antec_opts = ["NO", "SI", "SIN INFORMACIÓN"]
                antec_e = st.selectbox("¿Violencia previa?", options=antec_opts,
                                       index=antec_opts.index(registro.get("antec_violencia", "NO"))
                                       if registro.get("antec_violencia", "") in antec_opts else 0)

            # Víctima
            st.markdown("##### 👤 Víctima")
            col1, col2 = st.columns(2)
            with col1:
                nom_e = st.text_input("Nombres", value=registro.get("nombres", ""))
                tdoc_e = st.selectbox("Tipo documento", options=TIPOS_DOCUMENTO,
                                      index=TIPOS_DOCUMENTO.index(registro.get("tipo_documento", "CC"))
                                      if registro.get("tipo_documento", "") in TIPOS_DOCUMENTO else 2)
                edad_e = st.number_input("Edad", min_value=0, max_value=120,
                                         value=int(registro.get("edad") or 0))
            with col2:
                ape_e = st.text_input("Apellidos", value=registro.get("apellidos", ""))
                ndoc_e = st.text_input("Número de documento", value=str(registro.get("numero_documento", "")))
                sexo_opts = ["Masculino", "Femenino", "Indeterminado"]
                sexo_e = st.selectbox("Sexo", options=sexo_opts,
                                      index=sexo_opts.index(registro.get("sexo", "Femenino"))
                                      if registro.get("sexo", "") in sexo_opts else 1)

            mun_e = st.selectbox("Municipio de residencia", options=[""] + MUNICIPIOS_VALLE,
                                 index=(MUNICIPIOS_VALLE.index(registro.get("municipio_residencia", "")) + 1)
                                 if registro.get("municipio_residencia", "") in MUNICIPIOS_VALLE else 0)

            # Notificación / Atención
            st.markdown("##### 📋 Notificación y Atención")
            col1, col2 = st.columns(2)
            with col1:
                fev_e = st.date_input("Fecha del evento",
                                      value=parse_date_safe(registro.get("fecha_evento")))
                upgd_e = st.text_input("UPGD/IPS", value=registro.get("upgd_atencion", ""))
            with col2:
                muna_e = st.selectbox("Municipio de la atención", options=[""] + MUNICIPIOS_VALLE,
                                      index=(MUNICIPIOS_VALLE.index(registro.get("municipio_atencion", "")) + 1)
                                      if registro.get("municipio_atencion", "") in MUNICIPIOS_VALLE else 0)
                fat_e = st.date_input("Fecha de la atención",
                                      value=parse_date_safe(registro.get("fecha_atencion")))

            # Atención en Salud
            st.markdown("##### 🧠 Atención Integral en Salud")
            sino_na = ["NO", "SI", "NO APLICA"]
            col1, col2 = st.columns(2)
            with col1:
                asm_e = st.selectbox("Atención Salud Mental", options=sino_na,
                                     index=sino_na.index(registro.get("atencion_salud_mental", "NO"))
                                     if registro.get("atencion_salud_mental", "") in sino_na else 0)
                fsm_e = st.date_input("Fecha Salud Mental",
                                      value=parse_date_safe(registro.get("fecha_salud_mental")))
            with col2:
                rp_e = st.selectbox("Remisión a protección", options=sino_na,
                                    index=sino_na.index(registro.get("remision_proteccion", "NO"))
                                    if registro.get("remision_proteccion", "") in sino_na else 0)
                ra_e = st.selectbox("Reporte a autoridades", options=sino_na,
                                    index=sino_na.index(registro.get("reporte_autoridades", "NO"))
                                    if registro.get("reporte_autoridades", "") in sino_na else 0)

            # Seguimientos
            st.markdown("##### 📞 Seguimientos")
            seg1_e = st.text_input("Seguimiento 1", value=str(registro.get("seguimiento_1", "")),
                                   placeholder="Ej: 13/03/2026 PSICOLOGÍA")
            seg2_e = st.text_input("Seguimiento 2", value=str(registro.get("seguimiento_2", "")),
                                   placeholder="Ej: 20/03/2026 TRABAJO SOCIAL")
            seg3_e = st.text_input("Seguimiento 3", value=str(registro.get("seguimiento_3", "")),
                                   placeholder="Ej: 27/03/2026 PSIQUIATRÍA")

            # Estado
            st.markdown("##### 📊 Estado del Caso")
            col1, col2 = st.columns(2)
            ruta_opts = ["SI", "NO", "EN PROCESO"]
            asiste_opts = ["SI", "NO", "SIN CONTACTO"]
            ab_opts = ["NO", "SI", "SIN INFORMACIÓN"]
            with col1:
                ruta_e = st.selectbox("¿En ruta de atención integral?", options=ruta_opts,
                                      index=ruta_opts.index(registro.get("ruta_atencion_integral", "SI"))
                                      if registro.get("ruta_atencion_integral", "") in ruta_opts else 0)
                asiste_e = st.selectbox("¿Asiste a servicios?", options=asiste_opts,
                                        index=asiste_opts.index(registro.get("asiste_servicios", "SI"))
                                        if registro.get("asiste_servicios", "") in asiste_opts else 0)
                num_seg_e = st.number_input("Nº seguimientos realizados", min_value=0, max_value=50,
                                            value=int(registro.get("num_seguimientos_realizados") or 0))
            with col2:
                aban_e = st.selectbox("¿Abandonó el proceso?", options=ab_opts,
                                      index=ab_opts.index(registro.get("abandono_proceso", "NO"))
                                      if registro.get("abandono_proceso", "") in ab_opts else 0)
                rein_e = st.selectbox("¿Reincidencia / nuevo evento?", options=ab_opts,
                                      index=ab_opts.index(registro.get("reincidencia_nuevo_evento", "NO"))
                                      if registro.get("reincidencia_nuevo_evento", "") in ab_opts else 0)
                est_e = st.selectbox("Estado del caso", options=ESTADOS_CASO,
                                     index=ESTADOS_CASO.index(registro.get("estado_caso", "ACTIVO"))
                                     if registro.get("estado_caso", "") in ESTADOS_CASO else 0)

            obs_e = st.text_area("Observaciones", value=str(registro.get("observaciones", "")), height=120,
                                 placeholder="Bitácora de gestión: llamadas, notas, derivaciones...")

            submitted_e = st.form_submit_button("💾 Guardar Cambios",
                                                use_container_width=True, type="primary")

            if submitted_e:
                datos_act = {
                    "id": id_sel,
                    "fecha_digitacion": registro.get("fecha_digitacion", ""),
                    "funcionario_reporta": registro.get("funcionario_reporta", ""),
                    "eps_reporta": eps_e,
                    "semana_epidemiologica": str(semana_e),
                    "antec_violencia": antec_e,
                    "nombres": nom_e.upper().strip(),
                    "apellidos": ape_e.upper().strip(),
                    "tipo_documento": tdoc_e,
                    "numero_documento": ndoc_e.strip(),
                    "edad": str(edad_e),
                    "sexo": sexo_e,
                    "curso_vida": calcular_curso_vida(edad_e),
                    "municipio_residencia": mun_e,
                    "fecha_evento": str(fev_e) if fev_e else "",
                    "upgd_atencion": upgd_e,
                    "municipio_atencion": muna_e,
                    "fecha_atencion": str(fat_e) if fat_e else "",
                    "atencion_salud_mental": asm_e,
                    "fecha_salud_mental": str(fsm_e) if fsm_e else "",
                    "remision_proteccion": rp_e,
                    "reporte_autoridades": ra_e,
                    "seguimiento_1": seg1_e,
                    "seguimiento_2": seg2_e,
                    "seguimiento_3": seg3_e,
                    "ruta_atencion_integral": ruta_e,
                    "asiste_servicios": asiste_e,
                    "num_seguimientos_realizados": str(num_seg_e),
                    "abandono_proceso": aban_e,
                    "reincidencia_nuevo_evento": rein_e,
                    "estado_caso": est_e,
                    "observaciones": obs_e,
                }

                with st.spinner("Actualizando registro..."):
                    exito, msg = actualizar_registro(
                        spreadsheet, id_sel, datos_act,
                        st.session_state.get("nombre_completo", "")
                    )
                if exito:
                    st.success(f"✅ Registro actualizado para **{nom_e.upper()} {ape_e.upper()}**")
                else:
                    st.error(f"❌ Error al actualizar: {msg}")


# ============================================================
# MÓDULO 4: EXPORTACIÓN
# ============================================================

def modulo_exportacion(spreadsheet):
    st.markdown("""
    <div class="main-header">
        <h1>📥 Exportación de Datos</h1>
        <p>Descargue los datos en formato CSV o Excel</p>
    </div>
    """, unsafe_allow_html=True)

    df = cargar_datos(spreadsheet, forzar=True)
    df = filtrar_por_rol(df)

    if df.empty:
        st.info("📭 No hay datos disponibles para exportar.")
        return

    st.markdown(f"**Total de registros disponibles: {len(df)}**")

    with st.expander("🔽 Filtrar antes de exportar"):
        col1, col2 = st.columns(2)
        with col1:
            exp_eps = st.multiselect("EPS", options=sorted(df["eps_reporta"].unique().tolist()),
                                     key="exp_eps")
            exp_mun = st.multiselect("Municipio de residencia",
                                     options=sorted(df["municipio_residencia"].unique().tolist()),
                                     key="exp_mun")
        with col2:
            exp_estado = st.multiselect("Estado",
                                        options=sorted(df["estado_caso"].unique().tolist()),
                                        key="exp_estado")
            exp_curso = st.multiselect("Curso de vida",
                                       options=sorted(df["curso_vida"].unique().tolist()),
                                       key="exp_curso")

    df_e = df.copy()
    if exp_eps:
        df_e = df_e[df_e["eps_reporta"].isin(exp_eps)]
    if exp_mun:
        df_e = df_e[df_e["municipio_residencia"].isin(exp_mun)]
    if exp_estado:
        df_e = df_e[df_e["estado_caso"].isin(exp_estado)]
    if exp_curso:
        df_e = df_e[df_e["curso_vida"].isin(exp_curso)]

    st.markdown(f"**Registros a exportar: {len(df_e)}**")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📄 Descargar CSV")
        csv_data = df_e.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇️ Descargar CSV",
            data=csv_data,
            file_name=f"sivigila_875_violencia_valle_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        st.markdown("#### 📊 Descargar Excel (.xlsx)")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_e.to_excel(writer, sheet_name="TODOS_LOS_DATOS", index=False)
        buffer.seek(0)
        st.download_button(
            label="⬇️ Descargar Excel",
            data=buffer,
            file_name=f"sivigila_875_violencia_valle_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.markdown("---")
    st.markdown("#### 👁️ Vista previa")
    st.dataframe(df_e, use_container_width=True, hide_index=True)


# ============================================================
# MÓDULO 5: GESTIÓN DE USUARIOS
# ============================================================

def modulo_gestion_usuarios(spreadsheet):
    st.markdown("""
    <div class="main-header">
        <h1>⚙️ Gestión de Usuarios</h1>
        <p>Crear y administrar usuarios del sistema</p>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("rol") != "SECRETARÍA":
        st.error("⛔ No tiene permisos para acceder a este módulo.")
        return

    st.markdown("#### 👥 Usuarios registrados")
    try:
        hoja_u = obtener_hoja_usuarios(spreadsheet)
        registros = hoja_u.get_all_records()
        df_u = pd.DataFrame(registros)
        if not df_u.empty:
            st.dataframe(df_u[["usuario", "nombre_completo", "rol", "eps_asignada"]],
                         use_container_width=True, hide_index=True)
        else:
            st.info("No hay usuarios registrados.")
    except Exception as e:
        st.error(f"Error al cargar usuarios: {str(e)}")

    st.markdown("---")
    st.markdown("#### ➕ Crear Nuevo Usuario")
    with st.form("form_nuevo_usuario", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            n_user = st.text_input("Nombre de usuario *", placeholder="Ej: digitador.sura")
            n_pass = st.text_input("Contraseña *", type="password")
            n_pass2 = st.text_input("Confirmar contraseña *", type="password")
        with col2:
            n_nom = st.text_input("Nombre completo *", placeholder="Ej: María García")
            n_rol = st.selectbox("Rol *", options=["EPS", "SECRETARÍA"])
            n_eps = st.selectbox("EPS asignada (solo rol EPS)",
                                 options=["N/A"] + [e for e in EPS_LISTA if e != "OTRA (especificar)"])

        crear = st.form_submit_button("✅ Crear Usuario", use_container_width=True, type="primary")
        if crear:
            if not n_user or not n_pass or not n_nom:
                st.error("⚠️ Todos los campos marcados con * son obligatorios.")
            elif n_pass != n_pass2:
                st.error("⚠️ Las contraseñas no coinciden.")
            elif len(n_pass) < 6:
                st.error("⚠️ La contraseña debe tener al menos 6 caracteres.")
            else:
                eps_a = n_eps if n_rol == "EPS" and n_eps != "N/A" else ""
                exito, msg = crear_usuario(spreadsheet, n_user, n_pass, n_nom, n_rol, eps_a)
                if exito:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")


# ============================================================
# MÓDULO 6: CARGA MASIVA (solo SECRETARÍA)
# ============================================================

# Mapeo del archivo histórico SIVIGILA al esquema reducido
MAP_EAPB = {
    "ASMET SALUD": "ASMET SALUD",
    "ASOCIACION INDIGENA DEL CAUCA": "ASOCIACIÓN INDÍGENA DEL CAUCA EPSI",
    "C.C.F. COMFACHOCO": "COMFACHOCÓ",
    "CAPITAL SALUD EPSS S.A.S.": "CAPITAL SALUD",
    "COMFENALCO": "COMFENALCO VALLE",
    "COMPENSAR E.P.S.": "COMPENSAR",
    "COMPENSAR ENTIDAD PROMOTORA DE SALUD.": "COMPENSAR",
    "COOSALUD": "COOSALUD",
    "ECOPETROL": "OTRA (especificar)",
    "EMMSANAR": "EMSSANAR",
    "EMSSANAR": "EMSSANAR",
    "EPS FAMISANAR LTDA.": "FAMISANAR",
    "EPS SANITAS - CM": "SANITAS",
    "FIDUPREVISORA S.A": "OTRA (especificar)",
    "FONDO DE PASIVO SOCIAL DE FERROCARRILES NACIONALES DE COLOMBIA.": "FONDO PASIVO SOCIAL FERROCARRILES",
    "FUERZAS MILITARES": "OTRA (especificar)",
    "MALLAMAS - EMPRESA PROMOTORA DE SALUD MALLAMAS EPS INDIGENA": "MALLAMAS EPSI",
    "MUTUAL SER": "MUTUAL SER",
    "NUEVA EPS": "NUEVA EPS",
    "POLICIA NACIONAL": "OTRA (especificar)",
    "RES FONDO PRESTACION SOCIAL CO": "OTRA (especificar)",
    "S.O.S": "SOS (SERVICIO OCCIDENTAL DE SALUD)",
    "S.O.S.": "SOS (SERVICIO OCCIDENTAL DE SALUD)",
    "SALUD TOTAL": "SALUD TOTAL",
    "SANITAS E.P.S. S.A.": "SANITAS",
    "SAVIA SALUD SUBSIDIADO": "SAVIA SALUD",
    "SURA": "SURA",
}

MAP_SEXO = {"M": "Masculino", "F": "Femenino", "I": "Indeterminado"}


def _to_int_safe(val):
    try:
        if pd.isna(val):
            return None
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return None


def _fmt_fecha(val):
    if pd.isna(val) or str(val).strip() in ("", "None", "NaT"):
        return ""
    try:
        return pd.to_datetime(val, dayfirst=True, errors="coerce").strftime("%Y-%m-%d")
    except Exception:
        return ""


def _si_no(val):
    v = _to_int_safe(val)
    if v == 1:
        return "SI"
    if v == 2:
        return "NO"
    return "SIN INFORMACIÓN"


def transformar_base_875(df):
    """Transforma la base histórica al esquema reducido (39 columnas).

    Filtra automáticamente los registros de violencia sexual.
    """
    df = df.copy()
    df["_nat_int"] = df["naturaleza"].apply(_to_int_safe)
    n_inicial = len(df)
    df_no_sex = df[df["_nat_int"].isin([1, 2, 3])].copy()
    n_descartados = n_inicial - len(df_no_sex)

    registros = []
    for _, row in df_no_sex.iterrows():
        eps_raw = str(row.get("EAPB", "")).strip()
        eps_final = MAP_EAPB.get(eps_raw, "OTRA (especificar)")

        edad = _to_int_safe(row.get("edad_")) or 0

        pri_n = str(row.get("pri_nom_", "")).strip().upper()
        seg_n = str(row.get("seg_nom_", "")).strip().upper()
        pri_a = str(row.get("pri_ape_", "")).strip().upper()
        seg_a = str(row.get("seg_ape_", "")).strip().upper()
        nombres = (pri_n + " " + seg_n).replace("NAN", "").strip()
        apellidos = (pri_a + " " + seg_a).replace("NAN", "").strip()

        num_doc = str(row.get("num_ide_", "")).strip()
        if num_doc.endswith(".0"):
            num_doc = num_doc[:-2]

        reporte = "SI" if _to_int_safe(row.get("inf_aut")) == 1 else "NO"

        registro = {
            "id": generar_id(),
            "fecha_digitacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "funcionario_reporta": "CARGA MASIVA",
            "eps_reporta": eps_final,
            "semana_epidemiologica": str(_to_int_safe(row.get("semana")) or 0),
            "antec_violencia": _si_no(row.get("antec")),
            "nombres": nombres,
            "apellidos": apellidos,
            "tipo_documento": str(row.get("tip_ide_", "CC")).strip().upper(),
            "numero_documento": num_doc,
            "edad": str(edad),
            "sexo": MAP_SEXO.get(str(row.get("sexo_", "")).strip().upper(), "Indeterminado"),
            "curso_vida": calcular_curso_vida(edad),
            "municipio_residencia": str(row.get("nmun_resi", "")).strip().upper(),
            "fecha_evento": _fmt_fecha(row.get("fec_hecho")),
            "upgd_atencion": str(row.get("nom_upgd", "")).strip(),
            "municipio_atencion": str(row.get("nmun_notif", "")).strip().upper(),
            "fecha_atencion": _fmt_fecha(row.get("fec_con_")),
            "atencion_salud_mental": "SI" if _to_int_safe(row.get("ac_mental")) == 1 else "NO",
            "fecha_salud_mental": "",
            "remision_proteccion": "SI" if _to_int_safe(row.get("remit_prot")) == 1 else "NO",
            "reporte_autoridades": reporte,
            "seguimiento_1": "",
            "seguimiento_2": "",
            "seguimiento_3": "",
            "ruta_atencion_integral": "EN PROCESO",
            "asiste_servicios": "SIN CONTACTO",
            "num_seguimientos_realizados": "0",
            "abandono_proceso": "SIN INFORMACIÓN",
            "reincidencia_nuevo_evento": "SIN INFORMACIÓN",
            "estado_caso": "ACTIVO",
            "observaciones": f"Carga masiva - {datetime.now().strftime('%Y-%m-%d')}",
            "ultima_modificacion_por": st.session_state.get("nombre_completo", "CARGA MASIVA"),
            "ultima_modificacion_fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        registros.append(registro)
        time.sleep(0.001)  # IDs únicos

    return pd.DataFrame(registros), n_descartados


def modulo_carga_masiva(spreadsheet):
    """Importación masiva de la base histórica del Evento 875."""
    st.markdown("""
    <div class="main-header">
        <h1>📂 Carga Masiva</h1>
        <p>Importación masiva de registros del Evento 875 (excluye violencia sexual)</p>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("rol") != "SECRETARÍA":
        st.error("⛔ Solo el rol SECRETARÍA puede realizar carga masiva.")
        return

    st.info("ℹ️ El sistema descarta automáticamente los registros de violencia sexual "
            "(solo carga modalidades FÍSICA, PSICOLÓGICA y NEGLIGENCIA Y ABANDONO).")

    archivo = st.file_uploader("Seleccione el archivo Excel histórico (.xlsx)",
                               type=["xlsx", "xls"], key="carga_masiva_file")
    if archivo is None:
        return

    try:
        df_raw = pd.read_excel(archivo)
        st.success(f"✅ Archivo leído: **{len(df_raw)}** registros, **{len(df_raw.columns)}** columnas.")
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {e}")
        return

    if "naturaleza" not in df_raw.columns:
        st.error("❌ El archivo no contiene la columna 'naturaleza'. Verifique que sea la base SIVIGILA 875.")
        return

    with st.spinner("Transformando datos al esquema del aplicativo..."):
        df_t, n_sex = transformar_base_875(df_raw)

    with st.spinner("Verificando duplicados contra la base existente..."):
        df_exist = cargar_datos(spreadsheet, forzar=True)

    if not df_exist.empty:
        df_exist["_llave"] = (df_exist["numero_documento"].astype(str).str.strip() + "_" +
                              df_exist["fecha_evento"].astype(str).str.strip())
        df_t["_llave"] = (df_t["numero_documento"].astype(str).str.strip() + "_" +
                          df_t["fecha_evento"].astype(str).str.strip())
        llaves = set(df_exist["_llave"].tolist())
        mask = ~df_t["_llave"].isin(llaves)
        n_dup = (~mask).sum()
        df_n = df_t[mask].drop(columns=["_llave"])
    else:
        n_dup = 0
        df_n = df_t.drop(columns=["_llave"], errors="ignore")

    st.markdown("---")
    st.markdown("### 📊 Resumen")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total en archivo", len(df_raw))
    c2.metric("Sexuales descartados", n_sex)
    c3.metric("Duplicados omitidos", int(n_dup))
    c4.metric("Nuevos a cargar", len(df_n))

    if df_n.empty:
        st.warning("⚠️ No hay registros nuevos para insertar.")
        return

    with st.expander("👁️ Vista previa"):
        cols_p = ["nombres", "apellidos", "numero_documento", "edad", "sexo",
                  "municipio_residencia", "eps_reporta", "fecha_evento"]
        cols_pd = [c for c in cols_p if c in df_n.columns]
        st.dataframe(df_n[cols_pd].head(50), use_container_width=True, hide_index=True)
        if len(df_n) > 50:
            st.caption(f"Mostrando 50 de {len(df_n)} registros.")

    st.markdown("---")
    st.warning("⚠️ Esta acción insertará los registros en Google Sheets. No se puede deshacer desde la app.")
    if st.button(f"✅ Confirmar e insertar {len(df_n)} registros",
                 type="primary", use_container_width=True):
        hoja = obtener_hoja_datos(spreadsheet)
        progreso = st.progress(0)
        estado = st.empty()

        todas = [[str(r.get(col, "")) for col in COLUMNAS_DATOS]
                 for _, r in df_n.iterrows()]

        TAM = 50
        ins = 0
        err = 0
        total_lotes = (len(todas) - 1) // TAM + 1

        for i in range(0, len(todas), TAM):
            lote = todas[i:i + TAM]
            nl = i // TAM + 1
            estado.text(f"Insertando lote {nl} de {total_lotes} ({len(lote)} registros)...")
            try:
                hoja.append_rows(lote, value_input_option="USER_ENTERED", table_range="A1")
                ins += len(lote)
            except Exception as e:
                st.warning(f"Error en lote {nl}: {e}. Reintentando en 30 s...")
                time.sleep(30)
                try:
                    hoja.append_rows(lote, value_input_option="USER_ENTERED", table_range="A1")
                    ins += len(lote)
                except Exception as e2:
                    err += len(lote)
                    st.error(f"Lote {nl} falló: {e2}")

            progreso.progress(min((i + len(lote)) / len(todas), 1.0))
            time.sleep(2)

        progreso.empty()
        estado.empty()

        if "_datos_cache_time" in st.session_state:
            st.session_state["_datos_cache_time"] = 0

        if err == 0:
            st.success(f"🎉 Carga completada: **{ins}** registros insertados.")
            st.balloons()
        else:
            st.warning(f"⚠️ Insertados {ins}, fallaron {err}.")


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def main():
    if not st.session_state.get("autenticado", False):
        mostrar_login()
        return

    spreadsheet = obtener_conexion_gsheets()
    if not spreadsheet:
        st.error("No se pudo conectar a Google Sheets.")
        return

    pagina = mostrar_sidebar()

    if pagina == "📊 Tablero de Control":
        modulo_dashboard(spreadsheet)
    elif pagina == "📝 Registrar Nuevo Caso":
        modulo_formulario(spreadsheet)
    elif pagina == "✏️ Editar / Actualizar Caso":
        modulo_edicion(spreadsheet)
    elif pagina == "📥 Exportar Datos":
        modulo_exportacion(spreadsheet)
    elif pagina == "📂 Carga Masiva":
        modulo_carga_masiva(spreadsheet)
    elif pagina == "⚙️ Gestionar Usuarios":
        modulo_gestion_usuarios(spreadsheet)


if __name__ == "__main__":
    main()
