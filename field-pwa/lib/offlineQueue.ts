import { database } from './db'
import type { FieldEvent } from '../types'

export async function enqueue(event: FieldEvent): Promise<void> {
  await (await database()).put('events', event)
}

export async function eventsForUser(userId: string): Promise<FieldEvent[]> {
  return (await database()).getAllFromIndex('events', 'user_id', userId)
}

export async function saveCatalog<T>(userId: string, catalog: T): Promise<void> {
  await (await database()).put('catalogs', { user_id: userId, catalog, saved_at: new Date().toISOString() })
}

export async function readCatalog<T>(userId: string): Promise<T | null> {
  const row = await (await database()).get('catalogs', userId)
  return row?.catalog ?? null
}

export async function updateEvent(event: FieldEvent): Promise<void> {
  await (await database()).put('events', event)
}

export async function deleteEventsForUser(userId: string): Promise<void> {
  const db = await database()
  const tx = db.transaction(['events', 'catalogs'], 'readwrite')
  const keys = await tx.objectStore('events').index('user_id').getAllKeys(userId)
  await Promise.all(keys.map(key => tx.objectStore('events').delete(key)))
  await tx.objectStore('catalogs').delete(userId)
  await tx.done
}
