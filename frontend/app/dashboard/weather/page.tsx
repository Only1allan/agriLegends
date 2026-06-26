"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, Thermometer, Droplets, Sprout } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts";

const API = "";

const BG = "#0d1f15";
const SURFACE = "#13291e";
const BORDER = "#1e3a2a";
const TEXT = "#e8e6dc";
const TEXT_SEC = "#8b9e8e";
const GREEN = "#4ade80";
const BLUE = "#60a5fa";

export default function WeatherPage() {
  const router = useRouter();
  const [weather, setWeather] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const pid = localStorage.getItem("plotId");
    if (!pid) { router.push("/onboarding"); return; }
    fetch(`${API}/api/plot/${pid}/weather?days=14`)
      .then(r => r.json())
      .then(data => { setWeather(data?.map((d: any) => ({ ...d, date: d.date?.slice(5) })) ?? []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ display: "flex", minHeight: "100dvh", alignItems: "center", justifyContent: "center", background: BG }}>
      <Thermometer size={48} className="anim-pulse-soft" color={GREEN} />
    </div>
  );

  const latest = weather[weather.length - 1] || {};

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100dvh", background: BG, paddingBottom: "calc(88px + env(safe-area-inset-bottom, 0px))" }}>
      <header style={{ position: "sticky", top: 0, zIndex: 10, background: BG, borderBottom: `1px solid ${BORDER}`, padding: "8px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <a href="/" style={{ width: 34, height: 34, borderRadius: 10, background: SURFACE, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", textDecoration: "none" }}>
            <ChevronLeft size={18} color={TEXT} />
          </a>
          <h1 style={{ fontSize: 17, fontWeight: 700, letterSpacing: "-0.02em", color: TEXT }}>Weather</h1>
        </div>
      </header>

      <main style={{ flex: 1, padding: "16px 20px", display: "flex", flexDirection: "column", gap: 16 }}>
        {weather.length === 0 ? (
          <div className="card" style={{ padding: 32, textAlign: "center" }}>
            <Sprout size={40} style={{ margin: "0 auto 12px", color: TEXT_SEC, opacity: 0.4 }} />
            <p style={{ fontSize: 13, color: TEXT_SEC }}>No weather data available yet.</p>
          </div>
        ) : (
          <>
            <div className="anim-fade-up delay-1" style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
              <div className="card" style={{ padding: 16, textAlign: "center" }}>
                <Thermometer size={18} style={{ margin: "0 auto 6px", color: "#f87171" }} />
                <p style={{ fontSize: 20, fontWeight: 800, color: TEXT }}>{latest.tempMax ?? "—"}°</p>
                <p style={{ fontSize: 10, fontWeight: 500, color: TEXT_SEC }}>Max</p>
              </div>
              <div className="card" style={{ padding: 16, textAlign: "center" }}>
                <Thermometer size={18} style={{ margin: "0 auto 6px", color: BLUE }} />
                <p style={{ fontSize: 20, fontWeight: 800, color: TEXT }}>{latest.tempMin ?? "—"}°</p>
                <p style={{ fontSize: 10, fontWeight: 500, color: TEXT_SEC }}>Min</p>
              </div>
              <div className="card" style={{ padding: 16, textAlign: "center" }}>
                <Droplets size={18} style={{ margin: "0 auto 6px", color: BLUE }} />
                <p style={{ fontSize: 20, fontWeight: 800, color: TEXT }}>{latest.precipitation ?? "—"}mm</p>
                <p style={{ fontSize: 10, fontWeight: 500, color: TEXT_SEC }}>Rain</p>
              </div>
            </div>

            <div className="card anim-fade-up delay-2" style={{ padding: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
                <div style={{ width: 4, height: 16, borderRadius: 2, background: GREEN }} />
                <span className="stat-label">Temperature (°C)</span>
              </div>
              <div style={{ height: 220, marginLeft: -8 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={weather}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,58,42,0.5)" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: TEXT_SEC }} axisLine={false} tickLine={false} />
                    <YAxis domain={[0, 35]} tick={{ fontSize: 10, fill: TEXT_SEC }} axisLine={false} tickLine={false} width={30} />
                    <Tooltip contentStyle={{ background: SURFACE, borderRadius: 12, border: `1px solid ${BORDER}`, fontSize: 12, color: TEXT }} />
                    <Line type="monotone" dataKey="tempMax" stroke="#f87171" strokeWidth={2} dot={false} name="Max" />
                    <Line type="monotone" dataKey="tempMin" stroke={BLUE} strokeWidth={2} dot={false} name="Min" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="card anim-fade-up delay-3" style={{ padding: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
                <div style={{ width: 4, height: 16, borderRadius: 2, background: BLUE }} />
                <span className="stat-label">Rainfall (mm)</span>
              </div>
              <div style={{ height: 160, marginLeft: -8 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={weather}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,58,42,0.5)" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: TEXT_SEC }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: TEXT_SEC }} axisLine={false} tickLine={false} width={30} />
                    <Tooltip contentStyle={{ background: SURFACE, borderRadius: 12, border: `1px solid ${BORDER}`, fontSize: 12, color: TEXT }} />
                    <Bar dataKey="precipitation" fill={BLUE} radius={[6, 6, 0, 0]} name="Rainfall" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
