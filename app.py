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
import plotly.graph_objects as go
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

# --- Colores institucionales ---
COLOR_AZUL_OSCURO = "#1B3A5C"
COLOR_AZUL_MEDIO = "#2E6B9E"
COLOR_BLANCO = "#FFFFFF"
COLOR_GRIS_CLARO = "#F0F2F6"
COLOR_ROJO_ALERTA = "#D32F2F"
COLOR_AMARILLO_ALERTA = "#F9A825"

# --- CSS personalizado ---
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

MODALIDADES_VIOLENCIA = ["FÍSICA", "PSICOLÓGICA", "NEGLIGENCIA Y ABANDONO"]

MECANISMOS_AGRESION = [
    "NO APLICA",
    "Ahorcamiento/estrangulamiento",
    "Caídas",
    "Contundente",
    "Cortopunzante",
    "Proyectil arma de fuego",
    "Quemadura por fuego",
    "Quemadura por ácido",
    "Quemadura por líquido hirviente",
    "Sustancias domésticas",
    "Otros"
]

ESCENARIOS = [
    "Vivienda",
    "Vía pública",
    "Establecimiento educativo",
    "Lugar de trabajo",
    "Comercio",
    "Espacios abiertos",
    "Lugares con expendio de alcohol",
    "Institución de salud",
    "Área deportiva",
    "Otro"
]

AMBITOS = [
    "Hogar",
    "Escolar",
    "Laboral",
    "Institucional",
    "Virtual",
    "Comunitario",
    "Otros"
]

IDENTIDADES_GENERO = ["Hombre", "Mujer", "Hombre trans", "Mujer trans", "Otra", "Sin información"]

ORIENTACIONES_SEXUALES = ["Heterosexual", "Gay/Lesbiana", "Bisexual", "Otra", "Sin información"]

PERTENENCIAS_ETNICAS = [
    "Indígena", "Rom/Gitano", "Raizal", "Palenquero",
    "Negro/Mulato/Afrocolombiano", "Otro", "Ninguno"
]

PARENTESCOS_AGRESOR = [
    "Padre", "Madre", "Pareja", "Ex-Pareja",
    "Hijo/a", "Hermano/a", "Otro familiar", "Ninguno"
]

RELACIONES_NO_FAMILIAR = [
    "Profesor", "Amigo", "Compañero de trabajo", "Compañero de estudio",
    "Conocido sin trato", "Jefe", "Sacerdote/Pastor",
    "Servidor público", "Desconocido", "Vecino",
    "Sin información", "Otro"
]

ACTIVIDADES_VICTIMA = [
    "Estudiante", "Trabajador doméstico", "Persona dedicada al hogar",
    "Líder cívico", "Persona en situación de prostitución",
    "Campesino/a", "Cuidador", "Empleado", "Independiente",
    "Ninguna", "Otro"
]

GRUPOS_POBLACIONALES = [
    "Desplazado", "Migrante", "PPL (Privado de la libertad)",
    "Habitante de calle", "ICBF", "Madre comunitaria",
    "Desmovilizado", "Víctima del conflicto armado", "Otro"
]

ESTADOS_CASO = [
    "ACTIVO", "CERRADO", "EN SEGUIMIENTO",
    "REMITIDO A OTRA EPS", "FALLECIDO", "SIN CONTACTO"
]

# Columnas de la hoja DATOS en Google Sheets (70 columnas)
COLUMNAS_DATOS = [
    "id", "fecha_digitacion", "funcionario_reporta", "eps_reporta",
    "semana_epidemiologica",
    # Paciente
    "nombres", "apellidos", "tipo_documento", "numero_documento",
    "edad", "curso_vida", "sexo", "identidad_genero", "orientacion_sexual",
    "pertenencia_etnica", "municipio_residencia",
    "gestante", "semanas_gestacion", "discapacidad", "grupos_poblacionales",
    # Hecho
    "modalidad_violencia", "fecha_hecho", "hora_hecho",
    "municipio_hecho", "mecanismo_agresion", "escenario", "ambito",
    "consumo_spa_victima", "consumo_alcohol_victima",
    "jefatura_hogar", "actividad_victima",
    "antec_violencia", "conflicto_armado",
    # Agresor
    "sexo_agresor", "edad_agresor", "parentesco_agresor",
    "convive_agresor", "agresor_no_familiar",
    # Notificación / Atención
    "fecha_notificacion_sivigila", "fecha_consulta", "fecha_inicio_sintomas",
    "upgd_atencion", "municipio_atencion", "fecha_atencion",
    "hospitalizado", "fecha_hospitalizacion", "fecha_alta",
    "condicion_final", "fecha_defuncion",
    # Salud Mental y otras atenciones
    "atencion_salud_mental", "fecha_salud_mental",
    "valoracion_psicologia", "fecha_psicologia",
    "valoracion_psiquiatria", "fecha_psiquiatria",
    "atencion_medicina_general", "atencion_trabajo_social",
    "atencion_salud_ocupacional",
    "remision_proteccion", "reporte_autoridades",
    # Seguimiento
    "seguimiento_1", "seguimiento_2", "seguimiento_3",
    "ruta_atencion_integral", "asiste_servicios",
    "num_seguimientos_realizados",
    "abandono_proceso", "reincidencia_nuevo_evento",
    "estado_caso", "observaciones",
    # Trazabilidad
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
        st.info("Verifique que las credenciales en st.secrets estén correctamente configuradas.")
        return None


def obtener_hoja_datos(spreadsheet):
    """Retorna la hoja 'DATOS' del spreadsheet (la crea si no existe)."""
    try:
        return spreadsheet.worksheet("DATOS")
    except gspread.exceptions.WorksheetNotFound:
        hoja = spreadsheet.add_worksheet(title="DATOS", rows=2000, cols=len(COLUMNAS_DATOS))
        hoja.append_row(COLUMNAS_DATOS, table_range="A1")
        return hoja


def obtener_hoja_usuarios(spreadsheet):
    """Retorna la hoja 'USUARIOS' del spreadsheet (la crea si no existe)."""
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
    """Convierte número de columna (1-indexado) a letra(s) de Excel. Ej: 1→A, 27→AA."""
    resultado = ""
    while n > 0:
        n, residuo = divmod(n - 1, 26)
        resultado = chr(65 + residuo) + resultado
    return resultado


def generar_id():
    """Genera un ID único basado en timestamp para casos de violencia."""
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
    """Genera hash SHA-256 de la contraseña."""
    return hashlib.sha256(password.encode()).hexdigest()


def verificar_credenciales(spreadsheet, usuario, password):
    """Verifica las credenciales contra la hoja USUARIOS."""
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
    """Crea un nuevo usuario en la hoja USUARIOS."""
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
    """Filtra el DataFrame según el rol del usuario logueado."""
    if st.session_state.get("rol") == "SECRETARIA":
        return df
    eps_usuario = st.session_state.get("eps_asignada", "")
    if eps_usuario and not df.empty:
        return df[df["eps_reporta"] == eps_usuario]
    return df


# ============================================================
# PANTALLA DE LOGIN
# ============================================================

def mostrar_login():
    """Pantalla de inicio de sesión."""
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("Imagen1.png", width=250, use_container_width=False)
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
# SIDEBAR (después de login)
# ============================================================

def mostrar_sidebar():
    """Sidebar con logo, info de usuario y navegación."""
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
        if st.session_state.get("rol") == "SECRETARIA":
            opciones.append("⚙️ Gestionar Usuarios")

        pagina = st.radio("Navegación", opciones, label_visibility="collapsed")

        st.markdown("---")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        st.markdown("""
        <div style="position:fixed; bottom:10px; font-size:0.7rem; opacity:0.6;">
            SIVIGILA Evento 875<br>Valle del Cauca v1.0
        </div>
        """, unsafe_allow_html=True)

        return pagina


# ============================================================
# MÓDULO 1: FORMULARIO DE DIGITACIÓN
# ============================================================

def modulo_formulario(spreadsheet):
    """Formulario de registro de nuevos casos."""
    st.markdown("""
    <div class="main-header">
        <h1>📝 Registro de Nuevo Caso - Violencia de Género e Intrafamiliar</h1>
        <p>Evento 875 SIVIGILA | SIN componente sexual</p>
    </div>
    """, unsafe_allow_html=True)

    st.info("ℹ️ Este aplicativo NO registra violencia sexual. Solo modalidades: FÍSICA, PSICOLÓGICA y NEGLIGENCIA Y ABANDONO.")

    with st.form("formulario_nuevo_caso", clear_on_submit=True):
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
                                           options=["NO", "SI", "SIN INFORMACIÓN"])
            conflicto_armado = st.radio("¿Hecho en marco del conflicto armado?",
                                        options=["NO", "SI"], horizontal=True)

        eps_otra = ""
        if st.session_state.get("rol") != "EPS" and eps_seleccionada == "OTRA (especificar)":
            eps_otra = st.text_input("Especifique la EPS:").upper()

        st.markdown("---")

        # ---- Datos del Paciente / Víctima ----
        st.markdown("#### 👤 Datos del Paciente / Víctima")
        col1, col2 = st.columns(2)
        with col1:
            nombres = st.text_input("Nombres *", placeholder="NOMBRES DE LA VÍCTIMA")
            tipo_doc = st.selectbox("Tipo de documento *", options=TIPOS_DOCUMENTO, index=2)
            edad = st.number_input("Edad *", min_value=0, max_value=120, value=0, step=1)
            identidad_genero = st.selectbox("Identidad de género", options=IDENTIDADES_GENERO)
            pertenencia_etnica = st.selectbox("Pertenencia étnica", options=PERTENENCIAS_ETNICAS, index=6)
        with col2:
            apellidos = st.text_input("Apellidos *", placeholder="APELLIDOS DE LA VÍCTIMA")
            numero_doc = st.text_input("Número de documento *", placeholder="Solo números")
            sexo = st.selectbox("Sexo *", options=["Masculino", "Femenino", "Indeterminado"])
            orientacion_sexual = st.selectbox("Orientación sexual", options=ORIENTACIONES_SEXUALES)
            municipio_residencia = st.selectbox("Municipio de residencia *", options=[""] + MUNICIPIOS_VALLE)

        col1, col2 = st.columns(2)
        with col1:
            curso_vida = calcular_curso_vida(edad)
            st.text_input("Curso de vida (automático)", value=curso_vida, disabled=True)
            discapacidad = st.selectbox("Discapacidad", options=["NO", "SI"])
        with col2:
            gestante = st.selectbox("Gestante", options=["NO APLICA", "NO", "SI"])
            semanas_gestacion = st.number_input("Semanas de gestación (solo si gestante = SI)",
                                                min_value=0, max_value=42, value=0)

        grupos_pob = st.multiselect("Grupos poblacionales", options=GRUPOS_POBLACIONALES)

        # Alerta de menor de 14 años
        if edad > 0 and edad < 14:
            st.error("🚨 **CASO PRIORITARIO** - Menor de 14 años. Reporte obligatorio a ICBF y Fiscalía.")

        st.markdown("---")

        # ---- Datos del Hecho ----
        st.markdown("#### 🎯 Datos del Hecho")
        col1, col2 = st.columns(2)
        with col1:
            modalidad = st.selectbox("Modalidad de la violencia *", options=MODALIDADES_VIOLENCIA)
            fecha_hecho = st.date_input("Fecha del hecho *", value=date.today())
            municipio_hecho = st.selectbox("Municipio del hecho *", options=[""] + MUNICIPIOS_VALLE)
            escenario = st.selectbox("Escenario", options=ESCENARIOS)
        with col2:
            hora_hecho = st.time_input("Hora del hecho", value=None)
            mecanismo = st.selectbox("Mecanismo de la agresión", options=MECANISMOS_AGRESION,
                                     help="Si la modalidad es NEGLIGENCIA Y ABANDONO, seleccione NO APLICA.")
            ambito = st.selectbox("Ámbito", options=AMBITOS)
            actividad_victima = st.selectbox("Actividad de la víctima", options=ACTIVIDADES_VICTIMA)

        col1, col2 = st.columns(2)
        with col1:
            consumo_spa = st.selectbox("Consumo de SPA por la víctima",
                                       options=["NO", "SI", "SIN INFORMACIÓN"])
            jefatura_hogar = st.selectbox("¿Persona con jefatura de hogar?", options=["NO", "SI"])
        with col2:
            consumo_alcohol = st.selectbox("Consumo de alcohol por la víctima",
                                           options=["NO", "SI", "SIN INFORMACIÓN"])

        st.markdown("---")

        # ---- Datos del Agresor ----
        st.markdown("#### 👥 Datos del Agresor")
        col1, col2 = st.columns(2)
        with col1:
            sexo_agresor = st.selectbox("Sexo del agresor",
                                        options=["Masculino", "Femenino", "Intersexual", "Sin dato"])
            parentesco_agresor = st.selectbox("Parentesco con la víctima", options=PARENTESCOS_AGRESOR)
            convive_agresor = st.selectbox("¿Convive con el agresor?", options=["NO", "SI"])
        with col2:
            edad_agresor = st.number_input("Edad del agresor (0 = sin dato)",
                                           min_value=0, max_value=120, value=0)
            agresor_no_familiar = st.selectbox("Agresor no familiar (relación)",
                                               options=["No aplica"] + RELACIONES_NO_FAMILIAR)

        st.markdown("---")

        # ---- Notificación y Atención ----
        st.markdown("#### 📋 Notificación y Atención Inicial")
        col1, col2 = st.columns(2)
        with col1:
            fecha_notificacion = st.date_input("Fecha de notificación SIVIGILA *", value=date.today())
            fecha_consulta = st.date_input("Fecha de consulta", value=None)
            fecha_inicio_sintomas = st.date_input("Fecha de inicio de síntomas", value=None)
            upgd_atencion = st.text_input("UPGD / IPS que atendió")
        with col2:
            municipio_atencion = st.selectbox("Municipio de la atención", options=[""] + MUNICIPIOS_VALLE)
            fecha_atencion = st.date_input("Fecha de la atención", value=None)
            hospitalizado = st.selectbox("Hospitalizado", options=["NO", "SI", "NO APLICA"])

        col1, col2, col3 = st.columns(3)
        with col1:
            fecha_hospitalizacion = st.date_input("Fecha de hospitalización", value=None)
        with col2:
            fecha_alta = st.date_input("Fecha de alta", value=None)
        with col3:
            condicion_final = st.selectbox("Condición final", options=["VIVO", "MUERTO", "NO SABE"])

        fecha_defuncion = st.date_input("Fecha de defunción (solo si condición = MUERTO)", value=None)

        st.markdown("---")

        # ---- Atención Integral en Salud ----
        st.markdown("#### 🧠 Atención Integral en Salud")
        st.caption("Solo componentes aplicables a violencia NO sexual.")
        col1, col2 = st.columns(2)
        sino_na = ["NO", "SI", "NO APLICA"]
        with col1:
            atencion_sm = st.selectbox("Atención por Salud Mental", options=sino_na)
            fecha_sm = st.date_input("Fecha atención Salud Mental", value=None)
            val_psicologia = st.selectbox("Valoración por Psicología", options=sino_na)
            fecha_psicologia = st.date_input("Fecha primera atención Psicología", value=None)
            atencion_med_gral = st.selectbox("Atención Medicina General", options=sino_na)
            atencion_ts = st.selectbox("Atención Trabajo Social", options=sino_na)
        with col2:
            val_psiquiatria = st.selectbox("Valoración por Psiquiatría", options=sino_na)
            fecha_psiquiatria = st.date_input("Fecha primera atención Psiquiatría", value=None)
            atencion_so = st.selectbox("Atención Salud Ocupacional", options=sino_na)
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
                                         options=["SI", "NO", "EN PROCESO"])
            asiste_servicios = st.selectbox("¿Asiste a los servicios?",
                                            options=["SI", "NO", "SIN CONTACTO"])
            num_seguimientos = st.number_input("Número de seguimientos realizados",
                                               min_value=0, max_value=50, value=0)
        with col2:
            abandono_proceso = st.selectbox("¿Abandonó el proceso?",
                                            options=["NO", "SI", "SIN INFORMACIÓN"])
            reincidencia = st.selectbox("¿Reincidencia / nuevo evento?",
                                        options=["NO", "SI", "SIN INFORMACIÓN"])
            estado_caso = st.selectbox("Estado del caso *", options=ESTADOS_CASO)

        observaciones = st.text_area("Observaciones",
                                     placeholder="Bitácora de gestión: llamadas, notas, derivaciones...",
                                     height=120)

        funcionario = st.text_input("Funcionario que reporta",
                                    value=st.session_state.get("nombre_completo", ""),
                                    disabled=True)

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
            if not numero_doc.strip():
                errores.append("Número de documento es obligatorio.")
            if not municipio_residencia:
                errores.append("Municipio de residencia es obligatorio.")
            if not municipio_hecho:
                errores.append("Municipio del hecho es obligatorio.")
            if edad == 0:
                errores.append("Verifique que la edad sea correcta (actualmente es 0).")
            if gestante == "SI" and sexo != "Femenino":
                errores.append("Si está gestante, el sexo debe ser Femenino.")
            if modalidad == "NEGLIGENCIA Y ABANDONO" and mecanismo not in ("NO APLICA", ""):
                errores.append("Si la modalidad es NEGLIGENCIA Y ABANDONO, el mecanismo debe ser NO APLICA.")

            if errores:
                for err in errores:
                    st.error(f"⚠️ {err}")
            else:
                df_check = cargar_datos(spreadsheet, forzar=True)
                df_check = filtrar_por_rol(df_check)
                duplicados = buscar_por_documento(df_check, numero_doc)
                if not duplicados.empty:
                    st.warning(f"⚠️ Ya existe(n) **{len(duplicados)}** registro(s) con el documento "
                               f"**{numero_doc}**. Si desea actualizar, use el módulo "
                               "'Editar / Actualizar Caso'.")
                    cols_mostrar = ["nombres", "apellidos", "numero_documento", "eps_reporta",
                                    "estado_caso", "fecha_notificacion_sivigila"]
                    cols_disp = [c for c in cols_mostrar if c in duplicados.columns]
                    st.dataframe(duplicados[cols_disp], use_container_width=True, hide_index=True)
                else:
                    datos = {
                        "eps_reporta": eps_final,
                        "semana_epidemiologica": str(semana_epi),
                        "nombres": nombres.upper().strip(),
                        "apellidos": apellidos.upper().strip(),
                        "tipo_documento": tipo_doc,
                        "numero_documento": numero_doc.strip(),
                        "edad": str(edad),
                        "curso_vida": calcular_curso_vida(edad),
                        "sexo": sexo,
                        "identidad_genero": identidad_genero,
                        "orientacion_sexual": orientacion_sexual,
                        "pertenencia_etnica": pertenencia_etnica,
                        "municipio_residencia": municipio_residencia,
                        "gestante": gestante,
                        "semanas_gestacion": str(semanas_gestacion),
                        "discapacidad": discapacidad,
                        "grupos_poblacionales": ", ".join(grupos_pob),
                        "modalidad_violencia": modalidad,
                        "fecha_hecho": str(fecha_hecho) if fecha_hecho else "",
                        "hora_hecho": str(hora_hecho) if hora_hecho else "",
                        "municipio_hecho": municipio_hecho,
                        "mecanismo_agresion": mecanismo,
                        "escenario": escenario,
                        "ambito": ambito,
                        "consumo_spa_victima": consumo_spa,
                        "consumo_alcohol_victima": consumo_alcohol,
                        "jefatura_hogar": jefatura_hogar,
                        "actividad_victima": actividad_victima,
                        "antec_violencia": antec_violencia,
                        "conflicto_armado": conflicto_armado,
                        "sexo_agresor": sexo_agresor,
                        "edad_agresor": str(edad_agresor),
                        "parentesco_agresor": parentesco_agresor,
                        "convive_agresor": convive_agresor,
                        "agresor_no_familiar": agresor_no_familiar,
                        "fecha_notificacion_sivigila": str(fecha_notificacion) if fecha_notificacion else "",
                        "fecha_consulta": str(fecha_consulta) if fecha_consulta else "",
                        "fecha_inicio_sintomas": str(fecha_inicio_sintomas) if fecha_inicio_sintomas else "",
                        "upgd_atencion": upgd_atencion,
                        "municipio_atencion": municipio_atencion,
                        "fecha_atencion": str(fecha_atencion) if fecha_atencion else "",
                        "hospitalizado": hospitalizado,
                        "fecha_hospitalizacion": str(fecha_hospitalizacion) if fecha_hospitalizacion else "",
                        "fecha_alta": str(fecha_alta) if fecha_alta else "",
                        "condicion_final": condicion_final,
                        "fecha_defuncion": str(fecha_defuncion) if fecha_defuncion else "",
                        "atencion_salud_mental": atencion_sm,
                        "fecha_salud_mental": str(fecha_sm) if fecha_sm else "",
                        "valoracion_psicologia": val_psicologia,
                        "fecha_psicologia": str(fecha_psicologia) if fecha_psicologia else "",
                        "valoracion_psiquiatria": val_psiquiatria,
                        "fecha_psiquiatria": str(fecha_psiquiatria) if fecha_psiquiatria else "",
                        "atencion_medicina_general": atencion_med_gral,
                        "atencion_trabajo_social": atencion_ts,
                        "atencion_salud_ocupacional": atencion_so,
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


# ============================================================
# MÓDULO 2: TABLERO DE CONTROL (DASHBOARD)
# ============================================================

def modulo_dashboard(spreadsheet):
    """Tablero de control con KPIs, gráficas y alertas."""
    st.markdown("""
    <div class="main-header">
        <h1>📊 Tablero de Control - Violencia de Género e Intrafamiliar</h1>
        <p>Evento 875 SIVIGILA | Secretaría Departamental de Salud | Valle del Cauca</p>
    </div>
    """, unsafe_allow_html=True)

    df = cargar_datos(spreadsheet, forzar=False)
    df = filtrar_por_rol(df)

    if df.empty:
        st.info("📭 No hay datos registrados aún. Comience registrando casos en el módulo de Digitación.")
        return

    # Conversión de tipos
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
            filtro_municipio = st.multiselect("Municipio del hecho",
                                              options=sorted(df["municipio_hecho"].unique().tolist()))
        with col3:
            filtro_modalidad = st.multiselect("Modalidad",
                                              options=sorted(df["modalidad_violencia"].unique().tolist()))
        with col4:
            filtro_estado = st.multiselect("Estado del caso",
                                           options=sorted(df["estado_caso"].unique().tolist()))

        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_curso = st.multiselect("Curso de vida",
                                          options=sorted(df["curso_vida"].unique().tolist()))
        with col2:
            filtro_sexo = st.multiselect("Sexo de la víctima",
                                         options=sorted(df["sexo"].unique().tolist()))
        with col3:
            try:
                fechas_validas = pd.to_datetime(df["fecha_hecho"], errors="coerce").dropna()
                if not fechas_validas.empty:
                    fecha_min = fechas_validas.min().date()
                    fecha_max = fechas_validas.max().date()
                    filtro_fecha = st.date_input("Rango de fechas del hecho",
                                                 value=(fecha_min, fecha_max),
                                                 min_value=fecha_min, max_value=fecha_max)
                else:
                    filtro_fecha = None
            except Exception:
                filtro_fecha = None

    # Aplicar filtros
    df_filtrado = df.copy()
    if filtro_eps:
        df_filtrado = df_filtrado[df_filtrado["eps_reporta"].isin(filtro_eps)]
    if filtro_municipio:
        df_filtrado = df_filtrado[df_filtrado["municipio_hecho"].isin(filtro_municipio)]
    if filtro_modalidad:
        df_filtrado = df_filtrado[df_filtrado["modalidad_violencia"].isin(filtro_modalidad)]
    if filtro_estado:
        df_filtrado = df_filtrado[df_filtrado["estado_caso"].isin(filtro_estado)]
    if filtro_curso:
        df_filtrado = df_filtrado[df_filtrado["curso_vida"].isin(filtro_curso)]
    if filtro_sexo:
        df_filtrado = df_filtrado[df_filtrado["sexo"].isin(filtro_sexo)]
    if filtro_fecha and isinstance(filtro_fecha, tuple) and len(filtro_fecha) == 2:
        df_filtrado["_fecha_temp"] = pd.to_datetime(df_filtrado["fecha_hecho"], errors="coerce")
        df_filtrado = df_filtrado[
            (df_filtrado["_fecha_temp"] >= pd.Timestamp(filtro_fecha[0])) &
            (df_filtrado["_fecha_temp"] <= pd.Timestamp(filtro_fecha[1]))
        ]
        df_filtrado = df_filtrado.drop(columns=["_fecha_temp"], errors="ignore")

    # --- KPIs ---
    total_casos = len(df_filtrado)
    menores_18 = len(df_filtrado[df_filtrado["edad"] < 18])
    pct_menores = (menores_18 / total_casos * 100) if total_casos > 0 else 0
    mujeres = len(df_filtrado[df_filtrado["sexo"] == "Femenino"])
    pct_mujeres = (mujeres / total_casos * 100) if total_casos > 0 else 0
    reincidentes = len(df_filtrado[df_filtrado["antec_violencia"].str.upper() == "SI"])
    pct_reincidentes = (reincidentes / total_casos * 100) if total_casos > 0 else 0
    activos_sin_seg = len(df_filtrado[
        (df_filtrado["estado_caso"].str.upper() == "ACTIVO") &
        (df_filtrado["num_seguimientos_realizados"] == 0)
    ])
    gestantes = len(df_filtrado[df_filtrado["gestante"].str.upper() == "SI"])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{total_casos}</div>
            <div class="kpi-label">Total Casos Registrados</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card kpi-card-warning">
            <div class="kpi-value">{menores_18} <small style="font-size:0.5em;">({pct_menores:.1f}%)</small></div>
            <div class="kpi-label">⚠️ Menores de 18 años</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{mujeres} <small style="font-size:0.5em;">({pct_mujeres:.1f}%)</small></div>
            <div class="kpi-label">Casos en mujeres</div>
        </div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="kpi-card kpi-card-danger">
            <div class="kpi-value">{reincidentes} <small style="font-size:0.5em;">({pct_reincidentes:.1f}%)</small></div>
            <div class="kpi-label">🚨 Reincidentes (violencia previa)</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card kpi-card-danger">
            <div class="kpi-value">{activos_sin_seg}</div>
            <div class="kpi-label">🚨 Activos sin seguimiento</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-card kpi-card-danger">
            <div class="kpi-value">{gestantes}</div>
            <div class="kpi-label">🚨 Casos en gestantes</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Gráficas ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Distribución", "📈 Tendencias", "👥 Agresor", "🚨 Alertas"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            df_mun = df_filtrado["municipio_hecho"].value_counts().reset_index()
            df_mun.columns = ["Municipio", "Casos"]
            df_mun = df_mun.sort_values("Casos", ascending=True)
            fig_mun = px.bar(df_mun, x="Casos", y="Municipio", orientation="h",
                             title="Casos por Municipio del Hecho",
                             color="Casos", color_continuous_scale="Reds")
            fig_mun.update_layout(height=max(400, len(df_mun) * 28),
                                  showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig_mun, use_container_width=True)

        with col2:
            df_eps = df_filtrado["eps_reporta"].value_counts().reset_index()
            df_eps.columns = ["EPS", "Casos"]
            fig_eps = px.bar(df_eps, x="EPS", y="Casos",
                             title="Casos por EPS",
                             color="Casos", color_continuous_scale="Blues")
            fig_eps.update_layout(xaxis_tickangle=-45, height=400,
                                  showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig_eps, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            df_mod = df_filtrado["modalidad_violencia"].value_counts().reset_index()
            df_mod.columns = ["Modalidad", "Casos"]
            fig_mod = px.pie(df_mod, values="Casos", names="Modalidad",
                             title="Distribución por Modalidad de Violencia",
                             color_discrete_sequence=["#D32F2F", "#F9A825", "#9C27B0"],
                             hole=0.4)
            fig_mod.update_traces(textinfo="percent+value")
            st.plotly_chart(fig_mod, use_container_width=True)

        with col2:
            df_sexo = df_filtrado["sexo"].value_counts().reset_index()
            df_sexo.columns = ["Sexo", "Casos"]
            fig_sexo = px.pie(df_sexo, values="Casos", names="Sexo",
                              title="Distribución por Sexo de la Víctima",
                              color_discrete_sequence=["#D32F2F", "#1565C0", "#9E9E9E"],
                              hole=0.4)
            fig_sexo.update_traces(textinfo="percent+value")
            st.plotly_chart(fig_sexo, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            df_curso = df_filtrado["curso_vida"].value_counts().reset_index()
            df_curso.columns = ["Curso de Vida", "Casos"]
            fig_curso = px.pie(df_curso, values="Casos", names="Curso de Vida",
                               title="Distribución por Curso de Vida",
                               color_discrete_sequence=["#0D2137", "#1B3A5C", "#2E6B9E",
                                                        "#4A90C4", "#7FB3D8", "#B5D4E9"],
                               hole=0.4)
            fig_curso.update_traces(textinfo="percent+value")
            st.plotly_chart(fig_curso, use_container_width=True)

        with col2:
            df_mec = df_filtrado["mecanismo_agresion"].value_counts().reset_index()
            df_mec.columns = ["Mecanismo", "Casos"]
            df_mec = df_mec.sort_values("Casos", ascending=True)
            fig_mec = px.bar(df_mec, x="Casos", y="Mecanismo", orientation="h",
                             title="Mecanismo de Agresión más Frecuente",
                             color="Casos", color_continuous_scale="Oranges")
            fig_mec.update_layout(height=max(400, len(df_mec) * 32),
                                  showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig_mec, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            df_esc = df_filtrado["escenario"].value_counts().reset_index()
            df_esc.columns = ["Escenario", "Casos"]
            fig_esc = px.bar(df_esc, x="Escenario", y="Casos",
                             title="Escenario más Frecuente",
                             color="Casos", color_continuous_scale="Purples")
            fig_esc.update_layout(xaxis_tickangle=-45, height=400,
                                  showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig_esc, use_container_width=True)

        with col2:
            df_amb = df_filtrado["ambito"].value_counts().reset_index()
            df_amb.columns = ["Ámbito", "Casos"]
            fig_amb = px.bar(df_amb, x="Ámbito", y="Casos",
                             title="Distribución por Ámbito",
                             color="Casos", color_continuous_scale="Teal")
            fig_amb.update_layout(xaxis_tickangle=-45, height=400,
                                  showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig_amb, use_container_width=True)

    with tab2:
        df_sem = df_filtrado.groupby("semana_epidemiologica").size().reset_index(name="Casos")
        df_sem = df_sem.sort_values("semana_epidemiologica")
        fig_sem = px.line(df_sem, x="semana_epidemiologica", y="Casos",
                          title="Tendencia de Casos por Semana Epidemiológica",
                          markers=True)
        fig_sem.update_layout(xaxis_title="Semana Epidemiológica", yaxis_title="Número de Casos")
        fig_sem.update_traces(line_color=COLOR_AZUL_OSCURO, marker_color=COLOR_ROJO_ALERTA)
        st.plotly_chart(fig_sem, use_container_width=True)

        # Modalidad por curso de vida
        df_cross = df_filtrado.groupby(["curso_vida", "modalidad_violencia"]).size().reset_index(name="Casos")
        fig_cross = px.bar(df_cross, x="curso_vida", y="Casos", color="modalidad_violencia",
                           title="Modalidad de Violencia por Curso de Vida",
                           barmode="group",
                           color_discrete_map={"FÍSICA": "#D32F2F",
                                               "PSICOLÓGICA": "#F9A825",
                                               "NEGLIGENCIA Y ABANDONO": "#9C27B0"})
        fig_cross.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig_cross, use_container_width=True)

        df_estado = df_filtrado["estado_caso"].value_counts().reset_index()
        df_estado.columns = ["Estado", "Casos"]
        fig_estado = px.bar(df_estado, x="Estado", y="Casos",
                            title="Distribución por Estado del Caso",
                            color="Estado",
                            color_discrete_map={
                                "ACTIVO": "#F9A825",
                                "CERRADO": "#4CAF50",
                                "EN SEGUIMIENTO": "#2196F3",
                                "FALLECIDO": "#D32F2F",
                                "SIN CONTACTO": "#9E9E9E",
                                "REMITIDO A OTRA EPS": "#FF9800"
                            })
        fig_estado.update_layout(showlegend=False)
        st.plotly_chart(fig_estado, use_container_width=True)

    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            df_par = df_filtrado["parentesco_agresor"].value_counts().reset_index()
            df_par.columns = ["Parentesco", "Casos"]
            fig_par = px.bar(df_par, x="Parentesco", y="Casos",
                             title="Parentesco del Agresor con la Víctima",
                             color="Casos", color_continuous_scale="Reds")
            fig_par.update_layout(xaxis_tickangle=-30,
                                  showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig_par, use_container_width=True)
        with col2:
            df_sa = df_filtrado["sexo_agresor"].value_counts().reset_index()
            df_sa.columns = ["Sexo Agresor", "Casos"]
            fig_sa = px.pie(df_sa, values="Casos", names="Sexo Agresor",
                            title="Sexo del Agresor",
                            color_discrete_sequence=["#1565C0", "#D32F2F", "#9E9E9E", "#757575"],
                            hole=0.4)
            fig_sa.update_traces(textinfo="percent+value")
            st.plotly_chart(fig_sa, use_container_width=True)

        df_conv = df_filtrado["convive_agresor"].value_counts().reset_index()
        df_conv.columns = ["¿Convive con agresor?", "Casos"]
        fig_conv = px.bar(df_conv, x="¿Convive con agresor?", y="Casos",
                          title="¿La víctima convive con el agresor?",
                          color="Casos", color_continuous_scale="Reds")
        fig_conv.update_layout(showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig_conv, use_container_width=True)

    with tab4:
        # ALERTA ROJA - Reincidentes
        st.markdown("""
        <div class="alerta-roja">
            <strong>🚨 ALERTA ROJA — Pacientes con violencia previa (Reincidentes)</strong>
        </div>
        """, unsafe_allow_html=True)
        df_reinc = df_filtrado[df_filtrado["antec_violencia"].str.upper() == "SI"]
        if not df_reinc.empty:
            cols = ["numero_documento", "nombres", "apellidos", "municipio_residencia",
                    "edad", "modalidad_violencia", "eps_reporta", "estado_caso"]
            cols_disp = [c for c in cols if c in df_reinc.columns]
            st.dataframe(df_reinc[cols_disp], use_container_width=True, hide_index=True)
        else:
            st.info("No se encontraron pacientes reincidentes con los filtros actuales.")

        st.markdown("<br>", unsafe_allow_html=True)

        # ALERTA ROJA - Menores de 14
        st.markdown("""
        <div class="alerta-roja">
            <strong>🚨 ALERTA ROJA — Menores de 14 años (reporte obligatorio a ICBF y Fiscalía)</strong>
        </div>
        """, unsafe_allow_html=True)
        df_menores = df_filtrado[df_filtrado["edad"] < 14]
        if not df_menores.empty:
            cols = ["numero_documento", "nombres", "apellidos", "edad", "sexo",
                    "modalidad_violencia", "parentesco_agresor", "eps_reporta",
                    "reporte_autoridades", "estado_caso"]
            cols_disp = [c for c in cols if c in df_menores.columns]
            st.dataframe(df_menores[cols_disp], use_container_width=True, hide_index=True)
        else:
            st.info("No se encontraron casos en menores de 14 años con los filtros actuales.")

        st.markdown("<br>", unsafe_allow_html=True)

        # ALERTA ROJA - Gestantes
        st.markdown("""
        <div class="alerta-roja">
            <strong>🚨 ALERTA ROJA — Gestantes</strong>
        </div>
        """, unsafe_allow_html=True)
        df_gest = df_filtrado[df_filtrado["gestante"].str.upper() == "SI"]
        if not df_gest.empty:
            cols = ["numero_documento", "nombres", "apellidos", "edad",
                    "semanas_gestacion", "modalidad_violencia", "eps_reporta", "estado_caso"]
            cols_disp = [c for c in cols if c in df_gest.columns]
            st.dataframe(df_gest[cols_disp], use_container_width=True, hide_index=True)
        else:
            st.info("No se encontraron casos en gestantes con los filtros actuales.")

        st.markdown("<br>", unsafe_allow_html=True)

        # ALERTA AMARILLA - Sin seguimiento
        st.markdown("""
        <div class="alerta-amarilla">
            <strong>⚠️ ALERTA AMARILLA — Activos sin seguimiento o sin contacto</strong>
        </div>
        """, unsafe_allow_html=True)
        df_sinseg = df_filtrado[
            ((df_filtrado["estado_caso"].str.upper() == "ACTIVO") &
             (df_filtrado["num_seguimientos_realizados"] == 0)) |
            (df_filtrado["asiste_servicios"].str.upper().isin(["NO", "SIN CONTACTO"]))
        ]
        if not df_sinseg.empty:
            cols = ["numero_documento", "nombres", "apellidos", "municipio_residencia",
                    "modalidad_violencia", "asiste_servicios", "num_seguimientos_realizados",
                    "eps_reporta", "estado_caso"]
            cols_disp = [c for c in cols if c in df_sinseg.columns]
            st.dataframe(df_sinseg[cols_disp], use_container_width=True, hide_index=True)
        else:
            st.info("No hay casos sin seguimiento con los filtros actuales.")

        st.markdown("<br>", unsafe_allow_html=True)

        # ALERTA AMARILLA - Sin reporte a autoridades en casos graves
        st.markdown("""
        <div class="alerta-amarilla">
            <strong>⚠️ ALERTA — Casos graves sin reporte a autoridades</strong>
        </div>
        """, unsafe_allow_html=True)
        mecanismos_graves = ["Cortopunzante", "Proyectil arma de fuego",
                             "Quemadura por fuego", "Quemadura por ácido",
                             "Quemadura por líquido hirviente", "Ahorcamiento/estrangulamiento"]
        df_grave = df_filtrado[
            (df_filtrado["mecanismo_agresion"].isin(mecanismos_graves)) &
            (df_filtrado["reporte_autoridades"].str.upper() == "NO")
        ]
        if not df_grave.empty:
            cols = ["numero_documento", "nombres", "apellidos", "edad",
                    "modalidad_violencia", "mecanismo_agresion",
                    "reporte_autoridades", "eps_reporta", "estado_caso"]
            cols_disp = [c for c in cols if c in df_grave.columns]
            st.dataframe(df_grave[cols_disp], use_container_width=True, hide_index=True)
        else:
            st.info("No hay casos graves sin reporte a autoridades con los filtros actuales.")

        st.markdown("<br>", unsafe_allow_html=True)

        # ALERTA - Abandonos
        st.markdown("""
        <div class="alerta-amarilla">
            <strong>⚠️ ALERTA — Pacientes que abandonaron el proceso</strong>
        </div>
        """, unsafe_allow_html=True)
        df_aband = df_filtrado[df_filtrado["abandono_proceso"].str.upper() == "SI"]
        if not df_aband.empty:
            cols = ["numero_documento", "nombres", "apellidos", "municipio_residencia",
                    "modalidad_violencia", "eps_reporta", "estado_caso"]
            cols_disp = [c for c in cols if c in df_aband.columns]
            st.dataframe(df_aband[cols_disp], use_container_width=True, hide_index=True)
        else:
            st.info("No hay pacientes con abandono del proceso.")


# ============================================================
# MÓDULO 3: EDICIÓN Y ACTUALIZACIÓN DE CASOS
# ============================================================

def parse_date_safe(val):
    """Convierte un valor a fecha, tolerando vacíos y errores."""
    try:
        if val and str(val).strip() and str(val).strip() != "None":
            return pd.to_datetime(val).date()
    except Exception:
        pass
    return None


def modulo_edicion(spreadsheet):
    """Búsqueda y edición de registros existentes."""
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

    st.markdown("#### 🔍 Buscar Registro")
    col1, col2 = st.columns([2, 2])
    with col1:
        busq_doc = st.text_input("Buscar por número de documento", key="edit_busq_doc")
    with col2:
        busq_nombre = st.text_input("Buscar por nombre o apellido", key="edit_busq_nombre")

    df_resultado = df.copy()
    if busq_doc:
        df_resultado = df_resultado[df_resultado["numero_documento"].astype(str).str.contains(busq_doc, na=False)]
    if busq_nombre:
        busq_upper = busq_nombre.upper()
        df_resultado = df_resultado[
            df_resultado["nombres"].astype(str).str.upper().str.contains(busq_upper, na=False) |
            df_resultado["apellidos"].astype(str).str.upper().str.contains(busq_upper, na=False)
        ]

    if df_resultado.empty:
        st.warning("No se encontraron registros con los criterios de búsqueda.")
        return

    st.markdown(f"**{len(df_resultado)} registro(s) encontrado(s)**")
    cols_tabla = ["id", "nombres", "apellidos", "numero_documento", "eps_reporta",
                  "modalidad_violencia", "municipio_residencia", "edad",
                  "estado_caso", "fecha_notificacion_sivigila"]
    cols_disp = [c for c in cols_tabla if c in df_resultado.columns]
    st.dataframe(df_resultado[cols_disp], use_container_width=True, hide_index=True)

    ids_disponibles = df_resultado["id"].tolist()
    if not ids_disponibles:
        return

    st.markdown("---")
    id_seleccionado = st.selectbox("Seleccione el ID del registro a editar:", options=ids_disponibles)

    if id_seleccionado:
        registro = df_resultado[df_resultado["id"] == id_seleccionado].iloc[0].to_dict()

        st.markdown(f"#### Editando: **{registro.get('nombres', '')} {registro.get('apellidos', '')}** "
                    f"(Doc: {registro.get('numero_documento', '')})")

        with st.form("formulario_edicion"):
            # Identificación
            st.markdown("##### 🏷️ Identificación")
            col1, col2 = st.columns(2)
            with col1:
                eps_edit = st.selectbox("EPS/EAPB", options=EPS_LISTA,
                                        index=EPS_LISTA.index(registro.get("eps_reporta", ""))
                                        if registro.get("eps_reporta", "") in EPS_LISTA else 0)
                semana_edit = st.number_input("Semana epidemiológica", min_value=1, max_value=53,
                                              value=int(registro.get("semana_epidemiologica") or 1))
            with col2:
                antec_opts = ["NO", "SI", "SIN INFORMACIÓN"]
                antec_edit = st.selectbox("¿Violencia previa?", options=antec_opts,
                                          index=antec_opts.index(registro.get("antec_violencia", "NO"))
                                          if registro.get("antec_violencia", "") in antec_opts else 0)
                conf_edit = st.radio("¿Conflicto armado?", options=["NO", "SI"],
                                     index=0 if registro.get("conflicto_armado", "NO") != "SI" else 1,
                                     horizontal=True)

            # Paciente
            st.markdown("##### 👤 Datos de la Víctima")
            col1, col2 = st.columns(2)
            with col1:
                nombres_edit = st.text_input("Nombres", value=registro.get("nombres", ""))
                tipo_doc_edit = st.selectbox("Tipo documento", options=TIPOS_DOCUMENTO,
                                             index=TIPOS_DOCUMENTO.index(registro.get("tipo_documento", "CC"))
                                             if registro.get("tipo_documento", "") in TIPOS_DOCUMENTO else 2)
                edad_edit = st.number_input("Edad", min_value=0, max_value=120,
                                            value=int(registro.get("edad") or 0))
                ig_edit = st.selectbox("Identidad de género", options=IDENTIDADES_GENERO,
                                       index=IDENTIDADES_GENERO.index(registro.get("identidad_genero", "Sin información"))
                                       if registro.get("identidad_genero", "") in IDENTIDADES_GENERO else 5)
                pe_edit = st.selectbox("Pertenencia étnica", options=PERTENENCIAS_ETNICAS,
                                       index=PERTENENCIAS_ETNICAS.index(registro.get("pertenencia_etnica", "Ninguno"))
                                       if registro.get("pertenencia_etnica", "") in PERTENENCIAS_ETNICAS else 6)
            with col2:
                apellidos_edit = st.text_input("Apellidos", value=registro.get("apellidos", ""))
                num_doc_edit = st.text_input("Número de documento",
                                             value=str(registro.get("numero_documento", "")))
                sexo_opts = ["Masculino", "Femenino", "Indeterminado"]
                sexo_edit = st.selectbox("Sexo", options=sexo_opts,
                                         index=sexo_opts.index(registro.get("sexo", "Femenino"))
                                         if registro.get("sexo", "") in sexo_opts else 1)
                os_edit = st.selectbox("Orientación sexual", options=ORIENTACIONES_SEXUALES,
                                       index=ORIENTACIONES_SEXUALES.index(registro.get("orientacion_sexual",
                                                                                       "Sin información"))
                                       if registro.get("orientacion_sexual", "") in ORIENTACIONES_SEXUALES else 4)
                mun_res_edit = st.selectbox("Municipio de residencia", options=[""] + MUNICIPIOS_VALLE,
                                            index=(MUNICIPIOS_VALLE.index(registro.get("municipio_residencia", "")) + 1)
                                            if registro.get("municipio_residencia", "") in MUNICIPIOS_VALLE else 0)

            col1, col2 = st.columns(2)
            with col1:
                gest_opts = ["NO APLICA", "NO", "SI"]
                gest_edit = st.selectbox("Gestante", options=gest_opts,
                                         index=gest_opts.index(registro.get("gestante", "NO APLICA"))
                                         if registro.get("gestante", "") in gest_opts else 0)
                disc_edit = st.selectbox("Discapacidad", options=["NO", "SI"],
                                         index=0 if registro.get("discapacidad", "NO") != "SI" else 1)
            with col2:
                semgest_edit = st.number_input("Semanas de gestación", min_value=0, max_value=42,
                                               value=int(registro.get("semanas_gestacion") or 0))
                gp_actual = [g.strip() for g in str(registro.get("grupos_poblacionales", "")).split(",") if g.strip()]
                gp_edit = st.multiselect("Grupos poblacionales", options=GRUPOS_POBLACIONALES,
                                         default=[g for g in gp_actual if g in GRUPOS_POBLACIONALES])

            # Hecho
            st.markdown("##### 🎯 Datos del Hecho")
            col1, col2 = st.columns(2)
            with col1:
                mod_edit = st.selectbox("Modalidad de violencia", options=MODALIDADES_VIOLENCIA,
                                        index=MODALIDADES_VIOLENCIA.index(registro.get("modalidad_violencia", "FÍSICA"))
                                        if registro.get("modalidad_violencia", "") in MODALIDADES_VIOLENCIA else 0)
                fhecho_edit = st.date_input("Fecha del hecho",
                                            value=parse_date_safe(registro.get("fecha_hecho")))
                mun_hecho_edit = st.selectbox("Municipio del hecho", options=[""] + MUNICIPIOS_VALLE,
                                              index=(MUNICIPIOS_VALLE.index(registro.get("municipio_hecho", "")) + 1)
                                              if registro.get("municipio_hecho", "") in MUNICIPIOS_VALLE else 0)
                esc_edit = st.selectbox("Escenario", options=ESCENARIOS,
                                        index=ESCENARIOS.index(registro.get("escenario", "Vivienda"))
                                        if registro.get("escenario", "") in ESCENARIOS else 0)
            with col2:
                hora_edit = st.text_input("Hora del hecho", value=str(registro.get("hora_hecho", "")))
                mec_edit = st.selectbox("Mecanismo de la agresión", options=MECANISMOS_AGRESION,
                                        index=MECANISMOS_AGRESION.index(registro.get("mecanismo_agresion", "NO APLICA"))
                                        if registro.get("mecanismo_agresion", "") in MECANISMOS_AGRESION else 0)
                amb_edit = st.selectbox("Ámbito", options=AMBITOS,
                                        index=AMBITOS.index(registro.get("ambito", "Hogar"))
                                        if registro.get("ambito", "") in AMBITOS else 0)
                act_edit = st.selectbox("Actividad de la víctima", options=ACTIVIDADES_VICTIMA,
                                        index=ACTIVIDADES_VICTIMA.index(registro.get("actividad_victima", "Ninguna"))
                                        if registro.get("actividad_victima", "") in ACTIVIDADES_VICTIMA else 9)

            col1, col2, col3 = st.columns(3)
            sino_si = ["NO", "SI", "SIN INFORMACIÓN"]
            with col1:
                cspa_edit = st.selectbox("Consumo SPA víctima", options=sino_si,
                                         index=sino_si.index(registro.get("consumo_spa_victima", "NO"))
                                         if registro.get("consumo_spa_victima", "") in sino_si else 0)
            with col2:
                calc_edit = st.selectbox("Consumo alcohol víctima", options=sino_si,
                                         index=sino_si.index(registro.get("consumo_alcohol_victima", "NO"))
                                         if registro.get("consumo_alcohol_victima", "") in sino_si else 0)
            with col3:
                jh_edit = st.selectbox("Jefatura de hogar", options=["NO", "SI"],
                                       index=0 if registro.get("jefatura_hogar", "NO") != "SI" else 1)

            # Agresor
            st.markdown("##### 👥 Agresor")
            col1, col2 = st.columns(2)
            sa_opts = ["Masculino", "Femenino", "Intersexual", "Sin dato"]
            with col1:
                sa_edit = st.selectbox("Sexo del agresor", options=sa_opts,
                                       index=sa_opts.index(registro.get("sexo_agresor", "Masculino"))
                                       if registro.get("sexo_agresor", "") in sa_opts else 0)
                par_edit = st.selectbox("Parentesco", options=PARENTESCOS_AGRESOR,
                                        index=PARENTESCOS_AGRESOR.index(registro.get("parentesco_agresor", "Ninguno"))
                                        if registro.get("parentesco_agresor", "") in PARENTESCOS_AGRESOR else 7)
            with col2:
                ea_edit = st.number_input("Edad del agresor", min_value=0, max_value=120,
                                          value=int(registro.get("edad_agresor") or 0))
                conv_edit = st.selectbox("¿Convive con agresor?", options=["NO", "SI"],
                                         index=0 if registro.get("convive_agresor", "NO") != "SI" else 1)

            anf_opts = ["No aplica"] + RELACIONES_NO_FAMILIAR
            anf_edit = st.selectbox("Agresor no familiar (relación)", options=anf_opts,
                                    index=anf_opts.index(registro.get("agresor_no_familiar", "No aplica"))
                                    if registro.get("agresor_no_familiar", "") in anf_opts else 0)

            # Notificación / Atención
            st.markdown("##### 📋 Notificación y Atención")
            col1, col2 = st.columns(2)
            with col1:
                fnotif_edit = st.date_input("Fecha notificación SIVIGILA",
                                            value=parse_date_safe(registro.get("fecha_notificacion_sivigila")))
                fcons_edit = st.date_input("Fecha de consulta",
                                           value=parse_date_safe(registro.get("fecha_consulta")))
                finic_edit = st.date_input("Fecha inicio síntomas",
                                           value=parse_date_safe(registro.get("fecha_inicio_sintomas")))
                upgd_edit = st.text_input("UPGD/IPS", value=registro.get("upgd_atencion", ""))
            with col2:
                mun_at_edit = st.selectbox("Municipio atención", options=[""] + MUNICIPIOS_VALLE,
                                           index=(MUNICIPIOS_VALLE.index(registro.get("municipio_atencion", "")) + 1)
                                           if registro.get("municipio_atencion", "") in MUNICIPIOS_VALLE else 0)
                fat_edit = st.date_input("Fecha de la atención",
                                         value=parse_date_safe(registro.get("fecha_atencion")))
                hosp_opts = ["NO", "SI", "NO APLICA"]
                hosp_edit = st.selectbox("Hospitalizado", options=hosp_opts,
                                         index=hosp_opts.index(registro.get("hospitalizado", "NO"))
                                         if registro.get("hospitalizado", "") in hosp_opts else 0)

            col1, col2, col3 = st.columns(3)
            with col1:
                fhosp_edit = st.date_input("Fecha hospitalización",
                                           value=parse_date_safe(registro.get("fecha_hospitalizacion")))
            with col2:
                falta_edit = st.date_input("Fecha de alta",
                                           value=parse_date_safe(registro.get("fecha_alta")))
            with col3:
                cf_opts = ["VIVO", "MUERTO", "NO SABE"]
                cf_edit = st.selectbox("Condición final", options=cf_opts,
                                       index=cf_opts.index(registro.get("condicion_final", "VIVO"))
                                       if registro.get("condicion_final", "") in cf_opts else 0)

            fdef_edit = st.date_input("Fecha de defunción",
                                      value=parse_date_safe(registro.get("fecha_defuncion")))

            # Salud Mental
            st.markdown("##### 🧠 Atención Integral en Salud")
            sino_na = ["NO", "SI", "NO APLICA"]
            col1, col2 = st.columns(2)
            with col1:
                asm_edit = st.selectbox("Atención Salud Mental", options=sino_na,
                                        index=sino_na.index(registro.get("atencion_salud_mental", "NO"))
                                        if registro.get("atencion_salud_mental", "") in sino_na else 0)
                fsm_edit = st.date_input("Fecha Salud Mental",
                                         value=parse_date_safe(registro.get("fecha_salud_mental")))
                vp_edit = st.selectbox("Valoración Psicología", options=sino_na,
                                       index=sino_na.index(registro.get("valoracion_psicologia", "NO"))
                                       if registro.get("valoracion_psicologia", "") in sino_na else 0)
                fpsic_edit = st.date_input("Fecha Psicología",
                                           value=parse_date_safe(registro.get("fecha_psicologia")))
                amg_edit = st.selectbox("Atención Medicina General", options=sino_na,
                                        index=sino_na.index(registro.get("atencion_medicina_general", "NO"))
                                        if registro.get("atencion_medicina_general", "") in sino_na else 0)
                ats_edit = st.selectbox("Atención Trabajo Social", options=sino_na,
                                        index=sino_na.index(registro.get("atencion_trabajo_social", "NO"))
                                        if registro.get("atencion_trabajo_social", "") in sino_na else 0)
            with col2:
                vpq_edit = st.selectbox("Valoración Psiquiatría", options=sino_na,
                                        index=sino_na.index(registro.get("valoracion_psiquiatria", "NO"))
                                        if registro.get("valoracion_psiquiatria", "") in sino_na else 0)
                fpsiq_edit = st.date_input("Fecha Psiquiatría",
                                           value=parse_date_safe(registro.get("fecha_psiquiatria")))
                aso_edit = st.selectbox("Atención Salud Ocupacional", options=sino_na,
                                        index=sino_na.index(registro.get("atencion_salud_ocupacional", "NO"))
                                        if registro.get("atencion_salud_ocupacional", "") in sino_na else 0)
                rp_edit = st.selectbox("Remisión a protección", options=sino_na,
                                       index=sino_na.index(registro.get("remision_proteccion", "NO"))
                                       if registro.get("remision_proteccion", "") in sino_na else 0)
                ra_edit = st.selectbox("Reporte a autoridades", options=sino_na,
                                       index=sino_na.index(registro.get("reporte_autoridades", "NO"))
                                       if registro.get("reporte_autoridades", "") in sino_na else 0)

            # Seguimientos
            st.markdown("##### 📞 Seguimientos")
            seg1_edit = st.text_input("Seguimiento 1", value=str(registro.get("seguimiento_1", "")))
            seg2_edit = st.text_input("Seguimiento 2", value=str(registro.get("seguimiento_2", "")))
            seg3_edit = st.text_input("Seguimiento 3", value=str(registro.get("seguimiento_3", "")))

            # Estado
            st.markdown("##### 📊 Estado del Caso")
            col1, col2 = st.columns(2)
            ruta_opts = ["SI", "NO", "EN PROCESO"]
            asiste_opts = ["SI", "NO", "SIN CONTACTO"]
            ab_opts = ["NO", "SI", "SIN INFORMACIÓN"]
            with col1:
                ruta_edit = st.selectbox("¿En ruta de atención integral?", options=ruta_opts,
                                         index=ruta_opts.index(registro.get("ruta_atencion_integral", "SI"))
                                         if registro.get("ruta_atencion_integral", "") in ruta_opts else 0)
                asiste_edit = st.selectbox("¿Asiste a servicios?", options=asiste_opts,
                                           index=asiste_opts.index(registro.get("asiste_servicios", "SI"))
                                           if registro.get("asiste_servicios", "") in asiste_opts else 0)
                num_seg_edit = st.number_input("Nº seguimientos realizados", min_value=0, max_value=50,
                                               value=int(registro.get("num_seguimientos_realizados") or 0))
            with col2:
                aban_edit = st.selectbox("¿Abandonó el proceso?", options=ab_opts,
                                         index=ab_opts.index(registro.get("abandono_proceso", "NO"))
                                         if registro.get("abandono_proceso", "") in ab_opts else 0)
                rein_edit = st.selectbox("¿Reincidencia / nuevo evento?", options=ab_opts,
                                         index=ab_opts.index(registro.get("reincidencia_nuevo_evento", "NO"))
                                         if registro.get("reincidencia_nuevo_evento", "") in ab_opts else 0)
                est_edit = st.selectbox("Estado del caso", options=ESTADOS_CASO,
                                        index=ESTADOS_CASO.index(registro.get("estado_caso", "ACTIVO"))
                                        if registro.get("estado_caso", "") in ESTADOS_CASO else 0)

            obs_edit = st.text_area("Observaciones", value=str(registro.get("observaciones", "")), height=120)

            submitted_edit = st.form_submit_button("💾 Guardar Cambios",
                                                   use_container_width=True, type="primary")

            if submitted_edit:
                datos_actualizados = {
                    "id": id_seleccionado,
                    "fecha_digitacion": registro.get("fecha_digitacion", ""),
                    "funcionario_reporta": registro.get("funcionario_reporta", ""),
                    "eps_reporta": eps_edit,
                    "semana_epidemiologica": str(semana_edit),
                    "nombres": nombres_edit.upper().strip(),
                    "apellidos": apellidos_edit.upper().strip(),
                    "tipo_documento": tipo_doc_edit,
                    "numero_documento": num_doc_edit.strip(),
                    "edad": str(edad_edit),
                    "curso_vida": calcular_curso_vida(edad_edit),
                    "sexo": sexo_edit,
                    "identidad_genero": ig_edit,
                    "orientacion_sexual": os_edit,
                    "pertenencia_etnica": pe_edit,
                    "municipio_residencia": mun_res_edit,
                    "gestante": gest_edit,
                    "semanas_gestacion": str(semgest_edit),
                    "discapacidad": disc_edit,
                    "grupos_poblacionales": ", ".join(gp_edit),
                    "modalidad_violencia": mod_edit,
                    "fecha_hecho": str(fhecho_edit) if fhecho_edit else "",
                    "hora_hecho": hora_edit,
                    "municipio_hecho": mun_hecho_edit,
                    "mecanismo_agresion": mec_edit,
                    "escenario": esc_edit,
                    "ambito": amb_edit,
                    "consumo_spa_victima": cspa_edit,
                    "consumo_alcohol_victima": calc_edit,
                    "jefatura_hogar": jh_edit,
                    "actividad_victima": act_edit,
                    "antec_violencia": antec_edit,
                    "conflicto_armado": conf_edit,
                    "sexo_agresor": sa_edit,
                    "edad_agresor": str(ea_edit),
                    "parentesco_agresor": par_edit,
                    "convive_agresor": conv_edit,
                    "agresor_no_familiar": anf_edit,
                    "fecha_notificacion_sivigila": str(fnotif_edit) if fnotif_edit else "",
                    "fecha_consulta": str(fcons_edit) if fcons_edit else "",
                    "fecha_inicio_sintomas": str(finic_edit) if finic_edit else "",
                    "upgd_atencion": upgd_edit,
                    "municipio_atencion": mun_at_edit,
                    "fecha_atencion": str(fat_edit) if fat_edit else "",
                    "hospitalizado": hosp_edit,
                    "fecha_hospitalizacion": str(fhosp_edit) if fhosp_edit else "",
                    "fecha_alta": str(falta_edit) if falta_edit else "",
                    "condicion_final": cf_edit,
                    "fecha_defuncion": str(fdef_edit) if fdef_edit else "",
                    "atencion_salud_mental": asm_edit,
                    "fecha_salud_mental": str(fsm_edit) if fsm_edit else "",
                    "valoracion_psicologia": vp_edit,
                    "fecha_psicologia": str(fpsic_edit) if fpsic_edit else "",
                    "valoracion_psiquiatria": vpq_edit,
                    "fecha_psiquiatria": str(fpsiq_edit) if fpsiq_edit else "",
                    "atencion_medicina_general": amg_edit,
                    "atencion_trabajo_social": ats_edit,
                    "atencion_salud_ocupacional": aso_edit,
                    "remision_proteccion": rp_edit,
                    "reporte_autoridades": ra_edit,
                    "seguimiento_1": seg1_edit,
                    "seguimiento_2": seg2_edit,
                    "seguimiento_3": seg3_edit,
                    "ruta_atencion_integral": ruta_edit,
                    "asiste_servicios": asiste_edit,
                    "num_seguimientos_realizados": str(num_seg_edit),
                    "abandono_proceso": aban_edit,
                    "reincidencia_nuevo_evento": rein_edit,
                    "estado_caso": est_edit,
                    "observaciones": obs_edit,
                }

                with st.spinner("Actualizando registro..."):
                    exito, msg = actualizar_registro(
                        spreadsheet, id_seleccionado, datos_actualizados,
                        st.session_state.get("nombre_completo", "")
                    )
                if exito:
                    st.success(f"✅ Registro actualizado para "
                               f"**{nombres_edit.upper()} {apellidos_edit.upper()}**")
                else:
                    st.error(f"❌ Error al actualizar: {msg}")


# ============================================================
# MÓDULO 4: EXPORTACIÓN DE DATOS
# ============================================================

def modulo_exportacion(spreadsheet):
    """Exportación de datos a CSV y Excel."""
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

    with st.expander("🔽 Filtrar datos antes de exportar"):
        col1, col2 = st.columns(2)
        with col1:
            exp_eps = st.multiselect("EPS", options=sorted(df["eps_reporta"].unique().tolist()), key="exp_eps")
            exp_mun = st.multiselect("Municipio del hecho",
                                     options=sorted(df["municipio_hecho"].unique().tolist()), key="exp_mun")
        with col2:
            exp_mod = st.multiselect("Modalidad",
                                     options=sorted(df["modalidad_violencia"].unique().tolist()), key="exp_mod")
            exp_estado = st.multiselect("Estado",
                                        options=sorted(df["estado_caso"].unique().tolist()), key="exp_estado")

    df_export = df.copy()
    if exp_eps:
        df_export = df_export[df_export["eps_reporta"].isin(exp_eps)]
    if exp_mun:
        df_export = df_export[df_export["municipio_hecho"].isin(exp_mun)]
    if exp_mod:
        df_export = df_export[df_export["modalidad_violencia"].isin(exp_mod)]
    if exp_estado:
        df_export = df_export[df_export["estado_caso"].isin(exp_estado)]

    st.markdown(f"**Registros a exportar (con filtros): {len(df_export)}**")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📄 Descargar CSV")
        csv_data = df_export.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇️ Descargar CSV",
            data=csv_data,
            file_name=f"sivigila_875_violencia_valle_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        st.markdown("#### 📊 Descargar Excel (.xlsx)")
        st.markdown("*Con hojas separadas por modalidad*")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_export.to_excel(writer, sheet_name="TODOS_LOS_DATOS", index=False)
            for modalidad in MODALIDADES_VIOLENCIA:
                df_mod = df_export[df_export["modalidad_violencia"] == modalidad]
                if not df_mod.empty:
                    nombre_hoja = modalidad.split()[0][:31]
                    df_mod.to_excel(writer, sheet_name=nombre_hoja, index=False)
        buffer.seek(0)
        st.download_button(
            label="⬇️ Descargar Excel",
            data=buffer,
            file_name=f"sivigila_875_violencia_valle_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.markdown("---")
    st.markdown("#### 👁️ Vista previa de los datos")
    st.dataframe(df_export, use_container_width=True, hide_index=True)


# ============================================================
# MÓDULO 5: GESTIÓN DE USUARIOS (solo SECRETARÍA)
# ============================================================

def modulo_gestion_usuarios(spreadsheet):
    """Gestión de usuarios (solo administrador)."""
    st.markdown("""
    <div class="main-header">
        <h1>⚙️ Gestión de Usuarios</h1>
        <p>Crear y administrar usuarios del sistema</p>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("rol") != "SECRETARIA":
        st.error("⛔ No tiene permisos para acceder a este módulo.")
        return

    st.markdown("#### 👥 Usuarios registrados")
    try:
        hoja_usuarios = obtener_hoja_usuarios(spreadsheet)
        registros = hoja_usuarios.get_all_records()
        df_usuarios = pd.DataFrame(registros)
        if not df_usuarios.empty:
            df_mostrar = df_usuarios[["usuario", "nombre_completo", "rol", "eps_asignada"]].copy()
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        else:
            st.info("No hay usuarios registrados.")
    except Exception as e:
        st.error(f"Error al cargar usuarios: {str(e)}")

    st.markdown("---")

    st.markdown("#### ➕ Crear Nuevo Usuario")
    with st.form("form_nuevo_usuario", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nuevo_usuario = st.text_input("Nombre de usuario *", placeholder="Ej: digitador.sura")
            nueva_password = st.text_input("Contraseña *", type="password")
            confirmar_password = st.text_input("Confirmar contraseña *", type="password")
        with col2:
            nuevo_nombre = st.text_input("Nombre completo *", placeholder="Ej: María García López")
            nuevo_rol = st.selectbox("Rol *", options=["EPS", "SECRETARIA"])
            nueva_eps = st.selectbox("EPS asignada (solo para rol EPS)",
                                     options=["N/A"] + [e for e in EPS_LISTA if e != "OTRA (especificar)"])

        crear = st.form_submit_button("✅ Crear Usuario", use_container_width=True, type="primary")

        if crear:
            if not nuevo_usuario or not nueva_password or not nuevo_nombre:
                st.error("⚠️ Todos los campos marcados con * son obligatorios.")
            elif nueva_password != confirmar_password:
                st.error("⚠️ Las contraseñas no coinciden.")
            elif len(nueva_password) < 6:
                st.error("⚠️ La contraseña debe tener al menos 6 caracteres.")
            else:
                eps_asig = nueva_eps if nuevo_rol == "EPS" and nueva_eps != "N/A" else ""
                exito, msg = crear_usuario(spreadsheet, nuevo_usuario, nueva_password,
                                           nuevo_nombre, nuevo_rol, eps_asig)
                if exito:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def main():
    """Función principal."""
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
    elif pagina == "⚙️ Gestionar Usuarios":
        modulo_gestion_usuarios(spreadsheet)


if __name__ == "__main__":
    main()
