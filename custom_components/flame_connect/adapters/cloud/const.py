"""Public provider endpoints and identifiers (no account secrets)."""

HOST = "gdhvb2cflameconnect.b2clogin.com"
TENANT = "gdhvb2cflameconnect.onmicrosoft.com"
CLIENT_ID = "1af761dc-085a-411f-9cb9-53e5e2115bd2"
REDIRECT_URI = f"msal{CLIENT_ID}://auth"
ISSUER = f"https://{HOST}/b2185c80-45e7-454d-93c0-1f04e286f2ed/v2.0/"
SCOPE = f"openid profile offline_access https://{TENANT}/Mobile/read"
POLICIES = {"normal": "B2C_1A_FirePhoneSignUpOrSignInWithPhoneOrEmail", "social": "B2C_1A_FirePhoneSignInSocialOnly"}
