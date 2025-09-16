import { useState } from "react";
import { useAuth } from "../store/auth";
import { useNavigate } from "react-router-dom";


export default function Login() {
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const login = useAuth((s) => s.login);
  const nav = useNavigate();


  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await login(u, p);
      nav("/collection");
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "Falha no login");
    }
  }


  return (
    <div className="min-h-screen bg-app grid place-items-center">
      <form onSubmit={onSubmit} className="card w-[90%] max-w-md p-6 space-y-4">
        <div>
          <h1 className="text-2xl font-bold">Retrofagia</h1>
          <p className="text-white/70 text-sm">Sua coleção de música vintage</p>
        </div>
        <div className="space-y-2">
          <label className="text-sm text-white/80">Usuário ou e‑mail</label>
          <input className="input" placeholder="Digite seu usuário" value={u} onChange={(e)=>setU(e.target.value)} />
        </div>
        <div className="space-y-2">
          <label className="text-sm text-white/80">Senha</label>
          <input className="input" type="password" placeholder="Digite sua senha" value={p} onChange={(e)=>setP(e.target.value)} />
        </div>
        {err && <p className="text-sm text-red-400">{err}</p>}
        <button className="btn w-full">Entrar</button>
        <p className="text-xs text-white/50">Dica: jorge / 123456 (do seu backend)</p>
      </form>
    </div>
  );
}