#!/usr/bin/env node
// Run on the user's desktop, never on the Home Assistant server.
import {createInterface} from 'node:readline/promises';
import {stdin,stdout} from 'node:process';
import {launchLoginBrowser} from './browser.mjs';
import {validateAuthorizeUrl} from './auth.mjs';

const input=createInterface({input:stdin,output:stdout});
let browser,timer,completed=false,cancel=()=>{};
const abort=new AbortController();
const stop=()=>{abort.abort();cancel(Error('Vinculación cancelada.'));};
process.once('SIGINT',stop);process.once('SIGTERM',stop);
try{
 console.log('Flame Connect · Vinculación no oficial de Home Assistant\nLa contraseña se introduce solo en la ventana oficial de Microsoft.');
 const url=validateAuthorizeUrl((await input.question('Pega el enlace de acceso mostrado por Home Assistant: ',{signal:abort.signal})).trim());input.close();
 let resolve,reject;const returned=new Promise((yes,no)=>{resolve=yes;reject=no;});
 returned.catch(()=>{});cancel=reject;
 timer=setTimeout(()=>reject(Error('El acceso ha caducado. Reinicia la vinculación desde Home Assistant.')),600000);
 browser=await launchLoginBrowser({url,onEvent:message=>console.log(message),onCallback:raw=>{completed=true;resolve(raw);},onClose:()=>{if(!completed)reject(Error('Se cerró el acceso antes de completarlo.'));}});
 const callback=await returned;
 console.log('\nPega este retorno en el campo protegido de Home Assistant. Contiene un código de un solo uso; no lo compartas:\n');
 console.log(callback);
}catch(error){console.error(error.message);process.exitCode=1;}
finally{input.close();clearTimeout(timer);await browser?.close();process.removeListener('SIGINT',stop);process.removeListener('SIGTERM',stop);}
