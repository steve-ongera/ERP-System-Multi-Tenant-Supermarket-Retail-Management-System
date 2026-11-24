import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const TOKEN_KEY = "erp_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

// Attach the auth token to every request.
api.interceptors.request.use((config) => {
  const token = tokenStore.get();
  if (token) config.headers.Authorization = `Token ${token}`;
  return config;
});

// On 401, drop the token and tell the app so it can redirect to the login page.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && tokenStore.get()) {
      tokenStore.clear();
      window.dispatchEvent(new Event("erp:unauthorized"));
    }
    return Promise.reject(error);
  }
);

/** Turn any axios/DRF error into a single readable message. */
export function errorMessage(error) {
  const data = error?.response?.data;
  if (!data) return error?.message || "Something went wrong.";
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  const first = Object.entries(data)[0];
  if (!first) return "Request failed.";
  const [field, value] = first;
  const text = Array.isArray(value) ? value[0] : JSON.stringify(value);
  return field === "non_field_errors" ? text : `${field}: ${text}`;
}

/** DRF returns {results: [...]} when paginated and a bare array otherwise. */
export const unwrap = (data) => (Array.isArray(data) ? data : data?.results ?? []);

/** Build list/get/create/update/remove helpers for a REST resource. */
const resource = (path) => ({
  list: (params) => api.get(`/${path}/`, { params }).then((r) => r.data),
  get: (id) => api.get(`/${path}/${id}/`).then((r) => r.data),
  create: (payload) => api.post(`/${path}/`, payload).then((r) => r.data),
  update: (id, payload) => api.patch(`/${path}/${id}/`, payload).then((r) => r.data),
  remove: (id) => api.delete(`/${path}/${id}/`),
});

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
export const authApi = {
  login: async (username, password) => {
    const { data } = await api.post("/auth/login/", { username, password });
    tokenStore.set(data.token);
    return data.user;
  },
  logout: async () => {
    try {
      await api.post("/auth/logout/");
    } finally {
      tokenStore.clear();
    }
  },
  me: () => api.get("/auth/me/").then((r) => r.data),
};

// ---------------------------------------------------------------------------
// CRUD resources
// ---------------------------------------------------------------------------
export const branchesApi = resource("branches");
export const usersApi = resource("users");
export const employeesApi = resource("employees");
export const categoriesApi = resource("categories");
export const suppliersApi = resource("suppliers");
export const customersApi = resource("customers");
export const expensesApi = resource("expenses");
export const promotionsApi = resource("promotions");
export const returnsApi = resource("returns");

export const productsApi = {
  ...resource("products"),
  lookup: (code) => api.get("/products/lookup/", { params: { code } }).then((r) => r.data),
};

export const stockApi = {
  levels: (params) => api.get("/stock-levels/", { params }).then((r) => r.data),
  lowStock: () => api.get("/stock-levels/low/").then((r) => r.data),
  movements: (params) => api.get("/stock-movements/", { params }).then((r) => r.data),
  adjust: (payload) => api.post("/stock/adjust/", payload).then((r) => r.data),
  transfer: (payload) => api.post("/stock/transfer/", payload).then((r) => r.data),
  expiring: () => api.get("/stock/expiring/").then((r) => r.data),
};

export const purchaseOrdersApi = {
  ...resource("purchase-orders"),
  approve: (id) => api.post(`/purchase-orders/${id}/approve/`).then((r) => r.data),
  receive: (id, items) => api.post(`/purchase-orders/${id}/receive/`, { items }).then((r) => r.data),
  cancel: (id) => api.post(`/purchase-orders/${id}/cancel/`).then((r) => r.data),
};

export const salesApi = {
  list: (params) => api.get("/sales/", { params }).then((r) => r.data),
  get: (id) => api.get(`/sales/${id}/`).then((r) => r.data),
  checkout: (payload) => api.post("/sales/checkout/", payload).then((r) => r.data),
  void: (id, reason) => api.post(`/sales/${id}/void/`, { reason }).then((r) => r.data),
};

export const shiftsApi = {
  list: (params) => api.get("/shifts/", { params }).then((r) => r.data),
  current: () => api.get("/shifts/current/").then((r) => r.data),
  open: (branch, opening_cash) => api.post("/shifts/", { branch, opening_cash }).then((r) => r.data),
  close: (id, closing_cash, notes = "") =>
    api.post(`/shifts/${id}/close/`, { closing_cash, notes }).then((r) => r.data),
};

export const notificationsApi = {
  list: (params) => api.get("/notifications/", { params }).then((r) => r.data),
  markRead: (id) => api.post(`/notifications/${id}/mark-read/`).then((r) => r.data),
  markAllRead: () => api.post("/notifications/mark-all-read/").then((r) => r.data),
};

export const settingsApi = {
  get: () => api.get("/settings/").then((r) => r.data),
  update: (payload) => api.put("/settings/", payload).then((r) => r.data),
};

// ---------------------------------------------------------------------------
// M-Pesa
// ---------------------------------------------------------------------------
export const mpesaApi = {
  stkPush: (payload) => api.post("/mpesa/stk-push/", payload).then((r) => r.data),
  status: (checkoutRequestId) => api.get(`/mpesa/status/${checkoutRequestId}/`).then((r) => r.data),

  /**
   * Poll until the customer approves, declines or the prompt times out.
   * Resolves with the final transaction; rejects on timeout.
   */
  waitForPayment: async (checkoutRequestId, { intervalMs = 3000, timeoutMs = 90000 } = {}) => {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const txn = await mpesaApi.status(checkoutRequestId);
      if (txn.status !== "pending") return txn;
      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }
    throw new Error("Timed out waiting for the M-Pesa confirmation.");
  },
};

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------
export const reportsApi = {
  dashboard: () => api.get("/reports/dashboard/").then((r) => r.data),
  dailySales: (params) => api.get("/reports/daily-sales/", { params }).then((r) => r.data),
  salesTrend: (days = 14) => api.get("/reports/sales-trend/", { params: { days } }).then((r) => r.data),
  topProducts: (params) => api.get("/reports/top-products/", { params }).then((r) => r.data),
  salesByCategory: (params) => api.get("/reports/sales-by-category/", { params }).then((r) => r.data),
  profitLoss: (params) => api.get("/reports/profit-loss/", { params }).then((r) => r.data),
  inventoryValuation: () => api.get("/reports/inventory-valuation/").then((r) => r.data),
  topCustomers: () => api.get("/reports/top-customers/").then((r) => r.data),
};

export default api;