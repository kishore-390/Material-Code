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
import DataSynchronization from "@/pages/DataSynchronization";
import DemoDataImport from "@/pages/DemoDataImport";
import HarmonizationList from "@/pages/HarmonizationList";
import HarmonizationPairDetail from "@/pages/HarmonizationPairDetail";
import LegacyCodes from "@/pages/LegacyCodes";
import LegacyCodeDetail from "@/pages/LegacyCodeDetail";
import Login from "@/pages/Login";
import MaterialAnalysis from "@/pages/MaterialAnalysis";
import MaterialDetail from "@/pages/MaterialDetail";
import Materials from "@/pages/Materials";
import NotFound from "@/pages/NotFound";
import Notifications from "@/pages/Notifications";
import ProcurementAnalytics from "@/pages/ProcurementAnalytics";
import Settings from "@/pages/Settings";

const REVIEW_ROLES = ["ADMIN", "MATERIAL_EXPERT", "REVIEWER", "VIEWER"] as const;

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

        {/* Material Master */}
        <Route path="/materials" element={<Materials />} />
        <Route path="/materials/cpse" element={<Materials />} />
        <Route path="/materials/:id" element={<MaterialDetail />} />
        <Route path="/materials/:id/analysis" element={<MaterialAnalysis />} />
        <Route path="/common-material-master" element={<CommonMaterialMaster />} />
        <Route path="/common-material-master/:code" element={<CommonMaterialCodeDetailPage />} />
        <Route path="/legacy-codes" element={<LegacyCodes />} />
        <Route path="/legacy-codes/:code" element={<LegacyCodeDetail />} />

        {/* Harmonization */}
        <Route path="/harmonization" element={<Navigate to="/harmonization/recommendations" replace />} />
        <Route path="/harmonization/recommendations" element={<HarmonizationList />} />
        <Route path="/harmonization/duplicates" element={<HarmonizationList />} />
        <Route path="/harmonization/near-duplicates" element={<HarmonizationList />} />
        <Route path="/harmonization/functional-equivalence" element={<HarmonizationList />} />
        <Route path="/harmonization/technical-conflicts" element={<HarmonizationList />} />
        <Route path="/harmonization/pairs/:mappingId" element={<HarmonizationPairDetail />} />

        {/* CPSE Network */}
        <Route path="/cpse" element={<Cpse />} />
        <Route path="/cpse/:id" element={<CpseDetail />} />
        <Route
          path="/synchronization"
          element={
            <RequireAuth roles={["ADMIN", "MATERIAL_EXPERT"]}>
              <DataSynchronization />
            </RequireAuth>
          }
        />
        <Route
          path="/demo-import"
          element={
            <RequireAuth roles={["ADMIN", "MATERIAL_EXPERT"]}>
              <DemoDataImport />
            </RequireAuth>
          }
        />

        {/* Approvals */}
        <Route
          path="/approvals"
          element={<Navigate to="/approvals/pending" replace />}
        />
        <Route
          path="/approvals/pending"
          element={
            <RequireAuth roles={[...REVIEW_ROLES]}>
              <Approvals />
            </RequireAuth>
          }
        />
        <Route
          path="/approvals/approved"
          element={
            <RequireAuth roles={[...REVIEW_ROLES]}>
              <Approvals />
            </RequireAuth>
          }
        />
        <Route
          path="/approvals/rejected"
          element={
            <RequireAuth roles={[...REVIEW_ROLES]}>
              <Approvals />
            </RequireAuth>
          }
        />
        <Route
          path="/approvals/:id"
          element={
            <RequireAuth roles={[...REVIEW_ROLES]}>
              <ApprovalDetailPage />
            </RequireAuth>
          }
        />

        {/* Analytics */}
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/analytics/procurement" element={<ProcurementAnalytics />} />
        <Route path="/analytics/classification" element={<Analytics />} />
        <Route path="/analytics/trends" element={<Analytics />} />

        {/* Governance */}
        <Route
          path="/audit-log"
          element={
            <RequireAuth roles={[...REVIEW_ROLES]}>
              <AuditLogPage />
            </RequireAuth>
          }
        />
        <Route
          path="/governance/rules"
          element={
            <RequireAuth roles={["ADMIN"]}>
              <Settings />
            </RequireAuth>
          }
        />

        {/* System */}
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
