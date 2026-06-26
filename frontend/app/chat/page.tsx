"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, Send, Bot, User, Sparkles, Code, Droplets, Thermometer, CloudRain, Sprout, AlertTriangle } from "lucide-react";

const API = "";

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

interface Msg {
  role: "user" | "assistant";
  content: string;
  cypher?: string;
  results?: any[];
  confidence?: string;
}

function Sparkline({ data, color, height = 40, width = 120 }: { data: number[]; color: string; height?: number; width?: number }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width={width} height={height} style={{ overflow: "visible" }}>
      <polyline points={points} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
      {data.map((v, i) => {
        const x = (i / (data.length - 1)) * width;
        const y = height - ((v - min) / range) * height;
        return <circle key={i} cx={x} cy={y} r={2.5} fill={color} />;
      })}
    </svg>
  );
}

function WeatherCard({ tempMax, tempMin, precipitation, humidity }: { tempMax?: number; tempMin?: number; precipitation?: number; humidity?: number }) {
  return (
    <div style={{ background: SURFACE, borderRadius: 12, padding: 12, border: `1px solid ${BORDER}`, marginTop: 8, display: "flex", gap: 12, flexWrap: "wrap" }}>
      {tempMax != null && (
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <Thermometer size={14} color={RED} />
          <span style={{ fontSize: 11, color: TEXT }}>{tempMax}°C / {tempMin}°C</span>
        </div>
      )}
      {humidity != null && (
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <Droplets size={14} color={BLUE} />
          <span style={{ fontSize: 11, color: TEXT }}>{humidity}%</span>
        </div>
      )}
      {precipitation != null && (
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <CloudRain size={14} color={BLUE} />
          <span style={{ fontSize: 11, color: TEXT }}>{precipitation}mm</span>
        </div>
      )}
      <span style={{ fontSize: 10, color: TEXT_SEC, marginLeft: "auto" }}>Today&apos;s weather</span>
    </div>
  );
}

function GrowthBar({ stage, day, stageStart, stageEnd }: { stage: string; day?: number; stageStart?: number; stageEnd?: number }) {
  const pct = stageStart != null && stageEnd != null && day != null
    ? Math.min(100, Math.max(0, ((day - stageStart) / (stageEnd - stageStart)) * 100))
    : 0;
  return (
    <div style={{ background: SURFACE, borderRadius: 12, padding: 12, border: `1px solid ${BORDER}`, marginTop: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: TEXT, display: "flex", alignItems: "center", gap: 4 }}>
          <Sprout size={12} color={GREEN} /> {stage || "Growing"}
        </span>
        <span style={{ fontSize: 11, color: GREEN }}>{Math.round(pct)}%</span>
      </div>
      <div style={{ height: 6, borderRadius: 3, background: BORDER, overflow: "hidden" }}>
        <div style={{ height: "100%", borderRadius: 3, background: GREEN, width: `${pct}%`, transition: "width 0.5s ease" }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4, fontSize: 10, color: TEXT_SEC }}>
        <span>Day {stageStart ?? "0"}</span>
        <span>Day {stageEnd ?? "?"}</span>
      </div>
    </div>
  );
}

function ActionBadge({ action, cause, urgencyHours }: { action: string; cause?: string; urgencyHours?: number }) {
  const urgent = urgencyHours != null && urgencyHours < 24;
  return (
    <div style={{
      background: urgent ? "rgba(248,113,113,0.08)" : "rgba(74,222,128,0.06)",
      borderRadius: 12, padding: 12, border: `1px solid ${urgent ? RED : GREEN}22`, marginTop: 8
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
        <AlertTriangle size={14} color={urgent ? RED : GOLD} />
        <span style={{ fontSize: 12, fontWeight: 700, color: urgent ? RED : GOLD }}>{action}</span>
        {urgencyHours != null && (
          <span style={{ marginLeft: "auto", fontSize: 10, fontWeight: 700, color: urgent ? RED : GOLD, background: `${urgent ? RED : GOLD}15`, padding: "2px 8px", borderRadius: 9999 }}>
            {urgencyHours}h
          </span>
        )}
      </div>
      {cause && <p style={{ fontSize: 11, color: TEXT_SEC, margin: 0 }}>{cause}</p>}
    </div>
  );
}

function extractVisualizations(results: any[] | null) {
  const viz: { ndviData?: number[]; weather?: any; growth?: any; recommendation?: any } = {};
  if (!results) return viz;

  for (const r of results) {
    if (r.ndvi !== undefined) {
      if (!viz.ndviData) viz.ndviData = [];
      viz.ndviData.push(Number(r.ndvi ?? r.NDVI ?? 0));
    }
    if (r.tempMax !== undefined || r.temperatureMax !== undefined) {
      viz.weather = {
        tempMax: Number(r.tempMax ?? r.temperatureMax ?? 0),
        tempMin: Number(r.tempMin ?? r.temperatureMin ?? 0),
        precipitation: Number(r.precipitation ?? 0),
        humidity: Number(r.humidity ?? 0),
      };
    }
    if (r.stage || r.name) {
      viz.growth = {
        stage: r.stage || r.name,
        day: Number(r.seasonDay ?? r.day ?? 0),
        stageStart: Number(r.stageStart ?? r.dayStart ?? 0),
        stageEnd: Number(r.stageEnd ?? r.dayEnd ?? 0),
      };
    }
    if (r.action) {
      viz.recommendation = {
        action: r.action,
        cause: r.cause,
        urgencyHours: Number(r.urgencyHours ?? 0),
      };
    }
    const s = r.subgraph;
    if (s?.plot) {
      const p = s.plot;
      if (p.stage || s.stage) viz.growth = { stage: p.stage || s.stage, day: Number(p.seasonDay ?? 0) };
      if (p.todayRecommendation) viz.recommendation = { action: p.todayRecommendation };
    }
  }
  return viz;
}

function deriveAvailableDataTypes(results: any[] | null, subgraph: any): string[] {
  const types: string[] = [];
  if (!results) return types;

  const hasNdvi = results.some((r: any) => r.ndvi !== undefined || r.NDVI !== undefined);
  const hasWeather = results.some((r: any) => r.tempMax !== undefined || r.temperatureMax !== undefined || r.precipitation !== undefined);
  const hasSoil = results.some((r: any) => r.ph !== undefined || r.soilBaseline_pH !== undefined || r.soilBaseline_N !== undefined);
  const hasGrowth = results.some((r: any) => r.stage || r.name);
  const hasRecommendation = results.some((r: any) => r.action || r.todayRecommendation);

  if (hasNdvi) types.push("ndvi");
  if (hasWeather) types.push("weather");
  if (hasSoil) types.push("soil");
  if (hasGrowth) types.push("growth");
  if (hasRecommendation) types.push("recommendation");

  if (subgraph?.plot) {
    const p = subgraph.plot;
    if (p.soilBaseline_pH != null) { if (!types.includes("soil")) types.push("soil"); }
    if (p.todayRecommendation) { if (!types.includes("recommendation")) types.push("recommendation"); }
  }

  return types;
}

function getDynamicSuggestions(types: string[]): string[] {
  const suggestions: string[] = [];
  if (types.includes("soil")) {
    suggestions.push("What's my soil pH?", "How's my nitrogen?");
  }
  if (types.includes("weather")) {
    suggestions.push("What's today's weather?", "Will it rain?");
  }
  if (types.includes("ndvi")) {
    suggestions.push("Show my NDVI trend", "Is my crop stressed?");
  }
  if (types.includes("growth")) {
    suggestions.push("What growth stage am I in?", "When will I harvest?");
  }
  if (types.includes("recommendation")) {
    suggestions.push("What should I do today?", "Any pest risks?");
  }
  if (suggestions.length === 0) {
    suggestions.push("What is my current growth stage?");
  }
  return suggestions;
}

export default function ChatPage() {
  const router = useRouter();
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: "assistant", content: "Habari! I'm FarmWise AI. Ask me anything about your farm — growth stage, NDVI trends, pest risks, or today's recommendation. I also speak Swahili!" }
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  const send = async (text: string) => {
    if (!text.trim() || sending) return;
    const fid = localStorage.getItem("farmerId");
    if (!fid) { router.push("/onboarding"); return; }
    setMsgs(p => [...p, { role: "user", content: text }]);
    setInput(""); setSending(true);
    try {
      const r = await fetch(`${API}/api/chat/query`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ farmerId: fid, message: text })
      });
      const d = await r.json();
      setMsgs(p => [...p, {
        role: "assistant",
        content: d.answer || "Sorry, I could not process that.",
        cypher: d.cypher || undefined,
        results: d.results || undefined,
        confidence: d.confidence || "medium",
      }]);
    } catch {
      setMsgs(p => [...p, { role: "assistant", content: "Could not reach the AI service." }]);
    }
    setSending(false);
  };

  const collectiveResults = useMemo(() => {
    const all: any[] = [];
    msgs.forEach(m => {
      if (m.results) all.push(...m.results);
    });
    return all;
  }, [msgs]);

  const collectiveSubgraph = useMemo(() => {
    for (const m of msgs) {
      if (m.results) {
        for (const r of m.results) {
          if (r.subgraph) return r.subgraph;
        }
      }
    }
    return null;
  }, [msgs]);

  const availableTypes = useMemo(() =>
    deriveAvailableDataTypes(collectiveResults, collectiveSubgraph),
    [collectiveResults, collectiveSubgraph]
  );

  const dynamicSuggestions = useMemo(() =>
    getDynamicSuggestions(availableTypes),
    [availableTypes]
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100dvh", background: BG }}>
      <header style={{ position: "sticky", top: 0, zIndex: 10, background: BG, padding: "12px 20px 8px", paddingTop: "calc(12px + var(--safe-top))", borderBottom: `1px solid ${BORDER}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <a href="/" style={{ width: 34, height: 34, borderRadius: 10, background: SURFACE, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", textDecoration: "none" }}>
            <ChevronLeft size={18} color={TEXT} />
          </a>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: GREEN, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Bot size={16} color="#0d1f15" />
            </div>
            <div>
              <p style={{ fontSize: 15, fontWeight: 700, color: TEXT }}>FarmWise AI</p>
              <p style={{ fontSize: 10, color: TEXT_SEC }}>Ask in English or Swahili</p>
            </div>
          </div>
        </div>
      </header>

      <main style={{ flex: 1, overflowY: "auto", padding: "12px 16px", display: "flex", flexDirection: "column", gap: 10 }}>
        {msgs.map((m, i) => {
          const isLastAssistant = i > 0 && m.role === "assistant";
          const viz = m.results ? extractVisualizations(m.results) : {};

          return (
            <div key={i} className="anim-fade-up" style={{ display: "flex", flexDirection: "column", gap: 6, animationDelay: `${i * 0.03}s` }}>
              <div style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
                <div style={{ maxWidth: "86%", display: "flex", alignItems: "flex-start", gap: 8, flexDirection: m.role === "user" ? "row-reverse" : "row" }}>
                  <div style={{ width: 30, height: 30, borderRadius: 8, background: m.role === "user" ? GREEN : SURFACE, border: m.role === "user" ? "none" : `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    {m.role === "user" ? <User size={14} color="#0d1f15" /> : <Bot size={14} color={GREEN} />}
                  </div>
                  <div style={{ borderRadius: 14, padding: "10px 14px", background: m.role === "user" ? GREEN : SURFACE, color: m.role === "user" ? "#0d1f15" : TEXT, border: m.role === "user" ? "none" : `1px solid ${BORDER}`, boxShadow: "0 4px 24px rgba(0,0,0,0.3)" }}>
                    <p style={{ fontSize: 13, lineHeight: 1.6, whiteSpace: "pre-wrap", margin: 0 }}>{m.content}</p>
                    {m.cypher && (
                      <details style={{ marginTop: 8 }}>
                        <summary style={{ fontSize: 10, cursor: "pointer", opacity: 0.5, display: "flex", alignItems: "center", gap: 4 }}><Code size={11} /> Cypher</summary>
                        <pre style={{ marginTop: 6, fontSize: 10, fontFamily: "monospace", background: "rgba(0,0,0,0.2)", borderRadius: 8, padding: 8, overflowX: "auto", color: TEXT_SEC }}>{m.cypher}</pre>
                      </details>
                    )}
                  </div>
                </div>
              </div>

              {m.role === "assistant" && m.confidence === "low" && i > 0 && (
                <div style={{ marginLeft: 38, maxWidth: "86%" }}>
                  <DayOneBanner results={collectiveResults} subgraph={collectiveSubgraph} />
                </div>
              )}

              {m.role === "assistant" && viz && (
                <div style={{ marginLeft: 38, maxWidth: "78%" }}>
                  {viz.ndviData && viz.ndviData.length > 1 && (
                    <div style={{ background: SURFACE, borderRadius: 12, padding: 10, border: `1px solid ${BORDER}` }}>
                      <span style={{ fontSize: 10, fontWeight: 600, color: TEXT_SEC, textTransform: "uppercase", letterSpacing: "0.04em" }}>NDVI Trend</span>
                      <Sparkline data={viz.ndviData} color={GREEN} height={44} width={140} />
                    </div>
                  )}
                  {viz.weather && (viz.weather.tempMax != null || viz.weather.humidity != null) && (
                    <WeatherCard {...viz.weather} />
                  )}
                  {viz.growth && viz.growth.stage && (
                    <GrowthBar {...viz.growth} />
                  )}
                  {viz.recommendation && viz.recommendation.action && (
                    <ActionBadge {...viz.recommendation} />
                  )}
                </div>
              )}
            </div>
          );
        })}

        {msgs.length === 1 && (
          <div className="anim-fade-up delay-2" style={{ paddingTop: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
              <Sparkles size={14} color={GREEN} />
              <span style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: TEXT_SEC }}>Try asking</span>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {dynamicSuggestions.map(s => (
                <button key={s} onClick={() => send(s)} disabled={sending}
                  style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 9999, padding: "8px 14px", fontSize: 12, fontWeight: 500, color: TEXT_SEC, cursor: "pointer" }}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {sending && (
          <div style={{ display: "flex", justifyContent: "flex-start" }} className="anim-fade-up">
            <div style={{ background: SURFACE, borderRadius: 14, padding: "12px 18px", border: `1px solid ${BORDER}`, display: "flex", gap: 4 }}>
              {[0, 1, 2].map(i => (
                <div key={i} style={{ width: 7, height: 7, borderRadius: "50%", background: GREEN, animation: `bounceDot 1.4s ease-in-out ${i * 0.16}s infinite` }} />
              ))}
            </div>
          </div>
        )}
        <div ref={bottom} />
      </main>

      <div style={{ position: "sticky", bottom: 0, background: BG, borderTop: `1px solid ${BORDER}`, padding: "10px 16px", paddingBottom: "calc(10px + var(--safe-bottom))" }}>
        <div style={{ display: "flex", gap: 8, background: SURFACE, borderRadius: 14, padding: "4px 6px 4px 16px", border: `1px solid ${BORDER}` }}>
          <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && send(input)}
            placeholder="Ask about your farm..."
            style={{ flex: 1, border: "none", outline: "none", fontSize: 14, background: "transparent", color: TEXT, padding: "8px 0", fontFamily: "'DM Sans', sans-serif" }} />
          <button onClick={() => send(input)} disabled={sending || !input.trim()}
            style={{ width: 38, height: 38, borderRadius: 10, background: GREEN, border: "none", color: "#0d1f15", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", opacity: sending || !input.trim() ? 0.4 : 1 }}>
            <Send size={15} />
          </button>
        </div>
      </div>
    </div>
  );
}

function DayOneBanner({ results, subgraph }: { results: any[] | null; subgraph: any }) {
  const types = deriveAvailableDataTypes(results, subgraph);
  const hasSoil = types.includes("soil");
  const hasWeather = types.includes("weather");
  const hasNdvi = types.includes("ndvi");

  return (
    <div style={{
      background: "rgba(212,168,68,0.08)", borderRadius: 14, padding: 14,
      border: `1px solid ${GOLD}33`, marginTop: 4
    }}>
      <p style={{ fontSize: 18, margin: "0 0 8px" }}>We&apos;re just getting started!</p>
      <p style={{ fontSize: 12, color: TEXT_SEC, margin: "0 0 10px", lineHeight: 1.5 }}>
        Here&apos;s what we&apos;ve collected so far:
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <span style={{ fontSize: 12, color: hasSoil ? GREEN : TEXT_SEC }}>
          {hasSoil ? "✓" : "○"} Soil analysis (pH, nitrogen, carbon)
        </span>
        <span style={{ fontSize: 12, color: hasWeather ? GREEN : TEXT_SEC }}>
          {hasWeather ? "✓" : "○"} Today&apos;s weather
        </span>
        <span style={{ fontSize: 12, color: hasNdvi ? GREEN : TEXT_SEC }}>
          {hasNdvi ? "✓" : "○"} Satellite NDVI (arrives in 3-5 days)
        </span>
      </div>
      <p style={{ fontSize: 11, color: GOLD, margin: "10px 0 0", fontStyle: "italic" }}>
        Ask me about your soil or weather data!
      </p>
    </div>
  );
}
