import { useState } from "react";

interface Props {
  onSubmit: (identity: string, aliases: string[], urls: string[]) => void;
  loading: boolean;
}

export function IdentityForm({ onSubmit, loading }: Props) {
  const [identity, setIdentity] = useState("");
  const [aliasText, setAliasText] = useState("");
  const [urls, setUrls] = useState(["", "", ""]);

  function updateUrl(i: number, value: string) {
    const next = [...urls];
    next[i] = value;
    setUrls(next);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const aliases = aliasText
      .split(",")
      .map((a) => a.trim())
      .filter(Boolean);
    const cleanUrls = urls.map((u) => u.trim()).filter(Boolean);
    onSubmit(identity.trim(), aliases, cleanUrls);
  }

  return (
    <form onSubmit={handleSubmit} className="identity-form">
      <h1>KEYPER</h1>
      <p>What happens to your accounts if your school or work identity disappears?</p>

      <label>
        Institutional identity
        <input
          type="email"
          required
          placeholder="student@g.school.edu"
          value={identity}
          onChange={(e) => setIdentity(e.target.value)}
        />
      </label>

      <label>
        Known aliases (comma-separated, optional)
        <input
          type="text"
          placeholder="student@school.edu"
          value={aliasText}
          onChange={(e) => setAliasText(e.target.value)}
        />
      </label>

      <p className="section-label">Services to test</p>
      {urls.map((u, i) => (
        <input
          key={i}
          type="url"
          placeholder="https://..."
          value={u}
          onChange={(e) => updateUrl(i, e.target.value)}
        />
      ))}

      <button type="submit" disabled={loading}>
        {loading ? "Testing..." : "Test My Accounts"}
      </button>
    </form>
  );
}
