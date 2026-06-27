"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (loading) return;
    setLoading(true);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone.trim(), password }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || `Login failed (${res.status})`);
      }
      localStorage.setItem("farmwise_token", data.token);
      localStorage.setItem("farmwise_farmer_id", data.farmerId);
      localStorage.setItem("farmwise_name", data.name);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-dvh flex items-center justify-center bg-soil-900 p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="text-4xl mb-2">🌿</div>
          <h1 className="text-3xl font-bold font-display text-cream">FarmWise</h1>
          <p className="text-muted text-sm mt-2">Shamba lako, data yako.</p>
          <p className="text-muted text-xs">Your farm, your data.</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-soil-800 rounded-2xl border border-border p-6 space-y-4"
        >
          <div>
            <label className="block text-cream text-sm font-medium mb-1.5">Phone Number</label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="0712345678"
              required
              className="w-full bg-soil-700 border border-border rounded-lg px-4 py-3 text-cream placeholder-muted focus:outline-none focus:border-canopy-400 transition"
            />
          </div>
          <div>
            <label className="block text-cream text-sm font-medium mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
              className="w-full bg-soil-700 border border-border rounded-lg px-4 py-3 text-cream placeholder-muted focus:outline-none focus:border-canopy-400 transition"
            />
          </div>

          {error && (
            <div className="bg-alert-500/10 border border-alert-500/30 rounded-lg px-4 py-3 text-alert-300 text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-canopy-500 hover:bg-canopy-400 text-white font-semibold py-3 rounded-lg transition disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>

          <p className="text-center text-muted text-sm">
            New to FarmWise?{" "}
            <Link href="/register" className="text-canopy-300 hover:text-canopy-400">
              Create account
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
