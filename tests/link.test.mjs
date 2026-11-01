import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  validateAuthorizeUrl,
  isCallback,
  REDIRECT_URI,
  CLIENT_ID,
  B2C_HOST,
} from '../tools/link/auth.mjs';
const url = () => {
  const u = new URL(
    `https://${B2C_HOST}/gdhvb2cflameconnect.onmicrosoft.com/B2C_1A_FirePhoneSignUpOrSignInWithPhoneOrEmail/oauth2/v2.0/authorize`,
  );
  u.search = new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: 'code',
    code_challenge_method: 'S256',
    code_challenge: 'example',
    state: 'example',
    nonce: 'example',
  }).toString();
  return u;
};
test('Desktop helper accepts only the known provider and native redirect', () => {
  assert.equal(validateAuthorizeUrl(url().toString()), url().toString());
  for (const field of [
    'client_id',
    'redirect_uri',
    'response_type',
    'code_challenge_method',
    'state',
    'nonce',
    'code_challenge',
  ]) {
    const u = url();
    u.searchParams.set(field, '');
    assert.throws(() => validateAuthorizeUrl(u.toString()));
  }
  for (const change of [
    (u) => (u.hostname = 'evil.test'),
    (u) => (u.protocol = 'http:'),
    (u) => (u.username = 'evil'),
    (u) => (u.port = '123'),
    (u) => (u.hash = 'bad'),
    (u) => (u.pathname = '/bad'),
    (u) => u.searchParams.append('state', 'other'),
  ]) {
    const u = url();
    change(u);
    assert.throws(() => validateAuthorizeUrl(u.toString()));
  }
  assert.ok(isCallback(REDIRECT_URI + '/?code=one&state=two'));
  assert.ok(!isCallback('https://evil.test'));
  assert.ok(!isCallback(REDIRECT_URI + '/bad'));
  assert.ok(!isCallback('invalid'));
});
