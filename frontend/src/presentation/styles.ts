import { css } from 'lit';
export const sharedStyles = css`
  :host {
    display: block;
    color: var(--primary-text-color, #202020);
    font: inherit;
  }
  * {
    box-sizing: border-box;
  }
  button,
  input,
  select {
    font: inherit;
    color: inherit;
  }
  button,
  select,
  input {
    min-height: 44px;
    border: 1px solid var(--divider-color, #777);
    border-radius: 10px;
    background: var(--card-background-color, #fff);
  }
  button {
    cursor: pointer;
    padding: 8px 14px;
  }
  :where(button[aria-pressed='true']) {
    border-color: var(--primary-color, #007a91);
    background: var(--primary-color, #007a91);
    color: var(--text-primary-color, #fff);
  }
  button:disabled,
  select:disabled,
  input:disabled {
    cursor: default;
    opacity: 0.6;
  }
  :focus-visible {
    outline: 3px solid var(--primary-color, #007a91);
    outline-offset: 3px;
  }
  label {
    display: grid;
    gap: 6px;
    font-size: 0.9rem;
  }
  select,
  input {
    width: 100%;
    padding: 8px 10px;
  }
  .hint {
    font-size: 0.8rem;
    line-height: 1.5;
    color: var(--secondary-text-color, #555);
    margin: 6px 0 0;
  }
  .error {
    color: var(--error-color, #a72020);
    font-size: 0.9rem;
    line-height: 1.4;
  }
`;
