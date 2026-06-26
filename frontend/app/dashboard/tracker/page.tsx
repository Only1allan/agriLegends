"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, CheckCircle, XCircle, AlertCircle, Sprout, Calendar } from "lucide-react";

const API = "";

export default function TrackerPage() {
  const router = useRouter();
  const [recs, setRecs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fid = localStorage.getItem("farmerId");
    if (!fid) { router.push("/onboarding"); return; }
    const pid = localStorage.getItem("plotId");
    if (!pid) { setLoading(false); return; }
    fetch(`${API}/api/plot/${pid}/recommendations`).then(r => r.json()).then(d => { setRecs(d ?? []); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ display: "flex", minHeight: "100dvh", alignItems: "center", justifyContent: "center", background: "var(--bg)" }}><Sprout size={44} className="anim-pulse-soft" style={{ color: "var(--primary)", opacity: 0.6 }} /></div>;

  const items = recs.length > 0 ? recs : [
    { date: "2026-06-24", status: "done", narrative: "Apply fungicide for late blight" },
    { date: "2026-06-23", status: "done", narrative: "Monitor soil moisture" },
    { date: "2026-06-22", status: "done", narrative: "Check for early blight" },
    { date: "2026-06-21", status: "missed", narrative: "Irrigate 25-30mm" },
  ];
  const done = items.filter(r => r.status === "done").length;
  const pct = Math.round((done / items.length) * 100);

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
        <div className="card-lg anim-fade-up delay-1" style={{ overflow: "hidden", textAlign: "center" }}>
          <div className="card-header" style={{ background: "linear-gradient(90deg, var(--primary), var(--primary-light))" }} />
          <div style={{ padding: 24 }}>
            <p className="stat-label">Compliance Rate</p>
            <p style={{ fontSize: 48, fontWeight: 800, letterSpacing: "-0.03em", color: "var(--primary)", marginTop: 4 }}>{pct}%</p>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>{done}/{items.length} completed</p>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {items.map((r: any, i: number) => {
            const Icon = r.status === "done" ? CheckCircle : r.status === "missed" ? XCircle : AlertCircle;
            const ic = r.status === "done" ? "var(--primary)" : r.status === "missed" ? "#dc2626" : "#b45309";
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
                <span style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: ic, flexShrink: 0 }}>{r.status === "done" ? "Done" : r.status === "missed" ? "Missed" : "Partial"}</span>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
