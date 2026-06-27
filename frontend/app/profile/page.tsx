"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ProfilePage() {
  const router = useRouter();
  const [farmer, setFarmer] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("farmwise_token");
    if (!token) { router.push("/login"); return; }
    fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then(setFarmer)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) return <div className="min-h-dvh bg-soil-900 flex items-center justify-center"><p className="text-muted">Loading...</p></div>;

  return (
    <div className="min-h-dvh bg-soil-900">
      <header className="sticky top-0 bg-soil-900/90 backdrop-blur border-b border-border px-4 py-4">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <h1 className="text-lg font-display font-bold text-cream">Profile</h1>
          <button onClick={() => router.push("/dashboard")} className="text-muted text-sm hover:text-cream">
            ← Dashboard
          </button>
        </div>
      </header>

      <main className="max-w-2xl mx-auto p-4">
        <div className="bg-soil-800 rounded-2xl border border-border p-6 space-y-4">
          <div className="text-center mb-4">
            <div className="w-16 h-16 bg-canopy-600/30 rounded-full flex items-center justify-center mx-auto mb-3">
              <span className="text-2xl">🌿</span>
            </div>
            <h2 className="text-xl font-display font-bold text-cream">{farmer?.name || "Farmer"}</h2>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between py-2 border-b border-border/50">
              <span className="text-muted text-sm">Farmer ID</span>
              <span className="text-cream text-sm font-mono">{farmer?.farmerId || "—"}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-border/50">
              <span className="text-muted text-sm">Phone</span>
              <span className="text-cream text-sm">{farmer?.phone || "—"}</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
