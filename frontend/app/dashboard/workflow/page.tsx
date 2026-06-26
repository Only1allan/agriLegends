"use client";

import { useRouter } from "next/navigation";
import { ChevronLeft, Satellite, CloudSun, Leaf, Brain, ShieldCheck, ArrowDown, Sprout } from "lucide-react";

const BG = "#0d1f15";
const SURFACE = "#13291e";
const BORDER = "#1e3a2a";
const TEXT = "#e8e6dc";
const TEXT_SEC = "#8b9e8e";
const GREEN = "#4ade80";
const GOLD = "#d4a844";

const STEPS = [
  {
    icon: Satellite, label: "Satellite Data",
    desc: "Sentinel-2 satellite captures NDVI imagery every 3-5 days",
    detail: "Vegetation health index calculated from infrared reflectance"
  },
  {
    icon: CloudSun, label: "Weather Data",
    desc: "Temperature, rainfall, and humidity from AgroMonitoring API",
    detail: "Growing Degree Days (GDD) computed for potato development"
  },
  {
    icon: Leaf, label: "Knowledge Graph",
    desc: "Potato pest & disease profiles matched against conditions",
    detail: "4 growth stages, 5 pests, 7 interventions in the graph"
  },
  {
    icon: Brain, label: "AI Diagnostic",
    desc: "Featherless LLM synthesizes data into actionable advice",
    detail: "GraphRAG pipeline extracts subgraph → LLM translates → recommendation"
  },
  {
    icon: ShieldCheck, label: "Cardano Record",
    desc: "Decision logged on Cardano blockchain via Masumi",
    detail: "Real transaction hash — verifiable on Cardanoscan"
  },
];

export default function WorkflowPage() {
  const router = useRouter();

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100dvh", background: BG, paddingBottom: 96 }}>
      <header style={{ position: "sticky", top: 0, zIndex: 10, background: BG, borderBottom: `1px solid ${BORDER}`, padding: "12px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <a href="/" style={{ color: TEXT }}><ChevronLeft size={24} /></a>
          <h1 style={{ fontSize: 17, fontWeight: 700, letterSpacing: "-0.02em", color: TEXT }}>How It Works</h1>
        </div>
      </header>

      <main style={{ flex: 1, padding: "20px", display: "flex", flexDirection: "column", gap: 16 }}>
        <p style={{ fontSize: 13, lineHeight: 1.7, color: TEXT_SEC }}>
          FarmWise processes satellite and weather data through a pipeline that turns raw observations into a single actionable sentence — then records it on the Cardano blockchain.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {STEPS.map((step, i) => (
            <div key={step.label} style={{ position: "relative" }}>
              {i < STEPS.length - 1 && (
                <div style={{ position: "absolute", left: 27, top: 56, bottom: 0, width: 2, background: `linear-gradient(to bottom, ${GREEN}40, transparent)` }} />
              )}
              <div className="card" style={{ padding: 16 }}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
                  <div style={{ width: 56, height: 56, borderRadius: 12, background: "rgba(74, 222, 128, 0.1)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <step.icon size={24} color={GREEN} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <span style={{ width: 20, height: 20, borderRadius: "50%", background: GREEN, color: BG, fontSize: 10, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center" }}>{i + 1}</span>
                      <h3 style={{ fontSize: 14, fontWeight: 700, color: TEXT, margin: 0 }}>{step.label}</h3>
                    </div>
                    <p style={{ fontSize: 13, color: TEXT_SEC, margin: 0 }}>{step.desc}</p>
                    <p style={{ fontSize: 11, color: TEXT_SEC, marginTop: 4, opacity: 0.7 }}>{step.detail}</p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div style={{ background: "rgba(74, 222, 128, 0.08)", border: `1px solid rgba(74, 222, 128, 0.2)`, borderRadius: 16, padding: 16 }}>
          <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: GREEN, marginBottom: 6 }}>The Result</p>
          <p style={{ fontSize: 13, lineHeight: 1.6, color: TEXT }}>
            Each morning, farmers receive one clear sentence: <span style={{ fontWeight: 600, color: GREEN }}>"Spray mancozeb fungicide within 48 hours — late blight risk at tuber bulking."</span>
          </p>
        </div>
      </main>
    </div>
  );
}
