import React, { useState, useEffect } from "react";
import {
  LayoutDashboard, Search, Shuffle, CheckSquare, Database, Building2, BarChart3,
  History, Bell, Settings, Menu, HelpCircle, ChevronDown, X, Check, XCircle,
  Eye, ArrowRight, TrendingUp, TrendingDown, Clock, PlusCircle, FileBarChart2,
  Download, AlertCircle, Filter, Landmark, GitMerge, Boxes, CircleCheck,
} from "lucide-react";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Legend, BarChart, Bar,
} from "recharts";

/* ============================== palette ============================== */
const P = {
  navy: "#0A2342",
  navyDeep: "#071A34",
  navySoft: "#123561",
  paper: "#F4F6F9",
  card: "#FFFFFF",
  line: "#E4E8EF",
  ink: "#16233A",
  sub: "#5B6B85",
  blue: "#2563EB",
  blueSoft: "#EAF1FE",
  green: "#15803D",
  greenSoft: "#E6F5EA",
  orange: "#C2670A",
  orangeSoft: "#FDF0DD",
  red: "#DC2626",
  redSoft: "#FCEAEA",
  gray: "#94A3B8",
  graySoft: "#EEF1F5",
};

/* ============================== mock data ============================== */
const cpseList = [
  { name: "IOCL", full: "Indian Oil Corporation Limited", sector: "Oil & Gas", harmonized: 18765 },
  { name: "ONGC", full: "Oil and Natural Gas Corporation", sector: "Oil & Gas", harmonized: 15432 },
  { name: "BPCL", full: "Bharat Petroleum Corporation Limited", sector: "Oil & Gas", harmonized: 12876 },
  { name: "HPCL", full: "Hindustan Petroleum Corporation Limited", sector: "Oil & Gas", harmonized: 9874 },
  { name: "GAIL", full: "GAIL (India) Limited", sector: "Gas Transmission", harmonized: 7654 },
  { name: "BHEL", full: "Bharat Heavy Electricals Limited", sector: "Heavy Engineering", harmonized: 6921 },
];

const initialApprovals = [
  { id: 1, material: "Carbon Steel Seamless Pipe", cpse: "IOCL", code: "CS-PIPE-00124", confidence: 96.8, status: "Pending",
    category: "Piping & Fittings", existingCodes: ["IOCL-MAT-1023", "ONGC-PIP-4481", "BPCL-CS-0912"],
    reason: "High semantic and specification similarity confirmed across three CPSEs." },
  { id: 2, material: 'Ball Valve 4"', cpse: "ONGC", code: "BV-004-STD", confidence: 94.2, status: "Pending",
    category: "Valves", existingCodes: ["ONGC-VLV-2210", "GAIL-BV4-0087"],
    reason: "Matching pressure rating, bore size and body material across CPSEs." },
  { id: 3, material: "Industrial Lubricant", cpse: "BPCL", code: "LUB-IND-0021", confidence: 91.7, status: "Pending",
    category: "Consumables", existingCodes: ["BPCL-LUB-441", "HPCL-LB-0099"],
    reason: "Similar viscosity grade, base oil type and application class." },
  { id: 4, material: "Safety Helmet", cpse: "HPCL", code: "SH-STD-0045", confidence: 88.3, status: "Pending",
    category: "Safety Equipment", existingCodes: ["HPCL-PPE-118", "BHEL-HLM-552"],
    reason: "Shell material spec variance flagged — recommend manual verification." },
  { id: 5, material: 'Gasket Ring 2"', cpse: "GAIL", code: "GR-002-STD", confidence: 97.5, status: "Pending",
    category: "Fittings", existingCodes: ["GAIL-GSK-771", "IOCL-GSK-2290"],
    reason: "Near-identical dimensional and material specification." },
];

const initialChangeLog = [
  { time: "09:12", date: "30 Aug 2026", actor: "AI Engine", action: "Generated recommendation CS-PIPE-00124", material: "Carbon Steel Seamless Pipe", confidence: "96.8%", version: "v1" },
  { time: "09:40", date: "30 Aug 2026", actor: "AI Engine", action: "Flagged duplicate cluster across BHEL, ONGC", material: "M-10245", confidence: "—", version: "v1" },
  { time: "10:05", date: "30 Aug 2026", actor: "R. Sharma (IOCL)", action: "Approved recommendation", material: "LUB-IND-0021", confidence: "91.7%", version: "v1" },
  { time: "10:41", date: "30 Aug 2026", actor: "AI Engine", action: "Auto-scored new duplicate cluster", material: "Pressure Gauge 100mm", confidence: "93.4%", version: "v1" },
  { time: "11:15", date: "30 Aug 2026", actor: "S. Verma (ONGC)", action: "Rejected recommendation — specification mismatch", material: "Flange Class 300", confidence: "79.2%", version: "v1" },
];

const initialNotifications = [
  { type: "approval", text: "12,345 recommendations awaiting your approval", time: "5 minutes ago" },
  { type: "ai", text: "AI detected 3 new duplicate materials at BHEL", time: "20 minutes ago" },
  { type: "system", text: "Weekly harmonization report is ready to download", time: "1 hour ago" },
  { type: "approval", text: "Material M-9876 requires human approval", time: "2 hours ago" },
  { type: "system", text: "New CPSE onboarded: NTPC", time: "1 day ago" },
];

const materialMaster = [
  { code: "PVC-PIPE-00087", name: "PVC Pipe 6-inch", linked: 3, cpses: "IOCL, HPCL, BPCL", date: "12 Aug 2026" },
  { code: "MS-PLATE-00231", name: "MS Plate 10mm", linked: 4, cpses: "BHEL, SAIL, NTPC, ONGC", date: "08 Aug 2026" },
  { code: "BRG-6205-STD", name: "Ball Bearing 6205", linked: 2, cpses: "BHEL, GAIL", date: "03 Aug 2026" },
  { code: "CBL-XLPE-00119", name: "XLPE Power Cable 11kV", linked: 3, cpses: "NTPC, ONGC, IOCL", date: "29 Jul 2026" },
];

const recentActivity = [
  { tone: "green", text: "Material M-10245 harmonized", meta: "IOCL", time: "12 minutes ago" },
  { tone: "blue", text: "New duplicate material detected", meta: "BHEL", time: "35 minutes ago" },
  { tone: "orange", text: "Human approval required — M-9876", meta: "Pending", time: "1 hour ago" },
  { tone: "green", text: "Material recommendation approved", meta: "BPCL", time: "2 hours ago" },
  { tone: "blue", text: "New CPSE materials imported", meta: "ONGC", time: "4 hours ago" },
];

const trendData = [
  { week: "Week 1", harmonized: 58000, review: 14000, pending: 16000 },
  { week: "Week 2", harmonized: 63500, review: 15200, pending: 15100 },
  { week: "Week 3", harmonized: 69800, review: 16400, pending: 14300 },
  { week: "Week 4", harmonized: 75600, review: 17100, pending: 13500 },
  { week: "Week 5", harmonized: 80900, review: 18300, pending: 12800 },
  { week: "Week 6", harmonized: 86245, review: 18900, pending: 12345 },
];

const donutData = [
  { name: "Harmonized", value: 69.2, count: "86,245", color: P.green },
  { name: "Under AI Review", value: 15.1, count: "18,900", color: P.blue },
  { name: "Pending Human Approval", value: 9.9, count: "12,345", color: P.orange },
  { name: "Not Harmonized", value: 5.8, count: "7,077", color: P.gray },
];

const impactMetrics = [
  { label: "Duplicate Codes Reduced", value: "8,765", note: "Across all onboarded CPSEs", icon: Shuffle },
  { label: "Material Data Quality", value: "92.6%", note: "Improvement in master data accuracy", icon: CheckSquare },
  { label: "Estimated Procurement Savings", value: "₹24.8 Cr", note: "Via cross-CPSE rate consolidation", icon: TrendingUp },
  { label: "Inventory Visibility", value: "85.7%", note: "Cross-CPSE stock visibility", icon: Eye },
];

const pipelineSteps = [
  "Material Input", "Data Cleaning & Normalization", "Semantic Similarity Analysis",
  "AI Duplicate Detection", "Common Code Recommendation", "Confidence Score",
  "Human Approval", "Standardized Material Master",
];

const navItems = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { key: "search", label: "Material Search", icon: Search },
  { key: "harmonization", label: "AI Harmonization", icon: GitMerge },
  { key: "approval", label: "Approval Center", icon: CheckSquare },
  { key: "master", label: "Material Master", icon: Database },
  { key: "cpse", label: "CPSE Directory", icon: Building2 },
  { key: "analytics", label: "Analytics & Reports", icon: BarChart3 },
  { key: "changelog", label: "Change Log", icon: History },
  { key: "notifications", label: "Notifications", icon: Bell },
  { key: "settings", label: "Settings", icon: Settings },
];

/* ============================== shared bits ============================== */
function Card({ children, className = "", style = {} }) {
  return (
    <div className={`rounded-xl bg-white border shadow-sm ${className}`} style={{ borderColor: P.line, ...style }}>
      {children}
    </div>
  );
}

function ConfidencePill({ value }) {
  const tone = value >= 95 ? P.green : value >= 90 ? P.blue : P.orange;
  return (
    <span className="inline-flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-full" style={{ background: `${tone}18`, color: tone }}>
      {value}%
    </span>
  );
}

function StatusPill({ status }) {
  const map = {
    Pending: { bg: P.orangeSoft, fg: P.orange },
    Approved: { bg: P.greenSoft, fg: P.green },
    Rejected: { bg: P.redSoft, fg: P.red },
  };
  const c = map[status] || map.Pending;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full" style={{ background: c.bg, color: c.fg }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: c.fg }} />
      {status}
    </span>
  );
}

function Toast({ message, onClose }) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onClose, 3000);
    return () => clearTimeout(t);
  }, [message]);
  if (!message) return null;
  return (
    <div className="fixed bottom-6 right-6 z-[60] flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white"
      style={{ background: P.navy }}>
      <CircleCheck size={16} color={P.green} />
      {message}
      <button onClick={onClose} className="ml-2 opacity-70 hover:opacity-100"><X size={14} /></button>
    </div>
  );
}

/* ============================== compare / review modal ============================== */
function CompareModal({ item, onClose, onDecide }) {
  if (!item) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(7,26,52,0.55)" }} onClick={onClose}>
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[88vh] overflow-y-auto shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="px-6 py-4 flex items-center justify-between border-b" style={{ borderColor: P.line, background: P.paper }}>
          <div>
            <div className="text-xs font-medium" style={{ color: P.sub }}>{item.category}</div>
            <div className="text-lg font-bold" style={{ color: P.navy }}>{item.material}</div>
          </div>
          <div className="flex items-center gap-3">
            <StatusPill status={item.status} />
            <button onClick={onClose} className="p-1.5 rounded-full hover:bg-slate-200"><X size={18} /></button>
          </div>
        </div>
        <div className="p-6 space-y-6">
          <div>
            <div className="text-xs font-bold uppercase tracking-wide mb-2" style={{ color: P.sub }}>Existing CPSE Codes</div>
            <div className="flex flex-wrap gap-2">
              {item.existingCodes.map((c) => (
                <span key={c} className="text-xs font-mono font-semibold px-2.5 py-1.5 rounded-md" style={{ background: P.graySoft, color: P.ink }}>{c}</span>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-3 rounded-lg p-4" style={{ background: P.blueSoft }}>
            <ArrowRight size={18} color={P.blue} />
            <div>
              <div className="text-xs font-bold" style={{ color: P.blue }}>AI Recommended Common Code</div>
              <div className="text-xl font-bold font-mono" style={{ color: P.navy }}>{item.code}</div>
            </div>
            <div className="ml-auto"><ConfidencePill value={item.confidence} /></div>
          </div>
          <div className="rounded-lg p-4" style={{ background: P.paper, border: `1px solid ${P.line}` }}>
            <div className="text-xs font-bold mb-1" style={{ color: P.sub }}>AI Explainability</div>
            <p className="text-sm" style={{ color: P.ink }}>{item.reason}</p>
          </div>
          {item.status === "Pending" && (
            <div className="flex gap-3 pt-2">
              <button onClick={() => onDecide(item.id, "Approved")}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg font-semibold text-sm text-white" style={{ background: P.green }}>
                <Check size={16} /> Approve Recommendation
              </button>
              <button onClick={() => onDecide(item.id, "Rejected")}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg font-semibold text-sm" style={{ background: P.redSoft, color: P.red }}>
                <XCircle size={16} /> Reject
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ============================== AI Harmonization Engine block ============================== */
function AIEngineSection({ approvals, onDecide, onCompare }) {
  const sample = approvals.find((a) => a.id === 1);
  return (
    <Card className="p-6">
      <div className="flex items-center gap-2 mb-1">
        <GitMerge size={18} color={P.blue} />
        <h3 className="text-base font-bold" style={{ color: P.navy }}>AI Harmonization Engine</h3>
      </div>
      <p className="text-xs mb-5" style={{ color: P.sub }}>
        AI detects, compares and recommends — a human expert always makes the final approval decision.
      </p>
      <div className="flex items-center overflow-x-auto pb-2">
        {pipelineSteps.map((s, i) => (
          <React.Fragment key={s}>
            <div className="flex flex-col items-center text-center gap-1.5 shrink-0" style={{ width: 108 }}>
              <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white" style={{ background: P.navy }}>{i + 1}</div>
              <span className="text-[10px] font-semibold leading-tight" style={{ color: P.ink }}>{s}</span>
            </div>
            {i < pipelineSteps.length - 1 && <ArrowRight size={14} color={P.line} className="shrink-0 mx-0.5" />}
          </React.Fragment>
        ))}
      </div>

      {sample && (
        <div className="mt-5 rounded-xl p-5" style={{ background: P.paper, border: `1px solid ${P.line}` }}>
          <div className="text-[11px] font-bold uppercase tracking-wide mb-2" style={{ color: P.sub }}>Sample AI Recommendation</div>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-sm font-bold" style={{ color: P.navy }}>{sample.material}</div>
              <div className="text-xs mt-1" style={{ color: P.sub }}>Existing codes:</div>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {sample.existingCodes.map((c) => (
                  <span key={c} className="text-[11px] font-mono px-2 py-0.5 rounded" style={{ background: "#fff", border: `1px solid ${P.line}`, color: P.ink }}>{c}</span>
                ))}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs font-semibold" style={{ color: P.sub }}>COMMON CODE</div>
              <div className="text-lg font-bold font-mono" style={{ color: P.blue }}>{sample.code}</div>
              <div className="flex items-center gap-2 justify-end mt-1">
                <ConfidencePill value={sample.confidence} />
                <StatusPill status={sample.status} />
              </div>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button onClick={() => onDecide(sample.id, "Approved")} disabled={sample.status !== "Pending"}
              className="text-xs font-semibold px-3 py-2 rounded-md text-white flex items-center gap-1.5 disabled:opacity-40"
              style={{ background: P.green }}><Check size={14} /> Approve Recommendation</button>
            <button onClick={() => onDecide(sample.id, "Rejected")} disabled={sample.status !== "Pending"}
              className="text-xs font-semibold px-3 py-2 rounded-md flex items-center gap-1.5 disabled:opacity-40"
              style={{ background: P.redSoft, color: P.red }}><XCircle size={14} /> Reject</button>
            <button onClick={() => onCompare(sample)}
              className="text-xs font-semibold px-3 py-2 rounded-md border flex items-center gap-1.5" style={{ borderColor: P.line, color: P.navy }}>
              <Eye size={14} /> View Comparison
            </button>
          </div>
        </div>
      )}
    </Card>
  );
}

/* ============================== Dashboard tab ============================== */
function DashboardTab({ approvals, onDecide, onCompare, setTab }) {
  const kpis = [
    { label: "Total Material Records", value: "487", change: "+8.7% vs last month", icon: Database, tone: P.navy, bg: P.graySoft },
    { label: "Harmonized Materials", value: "342", change: "+12.5%", icon: GitMerge, tone: P.green, bg: P.greenSoft },
    { label: "Pending Human Approval", value: "89", change: "5.3% decrease", icon: Clock, tone: P.orange, bg: P.orangeSoft },
    { label: "CPSEs Onboarded", value: "24", change: "Across multiple sectors", icon: Building2, tone: P.blue, bg: P.blueSoft },
  ];
  const toneDot = { green: P.green, blue: P.blue, orange: P.orange };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold" style={{ color: P.navy }}>Welcome, Admin User</h2>
          <p className="text-sm" style={{ color: P.sub }}>Monitor and manage material-code harmonization across CPSEs</p>
        </div>
        <span className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full" style={{ background: P.greenSoft, color: P.green }}>
          <span className="w-2 h-2 rounded-full" style={{ background: P.green }} /> System Operational
        </span>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {kpis.map((k) => (
          <Card key={k.label} className="p-4">
            <div className="flex items-center justify-between">
              <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: k.bg }}>
                <k.icon size={17} color={k.tone} />
              </div>
            </div>
            <div className="text-2xl font-bold mt-3" style={{ color: P.navy }}>{k.value}</div>
            <div className="text-xs font-medium mt-0.5" style={{ color: P.sub }}>{k.label}</div>
            <div className="text-xs font-semibold mt-1.5" style={{ color: k.change.includes("decrease") ? P.orange : P.green }}>{k.change}</div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-5">
        <Card className="col-span-1 p-5">
          <h3 className="text-sm font-bold mb-3" style={{ color: P.ink }}>Material Harmonization Progress</h3>
          <div className="relative">
            <ResponsiveContainer width="100%" height={190}>
              <PieChart>
                <Pie data={donutData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={80} paddingAngle={2}>
                  {donutData.map((d, i) => <Cell key={i} fill={d.color} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none" style={{ marginTop: -8 }}>
              <div className="text-lg font-bold" style={{ color: P.navy }}>1,24,567</div>
              <div className="text-[10px]" style={{ color: P.sub }}>Total Materials</div>
            </div>
          </div>
          <div className="space-y-1.5 mt-2">
            {donutData.map((d) => (
              <div key={d.name} className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5" style={{ color: P.ink }}>
                  <span className="w-2 h-2 rounded-full" style={{ background: d.color }} />{d.name}
                </span>
                <span style={{ color: P.sub }}>{d.count} · {d.value}%</span>
              </div>
            ))}
          </div>
          <button onClick={() => setTab("analytics")} className="text-xs font-semibold mt-3 flex items-center gap-1" style={{ color: P.blue }}>
            View Detailed Analytics <ArrowRight size={12} />
          </button>
        </Card>

        <Card className="col-span-2 p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold" style={{ color: P.ink }}>AI Harmonization Trend</h3>
            <span className="text-xs font-semibold flex items-center gap-1 px-2 py-1 rounded-md border" style={{ borderColor: P.line, color: P.sub }}>
              Weekly <ChevronDown size={12} />
            </span>
          </div>
          <ResponsiveContainer width="100%" height={190}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke={P.line} vertical={false} />
              <XAxis dataKey="week" tick={{ fontSize: 11, fill: P.sub }} axisLine={{ stroke: P.line }} />
              <YAxis tick={{ fontSize: 11, fill: P.sub }} axisLine={{ stroke: P.line }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="harmonized" name="Harmonized" stroke={P.green} strokeWidth={2.5} dot={false} />
              <Line type="monotone" dataKey="review" name="Under AI Review" stroke={P.blue} strokeWidth={2.5} dot={false} />
              <Line type="monotone" dataKey="pending" name="Pending Approval" stroke={P.orange} strokeWidth={2.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
          <div className="text-xs font-semibold mt-1" style={{ color: P.green }}>+18.4% overall harmonization growth</div>
        </Card>
      </div>

      <div className="grid grid-cols-3 gap-5">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold" style={{ color: P.ink }}>Recent Activity</h3>
          </div>
          <div className="space-y-3">
            {recentActivity.map((a, i) => (
              <div key={i} className="flex items-start gap-2.5 text-sm">
                <span className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{ background: toneDot[a.tone] }} />
                <div>
                  <div style={{ color: P.ink }}>{a.text}</div>
                  <div className="text-xs" style={{ color: P.sub }}>{a.meta} · {a.time}</div>
                </div>
              </div>
            ))}
          </div>
          <button onClick={() => setTab("changelog")} className="text-xs font-semibold mt-3 flex items-center gap-1" style={{ color: P.blue }}>
            View All Activity <ArrowRight size={12} />
          </button>
        </Card>

        <Card className="p-5">
          <h3 className="text-sm font-bold mb-3" style={{ color: P.ink }}>Top CPSEs by Harmonized Materials</h3>
          <ResponsiveContainer width="100%" height={190}>
            <BarChart data={cpseList} layout="vertical" margin={{ left: 8 }}>
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: P.ink }} width={44} axisLine={false} tickLine={false} />
              <Tooltip />
              <Bar dataKey="harmonized" radius={[0, 4, 4, 0]} fill={P.blue} />
            </BarChart>
          </ResponsiveContainer>
          <button onClick={() => setTab("cpse")} className="text-xs font-semibold mt-1 flex items-center gap-1" style={{ color: P.blue }}>
            View All CPSEs <ArrowRight size={12} />
          </button>
        </Card>

        <Card className="p-5">
          <h3 className="text-sm font-bold mb-3" style={{ color: P.ink }}>Quick Actions</h3>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: "Search Material", icon: Search, tab: "search" },
              { label: "New Harmonization", icon: GitMerge, tab: "harmonization" },
              { label: "Review Approvals", icon: CheckSquare, tab: "approval" },
              { label: "Add Material", icon: PlusCircle, tab: "master" },
              { label: "Generate Report", icon: FileBarChart2, tab: "analytics" },
              { label: "CPSE Directory", icon: Building2, tab: "cpse" },
            ].map((q) => (
              <button key={q.label} onClick={() => setTab(q.tab)}
                className="flex flex-col items-start gap-2 p-3 rounded-lg border text-left hover:bg-slate-50 transition-colors" style={{ borderColor: P.line }}>
                <q.icon size={16} color={P.blue} />
                <span className="text-xs font-semibold" style={{ color: P.ink }}>{q.label}</span>
              </button>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {impactMetrics.map((m) => (
          <Card key={m.label} className="p-4">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-2" style={{ background: P.blueSoft }}>
              <m.icon size={15} color={P.blue} />
            </div>
            <div className="text-xl font-bold" style={{ color: P.navy }}>{m.value}</div>
            <div className="text-xs font-semibold mt-0.5" style={{ color: P.ink }}>{m.label}</div>
            <div className="text-[11px] mt-1" style={{ color: P.sub }}>{m.note}</div>
          </Card>
        ))}
      </div>

      <AIEngineSection approvals={approvals} onDecide={onDecide} onCompare={onCompare} />
    </div>
  );
}

/* ============================== Material Search tab ============================== */
function MaterialSearchTab() {
  const [query, setQuery] = useState("");
  const filters = ["Material Name", "Material Code", "CPSE", "Category", "Specification", "Status", "AI Confidence"];
  const result = {
    name: "Seamless Carbon Steel Pipe",
    existing: ["IOCL-1023", "ONGC-4481", "BPCL-0912"],
    match: 96.8,
    code: "CS-PIPE-00124",
    status: "Human Approval Required",
  };
  return (
    <div>
      <h2 className="text-lg font-bold mb-1" style={{ color: P.navy }}>Material Search</h2>
      <p className="text-sm mb-4" style={{ color: P.sub }}>Search across every CPSE's material catalogue in one place.</p>
      <Card className="p-4">
        <div className="flex items-center gap-2 rounded-lg border px-3 py-2.5" style={{ borderColor: P.line, background: P.paper }}>
          <Search size={16} color={P.sub} />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search by material name, specification, existing code, CPSE or category..."
            className="flex-1 bg-transparent text-sm outline-none" style={{ color: P.ink }} />
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {filters.map((f) => (
            <span key={f} className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full border" style={{ borderColor: P.line, color: P.sub }}>
              <Filter size={11} />{f}
            </span>
          ))}
        </div>
      </Card>

      <Card className="p-5 mt-4">
        <div className="text-xs font-bold uppercase tracking-wide mb-3" style={{ color: P.sub }}>Example Result</div>
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <div className="text-base font-bold" style={{ color: P.navy }}>{result.name}</div>
            <div className="text-xs mt-2" style={{ color: P.sub }}>Existing Codes</div>
            <div className="flex gap-1.5 mt-1 flex-wrap">
              {result.existing.map((c) => (
                <span key={c} className="text-xs font-mono px-2 py-1 rounded" style={{ background: P.graySoft, color: P.ink }}>{c}</span>
              ))}
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs font-semibold" style={{ color: P.sub }}>AI Match</div>
            <div className="text-lg font-bold" style={{ color: P.green }}>{result.match}%</div>
            <div className="text-xs font-semibold mt-2" style={{ color: P.sub }}>Suggested Common Code</div>
            <div className="text-sm font-bold font-mono" style={{ color: P.blue }}>{result.code}</div>
            <div className="mt-2"><StatusPill status="Pending" /></div>
          </div>
        </div>
      </Card>
    </div>
  );
}

/* ============================== Approval Center tab ============================== */
function ApprovalCenterTab({ approvals, onDecide, onCompare }) {
  const [filter, setFilter] = useState("Pending");
  const pendingCount = approvals.filter((a) => a.status === "Pending").length;
  const rows = filter === "All" ? approvals : approvals.filter((a) => a.status === filter);
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-lg font-bold" style={{ color: P.navy }}>Approval Center</h2>
        <div className="flex gap-2">
          {["Pending", "Approved", "Rejected", "All"].map((f) => (
            <button key={f} onClick={() => setFilter(f)}
              className="text-xs font-semibold px-3 py-1.5 rounded-full border"
              style={{ borderColor: filter === f ? P.navy : P.line, background: filter === f ? P.navy : "#fff", color: filter === f ? "#fff" : P.sub }}>
              {f}
            </button>
          ))}
        </div>
      </div>
      <p className="text-sm mb-4" style={{ color: P.sub }}>{pendingCount.toLocaleString()} recommendations awaiting approval</p>
      <Card className="overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left" style={{ background: P.paper }}>
              {["Material", "CPSE", "AI Recommendation", "Confidence", "Status", "Action"].map((h) => (
                <th key={h} className="px-4 py-3 text-xs font-bold" style={{ color: P.sub }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t" style={{ borderColor: P.line }}>
                <td className="px-4 py-3 font-semibold" style={{ color: P.ink }}>{r.material}</td>
                <td className="px-4 py-3" style={{ color: P.ink }}>{r.cpse}</td>
                <td className="px-4 py-3 font-mono text-xs font-semibold" style={{ color: P.blue }}>{r.code}</td>
                <td className="px-4 py-3"><ConfidencePill value={r.confidence} /></td>
                <td className="px-4 py-3"><StatusPill status={r.status} /></td>
                <td className="px-4 py-3">
                  <div className="flex gap-1.5">
                    <button onClick={() => onCompare(r)} className="text-xs font-semibold px-2.5 py-1.5 rounded-md border" style={{ borderColor: P.line, color: P.navy }}>Review</button>
                    {r.status === "Pending" && (
                      <>
                        <button onClick={() => onDecide(r.id, "Approved")} className="text-xs font-semibold px-2.5 py-1.5 rounded-md text-white" style={{ background: P.green }}>Approve</button>
                        <button onClick={() => onDecide(r.id, "Rejected")} className="text-xs font-semibold px-2.5 py-1.5 rounded-md" style={{ background: P.redSoft, color: P.red }}>Reject</button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <div className="flex items-start gap-2.5 mt-4 text-xs rounded-lg p-3" style={{ background: P.blueSoft, color: P.navy }}>
        <AlertCircle size={15} className="shrink-0 mt-0.5" />
        Human approval is mandatory for low-confidence matches, conflicting specifications, safety-critical and high-value materials, new standardized-code creation, and any exception flagged by AI.
      </div>
    </div>
  );
}

/* ============================== Material Master tab ============================== */
function MaterialMasterTab() {
  return (
    <div>
      <h2 className="text-lg font-bold mb-1" style={{ color: P.navy }}>Material Master</h2>
      <p className="text-sm mb-4" style={{ color: P.sub }}>The standardized common material-code database — updated only after human approval.</p>
      <Card className="overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left" style={{ background: P.paper }}>
              {["Common Code", "Material", "Linked CPSE Codes", "CPSEs", "Approved On"].map((h) => (
                <th key={h} className="px-4 py-3 text-xs font-bold" style={{ color: P.sub }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {materialMaster.map((m) => (
              <tr key={m.code} className="border-t" style={{ borderColor: P.line }}>
                <td className="px-4 py-3 font-mono font-semibold" style={{ color: P.blue }}>{m.code}</td>
                <td className="px-4 py-3 font-semibold" style={{ color: P.ink }}>{m.name}</td>
                <td className="px-4 py-3" style={{ color: P.sub }}>{m.linked} codes merged</td>
                <td className="px-4 py-3" style={{ color: P.ink }}>{m.cpses}</td>
                <td className="px-4 py-3" style={{ color: P.sub }}>{m.date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

/* ============================== CPSE Directory tab ============================== */
function CPSEDirectoryTab() {
  return (
    <div>
      <h2 className="text-lg font-bold mb-1" style={{ color: P.navy }}>CPSE Directory</h2>
      <p className="text-sm mb-4" style={{ color: P.sub }}>Central Public Sector Enterprises onboarded to the harmonization platform.</p>
      <div className="grid grid-cols-3 gap-4">
        {cpseList.map((c) => (
          <Card key={c.name} className="p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: P.blueSoft }}>
                <Building2 size={16} color={P.blue} />
              </div>
              <span className="text-xs font-medium px-2 py-1 rounded-full" style={{ background: P.graySoft, color: P.sub }}>{c.sector}</span>
            </div>
            <div className="text-sm font-bold" style={{ color: P.navy }}>{c.name}</div>
            <div className="text-xs" style={{ color: P.sub }}>{c.full}</div>
            <div className="text-lg font-bold mt-3" style={{ color: P.ink }}>{c.harmonized.toLocaleString()}</div>
            <div className="text-[11px]" style={{ color: P.sub }}>materials harmonized</div>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ============================== Analytics & Reports tab ============================== */
function AnalyticsTab() {
  const reports = [
    { name: "Weekly Harmonization Summary", desc: "Progress across all CPSEs for the current week." },
    { name: "Approval Turnaround Report", desc: "Average time from AI recommendation to human decision." },
    { name: "Procurement Savings Report", desc: "Estimated savings from consolidated material codes." },
  ];
  return (
    <div>
      <h2 className="text-lg font-bold mb-4" style={{ color: P.navy }}>Analytics &amp; Reports</h2>
      <Card className="p-5 mb-5">
        <h3 className="text-sm font-bold mb-3" style={{ color: P.ink }}>AI Harmonization Trend</h3>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" stroke={P.line} vertical={false} />
            <XAxis dataKey="week" tick={{ fontSize: 11, fill: P.sub }} axisLine={{ stroke: P.line }} />
            <YAxis tick={{ fontSize: 11, fill: P.sub }} axisLine={{ stroke: P.line }} />
            <Tooltip />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey="harmonized" name="Harmonized" stroke={P.green} strokeWidth={2.5} dot={false} />
            <Line type="monotone" dataKey="review" name="Under AI Review" stroke={P.blue} strokeWidth={2.5} dot={false} />
            <Line type="monotone" dataKey="pending" name="Pending Approval" stroke={P.orange} strokeWidth={2.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </Card>
      <div className="grid grid-cols-3 gap-5">
        {reports.map((r) => (
          <Card key={r.name} className="p-5 flex flex-col justify-between">
            <div>
              <div className="w-9 h-9 rounded-lg flex items-center justify-center mb-3" style={{ background: P.blueSoft }}>
                <FileBarChart2 size={16} color={P.blue} />
              </div>
              <div className="text-sm font-bold" style={{ color: P.ink }}>{r.name}</div>
              <p className="text-xs mt-1.5" style={{ color: P.sub }}>{r.desc}</p>
            </div>
            <button className="mt-4 text-xs font-semibold px-3 py-2 rounded-md text-white flex items-center justify-center gap-1.5" style={{ background: P.navy }}>
              <Download size={13} /> Download
            </button>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ============================== Change Log tab ============================== */
function ChangeLogTab({ changeLog }) {
  return (
    <div>
      <h2 className="text-lg font-bold mb-1" style={{ color: P.navy }}>Change Log</h2>
      <p className="text-sm mb-4" style={{ color: P.sub }}>Complete audit trail — every AI recommendation and human decision, fully traceable.</p>
      <Card className="overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left" style={{ background: P.paper }}>
              {["Date", "Time", "Actor", "Action", "Material", "AI Confidence", "Version"].map((h) => (
                <th key={h} className="px-4 py-2.5 text-xs font-bold" style={{ color: P.sub }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {changeLog.map((c, i) => (
              <tr key={i} className="border-t" style={{ borderColor: P.line }}>
                <td className="px-4 py-2.5" style={{ color: P.sub }}>{c.date}</td>
                <td className="px-4 py-2.5 font-mono text-xs" style={{ color: P.sub }}>{c.time}</td>
                <td className="px-4 py-2.5 font-semibold" style={{ color: P.navy }}>{c.actor}</td>
                <td className="px-4 py-2.5" style={{ color: P.ink }}>{c.action}</td>
                <td className="px-4 py-2.5" style={{ color: P.ink }}>{c.material}</td>
                <td className="px-4 py-2.5" style={{ color: P.sub }}>{c.confidence}</td>
                <td className="px-4 py-2.5 font-mono text-xs" style={{ color: P.sub }}>{c.version}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

/* ============================== Notifications tab ============================== */
function NotificationsTab({ notifications }) {
  const iconFor = { approval: CheckSquare, ai: GitMerge, system: Bell };
  const toneFor = { approval: P.orange, ai: P.blue, system: P.navy };
  return (
    <div>
      <h2 className="text-lg font-bold mb-4" style={{ color: P.navy }}>Notifications</h2>
      <Card className="divide-y" style={{ borderColor: P.line }}>
        {notifications.map((n, i) => {
          const Icon = iconFor[n.type];
          return (
            <div key={i} className="flex items-start gap-3 p-4">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: `${toneFor[n.type]}18` }}>
                <Icon size={15} color={toneFor[n.type]} />
              </div>
              <div>
                <div className="text-sm" style={{ color: P.ink }}>{n.text}</div>
                <div className="text-xs mt-0.5" style={{ color: P.sub }}>{n.time}</div>
              </div>
            </div>
          );
        })}
      </Card>
    </div>
  );
}

/* ============================== Settings tab ============================== */
function SettingsTab() {
  const rows = [
    { label: "Auto-flag duplicate threshold", value: "≥ 85% similarity" },
    { label: "Auto-recommend confidence floor", value: "≥ 80%" },
    { label: "Require human approval below", value: "95% confidence" },
    { label: "Notify approver on new recommendation", value: "Enabled" },
  ];
  return (
    <div>
      <h2 className="text-lg font-bold mb-4" style={{ color: P.navy }}>Settings</h2>
      <Card className="p-5 max-w-xl">
        <h3 className="text-sm font-bold mb-3" style={{ color: P.ink }}>Harmonization Engine Configuration</h3>
        <div className="divide-y" style={{ borderColor: P.line }}>
          {rows.map((r) => (
            <div key={r.label} className="flex items-center justify-between py-3">
              <span className="text-sm" style={{ color: P.ink }}>{r.label}</span>
              <span className="text-sm font-semibold" style={{ color: P.navy }}>{r.value}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

/* ============================== shell ============================== */
export default function MaterialHarmonizationDashboard() {
  const [tab, setTab] = useState("dashboard");
  const [approvals, setApprovals] = useState(initialApprovals);
  const [changeLog, setChangeLog] = useState(initialChangeLog);
  const [notifications] = useState(initialNotifications);
  const [compareItem, setCompareItem] = useState(null);
  const [toast, setToast] = useState("");

  const handleDecide = (id, status) => {
    const item = approvals.find((a) => a.id === id);
    setApprovals((prev) => prev.map((a) => (a.id === id ? { ...a, status } : a)));
    setChangeLog((prev) => [
      { time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }), date: "30 Aug 2026",
        actor: "Admin User", action: `${status} recommendation ${item?.code || ""}`, material: item?.material || "", confidence: `${item?.confidence}%`, version: "v1" },
      ...prev,
    ]);
    setToast(status === "Approved" ? `${item?.code} approved and added to Material Master` : `${item?.code} rejected`);
    setCompareItem(null);
  };

  const pendingCount = approvals.filter((a) => a.status === "Pending").length;
  const title = navItems.find((n) => n.key === tab)?.label;

  return (
    <div className="w-full min-h-[760px] flex" style={{ background: P.paper, fontFamily: "'Inter', system-ui, sans-serif" }}>
      {/* Sidebar */}
      <aside className="w-64 shrink-0 flex flex-col" style={{ background: P.navyDeep }}>
        <div className="px-5 py-5 border-b" style={{ borderColor: "rgba(255,255,255,0.08)" }}>
          <div className="text-white font-extrabold text-xl leading-snug tracking-wide">
            UniMat
          </div>
          <div className="text-[10px] leading-tight mt-1.5" style={{ color: "#8FA3C4" }}>
            AI-Powered CPSE Material Harmonization
          </div>
        </div>
        <nav className="flex-1 py-3 px-3 space-y-1 overflow-y-auto">
          {navItems.map((n) => {
            const Icon = n.icon;
            const isActive = tab === n.key;
            const badge = n.key === "approval" ? pendingCount : n.key === "notifications" ? notifications.length : null;
            return (
              <button key={n.key} onClick={() => setTab(n.key)}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
                style={{ background: isActive ? P.navySoft : "transparent", color: isActive ? "#fff" : "#93A6C2" }}>
                <Icon size={16} className="shrink-0" />
                <span className="flex-1 text-left truncate">{n.label}</span>
                {badge > 0 && (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full shrink-0" style={{ background: P.orange, color: "#fff" }}>
                    {badge > 999 ? "999+" : badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
        <div className="px-5 py-4 border-t flex items-center gap-2.5" style={{ borderColor: "rgba(255,255,255,0.08)" }}>
          <div className="w-8 h-8 rounded-md flex items-center justify-center shrink-0" style={{ background: "rgba(255,255,255,0.08)" }}>
            <Landmark size={16} color="#8FA3C4" />
          </div>
          <div className="text-[10px] leading-tight" style={{ color: "#8FA3C4" }}>
            <div className="font-semibold text-white">Government of India</div>
            CPSE Material Harmonization Initiative
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 flex items-center justify-between px-6 border-b bg-white gap-4" style={{ borderColor: P.line }}>
          <div className="flex items-center gap-3 min-w-0">
            <button className="p-1.5 rounded-md hover:bg-slate-100"><Menu size={18} color={P.sub} /></button>
            <h1 className="text-base font-bold truncate" style={{ color: P.navy }}>{title}</h1>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <div className="hidden lg:flex items-center gap-2 rounded-lg px-3 py-1.5 border" style={{ borderColor: P.line, background: P.paper, width: 220 }}>
              <Search size={14} color={P.sub} />
              <span className="text-xs" style={{ color: P.sub }}>Global search...</span>
            </div>
            <span className="flex items-center gap-1 text-xs font-semibold px-2.5 py-1.5 rounded-md border" style={{ borderColor: P.line, color: P.ink }}>
              Last 30 Days <ChevronDown size={12} />
            </span>
            <button onClick={() => setTab("notifications")} className="relative p-1.5 rounded-md hover:bg-slate-100">
              <Bell size={18} color={P.sub} />
              {notifications.length > 0 && (
                <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full text-white text-[9px] font-bold flex items-center justify-center" style={{ background: P.red }}>
                  {notifications.length}
                </span>
              )}
            </button>
            <HelpCircle size={18} color={P.sub} />
            <div className="flex items-center gap-2 pl-2 border-l" style={{ borderColor: P.line }}>
              <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white" style={{ background: P.navy }}>AU</div>
              <div className="hidden md:block">
                <div className="text-xs font-semibold" style={{ color: P.ink }}>Admin User</div>
                <div className="text-[10px]" style={{ color: P.sub }}>CPSE Administrator</div>
              </div>
              <ChevronDown size={14} color={P.sub} />
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          {tab === "dashboard" && <DashboardTab approvals={approvals} onDecide={handleDecide} onCompare={setCompareItem} setTab={setTab} />}
          {tab === "search" && <MaterialSearchTab />}
          {tab === "harmonization" && (
            <div className="space-y-5">
              <div>
                <h2 className="text-lg font-bold mb-1" style={{ color: P.navy }}>AI Harmonization</h2>
                <p className="text-sm" style={{ color: P.sub }}>AI-detected duplicate materials and recommended common codes, pending expert sign-off.</p>
              </div>
              <AIEngineSection approvals={approvals} onDecide={handleDecide} onCompare={setCompareItem} />
            </div>
          )}
          {tab === "approval" && <ApprovalCenterTab approvals={approvals} onDecide={handleDecide} onCompare={setCompareItem} />}
          {tab === "master" && <MaterialMasterTab />}
          {tab === "cpse" && <CPSEDirectoryTab />}
          {tab === "analytics" && <AnalyticsTab />}
          {tab === "changelog" && <ChangeLogTab changeLog={changeLog} />}
          {tab === "notifications" && <NotificationsTab notifications={notifications} />}
          {tab === "settings" && <SettingsTab />}
        </main>
      </div>

      <CompareModal item={compareItem} onClose={() => setCompareItem(null)} onDecide={handleDecide} />
      <Toast message={toast} onClose={() => setToast("")} />
    </div>
  );
}
