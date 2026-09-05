import * as React from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Landmark } from "lucide-react";

import { useAuth } from "@/auth/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiErrorMessage } from "@/services/api";

const DEMO_ACCOUNTS = [
  { role: "Admin", username: "admin", password: "Admin@123" },
  { role: "Material Expert", username: "raj.kumar", password: "Expert@123" },
  { role: "CPSE User (IOCL)", username: "iocl.user", password: "Cpse@123" },
  { role: "Viewer", username: "viewer", password: "Viewer@123" },
];

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  if (user) {
    const from = (location.state as { from?: Location })?.from?.pathname || "/dashboard";
    return <Navigate to={from} replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login({ username, password });
      navigate("/dashboard");
    } catch (err) {
      setError(apiErrorMessage(err, "Invalid User ID or Password"));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-100">
      <div className="gov-stripe h-[3px] w-full" />
      <div className="border-b border-slate-300 bg-navy-950 px-6 py-3 text-center text-xs font-semibold uppercase tracking-widest text-slate-300">
        Government of India &middot; Central Public Sector Enterprises
      </div>

      <div className="flex flex-1 items-center justify-center p-4">
        <div className="grid w-full max-w-4xl grid-cols-1 overflow-hidden rounded border border-slate-300 shadow-card md:grid-cols-2">
          <div className="hidden flex-col justify-between bg-navy-950 p-10 text-white md:flex">
            <div className="flex h-10 w-10 items-center justify-center rounded border border-white/10 bg-brand-600">
              <Landmark className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold uppercase leading-tight tracking-wide">CPSE Material Harmonization</h1>
              <p className="mt-4 text-xs text-slate-400">AI-Powered CPSE Material Harmonization Platform</p>
            </div>
            <p className="text-xs font-semibold uppercase tracking-wide text-warning-500">Prototype for Demonstration</p>
          </div>

          <Card className="rounded-none border-0">
            <CardContent className="p-10">
              <h2 className="text-xl font-bold text-slate-900">CPSE Material Harmonization Platform</h2>
              <p className="mb-6 mt-1 text-sm text-slate-500">Sign in to access your material harmonization workspace</p>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="username">User ID</Label>
                  <Input
                    id="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="e.g. admin"
                    required
                    autoFocus
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                  />
                </div>
                {error && <p className="text-sm text-danger-600">{error}</p>}
                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting ? "Signing in..." : "LOGIN"}
                </Button>
                <button type="button" className="text-xs text-brand-600 hover:underline">
                  Forgot Password?
                </button>
              </form>

              <div className="mt-6 rounded border border-slate-300 bg-slate-50 p-3">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Demo credentials (prototype only)
                </p>
                <ul className="space-y-1 text-xs text-slate-600">
                  {DEMO_ACCOUNTS.map((acc) => (
                    <li key={acc.username} className="flex justify-between">
                      <span>{acc.role}</span>
                      <span className="font-mono">
                        {acc.username} / {acc.password}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              <p className="mt-4 text-center text-xs text-slate-400">Authorized CPSE personnel only.</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
