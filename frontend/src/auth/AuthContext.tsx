import * as React from "react";

import { fetchMe, login as loginRequest, type LoginPayload } from "@/services/auth";
import type { User } from "@/types";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<User>;
  logout: () => void;
}

const AuthContext = React.createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<User | null>(() => {
    const cached = localStorage.getItem("current_user");
    return cached ? (JSON.parse(cached) as User) : null;
  });
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setIsLoading(false);
      return;
    }
    fetchMe()
      .then((me) => {
        setUser(me);
        localStorage.setItem("current_user", JSON.stringify(me));
      })
      .catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("current_user");
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = React.useCallback(async (payload: LoginPayload) => {
    const { access_token, user: loggedInUser } = await loginRequest(payload);
    localStorage.setItem("access_token", access_token);
    localStorage.setItem("current_user", JSON.stringify(loggedInUser));
    setUser(loggedInUser);
    return loggedInUser;
  }, []);

  const logout = React.useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("current_user");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
