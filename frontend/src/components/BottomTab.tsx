import { Home, Disc, MessageSquareText, LogOut } from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../store/auth";


const Tab = ({ to, icon: Icon, label }: { to: string; icon: any; label: string }) => (
  <NavLink to={to} className={({ isActive }) => `flex flex-col items-center gap-1 px-4 py-2 ${isActive ? "text-white" : "text-white/60"}`}>
    <Icon size={20} />
    <span className="text-xs">{label}</span>
  </NavLink>
);


export default function BottomTab() {
  const logout = useAuth(s => s.logout);
  const nav = useNavigate();
  const onLogout = () => { logout(); nav("/login"); };


    return (
    <nav
      className="fixed bottom-3 left-1/2 -translate-x-1/2
                 w-[95%] max-w-screen-lg bg-bg-card/90 backdrop-blur
                 border border-white/10 rounded-3xl shadow-soft
                 flex items-center justify-around py-2"
    >
      <Tab to="/" icon={Home} label="Feed" />
      <Tab to="/collection" icon={Disc} label="Coleção" />
      <Tab to="/dms" icon={MessageSquareText} label="DMs" />
      <button onClick={onLogout} className="flex flex-col items-center gap-1 px-4 py-2 text-white/60">
        <LogOut size={20} />
        <span className="text-xs">Sair</span>
      </button>
    </nav>
  );
}