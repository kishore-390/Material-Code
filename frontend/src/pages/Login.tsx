import * as React from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Shield } from "lucide-react";

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
      setError(apiErrorMessage(err, "Invalid username or password"));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-navy-950 p-4">
      <div className="grid w-full max-w-4xl grid-cols-1 overflow-hidden rounded-2xl shadow-2xl md:grid-cols-2">
        <div className="hidden flex-col justify-between bg-gradient-to-br from-navy-900 to-navy-700 p-10 text-white md:flex">
          <div className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600">
              <Shield className="h-6 w-6" />
            </div>
          </div>
          <div>
            <h1 className="text-3xl font-bold leading-tight">
              ONE NATION
              <br />
              ONE COMMON
              <br />
              MATERIAL CODE
            </h1>
            <p className="mt-4 text-sm text-slate-300">
              AI-Powered CPSE Material Harmonization Platform
            </p>
          </div>
          <p className="text-xs text-slate-400">
            Government of India &middot; Central Public Sector Enterprises
          </p>
        </div>

        <Card className="rounded-none border-0 md:rounded-r-2xl">
          <CardContent className="p-10">
            <h2 className="text-xl font-bold text-slate-900">Sign in</h2>
            <p className="mb-6 mt-1 text-sm text-slate-500">Access your material harmonization workspace</p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="username">Username</Label>
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
                {isSubmitting ? "Signing in..." : "Sign in"}
              </Button>
            </form>

            <div className="mt-6 rounded-lg bg-slate-50 p-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                Demo credentials
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
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
