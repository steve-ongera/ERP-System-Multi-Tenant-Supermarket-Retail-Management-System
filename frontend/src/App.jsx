import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Navigate, NavLink, Outlet, Route, Routes, useNavigate } from "react-router-dom";

import {
  authApi,
  branchesApi,
  customersApi,
  errorMessage,
  expensesApi,
  mpesaApi,
  productsApi,
  promotionsApi,
  reportsApi,
  salesApi,
  shiftsApi,
  stockApi,
  suppliersApi,
  tokenStore,
  unwrap,
} from "./services/api";

const kes = (value) =>
  new Intl.NumberFormat("en-KE", { style: "currency", currency: "KES" }).format(Number(value || 0));

// ---------------------------------------------------------------------------
// Auth context
// ---------------------------------------------------------------------------
const AuthContext = createContext(null);
const useAuth = () => useContext(AuthContext);

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(tokenStore.get()));

  useEffect(() => {
    if (!tokenStore.get()) return;
    authApi
      .me()
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const onUnauthorized = () => setUser(null);
    window.addEventListener("erp:unauthorized", onUnauthorized);
    return () => window.removeEventListener("erp:unauthorized", onUnauthorized);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      login: async (username, password) => setUser(await authApi.login(username, password)),
      logout: async () => {
        await authApi.logout();
        setUser(null);
      },
    }),
    [user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function ProtectedRoute() {
  const { user, loading } = useAuth();
  if (loading) return <p className="content muted">Loading...</p>;
  return user ? <Layout /> : <Navigate to="/login" replace />;
}

// ---------------------------------------------------------------------------
// Layout
// ---------------------------------------------------------------------------
const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/pos", label: "Point of Sale" },
  { to: "/sales", label: "Sales" },
  { to: "/products", label: "Products" },
  { to: "/inventory", label: "Inventory" },
  { to: "/customers", label: "Customers" },
  { to: "/suppliers", label: "Suppliers" },
  { to: "/expenses", label: "Expenses" },
  { to: "/promotions", label: "Promotions" },
  { to: "/shifts", label: "Shifts" },
];

function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="layout">
      <nav className="sidebar">
        <h1>ERP System</h1>
        {NAV.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end}>
            {item.label}
          </NavLink>
        ))}
        <div className="spacer" />
      </nav>
      <div className="main">
        <header className="topbar">
          <span className="muted">{user.branch_name || "All branches"}</span>
          <span>
            {user.full_name || user.username}{" "}
            <span className="badge">{String(user.user_type).replace("_", " ")}</span>{" "}
            <button
              className="secondary"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
            >
              Sign out
            </button>
          </span>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Login
// ---------------------------------------------------------------------------
function LoginPage() {
  const { user, login } = useAuth();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(form.username, form.password);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <form className="card" onSubmit={submit}>
        <h2>Sign in</h2>
        {error && <div className="error">{error}</div>}
        <div className="field">
          <label>Username</label>
          <input
            autoFocus
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
          />
        </div>
        <div className="field">
          <label>Password</label>
          <input
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </div>
        <button disabled={busy || !form.username || !form.password} style={{ width: "100%" }}>
          {busy ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
function Stat({ label, value }) {
  return (
    <div className="card stat">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  );
}

function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    reportsApi.dashboard().then(setData).catch((e) => setError(errorMessage(e)));
  }, []);

  if (error) return <div className="error">{error}</div>;
  if (!data) return <p className="muted">Loading...</p>;

  return (
    <>
      <h2>Today</h2>
      <div className="grid stats">
        <Stat label="Revenue" value={kes(data.today.revenue)} />
        <Stat label="Transactions" value={data.today.transactions} />
        <Stat label="Low stock items" value={data.low_stock_count} />
        <Stat label="Expiring soon" value={data.expiring_count} />
        <Stat label="Unread alerts" value={data.unread_notifications} />
      </div>

      <div className="grid" style={{ gridTemplateColumns: "2fr 1fr" }}>
        <div className="card">
          <h3>Last 7 days</h3>
          <table>
            <thead>
              <tr><th>Date</th><th>Sales</th></tr>
            </thead>
            <tbody>
              {data.trend.map((row) => (
                <tr key={row.date}>
                  <td>{row.date}</td>
                  <td>{kes(row.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h3>Payment methods today</h3>
          {data.today.payment_methods.length === 0 && <p className="muted">No payments yet.</p>}
          <table>
            <tbody>
              {data.today.payment_methods.map((row) => (
                <tr key={row.method}>
                  <td>{row.method}</td>
                  <td>{kes(row.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Generic list + create page, used for most simple resources
// ---------------------------------------------------------------------------
function ResourcePage({ title, api, columns, fields, searchable = true, canDelete = true }) {
  const [rows, setRows] = useState([]);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(unwrap(await api.list(search ? { search } : undefined)));
      setError("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [api, search]);

  useEffect(() => {
    const timer = setTimeout(load, 250); // debounce typing in the search box
    return () => clearTimeout(timer);
  }, [load]);

  const save = async (event) => {
    event.preventDefault();
    try {
      await api.create(form);
      setForm({});
      setShowForm(false);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const remove = async (row) => {
    if (!window.confirm("Delete this record?")) return;
    try {
      await api.remove(row.id);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <>
      <h2>{title}</h2>
      {error && <div className="error">{error}</div>}
      <div className="toolbar">
        {searchable && (
          <input placeholder="Search..." value={search} onChange={(e) => setSearch(e.target.value)} />
        )}
        {fields && <button onClick={() => setShowForm((v) => !v)}>{showForm ? "Cancel" : "Add new"}</button>}
      </div>

      {showForm && fields && (
        <form className="card" onSubmit={save} style={{ marginBottom: 16, maxWidth: 520 }}>
          {fields.map((f) => (
            <div className="field" key={f.name}>
              <label>{f.label}</label>
              {f.options ? (
                <select
                  value={form[f.name] ?? ""}
                  required={f.required}
                  onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
                >
                  <option value="">Select...</option>
                  {f.options.map((o) => (
                    <option key={o.value ?? o} value={o.value ?? o}>{o.label ?? o}</option>
                  ))}
                </select>
              ) : (
                <input
                  type={f.type || "text"}
                  step={f.type === "number" ? "0.01" : undefined}
                  required={f.required}
                  value={form[f.name] ?? ""}
                  onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
                />
              )}
            </div>
          ))}
          <button>Save</button>
        </form>
      )}

      <div className="card">
        {loading ? (
          <p className="muted">Loading...</p>
        ) : rows.length === 0 ? (
          <p className="muted">Nothing here yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                {columns.map((c) => <th key={c.key}>{c.label}</th>)}
                {canDelete && <th />}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  {columns.map((c) => (
                    <td key={c.key}>{c.render ? c.render(row) : row[c.key] ?? "-"}</td>
                  ))}
                  {canDelete && (
                    <td><button className="danger" onClick={() => remove(row)}>Delete</button></td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

const statusBadge = (row) => <span className={`badge ${row.status}`}>{row.status}</span>;

const ProductsPage = () => (
  <ResourcePage
    title="Products"
    api={productsApi}
    columns={[
      { key: "sku", label: "SKU" },
      { key: "name", label: "Name" },
      { key: "category_name", label: "Category" },
      { key: "selling_price", label: "Price", render: (r) => kes(r.selling_price) },
      { key: "total_stock", label: "Stock" },
    ]}
    fields={[
      { name: "name", label: "Name", required: true },
      { name: "sku", label: "SKU", required: true },
      { name: "barcode", label: "Barcode" },
      { name: "cost_price", label: "Cost price", type: "number", required: true },
      { name: "selling_price", label: "Selling price", type: "number", required: true },
      { name: "tax_rate", label: "Tax rate (%)", type: "number" },
      { name: "reorder_level", label: "Reorder level", type: "number" },
    ]}
  />
);

const CustomersPage = () => (
  <ResourcePage
    title="Customers"
    api={customersApi}
    columns={[
      { key: "name", label: "Name" },
      { key: "phone", label: "Phone" },
      { key: "customer_type", label: "Type" },
      { key: "loyalty_points", label: "Points" },
    ]}
    fields={[
      { name: "name", label: "Name", required: true },
      { name: "phone", label: "Phone" },
      { name: "email", label: "Email", type: "email" },
      { name: "customer_type", label: "Type", options: ["retail", "wholesale", "vip"] },
    ]}
  />
);

const SuppliersPage = () => (
  <ResourcePage
    title="Suppliers"
    api={suppliersApi}
    columns={[
      { key: "name", label: "Name" },
      { key: "phone", label: "Phone" },
      { key: "email", label: "Email" },
      { key: "credit_limit", label: "Credit limit", render: (r) => kes(r.credit_limit) },
    ]}
    fields={[
      { name: "name", label: "Name", required: true },
      { name: "phone", label: "Phone" },
      { name: "email", label: "Email", type: "email" },
      { name: "credit_limit", label: "Credit limit", type: "number" },
    ]}
  />
);

const ExpensesPage = () => (
  <ResourcePage
    title="Expenses"
    api={expensesApi}
    columns={[
      { key: "date", label: "Date" },
      { key: "category", label: "Category" },
      { key: "description", label: "Description" },
      { key: "amount", label: "Amount", render: (r) => kes(r.amount) },
      { key: "payment_method", label: "Paid by" },
    ]}
    fields={[
      { name: "date", label: "Date", type: "date", required: true },
      { name: "category", label: "Category", required: true },
      { name: "description", label: "Description" },
      { name: "amount", label: "Amount", type: "number", required: true },
      {
        name: "payment_method",
        label: "Payment method",
        options: ["cash", "mpesa", "card", "bank_transfer", "cheque"],
      },
    ]}
  />
);

const PromotionsPage = () => (
  <ResourcePage
    title="Promotions"
    api={promotionsApi}
    columns={[
      { key: "name", label: "Name" },
      { key: "code", label: "Code" },
      { key: "discount_type", label: "Type" },
      { key: "discount_value", label: "Value" },
      { key: "end_date", label: "Ends" },
    ]}
    fields={[
      { name: "name", label: "Name", required: true },
      { name: "code", label: "Code", required: true },
      { name: "discount_type", label: "Type", options: ["percentage", "fixed"], required: true },
      { name: "discount_value", label: "Value", type: "number", required: true },
      { name: "start_date", label: "Start date", type: "date", required: true },
      { name: "end_date", label: "End date", type: "date", required: true },
    ]}
  />
);

// ---------------------------------------------------------------------------
// Sales history
// ---------------------------------------------------------------------------
function SalesPage() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    salesApi.list().then((d) => setRows(unwrap(d))).catch((e) => setError(errorMessage(e)));
  }, []);

  return (
    <>
      <h2>Sales</h2>
      {error && <div className="error">{error}</div>}
      <div className="card">
        <table>
          <thead>
            <tr><th>Invoice</th><th>Date</th><th>Customer</th><th>Total</th><th>Status</th></tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id}>
                <td>{s.invoice_number}</td>
                <td>{new Date(s.created_at).toLocaleString("en-KE")}</td>
                <td>{s.customer_name || "Walk-in"}</td>
                <td>{kes(s.total_amount)}</td>
                <td>{statusBadge(s)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Inventory (stock levels + low stock)
// ---------------------------------------------------------------------------
function InventoryPage() {
  const [levels, setLevels] = useState([]);
  const [onlyLow, setOnlyLow] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const request = onlyLow ? stockApi.lowStock() : stockApi.levels();
    request.then((d) => setLevels(unwrap(d))).catch((e) => setError(errorMessage(e)));
  }, [onlyLow]);

  return (
    <>
      <h2>Inventory</h2>
      {error && <div className="error">{error}</div>}
      <div className="toolbar">
        <button className={onlyLow ? "" : "secondary"} onClick={() => setOnlyLow((v) => !v)}>
          {onlyLow ? "Showing low stock only" : "Show low stock only"}
        </button>
      </div>
      <div className="card">
        <table>
          <thead>
            <tr><th>Product</th><th>Branch</th><th>Quantity</th><th /></tr>
          </thead>
          <tbody>
            {levels.map((l) => (
              <tr key={l.id}>
                <td>{l.product_name}</td>
                <td>{l.branch_name}</td>
                <td>{l.quantity}</td>
                <td>{l.is_low && <span className="badge pending">Low</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Shifts
// ---------------------------------------------------------------------------
function ShiftsPage() {
  const { user } = useAuth();
  const [current, setCurrent] = useState(null);
  const [branches, setBranches] = useState([]);
  const [branch, setBranch] = useState(user.branch || "");
  const [cash, setCash] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const refresh = useCallback(() => shiftsApi.current().then(setCurrent), []);

  useEffect(() => {
    refresh().catch((e) => setError(errorMessage(e)));
    branchesApi.list().then((d) => setBranches(unwrap(d))).catch(() => {});
  }, [refresh]);

  const act = async (fn) => {
    setError("");
    setMessage("");
    try {
      await fn();
      setCash("");
      await refresh();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <>
      <h2>Shift</h2>
      {error && <div className="error">{error}</div>}
      {message && <p>{message}</p>}
      <div className="card" style={{ maxWidth: 420 }}>
        {current ? (
          <>
            <p>
              Shift open since {new Date(current.opened_at).toLocaleTimeString("en-KE")} with{" "}
              {kes(current.opening_cash)} opening cash.
            </p>
            <div className="field">
              <label>Counted cash in drawer</label>
              <input type="number" step="0.01" value={cash} onChange={(e) => setCash(e.target.value)} />
            </div>
            <button
              className="danger"
              disabled={cash === ""}
              onClick={() =>
                act(async () => {
                  const closed = await shiftsApi.close(current.id, cash);
                  setMessage(`Shift closed. Variance: ${kes(closed.variance)}`);
                })
              }
            >
              Close shift
            </button>
          </>
        ) : (
          <>
            <div className="field">
              <label>Branch</label>
              <select value={branch} onChange={(e) => setBranch(e.target.value)}>
                <option value="">Select...</option>
                {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Opening cash</label>
              <input type="number" step="0.01" value={cash} onChange={(e) => setCash(e.target.value)} />
            </div>
            <button disabled={!branch || cash === ""} onClick={() => act(() => shiftsApi.open(branch, cash))}>
              Open shift
            </button>
          </>
        )}
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Point of Sale
// ---------------------------------------------------------------------------
function PosPage() {
  const { user } = useAuth();
  const [branches, setBranches] = useState([]);
  const [branch, setBranch] = useState(user.branch || "");
  const [customers, setCustomers] = useState([]);
  const [customer, setCustomer] = useState("");
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState("");
  const [cart, setCart] = useState([]);
  const [method, setMethod] = useState("cash");
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState(null);

  useEffect(() => {
    branchesApi.list().then((d) => {
      const list = unwrap(d);
      setBranches(list);
      if (!branch && list.length === 1) setBranch(list[0].id);
    }).catch(() => {});
    customersApi.list().then((d) => setCustomers(unwrap(d))).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      productsApi
        .list({ search, is_active: true })
        .then((d) => setProducts(unwrap(d)))
        .catch((e) => setError(errorMessage(e)));
    }, 250);
    return () => clearTimeout(timer);
  }, [search]);

  const addToCart = (product) =>
    setCart((items) => {
      const existing = items.find((i) => i.product.id === product.id);
      if (existing) {
        return items.map((i) => (i.product.id === product.id ? { ...i, quantity: i.quantity + 1 } : i));
      }
      return [...items, { product, quantity: 1 }];
    });

  const setQuantity = (id, quantity) =>
    setCart((items) =>
      items
        .map((i) => (i.product.id === id ? { ...i, quantity: Math.max(0, Number(quantity)) } : i))
        .filter((i) => i.quantity > 0)
    );

  const total = cart.reduce((sum, i) => sum + i.quantity * Number(i.product.selling_price), 0);

  const checkout = async () => {
    setBusy(true);
    setError("");
    try {
      const payload = {
        branch,
        customer: customer || null,
        items: cart.map((i) => ({ product: i.product.id, quantity: i.quantity })),
        payments: [{ method, amount: total.toFixed(2) }],
      };
      let sale = await salesApi.checkout(payload);

      if (method === "mpesa") {
        // Sale is saved as pending; prompt the customer and wait for their PIN.
        const txn = await mpesaApi.stkPush({
          phone_number: phone,
          amount: sale.total_amount,
          sale: sale.id,
          account_reference: sale.invoice_number.slice(-12),
          description: "Purchase",
        });
        const result = await mpesaApi.waitForPayment(txn.checkout_request_id);
        if (result.status !== "success") {
          throw new Error(`M-Pesa payment ${result.status}: ${result.result_desc || "not completed"}`);
        }
        sale = await salesApi.get(sale.id);
      }

      setReceipt(sale);
      setCart([]);
      setPhone("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <h2>Point of Sale</h2>
      {error && <div className="error">{error}</div>}

      {receipt && (
        <div className="card" style={{ marginBottom: 16 }}>
          <strong>Sale {receipt.invoice_number}</strong> - {kes(receipt.total_amount)}{" "}
          <span className={`badge ${receipt.status}`}>{receipt.status}</span>{" "}
          <button className="secondary" onClick={() => setReceipt(null)}>Dismiss</button>
        </div>
      )}

      <div className="pos">
        <div className="card">
          <input
            autoFocus
            placeholder="Search by name, SKU or barcode..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="products">
            {products.map((p) => (
              <button key={p.id} className="product-tile" onClick={() => addToCart(p)}>
                <div>{p.name}</div>
                <div className="muted">{kes(p.selling_price)}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="card">
          <h3>Cart</h3>
          {!user.branch && (
            <div className="field">
              <label>Branch</label>
              <select value={branch} onChange={(e) => setBranch(e.target.value)}>
                <option value="">Select...</option>
                {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </div>
          )}
          <div className="field">
            <label>Customer (optional)</label>
            <select value={customer} onChange={(e) => setCustomer(e.target.value)}>
              <option value="">Walk-in</option>
              {customers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>

          {cart.length === 0 ? (
            <p className="muted">Tap a product to add it.</p>
          ) : (
            <table>
              <tbody>
                {cart.map((i) => (
                  <tr key={i.product.id}>
                    <td>{i.product.name}</td>
                    <td style={{ width: 70 }}>
                      <input
                        type="number"
                        min="0"
                        value={i.quantity}
                        onChange={(e) => setQuantity(i.product.id, e.target.value)}
                      />
                    </td>
                    <td>{kes(i.quantity * Number(i.product.selling_price))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <div className="totals">
            <span>Total</span>
            <span>{kes(total)}</span>
          </div>
          <p className="muted" style={{ marginTop: -8 }}>Tax and discounts are applied at checkout.</p>

          <div className="field">
            <label>Payment method</label>
            <select value={method} onChange={(e) => setMethod(e.target.value)}>
              <option value="cash">Cash</option>
              <option value="mpesa">M-Pesa</option>
              <option value="card">Card</option>
            </select>
          </div>
          {method === "mpesa" && (
            <div className="field">
              <label>Customer phone</label>
              <input placeholder="0712345678" value={phone} onChange={(e) => setPhone(e.target.value)} />
            </div>
          )}

          <button
            style={{ width: "100%" }}
            disabled={busy || cart.length === 0 || !branch || (method === "mpesa" && !phone)}
            onClick={checkout}
          >
            {busy ? (method === "mpesa" ? "Waiting for customer..." : "Processing...") : "Charge"}
          </button>
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------
export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route index element={<Dashboard />} />
          <Route path="pos" element={<PosPage />} />
          <Route path="sales" element={<SalesPage />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="inventory" element={<InventoryPage />} />
          <Route path="customers" element={<CustomersPage />} />
          <Route path="suppliers" element={<SuppliersPage />} />
          <Route path="expenses" element={<ExpensesPage />} />
          <Route path="promotions" element={<PromotionsPage />} />
          <Route path="shifts" element={<ShiftsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}