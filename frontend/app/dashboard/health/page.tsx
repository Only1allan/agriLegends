"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, BarChart3, AlertTriangle, Leaf } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function HealthPage() {
  const [obs, setObs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const fid = localStorage.getItem("farmerId");
    if (!fid) { router.push("/onboarding"); return; }
    const pid = localStorage.getItem("plotId");
    const go = (p: string) => fetch(`${API}/api/plot/${p}/observations?days=30`).then(r => r.json()).then(d => { setObs(d?.map((x: any) => ({ ...x, date: x.date?.slice(5) })) ?? []); setLoading(false); }).catch(() => setLoading(false));
    if (pid) { go(pid); return; }
    fetch(`${API}/api/farmer/${fid}`).then(r => r.json()).then(f => { const p = f.plots?.[0]?.plotId; if (p) { localStorage.setItem("plotId", p); go(p); } }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ display: "flex", minHeight: "100dvh", alignItems: "center", justifyContent: "center", background: "#0d1f15" }}><BarChart3 size={36} color="#4ade80" style={{ opacity: 0.3 }} /></div>;

  const last = obs[obs.length - 1];
  const avg = obs.length ? obs.reduce((a, b) => a + b.ndvi, 0) / obs.length : 0;
  const trend = obs.length >= 2 ? obs[obs.length - 1].ndvi - obs[0].ndvi : 0;
  const status = last ? last.ndvi > 0.65 ? ["Healthy", "#4ade80"] : last.ndvi > 0.4 ? ["Moderate", "#d4a844"] : ["Stressed", "#f87171"] : ["—", "#5a6e5e"];

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100dvh", background: "#0d1f15", paddingBottom: "calc(80px + var(--safe-bottom))" }}>
      <header style={{ position: "sticky", top: 0, zIndex: 10, background: "rgba(13,31,21,0.9)", backdropFilter: "blur(20px)", padding: "14px 18px 10px", paddingTop: "calc(14px + var(--safe-top))" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <a href="/" style={{ width: 32, height: 32, borderRadius: 8, background: "#13291e", border: "1px solid #1e3a2a", display: "flex", alignItems: "center", justifyContent: "center", textDecoration: "none" }}><ChevronLeft size={16} color="#e8e6dc" /></a>
          <h1 style={{ fontSize: 20, fontFamily: "'Cormorant Garamond', serif", fontWeight: 600, margin: 0, letterSpacing: "-0.02em", color: "#e8e6dc" }}>Plot Health</h1>
        </div>
      </header>

      <main style={{ flex: 1, padding: "0 18px 16px", display: "flex", flexDirection: "column", gap: 14 }}>
        <div className="anim-slide sd1" style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 1, background: "#1e3a2a", borderRadius: 16, overflow: "hidden" }}>
          {[
            { v: last?.ndvi?.toFixed(2) ?? "—", l: "NDVI" },
            { v: `${(trend * 100).toFixed(1)}%`, l: "Trend" },
            { v: status[0], l: "Status", c: status[1] },
          ].map(({ v, l, c }) => (
            <div key={l} style={{ background: "#13291e", padding: "14px 8px", textAlign: "center" }}>
              <p style={{ fontSize: 20, fontWeight: 700, fontFamily: "'Cormorant Garamond', serif", margin: 0, color: c || "#e8e6dc" }}>{v}</p>
              <p style={{ fontSize: 10, fontWeight: 600, color: "#8b9e8e", textTransform: "uppercase", letterSpacing: "0.04em", marginTop: 2 }}>{l}</p>
            </div>
          ))}
        </div>

        <div className="panel anim-slide sd2" style={{ padding: 18, overflow: "hidden" }}>
          <div className="sect-label" style={{ marginBottom: 14, paddingLeft: 0 }}>NDVI Trend (30 days)</div>
          <div style={{ height: 240, margin: "0 -8px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={obs}>
                <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4ade80" stopOpacity={0.25} /><stop offset="100%" stopColor="#4ade80" stopOpacity={0} /></linearGradient></defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#8b9e8e" }} axisLine={false} tickLine={false} />
                <YAxis domain={[0.2, 1.0]} tick={{ fontSize: 10, fill: "#8b9e8e" }} axisLine={false} tickLine={false} width={28} />
                <Tooltip contentStyle={{ background: "#13291e", border: "1px solid #1e3a2a", borderRadius: 12, fontSize: 12, color: "#e8e6dc" }} />
                <ReferenceLine y={0.65} stroke="#4ade80" strokeDasharray="4 4" />
                <ReferenceLine y={0.4} stroke="#d4a844" strokeDasharray="4 4" />
                <Area type="monotone" dataKey="ndvi" stroke="#4ade80" strokeWidth={2.5} fill="url(#g)" dot={false} activeDot={{ r: 4, fill: "#4ade80", stroke: "#0d1f15", strokeWidth: 2 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {last && last.ndvi <= 0.4 && (
          <div style={{ background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.15)", borderRadius: 14, padding: 14, display: "flex", gap: 10, alignItems: "flex-start" }}>
            <AlertTriangle size={18} color="#f87171" />
            <div><p style={{ fontSize: 13, fontWeight: 600, color: "#f87171", margin: 0 }}>Crop Stress</p><p style={{ fontSize: 12, color: "#f87171", opacity: 0.8, margin: "2px 0 0" }}>NDVI below healthy threshold. Run diagnostic for advice.</p></div>
          </div>
        )}
      </main>
    </div>
  );
}
