# 📋 Instrucciones de Migración - MyFinca Pro v2.0

## ⚠️ IMPORTANTE: Ejecutar en Supabase SQL Editor

Las migraciones **NO se pueden ejecutar desde Python** porque requieren funciones DDL (CREATE TABLE, ALTER TABLE, CREATE POLICY, etc.) que no están disponibles vía PostgREST.

### Pasos:

1. **Abrir el Dashboard del proyecto Supabase que configuraste** → https://supabase.com/dashboard
2. **Ir a SQL Editor** (icono de base de datos en sidebar izquierdo)
3. **Crear nueva consulta** (New Query)
4. **Copiar y pegar** el contenido de cada archivo de migración en orden
5. **Ejecutar** (Run / Ctrl+Enter)

---

## 📁 Orden de Ejecución

### 1. `supabase/migrations/001_initial_schema.sql`
- Esquema base: profiles, predios, lotes, animales, pesajes
- RLS policies, triggers, functions de seguridad

### 2. `supabase/migrations/002_admin_crisamo.sql`
- Configura `crisamo1203@gmail.com` como admin automáticamente

### 3. `supabase/migrations/003_operaciones_myfinca.sql`
- **Tablas operativas**: ventas, produccion, movimientos, salud, gastos
- **Campos extendidos animales**: 24 campos (tipo, clase, proposito, fecha_nacimiento, peso_kg, sexo, raza, color, proveedor, especie, origen, valor_compra, valor_venta, estado, propietario, marca, comentarios)
- **RLS policies** para todas las tablas nuevas

### 4. `supabase/migrations/004_contact_feedback.sql` **(NUEVO)**
- **Campos de contacto en profiles**: direccion, ciudad, notas_contacto
- **Tabla feedback**: problemas, sugerencias, mejoras con workflow (nuevo → en_revision → resuelto → cerrado)
- **RLS policies** para feedback (usuarios ven lo suyo, admins todo)
- No ejecutes el duplicado legacy `supabase/migrations/004_feedback_system.sql`.

### 5. `supabase/migrations/005_ventas_detalle.sql` **(NUEVO)**
- Añade cantidad, valor unitario y total a ventas (idempotente).
- Ejecutar antes de registrar ventas desde el modal del dashboard.

---

## 🔐 Configuración Google OAuth

1. **Supabase Dashboard** → Authentication → Providers → **Google** → Enable; copia desde esa pantalla la URL Callback del proyecto que configuraste (normalmente `https://<project-ref>.supabase.co/auth/v1/callback`).
2. En **Google Cloud Console** crea un OAuth Client ID tipo Web y agrega esa URL Callback exacta en **Authorized redirect URIs**. Copia el Client ID y Client Secret en el proveedor Google de Supabase.
3. En Google Cloud agrega `http://localhost:8501` como **Authorized JavaScript origin** para desarrollo local. Si abres Streamlit en `127.0.0.1` o usas otro puerto, usa ese origen también.
4. En **Supabase → Authentication → URL Configuration**, fija Site URL a `http://localhost:8501/` y agrega `http://localhost:8501/**` a Redirect URLs. El `app_url` de `.streamlit/secrets.toml` debe coincidir con el host y puerto que usas.

---

## 👤 Admin User Creation

Una vez ejecutadas las migraciones:
1. Inicia sesión con Google usando `crisamo1203@gmail.com` → se crea perfil y la migración 002 le asigna el rol admin.
2. Si tu correo administrador es diferente, inicia sesión con él una vez y luego asígnalo en SQL Editor:

   ```sql
   update public.profiles set rol = 'admin' where lower(email) = lower('tu.correo@gmail.com');
   ```

3. Para crear otros usuarios por email/contraseña, ve a **Usuarios** → **➕ Crear Usuario** y define una contraseña para esa cuenta. Las cuentas que ingresan con Google no reciben una contraseña local automáticamente; deben seguir usando Google salvo que un administrador les cree una cuenta/clave aparte.

---

## 📱 Android App (Capacitor)

```bash
# 1. Desde la carpeta del proyecto, instala dependencias y ejecuta el script
./build_android.sh

# 2. Abrir Android Studio (desde la carpeta del proyecto)
npx cap open android

# 3. Build APK
# En Android Studio: Build > Build Bundle(s) / APK(s) > Build APK(s)

# 4. APK generado en:
# android/app/build/outputs/apk/debug/app-debug.apk
```

---

## 🛡️ Protección de Código

| Capa | Protección |
|------|------------|
| **Backend (Supabase)** | ✅ RLS en PostgreSQL, solo anon key expuesta |
| **API** | ✅ service_role NUNCA en frontend |
| **Frontend (PWA/APK)** | ⚠️ JS siempre inspeccionable en navegador |
| **Ofuscación** | `npm install -g javascript-obfuscator` + build |
| **Datos sensibles** | ✅ En BD con RLS, no en localStorage |

---

## ✅ Checklist Post-Migración

- [ ] Ejecutar 5 migraciones en orden
- [ ] Configurar Google OAuth en Supabase + Google Cloud
- [ ] Login con `crisamo1203@gmail.com` vía Google
- [ ] Verificar que aparece módulo **Usuarios** y **Feedback**
- [ ] Crear usuario de prueba con email/password
- [ ] Probar login con email/password (sin Google)
- [ ] Verificar sidebar, filtros globales, alertas
- [ ] Build Android APK
