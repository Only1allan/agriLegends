"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, CheckCircle, Clock, AlertCircle, Sprout, Calendar } from "lucide-react";

const API = "";

export default function TrackerPage() {
  const router = useRouter();
  const [recs, setRecs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fid = localStorage.getItem("farmerId");
    if (!fid) { router.push("/onboarding"); return; }
    const pid = localStorage.getItem("plotId");
    if (!pid) { setLoading(false); return; }
    fetch(`${API}/api/plot/${pid}/recommendations`)
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); })
      .then(d => { setRecs(d ?? []); setLoading(false); })
      .catch(() => { setError(true); setLoading(false); });
  }, []);

  if (loading) return <div style={{ display: "flex", minHeight: "100dvh", alignItems: "center", justifyContent: "center", background: "var(--bg)" }}><Sprout size={44} className="anim-pulse-soft" style={{ color: "var(--primary)", opacity: 0.6 }} /></div>;

  const items = recs.map((r: any) => ({
    ...r,
    status: r.masumiStatus === "VERIFIED_ON_CHAIN" ? "done" : "pending",
  }));
  const done = items.filter(r => r.status === "done").length;
  const pct = items.length > 0 ? Math.round((done / items.length) * 100) : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100dvh", background: "var(--bg)", paddingBottom: "calc(72px + var(--safe-bottom))" }}>
      <header style={{ position: "sticky", top: 0, zIndex: 10, background: "var(--bg)", padding: "12px 20px 8px", paddingTop: "calc(12px + var(--safe-top))", borderBottom: "1px solid rgba(0,0,0,0.04)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <a href="/" style={{ width: 34, height: 34, borderRadius: 10, background: "var(--card)", border: "1px solid var(--card-border)", display: "flex", alignItems: "center", justifyContent: "center", textDecoration: "none" }}>
            <ChevronLeft size={18} color="var(--text)" />
          </a>
          <h1 style={{ fontSize: 17, fontWeight: 700, letterSpacing: "-0.02em", color: "var(--text)" }}>Action Tracker</h1>
        </div>
      </header>

      <main style={{ flex: 1, padding: "16px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
        {error ? (
          <div className="card anim-fade-up" style={{ padding: 24, textAlign: "center" }}>
            <AlertCircle size={32} style={{ color: "#dc2626", marginBottom: 8 }} />
            <p style={{ fontSize: 14, color: "var(--text)", margin: 0 }}>Failed to load recommendations</p>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "4px 0 0" }}>Check your connection and try again</p>
          </div>
        ) : items.length === 0 ? (
          <div className="card anim-fade-up" style={{ padding: 24, textAlign: "center" }}>
            <Clock size={32} style={{ color: "var(--text-secondary)", marginBottom: 8 }} />
            <p style={{ fontSize: 14, color: "var(--text)", margin: 0 }}>No recommendations yet</p>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "4px 0 0" }}>Run a diagnostic from the home screen to get your first action plan</p>
          </div>
        ) : (
          <>
            <div className="card-lg anim-fade-up delay-1" style={{ overflow: "hidden", textAlign: "center" }}>
              <div className="card-header" style={{ background: "linear-gradient(90deg, var(--primary), var(--primary-light))" }} />
              <div style={{ padding: 24 }}>
                <p className="stat-label">Compliance Rate</p>
                <p style={{ fontSize: 48, fontWeight: 800, letterSpacing: "-0.03em", color: "var(--primary)", marginTop: 4 }}>{pct}%</p>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>{done}/{items.length} verified on-chain</p>
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {items.map((r: any, i: number) => {
                const Icon = r.status === "done" ? CheckCircle : Clock;
                const ic = r.status === "done" ? "var(--primary)" : "#b45309";
                return (
                  <div key={i} className="card anim-fade-up" style={{ padding: 14, display: "flex", alignItems: "center", gap: 12, animationDelay: `${0.2 + i * 0.05}s` }}>
                    <Icon size={18} style={{ color: ic, flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <Calendar size={11} style={{ color: "var(--text-secondary)" }} />
                        <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)" }}>{r.date}</span>
                      </div>
                      <p style={{ fontSize: 13, color: "var(--text)", marginTop: 1 }}>{r.narrative || r.action}</p>
                    </div>
                    <span style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: ic, flexShrink: 0 }}>{r.status === "done" ? "Verified" : "Pending"}</span>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
