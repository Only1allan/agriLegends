"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, AlertTriangle, Activity, TrendingDown } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const BG = "#0d1f15";
const SURFACE = "#13291e";
const BORDER = "#1e3a2a";
const TEXT = "#e8e6dc";
const TEXT_SEC = "#8b9e8e";
const GREEN = "#4ade80";
const RED = "#f87171";
const GOLD = "#d4a844";

export default function StressPage() {
  const router = useRouter();
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const pid = localStorage.getItem("plotId");
    if (!pid) { router.push("/onboarding"); return; }
    fetch(`${API}/api/plot/${pid}/stress`)
      .then(r => r.json())
      .then(d => { setEvents(d ?? []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ display: "flex", minHeight: "100dvh", alignItems: "center", justifyContent: "center", background: BG }}>
      <Activity size={44} className="anim-pulse-soft" style={{ color: GREEN, opacity: 0.5 }} />
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100dvh", background: BG, paddingBottom: "calc(80px + var(--safe-bottom))" }}>
      <header style={{ position: "sticky", top: 0, zIndex: 10, background: BG, borderBottom: `1px solid ${BORDER}`, padding: "8px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <a href="/" style={{ width: 34, height: 34, borderRadius: 10, background: SURFACE, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", textDecoration: "none" }}>
            <ChevronLeft size={18} color={TEXT} />
          </a>
          <h1 style={{ fontSize: 17, fontWeight: 700, letterSpacing: "-0.02em", color: TEXT }}>Stress Detection</h1>
        </div>
      </header>

      <main style={{ flex: 1, padding: "16px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
        {/* Status Card */}
        <div className="card anim-fade-up delay-1" style={{ padding: 20, textAlign: "center" }}>
          {events.length === 0 ? (
            <>
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: "rgba(74,222,128,0.1)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 12px" }}>
                <Activity size={32} color={GREEN} />
              </div>
              <p style={{ fontSize: 18, fontWeight: 700, color: GREEN }}>No Stress Detected</p>
              <p style={{ fontSize: 13, color: TEXT_SEC, marginTop: 4 }}>Your crop is healthy. No NDVI anomalies found.</p>
            </>
          ) : (
            <>
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: "rgba(248,113,113,0.1)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 12px" }}>
                <AlertTriangle size={32} color={RED} />
              </div>
              <p style={{ fontSize: 18, fontWeight: 700, color: RED }}>{events.length} Stress Event{events.length > 1 ? "s" : ""}</p>
              <p style={{ fontSize: 13, color: TEXT_SEC, marginTop: 4 }}>NDVI drop detected — action required</p>
            </>
          )}
        </div>

        {/* Stress Events List */}
        {events.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <span className="stat-label">Event History</span>
            {events.map((ev, i) => {
              const drop = ev.baselineNdvi && ev.currentNdvi
                ? Math.round((ev.baselineNdvi - ev.currentNdvi) * 100) / 100
                : null;
              return (
                <div key={i} className="card anim-fade-up" style={{ padding: 14, borderLeft: `4px solid ${RED}`, animationDelay: `${0.2 + i * 0.05}s` }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <TrendingDown size={20} color={RED} style={{ flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: 13, fontWeight: 700, color: TEXT }}>{ev.type || "NDVI Stress"}</span>
                        <span style={{ fontSize: 10, fontWeight: 600, color: RED, background: "rgba(248,113,113,0.1)", padding: "2px 8px", borderRadius: 9999 }}>
                          {ev.date?.slice(0, 10)}
                        </span>
                      </div>
                      {drop !== null && (
                        <div style={{ marginTop: 4, display: "flex", gap: 12 }}>
                          <span style={{ fontSize: 11, color: TEXT_SEC }}>Baseline: <strong style={{ color: TEXT }}>{ev.baselineNdvi}</strong></span>
                          <span style={{ fontSize: 11, color: TEXT_SEC }}>Current: <strong style={{ color: RED }}>{ev.currentNdvi}</strong></span>
                          <span style={{ fontSize: 11, color: TEXT_SEC }}>Drop: <strong style={{ color: RED }}>{drop.toFixed(2)}</strong></span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* How It Works */}
        <div className="card anim-fade-up delay-2" style={{ padding: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <div style={{ width: 4, height: 16, borderRadius: 2, background: GOLD }} />
            <span className="stat-label">How Detection Works</span>
          </div>
          <p style={{ fontSize: 12, color: TEXT_SEC, lineHeight: 1.6 }}>
            FarmWise runs a <strong style={{ color: TEXT }}>14-day rolling NDVI baseline</strong> analysis. If the latest NDVI drops more than 15% below the 14-day average, a stress event is created. This catches drought, disease, and pest damage early.
          </p>
        </div>
      </main>
    </div>
  );
}
