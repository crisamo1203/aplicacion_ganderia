/// <reference lib="webworker" />
import { clientsClaim } from 'workbox-core'
import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from 'workbox-precaching'
import { NavigationRoute, registerRoute } from 'workbox-routing'
import { database, type OfflineAuth, type OfflineConfig } from './lib/db'

declare let self: ServiceWorkerGlobalScope & { __WB_MANIFEST: Array<{ url: string; revision?: string | null }> }

type QueuedEvent = {
  client_event_id: string
  user_id: string
  event_type: string
  payload: Record<string, unknown>
  client_created_at: string
  state: 'pending' | 'synced' | 'error'
  synced_at?: string
  error_message?: string
}

cleanupOutdatedCaches()
precacheAndRoute(self.__WB_MANIFEST)
registerRoute(new NavigationRoute(createHandlerBoundToURL('index.html')))
self.skipWaiting()
clientsClaim()

self.addEventListener('push', (event: PushEvent) => {
  const data = (() => {
    try { return event.data?.json() ?? {} } catch { return { body: event.data?.text() ?? '' } }
  })()
  const title = typeof data.title === 'string' ? data.title : 'MyFinca Pro'
  const options: NotificationOptions = {
    body: typeof data.body === 'string' ? data.body : 'Tienes una alerta de la finca.',
    icon: './icons/icon-192.png',
    badge: './icons/icon-192.png',
    tag: typeof data.tag === 'string' ? data.tag : 'myfinca-alert',
    data: { url: typeof data.url === 'string' ? data.url : './' }
  }
  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', (event: NotificationEvent) => {
  event.notification.close()
  const destination = new URL(String(event.notification.data?.url || './'), self.registration.scope).href
  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
    const existing = windows.find(client => client.url.startsWith(self.registration.scope))
    if (existing && 'focus' in existing) {
      await existing.focus()
      if ('navigate' in existing) await existing.navigate(destination)
      return
    }
    await self.clients.openWindow(destination)
  })())
})

async function notifyClients(): Promise<void> {
  const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
  for (const client of windows) client.postMessage({ type: 'MYFINCA_SYNC_READY' })
}

async function syncPendingEvents(): Promise<void> {
  const db = await database()
  const events = await db.getAllFromIndex('events', 'state', 'pending') as QueuedEvent[]
  const pendingUsers = [...new Set(events.map(row => row.user_id))]
  const config = await db.get('config', 'supabase') as OfflineConfig | undefined
  if (!events.length || !config?.supabaseUrl || !config.anonKey) return

  for (const userId of pendingUsers) {
    const auth = await db.get('auth', userId) as OfflineAuth | undefined
    if (!auth || auth.expiresAt * 1000 <= Date.now() + 15_000) continue
    const userEvents = events.filter(row => row.user_id === userId)
    for (const row of userEvents) {
      let response: Response
      try {
        response = await fetch(`${config.supabaseUrl.replace(/\/$/, '')}/rest/v1/field_events`, {
          method: 'POST',
          headers: {
            apikey: config.anonKey,
            Authorization: `Bearer ${auth.accessToken}`,
            'Content-Type': 'application/json',
            Prefer: 'return=minimal'
          },
          body: JSON.stringify({
            client_event_id: row.client_event_id,
            created_by: userId,
            event_type: row.event_type,
            payload: row.payload,
            client_created_at: row.client_created_at
          })
        })
      } catch {
        throw new Error('La red no está disponible; se reintentará la sincronización.')
      }

      if (response.ok) {
        await db.put('events', { ...row, state: 'synced', synced_at: new Date().toISOString(), error_message: undefined })
      } else {
        let details: { code?: string; message?: string } = {}
        try { details = await response.json() } catch { /* Keep generic error. */ }
        if (response.status === 409 || details.code === '23505') {
          await db.put('events', { ...row, state: 'synced', synced_at: new Date().toISOString(), error_message: undefined })
        } else if (response.status >= 500 || response.status === 429) {
          throw new Error('Supabase no está disponible; se reintentará la sincronización.')
        } else {
          await db.put('events', { ...row, state: 'error', error_message: details.message || `No autorizado o datos rechazados (${response.status}).` })
        }
      }
    }
  }
  await notifyClients()
}

self.addEventListener('sync', ((event: ExtendableEvent & { tag?: string }) => {
  if (event.tag === 'myfinca-field-sync') event.waitUntil(syncPendingEvents())
}) as EventListener)

self.addEventListener('online', (() => { void syncPendingEvents().catch(() => undefined) }) as EventListener)

self.addEventListener('message', (event: ExtendableMessageEvent) => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting()
  if (event.data?.type === 'SYNC_NOW') event.waitUntil(syncPendingEvents())
})
