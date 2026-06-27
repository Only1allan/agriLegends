"use client";

import { useState, useEffect } from "react";
import { useParams, useSearchParams } from "next/navigation";

export default function StakeholderPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const plotId = params.plotId as string;
  const token = searchParams.get("token") || "";
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) {
      setError("Missing access token");
      setLoading(false);
      return;
    }
    fetch(`/api/stakeholder/${plotId}/report?token=${token}`)
      .then((r) => {
        if (!r.ok) throw new Error("Invalid or expired link");
        return r.json();
      })
      .then(setReport)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [plotId, token]);

  const ndviColor =
    report?.latestNdvi > 0.5 ? "#2d8a3e" : report?.latestNdvi > 0.3 ? "#c8a020" : "#c03020";

  return (
    <div className="min-h-dvh bg-cream">
      <header className="bg-white border-b border-gray-200 px-4 py-6">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-3xl">🌿</span>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">FarmWise</h1>
              <p className="text-gray-500 text-sm">Verified Production Record</p>
            </div>
          </div>
          <div className="flex items-center gap-2 mt-4">
            <div className="bg-green-100 text-green-700 text-xs font-semibold px-3 py-1 rounded-full flex items-center gap-1">
              <span>✓</span> Verified by Satellite Monitoring
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto p-4 space-y-4">
        {loading && <p className="text-gray-500 text-center py-12">Loading report...</p>}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-2xl p-8 text-center">
            <p className="text-red-600">{error}</p>
            <p className="text-gray-500 text-sm mt-2">This link may have expired or is incorrect.</p>
          </div>
        )}

        {report && (
          <>
            {/* Farm Summary */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <h2 className="text-xs uppercase tracking-widest text-gray-400 mb-3">Farm Summary</h2>
              <div className="grid grid-cols-2 gap-4">
                <Field label="County" value={report.county} />
                <Field label="Area" value={`${report.areaHa} ha`} />
                <Field label="Soil Type" value={report.soilType || "Not specified"} />
                <Field label="Plot" value={report.plotName} />
              </div>
            </div>

            {/* Crop Identity */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <h2 className="text-xs uppercase tracking-widest text-gray-400 mb-3">Crop Identity</h2>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Variety" value={report.variety} />
                <Field label="Planted" value={report.plantingDate} />
                <Field label="Expected Harvest" value={report.expectedHarvestDate} />
                <Field label="Last Updated" value={report.lastUpdated} />
              </div>
            </div>

            {/* Crop Health */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <h2 className="text-xs uppercase tracking-widest text-gray-400 mb-3">Crop Health</h2>
              <div className="flex items-center gap-4">
                <div
                  className="w-4 h-4 rounded-full"
                  style={{ backgroundColor: ndviColor }}
                />
                <div>
                  <p className="text-2xl font-bold" style={{ color: ndviColor }}>{report.ndviHealth}</p>
                  <p className="text-gray-500 text-sm">NDVI: {report.latestNdvi?.toFixed(3) || "N/A"}</p>
                </div>
              </div>
            </div>

            {/* Field Activity */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <h2 className="text-xs uppercase tracking-widest text-gray-400 mb-3">Field Activity</h2>
              <p className="text-gray-800">
                <span className="font-bold text-xl">{report.interventionCount || 0}</span>
                <span className="text-gray-500 ml-2">interventions logged this season</span>
              </p>
            </div>

            {/* Yield Forecast */}
            {report.forecast && (
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                <h2 className="text-xs uppercase tracking-widest text-gray-400 mb-3">Yield Forecast</h2>
                <p className="text-3xl font-bold text-gray-800">
                  {report.forecast.predictedYield?.toLocaleString() || "—"} kg
                </p>
                <p className="text-gray-500 text-sm mt-1">
                  Range: {report.forecast.confidenceLow?.toLocaleString() || "?"} – {report.forecast.confidenceHigh?.toLocaleString() || "?"} kg
                </p>
                <p className="text-gray-400 text-xs mt-2">
                  AI-generated estimate based on satellite data
                </p>
              </div>
            )}

            {/* Traceability Seal */}
            <div className="bg-gray-50 rounded-2xl border border-gray-200 p-6 text-center">
              <p className="text-gray-700 font-semibold">Powered by FarmWise</p>
              <p className="text-gray-400 text-sm mt-1">
                This record is generated from real-time satellite monitoring via AgroMonitoring API and AI analysis.
              </p>
              <p className="text-gray-400 text-xs mt-2">{report.verification}</p>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className="text-gray-800 font-medium">{value || "—"}</p>
    </div>
  );
}
