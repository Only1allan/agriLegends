"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, Sprout, Droplets, FlaskConical, Mountain } from "lucide-react";

const API = "";

const BG = "#0d1f15";
const SURFACE = "#13291e";
const BORDER = "#1e3a2a";
const TEXT = "#e8e6dc";
const TEXT_SEC = "#8b9e8e";
const GREEN = "#4ade80";
const GOLD = "#d4a844";
const BLUE = "#60a5fa";

const METRICS = [
  { key: "ph", label: "Soil pH", ideal: "5.5–6.5", unit: "", icon: FlaskConical, color: GREEN,
    desc: (v: number) => v < 5.5 ? "Too acidic — apply lime" : v > 7.0 ? "Alkaline — add sulfur" : "Optimal for potatoes" },
  { key: "nitrogen_total", label: "Nitrogen (N)", ideal: "0.15–0.30%", unit: "%", icon: Sprout, color: GREEN,
    desc: (v: number) => v < 1.0 ? "Low — apply N top-dress" : v < 2.5 ? "Adequate" : "High — reduce N inputs" },
  { key: "carbon_total", label: "Total Carbon", ideal: "1.5–3.0%", unit: "%", icon: Mountain, color: GOLD,
    desc: (v: number) => v < 1.0 ? "Low organic matter" : v < 2.5 ? "Moderate" : "Good organic content" },
];

export default function SoilPage() {
  const router = useRouter();
  const [soil, setSoil] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const pid = localStorage.getItem("plotId");
    if (!pid) { router.push("/onboarding"); return; }
    fetch(`${API}/api/plot/${pid}/soil`)
      .then(r => r.json())
      .then(d => { setSoil(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ display: "flex", minHeight: "100dvh", alignItems: "center", justifyContent: "center", background: BG }}>
      <FlaskConical size={44} className="anim-pulse-soft" style={{ color: GREEN, opacity: 0.5 }} />
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100dvh", background: BG, paddingBottom: "calc(80px + var(--safe-bottom))" }}>
      <header style={{ position: "sticky", top: 0, zIndex: 10, background: BG, borderBottom: `1px solid ${BORDER}`, padding: "8px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <a href="/" style={{ width: 34, height: 34, borderRadius: 10, background: SURFACE, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", textDecoration: "none" }}>
            <ChevronLeft size={18} color={TEXT} />
          </a>
          <h1 style={{ fontSize: 17, fontWeight: 700, letterSpacing: "-0.02em", color: TEXT }}>Soil Analysis</h1>
        </div>
      </header>

      <main style={{ flex: 1, padding: "16px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
        {!soil ? (
          <div className="card" style={{ padding: 32, textAlign: "center" }}>
            <Mountain size={40} style={{ margin: "0 auto 12px", color: TEXT_SEC, opacity: 0.4 }} />
            <p style={{ fontSize: 13, color: TEXT_SEC }}>Soil data is being fetched from iSDAsoil. Run a diagnostic to populate.</p>
          </div>
        ) : (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
              {METRICS.map(({ key, label, icon: Icon, color, unit }) => (
                <div key={key} className="card anim-fade-up delay-1" style={{ padding: 16, textAlign: "center" }}>
                  <Icon size={20} style={{ marginBottom: 6, color }} />
                  <p style={{ fontSize: 20, fontWeight: 800, color: TEXT }}>{soil[key] ?? "—"}{unit}</p>
                  <p style={{ fontSize: 10, fontWeight: 600, color: TEXT_SEC }}>{label}</p>
                </div>
              ))}
            </div>

            <div className="card anim-fade-up delay-2" style={{ padding: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
                <div style={{ width: 4, height: 16, borderRadius: 2, background: GREEN }} />
                <span className="stat-label">Soil Health Assessment</span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {METRICS.map(({ key, label, ideal, icon: Icon, color, desc }) => {
                  const v = soil[key] || 0;
                  const barPct = key === "ph" ? Math.min(100, (v / 14) * 100) : Math.min(100, (v / 5) * 100);
                  return (
                    <div key={key} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <Icon size={14} color={color} />
                          <span style={{ fontSize: 12, fontWeight: 600, color: TEXT }}>{label}</span>
                        </div>
                        <span style={{ fontSize: 10, color: TEXT_SEC }}>Ideal: {ideal}</span>
                      </div>
                      <div style={{ height: 6, borderRadius: 3, background: BORDER, overflow: "hidden" }}>
                        <div style={{ height: "100%", borderRadius: 3, background: color, width: `${barPct}%`, transition: "width 0.6s ease" }} />
                      </div>
                      <p style={{ fontSize: 11, color: TEXT_SEC, margin: 0 }}>{desc(v)}</p>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="card anim-fade-up delay-3" style={{ padding: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <div style={{ width: 4, height: 16, borderRadius: 2, background: BLUE }} />
                <span className="stat-label">Data Source</span>
              </div>
              <p style={{ fontSize: 12, color: TEXT_SEC, lineHeight: 1.6 }}>
                Soil data is sourced from <strong style={{ color: TEXT }}>iSDAsoil</strong> at 30m resolution.
                GPS coordinates: {soil.latitude?.toFixed(4)}, {soil.longitude?.toFixed(4)}.
              </p>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
