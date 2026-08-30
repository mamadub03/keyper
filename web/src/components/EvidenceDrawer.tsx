import type { ScanResult } from "../types";

interface Props {
  result: ScanResult;
  onClose: () => void;
}

export function EvidenceDrawer({ result, onClose }: Props) {
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <button className="drawer-close" onClick={onClose}>
          Close
        </button>
        <h2>{result.service_name} — evidence</h2>
        <p>{result.summary}</p>

        <h3>Authentication</h3>
        <ul>
          <li>Institutional methods found: {result.authentication.institutional_methods_found.join(", ") || "none"}</li>
          <li>Independent method found: {String(result.authentication.independent_method_found)}{result.authentication.independent_method ? ` (${result.authentication.independent_method})` : ""}</li>
          <li>Verified: {String(result.authentication.verified)}</li>
        </ul>

        <h3>Recovery</h3>
        <ul>
          <li>Institutional dependency found: {String(result.recovery.institutional_dependency_found)}</li>
          <li>Independent method found: {String(result.recovery.independent_method_found)}</li>
          <li>Verified: {String(result.recovery.verified)}</li>
        </ul>

        <h3>Raw evidence</h3>
        <ul>
          {result.evidence.map((ev, i) => (
            <li key={i}>
              {ev.observation} <em>— {ev.source}</em>
            </li>
          ))}
          {result.evidence.length === 0 && <li>No evidence recorded.</li>}
        </ul>
      </div>
    </div>
  );
}
