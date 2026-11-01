import { B2C_HOST } from './auth.mjs';

// Only response error metadata is inspected. Never accept request/form payloads here.
/** @param {string} body @param {number} status */
export function b2cErrorSummary(body, status) {
  let data;
  try {
    data = JSON.parse(body);
  } catch {
    return `B2C rejected the form (HTTP ${status}); the response was not JSON.`;
  }
  const message =
    typeof data.message === 'string'
      ? data.message
      : typeof data.error_description === 'string'
        ? data.error_description
        : '';
  const aad =
    (typeof data.errorCode === 'string' && /^AADB2C\d+$/.test(data.errorCode)
      ? data.errorCode
      : null) ?? message.match(/AADB2C\d+/)?.[0];
  // Keep only known classifications, not arbitrary upstream strings or credential values.
  let reason = 'The provider did not supply a recognized public reason.';
  if (aad === 'AADB2C90053')
    reason = 'B2C could not find this account under the selected login policy.';
  if (/csrf|cross.?site|forgery|verification token/i.test(message))
    reason = 'B2C reported a session/CSRF verification problem.';
  else if (
    /invalid.*(?:username|password|credentials)|incorrect.*password|invalid.*provided|unable to validate/i.test(
      message,
    )
  )
    reason =
      'B2C could not validate the login; the account or policy configuration may need checking.';
  else if (
    /technical profile|claims exchange|internal error|service.*error|server error|exception/i.test(
      message,
    )
  )
    reason = 'B2C reported an internal policy or validation service failure.';
  else if (/locked|too many|throttl/i.test(message))
    reason = 'B2C reported a lockout or attempt limit.';
  const providerStatus =
    typeof data.status === 'string' && /^\d{1,4}$/.test(data.status)
      ? `; B2C status ${data.status}`
      : '';
  return `B2C rejected the form (HTTP ${status}${providerStatus}${aad ? `; ${aad}` : ''}). ${reason}`;
}

/** @param {string} body @param {number} status */
export function classifyFormResponse(body, status) {
  if (status >= 400) return 'error';
  let data;
  try {
    data = JSON.parse(body);
  } catch {
    return 'unknown';
  }
  if (Number(data.status) === 200) return 'success';
  if (Number(data.status) >= 400 || data.errorCode || data.error) return 'error';
  return 'unknown';
}

/** @param {unknown} raw */
export function isConfirmationUrl(raw) {
  if (typeof raw !== 'string') return false;
  try {
    const u = new URL(raw, `https://${B2C_HOST}`);
    return (
      u.protocol === 'https:' &&
      u.hostname === B2C_HOST &&
      !u.port &&
      !u.username &&
      !u.password &&
      /^\/gdhvb2cflameconnect\.onmicrosoft\.com\/(?:B2C_[^/]+\/)?api\/[A-Za-z]+\/confirmed$/.test(
        u.pathname,
      )
    );
  } catch {
    return false;
  }
}
