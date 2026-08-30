import type { ScanResult } from "../types";

interface Props {
  result: ScanResult;
  onApprove: () => void;
  onClose: () => void;
  fixing: boolean;
}

export function FixPanel({ result, onApprove, onClose, fixing }: Props) {
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <button className="drawer-close" onClick={onClose}>
          Close
        </button>
        <h2>Why this is at risk</h2>
        <p>{result.summary}</p>

        <h2>Keyper found</h2>
        {result.remediation_options.length === 0 ? (
          <p>No safe remediation found yet — run a fix to have the agent look.</p>
        ) : (
          <ul>
            {result.remediation_options.map((opt, i) => (
              <li key={i}>
                {opt.action}
                {opt.requires_secret_input ? " (will pause for you to enter a secret)" : ""}
              </li>
            ))}
          </ul>
        )}

        <button onClick={onApprove} disabled={fixing}>
          {fixing ? "Working..." : "Start Fix"}
        </button>
        {result.human_action_required && (
          <p className="checkpoint-note">
            The agent may pause and hand the browser to you for a sensitive step
            (password, MFA, OTP, recovery code, or security key). Complete that
            step yourself, then let it continue — Keyper never touches secrets.
          </p>
        )}
      </div>
    </div>
  );
}
