import { create } from "zustand";
import api from "../lib/api";


type User = { id: string; username: string; email: string };


type AuthState = {
  token: string | null;
  user: User | null;
  login: (uOrE: string, password: string) => Promise<void>;
  fetchMe: () => Promise<void>;
  logout: () => void;
};


export const useAuth = create<AuthState>((set) => ({
  token: localStorage.getItem("token"),
  user: null,
  async login(uOrE, password) {
    const { data } = await api.post("/auth/login", { username_or_email: uOrE, password });
    localStorage.setItem("token", data.access_token);
    set({ token: data.access_token });
    await api.get("/auth/me").then((r) => set({ user: r.data }));
  },
  async fetchMe() {
    const { data } = await api.get("/auth/me");
    set({ user: data });
  },
  logout() {
    localStorage.removeItem("token");
    set({ token: null, user: null });
  },
}));