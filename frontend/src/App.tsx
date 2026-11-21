import { Route, Routes } from "react-router-dom";
import { RequireAuth } from "./auth/RequireAuth";
import { AppShell } from "./components/AppShell";
import { ComparePage } from "./pages/ComparePage";
import { HistoryPage } from "./pages/HistoryPage";
import { LoginPage } from "./pages/LoginPage";
import { MatchDetailPage } from "./pages/MatchDetailPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ProfilePage } from "./pages/ProfilePage";
import { RegisterPage } from "./pages/RegisterPage";
import { SettingsPage } from "./pages/SettingsPage";
import { WebsiteCustomizationPage } from "./pages/WebsiteCustomizationPage";
import { ShipmentPage } from "./pages/ShipmentPage";
import { TripSheetPage } from "./pages/TripSheetPage";
import { WorkspacePage } from "./pages/WorkspacePage";
import { ClientJobsPage } from "./pages/ClientJobsPage";
import { OrganizationPage } from "./pages/OrganizationPage";
import { DeliveryProofPage } from "./pages/DeliveryProofPage";
import { StaffVerificationPage } from "./pages/StaffVerificationPage";
import { PortalHome } from "./pages/PortalHome";
import { RequirePermission } from "./auth/RequirePermission";
import { CustomizationRequestPage } from "./pages/CustomizationRequestPage";
import { CustomizationAdminPage } from "./pages/CustomizationAdminPage";
import { SubscriptionPage } from "./pages/SubscriptionPage";
import { FleetPage } from "./pages/FleetPage";
import { AdminProfilePage } from "./pages/AdminProfilePage";
import { DriverRestPage } from "./pages/DriverRestPage";
import { PortalsPage } from "./pages/PortalsPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<PortalHome />} />
          <Route path="portals" element={<PortalsPage />} />
          <Route path="workspace" element={<WorkspacePage />} />
          <Route element={<RequirePermission permission="jobs:create" />}>
            <Route path="client/jobs" element={<ClientJobsPage />} />
          </Route>
          <Route element={<RequirePermission permission="organization:manage" />}>
            <Route path="organization" element={<OrganizationPage />} />
          </Route>
          <Route element={<RequirePermission permission="fleet:manage" />}>
            <Route path="fleet" element={<FleetPage />} />
          </Route>
          <Route element={<RequirePermission permission="proof:upload" />}>
            <Route path="deliveries" element={<DeliveryProofPage />} />
            <Route path="driver/rest" element={<DriverRestPage />} />
          </Route>
          <Route element={<RequirePermission permission="deliveries:verify" />}>
            <Route path="staff/verify" element={<StaffVerificationPage />} />
          </Route>
          <Route path="match/:id" element={<MatchDetailPage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="shipments/:id" element={<ShipmentPage />} />
          <Route path="shipments/:id/sheet" element={<TripSheetPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route element={<RequirePermission permission="branding:platform" />}>
            <Route path="settings/website" element={<WebsiteCustomizationPage />} />
          </Route>
          <Route path="settings/customization-request" element={<CustomizationRequestPage />} />
          <Route path="subscription" element={<SubscriptionPage />} />
          <Route element={<RequirePermission permission="branding:platform" />}>
            <Route path="admin/customization" element={<CustomizationAdminPage />} />
          </Route>
          <Route element={<RequirePermission permission="branding:platform" />}>
            <Route path="admin/profile" element={<AdminProfilePage />} />
          </Route>
          <Route path="profile" element={<ProfilePage />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
