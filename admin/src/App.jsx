import { HashRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth'
import RequireAdmin from './RequireAdmin'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import QrCodesPage from './pages/QrCodesPage'
import QrDetailPage from './pages/QrDetailPage'
import UsersPage from './pages/UsersPage'
import UserDetailPage from './pages/UserDetailPage'
import ProductsPage from './pages/ProductsPage'
import ProductDetailPage from './pages/ProductDetailPage'
import ClothingPage from './pages/ClothingPage'
import ClothingDetailPage from './pages/ClothingDetailPage'
import CompetitionsPage from './pages/CompetitionsPage'
import CompetitionDetailPage from './pages/CompetitionDetailPage'

export default function App() {
  return (
    // HashRouter, not BrowserRouter — same reasoning as the Mini App
    // (miniapp/src/App.jsx): the panel is static files served by FastAPI, so
    // a hard navigation or refresh on a deep link like /admin-ui/users/<id>
    // hits the server before React ever loads, and StaticFiles(html=True)
    // only serves index.html for the mount root, not for an unmatched
    // sub-path — a plain 404. BrowserRouter's `basename` does not fix this;
    // it only affects how React Router matches paths client-side, not what
    // the server answers on first load. A hash keeps every route on the one
    // document that was actually served, so no basename is needed at all.
    <HashRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <RequireAdmin>
                <Layout />
              </RequireAdmin>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="qr-codes" element={<QrCodesPage />} />
            <Route path="qr-codes/:qrId" element={<QrDetailPage />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="users/:userId" element={<UserDetailPage />} />
            <Route path="products" element={<ProductsPage />} />
            <Route path="products/:productId" element={<ProductDetailPage />} />
            <Route path="clothing" element={<ClothingPage />} />
            <Route path="clothing/:itemId" element={<ClothingDetailPage />} />
            <Route path="competitions" element={<CompetitionsPage />} />
            <Route path="competitions/:competitionId" element={<CompetitionDetailPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </HashRouter>
  )
}