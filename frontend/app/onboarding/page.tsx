"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

const KENYA_COUNTY_COORDS: Record<string, { lat: number; lng: number }> = {
  "Nairobi": { lat: -1.2921, lng: 36.8219 },
  "Nyandarua": { lat: -0.1833, lng: 36.4333 },
  "Nakuru": { lat: -0.3031, lng: 36.0800 },
  "Kiambu": { lat: -1.1714, lng: 36.8356 },
  "Meru": { lat: 0.0463, lng: 37.6559 },
  "Uasin Gishu": { lat: 0.5143, lng: 35.2698 },
  "Nyeri": { lat: -0.4273, lng: 36.9548 },
  "Murang'a": { lat: -0.7351, lng: 37.1588 },
  "Bomet": { lat: -0.7822, lng: 35.3378 },
  "Kirinyaga": { lat: -0.4983, lng: 37.2838 },
  "Bungoma": { lat: 0.5695, lng: 34.5584 },
  "Kakamega": { lat: 0.2827, lng: 34.7519 },
  "Trans Nzoia": { lat: 1.0167, lng: 35.0000 },
  "Nandi": { lat: 0.1767, lng: 35.1167 },
  "Elgeyo Marakwet": { lat: 0.5000, lng: 35.5000 },
  "Kericho": { lat: -0.3679, lng: 35.2860 },
  "Laikipia": { lat: 0.3600, lng: 36.7800 },
  "Machakos": { lat: -1.5177, lng: 37.2634 },
  "Makueni": { lat: -1.8000, lng: 37.6167 },
  "Embu": { lat: -0.5333, lng: 37.4500 },
  "Kisii": { lat: -0.6817, lng: 34.7667 },
  "Kisumu": { lat: -0.1000, lng: 34.7500 },
  "Homa Bay": { lat: -0.5273, lng: 34.4571 },
  "Migori": { lat: -1.0634, lng: 34.4731 },
  "Siaya": { lat: 0.0600, lng: 34.2867 },
  "Busia": { lat: 0.4633, lng: 34.1050 },
  "Kilifi": { lat: -3.6300, lng: 39.8500 },
  "Kwale": { lat: -4.1767, lng: 39.4500 },
  "Mombasa": { lat: -4.0500, lng: 39.6667 },
  "Taita Taveta": { lat: -3.4167, lng: 38.3333 },
  "Kitui": { lat: -1.3667, lng: 38.0167 },
  "Tharaka Nithi": { lat: -0.3000, lng: 37.9167 },
  "Garissa": { lat: -0.4500, lng: 39.6500 },
  "Mandera": { lat: 3.9333, lng: 41.8667 },
  "Wajir": { lat: 1.7500, lng: 40.0667 },
  "Isiolo": { lat: 0.3500, lng: 37.5833 },
  "Marsabit": { lat: 2.3333, lng: 37.9833 },
  "Turkana": { lat: 3.1167, lng: 35.6000 },
  "Samburu": { lat: 1.1667, lng: 36.6667 },
  "Baringo": { lat: 0.4667, lng: 35.9667 },
  "West Pokot": { lat: 1.2500, lng: 35.0833 },
  "Vihiga": { lat: 0.0500, lng: 34.7333 },
  "Nyamira": { lat: -0.6167, lng: 34.9833 },
  "Lamu": { lat: -2.2667, lng: 40.9000 },
  "Tana River": { lat: -1.5000, lng: 40.0333 },
};


const SOIL_TYPES = [
  "Clay", "Clay Loam", "Sandy Loam", "Silt Loam", "Loam",
  "Sandy Clay Loam", "Silty Clay", "Volcanic",
];

const KENYA_COUNTIES = Object.keys(KENYA_COUNTY_COORDS);

const POTATO_VARIETIES = ["Shangi", "Dutch Robjn", "Kenya Mpya", "Asante", "Tigoni", "Purple Gold"];

const GROWTH_STAGES = [
  { value: "emergence", label: "Emergence (0-21 days)", daysOffset: 10 },
  { value: "tuber_initiation", label: "Tuber Initiation (22-45 days)", daysOffset: 33 },
  { value: "tuber_bulking", label: "Tuber Bulking (46-80 days)", daysOffset: 63 },
  { value: "maturation", label: "Maturation (81-110 days)", daysOffset: 95 },
];

const STEPS = [
  { id: 1, title: "Karibu FarmWise", subtitle: "Welcome" },
  { id: 2, title: "Your Farm Location", subtitle: "Location" },
  { id: 3, title: "Farm Details", subtitle: "Details" },
  { id: 4, title: "Your Crop", subtitle: "Crop" },
  { id: 5, title: "Growth Stage", subtitle: "Growth" },
  { id: 6, title: "Contact Preference", subtitle: "Contact" },
  { id: 7, title: "Setup Complete", subtitle: "Summary" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    name: "",
    county: "Nyandarua",
    plotName: "",
    areaHa: 1.0,
    soilType: "Clay Loam",
    variety: "Shangi",
    plantingDate: new Date().toISOString().split("T")[0],
    growthStage: "emergence" as string,
    channel: "whatsapp_text" as string,
    language: "sw" as string,
  });
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [setupSteps, setSetupSteps] = useState<string[]>([]);

  useEffect(() => {
    const t = localStorage.getItem("farmwise_token");
    const n = localStorage.getItem("farmwise_name");
    if (!t) router.push("/login");
    setForm((prev) => ({ ...prev, name: n || prev.name }));
  }, [router]);

  useEffect(() => {
    const stage = GROWTH_STAGES.find((s) => s.value === form.growthStage);
    if (stage) {
      const estimatedDate = new Date();
      estimatedDate.setDate(estimatedDate.getDate() - stage.daysOffset);
      update("plantingDate", estimatedDate.toISOString().split("T")[0]);
    }
  }, [form.growthStage]);

  const update = (field: string, value: string | number) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const handleComplete = async () => {
    setLoading(true);
    setErrorMsg("");
    setSetupSteps(["Creating your plot..."]);
    const token = localStorage.getItem("farmwise_token");
    if (!token) {
      setErrorMsg("Session expired. Please log in again.");
      setLoading(false);
      setTimeout(() => router.push("/login"), 1500);
      return;
    }
    const coords = KENYA_COUNTY_COORDS[form.county] || { lat: -1.2921, lng: 36.8219 };
    try {
      const plotRes = await fetch("/api/plots", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: form.plotName || "My Shamba",
          county: form.county,
          areaHa: form.areaHa,
          soilType: form.soilType,
          location: coords,
        }),
      });
      if (!plotRes.ok) {
        const errData = await plotRes.json().catch(() => ({}));
        throw new Error(errData.detail || `Plot creation failed (${plotRes.status})`);
      }
      const plotData = await plotRes.json();
      setSetupSteps(["Creating your plot... done", "Fetching soil data from iSDAsoil..."]);

      setSetupSteps((prev) => [...prev, "Creating season and ingesting satellite data..."]);
      const seasonRes = await fetch(`/api/plots/${plotData.plotId}/seasons`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          plantingDate: form.plantingDate,
          varietyName: form.variety,
          growthStage: form.growthStage,
        }),
      });
      if (!seasonRes.ok) {
        const errData = await seasonRes.json().catch(() => ({}));
        throw new Error(errData.detail || `Season creation failed (${seasonRes.status})`);
      }
      const seasonData = await seasonRes.json();
      const ingestion = seasonData.ingestion || {};
      setSetupSteps([
        "Creating your plot... done",
        `Soil data: ${ingestion.soil || "pending"}`,
        `Satellite data: ${ingestion.satellite || "pending"}`,
        `Weather data: ${ingestion.weather || "pending"}`,
        `Health analysis: ${ingestion.diagnostic || "pending"}`,
        "Setup complete!",
      ]);
      await new Promise((r) => setTimeout(r, 800));

      router.push("/dashboard");
    } catch (err: any) {
      setErrorMsg(err.message || "Setup failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const progress = (step / 7) * 100;

  return (
    <div className="min-h-dvh bg-soil-900 p-4">
      <div className="max-w-lg mx-auto">
        {/* Progress bar */}
        <div className="h-1 bg-soil-700 rounded-full mb-8 mt-4">
          <div
            className="h-full bg-canopy-500 rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="mb-6">
          <p className="text-muted text-xs uppercase tracking-widest">
            Step {step}/7
          </p>
          <h2 className="text-2xl font-display font-bold text-cream mt-1">
            {STEPS[step - 1].title}
          </h2>
        </div>

        {/* Step 1: Welcome */}
        {step === 1 && (
          <div className="bg-soil-800 rounded-2xl border border-border p-6 space-y-4">
            <p className="text-cream">Welcome to FarmWise, {form.name}!</p>
            <p className="text-muted text-sm">
              Your phone has been verified. Let&apos;s set up your farm in a few quick steps.
            </p>
            <div>
              <label className="block text-cream text-sm font-medium mb-1.5">Full Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => update("name", e.target.value)}
                className="w-full bg-soil-700 border border-border rounded-lg px-4 py-3 text-cream focus:outline-none focus:border-canopy-400"
              />
            </div>
          </div>
        )}

        {/* Step 2: Location */}
        {step === 2 && (
          <div className="bg-soil-800 rounded-2xl border border-border p-6 space-y-4">
            <div>
              <label className="block text-cream text-sm font-medium mb-1.5">County</label>
              <select
                value={form.county}
                onChange={(e) => update("county", e.target.value)}
                className="w-full bg-soil-700 border border-border rounded-lg px-4 py-3 text-cream focus:outline-none focus:border-canopy-400"
              >
                {KENYA_COUNTIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-cream text-sm font-medium mb-1.5">Plot / Shamba Name</label>
              <input
                type="text"
                value={form.plotName}
                onChange={(e) => update("plotName", e.target.value)}
                placeholder="Upper Shamba"
                className="w-full bg-soil-700 border border-border rounded-lg px-4 py-3 text-cream placeholder-muted focus:outline-none focus:border-canopy-400"
              />
            </div>
          </div>
        )}

        {/* Step 3: Farm Details */}
        {step === 3 && (
          <div className="bg-soil-800 rounded-2xl border border-border p-6 space-y-4">
            <div>
              <label className="block text-cream text-sm font-medium mb-1.5">Area (hectares)</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                max="500"
                value={form.areaHa}
                onChange={(e) => update("areaHa", parseFloat(e.target.value))}
                className="w-full bg-soil-700 border border-border rounded-lg px-4 py-3 text-cream focus:outline-none focus:border-canopy-400"
              />
            </div>
            <div>
              <label className="block text-cream text-sm font-medium mb-1.5">Soil Type</label>
              <select
                value={form.soilType}
                onChange={(e) => update("soilType", e.target.value)}
                className="w-full bg-soil-700 border border-border rounded-lg px-4 py-3 text-cream focus:outline-none focus:border-canopy-400"
              >
                {SOIL_TYPES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
        )}

        {/* Step 4: Crop */}
        {step === 4 && (
          <div className="bg-soil-800 rounded-2xl border border-border p-6 space-y-4">
            <div>
              <label className="block text-cream text-sm font-medium mb-1.5">Potato Variety</label>
              <select
                value={form.variety}
                onChange={(e) => update("variety", e.target.value)}
                className="w-full bg-soil-700 border border-border rounded-lg px-4 py-3 text-cream focus:outline-none focus:border-canopy-400"
              >
                {POTATO_VARIETIES.map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-cream text-sm font-medium mb-1.5">Planting Date</label>
              <input
                type="date"
                value={form.plantingDate}
                onChange={(e) => update("plantingDate", e.target.value)}
                className="w-full bg-soil-700 border border-border rounded-lg px-4 py-3 text-cream focus:outline-none focus:border-canopy-400"
              />
            </div>
          </div>
        )}

        {/* Step 5: Growth Stage */}
        {step === 5 && (
          <div className="bg-soil-800 rounded-2xl border border-border p-6 space-y-4">
            <p className="text-cream text-sm">
              Help us estimate your planting date by telling us which growth stage your crop is in.
            </p>
            <div>
              <label className="block text-cream text-sm font-medium mb-1.5">Which growth stage is your crop in?</label>
              <select
                value={form.growthStage}
                onChange={(e) => update("growthStage", e.target.value)}
                className="w-full bg-soil-700 border border-border rounded-lg px-4 py-3 text-cream focus:outline-none focus:border-canopy-400"
              >
                {GROWTH_STAGES.map((gs) => (
                  <option key={gs.value} value={gs.value}>{gs.label}</option>
                ))}
              </select>
            </div>
            {form.plantingDate && (
              <div className="bg-canopy-600/10 border border-canopy-600/30 rounded-lg p-3">
                <p className="text-muted text-xs mb-1">Estimated Planting Date</p>
                <p className="text-canopy-300 text-sm font-mono">{form.plantingDate}</p>
              </div>
            )}
          </div>
        )}

        {/* Step 6: Contact Preference */}
        {step === 6 && (
          <div className="bg-soil-800 rounded-2xl border border-border p-6 space-y-4">
            <div>
              <label className="block text-cream text-sm font-medium mb-1.5">Notification Channel</label>
              <select
                value={form.channel}
                onChange={(e) => update("channel", e.target.value)}
                className="w-full bg-soil-700 border border-border rounded-lg px-4 py-3 text-cream focus:outline-none focus:border-canopy-400"
              >
                <option value="whatsapp_text">WhatsApp (Recommended)</option>
                <option value="sms">SMS</option>
                <option value="whatsapp_audio">WhatsApp + Audio</option>
              </select>
            </div>
            <div>
              <label className="block text-cream text-sm font-medium mb-1.5">Language</label>
              <select
                value={form.language}
                onChange={(e) => update("language", e.target.value)}
                className="w-full bg-soil-700 border border-border rounded-lg px-4 py-3 text-cream focus:outline-none focus:border-canopy-400"
              >
                <option value="sw">Swahili</option>
                <option value="en">English</option>
              </select>
            </div>
          </div>
        )}

        {/* Step 7: Summary */}
        {step === 7 && (
          <div className="bg-soil-800 rounded-2xl border border-border p-6 space-y-3">
            <h3 className="text-lg font-display font-bold text-cream">Confirm your setup</h3>
            <div className="space-y-2 text-sm">
              <SummaryRow label="Name" value={form.name} />
              <SummaryRow label="County" value={form.county} />
              <SummaryRow label="Plot" value={form.plotName || "(not set)"} />
              <SummaryRow label="Area" value={`${form.areaHa} ha`} />
              <SummaryRow label="Soil" value={form.soilType} />
              <SummaryRow label="Variety" value={form.variety} />
              <SummaryRow label="Growth Stage" value={GROWTH_STAGES.find((s) => s.value === form.growthStage)?.label || form.growthStage} />
              <SummaryRow label="Planted (est.)" value={form.plantingDate} />
              <SummaryRow label="Language" value={form.language === "sw" ? "Swahili" : "English"} />
            </div>
            {loading && setupSteps.length > 0 && (
              <div className="bg-soil-700 rounded-xl p-4 space-y-1.5 mt-3 mb-3">
                {setupSteps.map((s, i) => (
                  <p key={i} className={`text-sm font-mono ${s.includes("done") || s.includes("complete") ? "text-canopy-300" : "text-cream"}`}>
                    {s.includes("done") || s.includes("complete") ? "✓ " : "⏳ "}{s}
                  </p>
                ))}
              </div>
            )}
            {errorMsg && (
              <div className="bg-alert-500/10 border border-alert-500/30 rounded-lg px-4 py-3 text-alert-300 text-sm mt-3">
                {errorMsg}
              </div>
            )}
            <button
              onClick={handleComplete}
              disabled={loading}
              className="w-full bg-canopy-500 hover:bg-canopy-400 text-white font-semibold py-3 rounded-lg transition disabled:opacity-50 mt-4"
            >
              {loading ? "Setting up..." : "Finish Setup & Go to Dashboard"}
            </button>
          </div>
        )}

        {/* Navigation */}
        {step < 7 && (
          <div className="flex justify-between mt-6">
            <button
              onClick={() => setStep((s) => Math.max(1, s - 1))}
              disabled={step === 1}
              className="px-6 py-3 bg-soil-800 border border-border text-cream rounded-lg disabled:opacity-30 hover:border-canopy-400 transition"
            >
              Back
            </button>
            <button
              onClick={() => setStep((s) => Math.min(7, s + 1))}
              className="px-6 py-3 bg-canopy-500 hover:bg-canopy-400 text-white font-semibold rounded-lg transition"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-1 border-b border-border/50">
      <span className="text-muted">{label}</span>
      <span className="text-cream font-medium">{value}</span>
    </div>
  );
}
