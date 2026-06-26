"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, ExternalLink, Sprout, CheckCircle, Calendar } from "lucide-react";

const API = "";

interface Cert { farmerId: string; plotId: string; plotName: string; variety: string; seasonDay: number; recommendationAction: string; recommendationCause: string; recommendationNarrative: string; recommendationDate: string; stressEventsResolved: number; currentYieldForecastKg: number; masumiTxHash: string | null; verified: boolean; }

export default function CertificatePage() {
  const router = useRouter();
  const [c, setC] = useState<Cert | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fid = localStorage.getItem("farmerId"); if (!fid) { router.push("/onboarding"); return; }
    const pid = localStorage.getItem("plotId");
    const go = (p: string) => fetch(`${API}/api/plot/${p}/certificate`).then(r => r.json()).then(d => { setC(d); setLoading(false); }).catch(() => setLoading(false));
    if (pid) { go(pid); return; }
    fetch(`${API}/api/farmer/${fid}`).then(r => r.json()).then(f => { const p = f.plots?.[0]?.plotId; if (p) { localStorage.setItem("plotId", p); go(p); } }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ display: "flex", minHeight: "100dvh", alignItems: "center", justifyContent: "center", background: "#0d1f15" }}><Sprout size={36} color="#4ade80" style={{ opacity: 0.3 }} /></div>;

  if (!c?.recommendationAction) return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100dvh", alignItems: "center", justifyContent: "center", background: "#0d1f15", padding: 20 }}>
      <div className="panel" style={{ maxWidth: 300, textAlign: "center" }}>
        <Sprout size={40} color="#7a937e" style={{ margin: "0 auto 12px" }} />
        <p style={{ fontSize: 17, fontWeight: 700, color: "#e8e6dc", margin: "0 0 4px" }}>No Certificate Yet</p>
        <p style={{ fontSize: 13, color: "#7a937e", margin: "0 0 16px" }}>Run the diagnostic to generate your first verifiable record.</p>
        <a href="/" style={{ display: "inline-block", textDecoration: "none", background: "linear-gradient(135deg, #4ade80, #22c55e)", color: "#0d1f15", borderRadius: 14, padding: "10px 24px", fontSize: 13, fontWeight: 700 }}>Go Home</a>
      </div>
    </div>
  );

  const explorer = c.masumiTxHash ? `https://preprod.cardanoscan.io/transaction/${c.masumiTxHash}` : null;

  return (
    <div style={{ background: "#0d1f15", minHeight: "100dvh", paddingBottom: "calc(80px + var(--safe-bottom))" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "14px 18px 10px", paddingTop: "calc(14px + var(--safe-top))" }}>
        <a href="/" style={{ width: 30, height: 30, borderRadius: 8, background: "#13291e", border: "1px solid #1e3a2a", display: "flex", alignItems: "center", justifyContent: "center", textDecoration: "none" }}>
          <ChevronLeft size={16} color="#e8e6dc" />
        </a>
        <h1 style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-0.03em", color: "#e8e6dc", margin: 0 }}>Certificate</h1>
      </div>

      <main style={{ padding: "0 18px 16px", display: "flex", flexDirection: "column", gap: 14 }}>

        <div className="panel anim-slide sd1" style={{ overflow: "hidden" }}>
          <div style={{ height: 4, background: c.verified ? "linear-gradient(90deg, #4ade80, #22c55e, #4ade80)" : "linear-gradient(90deg, #2a3a2e, #1e2e22, #2a3a2e)", margin: "-20px -20px 0" }} />

          <div style={{ paddingTop: 16 }}>
            {/* Header + Verified stamp */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 18 }}>
              <div>
                <p style={{ fontSize: 14, fontWeight: 700, color: "#e8e6dc", margin: 0 }}>FarmWise Production Record</p>
                <p style={{ fontSize: 11, color: "#7a937e", margin: "2px 0 0" }}>Verified on Cardano</p>
              </div>
              <div style={{ textAlign: "center" }}>
                <div style={{ width: 46, height: 46, borderRadius: "50%", border: c.verified ? "2px solid #4ade80" : "2px solid #3a4a3e", display: "flex", alignItems: "center", justifyContent: "center", background: c.verified ? "rgba(74,222,128,0.1)" : "rgba(122,147,126,0.05)" }}>
                  <CheckCircle size={24} color={c.verified ? "#4ade80" : "#5a6a5e"} />
                </div>
                <span style={{ fontSize: 7, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.08em", color: c.verified ? "#4ade80" : "#5a6a5e", marginTop: 2, display: "block" }}>
                  {c.verified ? "Verified" : "Pending"}
                </span>
              </div>
            </div>

            {/* Plot details */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 16px", padding: 12, background: "rgba(255,255,255,0.02)", borderRadius: 10, marginBottom: 14 }}>
              {[
                ["Plot", c.plotName], ["Variety", c.variety],
                ["Season", `Day ${c.seasonDay}`], ["Farmer", `${c.farmerId.slice(0,10)}...`],
              ].map(([l, v]) => (
                <div key={l}>
                  <span style={{ fontSize: 9, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "#7a937e" }}>{l}</span>
                  <p style={{ fontSize: 12, fontWeight: 600, color: "#e8e6dc", margin: "1px 0 0" }}>{v}</p>
                </div>
              ))}
            </div>

            {/* Recommendation */}
            <div style={{ padding: 12, background: "rgba(74,222,128,0.05)", borderRadius: 10, border: "1px solid rgba(74,222,128,0.1)", marginBottom: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                <Calendar size={12} color="#4ade80" />
                <span style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "#4ade80" }}>{c.recommendationDate} Recommendation</span>
              </div>
              <p style={{ fontSize: 13, lineHeight: 1.5, color: "#d8d6cc", margin: 0 }}>{c.recommendationNarrative}</p>
              <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
                <span style={{ fontSize: 10, fontWeight: 700, background: "#4ade80", color: "#0d1f15", borderRadius: 9999, padding: "2px 10px" }}>{c.recommendationAction}</span>
                <span style={{ fontSize: 10, fontWeight: 600, color: "#4ade80", borderRadius: 9999, padding: "2px 10px", border: "1px solid rgba(74,222,128,0.3)" }}>{c.recommendationCause}</span>
              </div>
            </div>

            {/* Stats */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
              {[
                [c.stressEventsResolved, "Alerts Resolved"],
                [c.currentYieldForecastKg.toLocaleString(), "Yield (kg)"],
              ].map(([v, l]) => (
                <div key={l} style={{ background: "rgba(255,255,255,0.02)", borderRadius: 10, padding: 10, textAlign: "center" }}>
                  <p style={{ fontSize: 18, fontWeight: 700, color: "#4ade80", margin: 0 }}>{v}</p>
                  <p style={{ fontSize: 10, color: "#7a937e", margin: "2px 0 0" }}>{l}</p>
                </div>
              ))}
            </div>

            {/* TX hash */}
            {c.masumiTxHash && (
              <div style={{ padding: 12, background: c.verified ? "rgba(74,222,128,0.05)" : "rgba(255,255,255,0.02)", borderRadius: 10, border: c.verified ? "1px solid rgba(74,222,128,0.15)" : "1px solid #1e3a2a" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                  <span style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "#7a937e" }}>Cardano Transaction</span>
                  {c.verified && <span style={{ fontSize: 7, fontWeight: 800, background: "#4ade80", color: "#0d1f15", borderRadius: 9999, padding: "2px 8px", letterSpacing: "0.06em" }}>ON-CHAIN</span>}
                </div>
                <p style={{ fontFamily: "monospace", fontSize: 10, color: "#7a937e", wordBreak: "break-all", background: "rgba(255,255,255,0.03)", borderRadius: 8, padding: 8, margin: "0 0 8px" }}>{c.masumiTxHash}</p>
                {explorer && (
                  <a href={explorer} target="_blank" rel="noopener noreferrer"
                    style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "linear-gradient(135deg, #4ade80, #22c55e)", color: "#0d1f15", borderRadius: 10, padding: "8px 16px", fontSize: 12, fontWeight: 700, textDecoration: "none" }}>
                    <ExternalLink size={13} /> Verify on Cardanoscan
                  </a>
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
