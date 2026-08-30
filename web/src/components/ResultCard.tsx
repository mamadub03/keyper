import type { ScanResult } from "../types";

const BADGE: Record<ScanResult["status"], string> = {
  SAFE: "🟢 SAFE",
  AT_RISK: "🔴 AT RISK",
  UNKNOWN: "🟡 UNKNOWN",
};

interface Props {
  result: ScanResult;
  onViewEvidence: () => void;
  onFix: () => void;
}

export function ResultCard({ result, onViewEvidence, onFix }: Props) {
  return (
    <div className={`result-card status-${result.status.toLowerCase()}`}>
      <h3>{result.service_name}</h3>
      <p className="badge">{BADGE[result.status]}</p>
      <p>{result.summary}</p>
      <div className="card-actions">
        <button onClick={onViewEvidence}>View Evidence</button>
        {result.status === "AT_RISK" && <button onClick={onFix}>Fix with Keyper</button>}
      </div>
    </div>
  );
}
