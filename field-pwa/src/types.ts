export type FieldEventType = 'birth' | 'weight' | 'death' | 'health' | 'transfer'
export type QueueState = 'pending' | 'synced' | 'error'

export interface FieldEvent {
  client_event_id: string
  user_id: string
  event_type: FieldEventType
  payload: Record<string, string | number | boolean | null>
  client_created_at: string
  state: QueueState
  synced_at?: string
  error_message?: string
}

export interface FarmLot {
  id: string
  nombre: string
  predio_id: string
  predio_nombre: string
}

export interface FieldAnimal {
  id: string
  arete: string
  nombre: string | null
  lote_id: string
  lote_nombre: string
  predio_id: string
  predio_nombre: string
  activo: boolean
}

export interface FieldProfile {
  id: string
  email: string
  nombre?: string | null
  rol: string
  activo: boolean
}
