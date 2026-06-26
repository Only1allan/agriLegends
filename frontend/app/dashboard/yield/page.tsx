"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, TrendingUp } from "lucide-react";
import { RadialBarChart, RadialBar, PolarAngleAxis, ResponsiveContainer } from "recharts";

const API = "";

export default function YieldPage() {
  const router = useRouter();
  const [y, setY] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fid = localStorage.getItem("farmerId");
    if (!fid) { router.push("/onboarding"); return; }
    fetch(`${API}/api/farmer/${fid}`).then(r => r.json()).then(d => { setY(d.plots?.[0]?.forecastedYieldKg || 0); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ display: "flex", minHeight: "100dvh", alignItems: "center", justifyContent: "center", background: "var(--bg)" }}><TrendingUp size={44} className="anim-pulse-soft" style={{ color: "var(--primary)", opacity: 0.6 }} /></div>;

  const max = 12000;
  const pct = Math.min(100, (y / max) * 100);
  const data = [{ name: "y", value: pct, fill: "#4ade80" }];

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100dvh", background: "var(--bg)", paddingBottom: "calc(72px + var(--safe-bottom))" }}>
      <header style={{ position: "sticky", top: 0, zIndex: 10, background: "var(--bg)", padding: "12px 20px 8px", paddingTop: "calc(12px + var(--safe-top))", borderBottom: "1px solid rgba(0,0,0,0.04)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <a href="/" style={{ width: 34, height: 34, borderRadius: 10, background: "var(--card)", border: "1px solid var(--card-border)", display: "flex", alignItems: "center", justifyContent: "center", textDecoration: "none" }}>
            <ChevronLeft size={18} color="var(--text)" />
          </a>
          <h1 style={{ fontSize: 17, fontWeight: 700, letterSpacing: "-0.02em", color: "var(--text)" }}>Yield Forecast</h1>
        </div>
      </header>

      <main style={{ flex: 1, padding: "16px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
        <div className="card-lg anim-fade-up delay-1" style={{ overflow: "hidden" }}>
          <div className="card-header" style={{ background: "linear-gradient(90deg, #b45309, #d97706)" }} />
          <div style={{ padding: 24, textAlign: "center" }}>
            <div style={{ width: 180, height: 180, margin: "0 auto" }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart cx="50%" cy="50%" innerRadius="65%" outerRadius="100%" barSize={16} data={data} startAngle={180} endAngle={0}>
                  <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                  <RadialBar background={{ fill: "rgba(74,222,128,0.06)" }} dataKey="value" cornerRadius={10} />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <p style={{ fontSize: 36, fontWeight: 800, letterSpacing: "-0.03em", color: "var(--text)", marginTop: -20 }}>{y.toLocaleString()}</p>
            <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", marginTop: 4 }}>kg forecasted</p>
          </div>
        </div>

        <div className="anim-fade-up delay-2" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div className="card" style={{ padding: 16 }}>
            <p className="stat-label">Capacity</p>
            <p style={{ fontSize: 22, fontWeight: 800, color: "var(--text)", marginTop: 4 }}>{Math.round(pct)}%</p>
            <p style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2 }}>of {max.toLocaleString()} kg</p>
          </div>
          <div className="card" style={{ padding: 16 }}>
            <p className="stat-label">Confidence</p>
            <p style={{ fontSize: 22, fontWeight: 800, color: "var(--primary)", marginTop: 4 }}>Medium</p>
            <p style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2 }}>30 days of data</p>
          </div>
        </div>

        <div className="card anim-fade-up delay-3" style={{ padding: 20 }}>
          <div className="section-label" style={{ marginBottom: 8 }}>How It&apos;s Calculated</div>
          <p style={{ fontSize: 13, lineHeight: 1.7, color: "var(--text-secondary)" }}>
            Yield is forecasted using Growing Degree Days (GDD), soil baselines, and satellite NDVI data. The estimate improves as more observations are collected.
          </p>
        </div>
      </main>
    </div>
  );
}
