"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, User, Phone, MapPin, Sprout, Clock, ShieldCheck, Camera, ArrowRight, BarChart3 } from "lucide-react";

const API = "";

const BG = "#0d1f15";
const SURFACE = "#13291e";
const BORDER = "#1e3a2a";
const TEXT = "#e8e6dc";
const TEXT_SEC = "#8b9e8e";
const GREEN = "#4ade80";
const GOLD = "#d4a844";
const GREEN_DIM = "#22c55e";
const RED = "#f87171";
const BLUE = "#60a5fa";

export default function ProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fid = localStorage.getItem("farmerId");
    if (!fid) { router.push("/onboarding"); return; }
    fetch(`${API}/api/farmer/${fid}/profile`)
      .then(r => r.json())
      .then(d => { setProfile(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ display: "flex", minHeight: "100dvh", alignItems: "center", justifyContent: "center", background: BG }}>
      <User size={44} className="anim-pulse-soft" style={{ color: GREEN, opacity: 0.5 }} />
    </div>
  );

  const plots = profile?.plots || [];
  const recommendations = profile?.recommendations || [];
  const groundTruth = profile?.groundTruthEntries || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100dvh", background: BG, paddingBottom: "calc(80px + var(--safe-bottom))" }}>
      <header style={{ position: "sticky", top: 0, zIndex: 10, background: BG, borderBottom: `1px solid ${BORDER}`, padding: "8px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <a href="/" style={{ width: 34, height: 34, borderRadius: 10, background: SURFACE, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", textDecoration: "none" }}>
            <ChevronLeft size={18} color={TEXT} />
          </a>
          <h1 style={{ fontSize: 17, fontWeight: 700, letterSpacing: "-0.02em", color: TEXT }}>My Profile</h1>
        </div>
      </header>

      <main style={{ flex: 1, padding: "16px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
        <div className="card anim-fade-up delay-1" style={{ padding: 20, textAlign: "center" }}>
          <div style={{ width: 64, height: 64, borderRadius: "50%", background: "rgba(96,165,250,0.12)", border: `2px solid ${BLUE}33`, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 12px" }}>
            <User size={32} color={BLUE} />
          </div>
          <h2 style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 22, fontWeight: 700, color: TEXT, margin: "0 0 4px" }}>
            {profile?.name || "Farmer"}
          </h2>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, marginTop: 8 }}>
            {profile?.phone && (
              <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: TEXT_SEC }}>
                <Phone size={12} /> {profile.phone}
              </span>
            )}
            {profile?.language && (
              <span style={{ fontSize: 11, fontWeight: 600, color: GREEN, background: "rgba(74,222,128,0.1)", padding: "2px 10px", borderRadius: 9999 }}>
                {profile.language === "sw" ? "Kiswahili" : "English"}
              </span>
            )}
          </div>
        </div>

        {plots.length > 0 && (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <div style={{ width: 4, height: 16, borderRadius: 2, background: GREEN }} />
              <span style={{ fontSize: 11, fontWeight: 600, color: TEXT_SEC, textTransform: "uppercase", letterSpacing: "0.06em" }}>My Plots</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {plots.map((p: any, i: number) => (
                <a key={p.plotId || i} href="/dashboard/growth" style={{ textDecoration: "none" }}>
                  <div className="card anim-fade-up" style={{ padding: 16, display: "flex", alignItems: "center", gap: 12, animationDelay: `${0.1 + i * 0.05}s` }}>
                    <div style={{ width: 40, height: 40, borderRadius: 10, background: `${GREEN}15`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <Sprout size={20} color={GREEN} />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: 14, fontWeight: 600, color: TEXT }}>{p.name || "Plot"}</span>
                        <span style={{ fontSize: 10, fontWeight: 700, color: GREEN, background: "rgba(74,222,128,0.1)", padding: "2px 8px", borderRadius: 9999 }}>Day {p.seasonDay}</span>
                      </div>
                      <div style={{ display: "flex", gap: 12, marginTop: 3 }}>
                        <span style={{ fontSize: 11, color: TEXT_SEC, display: "flex", alignItems: "center", gap: 3 }}>
                          <Sprout size={10} /> {p.variety}
                        </span>
                        <span style={{ fontSize: 11, color: TEXT_SEC, display: "flex", alignItems: "center", gap: 3 }}>
                          <MapPin size={10} /> {p.county}
                        </span>
                        {p.stage && (
                          <span style={{ fontSize: 11, color: GREEN, display: "flex", alignItems: "center", gap: 3 }}>
                            <BarChart3 size={10} /> {p.stage}
                          </span>
                        )}
                      </div>
                    </div>
                    <ArrowRight size={14} color={TEXT_SEC} />
                  </div>
                </a>
              ))}
            </div>
          </div>
        )}

        {recommendations.length > 0 && (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <div style={{ width: 4, height: 16, borderRadius: 2, background: GOLD }} />
              <span style={{ fontSize: 11, fontWeight: 600, color: TEXT_SEC, textTransform: "uppercase", letterSpacing: "0.06em" }}>Recent Recommendations</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {recommendations.slice(0, 5).map((r: any, i: number) => (
                <div key={i} className="card anim-fade-up" style={{ padding: 14, borderLeft: `4px solid ${GREEN_DIM}`, animationDelay: `${0.15 + i * 0.05}s` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: 13, fontWeight: 600, color: TEXT, margin: 0 }}>{r.action}</p>
                      <p style={{ fontSize: 11, color: TEXT_SEC, margin: "2px 0 0" }}>{r.cause}</p>
                    </div>
                    <span style={{ fontSize: 10, fontWeight: 600, color: r.urgencyHours && r.urgencyHours < 24 ? RED : GOLD, background: `${r.urgencyHours && r.urgencyHours < 24 ? RED : GOLD}15`, padding: "3px 8px", borderRadius: 9999, flexShrink: 0 }}>
                      {r.date ? new Date(r.date).toLocaleDateString("en-KE") : ""}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {groundTruth.length > 0 && (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <div style={{ width: 4, height: 16, borderRadius: 2, background: BLUE }} />
              <span style={{ fontSize: 11, fontWeight: 600, color: TEXT_SEC, textTransform: "uppercase", letterSpacing: "0.06em" }}>Ground Truth Timeline</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {groundTruth.slice(0, 10).map((e: any, i: number) => (
                <div key={e.logId || i} className="card anim-fade-up" style={{ padding: 12, display: "flex", alignItems: "center", gap: 10, animationDelay: `${0.2 + i * 0.03}s` }}>
                  <div style={{ width: 28, height: 28, borderRadius: 7, background: `${e.type === "pest_sighting" ? RED : e.type === "yield_report" ? GOLD : BLUE}15`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    {e.type === "pest_sighting" ? <ShieldCheck size={14} color={RED} /> : <Camera size={14} color={BLUE} />}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: 12, fontWeight: 600, color: TEXT, margin: 0 }}>
                      {e.classification ? e.classification.replace(/_/g, " ") : e.type?.replace(/_/g, " ") || "Entry"}
                    </p>
                    <p style={{ fontSize: 11, color: TEXT_SEC, margin: "1px 0 0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {e.textRecord || ""}
                    </p>
                  </div>
                  <span style={{ fontSize: 10, color: TEXT_SEC, flexShrink: 0 }}>
                    {e.timestamp ? new Date(e.timestamp).toLocaleDateString("en-KE") : ""}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <a href="/dashboard/ground-truth"
          style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, background: "linear-gradient(135deg, #4ade80, #22c55e)", border: "none", borderRadius: 14, padding: "14px", fontSize: 14, fontWeight: 700, color: "#0d1f15", textDecoration: "none", marginTop: 4 }}>
          <Camera size={16} /> Add More Data
        </a>
      </main>
    </div>
  );
}
