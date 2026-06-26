"use client";

import { useRouter } from "next/navigation";
import { Sprout, Satellite, ShieldCheck, Brain, CloudSun, ArrowRight, Leaf, BarChart3 } from "lucide-react";

export default function LandingPage() {
  const router = useRouter();

  return (
    <div style={{ background: "#0d1f15", minHeight: "100dvh", color: "#e8e6dc" }}>

      {/* Hero */}
      <div style={{
        display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
        minHeight: "100dvh", padding: "20px", textAlign: "center",
        background: "radial-gradient(ellipse at 50% 30%, rgba(74,222,128,0.08) 0%, transparent 60%), #0d1f15",
      }}>

        <div style={{ marginBottom: 8 }}>
          <div style={{
            width: 72, height: 72, borderRadius: 22, background: "linear-gradient(135deg, #4ade80, #22c55e)",
            display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px",
            boxShadow: "0 8px 32px rgba(74,222,128,0.2)",
          }}>
            <Sprout size={36} color="#0d1f15" />
          </div>
          <h1 style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 42, fontWeight: 700, letterSpacing: "-0.03em", lineHeight: 1.1, margin: 0 }}>
            Your Potato Farm,<br />Powered by <span style={{ color: "#4ade80" }}>Satellites</span>
          </h1>
        </div>

        <p style={{ fontSize: 17, color: "#8b9e8e", maxWidth: 320, lineHeight: 1.6, margin: "16px 0 32px" }}>
          AI-powered crop monitoring that gives you one clear action every day — verified on the Cardano blockchain.
        </p>

        <button onClick={() => router.push("/onboarding")}
          style={{
            background: "linear-gradient(135deg, #4ade80, #22c55e)", color: "#0d1f15", border: "none",
            borderRadius: 16, padding: "16px 36px", fontSize: 16, fontWeight: 700, cursor: "pointer",
            display: "flex", alignItems: "center", gap: 10, letterSpacing: "-0.01em",
            boxShadow: "0 4px 24px rgba(74,222,128,0.15)",
          }}>
          Get Started <ArrowRight size={20} />
        </button>

        <button onClick={async () => {
          try {
            const r = await fetch("http://localhost:8000/api/demo/credentials");
            const d = await r.json();
            localStorage.setItem("farmerId", d.farmerId);
            localStorage.setItem("plotId", d.plotId);
            window.location.href = "/";
          } catch {}
        }}
          style={{
            background: "transparent", color: "#4ade80", border: "1px solid rgba(74,222,128,0.3)",
            borderRadius: 16, padding: "14px 32px", fontSize: 14, fontWeight: 600, cursor: "pointer",
            marginTop: 12, letterSpacing: "-0.01em",
          }}>
          Try Demo
        </button>

        {/* Feature pills */}
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 10, marginTop: 48 }}>
          {[
            { icon: Satellite, label: "Satellite NDVI" },
            { icon: CloudSun, label: "Live Weather" },
            { icon: Brain, label: "AI Diagnosis" },
            { icon: ShieldCheck, label: "Cardano Verified" },
          ].map(({ icon: Icon, label }) => (
            <div key={label} style={{
              display: "flex", alignItems: "center", gap: 8,
              background: "rgba(255,255,255,0.04)", borderRadius: 12, padding: "10px 16px",
              border: "1px solid rgba(255,255,255,0.06)",
            }}>
              <Icon size={16} color="#4ade80" />
              <span style={{ fontSize: 13, fontWeight: 500, color: "#8b9e8e" }}>{label}</span>
            </div>
          ))}
        </div>

        {/* How it works */}
        <div style={{ marginTop: 56, maxWidth: 340, textAlign: "left" }}>
          <p style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "#5a6e5e", marginBottom: 16, textAlign: "center" }}>
            How It Works
          </p>
          {[
            { step: "1", title: "Register Your Farm", desc: "Enter your plot location and details — we handle the rest." },
            { step: "2", title: "We Monitor Daily", desc: "Satellites, weather stations, and soil data run 24/7." },
            { step: "3", title: "Get One Clear Action", desc: "Every morning: spray, irrigate, or wait — one sentence." },
            { step: "4", title: "Verify on Blockchain", desc: "Every recommendation is logged on Cardano — shareable." },
          ].map(({ step, title, desc }) => (
            <div key={step} style={{ display: "flex", gap: 14, marginBottom: 18 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10, background: "rgba(74,222,128,0.1)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 14, fontWeight: 700, color: "#4ade80", flexShrink: 0,
              }}>{step}</div>
              <div>
                <p style={{ fontSize: 15, fontWeight: 600, margin: "0 0 2px", color: "#e8e6dc" }}>{title}</p>
                <p style={{ fontSize: 13, color: "#7a937e", margin: 0, lineHeight: 1.4 }}>{desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Trust badges */}
        <div style={{ marginTop: 48, display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap", justifyContent: "center" }}>
          {[
            "Sentinel-2 Satellite", "Cardano Blockchain", "AgroMonitoring", "iSDAsoil", "Featherless AI",
          ].map(name => (
            <span key={name} style={{ fontSize: 11, color: "#5a6e5e", fontWeight: 500 }}>{name}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
