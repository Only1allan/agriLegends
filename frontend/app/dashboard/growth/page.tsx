"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, Sprout, Leaf, Check, AlertTriangle } from "lucide-react";

const API = "";

const STAGES = [
  { name: "Emergence", days: "0-21", desc: "Seedlings emerge from soil", tip: "Keep soil moist, control weeds" },
  { name: "Tuber Initiation", days: "22-45", desc: "Tubers begin forming", tip: "Scout for late blight" },
  { name: "Tuber Bulking", days: "46-80", desc: "Tubers grow rapidly", tip: "Critical moisture period" },
  { name: "Maturation", days: "81-110", desc: "Skin sets, harvest nears", tip: "Reduce irrigation" },
];

const BG = "#0d1f15";
const SURFACE = "#13291e";
const BORDER = "#1e3a2a";
const TEXT = "#e8e6dc";
const TEXT_SEC = "#8b9e8e";
const GREEN = "#4ade80";
const GREEN_DIM = "#22c55e";
const GOLD = "#d4a844";

export default function GrowthPage() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fid = localStorage.getItem("farmerId");
    if (!fid) { router.push("/onboarding"); return; }
    const pid = localStorage.getItem("plotId");
    const go = (p: string) => fetch(`${API}/api/plot/${p}/growth`)
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); })
      .then(d => { setData(d); setLoading(false); })
      .catch(() => { setError(true); setLoading(false); });
    if (pid) { go(pid); return; }
    fetch(`${API}/api/farmer/${fid}`).then(r => r.json()).then(f => { const p = f.plots?.[0]?.plotId; if (p) { localStorage.setItem("plotId", p); go(p); } }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ display: "flex", minHeight: "100dvh", alignItems: "center", justifyContent: "center", background: BG }}>
    <Sprout size={40} color={GREEN} style={{ opacity: 0.5 }} className="anim-up" /></div>;

  if (error) return <div style={{ display: "flex", flexDirection: "column", minHeight: "100dvh", alignItems: "center", justifyContent: "center", background: BG, padding: 24, textAlign: "center" }}>
    <AlertTriangle size={36} color="#dc2626" style={{ marginBottom: 10 }} />
    <p style={{ fontSize: 15, fontWeight: 600, color: TEXT, margin: "0 0 4px" }}>Failed to load growth data</p>
    <p style={{ fontSize: 13, color: TEXT_SEC, margin: "0 0 16px" }}>Check your connection and try again</p>
    <button onClick={() => window.location.reload()} style={{ background: GREEN, color: BG, border: "none", borderRadius: 10, padding: "8px 20px", fontSize: 13, fontWeight: 700, cursor: "pointer" }}>Retry</button>
  </div>;

  const idx = Math.max(0, STAGES.findIndex(s => s.name === data?.stage));
  const cur = STAGES[idx];
  const pct = Math.min(100, Math.max(0, data?.progress ?? 0));

  return (
    <div style={{ background: BG, minHeight: "100dvh", paddingBottom: "calc(80px + var(--safe-bottom))" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "16px 20px 8px", paddingTop: "calc(16px + var(--safe-top))" }}>
        <a href="/" style={{ width: 32, height: 32, borderRadius: 8, background: SURFACE, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", textDecoration: "none" }}>
          <ChevronLeft size={16} color={TEXT} />
        </a>
        <h1 style={{ fontSize: 17, fontWeight: 600, margin: 0, letterSpacing: "-0.02em", color: TEXT }}>Growth Timeline</h1>
      </div>

      <main style={{ padding: "8px 20px 16px" }}>
        <div className="anim-up d1" style={{ marginBottom: 20 }}>
          <p className="stat-label" style={{ marginBottom: 6 }}>Current Stage</p>
          <div style={{ borderLeft: `4px solid ${GREEN_DIM}`, paddingLeft: 16 }}>
            <p style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-0.03em", color: TEXT, margin: 0 }}>{data?.stage}</p>
            <p style={{ fontSize: 14, color: TEXT_SEC, margin: "4px 0 0" }}>{cur.desc} &mdash; <strong>Day {data?.day}</strong></p>
          </div>
        </div>

        <div className="anim-up d2" style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <span className="stat-label">Progress</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: GREEN, fontFamily: "DM Sans, sans-serif" }}>{Math.round(pct)}%</span>
          </div>
          <div style={{ height: 4, borderRadius: 2, background: BORDER, overflow: "hidden" }}>
            <div style={{ height: "100%", borderRadius: 2, background: GREEN, width: `${pct}%`, transition: "width 0.6s ease" }} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4, fontSize: 11, color: TEXT_SEC }}>
            <span>Day {data?.stageStart}</span>
            <span>Day {data?.stageEnd}</span>
          </div>
        </div>

        <p className="stat-label" style={{ marginBottom: 10 }}>All Stages</p>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {STAGES.map((s, i) => {
            const active = i === idx;
            const past = i < idx;
            return (
              <div key={s.name} className="card anim-up" style={{ padding: 14, opacity: past && !active ? 0.65 : 1, borderLeft: active ? `4px solid ${GREEN}` : `4px solid ${BORDER}`, animationDelay: `${0.2 + i * 0.06}s` }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ width: 36, height: 36, borderRadius: 8, background: active ? GREEN : past ? "rgba(74, 222, 128, 0.12)" : SURFACE, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    {past ? <Check size={18} color={GREEN} /> : <Leaf size={18} color={active ? BG : TEXT_SEC} />}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <p style={{ fontSize: 14, fontWeight: 600, color: TEXT, margin: 0 }}>{s.name}</p>
                      {active && <span style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", background: "rgba(74, 222, 128, 0.15)", color: GREEN, borderRadius: 9999, padding: "2px 8px" }}>Now</span>}
                    </div>
                    <p style={{ fontSize: 12, color: TEXT_SEC, margin: "2px 0 0" }}>{s.tip}</p>
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 600, color: TEXT_SEC, flexShrink: 0 }}>Days {s.days}</span>
                </div>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
