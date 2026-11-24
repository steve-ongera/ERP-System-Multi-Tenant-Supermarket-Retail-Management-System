import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./components/Layout";
import { AuthProvider } from "./context/AuthContext";

import BranchesPage from "./pages/BranchesPage";
import CustomersPage from "./pages/CustomersPage";
import DashboardPage from "./pages/DashboardPage";
import ExpensesPage from "./pages/ExpensesPage";
import InventoryPage from "./pages/InventoryPage";
import LoginPage from "./pages/LoginPage";
import MpesaPage from "./pages/MpesaPage";
import NotificationsPage from "./pages/NotificationsPage";
import PosPage from "./pages/PosPage";
import ProductsPage from "./pages/ProductsPage";
import PromotionsPage from "./pages/PromotionsPage";
import PurchaseOrdersPage from "./pages/PurchaseOrdersPage";
import ReportsPage from "./pages/ReportsPage";
import ReturnsPage from "./pages/ReturnsPage";
import SalesPage from "./pages/SalesPage";
import SettingsPage from "./pages/SettingsPage";
import ShiftsPage from "./pages/ShiftsPage";
import SuppliersPage from "./pages/SuppliersPage";
import UsersPage from "./pages/UsersPage";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route element={<ProtectedRoute />}>
          <Route index element={<DashboardPage />} />
          <Route path="pos" element={<PosPage />} />
          <Route path="sales" element={<SalesPage />} />
          <Route path="returns" element={<ReturnsPage />} />
          <Route path="shifts" element={<ShiftsPage />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="inventory" element={<InventoryPage />} />
          <Route path="purchase-orders" element={<PurchaseOrdersPage />} />
          <Route path="suppliers" element={<SuppliersPage />} />
          <Route path="customers" element={<CustomersPage />} />
          <Route path="promotions" element={<PromotionsPage />} />
          <Route path="expenses" element={<ExpensesPage />} />
          <Route path="mpesa" element={<MpesaPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="branches" element={<BranchesPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}