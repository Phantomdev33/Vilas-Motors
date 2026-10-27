import test from 'node:test';
import assert from 'node:assert/strict';
import {api, initCSRF} from '../../src/api.js';

test('la inicialización simultánea comparte una petición sin caché', async () => {
  let calls = 0;
  globalThis.fetch = async (_url, options) => {
    calls++;
    assert.equal(options.cache, 'no-store');
    return {ok: true, json: async () => ({csrfToken: 'initial-token'})};
  };
  await Promise.all([initCSRF(), initCSRF()]);
  assert.equal(calls, 1);
});

test('las escrituras usan la cookie vigente aunque el token en memoria sea anterior', async () => {
  globalThis.document = {cookie: 'other=value; csrftoken=current-cookie'};
  globalThis.fetch = async (_url, options) => {
    assert.equal(options.headers['X-CSRFToken'], 'current-cookie');
    return {status: 200, ok: true, json: async () => ({})};
  };
  await api('auth/login/', {method: 'POST', body: {}});
});
