import { Heart } from "lucide-react";
import { Link } from "react-router-dom";
import { type RecordItem } from "../types";

export default function RecordCard({
  rec, badge, favorite, onToggleFav,
}: {
  rec: RecordItem; badge?: string; favorite?: boolean; onToggleFav?: () => void;
}) {
  const apiBase = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const cover = rec.cover_url || `${apiBase}/uploads/covers/${rec.id}.webp`;

  return (
    <div className="card overflow-hidden">
      <Link to={`/record/${rec.id}`} state={{ record: rec }} className="block">
        <div className="relative aspect-[4/3] bg-gradient-to-br from-zinc-600/40 to-zinc-800/40">
          <img src={cover} onError={(e)=>{(e.currentTarget as HTMLImageElement).style.display='none';}}
               alt={rec.title} className="w-full h-full object-cover" />
          <button
            onClick={(e)=>{ e.preventDefault(); onToggleFav?.(); }}
            className={`absolute top-2 right-2 rounded-full border px-2 py-1 text-xs backdrop-blur ${
              favorite ? "bg-white text-black border-white" : "bg-black/40 text-white border-white/20"
            }`}
          >
            <span className="inline-flex items-center gap-1">
              <Heart size={14} fill={favorite ? "currentColor" : "none"} /> {favorite ? "Fav" : "Favoritar"}
            </span>
          </button>
        </div>
        <div className="p-3">
          <div className="font-semibold leading-tight line-clamp-1">{rec.title}</div>
          <div className="text-sm text-white/70 line-clamp-1">{rec.artist}</div>
          <div className="mt-2 flex items-center justify-between">
            <div className="text-xs text-white/50">{rec.year ?? ""}</div>
            {badge && <span className="badge">{badge}</span>}
          </div>
        </div>
      </Link>
    </div>
  );
}
