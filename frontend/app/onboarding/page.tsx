"use client";

import { useState, useCallback } from "react";
import { Sprout, ArrowRight, Check, ChevronLeft, Database, MapPin, Crosshair, Loader2, Camera, Upload, Bug } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const BG = "#0d1f15";
const SURFACE = "#13291e";
const BORDER = "#1e3a2a";
const TEXT = "#e8e6dc";
const TEXT_SEC = "#8b9e8e";
const GREEN = "#4ade80";
const GREEN_DIM = "#22c55e";
const GOLD = "#d4a844";
const RED = "#f87171";
const BLUE = "#60a5fa";

const COUNTIES = ["Nyandarua", "Nakuru", "Kiambu", "Meru", "Nyeri", "Muranga", "Laikipia", "Bomet", "Uasin Gishu"];
const VARIETIES = ["Shangi", "Kenya Mpya", "Dutch Robjin", "Tigoni", "Asante"];

const KNOWN_PESTS = [
  { id: "late_blight", label: "Late Blight", emoji: "🟤" },
  { id: "early_blight", label: "Early Blight", emoji: "🟡" },
  { id: "bacterial_wilt", label: "Bacterial Wilt", emoji: "🦠" },
  { id: "aphids", label: "Aphids", emoji: "🟢" },
  { id: "tuber_moth", label: "Tuber Moth", emoji: "🦋" },
];

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const [phone, setPhone] = useState("+254");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [farmerId, setFarmerId] = useState("");
  const [name, setName] = useState("");

  const [county, setCounty] = useState("Nyandarua");
  const [plotName, setPlotName] = useState("");
  const [acres, setAcres] = useState("1.5");
  const [variety, setVariety] = useState("Shangi");
  const [plantingDate, setPlantingDate] = useState(
    () => new Date(Date.now() - 60 * 86400000).toISOString().split("T")[0],
  );
  const [latitude, setLatitude] = useState("-0.1833");
  const [longitude, setLongitude] = useState("36.4333");
  const [locating, setLocating] = useState(false);

  const [photoBase64, setPhotoBase64] = useState("");
  const [photoPreview, setPhotoPreview] = useState("");
  const [farmHistory, setFarmHistory] = useState("");
  const [docBase64, setDocBase64] = useState("");
  const [docName, setDocName] = useState("");
  const [knownPests, setKnownPests] = useState<string[]>([]);

  const [textEnabled, setTextEnabled] = useState(true);
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [language, setLanguage] = useState("en");
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const getLocation = () => {
    if (!navigator.geolocation) { setError("Geolocation not supported"); return; }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      pos => { setLatitude(pos.coords.latitude.toFixed(6)); setLongitude(pos.coords.longitude.toFixed(6)); setLocating(false); },
      () => { setError("Could not get location"); setLocating(false); },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  const toBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve((reader.result as string).split(",")[1]);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };

  const handlePhotoSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const b64 = await toBase64(file);
      setPhotoBase64(b64);
      setPhotoPreview(URL.createObjectURL(file));
    } catch {
      setError("Could not read photo");
    }
  }, []);

  const handleDocSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const b64 = await toBase64(file);
      setDocBase64(b64);
      setDocName(file.name);
    } catch {
      setError("Could not read document");
    }
  }, []);

  const togglePest = (id: string) => {
    setKnownPests(prev => prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]);
  };

  const submitGroundTruth = async (fid: string) => {
    const submissions: Promise<any>[] = [];
    if (photoBase64) {
      submissions.push(
        fetch(`${API}/api/farmer/${fid}/ground-truth`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ type: "photo", text: farmHistory || "Farm photo during registration", imageBase64: photoBase64 }),
        })
      );
    }
    if (farmHistory.trim()) {
      submissions.push(
        fetch(`${API}/api/farmer/${fid}/ground-truth`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ type: "farmer_observation", text: farmHistory }),
        })
      );
    }
    if (docBase64) {
      submissions.push(
        fetch(`${API}/api/farmer/${fid}/ground-truth`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ type: "document", text: docName, imageBase64: docBase64 }),
        })
      );
    }
    if (knownPests.length > 0) {
      submissions.push(
        fetch(`${API}/api/farmer/${fid}/ground-truth`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ type: "known_pests", text: knownPests.join(", "), metadata: { pests: knownPests } }),
        })
      );
    }
    if (submissions.length > 0) {
      try { await Promise.all(submissions); } catch {}
    }
  };

  const register = async () => {
    setError("");
    setStatus("Fetching live soil and weather data...");
    try {
      const r = await fetch(`${API}/api/farmer/register`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          farmerId: farmerId || undefined, name, county,
          plotName: plotName || `Shamba ${county}`, acres: parseFloat(acres),
          variety, plantingDate, latitude: parseFloat(latitude), longitude: parseFloat(longitude),
          channels: [...(textEnabled ? ["whatsapp_text"] : []), ...(audioEnabled ? ["whatsapp_audio"] : [])],
          language,
        }),
      });
      const data = await r.json();
      if (!data.plotId) { setError("Registration failed"); return; }
      let fid = data.farmerId;
      if (!fid || fid === "undefined") {
        const id = `farmer-${Date.now()}`;
        localStorage.setItem("farmerId", id);
        await fetch(`${API}/api/farmer/register`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            farmerId: id, name, county,
            plotName: plotName || `Shamba ${county}`, acres: parseFloat(acres),
            variety, plantingDate, latitude: parseFloat(latitude), longitude: parseFloat(longitude),
            channels: [...(textEnabled ? ["whatsapp_text"] : []), ...(audioEnabled ? ["whatsapp_audio"] : [])],
            language,
          }),
        });
        localStorage.setItem("farmerId", id);
        fid = id;
      } else {
        localStorage.setItem("farmerId", fid);
      }
      const pid = data.plotId;
      if (pid) localStorage.setItem("plotId", pid);
      await submitGroundTruth(fid);
      setStatus(data.message || "Registration complete!");
      setStep(4);
    } catch {
      setError("Registration failed. Check backend connection.");
      setStatus("");
    }
  };

  const inputStyle: React.CSSProperties = {
    width: "100%", background: "rgba(255,255,255,0.03)", border: `1px solid ${BORDER}`, borderRadius: 12,
    padding: "14px", fontSize: 16, color: TEXT, outline: "none", fontFamily: "'DM Sans', sans-serif", boxSizing: "border-box"
  };
  const labelStyle: React.CSSProperties = {
    fontSize: 11, fontWeight: 600, color: TEXT_SEC, textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: 6
  };
  const btnStyle: React.CSSProperties = {
    background: "linear-gradient(135deg, #4ade80, #22c55e)", border: "none", borderRadius: 14, padding: "14px",
    fontSize: 15, fontWeight: 700, color: "#0d1f15", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8, letterSpacing: "-0.01em"
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100dvh", background: BG, color: TEXT }}>
      <header style={{ padding: "14px 18px 10px", paddingTop: "calc(14px + var(--safe-top))", display: "flex", alignItems: "center", gap: 12 }}>
        {step > 0 && step < 4 && (
          <button onClick={() => setStep(step - 1)} style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 10, width: 34, height: 34, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>
            <ChevronLeft size={18} color={TEXT} />
          </button>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Sprout size={20} color={GREEN} />
          <span style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-0.02em" }}>FarmWise</span>
        </div>
      </header>

      <div style={{ display: "flex", gap: 4, padding: "0 20px", marginBottom: 20 }}>
        {[0, 1, 2, 3, 4].map(i => (
          <div key={i} style={{ height: 3, flex: 1, borderRadius: 2, background: i <= step ? GREEN : BORDER, transition: "background 0.3s" }} />
        ))}
      </div>

      <main style={{ flex: 1, padding: "0 20px 16px", maxWidth: 400, margin: "0 auto", width: "100%" }}>

        {step === 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20, paddingTop: 8 }}>
            <div>
              <h1 style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 32, fontWeight: 700, letterSpacing: "-0.02em", margin: "0 0 4px" }}>Register Your Farm</h1>
              <p style={{ fontSize: 14, color: TEXT_SEC, lineHeight: 1.5 }}>Enter your phone number. We'll send a verification code.</p>
            </div>

            <div style={{ background: SURFACE, borderRadius: 16, padding: 20, border: `1px solid ${BORDER}`, display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label style={labelStyle}>Phone Number</label>
                <input type="tel" value={phone} onChange={e => setPhone(e.target.value)} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Your Name</label>
                <input type="text" value={name} onChange={e => setName(e.target.value)} style={inputStyle} />
              </div>
              {!otpSent ? (
                <button onClick={async () => {
                  try {
                    const r = await fetch(`${API}/api/auth/send-otp`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ phone }) });
                    if (r.ok) setOtpSent(true);
                  } catch { setError("Could not send OTP"); }
                }} style={btnStyle}>
                  Send Verification Code
                </button>
              ) : (
                <>
                  <div>
                    <label style={labelStyle}>Enter Code</label>
                    <input type="text" value={otp} onChange={e => setOtp(e.target.value)}
                      style={{ ...inputStyle, fontSize: 24, fontWeight: 600, color: GREEN, textAlign: "center", letterSpacing: "0.4em", fontFamily: "monospace" }} />
                  </div>
                  <button onClick={async () => {
                    try {
                      const r = await fetch(`${API}/api/auth/verify-otp`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ phone, code: otp }) });
                      const data = await r.json();
                      setFarmerId(data.farmerId);
                      localStorage.setItem("farmerId", data.farmerId);
                      setStep(1);
                    } catch { setError("Wrong code. Try again."); }
                  }} style={btnStyle}>
                    Verify <ArrowRight size={18} />
                  </button>
                </>
              )}
            </div>
            {error && <p style={{ fontSize: 13, color: RED, textAlign: "center" }}>{error}</p>}
          </div>
        )}

        {step === 1 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 18, paddingTop: 8 }}>
            <div>
              <h1 style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 32, fontWeight: 700, letterSpacing: "-0.02em", margin: "0 0 4px" }}>Your Farm Details</h1>
              <p style={{ fontSize: 14, color: TEXT_SEC, lineHeight: 1.5 }}>Tell us about your plot so we can monitor it.</p>
            </div>

            <div style={{ background: SURFACE, borderRadius: 16, padding: 20, border: `1px solid ${BORDER}`, display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label style={labelStyle}>County</label>
                <select value={county} onChange={e => setCounty(e.target.value)}
                  style={{ ...inputStyle, fontSize: 15 }}>{COUNTIES.map(c => <option key={c} value={c}>{c}</option>)}</select>
              </div>
              <div>
                <label style={labelStyle}>Plot Name</label>
                <input type="text" value={plotName} onChange={e => setPlotName(e.target.value)} placeholder="Shamba ya Mlima" style={{ ...inputStyle, fontSize: 15 }} />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <label style={labelStyle}>Acres</label>
                  <input type="number" step="0.25" value={acres} onChange={e => setAcres(e.target.value)} style={{ ...inputStyle, fontSize: 15 }} />
                </div>
                <div>
                  <label style={labelStyle}>Variety</label>
                  <select value={variety} onChange={e => setVariety(e.target.value)}
                    style={{ ...inputStyle, fontSize: 15 }}>{VARIETIES.map(v => <option key={v} value={v}>{v}</option>)}</select>
                </div>
              </div>
              <div>
                <label style={labelStyle}>Planting Date</label>
                <input type="date" value={plantingDate} onChange={e => setPlantingDate(e.target.value)} style={{ ...inputStyle, fontSize: 15 }} />
              </div>

              <div style={{ padding: 14, background: "rgba(74,222,128,0.03)", borderRadius: 12, border: "1px solid rgba(74,222,128,0.1)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                  <MapPin size={16} color={GREEN} />
                  <span style={{ fontSize: 12, fontWeight: 600, color: GREEN, textTransform: "uppercase", letterSpacing: "0.04em" }}>Farm Location</span>
                  <button onClick={getLocation} disabled={locating}
                    style={{ marginLeft: "auto", background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 10, padding: "6px 12px", fontSize: 11, fontWeight: 600, color: GREEN, cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
                    {locating ? <Loader2 size={14} className="anim-slide" /> : <Crosshair size={14} />}
                    {locating ? "Getting..." : "Use GPS"}
                  </button>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <div>
                    <label style={{ fontSize: 10, color: "#5a6e5e", display: "block", marginBottom: 4 }}>Latitude</label>
                    <input type="text" value={latitude} onChange={e => setLatitude(e.target.value)}
                      style={{ width: "100%", background: "rgba(255,255,255,0.02)", border: `1px solid ${BORDER}`, borderRadius: 10, padding: "10px 12px", fontSize: 14, fontFamily: "monospace", color: TEXT, outline: "none", boxSizing: "border-box" }} />
                  </div>
                  <div>
                    <label style={{ fontSize: 10, color: "#5a6e5e", display: "block", marginBottom: 4 }}>Longitude</label>
                    <input type="text" value={longitude} onChange={e => setLongitude(e.target.value)}
                      style={{ width: "100%", background: "rgba(255,255,255,0.02)", border: `1px solid ${BORDER}`, borderRadius: 10, padding: "10px 12px", fontSize: 14, fontFamily: "monospace", color: TEXT, outline: "none", boxSizing: "border-box" }} />
                  </div>
                </div>
              </div>
            </div>
            <button onClick={() => setStep(2)} style={btnStyle}>
              Continue <ArrowRight size={18} />
            </button>
          </div>
        )}

        {step === 2 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 18, paddingTop: 8 }}>
            <div>
              <h1 style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em", margin: "0 0 4px" }}>Farm Details Collection</h1>
              <p style={{ fontSize: 14, color: TEXT_SEC, lineHeight: 1.5 }}>Help us understand your farm better. This helps us give you accurate advice.</p>
            </div>

            <div style={{ background: SURFACE, borderRadius: 16, padding: 20, border: `1px solid ${BORDER}`, display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label style={{ ...labelStyle, display: "flex", alignItems: "center", gap: 6 }}><Camera size={14} color={GOLD} /> Farm Photo</label>
                <input type="file" accept="image/*" capture="environment" onChange={handlePhotoSelect} id="farm-photo" style={{ display: "none" }} />
                <label htmlFor="farm-photo" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, width: "100%", background: "rgba(212,168,68,0.06)", border: `1px dashed ${GOLD}44`, borderRadius: 12, padding: "24px 14px", cursor: "pointer", textAlign: "center" }}>
                  <Upload size={20} color={GOLD} />
                  <span style={{ fontSize: 13, fontWeight: 500, color: TEXT_SEC }}>
                    {photoPreview ? "Change photo" : "Take or upload farm photo"}
                  </span>
                </label>
                {photoPreview && (
                  <div style={{ marginTop: 8, borderRadius: 10, overflow: "hidden", border: `1px solid ${BORDER}` }}>
                    <img src={photoPreview} alt="Farm preview" style={{ width: "100%", maxHeight: 200, objectFit: "cover", display: "block" }} />
                  </div>
                )}
              </div>

              <div>
                <label style={labelStyle}>Farm History</label>
                <textarea value={farmHistory} onChange={e => setFarmHistory(e.target.value)}
                  rows={4}
                  placeholder="Tell us about your farm — past yields, pests you've seen, soil type, irrigation method / Tuambie kuhusu shamba lako — mavuno ya awali, wadudu uliowaona, aina ya udongo, njia ya kumwagilia"
                  style={{ ...inputStyle, fontSize: 14, resize: "vertical", padding: "12px", lineHeight: 1.5, minHeight: 100 }} />
              </div>

              <div>
                <label style={{ ...labelStyle, display: "flex", alignItems: "center", gap: 6 }}><Upload size={14} color={GOLD} /> Previous Reports (optional)</label>
                <input type="file" accept="image/*,.pdf" onChange={handleDocSelect} id="farm-doc" style={{ display: "none" }} />
                <label htmlFor="farm-doc" style={{ display: "flex", alignItems: "center", gap: 8, width: "100%", background: "rgba(212,168,68,0.06)", border: `1px dashed ${GOLD}44`, borderRadius: 12, padding: "14px", cursor: "pointer" }}>
                  <Upload size={16} color={GOLD} />
                  <span style={{ fontSize: 13, fontWeight: 500, color: TEXT_SEC }}>
                    {docName ? docName : "Upload soil test or agronomist report (PDF/Image)"}
                  </span>
                </label>
              </div>

              <div>
                <label style={{ ...labelStyle, display: "flex", alignItems: "center", gap: 6 }}><Bug size={14} color={GOLD} /> Known Pests</label>
                <p style={{ fontSize: 12, color: TEXT_SEC, margin: "0 0 10px" }}>Select pests you've seen on your potatoes:</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {KNOWN_PESTS.map(p => {
                    const sel = knownPests.includes(p.id);
                    return (
                      <button key={p.id} onClick={() => togglePest(p.id)}
                        style={{
                          padding: "8px 14px", borderRadius: 20, border: sel ? `2px solid ${GREEN}` : `1px solid ${BORDER}`,
                          background: sel ? "rgba(74,222,128,0.1)" : "transparent",
                          color: sel ? GREEN : TEXT_SEC, fontSize: 12, fontWeight: 600,
                          cursor: "pointer", display: "flex", alignItems: "center", gap: 6,
                          transition: "all 0.2s",
                        }}>
                        <span>{p.emoji}</span> {p.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
            <button onClick={() => setStep(3)} style={btnStyle}>
              Continue <ArrowRight size={18} />
            </button>
          </div>
        )}

        {step === 3 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 18, paddingTop: 8 }}>
            <div>
              <h1 style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em", margin: "0 0 4px" }}>How do you want your advice?</h1>
            </div>
            <div style={{ background: SURFACE, borderRadius: 16, padding: 20, border: `1px solid ${BORDER}`, display: "flex", flexDirection: "column", gap: 16 }}>
              {[
                { k: "text", l: "WhatsApp Text", d: "Daily message with advice", s: textEnabled, set: setTextEnabled },
                { k: "audio", l: "WhatsApp Audio", d: "Voice note in Swahili", s: audioEnabled, set: setAudioEnabled },
              ].map(({ k, l, d, s, set }) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div><p style={{ fontWeight: 600, margin: 0 }}>{l}</p><p style={{ fontSize: 13, color: TEXT_SEC, margin: "2px 0 0" }}>{d}</p></div>
                  <button onClick={() => set(!s)}
                    style={{ width: 48, height: 28, borderRadius: 14, border: "none", background: s ? GREEN : BORDER, cursor: "pointer", position: "relative", transition: "background 0.2s" }}>
                    <div style={{ width: 22, height: 22, borderRadius: "50%", background: BG, position: "absolute", top: 3, left: s ? 23 : 3, transition: "left 0.2s" }} />
                  </button>
                </div>
              ))}
              <div>
                <label style={{ ...labelStyle, marginBottom: 8 }}>Language</label>
                <div style={{ display: "flex", gap: 8 }}>
                  {[{ k: "en", l: "English" }, { k: "sw", l: "Kiswahili" }].map(({ k, l }) => (
                    <button key={k} onClick={() => setLanguage(k)}
                      style={{ flex: 1, borderRadius: 12, padding: "12px", fontSize: 14, fontWeight: 600, border: language === k ? `2px solid ${GREEN}` : `1px solid ${BORDER}`, background: language === k ? "rgba(74,222,128,0.08)" : "transparent", color: language === k ? GREEN : TEXT_SEC, cursor: "pointer", transition: "all 0.2s" }}>{l}</button>
                  ))}
                </div>
              </div>
            </div>
            <button onClick={register} style={btnStyle}>
              Complete Registration <Check size={18} />
            </button>
            {status && <p style={{ fontSize: 13, color: GREEN, textAlign: "center" }}>{status}</p>}
            {error && <p style={{ fontSize: 13, color: RED, textAlign: "center" }}>{error}</p>}
          </div>
        )}

        {step === 4 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16, paddingTop: 24, textAlign: "center", alignItems: "center" }}>
            <div style={{ width: 72, height: 72, borderRadius: "50%", background: "rgba(74,222,128,0.1)", border: "2px solid rgba(74,222,128,0.2)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Check size={36} color={GREEN} />
            </div>
            <div>
              <h1 style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em", margin: 0 }}>Karibu FarmWise!</h1>
              <p style={{ fontSize: 14, color: TEXT_SEC, lineHeight: 1.5, marginTop: 8 }}>
                Your farm <strong>{plotName || "plot"}</strong> in {county} is now being monitored.
                {status && <><br />{status}</>}
              </p>
            </div>
            <a href="/"
              style={{ background: "linear-gradient(135deg, #4ade80, #22c55e)", border: "none", borderRadius: 14, padding: "14px 36px", fontSize: 15, fontWeight: 700, color: "#0d1f15", textDecoration: "none", display: "flex", alignItems: "center", gap: 8 }}>
              Go to Dashboard <ArrowRight size={18} />
            </a>
          </div>
        )}
      </main>
    </div>
  );
}
