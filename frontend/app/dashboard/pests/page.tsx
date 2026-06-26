"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, Bug, AlertTriangle, Shield, Clock, Thermometer } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const BG = "#0d1f15";
const SURFACE = "#13291e";
const BORDER = "#1e3a2a";
const TEXT = "#e8e6dc";
const TEXT_SEC = "#8b9e8e";
const GREEN = "#4ade80";
const RED = "#f87171";
const GOLD = "#d4a844";

export default function PestsPage() {
  const router = useRouter();
  const [pests, setPests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const pid = localStorage.getItem("plotId");
    if (!pid) { router.push("/onboarding"); return; }
    fetch(`${API}/api/diagnostic/pest-check/${pid}`)
      .then(r => r.json())
      .then(d => { setPests(d ?? []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ display: "flex", minHeight: "100dvh", alignItems: "center", justifyContent: "center", background: BG }}>
      <Bug size={44} className="anim-pulse-soft" style={{ color: GREEN, opacity: 0.5 }} />
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100dvh", background: BG, paddingBottom: "calc(80px + var(--safe-bottom))" }}>
      <header style={{ position: "sticky", top: 0, zIndex: 10, background: BG, borderBottom: `1px solid ${BORDER}`, padding: "8px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <a href="/" style={{ width: 34, height: 34, borderRadius: 10, background: SURFACE, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", textDecoration: "none" }}>
            <ChevronLeft size={18} color={TEXT} />
          </a>
          <h1 style={{ fontSize: 17, fontWeight: 700, letterSpacing: "-0.02em", color: TEXT }}>Pest &amp; Disease</h1>
        </div>
      </header>

      <main style={{ flex: 1, padding: "16px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
        {/* Status */}
        <div className="card anim-fade-up delay-1" style={{ padding: 20, textAlign: "center" }}>
          {pests.length === 0 ? (
            <>
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: "rgba(74,222,128,0.1)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 12px" }}>
                <Shield size={32} color={GREEN} />
              </div>
              <p style={{ fontSize: 18, fontWeight: 700, color: GREEN }}>No Pest Risks Detected</p>
              <p style={{ fontSize: 13, color: TEXT_SEC, marginTop: 4 }}>Current weather conditions don&apos;t match known pest thresholds.</p>
            </>
          ) : (
            <>
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: "rgba(248,113,113,0.1)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 12px" }}>
                <Bug size={32} color={RED} />
              </div>
              <p style={{ fontSize: 18, fontWeight: 700, color: RED }}>{pests.length} Active Risk{pests.length > 1 ? "s" : ""}</p>
              <p style={{ fontSize: 13, color: TEXT_SEC, marginTop: 4 }}>Weather conditions matched — intervention needed</p>
            </>
          )}
        </div>

        {/* Pest list */}
        {pests.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <span className="stat-label">Active Pest Risks</span>
            {pests.map((p, i) => (
              <div key={i} className="card anim-fade-up" style={{ padding: 16, borderLeft: `4px solid ${RED}`, animationDelay: `${0.2 + i * 0.05}s` }}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                  <div style={{ width: 40, height: 40, borderRadius: 10, background: "rgba(248,113,113,0.1)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <Bug size={20} color={RED} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div>
                        <p style={{ fontSize: 14, fontWeight: 700, color: TEXT, margin: 0 }}>{p.cause}</p>
                        <p style={{ fontSize: 11, color: TEXT_SEC, margin: "2px 0 0", fontStyle: "italic" }}>{p.scientific}</p>
                      </div>
                      <span style={{ fontSize: 10, fontWeight: 600, background: "rgba(248,113,113,0.1)", color: RED, padding: "4px 10px", borderRadius: 9999, flexShrink: 0 }}>{p.stage}</span>
                    </div>

                    <div style={{ marginTop: 10, padding: 10, background: "rgba(74,222,128,0.06)", borderRadius: 10, border: `1px solid ${BORDER}` }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                        <Clock size={12} color={GREEN} />
                        <span style={{ fontSize: 11, fontWeight: 700, color: GREEN }}>Recommended Action</span>
                      </div>
                      <p style={{ fontSize: 12, fontWeight: 600, color: TEXT, margin: 0 }}>{p.action}</p>
                      <p style={{ fontSize: 11, color: TEXT_SEC, margin: "2px 0 0" }}>{p.method}</p>
                      <p style={{ fontSize: 10, fontWeight: 700, color: GOLD, margin: "6px 0 0" }}>
                        Urgency: {p.urgencyHours}h
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Info card */}
        <div className="card anim-fade-up delay-2" style={{ padding: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <div style={{ width: 4, height: 16, borderRadius: 2, background: GOLD }} />
            <span className="stat-label">How Pest Detection Works</span>
          </div>
          <p style={{ fontSize: 12, color: TEXT_SEC, lineHeight: 1.6 }}>
            Our <strong style={{ color: TEXT }}>knowledge graph</strong> matches your plot&apos;s current growth stage and weather conditions against pest thresholds. When temperature, humidity, and precipitation align with pest-thriving conditions, risks are flagged with scientific intervention recommendations.
          </p>
        </div>
      </main>
    </div>
  );
}
