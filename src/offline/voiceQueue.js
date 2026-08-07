import { openDB } from 'idb'

const DB = 'nagrikawaaz-voice'
const STORE = 'pending'
const V = 1

async function getDb() {
  return openDB(DB, V, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: 'id' })
      }
    },
  })
}

export async function listPendingJobs() {
  const db = await getDb()
  return db.getAll(STORE)
}

/**
 * @param {{ language: string, file: File }} payload
 * @returns {Promise<string>} job id
 */
export async function enqueueVoiceJob({ language, file }) {
  const db = await getDb()
  const id = crypto.randomUUID()
  const buffer = await file.arrayBuffer()
  await db.put(STORE, {
    id,
    createdAt: Date.now(),
    language,
    name: file.name,
    mime: file.type || 'application/octet-stream',
    buffer,
  })
  return id
}

export async function removeJob(id) {
  const db = await getDb()
  await db.delete(STORE, id)
}

export function bufferToFile(job) {
  return new File([job.buffer], job.name || 'recording.webm', { type: job.mime })
}
