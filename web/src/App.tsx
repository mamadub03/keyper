import { useEffect, useState } from "react";
import { IdentityForm } from "./components/IdentityForm";
import { ResultCard } from "./components/ResultCard";
import { EvidenceDrawer } from "./components/EvidenceDrawer";
import { FixPanel } from "./components/FixPanel";
import { fixService, getDemoConfig, scanService } from "./api";
import type { DemoConfig, ScanResult } from "./types";

export default function App() {
  const [identity, setIdentity] = useState("");
  const [aliases, setAliases] = useState<string[]>([]);
  const [results, setResults] = useState<ScanResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [fixing, setFixing] = useState<string | null>(null);
  const [evidenceFor, setEvidenceFor] = useState<ScanResult | null>(null);
  const [fixPanelFor, setFixPanelFor] = useState<ScanResult | null>(null);

  // Ask the API how to pre-fill the form. Until this resolves we don't
  // render the form, so IdentityForm can seed its state straight from the
  // config with no async races. `null` = still loading; a config with an
  // empty service_urls just means "start blank".
  const [demo, setDemo] = useState<DemoConfig | null>(null);
  useEffect(() => {
    getDemoConfig()
      .then(setDemo)
      .catch(() => setDemo({ lab_url: "", identity: "", service_urls: [] }));
  }, []);

  async function handleTest(newIdentity: string, newAliases: string[], urls: string[]) {
    setIdentity(newIdentity);
    setAliases(newAliases);
    setResults([]);
    setLoading(true);
    // Scan one service at a time and show each card as it lands. Sequential
    // on purpose: each scan drives its own AgentCore Browser session, and
    // firing four at once risks a concurrency quota mid-demo. It also reads
    // better on screen — the report builds up service by service.
    try {
      for (const url of urls) {
        let card: ScanResult;
        try {
          card = await scanService({
            institutional_identity: newIdentity,
            institutional_aliases: newAliases,
            service_url: url,
            mode: "SCAN",
          });
        } catch (err) {
          card = {
            service_name: url,
            service_url: url,
            status: "UNKNOWN",
            authentication: { institutional_methods_found: [], independent_method_found: false, independent_method: null, verified: false },
            recovery: { institutional_dependency_found: false, independent_method_found: false, verified: false },
            dependencies: [],
            evidence: [],
            remediation_options: [],
            human_action_required: true,
            summary: `Scan failed: ${err instanceof Error ? err.message : String(err)}`,
          };
        }
        setResults((prev) => [...prev, card]);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleApproveFix(result: ScanResult) {
    setFixing(result.service_url);
    try {
      const updated = await fixService({
        institutional_identity: identity,
        institutional_aliases: aliases,
        service_url: result.service_url,
        mode: "FIX",
        approved: true,
      });
      setResults((prev) => prev.map((r) => (r.service_url === updated.service_url ? updated : r)));
      setFixPanelFor(null);
    } finally {
      setFixing(null);
    }
  }

  if (!demo) {
    return <div className="app" />; // brief: waiting on /demo-config from localhost
  }

  return (
    <div className="app">
      <IdentityForm
        onSubmit={handleTest}
        loading={loading}
        defaultIdentity={demo.identity}
        defaultUrls={demo.service_urls}
      />

      {(results.length > 0 || loading) && (
        <section>
          <h2>
            Continuity Report
            {loading && <span className="scanning"> — scanning… ({results.length} done)</span>}
          </h2>
          <div className="results-grid">
            {results.map((r) => (
              <ResultCard
                key={r.service_url}
                result={r}
                onViewEvidence={() => setEvidenceFor(r)}
                onFix={() => setFixPanelFor(r)}
              />
            ))}
          </div>
        </section>
      )}

      {evidenceFor && <EvidenceDrawer result={evidenceFor} onClose={() => setEvidenceFor(null)} />}
      {fixPanelFor && (
        <FixPanel
          result={fixPanelFor}
          fixing={fixing === fixPanelFor.service_url}
          onApprove={() => handleApproveFix(fixPanelFor)}
          onClose={() => setFixPanelFor(null)}
        />
      )}
    </div>
  );
}
