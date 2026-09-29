import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import {
  Activity, AlertTriangle, ArrowDownUp, Baby, Bell, Check, CheckCircle2,
  CloudUpload, HeartPulse, LoaderCircle, LogIn, LogOut, RefreshCw, Scale,
  Wifi, WifiOff, X, Moon, Sun
} from 'lucide-react'
import type { Session } from '@supabase/supabase-js'
import { enqueue, eventsForUser, readCatalog, saveCatalog, updateEvent } from './lib/offlineQueue'
import { saveOfflineAuth, saveOfflineConfig, clearOfflineAuth } from './lib/db'
import { authRedirectUrl, supabase, supabaseConfigured } from './lib/supabase'
import type { FieldAnimal, FieldEvent, FieldEventType, FieldProfile, FarmLot } from './types'

const FIELD_ROLES = new Set(['admin', 'gerencia', 'encargado', 'operario'])
const eventLabels: Record<FieldEventType, string> = {
  birth: 'Nacimiento', weight: 'Pesaje', death: 'Muerte', health: 'Sanidad', transfer: 'Traslado'
}

type Catalog = { animals: FieldAnimal[]; lots: FarmLot[] }
type HealthKind = 'Vacunación' | 'Tratamiento' | 'Desparasitación' | 'Revisión' | 'Otro'

async function fetchPagedRows<T>(buildQuery: () => any, pageSize = 500, maxRows = 10000): Promise<T[]> {
  const rows: T[] = []
  for (let start = 0; start < maxRows; start += pageSize) {
    const { data, error } = await buildQuery().range(start, Math.min(start + pageSize - 1, maxRows - 1))
    if (error) throw error
    const page = (data || []) as T[]
    rows.push(...page)
    if (page.length < pageSize) return rows
  }
  return rows
}

function errorText(error: unknown): string {
  if (error instanceof Error) return error.message
  return String(error || 'Error desconocido')
}

function cleanPayload(value: Record<string, unknown>): FieldEvent['payload'] {
  return Object.fromEntries(Object.entries(value).map(([key, item]) => [
    key,
    item === '' || item === undefined ? null : item as string | number | boolean | null
  ]))
}

export default function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<FieldProfile | null>(null)
  const [booting, setBooting] = useState(true)
  const [online, setOnline] = useState(navigator.onLine)
  const [catalog, setCatalog] = useState<Catalog>({ animals: [], lots: [] })
  const [catalogFresh, setCatalogFresh] = useState(false)
  const [queue, setQueue] = useState<FieldEvent[]>([])
  const [activeKind, setActiveKind] = useState<FieldEventType>('weight')
  const [syncing, setSyncing] = useState(false)
  const syncingRef = useRef(false)
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('myfinca-field-theme') === 'dark')
  const [notice, setNotice] = useState<{ kind: 'success' | 'error' | 'info'; text: string } | null>(null)
  const [pushEnabled, setPushEnabled] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const refreshQueue = useCallback(async (userId: string) => {
    setQueue(await eventsForUser(userId))
  }, [])

  const loadCatalog = useCallback(async (userId: string) => {
    if (!supabase) return
    const client = supabase
    const [farms, lotRows, animalRows] = await Promise.all([
      fetchPagedRows<{ id: string; nombre: string }>(() => client.from('predios').select('id,nombre').order('nombre')),
      fetchPagedRows<{ id: string; nombre: string; predio_id: string; activo: boolean }>(() => client.from('lotes').select('id,nombre,predio_id,activo').eq('activo', true).order('nombre')),
      fetchPagedRows<{ id: string; arete: string; nombre: string | null; lote_id: string; activo: boolean }>(() => client.from('animales').select('id,arete,nombre,lote_id,activo').eq('activo', true).order('arete'))
    ])
    const farmMap = new Map(farms.map(farm => [farm.id, farm.nombre]))
    const lots: FarmLot[] = lotRows.map((lot) => ({
      id: lot.id,
      nombre: lot.nombre,
      predio_id: lot.predio_id,
      predio_nombre: String(farmMap.get(lot.predio_id) || 'Predio')
    }))
    const lotMap = new Map(lots.map(lot => [lot.id, lot]))
    const animals: FieldAnimal[] = animalRows.flatMap((animal) => {
      const lot = lotMap.get(animal.lote_id)
      if (!lot) return []
      return [{
        id: animal.id,
        arete: animal.arete,
        nombre: animal.nombre || null,
        lote_id: lot.id,
        lote_nombre: lot.nombre,
        predio_id: lot.predio_id,
        predio_nombre: lot.predio_nombre,
        activo: animal.activo !== false
      }]
    })
    const value = { animals, lots }
    await saveCatalog(userId, value)
    setCatalog(value)
    setCatalogFresh(true)
  }, [])

  const syncQueue = useCallback(async () => {
    if (!session || !supabase || !navigator.onLine || syncingRef.current) return
    syncingRef.current = true
    setSyncing(true)
    try {
      const pending = (await eventsForUser(session.user.id)).filter(item => item.state === 'pending')
      for (const item of pending) {
        const { error } = await supabase.from('field_events').insert({
          client_event_id: item.client_event_id,
          created_by: session.user.id,
          event_type: item.event_type,
          payload: item.payload,
          client_created_at: item.client_created_at
        })
        // A lost acknowledgement may cause a retry after PostgreSQL already committed.
        // The client UUID primary key makes that retry safe and non-duplicating.
        if (error && error.code !== '23505') {
          const status = Number((error as { status?: number }).status || 0)
          const isTransient = !status || status >= 500 || status === 429
          if (isTransient) continue
          await updateEvent({ ...item, state: 'error', error_message: error.message })
          continue
        }
        await updateEvent({ ...item, state: 'synced', synced_at: new Date().toISOString(), error_message: undefined })
      }
      const remaining = (await eventsForUser(session.user.id)).filter(item => item.state === 'pending')
      await refreshQueue(session.user.id)
      if (remaining.length) {
        setNotice({ kind: 'info', text: `${remaining.length} registro(s) siguen pendientes; se reintentará al recuperar una conexión estable.` })
      } else if (pending.length) {
        setNotice({ kind: 'success', text: 'Sincronización terminada. Los registros aceptados ya están en la finca.' })
      }
    } catch (error) {
      setNotice({ kind: 'error', text: `No se pudo sincronizar: ${errorText(error)}` })
    } finally {
      syncingRef.current = false
      setSyncing(false)
    }
  }, [session, refreshQueue])

  useEffect(() => {
    document.documentElement.dataset.theme = darkMode ? 'dark' : 'light'
    localStorage.setItem('myfinca-field-theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  useEffect(() => {
    if (!session || !supabaseConfigured) return
    void Promise.all([
      saveOfflineConfig({
        supabaseUrl: import.meta.env.VITE_SUPABASE_URL,
        anonKey: import.meta.env.VITE_SUPABASE_ANON_KEY
      }),
      saveOfflineAuth({
        userId: session.user.id,
        accessToken: session.access_token,
        expiresAt: session.expires_at || 0
      })
    ]).catch(() => undefined)
  }, [session?.user.id, session?.access_token, session?.expires_at])

  useEffect(() => {
    if (!supabase) { setBooting(false); return }
    const client = supabase
    let alive = true
    const restore = async () => {
      try {
        const { data } = await client.auth.getSession()
        if (alive && data.session) setSession(data.session)
      } catch { /* Login still offers a reconnect path while offline. */ }
      if (alive) setBooting(false)
    }
    void restore()
    const { data: listener } = client.auth.onAuthStateChange((_event, nextSession) => {
      if (alive) setSession(nextSession)
    })
    return () => { alive = false; listener.subscription.unsubscribe() }
  }, [])

  useEffect(() => {
    const onOnline = () => { setOnline(true); void syncQueue() }
    const onOffline = () => setOnline(false)
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
    return () => { window.removeEventListener('online', onOnline); window.removeEventListener('offline', onOffline) }
  }, [syncQueue])

  useEffect(() => {
    if (!session || !supabase) { setProfile(null); return }
    const client = supabase
    let alive = true
    const restoreUser = async () => {
      const [{ data, error }, saved] = await Promise.all([
        client.from('profiles').select('id,email,nombre,rol,activo').eq('id', session.user.id).maybeSingle(),
        readCatalog<Catalog>(session.user.id)
      ])
      if (saved && alive) { setCatalog(saved); setCatalogFresh(false) }
      if (error) {
        if (!navigator.onLine && saved && alive) {
          const cached = localStorage.getItem(`myfinca-profile:${session.user.id}`)
          if (cached) setProfile(JSON.parse(cached) as FieldProfile)
        } else if (alive) setNotice({ kind: 'error', text: `No fue posible validar el perfil: ${error.message}` })
      } else if (alive && data) {
        const next = data as FieldProfile
        setProfile(next)
        localStorage.setItem(`myfinca-profile:${session.user.id}`, JSON.stringify(next))
      }
      if (alive) await refreshQueue(session.user.id)
      if (navigator.onLine) {
        try { await loadCatalog(session.user.id) }
        catch (error) {
          if (alive) setNotice({ kind: 'info', text: `Se conserva el catálogo guardado en este dispositivo. ${errorText(error)}` })
        }
      }
      if (alive && navigator.onLine) void syncQueue()
    }
    void restoreUser()
    return () => { alive = false }
  }, [session?.user.id, loadCatalog, refreshQueue, syncQueue])

  useEffect(() => {
    if (!session || !supabase || !('serviceWorker' in navigator)) return
    let active = true
    void navigator.serviceWorker.ready.then(async registration => {
      const subscription = await registration.pushManager.getSubscription()
      if (!active || !subscription) return
      setPushEnabled(true)
    }).catch(() => undefined)
    const onMessage = (event: MessageEvent) => {
      if (event.data?.type === 'MYFINCA_SYNC_READY') void syncQueue()
    }
    navigator.serviceWorker.addEventListener('message', onMessage)
    return () => { active = false; navigator.serviceWorker.removeEventListener('message', onMessage) }
  }, [session?.user.id, syncQueue])

  const sortedQueue = useMemo(() => [...queue].sort((a, b) => b.client_created_at.localeCompare(a.client_created_at)), [queue])
  const pendingCount = queue.filter(item => item.state !== 'synced').length

  async function signInGoogle() {
    if (!supabase) return
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: authRedirectUrl(), queryParams: { access_type: 'offline', prompt: 'select_account' } }
    })
    if (error) setNotice({ kind: 'error', text: error.message })
  }

  async function signOut() {
    if (!supabase) return
    if (session) await clearOfflineAuth(session.user.id)
    await supabase.auth.signOut()
    setSession(null)
    setProfile(null)
    setNotice({ kind: 'info', text: 'Sesión cerrada. La cola local permanece aislada por usuario en este dispositivo.' })
  }

  async function enablePush() {
    if (!supabase || !session || !('serviceWorker' in navigator) || !('PushManager' in window)) {
      setNotice({ kind: 'error', text: 'Este navegador no admite notificaciones push.' }); return
    }
    const publicKey = import.meta.env.VITE_WEB_PUSH_PUBLIC_KEY?.trim()
    if (!publicKey) {
      setNotice({ kind: 'info', text: 'La PWA puede registrar el dispositivo, pero falta configurar la clave pública VAPID y un emisor seguro del lado servidor.' }); return
    }
    const permission = await Notification.requestPermission()
    if (permission !== 'granted') { setNotice({ kind: 'error', text: 'No se concedió permiso para notificaciones.' }); return }
    try {
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToArrayBuffer(publicKey) })
      const { error } = await supabase.from('push_subscriptions').upsert({
        user_id: session.user.id,
        endpoint: subscription.endpoint,
        subscription: subscription.toJSON(),
        active: true
      }, { onConflict: 'endpoint' })
      if (error) throw error
      setPushEnabled(true)
      setNotice({ kind: 'success', text: 'Dispositivo registrado. La entrega requiere desplegar el emisor push seguro con su clave privada VAPID.' })
    } catch (error) { setNotice({ kind: 'error', text: `No se pudo registrar el dispositivo: ${errorText(error)}` }) }
  }

  async function submitEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!session || !profile || !FIELD_ROLES.has(profile.rol)) return
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    const raw = Object.fromEntries(form.entries())
    const payload = cleanPayload(raw)
    if (activeKind === 'birth' && (!payload.arete || !payload.lote_id)) {
      setNotice({ kind: 'error', text: 'Completa el arete y el lote antes de guardar.' }); return
    }
    if (activeKind === 'weight' && (!payload.animal_id || Number(payload.weight_kg) <= 0)) {
      setNotice({ kind: 'error', text: 'Selecciona el animal e ingresa un peso mayor que cero.' }); return
    }
    if (['death', 'health', 'transfer'].includes(activeKind) && !payload.animal_id) {
      setNotice({ kind: 'error', text: 'Selecciona el animal.' }); return
    }
    if (activeKind === 'transfer' && !payload.to_lote_id) {
      setNotice({ kind: 'error', text: 'Selecciona el lote de destino.' }); return
    }
    setSubmitting(true)
    try {
      const record: FieldEvent = {
        client_event_id: crypto.randomUUID(),
        user_id: session.user.id,
        event_type: activeKind,
        payload: { ...payload, event_date: String(payload.event_date || new Date().toISOString().slice(0, 10)) },
        client_created_at: new Date().toISOString(),
        state: 'pending'
      }
      await enqueue(record)
      await refreshQueue(session.user.id)
      formElement.reset()
      setNotice({ kind: 'success', text: online ? 'Guardado en este dispositivo; iniciando sincronización segura.' : 'Guardado en este dispositivo y pendiente de sincronizar cuando regrese la señal.' })
      void requestBackgroundSync()
      if (navigator.onLine) void syncQueue()
    } catch (error) {
      setNotice({ kind: 'error', text: `No se pudo guardar localmente: ${errorText(error)}` })
    } finally { setSubmitting(false) }
  }

  async function retryFailed() {
    if (!session) return
    const all = await eventsForUser(session.user.id)
    for (const item of all.filter(row => row.state === 'error')) {
      await updateEvent({ ...item, state: 'pending', error_message: undefined })
    }
    await refreshQueue(session.user.id)
    void syncQueue()
  }

  if (!supabaseConfigured || !supabase) return <SetupScreen />
  if (booting) return <div className="boot"><LoaderCircle className="spin" /> Cargando MyFinca Pro…</div>
  if (!session) return <LoginScreen online={online} onGoogle={signInGoogle} />
  if (!profile) return <div className="boot"><LoaderCircle className="spin" /> Validando permisos del usuario…</div>
  if (!profile.activo || !FIELD_ROLES.has(profile.rol)) return <AccessDenied profile={profile} onSignOut={signOut} />

  const currentAnimals = catalog.animals.filter(animal => animal.activo)
  const renderAnimalSelect = (required = true, excludeId = '') => (
    <label className="field"><span>Animal{required ? ' *' : ''}</span>
      <select name="animal_id" required={required} defaultValue="">
        <option value="" disabled>Selecciona arete o nombre</option>
        {currentAnimals.filter(item => item.id !== excludeId).map(item => (
          <option key={item.id} value={item.id}>{item.arete}{item.nombre ? ` · ${item.nombre}` : ''} — ${item.lote_nombre}</option>
        ))}
      </select>
    </label>
  )
  const renderDate = (label = 'Fecha del evento') => <label className="field"><span>{label}</span><input name="event_date" type="date" defaultValue={new Date().toISOString().slice(0, 10)} required /></label>

  return <main className="app-shell">
    <header className="topbar">
      <div className="brand"><img src={`${import.meta.env.BASE_URL}icons/icon-192.png`} alt="" /><div><strong>MyFinca Pro</strong><small>Operación de campo</small></div></div>
      <div className="top-actions">
        <span className={`connection ${online ? 'is-online' : 'is-offline'}`}><i />{online ? 'En línea' : 'Sin señal'}</span>
        <button className="icon-button theme-button" title={darkMode ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'} aria-label={darkMode ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'} onClick={() => setDarkMode(value => !value)}>{darkMode ? <Sun /> : <Moon />}</button>
        <button className="icon-button" title="Actualizar y sincronizar" onClick={() => void syncQueue()} disabled={!online || syncing}>
          {syncing ? <LoaderCircle className="spin" /> : <RefreshCw />}
        </button>
        <button className="icon-button" title="Cerrar sesión" onClick={() => void signOut()}><LogOut /></button>
      </div>
    </header>

    <section className="welcome-row">
      <div><p className="eyebrow">REGISTRO RÁPIDO</p><h1>Hola{profile.nombre ? `, ${profile.nombre.split(' ')[0]}` : ''}</h1><p className="muted">{profile.email} · {profile.rol}</p></div>
      <div className="sync-chip" aria-live="polite">
        {pendingCount > 0 ? <><CloudUpload /><b>{pendingCount}</b><span>pendiente{pendingCount === 1 ? '' : 's'}</span></> : <><CheckCircle2 /><span>Todo sincronizado</span></>}
      </div>
    </section>

    <section className="status-strip" aria-live="polite">
      {online ? <Wifi /> : <WifiOff />}
      <span>{online ? 'Conexión disponible.' : 'Sin internet: puedes seguir registrando; los eventos quedan separados por usuario en el almacenamiento de este navegador.'}</span>
      {!catalogFresh && <em>Catálogo guardado en este dispositivo</em>}
    </section>

    <nav className="event-tabs" aria-label="Tipo de registro">
      {([
        ['weight', Scale, 'Pesaje'], ['birth', Baby, 'Nacimiento'], ['health', HeartPulse, 'Sanidad'],
        ['transfer', ArrowDownUp, 'Traslado'], ['death', Activity, 'Muerte']
      ] as const).map(([kind, Icon, label]) => (
        <button key={kind} className={`event-tab ${activeKind === kind ? 'active' : ''}`} onClick={() => setActiveKind(kind)}>
          <Icon /><span>{label}</span>
        </button>
      ))}
    </nav>

    <section className="work-grid">
      <article className="panel form-panel">
        <div className="panel-heading"><div><p className="eyebrow">NUEVO EVENTO</p><h2>{eventLabels[activeKind]}</h2></div><span className="panel-mark"><Activity /></span></div>
        {!catalog.lots.length && activeKind === 'birth' && <div className="inline-alert"><AlertTriangle />No hay lotes disponibles en el catálogo de este usuario. Conéctate y solicita que un administrador te asigne un predio.</div>}
        {!currentAnimals.length && ['weight','death','health','transfer'].includes(activeKind) && <div className="inline-alert"><AlertTriangle />No hay animales activos en el catálogo. Conéctate y actualiza el catálogo antes de registrar.</div>}
        <form className="event-form" onSubmit={submitEvent}>
          {activeKind === 'birth' && <>
            <div className="form-row"><label className="field"><span>Arete / identificación *</span><input name="arete" required maxLength={50} autoComplete="off" placeholder="Ej. MF-0248" /></label><label className="field"><span>RFID / chip</span><input name="rfid" maxLength={100} autoComplete="off" placeholder="Escanea o escribe el código" /></label></div>
            <label className="field"><span>Nombre (opcional)</span><input name="nombre" maxLength={100} placeholder="Nombre del ternero" /></label>
            <label className="field"><span>Lote de nacimiento *</span><select name="lote_id" required defaultValue=""><option value="" disabled>Selecciona lote y predio</option>{catalog.lots.map(lot => <option key={lot.id} value={lot.id}>{lot.nombre} · {lot.predio_nombre}</option>)}</select></label>
            <div className="form-row"><label className="field"><span>Sexo</span><select name="sexo" defaultValue="No aplica"><option>No aplica</option><option>Hembra</option><option>Macho</option></select></label><label className="field"><span>Fecha de nacimiento</span><input name="event_date" type="date" defaultValue={new Date().toISOString().slice(0, 10)} required /></label></div>
            <div className="form-row"><label className="field"><span>Especie</span><select name="especie" defaultValue="Bovino"><option>Bovino</option><option>Bufalino</option><option>Ovino</option><option>Caprino</option><option>Porcino</option><option>Equino</option><option>Otro</option></select></label><label className="field"><span>Propósito</span><select name="proposito" defaultValue="Carne"><option>Carne</option><option>Leche</option><option>Doble propósito</option><option>Cría</option><option>Reproducción</option><option>Otro</option></select></label></div>
            <div className="form-row"><label className="field"><span>Madre</span><select name="mother_id" defaultValue=""><option value="">Sin registrar</option>{currentAnimals.filter(a => a.id !== '').map(a => <option key={a.id} value={a.id}>{a.arete}{a.nombre ? ` · ${a.nombre}` : ''}</option>)}</select></label><label className="field"><span>Padre</span><select name="father_id" defaultValue=""><option value="">Sin registrar</option>{currentAnimals.map(a => <option key={a.id} value={a.id}>{a.arete}{a.nombre ? ` · ${a.nombre}` : ''}</option>)}</select></label></div>
            <label className="field"><span>Observación</span><textarea name="notes" rows={2} maxLength={500} placeholder="Dificultad de parto, condición inicial…" /></label>
          </>}
          {activeKind === 'weight' && <>
            {renderAnimalSelect()}
            <div className="form-row"><label className="field"><span>Peso (kg) *</span><input name="weight_kg" type="number" inputMode="decimal" min="0.1" step="0.1" required placeholder="0,0" /></label>{renderDate('Fecha del pesaje')}</div>
            <label className="field"><span>Observación</span><textarea name="notes" rows={3} maxLength={300} placeholder="Condición, báscula, lote…" /></label>
          </>}
          {activeKind === 'death' && <>
            {renderAnimalSelect()}{renderDate('Fecha de defunción')}
            <label className="field"><span>Causa / observación</span><textarea name="notes" rows={4} maxLength={500} placeholder="Describe la causa si se conoce" /></label>
          </>}
          {activeKind === 'health' && <>
            {renderAnimalSelect()}{renderDate('Fecha del procedimiento')}
            <div className="form-row"><label className="field"><span>Tipo de atención</span><select name="type" defaultValue="Tratamiento">{(['Vacunación','Tratamiento','Desparasitación','Revisión','Otro'] as HealthKind[]).map(kind => <option key={kind}>{kind}</option>)}</select></label><label className="field"><span>Medicamento / vacuna</span><input name="medicine" maxLength={150} placeholder="Producto aplicado" /></label></div>
            <label className="field"><span>Veterinario / responsable</span><input name="veterinarian" maxLength={150} placeholder="Nombre" /></label>
            <div className="form-row"><label className="field"><span>Retiro carne (días)</span><input name="withdrawal_days_meat" type="number" inputMode="numeric" min="0" max="365" step="1" defaultValue="0" /></label><label className="field"><span>Retiro leche (días)</span><input name="withdrawal_days_milk" type="number" inputMode="numeric" min="0" max="365" step="1" defaultValue="0" /></label></div>
            <div className="form-row"><label className="field"><span>Próxima revisión</span><input name="next_visit" type="date" /></label><label className="field"><span>Nota</span><input name="notes" maxLength={500} placeholder="Dosis, lote de vacuna…" /></label></div>
          </>}
          {activeKind === 'transfer' && <>
            {renderAnimalSelect()}{renderDate('Fecha del traslado')}
            <label className="field"><span>Nuevo lote / predio *</span><select name="to_lote_id" required defaultValue=""><option value="" disabled>Selecciona destino</option>{catalog.lots.map(lot => <option key={lot.id} value={lot.id}>{lot.nombre} · {lot.predio_nombre}</option>)}</select></label>
            <label className="field"><span>Motivo / observación</span><textarea name="notes" rows={3} maxLength={500} placeholder="Rotación, manejo, traslado interno…" /></label>
          </>}
          <div className="form-actions"><button className="primary-button" type="submit" disabled={submitting || (activeKind === 'birth' && !catalog.lots.length)}>
            {submitting ? <LoaderCircle className="spin" /> : <Check />} Guardar {online ? 'en este dispositivo' : 'sin conexión'}
          </button><span className="form-hint">Se valida con Supabase al sincronizar.</span></div>
        </form>
      </article>

      <aside className="panel queue-panel">
        <div className="panel-heading"><div><p className="eyebrow">DISPOSITIVO</p><h2>Cola de sincronización</h2></div><span className="queue-count">{pendingCount}</span></div>
        <div className="queue-summary">
          <div><strong>{queue.filter(item => item.state === 'pending').length}</strong><span>Pendiente</span></div>
          <div><strong>{queue.filter(item => item.state === 'synced').length}</strong><span>Sincronizado</span></div>
          <div><strong>{queue.filter(item => item.state === 'error').length}</strong><span>Revisar</span></div>
        </div>
        <div className="queue-list">
          {sortedQueue.length === 0 ? <div className="empty-queue"><CheckCircle2 /><p>Sin registros en cola</p><small>Los nuevos eventos aparecen aquí hasta sincronizarse.</small></div> : sortedQueue.slice(0, 12).map(item => (
            <div className="queue-item" key={item.client_event_id}>
              <span className={`queue-icon ${item.state}`}>
                {item.state === 'synced' ? <CheckCircle2 /> : item.state === 'error' ? <AlertTriangle /> : <CloudUpload />}
              </span>
              <span className="queue-copy"><b>{eventLabels[item.event_type]}</b><small>{new Date(item.client_created_at).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })}</small>{item.error_message && <small className="queue-error">{item.error_message}</small>}</span>
              <span className={`queue-state ${item.state}`}>{item.state === 'synced' ? 'Listo' : item.state === 'error' ? 'Revisar' : 'Pendiente'}</span>
            </div>
          ))}
        </div>
        {queue.some(item => item.state === 'error') && <button className="secondary-button full-button" onClick={() => void retryFailed()}><RefreshCw /> Reintentar errores</button>}
        <div className="push-box"><div className="push-icon"><Bell /></div><div><b>Alertas al dispositivo</b><small>Notificaciones push cuando el emisor seguro esté configurado.</small></div><button className="push-button" onClick={() => void enablePush()} disabled={pushEnabled}>{pushEnabled ? <Check /> : <Bell />}</button></div>
        <p className="privacy-note">Los eventos quedan separados por usuario en este dispositivo. No guardes datos en teléfonos compartidos sin proteger la sesión.</p>
      </aside>
    </section>
    <footer className="app-footer"><img src={`${import.meta.env.BASE_URL}icons/icon-192.png`} alt="" />MyFinca Pro · Registro de campo <span>Los eventos offline son borradores locales hasta que Supabase los acepte.</span></footer>
    {notice && <div className={`notice ${notice.kind}`} role="status"><span>{notice.kind === 'error' ? <AlertTriangle /> : notice.kind === 'success' ? <CheckCircle2 /> : <Activity />}{notice.text}</span><button onClick={() => setNotice(null)} aria-label="Cerrar"><X /></button></div>}
  </main>
}

function LoginScreen({ online, onGoogle }: { online: boolean; onGoogle: () => void }) {
  return <main className="login-shell">
    <section className="login-card">
      <img className="login-logo" src={`${import.meta.env.BASE_URL}icons/myfinca-logo-original.jpeg`} alt="Logo MyFinca Pro" />
      <p className="eyebrow">MYFINCA PRO · CAMPO</p><h1>Operación de finca,<br /><em>incluso sin señal.</em></h1>
      <p className="login-copy">Inicia sesión con tu cuenta autorizada. Después de cargar tu catálogo, podrás registrar eventos y sincronizarlos cuando vuelva la conexión.</p>
      <div className={`login-status ${online ? 'is-online' : 'is-offline'}`}>{online ? <Wifi /> : <WifiOff />}{online ? 'Conectado a internet' : 'Sin conexión: inicia sesión primero cuando estés en línea'}</div>
      <button className="primary-button login-button" onClick={onGoogle} disabled={!online}><LogIn /> Continuar con Google</button>
      <small className="login-footnote">El acceso y los permisos los administra MyFinca Pro en Supabase.</small>
    </section>
  </main>
}

function SetupScreen() {
  return <main className="login-shell"><section className="login-card setup-card"><img className="login-logo" src={`${import.meta.env.BASE_URL}icons/myfinca-logo-original.jpeg`} alt="Logo MyFinca Pro" /><p className="eyebrow">CONFIGURACIÓN NECESARIA</p><h1>Conecta tu proyecto</h1><p className="login-copy">Copia <code>.env.example</code> como <code>.env.local</code> y configura la URL de Supabase y la clave anon/publishable. Nunca uses la clave <code>service_role</code> en esta PWA.</p></section></main>
}

function AccessDenied({ profile, onSignOut }: { profile: FieldProfile; onSignOut: () => void }) {
  return <main className="login-shell"><section className="login-card setup-card"><img className="login-logo" src={`${import.meta.env.BASE_URL}icons/myfinca-logo-original.jpeg`} alt="Logo MyFinca Pro" /><p className="eyebrow">ACCESO CONTROLADO</p><h1>Perfil no autorizado</h1><p className="login-copy">La cuenta <b>{profile.email}</b> está inactiva o su rol ({profile.rol}) no permite registrar eventos de campo. Solicita al administrador que revise el rol y la asignación de predios.</p><button className="secondary-button full-button" onClick={onSignOut}><LogOut /> Cerrar sesión</button></section></main>
}

function urlBase64ToArrayBuffer(value: string): ArrayBuffer {
  const padding = '='.repeat((4 - value.length % 4) % 4)
  const base64 = (value + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = window.atob(base64)
  const bytes = Uint8Array.from([...raw].map(char => char.charCodeAt(0)))
  return bytes.buffer as ArrayBuffer
}

async function requestBackgroundSync(): Promise<void> {
  if (!('serviceWorker' in navigator)) return
  try {
    const registration = await navigator.serviceWorker.ready as ServiceWorkerRegistration & { sync?: { register: (tag: string) => Promise<void> } }
    await registration.sync?.register('myfinca-field-sync')
  } catch {
    // No todos los navegadores ejecutan Background Sync; la app reintenta al abrirse o al recuperar red.
  }
}
