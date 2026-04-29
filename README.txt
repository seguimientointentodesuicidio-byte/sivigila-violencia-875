SIVIGILA - Vigilancia Violencia de Género e Intrafamiliar | Valle del Cauca

Evento 875 - Violencia (Física, Psicológica, Negligencia y Abandono)
Secretaría Departamental de Salud | Gobernación del Valle del Cauca

Sistema web para la vigilancia epidemiológica y seguimiento de casos de
violencia de género e intrafamiliar (Evento SIVIGILA 875), desarrollado con
Streamlit y Google Sheets como backend. Este aplicativo NO incluye violencia
sexual: solo registra modalidades física, psicológica y negligencia/abandono.

------------------------------------------------------------------------
ARQUITECTURA
------------------------------------------------------------------------

- Frontend + Backend: Python / Streamlit
- Base de datos: Google Sheets (vía gspread)
- Hosting: Streamlit Community Cloud (gratuito)
- Autenticación: Hash SHA-256 + session_state

------------------------------------------------------------------------
MÓDULOS DEL SISTEMA
------------------------------------------------------------------------

1. Formulario de Digitación: registro de nuevos casos con validación y
   búsqueda de duplicados.
2. Tablero de Control: dashboard con KPIs, gráficas (Plotly) y tablas de
   alertas (reincidentes, menores de 14 años, gestantes, sin seguimiento,
   casos graves sin reporte a autoridades, abandonos).
3. Edición de Casos: búsqueda y actualización de registros existentes.
4. Exportación: descarga en CSV y Excel (con hojas separadas por modalidad
   de violencia).
5. Gestión de Usuarios: crear y administrar cuentas (solo rol SECRETARÍA).

------------------------------------------------------------------------
DESPLIEGUE PASO A PASO
------------------------------------------------------------------------

PASO 1. Reutilizar las APIs de Google Cloud del proyecto 356
   - Las APIs (Sheets API y Drive API) ya están habilitadas en el proyecto
     de Google Cloud usado para SIVIGILA 356.
   - Se reutiliza la misma cuenta de servicio:
     sivigila-app@seguimiento-intento-suicido.iam.gserviceaccount.com
   - No se requiere crear nueva cuenta de servicio ni nuevas credenciales
     JSON.

PASO 2. Crear la nueva hoja de Google Sheets
   1. Iniciar sesión en https://sheets.google.com con el correo
      seguimientointentodesuicidio@gmail.com
   2. Crear una nueva hoja con nombre: SIVIGILA_875_VIOLENCIA_VALLE
   3. Crear la pestaña DATOS:
      - Renombrar la primera pestaña a DATOS
      - En la fila 1, escribir los encabezados (uno por celda, A1 en
        adelante) en el orden definido por COLUMNAS_DATOS en app.py
        (70 columnas en total).
   4. Crear la pestaña USUARIOS:
      - Agregar pestaña USUARIOS
      - En la fila 1: usuario | password_hash | nombre_completo | rol |
        eps_asignada
   5. Crear el primer usuario administrador en la fila 2 de USUARIOS:
      - usuario: admin
      - password_hash:
        8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918
        (hash SHA-256 de "admin")
      - nombre_completo: Administrador SDSS - Violencia 875
      - rol: SECRETARIA
      - eps_asignada: (vacío)
   6. Compartir la hoja con la cuenta de servicio:
      - Clic en Compartir
      - Pegar:
        sivigila-app@seguimiento-intento-suicido.iam.gserviceaccount.com
      - Permisos de Editor
      - Desmarcar "Notificar"
   7. Copiar el ID de la hoja desde la URL.

PASO 3. Subir el código a GitHub
   1. Crear nuevo repositorio: sivigila-violencia-875
   2. Subir los archivos:
      - app.py
      - requirements.txt
      - Imagen1.png (reutilizar el logo del proyecto 356)
      - README.txt (este archivo)
   3. NO subir credenciales JSON ni secrets.toml.

PASO 4. Desplegar en Streamlit Community Cloud
   1. Ir a https://share.streamlit.io
   2. Clic en New app
   3. Seleccionar:
      - Repository: su-usuario/sivigila-violencia-875
      - Branch: main
      - Main file path: app.py
   4. En Advanced settings > Secrets pegar:

      spreadsheet_id = "ID_DE_LA_NUEVA_HOJA_DE_VIOLENCIA"

      [gcp_service_account]
      type = "service_account"
      project_id = "seguimiento-intento-suicido"
      private_key_id = "..."
      private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
      client_email = "sivigila-app@seguimiento-intento-suicido.iam.gserviceaccount.com"
      client_id = "..."
      auth_uri = "https://accounts.google.com/o/oauth2/auth"
      token_uri = "https://oauth2.googleapis.com/token"
      auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
      client_x509_cert_url = "..."

      Los valores de [gcp_service_account] son los MISMOS del proyecto
      356; solo cambia el spreadsheet_id.

   5. Clic en Save y luego en Deploy.
   6. La URL será algo como:
      https://sivigila-violencia-875.streamlit.app

PASO 5. Primer Ingreso
   1. Acceder a la URL del aplicativo.
   2. Ingresar con: admin / admin
   3. Ir a Gestionar Usuarios y crear las 28 cuentas de digitadores EPS
      según las contraseñas listadas en
      INSTRUCTIVO_SIVIGILA_875_COMPLETO.docx.

------------------------------------------------------------------------
GENERACIÓN DE HASH SHA-256 PARA CONTRASEÑAS MANUALES
------------------------------------------------------------------------

Si necesita crear usuarios directamente en Google Sheets:

   import hashlib
   password = "su_contraseña_aqui"
   print(hashlib.sha256(password.encode()).hexdigest())

------------------------------------------------------------------------
SEGURIDAD
------------------------------------------------------------------------

- Las contraseñas se almacenan como hash SHA-256.
- Las credenciales de Google Cloud están en st.secrets.
- Cada EPS solo ve y edita sus propios registros.
- Solo el rol SECRETARÍA ve todos los datos y gestiona usuarios.

------------------------------------------------------------------------
ESTRUCTURA DE LA HOJA DE GOOGLE SHEETS
------------------------------------------------------------------------

Pestaña DATOS: 70 columnas con todos los registros (sin separar por
modalidad; modalidad es una columna más).

Pestaña USUARIOS: 5 columnas
   usuario | password_hash | nombre_completo | rol | eps_asignada

------------------------------------------------------------------------
DIFERENCIAS CON SIVIGILA 356 (CONDUCTA SUICIDA)
------------------------------------------------------------------------

- Variables específicas: modalidad de violencia (Física, Psicológica,
  Negligencia), datos del agresor (sexo, edad, parentesco, convivencia,
  relación no familiar), datos del hecho (fecha, hora, municipio,
  mecanismo, escenario, ámbito), atenciones por trabajo social y salud
  ocupacional, remisión a protección, reporte a autoridades.
- Variables EXCLUIDAS: profilaxis VIH, profilaxis Hep B, otras profilaxis,
  anticoncepción de emergencia, orientación IVE, recolección de evidencia
  médico legal, mecanismos sexuales (no aplica al alcance del aplicativo).
- Identidad visual: misma paleta azul/blanco institucional.
- Stack y arquitectura: idénticos al 356.

------------------------------------------------------------------------
SOLUCIÓN DE PROBLEMAS
------------------------------------------------------------------------

- "Error al conectar con Google Sheets": verificar APIs habilitadas y
  permisos de la cuenta de servicio sobre la hoja.
- Login no funciona: verificar pestaña USUARIOS y encabezados.
- Datos no se guardan: verificar permisos de Editor de la cuenta de
  servicio.
- App se reinicia: normal en Streamlit Cloud gratuito; los datos persisten
  en Google Sheets.

------------------------------------------------------------------------
CONTACTO
------------------------------------------------------------------------

Secretaría Departamental de Salud
Gobernación del Valle del Cauca
Referente ASIS - Vigilancia Epidemiológica

Sistema desarrollado para uso institucional exclusivo
Vigilancia de Evento 875 SIVIGILA - Violencia de Género e Intrafamiliar
(sin componente sexual)
