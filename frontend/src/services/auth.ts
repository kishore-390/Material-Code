import { api } from "@/services/api";
import type { User } from "@/types";

export interface LoginPayload {
  username: string;
  password: string;
}

export interface RegisterPayload {
  username: string;
  email: string;
  full_name: string;
  password: string;
  role_name: string;
  cpse_code?: string;
}

export async function login(payload: LoginPayload) {
  const { data } = await api.post<{ access_token: string; user: User }>("/auth/login", payload);
  return data;
}

export async function register(payload: RegisterPayload) {
  const { data } = await api.post<User>("/auth/register", payload);
  return data;
}

export async function fetchMe() {
  const { data } = await api.get<User>("/auth/me");
  return data;
}
