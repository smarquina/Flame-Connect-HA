// Public application identifiers; no tokens or account credentials live here.
export const B2C_HOST='gdhvb2cflameconnect.b2clogin.com';
export const CLIENT_ID='1af761dc-085a-411f-9cb9-53e5e2115bd2';
export const REDIRECT_URI=`msal${CLIENT_ID}://auth`;
export function isCallback(raw){try{const u=new URL(raw);return u.protocol===`msal${CLIENT_ID}:`&&u.hostname==='auth'&&!u.username&&!u.password&&!u.port&&['','/'].includes(u.pathname)&&!u.hash;}catch{return false;}}
export function validateAuthorizeUrl(raw){
 const u=new URL(raw);
 if(u.protocol!=='https:'||u.hostname!==B2C_HOST||u.port||u.username||u.password||u.hash||!/^\/gdhvb2cflameconnect\.onmicrosoft\.com\/B2C_1A_FirePhone(?:SignUpOrSignInWithPhoneOrEmail|SignInSocialOnly)\/oauth2\/v2\.0\/authorize$/.test(u.pathname))throw Error('La URL no es el login oficial de Flame Connect.');
 if([...u.searchParams.keys()].some(k=>u.searchParams.getAll(k).length!==1)||u.searchParams.get('client_id')!==CLIENT_ID||u.searchParams.get('redirect_uri')!==REDIRECT_URI||u.searchParams.get('response_type')!=='code'||u.searchParams.get('code_challenge_method')!=='S256'||!u.searchParams.get('state')||!u.searchParams.get('nonce')||!u.searchParams.get('code_challenge'))throw Error('La URL no contiene una transacción PKCE válida.');
 return u.toString();
}
