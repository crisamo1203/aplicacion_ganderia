import { openDB, type IDBPDatabase } from 'idb'
import type { FieldEvent } from '../types'

const DB_NAME = 'myfinca-field-v1'
const DB_VERSION = 2
let dbPromise: Promise<IDBPDatabase> | undefined

export interface OfflineAuth {
  userId: string
  accessToken: string
  expiresAt: number
}
export interface OfflineConfig { supabaseUrl: string; anonKey: string }

export function database(): Promise<IDBPDatabase> {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains('events')) {
          const store = db.createObjectStore('events', { keyPath: 'client_event_id' })
          store.createIndex('user_id', 'user_id')
          store.createIndex('state', 'state')
          store.createIndex('user_state', ['user_id', 'state'])
        }
        if (!db.objectStoreNames.contains('catalogs')) db.createObjectStore('catalogs', { keyPath: 'user_id' })
        if (!db.objectStoreNames.contains('auth')) db.createObjectStore('auth')
        if (!db.objectStoreNames.contains('config')) db.createObjectStore('config')
      }
    })
  }
  return dbPromise
}

export async function saveOfflineConfig(config: OfflineConfig): Promise<void> {
  const db = await database()
  await db.put('config', config, 'supabase')
}
export async function readOfflineConfig(): Promise<OfflineConfig | undefined> {
  return (await database()).get('config', 'supabase')
}
export async function saveOfflineAuth(auth: OfflineAuth): Promise<void> {
  await (await database()).put('auth', auth, auth.userId)
}
export async function readOfflineAuth(userId: string): Promise<OfflineAuth | undefined> {
  return (await database()).get('auth', userId)
}
export async function clearOfflineAuth(userId: string): Promise<void> {
  await (await database()).delete('auth', userId)
}

export async function setEvent(event: FieldEvent): Promise<void> {
  await (await database()).put('events', event)
}
