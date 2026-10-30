#!/usr/bin/env node
// Run on the user's desktop, never on the Home Assistant server.
import {createInterface} from 'node:readline/promises';
import {stdin,stdout} from 'node:process';
import {launchLoginBrowser} from './browser.mjs';
import {validateAuthorizeUrl} from './auth.mjs';

const input=createInterface({input:stdin,output:stdout});
let browser,timer,completed=false,cancel=()=>{};
const abort=new AbortController();
const stop=()=>{abort.abort();cancel(Error('Account linking cancelled.'));};
process.once('SIGINT',stop);process.once('SIGTERM',stop);
try{
 console.log('Flame Connect · Unofficial Home Assistant account linking\nEnter your password only in the official Microsoft window.');
 const url=validateAuthorizeUrl((await input.question('Paste the authorization link shown by Home Assistant: ',{signal:abort.signal})).trim());input.close();
 let resolve,reject;const returned=new Promise((yes,no)=>{resolve=yes;reject=no;});
 returned.catch(()=>{});cancel=reject;
 timer=setTimeout(()=>reject(Error('Login expired. Restart account linking from Home Assistant.')),600000);
 browser=await launchLoginBrowser({url,onEvent:message=>console.log(message),onCallback:raw=>{completed=true;resolve(raw);},onClose:()=>{if(!completed)reject(Error('The login window closed before linking finished.'));}});
 const callback=await returned;
 console.log('\nPaste this return URL into the protected Home Assistant field. It contains a one-use code; do not share it:\n');
 console.log(callback);
}catch(error){console.error(error.message);process.exitCode=1;}
finally{input.close();clearTimeout(timer);await browser?.close();process.removeListener('SIGINT',stop);process.removeListener('SIGTERM',stop);}
