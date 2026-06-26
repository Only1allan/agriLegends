export default function OfflinePage() {
  return (
    <div style={{ display: "flex", minHeight: "100dvh", alignItems: "center", justifyContent: "center", background: "#0d1f15", padding: 24 }}>
      <div className="glass-card" style={{ padding: 40, textAlign: "center", maxWidth: 320, width: "100%" }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>🌱</div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "#4ade80", marginBottom: 8 }}>FarmWise</h2>
        <p style={{ fontSize: 13, color: "#8b9e8e", lineHeight: 1.6 }}>
          You&apos;re offline. FarmWise needs an internet connection to fetch the latest satellite and weather data for your farm.
        </p>
        <p style={{ fontSize: 11, color: "#5a6e5e", marginTop: 16 }}>
          Your previous recommendations are saved and available when you reconnect.
        </p>
      </div>
    </div>
  );
}
