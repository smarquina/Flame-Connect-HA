import {test} from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {spawnSync} from 'node:child_process';
import {CDP, stopBrowserProcess} from '../tools/link/browser.mjs';
import {b2cErrorSummary,classifyFormResponse,isConfirmationUrl} from '../tools/link/diagnostics.mjs';

test('desktop CLI rejects an unofficial URL with an English message before launching a browser', () => {
 const result=spawnSync(process.execPath,['tools/link/link.mjs'],{
  input:'https://example.invalid/\n',encoding:'utf8',timeout:10000,
  env:{...process.env,FLAME_CHROME_PATH:'/nonexistent/browser'},
 });
 assert.equal(result.error,undefined);
 assert.equal(result.status,1);
 assert.match(result.stdout,/Unofficial Home Assistant account linking/);
 assert.match(result.stdout,/Enter your password only in the official Microsoft window/);
 assert.match(result.stderr,/The URL is not the official Flame Connect login/);
 assert.doesNotMatch(result.stdout,/msal.*code=/);
});

class FakeWebSocket extends EventTarget {
 static OPEN=1;
 readyState=1;
 constructor(url){super();queueMicrotask(()=>this.dispatchEvent(new Event('open')));FakeWebSocket.last=this;}
 send(raw){const message=JSON.parse(raw);queueMicrotask(()=>{const event=new Event('message');event.data=JSON.stringify(message.method==='reject'?{id:message.id,error:{code:-1}}:{id:message.id,result:{value:'ok'}});this.dispatchEvent(event);});}
 close(){this.readyState=3;this.dispatchEvent(new Event('close'));}
}

test('CDP correlates replies, handles provider errors and does not connect off loopback',async()=>{
 const original=globalThis.WebSocket;globalThis.WebSocket=FakeWebSocket;
 try{
  assert.throws(()=>new CDP('wss://evil.test/socket'));
  const cdp=new CDP('ws://127.0.0.1/socket');assert.deepEqual(await cdp.send('example'),{value:'ok'});
  await assert.rejects(cdp.send('reject'),/Chrome: -1/);
  let received;cdp.on('notification',params=>{received=params;});
  const event=new Event('message');event.data=JSON.stringify({method:'notification',params:{status:1}});FakeWebSocket.last.dispatchEvent(event);
  await Promise.resolve();assert.deepEqual(received,{status:1});
  const invalid=new Event('message');invalid.data='invalid';FakeWebSocket.last.dispatchEvent(invalid);
  cdp.close();await assert.rejects(cdp.send('after-close'),/closed/);
 }finally{globalThis.WebSocket=original;}
});

test('B2C diagnostics classify known errors without echoing passwords or payloads',()=>{
 assert.equal(classifyFormResponse('{"status":200}',200),'success');
 assert.equal(classifyFormResponse('{"status":400}',200),'error');
 assert.equal(classifyFormResponse('{}',400),'error');
 assert.equal(classifyFormResponse('not-json',200),'unknown');
 assert.equal(classifyFormResponse('{}',200),'unknown');
 assert.equal(classifyFormResponse('{"error":"bad"}',200),'error');
 for(const message of ['csrf token invalid','incorrect password','technical profile exception','locked too many attempts','unknown','AADB2C90053']){
  const result=b2cErrorSummary(JSON.stringify({message:message+' private-password',status:'400',errorCode:'AADB2C90053'}),400);
  assert.ok(!result.includes('private-password'));
 }
 for(const message of ['csrf','invalid credentials','technical profile','too many attempts','none','AADB2C90053'])assert.ok(b2cErrorSummary(JSON.stringify({error_description:message}),400));
 assert.ok(b2cErrorSummary('not-json',400));assert.ok(b2cErrorSummary('{}',400));
 assert.ok(isConfirmationUrl('/gdhvb2cflameconnect.onmicrosoft.com/B2C_1A_Test/api/CombinedSigninAndSignup/confirmed?x=1'));
 assert.ok(!isConfirmationUrl('https://evil.test/confirmed'));assert.ok(!isConfirmationUrl(null));
});


test('browser cleanup observes async exit and escalates only after its grace period', async () => {
  const signals = [];
  const child = {exitCode: null, signalCode: null, kill: signal => signals.push(signal)};
  let polls = 0;
  await stopBrowserProcess(child, async () => { if (++polls === 2) child.exitCode = 0; });
  assert.deepEqual(signals, ['SIGTERM']);
  assert.equal(polls, 2);
  await stopBrowserProcess(child, async () => assert.fail('already exited'));
  await stopBrowserProcess(undefined, async () => assert.fail('no process'));
  child.exitCode = null;
  signals.length = 0;
  const waits = [];
  await stopBrowserProcess(child, async duration => waits.push(duration));
  assert.deepEqual(signals, ['SIGTERM', 'SIGKILL']);
  assert.equal(waits.length, 31);
  assert.equal(waits.at(-1), 200);
  child.signalCode = 'SIGTERM';
  signals.length = 0;
  await stopBrowserProcess(child, async () => assert.fail('already signaled'));
  assert.deepEqual(signals, []);
});
