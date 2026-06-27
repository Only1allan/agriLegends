const API_BASE = "";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("farmwise_token") || "";
}

async function authHeaders(): Promise<Record<string, string>> {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${getToken()}`,
  };
}

export async function apiGet<T>(path: string): Promise<T> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE}${path}`, { headers });
  if (!res.ok) throw new ApiError(`API error: ${res.status}`, res.status);
  return res.json();
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(`API error: ${res.status}`, res.status);
  return res.json();
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(`API error: ${res.status}`, res.status);
  return res.json();
}

// --- Auth ---
export interface LoginInput { phone: string; password: string }
export interface RegisterInput { name: string; phone: string; password: string }
export interface AuthResponse { farmerId: string; token: string; name: string }

// --- Plots ---
export interface CreatePlotInput {
  name: string; county: string; areaHa: number;
  boundaryPolygon?: string; soilType?: string; location?: { lat: number; lng: number };
}
export interface Plot {
  plotId: string; name: string; county: string; areaHa: number;
  stakeholderToken: string; activeSeasonCount?: number; activeAlertCount?: number;
  activeSeasonId?: string;
}

// --- Seasons ---
export interface CreateSeasonInput { plantingDate: string; varietyName: string }
export interface CloseSeasonInput { actualHarvestDate: string }
export interface Season {
  seasonId: string; plantingDate: string; expectedHarvestDate: string;
  status: string; varietyName: string; growthStage?: string;
}

// --- Snapshots ---
export interface DailySnapshot {
  snapshotId: string; date: string; daily_precip_mm: number;
  daily_avg_temp_c: number; daily_avg_humidity: number;
  rolling_5d_precip: number; rolling_10d_precip: number; rolling_14d_precip: number;
  rolling_5d_temp_avg: number; rolling_5d_humidity_avg: number;
  has_satellite_data: boolean; cloud_cover_percentage?: number;
  mean_ndvi?: number; mean_evi?: number;
}

// --- Alerts ---
export interface Alert {
  alertId: string; detectedCondition: string; confidence: number;
  explanation: string; recommendation: string; urgency: string;
  status: string; createdAt: number; dispatchedAt?: number;
  smsEnglish?: string; smsSwahili?: string; snapshotDate?: string;
}

// --- Observations ---
export interface CreateObservationInput { notes: string; imageUrl?: string; date: string }
export interface Observation {
  observationId: string; date: string; notes: string;
  imageUrl?: string; interpretation?: string; interpretationStatus: string;
}

// --- Interventions ---
export interface CreateInterventionInput { actionTaken: string; date: string }

// --- Expenses ---
export interface CreateExpenseInput { category: string; description: string; amount: number; date: string }
export interface ExpenseSummary {
  expenses: any[]; byCategory: Record<string, { count: number; total: number }>;
  totalAmount: number;
}

// --- Sales ---
export interface CreateSaleInput { quantity_kg: number; unit_price: number; buyer: string; sale_date: string }
export interface SaleSummary { sales: any[]; totalKg: number; totalRevenue: number }

// --- Forecast ---
export interface YieldForecast {
  forecastId: string; date: string; predictedYield: number;
  confidenceLow: number; confidenceHigh: number; basis: string;
}

// --- Stakeholder ---
export interface StakeholderReport {
  plotName: string; county: string; areaHa: number; soilType?: string;
  variety: string; plantingDate: string; expectedHarvestDate: string;
  ndviHealth: string; latestNdvi: number; lastUpdated: string;
  interventionCount: number; forecast?: any; sales?: any[];
  verification: string;
}

// --- Chat ---
export interface ChatMessage { role: string; content: string }

// Concrete API functions
export const api = {
  // Plots
  createPlot: (data: CreatePlotInput) => apiPost<Plot>("/api/plots", data),
  getPlots: () => apiGet<Plot[]>("/api/plots"),
  getPlot: (plotId: string) => apiGet<any>(`/api/plots/${plotId}`),
  regenerateToken: (plotId: string) => apiPost<{ token: string; url: string }>(`/api/plots/${plotId}/stakeholder-token`, {}),

  // Seasons
  createSeason: (plotId: string, data: CreateSeasonInput) => apiPost<Season>(`/api/plots/${plotId}/seasons`, data),
  getSeasons: (plotId: string) => apiGet<Season[]>(`/api/plots/${plotId}/seasons`),
  closeSeason: (seasonId: string, data: CloseSeasonInput) => apiPatch<any>(`/api/seasons/${seasonId}/close`, data),

  // Snapshots
  getSnapshots: (seasonId: string) => apiGet<DailySnapshot[]>(`/api/seasons/${seasonId}/snapshots`),
  getLatestSnapshot: (seasonId: string) => apiGet<DailySnapshot>(`/api/seasons/${seasonId}/snapshots/latest`),

  // Alerts
  getAlerts: (seasonId: string) => apiGet<Alert[]>(`/api/seasons/${seasonId}/alerts`),
  getAlert: (alertId: string) => apiGet<any>(`/api/alerts/${alertId}`),
  updateAlertStatus: (alertId: string, status: string) => apiPatch<any>(`/api/alerts/${alertId}/status`, { status }),

  // Observations
  createObservation: (seasonId: string, data: CreateObservationInput) => apiPost<Observation>(`/api/seasons/${seasonId}/observations`, data),
  getObservations: (seasonId: string) => apiGet<Observation[]>(`/api/seasons/${seasonId}/observations`),

  // Interventions
  createIntervention: (alertId: string, data: CreateInterventionInput) => apiPost<any>(`/api/alerts/${alertId}/interventions`, data),

  // Expenses
  getExpenses: (seasonId: string) => apiGet<ExpenseSummary>(`/api/seasons/${seasonId}/expenses`),
  createExpense: (seasonId: string, data: CreateExpenseInput) => apiPost<any>(`/api/seasons/${seasonId}/expenses`, data),

  // Sales
  createSale: (seasonId: string, data: CreateSaleInput) => apiPost<any>(`/api/seasons/${seasonId}/sales`, data),
  getSales: (seasonId: string) => apiGet<SaleSummary>(`/api/seasons/${seasonId}/sales`),

  // Forecasts
  getForecast: (seasonId: string) => apiGet<YieldForecast>(`/api/seasons/${seasonId}/forecast`),
  generateForecast: (seasonId: string) => apiPost<YieldForecast>(`/api/seasons/${seasonId}/forecast/generate`, {}),

  // Stakeholder
  getStakeholderReport: (plotId: string, token: string) => fetch(`/api/stakeholder/${plotId}/report?token=${token}`).then((r) => r.json()),

  // Chat
  chatWithFarm: (farmerId: string, message: string, seasonId?: string, history?: ChatMessage[]) =>
    fetch("/api/chat/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ farmerId, message, seasonId, history }),
    }).then((r) => r.json()),
};
