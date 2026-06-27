"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  LineChart, Line, ComposedChart, AreaChart, Area, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend,
} from "recharts";

const TABS = [
  "Overview", "Telemetry", "Alerts", "Observations",
  "Pests", "Soil", "Actions", "Finances", "Forecast", "Farm Chat", "Certificate",
];

export default function PlotDetailPage() {
  const params = useParams();
  const router = useRouter();
  const plotId = params.plotId as string;
  const [activeTab, setActiveTab] = useState("Overview");
  const [plot, setPlot] = useState<any>(null);
  const [activeSeason, setActiveSeason] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState("");

  useEffect(() => {
    const t = localStorage.getItem("farmwise_token");
    if (!t) { router.push("/login"); return; }
    setToken(t);
  }, [router]);

  useEffect(() => {
    if (!token || !plotId) return;
    fetch(`/api/plots/${plotId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (r) => {
        const text = await r.text();
        if (!r.ok) throw new Error(`Server error (${r.status}): ${text.slice(0, 200)}`);
        try { return JSON.parse(text); }
        catch { throw new Error(`Invalid response from server`); }
      })
      .then((data) => { setPlot(data.p || data); })
      .catch((err) => { console.error("Plot load failed:", err); setPlot(null); })
      .finally(() => setLoading(false));
  }, [token, plotId]);

  useEffect(() => {
    if (!token || !plotId) return;
    fetch(`/api/plots/${plotId}/seasons`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((seasons: any[]) => {
        const active = seasons.find((s: any) => s.status === "ACTIVE");
        setActiveSeason(active || null);
      })
      .catch(console.error);
  }, [token, plotId]);

  if (loading) {
    return (
      <div className="min-h-dvh bg-soil-900 flex items-center justify-center">
        <p className="text-muted">Loading plot...</p>
      </div>
    );
  }

  if (!plot) {
    return (
      <div className="min-h-dvh bg-soil-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-cream text-lg">Plot not found</p>
          <button onClick={() => router.push("/dashboard")} className="mt-4 text-canopy-300">
            Back to Dashboard
          </button>
      </div>
    </div>
  );
}
/* ─── Overview Tab ─── */
function OverviewTab({ plotId, token, plot, activeSeason, setActiveTab }: {
  plotId: string; token: string; plot: any; activeSeason: any; setActiveTab: (t: string) => void;
}) {
  const [latest, setLatest] = useState<any>(null);
  const router = useRouter();

  useEffect(() => {
    if (!activeSeason?.seasonId) return;
    fetch(`/api/seasons/${activeSeason.seasonId}/snapshots/latest`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setLatest(data.d || data))
      .catch(console.error);
  }, [activeSeason, token]);

  return (
    <div className="space-y-4">
      <div className="bg-soil-800 rounded-2xl border border-border p-6">
        <h3 className="text-xs uppercase tracking-widest text-muted mb-3">Current Season</h3>
        {activeSeason ? (
          <div className="space-y-2">
            <InfoRow label="Variety" value={activeSeason.varietyName} />
            <InfoRow label="Planted" value={activeSeason.plantingDate} />
            <InfoRow label="Expected Harvest" value={activeSeason.expectedHarvestDate || "—"} />
            <InfoRow label="Growth Stage" value={activeSeason.growthStage || "Unknown"} />
            <InfoRow label="Status" value={activeSeason.status} />
          </div>
        ) : (
          <div className="text-center py-4">
            <p className="text-muted text-sm mb-3">No active season. Start a new one to monitor crop health.</p>
            <button
              onClick={() => {
                const plantingDate = new Date().toISOString().split("T")[0];
                const variety = prompt("Potato variety? (e.g. Shangi)") || "Shangi";
                fetch(`/api/plots/${plotId}/seasons`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                  body: JSON.stringify({ plantingDate, varietyName: variety }),
                })
                  .then((r) => r.json())
                  .then(() => window.location.reload())
                  .catch((e) => alert("Failed: " + e.message));
              }}
              className="px-6 py-2 bg-canopy-500 hover:bg-canopy-400 text-white font-semibold rounded-lg transition text-sm"
            >
              + Start New Season
            </button>
          </div>
        )}
      </div>

      {latest && (
        <div className="bg-soil-800 rounded-2xl border border-border p-6">
          <h3 className="text-xs uppercase tracking-widest text-muted mb-4">Latest Reading — {latest.date}</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <MetricCard label="Temperature" value={`${latest.daily_avg_temp_c ?? "—"}°C`} />
            <MetricCard label="Precipitation" value={`${latest.daily_precip_mm ?? "—"} mm`} />
            <MetricCard label="Humidity" value={`${latest.daily_avg_humidity ?? "—"}%`} />
            <MetricCard
              label="NDVI"
              value={latest.has_satellite_data ? (latest.mean_ndvi?.toFixed(3) ?? "—") : "—"}
              sub={latest.has_satellite_data ? undefined : "No satellite data"}
            />
            <MetricCard label="EVI" value={latest.has_satellite_data ? (latest.mean_evi?.toFixed(3) ?? "—") : "—"} />
            <MetricCard label="Cloud Cover" value={latest.has_satellite_data ? `${latest.cloud_cover_percentage ?? "—"}%` : "—"} />
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <QuickAction label="Log Observation" onClick={() => setActiveTab("Observations")} />
        <QuickAction label="Log Expense" onClick={() => setActiveTab("Finances")} />
        <QuickAction label="Record Sale" onClick={() => setActiveTab("Finances")} />
        <QuickAction label="Generate Forecast" onClick={() => setActiveTab("Forecast")} />
      </div>
    </div>
  );
}

function QuickAction({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="bg-soil-800 border border-border rounded-xl p-4 text-cream text-sm font-medium hover:border-canopy-400 transition text-center"
    >
      {label}
    </button>
  );
}

/* ─── Telemetry Tab ─── */
function TelemetryTab({ plotId, token, activeSeason }: {
  plotId: string; token: string; activeSeason: any;
}) {
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [latest, setLatest] = useState<any>(null);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [selectedDay, setSelectedDay] = useState<any>(null);

  useEffect(() => {
    if (!activeSeason?.seasonId) return;
    fetch(`/api/seasons/${activeSeason.seasonId}/snapshots?days=30`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data: any[]) => {
        const snaps = Array.isArray(data) ? data : [];
        setSnapshots(snaps);
        if (snaps.length > 0) setSelectedDate(snaps[snaps.length - 1].d?.date || snaps[snaps.length - 1].date || "");
      })
      .catch(console.error);

    fetch(`/api/seasons/${activeSeason.seasonId}/snapshots/latest`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setLatest(data.d || data))
      .catch(console.error);
  }, [activeSeason, token]);

  useEffect(() => {
    if (!selectedDate) { setSelectedDay(null); return; }
    const day = snapshots.find((s: any) => (s.d?.date || s.date) === selectedDate);
    setSelectedDay(day?.d || day || null);
  }, [selectedDate, snapshots]);

  const chartData = snapshots.map((s: any) => {
    const d = s.d || s;
    return {
      date: d.date,
      temp: d.daily_avg_temp_c,
      precip: d.daily_precip_mm,
      humidity: d.daily_avg_humidity,
      ndvi: d.has_satellite_data ? d.mean_ndvi : null,
      hasSat: d.has_satellite_data,
      rolling5: d.rolling_5d_precip,
      rolling10: d.rolling_10d_precip,
      rolling14: d.rolling_14d_precip,
    };
  });

  const last7 = chartData.slice(-7);
  const ndviData = chartData.filter((d: any) => d.ndvi != null);

  if (!activeSeason?.seasonId) {
    return (
      <div className="bg-soil-800 rounded-2xl border border-border p-10 text-center">
        <p className="text-muted text-sm">No active season. Start a season to view telemetry.</p>
      </div>
    );
  }

  if (snapshots.length === 0) {
    return (
      <div className="bg-soil-800 rounded-2xl border border-border p-10 text-center">
        <p className="text-cream mb-2">No weather data yet.</p>
        <p className="text-muted text-sm">Data appears after daily ingestions.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Day selector */}
      <div className="bg-soil-800 rounded-2xl border border-border p-4">
        <label className="text-xs uppercase tracking-widest text-muted block mb-2">View Specific Day</label>
        <select
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
          className="w-full bg-soil-700 border border-border rounded-lg px-4 py-2.5 text-cream text-sm focus:outline-none focus:border-canopy-400"
        >
          {chartData.map((d: any) => (
            <option key={d.date} value={d.date}>{d.date}</option>
          ))}
        </select>

        {selectedDay && (
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
            <MetricCard label="Temp" value={`${selectedDay.daily_avg_temp_c ?? "—"}°C`} />
            <MetricCard label="Precip" value={`${selectedDay.daily_precip_mm ?? "—"} mm`} />
            <MetricCard label="Humidity" value={`${selectedDay.daily_avg_humidity ?? "—"}%`} />
            <MetricCard label="NDVI" value={selectedDay.has_satellite_data ? (selectedDay.mean_ndvi?.toFixed(3) ?? "—") : "N/A"} />
            <MetricCard label="EVI" value={selectedDay.has_satellite_data ? (selectedDay.mean_evi?.toFixed(3) ?? "—") : "N/A"} />
            <MetricCard label="Cloud" value={`${selectedDay.cloud_cover_percentage ?? "—"}%`} />
            <MetricCard label="5-Day Precip" value={`${selectedDay.rolling_5d_precip ?? "—"} mm`} />
            <MetricCard label="10-Day Precip" value={`${selectedDay.rolling_10d_precip ?? "—"} mm`} />
            <MetricCard label="14-Day Precip" value={`${selectedDay.rolling_14d_precip ?? "—"} mm`} />
            <MetricCard label="5-Day Temp Avg" value={`${selectedDay.rolling_5d_temp_avg ?? "—"}°C`} />
          </div>
        )}
      </div>

      {/* Chart A: 7-Day Weather */}
      <div className="bg-soil-800 rounded-2xl border border-border p-6">
        <h3 className="text-xs uppercase tracking-widest text-muted mb-4">7-Day Weather</h3>
        {last7.length === 0 ? (
          <p className="text-muted text-sm text-center py-8">No weather data yet. Data appears after daily ingestions.</p>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <ComposedChart data={last7} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#3d3020" />
              <XAxis dataKey="date" stroke="#8a8070" fontSize={11} tick={{ fill: "#8a8070" }} />
              <YAxis yAxisId="left" stroke="#7ec88a" fontSize={11} tick={{ fill: "#8a8070" }} unit="°C" />
              <YAxis yAxisId="right" orientation="right" stroke="#f0cc60" fontSize={11} tick={{ fill: "#8a8070" }} unit="mm" />
              <Tooltip
                contentStyle={{ backgroundColor: "#2d2010", border: "1px solid #3d3020", borderRadius: 8, color: "#f5f0e8" }}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: "#8a8070" }} />
              <Bar yAxisId="right" dataKey="precip" fill="#f0cc60" name="Precip (mm)" radius={[4, 4, 0, 0]} barSize={20} />
              <Line yAxisId="left" type="monotone" dataKey="temp" stroke="#7ec88a" strokeWidth={2} name="Temp (°C)" dot={{ r: 3 }} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Chart B: 30-Day NDVI */}
      <div className="bg-soil-800 rounded-2xl border border-border p-6">
        <h3 className="text-xs uppercase tracking-widest text-muted mb-4">30-Day NDVI</h3>
        {ndviData.length === 0 ? (
          <p className="text-muted text-sm text-center py-8">No satellite data available (cloud cover).</p>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={ndviData} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#3d3020" />
              <XAxis dataKey="date" stroke="#8a8070" fontSize={11} tick={{ fill: "#8a8070" }} />
              <YAxis domain={[0, 1]} stroke="#8a8070" fontSize={11} tick={{ fill: "#8a8070" }} />
              <Tooltip
                contentStyle={{ backgroundColor: "#2d2010", border: "1px solid #3d3020", borderRadius: 8, color: "#f5f0e8" }}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: "#8a8070" }} />
              <ReferenceLine y={0.3} stroke="#c03020" strokeDasharray="5 5" label={{ value: "Stress 0.3", fill: "#f07060", fontSize: 10, position: "left" }} />
              <ReferenceLine y={0.5} stroke="#2d8a3e" strokeDasharray="5 5" label={{ value: "Healthy 0.5", fill: "#2d8a3e", fontSize: 10, position: "left" }} />
              <Line
                type="monotone"
                dataKey="ndvi"
                stroke="#7ec88a"
                strokeWidth={2}
                name="NDVI"
                dot={{ r: 2, fill: "#7ec88a" }}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Chart C: Rolling Precipitation */}
      <div className="bg-soil-800 rounded-2xl border border-border p-6">
        <h3 className="text-xs uppercase tracking-widest text-muted mb-4">Rolling Precipitation</h3>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#3d3020" />
            <XAxis dataKey="date" stroke="#8a8070" fontSize={11} tick={{ fill: "#8a8070" }} />
            <YAxis stroke="#8a8070" fontSize={11} tick={{ fill: "#8a8070" }} unit="mm" />
            <Tooltip
              contentStyle={{ backgroundColor: "#2d2010", border: "1px solid #3d3020", borderRadius: 8, color: "#f5f0e8" }}
            />
            <Legend wrapperStyle={{ fontSize: 12, color: "#8a8070" }} />
            <ReferenceLine y={40} stroke="#c03020" strokeDasharray="5 5" label={{ value: "Waterlog 40mm", fill: "#f07060", fontSize: 10 }} />
            <Area type="monotone" dataKey="rolling5" stroke="#7ec88a" fill="#7ec88a" fillOpacity={0.15} name="5-Day" />
            <Area type="monotone" dataKey="rolling10" stroke="#f0cc60" fill="#f0cc60" fillOpacity={0.12} name="10-Day" />
            <Area type="monotone" dataKey="rolling14" stroke="#f07060" fill="#f07060" fillOpacity={0.1} name="14-Day" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Latest snapshot detail grid */}
      {latest && (
        <div className="bg-soil-800 rounded-2xl border border-border p-6">
          <h3 className="text-xs uppercase tracking-widest text-muted mb-4">Latest Snapshot Detail</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <MetricCard label="Date" value={latest.date} />
            <MetricCard label="Temp" value={`${latest.daily_avg_temp_c ?? "—"}°C`} />
            <MetricCard label="Precip" value={`${latest.daily_precip_mm ?? "—"} mm`} />
            <MetricCard label="Humidity" value={`${latest.daily_avg_humidity ?? "—"}%`} />
            <MetricCard label="NDVI" value={latest.has_satellite_data ? (latest.mean_ndvi?.toFixed(3) ?? "—") : "N/A"} />
            <MetricCard label="EVI" value={latest.has_satellite_data ? (latest.mean_evi?.toFixed(3) ?? "—") : "N/A"} />
            <MetricCard label="Cloud Cover" value={`${latest.cloud_cover_percentage ?? "—"}%`} />
            <MetricCard label="5-Day Precip" value={`${latest.rolling_5d_precip ?? "—"} mm`} />
            <MetricCard label="10-Day Precip" value={`${latest.rolling_10d_precip ?? "—"} mm`} />
            <MetricCard label="14-Day Precip" value={`${latest.rolling_14d_precip ?? "—"} mm`} />
            <MetricCard label="5-Day Temp Avg" value={`${latest.rolling_5d_temp_avg ?? "—"}°C`} />
            <MetricCard label="5-Day Hum Avg" value={`${latest.rolling_5d_humidity_avg ?? "—"}%`} />
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Alerts Tab ─── */
function AlertsTab({ plotId, token, activeSeason }: {
  plotId: string; token: string; activeSeason: any;
}) {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [actionForm, setActionForm] = useState<{alertId: string; action: string; cost: string; cat: string; desc: string} | null>(null);

  useEffect(() => {
    if (!activeSeason?.seasonId) return;
    fetch(`/api/seasons/${activeSeason.seasonId}/alerts`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then(setAlerts)
      .catch(console.error);
  }, [activeSeason, token]);

  const submitIntervention = async () => {
    if (!actionForm) return;
    const { alertId, action, cost, cat, desc } = actionForm;
    if (!action.trim() || !cost) return;
    const res = await fetch(`/api/alerts/${alertId}/interventions`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        actionTaken: action,
        date: new Date().toISOString().split("T")[0],
        category: cat || "Pesticide",
        description: desc || action,
        amount: parseFloat(cost),
      }),
    });
    if (res.ok) {
      setAlerts((prev) => prev.map((a) => (a.alertId === alertId ? { ...a, status: "RESOLVED" } : a)));
      setActionForm(null);
    } else {
      try { const err = await res.json(); alert(err.detail || "Failed to submit intervention"); } catch {}
    }
  };

  return (
    <div className="space-y-3">
      {alerts.length === 0 && (
        <div className="bg-soil-800 rounded-2xl border border-border p-10 text-center">
          <p className="text-3xl mb-2">{'\u2705'}</p>
          <p className="text-cream">No alerts — your crop looks good today.</p>
        </div>
      )}
      {alerts.map((a) => {
        const urgencyColor =
          a.urgency === "HIGH" ? "border-alert-500" : a.urgency === "MEDIUM" ? "border-harvest-500" : "border-canopy-300";
        return (
          <div key={a.alertId} className={`bg-soil-800 rounded-2xl border ${urgencyColor} border-l-4 overflow-hidden`}>
            <button
              onClick={() => setExpanded(expanded === a.alertId ? null : a.alertId)}
              className="w-full text-left p-4"
            >
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-cream font-semibold">{a.detectedCondition}</span>
                  <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${
                    a.status === "ACTIVE" ? "bg-alert-500/20 text-alert-300" : "bg-canopy-600/20 text-canopy-300"
                  }`}>
                    {a.status}
                  </span>
                </div>
                <span className="text-muted text-xs">{a.urgency}</span>
              </div>
            </button>

            {expanded === a.alertId && (
              <div className="px-4 pb-4 space-y-3 border-t border-border pt-3">
                <div>
                  <p className="text-xs text-muted uppercase mb-1">Confidence</p>
                  <p className="text-cream text-sm">{a.confidence != null ? `${(a.confidence * 100).toFixed(0)}%` : "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted uppercase mb-1">Explanation</p>
                  <p className="text-cream text-sm">{a.explanation}</p>
                </div>
                <div className="bg-canopy-600/10 border border-canopy-600/30 rounded-lg p-3">
                  <p className="text-xs text-muted uppercase mb-1">Recommendation</p>
                  <p className="text-canopy-300 text-sm">{a.recommendation}</p>
                </div>
                {a.smsSwahili && (
                  <div>
                    <p className="text-xs text-muted uppercase mb-1">SMS Preview (Swahili)</p>
                    <p className="text-cream text-sm bg-soil-700 rounded-lg p-2">{a.smsSwahili}</p>
                  </div>
                )}
                <div className="flex gap-2 pt-2 flex-wrap">
                  {a.status === "ACTIVE" && (
                    <>
                      <button
                        onClick={() => setActionForm({ alertId: a.alertId, action: a.recommendation || "", cost: "", cat: "Pesticide", desc: a.detectedCondition || "" })}
                        className="px-4 py-2 bg-canopy-500 hover:bg-canopy-400 text-white font-semibold text-sm rounded-lg transition"
                      >
                        Take Action
                      </button>
                      <button
                        onClick={async () => {
                          await fetch(`/api/alerts/${a.alertId}/status`, {
                            method: "PATCH",
                            headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                            body: JSON.stringify({ status: "IGNORED" }),
                          });
                          setAlerts((prev) => prev.map((x) => (x.alertId === a.alertId ? { ...x, status: "IGNORED" } : x)));
                        }}
                        className="px-3 py-2 bg-soil-700 text-muted text-sm rounded-lg hover:text-cream transition"
                      >
                        Ignore
                      </button>
                    </>
                  )}
                  <button
                    onClick={() => {
                      const msg = `Tell me more about: ${a.detectedCondition}. ${a.explanation || ""}`;
                      const el = document.querySelector<HTMLInputElement>('[data-chat-input]');
                      if (el) {
                        el.value = msg;
                        el.dispatchEvent(new Event("input", { bubbles: true }));
                        const tabBtn = [...document.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Farm Chat");
                        tabBtn?.click();
                      }
                    }}
                    className="px-3 py-2 bg-soil-700 text-canopy-300 text-sm rounded-lg hover:bg-soil-600 transition"
                  >
                    Chat about Alert
                  </button>
                </div>

                {/* Intervention form */}
                {actionForm?.alertId === a.alertId && actionForm && (
                  (() => {
                    const af = actionForm!;
                    const update = (patch: Partial<typeof af>) => setActionForm({ ...af, ...patch });
                    return (
                  <div className="bg-soil-700 rounded-xl p-4 space-y-3 mt-2 border border-canopy-500/30">
                    <p className="text-cream text-sm font-semibold">Record Your Action</p>
                    <div>
                      <label className="text-muted text-xs mb-1 block">What did you do? *</label>
                      <textarea
                        value={af.action}
                        onChange={(e) => update({ action: e.target.value })}
                        placeholder="e.g. Applied Ridomil fungicide spray"
                        rows={2}
                        className="w-full bg-soil-800 border border-border rounded-lg px-3 py-2 text-cream text-sm placeholder-muted focus:outline-none focus:border-canopy-400 resize-none"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-muted text-xs mb-1 block">Category *</label>
                        <select
                          value={af.cat}
                          onChange={(e) => update({ cat: e.target.value })}
                          className="w-full bg-soil-800 border border-border rounded-lg px-3 py-2 text-cream text-sm"
                        >
                          {["Pesticide","Fertilizer","Labour","Irrigation","Transport","Seed","Land Preparation"].map((c) => (
                            <option key={c} value={c}>{c}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="text-muted text-xs mb-1 block">Cost (KES) *</label>
                        <input
                          type="number"
                          value={af.cost}
                          onChange={(e) => update({ cost: e.target.value })}
                          placeholder="e.g. 850"
                          className="w-full bg-soil-800 border border-border rounded-lg px-3 py-2 text-cream text-sm placeholder-muted focus:outline-none focus:border-canopy-400"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-muted text-xs mb-1 block">Description</label>
                      <input
                        value={af.desc}
                        onChange={(e) => update({ desc: e.target.value })}
                        placeholder="e.g. Ridomil 500g"
                        className="w-full bg-soil-800 border border-border rounded-lg px-3 py-2 text-cream text-sm placeholder-muted focus:outline-none focus:border-canopy-400"
                      />
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={submitIntervention}
                        disabled={!af.action.trim() || !af.cost}
                        className="px-4 py-2 bg-canopy-500 hover:bg-canopy-400 text-white font-semibold text-sm rounded-lg transition disabled:opacity-50"
                      >
                        Submit &amp; Resolve Alert
                      </button>
                      <button
                        onClick={() => setActionForm(null)}
                        className="px-4 py-2 bg-soil-800 text-muted text-sm rounded-lg hover:text-cream transition"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                    );
                  })()
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ─── Observations Tab ─── */
function ObservationsTab({ plotId, token, activeSeason }: {
  plotId: string; token: string; activeSeason: any;
}) {
  const [observations, setObservations] = useState<any[]>([]);
  const [notes, setNotes] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
  const [submitting, setSubmitting] = useState(false);

  const fetchObs = useCallback(() => {
    if (!activeSeason?.seasonId) return;
    fetch(`/api/seasons/${activeSeason.seasonId}/observations`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setObservations(Array.isArray(data) ? data : []))
      .catch(console.error);
  }, [activeSeason, token]);

  useEffect(() => { fetchObs(); }, [fetchObs]);

  const submit = async () => {
    if (!notes.trim()) return;
    if (!activeSeason?.seasonId) return;
    setSubmitting(true);
    await fetch(`/api/seasons/${activeSeason.seasonId}/observations`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ notes, imageUrl: imageUrl || undefined, date }),
    });
    setNotes("");
    setImageUrl("");
    setSubmitting(false);
    fetchObs();
  };

  return (
    <div className="space-y-4">
      <div className="bg-soil-800 rounded-2xl border border-border p-6">
        <h3 className="text-xs uppercase tracking-widest text-muted mb-4">Add Observation</h3>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="What did you see in the field today?"
          rows={3}
          className="w-full bg-soil-700 border border-border rounded-lg px-4 py-3 text-cream placeholder-muted focus:outline-none focus:border-canopy-400 resize-none text-sm"
        />
        <div className="mt-3 space-y-3">
          <input
            type="text"
            value={imageUrl}
            onChange={(e) => setImageUrl(e.target.value)}
            placeholder="Photo URL (optional)"
            className="w-full bg-soil-700 border border-border rounded-lg px-4 py-3 text-cream placeholder-muted focus:outline-none focus:border-canopy-400 text-sm"
          />
          <div className="flex gap-3">
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="bg-soil-700 border border-border rounded-lg px-3 py-2 text-cream text-sm flex-1"
            />
            <button
              onClick={submit}
              disabled={submitting || !notes.trim()}
              className="px-4 py-2 bg-canopy-500 hover:bg-canopy-400 text-white font-semibold text-sm rounded-lg transition disabled:opacity-50"
            >
              {submitting ? "Interpreting observation..." : "Submit Observation"}
            </button>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {observations.map((o: any) => {
          const obs = o.o || o;
          return (
            <div key={obs.observationId} className="bg-soil-800 rounded-2xl border border-border p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-muted text-xs">{obs.date}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  obs.interpretationStatus === "CRITICAL" ? "bg-alert-500/20 text-alert-300"
                  : obs.interpretationStatus === "WARNING" ? "bg-harvest-500/20 text-harvest-300"
                  : "bg-canopy-600/20 text-canopy-300"
                }`}>
                  {obs.interpretationStatus || "PENDING"}
                </span>
              </div>
              <p className="text-cream text-sm">{obs.notes}</p>
              {obs.imageUrl && (
                <div className="mt-2">
                  <img
                    src={obs.imageUrl}
                    alt="Observation"
                    className="rounded-lg max-h-48 object-cover border border-border"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                  />
                </div>
              )}
              {obs.interpretation && (
                <div className="mt-2 bg-soil-700 rounded-lg p-3">
                  <p className="text-muted text-xs">{obs.interpretation}</p>
                </div>
              )}
            </div>
          );
        })}
        {observations.length === 0 && (
          <div className="bg-soil-800 rounded-2xl border border-border p-10 text-center">
            <p className="text-muted text-sm">No observations yet. Log your first field observation above.</p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Pests & Diseases Tab ─── */
function PestsTab({ plotId, token, activeSeason }: {
  plotId: string; token: string; activeSeason: any;
}) {
  const [pests, setPests] = useState<any>(null);
  const [conditions, setConditions] = useState<any>(null);

  useEffect(() => {
    if (!activeSeason?.seasonId) return;
    const sid = activeSeason.seasonId;
    Promise.all([
      fetch(`/api/seasons/${sid}/pests`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      fetch(`/api/seasons/${sid}/weather-conditions`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
    ]).then(([p, c]) => { setPests(p); setConditions(c); }).catch(console.error);
  }, [activeSeason, token]);

  if (!activeSeason?.seasonId) {
    return <div className="bg-soil-800 rounded-2xl border border-border p-10 text-center"><p className="text-muted">No active season</p></div>;
  }

  return (
    <div className="space-y-4">
      {/* Active Weather Conditions */}
      {conditions && (
        <div className="bg-soil-800 rounded-2xl border border-border p-6">
          <h3 className="text-xs uppercase tracking-widest text-muted mb-3">Current Weather Conditions</h3>
          {conditions.latest && (
            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="bg-soil-700 rounded-xl p-3 text-center">
                <p className="text-muted text-xs">5-Day Precip</p>
                <p className="text-cream font-display font-bold text-xl">{conditions.latest.r5precip} mm</p>
              </div>
              <div className="bg-soil-700 rounded-xl p-3 text-center">
                <p className="text-muted text-xs">Temperature</p>
                <p className="text-cream font-display font-bold text-xl">{conditions.latest.temp}°C</p>
              </div>
              <div className="bg-soil-700 rounded-xl p-3 text-center">
                <p className="text-muted text-xs">Humidity</p>
                <p className="text-cream font-display font-bold text-xl">{conditions.latest.humidity}%</p>
              </div>
            </div>
          )}
          {conditions.active?.length > 0 ? (
            <div className="space-y-2">
              {conditions.active.map((c: any, i: number) => (
                <div key={i} className="bg-soil-700/50 rounded-xl p-3 flex items-center justify-between">
                  <div>
                    <span className="text-cream font-semibold text-sm">{c.condition}</span>
                    <div className="flex gap-1 mt-1 flex-wrap">
                      {c.diseases.map((d: string) => (
                        <span key={d} className="text-xs px-2 py-0.5 rounded-full bg-alert-500/10 text-alert-300">{d}</span>
                      ))}
                    </div>
                  </div>
                  <span className="text-harvest-500 text-xs font-bold">Active</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted text-sm">No disease-favoring conditions detected</p>
          )}
        </div>
      )}

      {/* Pest Risks by Growth Stage */}
      {pests && (
        <div className="bg-soil-800 rounded-2xl border border-border p-6">
          <h3 className="text-xs uppercase tracking-widest text-muted mb-3">
            Pest Risks — {pests.stage || "Unknown"} Stage
          </h3>
          {pests.pests?.length > 0 ? (
            <div className="space-y-3">
              {pests.pests.map((p: any, i: number) => (
                <div key={i} className="bg-soil-700 rounded-xl p-4 border-l-4 border-alert-500/50">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h4 className="text-cream font-display font-bold">{p.name}</h4>
                      {p.scientific && <p className="text-muted text-xs italic">{p.scientific}</p>}
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-canopy-600/20 text-canopy-300">{p.weatherCondition}</span>
                  </div>
                  {p.symptoms?.length > 0 && (
                    <div className="mt-2">
                      <p className="text-muted text-xs mb-1">Detection:</p>
                      <div className="flex gap-1 flex-wrap">
                        {p.symptoms.map((s: string) => (
                          <span key={s} className="text-xs bg-soil-800 px-2 py-0.5 rounded text-cream/70">{s}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {p.treatments?.length > 0 && (
                    <div className="mt-2">
                      <p className="text-muted text-xs mb-1">Recommended Actions:</p>
                      <div className="space-y-1">
                        {p.treatments.map((t: string, j: number) => (
                          <div key={j} className="text-sm text-canopy-300 flex items-start gap-1.5">
                            <span className="text-xs mt-0.5">•</span>
                            <span>{t.replace(/_/g, " ")}</span>
                            {p.methods?.[j] && <span className="text-muted text-xs ml-1">({p.methods[j]})</span>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted text-sm">No pest risks identified for this growth stage</p>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Soil Data Tab ─── */
function SoilTab({ plotId, token }: { plotId: string; token: string }) {
  const [soil, setSoil] = useState<any>(null);

  useEffect(() => {
    fetch(`/api/plots/${plotId}/soil`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json()).then(setSoil).catch(console.error);
  }, [plotId, token]);

  if (!soil) {
    return <div className="bg-soil-800 rounded-2xl border border-border p-10 text-center"><p className="text-muted">Loading soil data...</p></div>;
  }

  const getPHLabel = (ph: number) => ph < 5.5 ? "Acidic" : ph > 7.5 ? "Alkaline" : "Neutral";
  const getPHColor = (ph: number) => ph < 5.5 ? "text-harvest-300" : ph > 7.5 ? "text-alert-300" : "text-canopy-300";

  return (
    <div className="space-y-4">
      <div className="bg-soil-800 rounded-2xl border border-border p-6">
        <h3 className="text-xs uppercase tracking-widest text-muted mb-4">Soil Analysis — {soil.plotName} ({soil.county})</h3>
        <p className="text-muted text-xs mb-4">Source: iSDAsoil 30m resolution &middot; Depth: 0-20 cm</p>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="bg-soil-700 rounded-xl p-4 text-center">
            <p className="text-muted text-xs mb-1">pH</p>
            <p className={`text-3xl font-display font-bold ${getPHColor(soil.ph)}`}>{soil.ph?.toFixed(1)}</p>
            <p className="text-muted text-xs mt-1">{getPHLabel(soil.ph)}</p>
            {soil.targetPH && (
              <p className="text-muted text-xs mt-1">Target: {soil.targetPH}</p>
            )}
          </div>
          <div className="bg-soil-700 rounded-xl p-4 text-center">
            <p className="text-muted text-xs mb-1">Nitrogen (N)</p>
            <p className="text-3xl font-display font-bold text-cream">{soil.nitrogen?.toFixed(1)}</p>
            <p className="text-muted text-xs mt-1">g/kg</p>
            {soil.targetN && (
              <p className={`text-xs mt-1 ${soil.nitrogen < soil.targetN ? "text-harvest-300" : "text-canopy-300"}`}>
                Target: {soil.targetN} g/kg
              </p>
            )}
          </div>
          <div className="bg-soil-700 rounded-xl p-4 text-center">
            <p className="text-muted text-xs mb-1">Carbon (C)</p>
            <p className="text-3xl font-display font-bold text-cream">{soil.carbon?.toFixed(1)}</p>
            <p className="text-muted text-xs mt-1">g/kg</p>
          </div>
          <div className="bg-soil-700 rounded-xl p-4 text-center">
            <p className="text-muted text-xs mb-1">Aluminium</p>
            <p className="text-3xl font-display font-bold text-cream">{soil.aluminium?.toFixed(1)}</p>
            <p className="text-muted text-xs mt-1">mg/kg</p>
            {soil.aluminium > 200 && <p className="text-harvest-300 text-xs mt-1">High — may limit roots</p>}
          </div>
          <div className="bg-soil-700 rounded-xl p-4 text-center">
            <p className="text-muted text-xs mb-1">Organic Carbon</p>
            <p className="text-3xl font-display font-bold text-cream">{soil.organicCarbon?.toFixed(1)}</p>
            <p className="text-muted text-xs mt-1">g/kg</p>
          </div>
        </div>

        {/* Recommendations */}
        {(soil.ph < 5.5 || soil.nitrogen < (soil.targetN || 2)) && (
          <div className="mt-4 bg-harvest-500/10 border border-harvest-500/30 rounded-xl p-4">
            <p className="text-harvest-300 font-semibold text-sm">Soil Amendment Recommendations</p>
            <ul className="mt-2 space-y-1 text-sm text-cream">
              {soil.ph < 5.5 && <li>• Apply lime to raise pH (current: {soil.ph}, target: {soil.targetN ? '≥' + soil.targetN : '5.5-7.0'})</li>}
              {soil.ph > 7.5 && <li>• Consider acidifying amendments (pH {soil.ph} is alkaline)</li>}
              {soil.nitrogen < (soil.targetN || 2) && <li>• Apply nitrogen top-dressing (current: {soil.nitrogen} g/kg, target: {soil.targetN || 2} g/kg)</li>}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Actions Tab ─── */
function ActionsTab({ plotId, token, activeSeason }: {
  plotId: string; token: string; activeSeason: any;
}) {
  const [interventions, setInterventions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!activeSeason?.seasonId) { setLoading(false); return; }
    fetch(`/api/seasons/${activeSeason.seasonId}/alerts`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then(async (alerts: any[]) => {
        const allInterventions: any[] = [];
        for (const alert of alerts) {
          try {
            const res = await fetch(`/api/alerts/${alert.alertId}`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            const detail = await res.json();
            const ints = detail.interventions || detail.d?.interventions || [];
            for (const int of ints) {
              allInterventions.push({ ...int, alertCondition: alert.detectedCondition, alertId: alert.alertId });
            }
          } catch {}
        }
        setInterventions(allInterventions);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [activeSeason, token]);

  if (loading) {
    return (
      <div className="bg-soil-800 rounded-2xl border border-border p-10 text-center">
        <p className="text-muted text-sm">Loading interventions...</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {interventions.length === 0 ? (
        <div className="bg-soil-800 rounded-2xl border border-border p-10 text-center">
          <p className="text-3xl mb-2">{'\uD83D\uDCCB'}</p>
          <p className="text-cream">Intervention timeline</p>
          <p className="text-muted text-sm mt-1">Actions taken against alerts will appear here.</p>
        </div>
      ) : (
        interventions.map((int: any, i: number) => (
          <div key={i} className="bg-soil-800 rounded-2xl border border-border p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-muted">{int.date}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-canopy-600/20 text-canopy-300">
                {int.alertCondition}
              </span>
            </div>
            <p className="text-cream text-sm">{int.actionTaken}</p>
          </div>
        ))
      )}
    </div>
  );
}

/* ─── Finances Tab ─── */
function FinancesTab({ plotId, token, activeSeason }: {
  plotId: string; token: string; activeSeason: any;
}) {
  const [expenses, setExpenses] = useState<any>(null);
  const [sales, setSales] = useState<any>(null);
  const [showExpenseForm, setShowExpenseForm] = useState(false);
  const [showSaleForm, setShowSaleForm] = useState(false);
  const [expForm, setExpForm] = useState({ category: "Fertilizer", description: "", amount: 0, date: new Date().toISOString().split("T")[0] });
  const [saleForm, setSaleForm] = useState({ quantity_kg: 0, unit_price: 0, buyer: "", sale_date: new Date().toISOString().split("T")[0] });

  useEffect(() => {
    if (!activeSeason?.seasonId) return;
    Promise.all([
      fetch(`/api/seasons/${activeSeason.seasonId}/expenses`, {
        headers: { Authorization: `Bearer ${token}` },
      }).then((r) => r.json()),
      fetch(`/api/seasons/${activeSeason.seasonId}/sales`, {
        headers: { Authorization: `Bearer ${token}` },
      }).then((r) => r.json()),
    ])
      .then(([expData, salesData]) => {
        if (expData) setExpenses(expData);
        if (salesData) setSales(salesData);
      })
      .catch(console.error);
  }, [activeSeason, token]);

  const addExpense = async () => {
    if (!activeSeason?.seasonId) return;
    await fetch(`/api/seasons/${activeSeason.seasonId}/expenses`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(expForm),
    });
    setShowExpenseForm(false);
    setExpForm({ category: "Fertilizer", description: "", amount: 0, date: new Date().toISOString().split("T")[0] });
    const res = await fetch(`/api/seasons/${activeSeason.seasonId}/expenses`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    setExpenses(await res.json());
  };

  const addSale = async () => {
    if (!activeSeason?.seasonId) return;
    await fetch(`/api/seasons/${activeSeason.seasonId}/sales`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(saleForm),
    });
    setShowSaleForm(false);
    setSaleForm({ quantity_kg: 0, unit_price: 0, buyer: "", sale_date: new Date().toISOString().split("T")[0] });
    const res = await fetch(`/api/seasons/${activeSeason.seasonId}/sales`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    setSales(await res.json());
  };

  if (!activeSeason?.seasonId) {
    return (
      <div className="bg-soil-800 rounded-2xl border border-border p-10 text-center">
        <p className="text-muted text-sm">No active season. Start a season to track finances.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Expenses */}
      <div className="bg-soil-800 rounded-2xl border border-border p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xs uppercase tracking-widest text-muted">Expenses</h3>
          <button onClick={() => { setShowExpenseForm(!showExpenseForm); setShowSaleForm(false); }} className="text-canopy-300 text-sm">
            + Add Expense
          </button>
        </div>
        {showExpenseForm && (
          <div className="bg-soil-700 rounded-xl p-4 mb-4 space-y-3">
            <select
              value={expForm.category}
              onChange={(e) => setExpForm((f) => ({ ...f, category: e.target.value }))}
              className="w-full bg-soil-900 border border-border rounded-lg px-3 py-2 text-cream text-sm"
            >
              {["Land Preparation", "Seed", "Fertilizer", "Labour", "Pesticide", "Transport", "Irrigation"].map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <input
              placeholder="Description"
              value={expForm.description}
              onChange={(e) => setExpForm((f) => ({ ...f, description: e.target.value }))}
              className="w-full bg-soil-900 border border-border rounded-lg px-3 py-2 text-cream text-sm"
            />
            <input
              type="number"
              placeholder="Amount (KES)"
              value={expForm.amount || ""}
              onChange={(e) => setExpForm((f) => ({ ...f, amount: parseFloat(e.target.value) || 0 }))}
              className="w-full bg-soil-900 border border-border rounded-lg px-3 py-2 text-cream text-sm"
            />
            <input
              type="date"
              value={expForm.date}
              onChange={(e) => setExpForm((f) => ({ ...f, date: e.target.value }))}
              className="w-full bg-soil-900 border border-border rounded-lg px-3 py-2 text-cream text-sm"
            />
            <button
              onClick={addExpense}
              className="w-full bg-canopy-500 hover:bg-canopy-400 text-white font-semibold py-2 rounded-lg text-sm transition"
            >
              Save Expense
            </button>
          </div>
        )}
        {expenses?.expenses?.length > 0 ? (
          <>
            {expenses.expenses.map((e: any, i: number) => (
              <div key={i} className="flex justify-between py-2 border-b border-border/30">
                <div>
                  <span className="text-cream text-sm">{e.description || e.category}</span>
                  <span className="text-muted text-xs ml-2">{e.category}</span>
                </div>
                <span className="text-cream text-sm font-mono">KES {e.amount?.toLocaleString()}</span>
              </div>
            ))}
            {expenses.totalAmount > 0 && (
              <div className="flex justify-between py-2 mt-2 border-t border-border pt-2">
                <span className="text-cream font-semibold">Total</span>
                <span className="text-cream font-bold font-mono">KES {expenses.totalAmount?.toLocaleString()}</span>
              </div>
            )}
          </>
        ) : (
          <p className="text-muted text-sm text-center py-4">No expenses recorded yet.</p>
        )}

        {expenses?.byCategory && Object.keys(expenses.byCategory).length > 0 && (
          <div className="mt-4 pt-4 border-t border-border">
            <h4 className="text-xs uppercase tracking-widest text-muted mb-2">By Category</h4>
            {Object.entries(expenses.byCategory).map(([cat, data]: [string, any]) => (
              <div key={cat} className="flex justify-between py-1 text-sm">
                <span className="text-muted">{cat}</span>
                <span className="text-cream font-mono text-xs">KES {data.total?.toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Sales */}
      <div className="bg-soil-800 rounded-2xl border border-border p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xs uppercase tracking-widest text-muted">Sales</h3>
          <button onClick={() => { setShowSaleForm(!showSaleForm); setShowExpenseForm(false); }} className="text-harvest-300 text-sm">
            + Record Sale
          </button>
        </div>
        {showSaleForm && (
          <div className="bg-soil-700 rounded-xl p-4 mb-4 space-y-3">
            <input
              type="number"
              placeholder="Quantity (kg)"
              value={saleForm.quantity_kg || ""}
              onChange={(e) => setSaleForm((f) => ({ ...f, quantity_kg: parseFloat(e.target.value) || 0 }))}
              className="w-full bg-soil-900 border border-border rounded-lg px-3 py-2 text-cream text-sm"
            />
            <input
              type="number"
              placeholder="Unit Price (KES/kg)"
              value={saleForm.unit_price || ""}
              onChange={(e) => setSaleForm((f) => ({ ...f, unit_price: parseFloat(e.target.value) || 0 }))}
              className="w-full bg-soil-900 border border-border rounded-lg px-3 py-2 text-cream text-sm"
            />
            <input
              placeholder="Buyer name"
              value={saleForm.buyer}
              onChange={(e) => setSaleForm((f) => ({ ...f, buyer: e.target.value }))}
              className="w-full bg-soil-900 border border-border rounded-lg px-3 py-2 text-cream text-sm"
            />
            <input
              type="date"
              value={saleForm.sale_date}
              onChange={(e) => setSaleForm((f) => ({ ...f, sale_date: e.target.value }))}
              className="w-full bg-soil-900 border border-border rounded-lg px-3 py-2 text-cream text-sm"
            />
            <button
              onClick={addSale}
              className="w-full bg-harvest-500 hover:bg-harvest-400 text-white font-semibold py-2 rounded-lg text-sm transition"
            >
              Record Sale
            </button>
          </div>
        )}
        {sales?.sales?.length > 0 ? (
          <>
            {sales.sales.map((s: any, i: number) => (
              <div key={i} className="flex justify-between py-2 border-b border-border/30">
                <div>
                  <span className="text-cream text-sm">{s.buyer}</span>
                  <span className="text-muted text-xs ml-2">{s.quantity_kg} kg @ KES {s.unit_price}</span>
                </div>
                <span className="text-cream text-sm font-mono">KES {s.total_amount?.toLocaleString()}</span>
              </div>
            ))}
            {sales.totalRevenue > 0 && (
              <div className="flex justify-between py-2 mt-2 border-t border-border pt-2">
                <span className="text-cream font-semibold">Total Revenue</span>
                <span className="text-harvest-300 font-bold font-mono">KES {sales.totalRevenue?.toLocaleString()}</span>
              </div>
            )}
          </>
        ) : (
          <p className="text-muted text-sm text-center py-4">No sales recorded yet.</p>
        )}
      </div>
    </div>
  );
}

/* ─── Forecast Tab ─── */
function ForecastTab({ plotId, token, activeSeason }: {
  plotId: string; token: string; activeSeason: any;
}) {
  const [forecast, setForecast] = useState<any>(null);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    if (!activeSeason?.seasonId) return;
    fetch(`/api/seasons/${activeSeason.seasonId}/forecast`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => { if (data) setForecast(data.f || data); })
      .catch(console.error);
  }, [activeSeason, token]);

  const generate = async () => {
    if (!activeSeason?.seasonId) return;
    setGenerating(true);
    const res = await fetch(`/api/seasons/${activeSeason.seasonId}/forecast/generate`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    setForecast(data);
    setGenerating(false);
  };

  if (!activeSeason?.seasonId) {
    return (
      <div className="bg-soil-800 rounded-2xl border border-border p-10 text-center">
        <p className="text-muted text-sm">No active season. Start a season to generate forecasts.</p>
      </div>
    );
  }

  return (
    <div className="bg-soil-800 rounded-2xl border border-border p-6 space-y-4">
      <h3 className="text-xs uppercase tracking-widest text-muted">Yield Forecast</h3>
      {forecast ? (
        <>
          <div className="text-center py-4">
            <p className="text-5xl font-display font-bold text-canopy-300">
              {forecast.predictedYield?.toLocaleString() ?? "—"} kg
            </p>
            <p className="text-muted text-sm mt-2">
              Between {forecast.confidenceLow?.toLocaleString() ?? "?"} and {forecast.confidenceHigh?.toLocaleString() ?? "?"} kg
            </p>
            {forecast.date && <p className="text-muted text-xs mt-1">Generated {forecast.date}</p>}
          </div>
          <p className="text-cream text-sm">{forecast.basis}</p>
        </>
      ) : (
        <p className="text-muted text-sm text-center py-8">No forecast generated yet.</p>
      )}
      <button
        onClick={generate}
        disabled={generating}
        className="w-full bg-canopy-500 hover:bg-canopy-400 text-white font-semibold py-3 rounded-lg transition disabled:opacity-50"
      >
        {generating ? "Generating..." : forecast ? "Regenerate Forecast" : "Generate Forecast"}
      </button>
      <p className="text-muted text-xs text-center">
        Based on satellite health indices, weather patterns, and your crop variety.
      </p>
    </div>
  );
}

/* ─── Farm Chat Tab ─── */
function ChatTab({ plotId, token, activeSeason }: {
  plotId: string; token: string; activeSeason: any;
}) {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([
    { role: "system", content: "Ask me anything about your field — weather conditions, disease risks, or what to do next. I speak English and Swahili." },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  const send = async () => {
    if (!input.trim()) return;
    const userMsg = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSending(true);

    try {
      const res = await fetch("/api/chat/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          farmerId: localStorage.getItem("farmwise_farmer_id"),
          message: input,
          seasonId: activeSeason?.seasonId,
          history: messages.filter((m) => m.role !== "system").slice(-10),
        }),
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.answer || data.reply || "No response" }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Sorry, something went wrong. Please try again." }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="bg-soil-800 rounded-2xl border border-border overflow-hidden">
      <div className="p-4 border-b border-border bg-soil-700/50">
        <p className="text-muted text-xs">{messages[0].content}</p>
      </div>
      <div className="h-96 overflow-y-auto p-4 space-y-3">
        {messages.slice(1).map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm ${
              m.role === "user"
                ? "bg-canopy-600/30 text-cream"
                : "bg-soil-700 text-cream"
            }`}>
              {m.content}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="bg-soil-700 rounded-xl px-4 py-2.5 text-sm text-muted animate-pulse">
              Thinking...
            </div>
          </div>
        )}
      </div>
      <div className="p-4 border-t border-border flex gap-2">
        <input
          data-chat-input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask about your farm..."
          className="flex-1 bg-soil-700 border border-border rounded-lg px-4 py-3 text-cream placeholder-muted focus:outline-none focus:border-canopy-400 text-sm"
        />
        <button
          onClick={send}
          disabled={!input.trim() || sending}
          className="px-4 py-3 bg-canopy-500 hover:bg-canopy-400 text-white font-semibold rounded-lg transition disabled:opacity-50 text-sm"
        >
          Send
        </button>
      </div>
    </div>
  );
}

/* ─── Certificate Tab ─── */
function CertificateTab({ plotId, token, activeSeason }: {
  plotId: string; token: string; activeSeason: any;
}) {
  const [cert, setCert] = useState<any>(null);
  const [audit, setAudit] = useState<any>(null);

  useEffect(() => {
    fetch(`/api/plots/${plotId}/certificate`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then(setCert)
      .catch(console.error);
    if (activeSeason?.seasonId) {
      fetch(`/api/seasons/${activeSeason.seasonId}/audit-trail`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => r.json())
        .then(setAudit)
        .catch(console.error);
    }
  }, [plotId, token, activeSeason]);

  if (!cert) {
    return (
      <div className="bg-soil-800 rounded-2xl border border-border p-10 text-center">
        <p className="text-muted">Loading certificate...</p>
      </div>
    );
  }

  const verified = audit?.verifiedOnChain || cert.verified;

  return (
    <div className="space-y-4">
      {/* Certificate Card */}
      <div className="bg-soil-800 rounded-2xl border-2 border-canopy-500/30 p-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 bg-canopy-500/5 rounded-bl-full" />
        <div className="text-center mb-6">
          <div className="text-4xl mb-2">🌿</div>
          <h2 className="text-2xl font-display font-bold text-cream">FarmWise</h2>
          <p className="text-muted text-sm">Verified Production Certificate</p>
        </div>

        <div className="border-t border-b border-border py-4 mb-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted text-xs">Plot</p>
              <p className="text-cream font-semibold">{cert.plotName}</p>
            </div>
            <div>
              <p className="text-muted text-xs">County</p>
              <p className="text-cream font-semibold">{cert.county}</p>
            </div>
            <div>
              <p className="text-muted text-xs">Area</p>
              <p className="text-cream font-semibold">{cert.areaHa} ha</p>
            </div>
            <div>
              <p className="text-muted text-xs">Variety</p>
              <p className="text-cream font-semibold">{cert.variety}</p>
            </div>
            <div>
              <p className="text-muted text-xs">Planted</p>
              <p className="text-cream font-semibold">{cert.plantingDate}</p>
            </div>
            <div>
              <p className="text-muted text-xs">Expected Harvest</p>
              <p className="text-cream font-semibold">{cert.expectedHarvestDate}</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 mb-4 text-center">
          <div className="bg-soil-700 rounded-xl p-3">
            <p className="text-xl font-display font-bold text-cream">{cert.monitoringDays}</p>
            <p className="text-muted text-xs">Days Monitored</p>
          </div>
          <div className="bg-soil-700 rounded-xl p-3">
            <p className="text-xl font-display font-bold text-cream">{cert.alertCount}</p>
            <p className="text-muted text-xs">Alerts</p>
          </div>
          <div className="bg-soil-700 rounded-xl p-3">
            <p className="text-xl font-display font-bold text-cream">{cert.interventionCount}</p>
            <p className="text-muted text-xs">Interventions</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-4 text-center">
          <div className="bg-soil-700 rounded-xl p-3">
            <p className="text-xl font-display font-bold text-cream">{cert.observationCount}</p>
            <p className="text-muted text-xs">Observations</p>
          </div>
          <div className="bg-soil-700 rounded-xl p-3">
            <p className="text-xl font-display font-bold text-canopy-300">KES {cert.totalExpenses?.toLocaleString()}</p>
            <p className="text-muted text-xs">Total Expenses</p>
          </div>
        </div>

        {cert.totalRevenue > 0 && (
          <div className="bg-soil-700 rounded-xl p-3 mb-4 text-center">
            <p className="text-xl font-display font-bold text-harvest-300">KES {cert.totalRevenue?.toLocaleString()}</p>
            <p className="text-muted text-xs">Total Revenue</p>
          </div>
        )}

        {/* Blockchain Verification */}
        <div className={`rounded-xl p-4 border ${verified ? "border-canopy-500/50 bg-canopy-600/10" : "border-harvest-500/30 bg-harvest-500/5"}`}>
          <div className="flex items-center gap-3 mb-2">
            <div className={`w-3 h-3 rounded-full ${verified ? "bg-canopy-400" : "bg-harvest-500"}`} />
            <span className={`font-semibold text-sm ${verified ? "text-canopy-300" : "text-harvest-300"}`}>
              {verified ? "Verified on Cardano Blockchain" : "Blockchain Verification Pending"}
            </span>
          </div>
          <p className="text-muted text-xs">
            {verified
              ? "This production record is cryptographically sealed on the Cardano blockchain via Masumi. All satellite observations and AI recommendations are immutable and verifiable."
              : "Records are being prepared for blockchain submission. The Masumi Cardano agent will log decisions when active."}
          </p>
        </div>
      </div>

      {/* Masumi Audit Trail */}
      {audit && (
        <div className="bg-soil-800 rounded-2xl border border-border p-6">
          <h3 className="text-xs uppercase tracking-widest text-muted mb-4">Blockchain Audit Trail</h3>
          {audit.totalAlerts > 0 ? (
            <div className="space-y-3">
              <div className="grid grid-cols-4 gap-2 text-xs text-muted mb-2">
                <span>Condition</span>
                <span>Status</span>
                <span>Masumi</span>
                <span>Actions</span>
              </div>
              {audit.alerts.map((a: any, i: number) => (
                <div key={i} className="bg-soil-700 rounded-xl p-3 text-sm">
                  <div className="grid grid-cols-4 gap-2 items-center">
                    <div>
                      <p className="text-cream font-medium">{a.condition}</p>
                      <p className="text-muted text-xs">{a.urgency}</p>
                    </div>
                    <div>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        a.alertStatus === "RESOLVED" ? "bg-canopy-600/20 text-canopy-300" :
                        a.alertStatus === "ACTIVE" ? "bg-alert-500/20 text-alert-300" :
                        "bg-soil-700 text-muted"
                      }`}>{a.alertStatus}</span>
                    </div>
                    <div>
                      {a.txHash ? (
                        <span className="text-xs font-mono text-canopy-300" title={a.txHash}>
                          {a.txHash.slice(0, 10)}...
                        </span>
                      ) : (
                        <span className="text-muted text-xs">Not logged</span>
                      )}
                    </div>
                    <div>
                      <span className="text-xs">{a.masumiStatus}</span>
                    </div>
                  </div>
                  {/* Intervention details */}
                  {audit.interventions && audit.interventions
                    .filter((int: any) => int.forCondition === a.condition)
                    .slice(0, 1)
                    .map((int: any, j: number) => (
                      <div key={j} className="mt-2 pt-2 border-t border-border/30 text-xs">
                        <p className="text-canopy-300">Action: {int.action}</p>
                        <p className="text-muted">Date: {int.date} | Cost: KES {int.totalCost?.toLocaleString()}</p>
                      </div>
                    ))}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted text-sm text-center py-4">No blockchain records yet. Records are created when diagnostic alerts are processed.</p>
          )}
        </div>
      )}

      {/* Interventions Summary */}
      {audit?.totalInterventions > 0 && (
        <div className="bg-soil-800 rounded-2xl border border-border p-6">
          <h3 className="text-xs uppercase tracking-widest text-muted mb-4">Farmer Actions ({audit.totalInterventions})</h3>
          <div className="space-y-2">
            {audit.interventions.slice(0, 5).map((int: any, i: number) => (
              <div key={i} className="bg-soil-700 rounded-xl p-3 flex items-start gap-3">
                <div className="bg-canopy-600/20 rounded-full p-1.5 mt-0.5">
                  <span className="text-canopy-300 text-xs">✓</span>
                </div>
                <div className="flex-1">
                  <p className="text-cream text-sm">{int.action}</p>
                  <p className="text-muted text-xs">For: {int.forCondition} | {int.date}</p>
                  {int.totalCost > 0 && (
                    <p className="text-muted text-xs">Cost: KES {int.totalCost?.toLocaleString()} ({int.categories?.join(", ")})</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Observations Summary */}
      {audit?.totalObservations > 0 && (
        <div className="bg-soil-800 rounded-2xl border border-border p-6">
          <h3 className="text-xs uppercase tracking-widest text-muted mb-4">Farmer Observations ({audit.totalObservations})</h3>
          <div className="space-y-2">
            {audit.observations.slice(0, 5).map((obs: any, i: number) => (
              <div key={i} className="bg-soil-700 rounded-xl p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-muted text-xs">{obs.date}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    obs.status === "CRITICAL" ? "bg-alert-500/20 text-alert-300" :
                    obs.status === "WARNING" ? "bg-harvest-500/20 text-harvest-300" :
                    "bg-canopy-600/20 text-canopy-300"
                  }`}>{obs.status}</span>
                </div>
                <p className="text-cream text-sm">{obs.notes}</p>
                {obs.interpretation && <p className="text-muted text-xs mt-1 italic">{obs.interpretation.slice(0, 150)}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Powered by */}
      <div className="text-center text-muted text-xs space-y-1">
        <p>Powered by FarmWise</p>
        <p>Satellite data: AgroMonitoring | Soil data: iSDAsoil | Blockchain: Masumi (Cardano)</p>
        <p>AI: Featherless | Database: Neo4j AuraDB</p>
      </div>
    </div>
  );
}

  const daysPlanted = activeSeason?.plantingDate
    ? Math.floor((Date.now() - new Date(activeSeason.plantingDate).getTime()) / 86400000)
    : null;
  const daysToHarvest = activeSeason?.expectedHarvestDate
    ? Math.floor((new Date(activeSeason.expectedHarvestDate).getTime() - Date.now()) / 86400000)
    : null;

  return (
    <div className="min-h-dvh bg-soil-900 pb-24">
      <header className="sticky top-0 bg-soil-900/90 backdrop-blur border-b border-border z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-2">
            <button onClick={() => router.push("/dashboard")} className="text-muted text-sm hover:text-cream transition">
              &larr; Dashboard
            </button>
            {activeSeason && (
              <button
                onClick={async () => {
                  try {
                    const res = await fetch(`/api/plots/${plotId}/stakeholder-token`, {
                      method: "POST",
                      headers: { Authorization: `Bearer ${token}` },
                    });
                    const data = await res.json();
                    navigator.clipboard.writeText(data.url || data.token);
                    alert("Stakeholder URL copied to clipboard!");
                  } catch {}
                }}
                className="text-canopy-300 text-sm hover:text-canopy-400 transition"
              >
                Share with Buyer
              </button>
            )}
          </div>
          <h1 className="text-xl font-display font-bold text-cream">{plot.name || "Plot"}</h1>
          <div className="flex gap-3 text-sm text-muted mt-1">
            <span>{plot.county || ""}</span>
            <span>&middot;</span>
            <span>{plot.areaHa ? `${plot.areaHa} ha` : ""}</span>
          </div>
          {activeSeason && (
            <div className="flex flex-wrap gap-x-6 gap-y-1 mt-3 text-sm">
              <span className="text-canopy-300 font-medium">{activeSeason.varietyName}</span>
              <span className="text-muted">{activeSeason.growthStage || "Unknown stage"}</span>
              {daysPlanted != null && (
                <span className="text-muted">
                  {daysPlanted} day{daysPlanted !== 1 ? "s" : ""} planted
                  {daysToHarvest != null && daysToHarvest > 0 ? ` / ~${daysToHarvest} to harvest` : ""}
                </span>
              )}
            </div>
          )}
          {!activeSeason && (
            <button
              onClick={() => setActiveTab("Overview")}
              className="mt-3 px-4 py-1.5 bg-canopy-500 hover:bg-canopy-400 text-white text-sm font-semibold rounded-lg transition"
            >
              + Start New Season
            </button>
          )}
        </div>

        <div className="max-w-6xl mx-auto px-4 flex flex-wrap gap-0.5">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-2.5 py-1.5 text-xs whitespace-nowrap rounded-t-lg transition border-b-2 font-medium ${
                activeTab === tab
                  ? "border-canopy-400 text-canopy-300 bg-soil-800/50"
                  : "border-transparent text-muted hover:text-cream"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </header>

      <main className="max-w-6xl mx-auto p-4">
        <TabContent tab={activeTab} setActiveTab={setActiveTab} plotId={plotId} token={token} plot={plot} activeSeason={activeSeason} />
      </main>
    </div>
  );

function TabContent({ tab, setActiveTab, plotId, token, plot, activeSeason }: {
  tab: string; setActiveTab: (t: string) => void; plotId: string; token: string; plot: any; activeSeason: any;
}) {
  switch (tab) {
    case "Overview":
      return <OverviewTab plotId={plotId} token={token} plot={plot} activeSeason={activeSeason} setActiveTab={setActiveTab} />;
    case "Telemetry":
      return <TelemetryTab plotId={plotId} token={token} activeSeason={activeSeason} />;
    case "Alerts":
      return <AlertsTab plotId={plotId} token={token} activeSeason={activeSeason} />;
    case "Observations":
      return <ObservationsTab plotId={plotId} token={token} activeSeason={activeSeason} />;
    case "Pests":
      return <PestsTab plotId={plotId} token={token} activeSeason={activeSeason} />;
    case "Soil":
      return <SoilTab plotId={plotId} token={token} />;
    case "Actions":
      return <ActionsTab plotId={plotId} token={token} activeSeason={activeSeason} />;
    case "Finances":
      return <FinancesTab plotId={plotId} token={token} activeSeason={activeSeason} />;
    case "Forecast":
      return <ForecastTab plotId={plotId} token={token} activeSeason={activeSeason} />;
    case "Farm Chat":
      return <ChatTab plotId={plotId} token={token} activeSeason={activeSeason} />;
    case "Certificate":
      return <CertificateTab plotId={plotId} token={token} activeSeason={activeSeason} />;
    default:
      return null;
  }
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-2 border-b border-border/50">
      <span className="text-muted text-sm">{label}</span>
      <span className="text-cream text-sm font-medium">{value}</span>
    </div>
  );
}

function MetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-soil-700 rounded-xl p-3">
      <p className="text-muted text-xs">{label}</p>
      <p className="text-cream font-display font-bold text-lg mt-1">{value}</p>
      {sub && <p className="text-muted text-xs mt-0.5">{sub}</p>}
    </div>
  );
}

}
