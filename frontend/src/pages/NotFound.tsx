import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 text-slate-500">
      <p className="text-4xl font-bold text-slate-300">404</p>
      <p>This page does not exist.</p>
      <Link to="/dashboard" className="text-brand-600 hover:underline">
        Back to dashboard
      </Link>
    </div>
  );
}
