"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Sprout, RefreshCw, Leaf, TrendingUp, Thermometer, ShieldCheck, MessageCircle, Calendar, BarChart3, CloudSun, ChevronRight, Zap, Mountain, AlertTriangle, Bug, Camera, User } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function DashboardPage() {
  const router = useRouter();
  const [farmer, setFarmer] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    const fid = localStorage.getItem("farmerId");
    if (!fid) { router.push("/onboarding"); return; }
    fetch(`${API}/api/farmer/${fid}`).then(r => r.json()).then(d => { setFarmer(d); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  const diagnose = useCallback(async () => {
    const pid = localStorage.getItem("plotId");
    if (!pid) return;
    setRunning(true);
    try {
      await fetch(`${API}/api/diagnostic/run`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ plotId: pid }) });
      const fid = localStorage.getItem("farmerId");
      if (fid) { const r = await fetch(`${API}/api/farmer/${fid}`); const d = await r.json(); setFarmer(d); }
    } catch {}
    setRunning(false);
  }, []);

  if (loading) return (
    <div style={{ display: "flex", minHeight: "100dvh", alignItems: "center", justifyContent: "center", background: "#0d1f15" }}>
      <Sprout size={36} color="#4ade80" style={{ opacity: 0.3 }} />
    </div>
  );

  const plot = farmer?.plots?.[0];
  const s: any = { background: "#13291e", borderRadius: 14, border: "1px solid #1e3a2a", padding: 16 };
  const met = { fontSize: 22, fontWeight: 700, fontFamily: "'Cormorant Garamond', serif", margin: 0, color: "#e8e6dc" };
  const lab = { fontSize: 10, fontWeight: 600, color: "#8b9e8e", textTransform: "uppercase" as any, letterSpacing: "0.04em", margin: "4px 0 0" };

  return (
    <div style={{ background: "#0d1f15", minHeight: "100dvh", paddingBottom: "calc(80px + env(safe-area-inset-bottom,0px))" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 18px 10px", paddingTop: "calc(14px + env(safe-area-inset-top,0px))", background: "rgba(13,31,21,0.9)", backdropFilter: "blur(20px)", position: "sticky", top: 0, zIndex: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 32, height: 32, borderRadius: 9, background: "linear-gradient(135deg,#4ade80,#22c55e)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Sprout size={18} color="#0d1f15" />
          </div>
          <div>
            <span style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-0.02em", color: "#e8e6dc" }}>FarmWise</span>
            {plot && <p style={{ fontSize: 10, color: "#8b9e8e", margin: 0 }}>{plot.name} &middot; Day {plot.seasonDay}</p>}
          </div>
        </div>
        <button onClick={diagnose} disabled={running}
          style={{ display: "flex", alignItems: "center", gap: 6, background: "linear-gradient(135deg,#4ade80,#22c55e)", color: "#0d1f15", border: "none", borderRadius: 20, padding: "8px 16px", fontSize: 12, fontWeight: 700, cursor: "pointer", letterSpacing: "-0.01em" }}>
          <RefreshCw size={14} className={running ? "anim-slide" : ""} />
          {running ? "Running" : "Diagnose"}
        </button>
      </div>

      <main style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 12 }}>
        {/* Greeting + metrics */}
        <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
          <h1 style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 26, fontWeight: 700, letterSpacing: "-0.03em", color: "#e8e6dc", margin: "0 0 2px" }}>
            {farmer?.name?.split(" ")[0] || "Farmer"}
          </h1>
        </div>

        {/* KPI Row */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 1, background: "#1e3a2a", borderRadius: 14, overflow: "hidden" }}>
          {[
            { v: plot?.stage || "—", l: "Stage" },
            { v: `Day ${plot?.seasonDay || "—"}`, l: "Season" },
            { v: `${(plot?.forecastedYieldKg || 0).toLocaleString()} kg`, l: "Yield" },
          ].map(({ v, l }) => (
            <div key={l} style={{ background: "#13291e", padding: "14px 8px", textAlign: "center" }}>
              <p style={met}>{v}</p>
              <p style={lab}>{l}</p>
            </div>
          ))}
        </div>

        {/* Today's Advice */}
        <div style={{ ...s, borderLeft: "4px solid #4ade80" }}>
          <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
            <CloudSun size={18} color="#4ade80" style={{ flexShrink: 0, marginTop: 1 }} />
            {plot?.todayRecommendation ? (
              <p style={{ fontSize: 14, lineHeight: 1.5, color: "#d8d6cc", margin: 0 }}>{plot.todayRecommendation}</p>
            ) : (
              <div>
                <p style={{ fontSize: 13, color: "#8b9e8e", margin: "0 0 10px" }}>No advice yet. Tap Diagnose to get your first recommendation.</p>
                <button onClick={diagnose} disabled={running}
                  style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "linear-gradient(135deg,#4ade80,#22c55e)", color: "#0d1f15", border: "none", borderRadius: 12, padding: "8px 16px", fontSize: 12, fontWeight: 700, cursor: "pointer" }}>
                  <Zap size={14} /> {running ? "Analyzing..." : "Run Diagnostic"}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Tools Grid */}
        <div>
          <p style={{ fontSize: 11, fontWeight: 600, color: "#8b9e8e", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 8px 2px", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 3, height: 10, borderRadius: 2, background: "#4ade80" }} /> Quick Actions
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {[
              { href: "/dashboard/growth", icon: Leaf, label: "Growth Stage", desc: "Progress & timeline", c: "#4ade80" },
              { href: "/dashboard/health", icon: BarChart3, label: "Plot Health", desc: "NDVI analysis", c: "#4ade80" },
              { href: "/dashboard/weather", icon: Thermometer, label: "Weather", desc: "Temp & rainfall", c: "#60a5fa" },
              { href: "/dashboard/soil", icon: Mountain, label: "Soil Data", desc: "iSDAsoil analysis", c: "#d4a844" },
              { href: "/dashboard/stress", icon: AlertTriangle, label: "Stress Detection", desc: "NDVI anomalies", c: "#f87171" },
              { href: "/dashboard/pests", icon: Bug, label: "Pests & Disease", desc: "Risk diagnosis", c: "#f59e0b" },
              { href: "/dashboard/yield", icon: TrendingUp, label: "Yield Forecast", desc: "Estimated harvest", c: "#d4a844" },
              { href: "/dashboard/tracker", icon: Calendar, label: "Action Tracker", desc: "Compliance log", c: "#a78bfa" },
              { href: "/dashboard/certificate", icon: ShieldCheck, label: "Certificate", desc: "On-chain verified", c: "#4ade80" },
              { href: "/dashboard/ground-truth", icon: Camera, label: "Ground Truth", desc: "Your farm data", c: "#d4a844" },
              { href: "/dashboard/profile", icon: User, label: "My Profile", desc: "Account & history", c: "#60a5fa" },
              { href: "/chat", icon: MessageCircle, label: "Ask AI", desc: "Chat assistant", c: "#4ade80" },
            ].map(({ href, icon: Icon, label, desc, c }) => (
              <a key={href} href={href} style={{ textDecoration: "none" }}>
                <div style={{ ...s, display: "flex", alignItems: "center", gap: 12, padding: "12px 14px" }}>
                  <div style={{ width: 36, height: 36, borderRadius: 10, background: c + "15", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <Icon size={18} color={c} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: 13, fontWeight: 600, color: "#e8e6dc", margin: 0 }}>{label}</p>
                    <p style={{ fontSize: 11, color: "#8b9e8e", margin: "1px 0 0" }}>{desc}</p>
                  </div>
                  <ChevronRight size={14} color="#5a6e5e" />
                </div>
              </a>
            ))}
          </div>
        </div>
      </main>

      {/* Bottom Nav */}
      <nav style={{ position: "fixed", bottom: 0, left: 0, right: 0, background: "rgba(13,31,21,0.9)", backdropFilter: "blur(20px)", borderTop: "1px solid #1e3a2a", padding: "6px 0 4px", paddingBottom: "calc(4px + env(safe-area-inset-bottom,0px))" }}>
        <div style={{ display: "flex", justifyContent: "space-around", maxWidth: 400, margin: "0 auto" }}>
          {[
            { href: "/home", icon: Sprout, label: "Home" },
            { href: "/dashboard/growth", icon: Leaf, label: "Growth" },
            { href: "/dashboard/health", icon: BarChart3, label: "Health" },
            { href: "/chat", icon: MessageCircle, label: "Chat" },
            { href: "/dashboard/certificate", icon: ShieldCheck, label: "Verify" },
          ].map(({ href, icon: Icon, label }) => (
            <a key={href} href={href} style={{ textDecoration: "none", display: "flex", flexDirection: "column", alignItems: "center", gap: 2, padding: "4px 12px", fontSize: 9, fontWeight: 600, color: "#8b9e8e" }}>
              <Icon size={20} />{label}
            </a>
          ))}
        </div>
      </nav>
    </div>
  );
}
