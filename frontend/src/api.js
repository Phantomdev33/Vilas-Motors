let csrfToken = '';
export async function initCSRF() {
  const response = await fetch('/api/auth/csrf/', { credentials: 'include' });
  const data = await response.json(); csrfToken = data.csrfToken;
}
function errorText(data) {
  if (typeof data === 'string') return data;
  if (Array.isArray(data)) return data.map(errorText).join(' ');
  return Object.entries(data).map(([key, value]) => `${key === 'detail' || key === 'non_field_errors' ? '' : key + ': '}${errorText(value)}`).join(' ');
}
export async function api(path, {method = 'GET', body, ...options} = {}) {
  const headers = {};
  if (method !== 'GET') headers['X-CSRFToken'] = csrfToken;
  if (body && !(body instanceof FormData)) headers['Content-Type'] = 'application/json';
  const response = await fetch('/api/' + path, {method, credentials: 'include', headers, body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined, ...options});
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({detail: 'No se pudo conectar con el servidor.'}));
  if (!response.ok) { const error = new Error(errorText(data)); error.status = response.status; throw error; }
  return data;
}
export async function download(path, filename) {
  const response = await fetch('/api/'+path, {credentials: 'include'});
  if (!response.ok) throw new Error('No se pudo generar el archivo. Revisa tu sesión.');
  const url = URL.createObjectURL(await response.blob());
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function database() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('vilas-offline', 1);
    req.onupgradeneeded = () => req.result.createObjectStore('readings', {keyPath: 'client_id'});
    req.onsuccess = () => resolve(req.result); req.onerror = () => reject(req.error);
  });
}
export async function pendingReadings(userId) {
  const db = await database();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction('readings', 'readonly'); const req = transaction.objectStore('readings').getAll();
    req.onsuccess = () => resolve(req.result.filter(item => item.userId === userId)); req.onerror = () => reject(req.error);
    transaction.oncomplete = () => db.close();
  });
}
export async function queueReading(data, userId) {
  const db = await database();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction('readings', 'readwrite'); transaction.objectStore('readings').put({...data, userId});
    transaction.oncomplete = () => {db.close(); resolve();}; transaction.onerror = () => reject(transaction.error);
  });
}
export function readingForm(data) {
  const form = new FormData();
  Object.entries(data).forEach(([key,value]) => { if (value != null && key !== 'userId') form.append(key, value); });
  return form;
}
export async function syncReadings(userId) {
  const items = (await pendingReadings(userId)).sort((a,b) => a.recorded_at.localeCompare(b.recorded_at) || Number(a.value)-Number(b.value));
  for (const item of items) {
    await api('readings/', {method:'POST',body:readingForm(item)});
    const db = await database();
    await new Promise((resolve,reject) => {
      const transaction = db.transaction('readings','readwrite'); transaction.objectStore('readings').delete(item.client_id);
      transaction.oncomplete = () => {db.close();resolve();}; transaction.onerror = () => reject(transaction.error);
    });
  }
  return items.length;
}
