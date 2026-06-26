"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, Camera, Upload, Bug, Calendar, TrendingUp, MessageSquare, Clock, Sprout, Shield, Check } from "lucide-react";

const API = "";

const BG = "#0d1f15";
const SURFACE = "#13291e";
const BORDER = "#1e3a2a";
const TEXT = "#e8e6dc";
const TEXT_SEC = "#8b9e8e";
const GREEN = "#4ade80";
const GOLD = "#d4a844";
const RED = "#f87171";
const BLUE = "#60a5fa";

export default function GroundTruthPage() {
  const router = useRouter();
  const [farmerId, setFarmerId] = useState("");
  const [activeTab, setActiveTab] = useState(0);

  const [pestPhoto, setPestPhoto] = useState("");
  const [pestPhotoB64, setPestPhotoB64] = useState("");
  const [pestDesc, setPestDesc] = useState("");
  const [pestDate, setPestDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [pestSubmitting, setPestSubmitting] = useState(false);
  const [pestFeedback, setPestFeedback] = useState("");

  const [yieldKg, setYieldKg] = useState("");
  const [yieldAcres, setYieldAcres] = useState("");
  const [yieldVariety, setYieldVariety] = useState("Shangi");
  const [yieldDate, setYieldDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [yieldSubmitting, setYieldSubmitting] = useState(false);
  const [yieldFeedback, setYieldFeedback] = useState("");

  const [obsText, setObsText] = useState("");
  const [obsPhoto, setObsPhoto] = useState("");
  const [obsPhotoB64, setObsPhotoB64] = useState("");
  const [obsSubmitting, setObsSubmitting] = useState(false);
  const [obsFeedback, setObsFeedback] = useState("");

  const [logs, setLogs] = useState<any[]>([]);
  const [logsLoading, setLogsLoading] = useState(true);

  useEffect(() => {
    const fid = localStorage.getItem("farmerId");
    if (!fid) { router.push("/onboarding"); return; }
    setFarmerId(fid);
    fetchLogs(fid);
  }, []);

  const fetchLogs = async (fid: string) => {
    setLogsLoading(true);
    try {
      const r = await fetch(`${API}/api/farmer/${fid}/ground-truth`);
      const d = await r.json();
      setLogs(d ?? []);
    } catch {}
    setLogsLoading(false);
  };

  const toBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve((reader.result as string).split(",")[1]);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };

  const handlePestPhoto = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const b64 = await toBase64(file);
      setPestPhotoB64(b64);
      setPestPhoto(URL.createObjectURL(file));
    } catch {}
  }, []);

  const handleObsPhoto = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const b64 = await toBase64(file);
      setObsPhotoB64(b64);
      setObsPhoto(URL.createObjectURL(file));
    } catch {}
  }, []);

  const submitPestSighting = async () => {
    setPestSubmitting(true);
    setPestFeedback("");
    try {
      const r = await fetch(`${API}/api/farmer/${farmerId}/ground-truth`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "pest_sighting",
          text: pestDesc,
          imageBase64: pestPhotoB64 || undefined,
          metadata: { date: pestDate },
        }),
      });
      const d = await r.json();
      setPestFeedback(d.classification ? `Classified as: ${d.classification} (${Math.round(d.confidence * 100)}% confidence)` : "Recorded successfully!");
      setPestPhoto(""); setPestPhotoB64(""); setPestDesc("");
      fetchLogs(farmerId);
    } catch {
      setPestFeedback("Failed to submit. Try again.");
    }
    setPestSubmitting(false);
  };

  const submitYield = async () => {
    if (!yieldKg) return;
    setYieldSubmitting(true);
    setYieldFeedback("");
    try {
      await fetch(`${API}/api/farmer/${farmerId}/ground-truth`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "yield_report",
          text: `${yieldKg}kg from ${yieldAcres || "?"} acres of ${yieldVariety}`,
          metadata: { kg: parseFloat(yieldKg), acres: parseFloat(yieldAcres), variety: yieldVariety, date: yieldDate },
        }),
      });
      setYieldFeedback("Yield recorded successfully!");
      setYieldKg(""); setYieldAcres(""); setYieldDate(new Date().toISOString().split("T")[0]);
      fetchLogs(farmerId);
    } catch {
      setYieldFeedback("Failed to submit.");
    }
    setYieldSubmitting(false);
  };

  const submitObservation = async () => {
    if (!obsText.trim()) return;
    setObsSubmitting(true);
    setObsFeedback("");
    try {
      await fetch(`${API}/api/farmer/${farmerId}/ground-truth`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "farmer_observation",
          text: obsText,
          imageBase64: obsPhotoB64 || undefined,
        }),
      });
      setObsFeedback("Observation recorded!");
      setObsText(""); setObsPhoto(""); setObsPhotoB64("");
      fetchLogs(farmerId);
    } catch {
      setObsFeedback("Failed to submit.");
    }
    setObsSubmitting(false);
  };

  const inputStyle: React.CSSProperties = {
    width: "100%", background: "rgba(255,255,255,0.03)", border: `1px solid ${BORDER}`,
    borderRadius: 12, padding: "12px 14px", fontSize: 14, color: TEXT, outline: "none",
    fontFamily: "'DM Sans', sans-serif", boxSizing: "border-box"
  };
  const labelStyle: React.CSSProperties = {
    fontSize: 11, fontWeight: 600, color: TEXT_SEC, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6, display: "block"
  };
  const btnStyle: React.CSSProperties = {
    background: "linear-gradient(135deg, #4ade80, #22c55e)", border: "none", borderRadius: 12, padding: "12px 20px",
    fontSize: 13, fontWeight: 700, color: "#0d1f15", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6
  };
  const photoBtnStyle: React.CSSProperties = {
    display: "flex", alignItems: "center", justifyContent: "center", gap: 8, width: "100%",
    background: "rgba(212,168,68,0.06)", border: `1px dashed ${GOLD}44`, borderRadius: 12,
    padding: "20px", cursor: "pointer", textAlign: "center" as const
  };

  const tabs = [
    { icon: Bug, label: "Pest Sighting" },
    { icon: TrendingUp, label: "Yield History" },
    { icon: MessageSquare, label: "Observations" },
    { icon: Clock, label: "History" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100dvh", background: BG, paddingBottom: "calc(80px + var(--safe-bottom))" }}>
      <header style={{ position: "sticky", top: 0, zIndex: 10, background: BG, borderBottom: `1px solid ${BORDER}`, padding: "8px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <a href="/" style={{ width: 34, height: 34, borderRadius: 10, background: SURFACE, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", textDecoration: "none" }}>
            <ChevronLeft size={18} color={TEXT} />
          </a>
          <div>
            <h1 style={{ fontSize: 17, fontWeight: 700, letterSpacing: "-0.02em", color: TEXT, margin: 0 }}>Ground Truth</h1>
            <p style={{ fontSize: 11, color: TEXT_SEC, margin: 0 }}>Your farm data collection</p>
          </div>
        </div>
      </header>

      <div style={{ display: "flex", padding: "12px 20px", gap: 6, overflowX: "auto" }}>
        {tabs.map((t, i) => (
          <button key={i} onClick={() => setActiveTab(i)}
            style={{
              display: "flex", alignItems: "center", gap: 6, padding: "8px 16px", borderRadius: 20,
              border: activeTab === i ? `1px solid ${GOLD}` : `1px solid ${BORDER}`,
              background: activeTab === i ? "rgba(212,168,68,0.08)" : "transparent",
              color: activeTab === i ? GOLD : TEXT_SEC, fontSize: 12, fontWeight: 600, cursor: "pointer",
              whiteSpace: "nowrap",
            }}>
            <t.icon size={14} /> {t.label}
          </button>
        ))}
      </div>

      <main style={{ flex: 1, padding: "12px 20px", display: "flex", flexDirection: "column", gap: 14 }}>

        {activeTab === 0 && (
          <div className="anim-fade-up" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="card" style={{ padding: 20, borderLeft: `4px solid ${RED}` }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <Bug size={16} color={RED} />
                <span style={{ fontSize: 13, fontWeight: 700, color: TEXT }}>Have you seen any pests or diseases on your potatoes?</span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <input type="file" accept="image/*" capture="environment" onChange={handlePestPhoto} id="pest-photo" style={{ display: "none" }} />
                <label htmlFor="pest-photo" style={photoBtnStyle}>
                  <Camera size={18} color={GOLD} />
                  <span style={{ fontSize: 13, fontWeight: 500, color: TEXT_SEC }}>
                    {pestPhoto ? "Change photo" : "Take photo of affected plant"}
                  </span>
                </label>
                {pestPhoto && (
                  <img src={pestPhoto} alt="Pest" style={{ width: "100%", maxHeight: 200, objectFit: "cover", borderRadius: 10, border: `1px solid ${BORDER}` }} />
                )}

                <div>
                  <label style={{ ...labelStyle, fontSize: 10 }}>Description (optional)</label>
                  <textarea value={pestDesc} onChange={e => setPestDesc(e.target.value)}
                    rows={3} placeholder="Describe what you see — spots, wilting, bugs..."
                    style={{ ...inputStyle, fontSize: 13, resize: "vertical", minHeight: 70 }} />
                </div>

                <div>
                  <label style={{ ...labelStyle, fontSize: 10 }}>Date Seen</label>
                  <input type="date" value={pestDate} onChange={e => setPestDate(e.target.value)} style={inputStyle} />
                </div>

                <button onClick={submitPestSighting} disabled={pestSubmitting || (!pestDesc && !pestPhotoB64)} style={{ ...btnStyle, opacity: pestSubmitting || (!pestDesc && !pestPhotoB64) ? 0.4 : 1 }}>
                  <Camera size={14} /> Submit Pest Sighting
                </button>
                {pestFeedback && (
                  <p style={{ fontSize: 12, color: pestFeedback.includes("Classified") ? GREEN : RED, margin: 0, padding: "4px 12px", background: "rgba(74,222,128,0.06)", borderRadius: 8 }}>
                    {pestFeedback}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 1 && (
          <div className="anim-fade-up" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="card" style={{ padding: 20, borderLeft: `4px solid ${GOLD}` }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <TrendingUp size={16} color={GOLD} />
                <span style={{ fontSize: 13, fontWeight: 700, color: TEXT }}>What was your last harvest?</span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <div>
                    <label style={{ ...labelStyle, fontSize: 10 }}>Kilograms Harvested</label>
                    <input type="number" value={yieldKg} onChange={e => setYieldKg(e.target.value)} placeholder="e.g. 2500" style={inputStyle} />
                  </div>
                  <div>
                    <label style={{ ...labelStyle, fontSize: 10 }}>Acres Planted</label>
                    <input type="number" step="0.25" value={yieldAcres} onChange={e => setYieldAcres(e.target.value)} placeholder="e.g. 1.5" style={inputStyle} />
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <div>
                    <label style={{ ...labelStyle, fontSize: 10 }}>Variety</label>
                    <select value={yieldVariety} onChange={e => setYieldVariety(e.target.value)} style={inputStyle}>
                      {["Shangi", "Kenya Mpya", "Dutch Robjin", "Tigoni", "Asante"].map(v => <option key={v} value={v}>{v}</option>)}
                    </select>
                  </div>
                  <div>
                    <label style={{ ...labelStyle, fontSize: 10 }}>Harvest Date</label>
                    <input type="date" value={yieldDate} onChange={e => setYieldDate(e.target.value)} style={inputStyle} />
                  </div>
                </div>

                <button onClick={submitYield} disabled={yieldSubmitting || !yieldKg} style={{ ...btnStyle, opacity: yieldSubmitting || !yieldKg ? 0.4 : 1 }}>
                  <Check size={14} /> Record Yield
                </button>
                {yieldFeedback && (
                  <p style={{ fontSize: 12, color: yieldFeedback.includes("success") ? GREEN : RED, margin: 0, padding: "4px 12px", background: "rgba(74,222,128,0.06)", borderRadius: 8 }}>
                    {yieldFeedback}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 2 && (
          <div className="anim-fade-up" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="card" style={{ padding: 20, borderLeft: `4px solid ${BLUE}` }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <MessageSquare size={16} color={BLUE} />
                <span style={{ fontSize: 13, fontWeight: 700, color: TEXT }}>Anything you've noticed about your crop?</span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <textarea value={obsText} onChange={e => setObsText(e.target.value)}
                  rows={4} placeholder="Crop color, size, water needs, anything unusual..."
                  style={{ ...inputStyle, fontSize: 13, resize: "vertical", minHeight: 100 }} />

                <input type="file" accept="image/*" capture="environment" onChange={handleObsPhoto} id="obs-photo" style={{ display: "none" }} />
                <label htmlFor="obs-photo" style={photoBtnStyle}>
                  <Camera size={18} color={GOLD} />
                  <span style={{ fontSize: 13, fontWeight: 500, color: TEXT_SEC }}>
                    {obsPhoto ? "Change photo" : "Add photo (optional)"}
                  </span>
                </label>
                {obsPhoto && (
                  <img src={obsPhoto} alt="Observation" style={{ width: "100%", maxHeight: 200, objectFit: "cover", borderRadius: 10, border: `1px solid ${BORDER}` }} />
                )}

                <button onClick={submitObservation} disabled={obsSubmitting || !obsText.trim()} style={{ ...btnStyle, opacity: obsSubmitting || !obsText.trim() ? 0.4 : 1 }}>
                  <Check size={14} /> Submit Observation
                </button>
                {obsFeedback && (
                  <p style={{ fontSize: 12, color: obsFeedback.includes("Recorded") ? GREEN : RED, margin: 0, padding: "4px 12px", background: "rgba(74,222,128,0.06)", borderRadius: 8 }}>
                    {obsFeedback}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 3 && (
          <div className="anim-fade-up" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 4, height: 16, borderRadius: 2, background: GREEN }} />
              <span style={{ fontSize: 11, fontWeight: 600, color: TEXT_SEC, textTransform: "uppercase", letterSpacing: "0.06em" }}>Collected Data Timeline</span>
            </div>
            {logsLoading ? (
              <p style={{ fontSize: 13, color: TEXT_SEC, padding: 20, textAlign: "center" }}>Loading...</p>
            ) : logs.length === 0 ? (
              <div className="card" style={{ padding: 32, textAlign: "center" }}>
                <Camera size={36} style={{ margin: "0 auto 12px", color: TEXT_SEC, opacity: 0.3 }} />
                <p style={{ fontSize: 13, color: TEXT_SEC }}>No ground truth data collected yet.</p>
                <p style={{ fontSize: 12, color: TEXT_SEC, opacity: 0.6 }}>Submit a pest sighting, yield report, or observation to start.</p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {logs.map((log, i) => (
                  <div key={log.logId || i} className="card anim-fade-up" style={{ padding: 14, borderLeft: `4px solid ${log.type === "pest_sighting" ? RED : log.type === "yield_report" ? GOLD : BLUE}`, animationDelay: `${i * 0.03}s` }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                          <span style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: log.type === "pest_sighting" ? RED : log.type === "yield_report" ? GOLD : BLUE, background: `${log.type === "pest_sighting" ? RED : log.type === "yield_report" ? GOLD : BLUE}15`, padding: "2px 8px", borderRadius: 9999 }}>
                            {log.type?.replace(/_/g, " ") || "entry"}
                          </span>
                          {log.classification && (
                            <span style={{ fontSize: 10, fontWeight: 600, color: TEXT_SEC, background: `${SURFACE}`, padding: "2px 8px", borderRadius: 9999 }}>
                              {log.classification}
                            </span>
                          )}
                        </div>
                        <p style={{ fontSize: 13, color: TEXT, margin: "4px 0 0", lineHeight: 1.5 }}>
                          {log.textRecord || "No description"}
                        </p>
                      </div>
                      <span style={{ fontSize: 10, color: TEXT_SEC, flexShrink: 0, whiteSpace: "nowrap" }}>
                        {log.timestamp ? new Date(log.timestamp).toLocaleDateString("en-KE", { year: "numeric", month: "short", day: "numeric" }) : ""}
                      </span>
                    </div>
                    {log.mediaUrl && (
                      <div style={{ marginTop: 8 }}>
                        <a href={log.mediaUrl} target="_blank" rel="noopener noreferrer"
                          style={{ fontSize: 11, color: BLUE, textDecoration: "none", display: "flex", alignItems: "center", gap: 4 }}>
                          <Camera size={12} /> View image
                        </a>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
