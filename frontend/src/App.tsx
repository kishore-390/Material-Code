import { Navigate, Route, Routes } from "react-router-dom";

import { RequireAuth } from "@/auth/RequireAuth";
import { AppLayout } from "@/layouts/AppLayout";
import ApprovalDetailPage from "@/pages/ApprovalDetail";
import Approvals from "@/pages/Approvals";
import Analytics from "@/pages/Analytics";
import AuditLogPage from "@/pages/AuditLog";
import CommonMaterialMaster from "@/pages/CommonMaterialMaster";
import CommonMaterialCodeDetailPage from "@/pages/CommonMaterialCodeDetail";
import Cpse from "@/pages/Cpse";
import CpseDetail from "@/pages/CpseDetail";
import Dashboard from "@/pages/Dashboard";
import FullDatabaseAnalysis from "@/pages/FullDatabaseAnalysis";
import Harmonization from "@/pages/Harmonization";
import HarmonizationDetail from "@/pages/HarmonizationDetail";
import Login from "@/pages/Login";
import MaterialAnalysis from "@/pages/MaterialAnalysis";
import MaterialDetail from "@/pages/MaterialDetail";
import Materials from "@/pages/Materials";
import NotFound from "@/pages/NotFound";
import Notifications from "@/pages/Notifications";
import Settings from "@/pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/materials" element={<Materials />} />
        <Route path="/materials/upload" element={<Navigate to="/dashboard" replace />} />
        <Route path="/materials/search" element={<Navigate to="/materials" replace />} />
        <Route path="/materials/:id" element={<MaterialDetail />} />
        <Route path="/materials/:id/analysis" element={<MaterialAnalysis />} />

        <Route path="/harmonization" element={<Harmonization />} />
        <Route
          path="/harmonization/full-database"
          element={
            <RequireAuth roles={["ADMIN", "MATERIAL_EXPERT"]}>
              <FullDatabaseAnalysis />
            </RequireAuth>
          }
        />
        <Route path="/harmonization/:id" element={<HarmonizationDetail />} />

        <Route
          path="/approvals"
          element={
            <RequireAuth roles={["ADMIN", "MATERIAL_EXPERT", "VIEWER"]}>
              <Approvals />
            </RequireAuth>
          }
        />
        <Route
          path="/approvals/:id"
          element={
            <RequireAuth roles={["ADMIN", "MATERIAL_EXPERT", "VIEWER"]}>
              <ApprovalDetailPage />
            </RequireAuth>
          }
        />

        <Route path="/common-material-master" element={<CommonMaterialMaster />} />
        <Route path="/common-material-master/:code" element={<CommonMaterialCodeDetailPage />} />

        <Route path="/cpse" element={<Cpse />} />
        <Route path="/cpse/:id" element={<CpseDetail />} />

        <Route path="/analytics" element={<Analytics />} />

        <Route
          path="/audit-log"
          element={
            <RequireAuth roles={["ADMIN", "MATERIAL_EXPERT", "VIEWER"]}>
              <AuditLogPage />
            </RequireAuth>
          }
        />

        <Route path="/notifications" element={<Notifications />} />

        <Route
          path="/settings"
          element={
            <RequireAuth roles={["ADMIN"]}>
              <Settings />
            </RequireAuth>
          }
        />

        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
