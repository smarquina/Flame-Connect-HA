"""Public provider endpoints and identifiers (no account secrets)."""

HOST = "gdhvb2cflameconnect.b2clogin.com"
TENANT = "gdhvb2cflameconnect.onmicrosoft.com"
CLIENT_ID = "1af761dc-085a-411f-9cb9-53e5e2115bd2"
REDIRECT_URI = f"msal{CLIENT_ID}://auth"
ISSUER = f"https://{HOST}/b2185c80-45e7-454d-93c0-1f04e286f2ed/v2.0/"
SCOPE = f"openid profile offline_access https://{TENANT}/Mobile/read"
POLICIES = {"normal": "B2C_1A_FirePhoneSignUpOrSignInWithPhoneOrEmail", "social": "B2C_1A_FirePhoneSignInSocialOnly"}

# Resource limits are policy choices, not protocol enum values.
HTTP_REQUEST_TIMEOUT_SECONDS = 30
HTTP_RESPONSE_CHUNK_BYTES = 65536
HTTP_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
LOGIN_TIMEOUT_SECONDS = 60
LOGIN_MAX_REDIRECTS = 20
LOGIN_FIELD_MAX_CHARS = 16000
LOGIN_EMAIL_MAX_CHARS = 512
LOGIN_PASSWORD_MAX_CHARS = 4096
TOKEN_MAX_CHARS = 20000
