"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

interface PlotCard {
  plotId: string;
  name: string;
  county: string;
  areaHa: number;
  activeSeasonId?: string;
  activeSeasonCount?: number;
  activeAlertCount?: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const [farmerName, setFarmerName] = useState("");
  const [plots, setPlots] = useState<PlotCard[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const alertsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const token = localStorage.getItem("farmwise_token");
    if (!token) {
      router.push("/login");
      return;
    }
    setFarmerName(localStorage.getItem("farmwise_name") || "Mkulima");
    loadDashboard(token);
  }, [router]);

  const loadDashboard = async (token: string) => {
    try {
      const res = await fetch("/api/plots", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Failed to load plots (${res.status})`);
      const data: PlotCard[] = await res.json();
      setPlots(data);

      const allAlerts: any[] = [];
      for (const plot of data) {
        if (plot.activeSeasonId) {
          try {
            const alertRes = await fetch(`/api/seasons/${plot.activeSeasonId}/alerts`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (alertRes.ok) {
              const alertData = await alertRes.json();
              for (const a of alertData) {
                if (a.status === "ACTIVE") {
                  allAlerts.push({ ...a, plotName: plot.name, plotId: plot.plotId });
                }
              }
            }
          } catch {}
        }
      }
      setAlerts(allAlerts);
    } catch (err) {
      console.error("Dashboard load failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("farmwise_token");
    localStorage.removeItem("farmwise_farmer_id");
    localStorage.removeItem("farmwise_name");
    router.push("/login");
  };

  const getUrgencyColor = (urgency: string) =>
    urgency === "HIGH" ? "bg-alert-500" : urgency === "MEDIUM" ? "bg-harvest-500" : "bg-canopy-300";

  return (
    <div className="min-h-dvh bg-soil-900">
      <header className="sticky top-0 bg-soil-900/90 backdrop-blur border-b border-border px-4 py-4 z-10">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-display font-bold text-cream">
              Habari{farmerName ? `, ${farmerName}` : ""}
            </h1>
            <p className="text-muted text-sm">
              {plots.length} {plots.length === 1 ? "plot" : "plots"} registered
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => router.push("/onboarding")}
              className="bg-canopy-500 hover:bg-canopy-400 text-white text-sm font-medium px-4 py-2 rounded-lg transition"
            >
              + Add Plot
            </button>
            <button
              onClick={handleLogout}
              className="text-muted text-sm hover:text-cream transition"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto p-4 space-y-6">
        {/* Summary card */}
        <div className="bg-soil-800 rounded-2xl border border-border p-5">
          <h3 className="text-xs uppercase tracking-widest text-muted mb-3">Dashboard Summary</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-soil-700 rounded-xl p-3 text-center">
              <p className="text-2xl font-display font-bold text-cream">{plots.length}</p>
              <p className="text-muted text-xs mt-1">Total Plots</p>
            </div>
            <div className="bg-soil-700 rounded-xl p-3 text-center">
              <p className="text-2xl font-display font-bold text-canopy-300">
                {plots.filter((p) => (p.activeSeasonCount ?? 0) > 0).length}
              </p>
              <p className="text-muted text-xs mt-1">Active Seasons</p>
            </div>
            <div className="bg-soil-700 rounded-xl p-3 text-center">
              <p className="text-2xl font-display font-bold text-alert-300">{alerts.length}</p>
              <p className="text-muted text-xs mt-1">Today&apos;s Alerts</p>
            </div>
            <div className="bg-soil-700 rounded-xl p-3 text-center">
              <button
                onClick={() => alertsRef.current?.scrollIntoView({ behavior: "smooth" })}
                className="text-canopy-300 text-sm hover:text-canopy-400 transition"
              >
                View All Alerts &rarr;
              </button>
            </div>
          </div>
        </div>

        {/* Alert strip */}
        {alerts.length > 0 && (
          <div ref={alertsRef} className="space-y-2">
            <h3 className="text-xs uppercase tracking-widest text-muted flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-alert-500 animate-pulse" />
              {alerts.length} Active {alerts.length === 1 ? "Alert" : "Alerts"}
            </h3>
            <div className="flex gap-3 overflow-x-auto scroll-hide pb-2">
              {alerts.map((a) => (
                <button
                  key={a.alertId}
                  onClick={() => router.push(`/plot/${a.plotId}`)}
                  className="bg-soil-800 rounded-xl border border-border p-4 min-w-[270px] flex-shrink-0 text-left hover:border-canopy-400 transition cursor-pointer"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`w-2.5 h-2.5 rounded-full ${getUrgencyColor(a.urgency)}`} />
                    <span className="text-cream text-sm font-semibold">{a.detectedCondition}</span>
                    <span className="text-xs text-muted ml-auto">{a.urgency}</span>
                  </div>
                  <p className="text-muted text-xs">{a.plotName}</p>
                  <p className="text-muted text-xs mt-1.5 line-clamp-2">{a.smsSwahili}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Plot grid */}
        <div>
          <h3 className="text-xs uppercase tracking-widest text-muted mb-4">My Plots</h3>
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[1, 2].map((i) => (
                <div key={i} className="bg-soil-800 rounded-2xl border border-border p-6 h-44 animate-pulse" />
              ))}
            </div>
          ) : plots.length === 0 ? (
            <div className="bg-soil-800 rounded-2xl border border-border p-12 text-center">
              <div className="text-5xl mb-4">🌱</div>
              <h3 className="text-xl font-display font-bold text-cream mb-2">Welcome to FarmWise</h3>
              <p className="text-muted text-sm mb-6 max-w-md mx-auto">
                You haven&apos;t added any plots yet. Each plot can have multiple planting seasons.
                Add your first plot to start monitoring your crop health.
              </p>
              <button
                onClick={() => router.push("/onboarding")}
                className="px-8 py-3 bg-canopy-500 hover:bg-canopy-400 text-white font-semibold rounded-xl transition text-lg"
              >
                + Add Your First Plot
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {plots.map((plot) => (
                <button
                  key={plot.plotId}
                  onClick={() => router.push(`/plot/${plot.plotId}`)}
                  className="bg-soil-800 rounded-2xl border border-border p-5 text-left hover:border-canopy-400 hover:bg-soil-700/50 transition-all cursor-pointer group"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h4 className="text-cream font-display font-bold text-lg group-hover:text-canopy-300 transition">
                        {plot.name || "Unnamed Plot"}
                      </h4>
                      <p className="text-muted text-sm">
                        {plot.county} &middot; {plot.areaHa} ha
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        (plot.activeSeasonCount ?? 0) > 0
                          ? "bg-canopy-600/20 text-canopy-300"
                          : "bg-soil-700 text-muted"
                      }`}>
                        {(plot.activeSeasonCount ?? 0) > 0
                          ? `${plot.activeSeasonCount} active season${plot.activeSeasonCount !== 1 ? "s" : ""}`
                          : "No seasons"}
                      </span>
                      {plot.activeAlertCount ? (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-alert-500/20 text-alert-300 font-medium">
                          {plot.activeAlertCount} alert{plot.activeAlertCount !== 1 ? "s" : ""}
                        </span>
                      ) : (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-soil-700 text-muted">
                          No alerts
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-muted text-xs group-hover:text-canopy-300 transition">
                    View details &rarr;
                  </div>
                </button>
              ))}
              {/* Add plot card */}
              <button
                onClick={() => router.push("/onboarding")}
                className="bg-soil-800/50 rounded-2xl border border-dashed border-border hover:border-canopy-400 p-10 text-center cursor-pointer transition-all group"
              >
                <div className="text-3xl mb-2 group-hover:scale-110 transition-transform">+</div>
                <p className="text-muted text-sm group-hover:text-cream transition">Add Another Plot</p>
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
